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
            vault_access BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE TABLE IF NOT EXISTS device_logins (
            device_hash TEXT PRIMARY KEY,
            user_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            expires_at BIGINT NOT NULL,
            state TEXT NOT NULL,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            polled_at BIGINT NOT NULL,
            vault_access BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE TABLE IF NOT EXISTS auth_attempts (
            key TEXT PRIMARY KEY,
            count INTEGER NOT NULL,
            resets_at BIGINT NOT NULL
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
            PRIMARY KEY(owner, id)
        );
        CREATE INDEX IF NOT EXISTS records_owner_kind_created_idx
            ON records(owner, kind, created_at DESC, id);
        CREATE INDEX IF NOT EXISTS records_owner_active_idx
            ON records(owner, created_at DESC, id) WHERE archived_at IS NULL;

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
            PRIMARY KEY(owner, id),
            FOREIGN KEY(owner, source_id) REFERENCES records(owner, id) ON DELETE CASCADE,
            FOREIGN KEY(owner, target_id) REFERENCES records(owner, id) ON DELETE CASCADE,
            CHECK (source_id <> target_id)
        );
        CREATE INDEX IF NOT EXISTS relations_owner_source_idx
            ON relations(owner, source_id, status);
        CREATE INDEX IF NOT EXISTS relations_owner_target_idx
            ON relations(owner, target_id, status);

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
            created_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY(owner, id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS feature_request_idempotency_idx
            ON feature_requests(owner, client_request_id) WHERE client_request_id IS NOT NULL;

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
