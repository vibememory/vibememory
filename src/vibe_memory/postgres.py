"""Shared PostgreSQL connection pool and schema.

PostgreSQL is the production source of truth when MEMORY_DATABASE_URL is set.
The compatibility wrapper lets the existing authentication stores use the same
transactional database while the legacy SQLite files remain migration inputs.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class CompatRow(dict):
    """A mapping that also supports sqlite3.Row-style numeric indexing."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


@dataclass
class CompatResult:
    rows: list[CompatRow]
    rowcount: int

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class CompatConnection:
    def __init__(self, connection):
        self.connection = connection

    @staticmethod
    def _sql(statement: str) -> str:
        return statement.replace("?", "%s")

    def execute(self, statement: str, parameters=()):
        cursor = self.connection.execute(self._sql(statement), parameters)
        rows = [CompatRow(row) for row in cursor.fetchall()] if cursor.description else []
        result = CompatResult(rows, cursor.rowcount)
        cursor.close()
        return result


class PostgresDatabase:
    def __init__(self, url: str, model: str, dimension: int, pool_size: int = 10):
        self.url = url
        self.model = model
        self.dimension = dimension
        self.pool = ConnectionPool(
            conninfo=url,
            min_size=1,
            max_size=pool_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        self.pool.wait(timeout=15)
        self._initialize()

    @contextmanager
    def connection(self):
        with self.pool.connection() as connection:
            yield connection

    @contextmanager
    def compat_connection(self):
        with self.pool.connection() as connection:
            yield CompatConnection(connection)

    def close(self):
        self.pool.close()

    def _initialize(self):
        dimension = int(self.dimension)
        schema = f"""
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS vm_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            prefix TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            vault_access BOOLEAN NOT NULL DEFAULT FALSE,
            feature_request_operator BOOLEAN NOT NULL DEFAULT FALSE,
            permissions TEXT NOT NULL DEFAULT '["memory:read","memory:write","files:read","files:write","messages:read","messages:write","feature:write","events:read"]'
        );
        ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS
            feature_request_operator BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS
            permissions TEXT NOT NULL DEFAULT '["memory:read","memory:write","files:read","files:write","messages:read","messages:write","feature:write","events:read"]';
        CREATE TABLE IF NOT EXISTS api_key_permission_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            api_key_id TEXT NOT NULL,
            key_name TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            changed_at BIGINT NOT NULL,
            before_permissions TEXT NOT NULL,
            after_permissions TEXT NOT NULL,
            before_vault_access BOOLEAN NOT NULL,
            after_vault_access BOOLEAN NOT NULL
        );
        CREATE INDEX IF NOT EXISTS api_key_permission_events_owner_idx
            ON api_key_permission_events(user_id, changed_at DESC, id DESC);
        CREATE TABLE IF NOT EXISTS device_logins (
            device_hash TEXT PRIMARY KEY,
            user_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            expires_at BIGINT NOT NULL,
            state TEXT NOT NULL,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            polled_at BIGINT NOT NULL,
            vault_access BOOLEAN NOT NULL DEFAULT FALSE,
            upgrade_key_id TEXT,
            upgrade_user_id TEXT
        );
        ALTER TABLE device_logins ADD COLUMN IF NOT EXISTS upgrade_key_id TEXT;
        ALTER TABLE device_logins ADD COLUMN IF NOT EXISTS upgrade_user_id TEXT;
        CREATE TABLE IF NOT EXISTS auth_attempts (
            key TEXT PRIMARY KEY,
            count INTEGER NOT NULL,
            resets_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_totp (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            nonce BYTEA NOT NULL,
            ciphertext BYTEA NOT NULL,
            enabled_at BIGINT NOT NULL,
            last_counter BIGINT NOT NULL DEFAULT -1
        );
        CREATE TABLE IF NOT EXISTS totp_setups (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            nonce BYTEA NOT NULL,
            ciphertext BYTEA NOT NULL,
            expires_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS recovery_codes (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            hash TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            PRIMARY KEY(user_id, hash)
        );
        CREATE TABLE IF NOT EXISTS login_challenges (
            hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at BIGINT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS oauth_clients (
            client_id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            redirect_uris TEXT NOT NULL,
            created_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oauth_codes (
            hash TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            redirect_uri TEXT NOT NULL,
            scope TEXT NOT NULL,
            resource TEXT NOT NULL,
            code_challenge TEXT NOT NULL,
            expires_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oauth_access_tokens (
            hash TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scope TEXT NOT NULL,
            resource TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            expires_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
            hash TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scope TEXT NOT NULL,
            resource TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            expires_at BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oauth_connections (
            client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            scope TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            last_used_at BIGINT NOT NULL,
            PRIMARY KEY(client_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS oauth_vault_grants (
            client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            PRIMARY KEY(client_id, user_id, name)
        );
        CREATE TABLE IF NOT EXISTS oauth_permission_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            client_id TEXT NOT NULL,
            client_name TEXT NOT NULL,
            changed_at BIGINT NOT NULL,
            before_scope TEXT NOT NULL,
            after_scope TEXT NOT NULL,
            source TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS oauth_permission_events_owner_idx
            ON oauth_permission_events(user_id, client_id, changed_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS records (
            owner TEXT NOT NULL,
            id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('memory','document','entity','file')),
            subtype TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            tags TEXT[] NOT NULL DEFAULT '{{}}',
            created_at TIMESTAMPTZ NOT NULL,
            keywords TEXT[] NOT NULL DEFAULT '{{}}',
            metadata JSONB NOT NULL DEFAULT '{{}}',
            file_id TEXT,
            version BIGINT NOT NULL DEFAULT 1,
            archived_at TIMESTAMPTZ,
            trust_level TEXT NOT NULL DEFAULT 'trusted'
                CHECK (trust_level IN ('trusted','untrusted')),
            security_state TEXT NOT NULL DEFAULT 'active'
                CHECK (security_state IN ('active','quarantined')),
            provenance JSONB NOT NULL DEFAULT '{{}}',
            content_hash TEXT NOT NULL DEFAULT '',
            security_warnings TEXT[] NOT NULL DEFAULT '{{}}',
            security_history JSONB NOT NULL DEFAULT '[]',
            creator_agent_id TEXT NOT NULL DEFAULT 'unknown',
            creator_agent_name TEXT NOT NULL DEFAULT 'Unknown agent',
            writer_history JSONB NOT NULL DEFAULT '[]',
            PRIMARY KEY(owner, id)
        );
        ALTER TABLE records ADD COLUMN IF NOT EXISTS trust_level TEXT NOT NULL
            DEFAULT 'trusted' CHECK (trust_level IN ('trusted','untrusted'));
        ALTER TABLE records ADD COLUMN IF NOT EXISTS security_state TEXT NOT NULL
            DEFAULT 'active' CHECK (security_state IN ('active','quarantined'));
        ALTER TABLE records ADD COLUMN IF NOT EXISTS provenance JSONB NOT NULL DEFAULT '{{}}';
        ALTER TABLE records ADD COLUMN IF NOT EXISTS content_hash TEXT NOT NULL DEFAULT '';
        ALTER TABLE records ADD COLUMN IF NOT EXISTS security_warnings TEXT[] NOT NULL DEFAULT '{{}}';
        ALTER TABLE records ADD COLUMN IF NOT EXISTS security_history JSONB NOT NULL DEFAULT '[]';
        ALTER TABLE records ADD COLUMN IF NOT EXISTS creator_agent_id TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE records ADD COLUMN IF NOT EXISTS creator_agent_name TEXT NOT NULL DEFAULT 'Unknown agent';
        ALTER TABLE records ADD COLUMN IF NOT EXISTS writer_history JSONB NOT NULL DEFAULT '[]';
        CREATE INDEX IF NOT EXISTS records_owner_kind_created_idx
            ON records(owner, kind, created_at DESC, id);
        CREATE INDEX IF NOT EXISTS records_owner_active_idx
            ON records(owner, created_at DESC, id) WHERE archived_at IS NULL;
        CREATE INDEX IF NOT EXISTS records_owner_security_idx
            ON records(owner, security_state, trust_level, created_at DESC, id)
            WHERE archived_at IS NULL;

        CREATE TABLE IF NOT EXISTS keyword_embeddings (
            id BIGSERIAL PRIMARY KEY,
            owner TEXT NOT NULL,
            record_id TEXT NOT NULL,
            keyword TEXT NOT NULL,
            normalized_keyword TEXT NOT NULL,
            embedding vector({dimension}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner, record_id) REFERENCES records(owner, id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS keyword_owner_record_idx
            ON keyword_embeddings(owner, record_id);
        CREATE INDEX IF NOT EXISTS keyword_owner_exact_idx
            ON keyword_embeddings(owner, normalized_keyword);

        CREATE TABLE IF NOT EXISTS relations (
            owner TEXT NOT NULL,
            id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active','retracted')),
            version BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            history JSONB NOT NULL,
            creator_agent_id TEXT NOT NULL DEFAULT 'unknown',
            creator_agent_name TEXT NOT NULL DEFAULT 'Unknown agent',
            confidence DOUBLE PRECISION CHECK (confidence >= 0 AND confidence <= 1),
            evidence_record_ids TEXT[] NOT NULL DEFAULT '{{}}',
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            evidence_coverage TEXT NOT NULL DEFAULT 'unknown'
                CHECK (evidence_coverage IN ('selected','partial','unknown')),
            input_manifest_id TEXT,
            extraction_method TEXT NOT NULL DEFAULT '',
            extraction_version TEXT NOT NULL DEFAULT '',
            correction_scope TEXT NOT NULL DEFAULT 'unknown'
                CHECK (correction_scope IN ('unknown','full','partial')),
            PRIMARY KEY(owner, id),
            FOREIGN KEY(owner, source_id) REFERENCES records(owner, id) ON DELETE CASCADE,
            FOREIGN KEY(owner, target_id) REFERENCES records(owner, id) ON DELETE CASCADE,
            CHECK (source_id <> target_id)
        );
        CREATE INDEX IF NOT EXISTS relations_owner_source_idx
            ON relations(owner, source_id, status);
        CREATE INDEX IF NOT EXISTS relations_owner_target_idx
            ON relations(owner, target_id, status);
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS creator_agent_id TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS creator_agent_name TEXT NOT NULL DEFAULT 'Unknown agent';
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION;
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS evidence_record_ids TEXT[] NOT NULL DEFAULT '{{}}';
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS evidence JSONB NOT NULL DEFAULT '[]'::jsonb;
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS evidence_coverage TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS correction_scope TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS input_manifest_id TEXT;
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS extraction_method TEXT NOT NULL DEFAULT '';
        ALTER TABLE relations ADD COLUMN IF NOT EXISTS extraction_version TEXT NOT NULL DEFAULT '';

        CREATE TABLE IF NOT EXISTS batch_operations (
            owner TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            client_request_id TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            result JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(owner, agent_id, operation, client_request_id)
        );
        CREATE INDEX IF NOT EXISTS batch_operations_owner_created_idx
            ON batch_operations(owner, created_at DESC);

        CREATE TABLE IF NOT EXISTS change_events (
            id BIGSERIAL PRIMARY KEY,
            owner TEXT NOT NULL,
            event TEXT NOT NULL,
            payload JSONB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS change_events_owner_id_idx ON change_events(owner, id);

        CREATE TABLE IF NOT EXISTS feature_requests (
            owner TEXT NOT NULL,
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            use_case TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL CHECK (priority IN ('low','medium','high')),
            source TEXT NOT NULL DEFAULT '',
            client_request_id TEXT,
            status TEXT NOT NULL,
            result TEXT NOT NULL DEFAULT '',
            result_url TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            resolved_at TIMESTAMPTZ,
            PRIMARY KEY(owner, id)
        );
        ALTER TABLE feature_requests ADD COLUMN IF NOT EXISTS result TEXT NOT NULL DEFAULT '';
        ALTER TABLE feature_requests ADD COLUMN IF NOT EXISTS result_url TEXT NOT NULL DEFAULT '';
        ALTER TABLE feature_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
        ALTER TABLE feature_requests ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
        UPDATE feature_requests SET updated_at=created_at WHERE updated_at IS NULL;
        ALTER TABLE feature_requests ALTER COLUMN updated_at SET NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS feature_request_idempotency_idx
            ON feature_requests(owner, client_request_id) WHERE client_request_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS agents (
            owner TEXT NOT NULL,
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            transport TEXT NOT NULL CHECK (transport IN ('api-key','oauth','legacy-key','browser')),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY(owner, id)
        );
        CREATE INDEX IF NOT EXISTS agents_owner_seen_idx
            ON agents(owner, last_seen_at DESC, id);

        CREATE TABLE IF NOT EXISTS agent_messages (
            sequence BIGSERIAL UNIQUE NOT NULL,
            owner TEXT NOT NULL,
            id TEXT NOT NULL,
            sender_agent_id TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            recipient_agent_id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('message','request','response','notification')),
            subject TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{{}}',
            thread_id TEXT NOT NULL,
            reply_to TEXT,
            client_request_id TEXT,
            request_payload JSONB NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued','delivered','read','acked')),
            created_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            delivered_at TIMESTAMPTZ,
            read_at TIMESTAMPTZ,
            acked_at TIMESTAMPTZ,
            PRIMARY KEY(owner, id),
            FOREIGN KEY(owner, sender_agent_id) REFERENCES agents(owner, id),
            FOREIGN KEY(owner, recipient_agent_id) REFERENCES agents(owner, id),
            FOREIGN KEY(owner, reply_to) REFERENCES agent_messages(owner, id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS agent_message_idempotency_idx
            ON agent_messages(owner, sender_agent_id, client_request_id)
            WHERE client_request_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS agent_message_inbox_idx
            ON agent_messages(owner, recipient_agent_id, sequence);
        CREATE INDEX IF NOT EXISTS agent_message_sent_idx
            ON agent_messages(owner, sender_agent_id, sequence DESC);

        CREATE TABLE IF NOT EXISTS vault_secrets (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            nonce BYTEA NOT NULL,
            ciphertext BYTEA NOT NULL,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL,
            last_accessed_at BIGINT,
            access_count BIGINT NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, name)
        );
        CREATE TABLE IF NOT EXISTS vault_captures (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            requester_agent_id TEXT NOT NULL,
            requester_agent_name TEXT NOT NULL,
            created_at BIGINT NOT NULL,
            expires_at BIGINT NOT NULL,
            consumed_at BIGINT
        );
        CREATE INDEX IF NOT EXISTS vault_captures_owner_idx
            ON vault_captures(user_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS vault_access_audit (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            client_id TEXT NOT NULL,
            name TEXT NOT NULL,
            accessed_at BIGINT NOT NULL,
            outcome TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS vault_access_audit_owner_idx
            ON vault_access_audit(user_id, accessed_at DESC, id DESC);
        """
        with self.pool.connection() as connection:
            for statement in (part.strip() for part in schema.split(";") if part.strip()):
                connection.execute(statement)
            current = {
                row["key"]: row["value"]
                for row in connection.execute(
                    "SELECT key,value FROM vm_meta WHERE key IN ('embedding_model','embedding_dimension')"
                ).fetchall()
            }
            expected = {"embedding_model": self.model, "embedding_dimension": str(dimension)}
            for key, value in expected.items():
                if key in current and current[key] != value:
                    raise ValueError(
                        f"PostgreSQL {key} is {current[key]!r}, expected {value!r}; rebuild the keyword index"
                    )
                connection.execute(
                    "INSERT INTO vm_meta(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",
                    (key, value),
                )


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".17g") for value in values) + "]"


def vector_from_text(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    text = str(value).strip()[1:-1]
    return [] if not text else [float(item) for item in text.split(",")]


IntegrityError = psycopg.IntegrityError
