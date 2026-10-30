"""OAuth 2.1 storage for remote MCP clients.

Only hashes of authorization codes and bearer tokens are persisted. Clients are
public PKCE clients; Vibe Memory never asks users to copy an MCP credential.
"""

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager

from .clock import utc_epoch_seconds
from .postgres import PostgresDatabase

ACCESS_TOKEN_SECONDS = 3600
REFRESH_TOKEN_SECONDS = 30 * 24 * 3600
AUTHORIZATION_CODE_SECONDS = 300
SUPPORTED_MCP_SCOPES = (
    "memory:read",
    "memory:write",
    "feature:write",
    "vault:read",
)


def token_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class OAuthError(Exception):
    def __init__(self, code: str, description: str):
        super().__init__(description)
        self.code = code
        self.description = description


class OAuthStore:
    def __init__(self, path):
        self.postgres = path if isinstance(path, PostgresDatabase) else None
        if self.postgres:
            self.path, self.lock = None, threading.RLock()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self.connection() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    redirect_uris TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_codes (
                    hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    redirect_uri TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    code_challenge TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_access_tokens (
                    hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    scope TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
                    hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    scope TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_token_revocations (
                    hash TEXT PRIMARY KEY,
                    reason TEXT NOT NULL DEFAULT 'revoked',
                    revoked_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_connections (
                    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    scope TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_used_at INTEGER NOT NULL,
                    PRIMARY KEY(client_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS oauth_vault_grants (
                    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY(client_id, user_id, name)
                );
                CREATE TABLE IF NOT EXISTS oauth_permission_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    client_id TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    changed_at INTEGER NOT NULL,
                    before_scope TEXT NOT NULL,
                    after_scope TEXT NOT NULL,
                    source TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS oauth_permission_events_owner_idx
                    ON oauth_permission_events(user_id, client_id, changed_at DESC, id DESC);
                """
            )
        path.chmod(0o600)

    @contextmanager
    def connection(self):
        if self.postgres:
            with self.postgres.compat_connection() as db:
                yield db
            return
        with self.lock:
            db = sqlite3.connect(self.path, timeout=10)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            try:
                with db:
                    yield db
            finally:
                db.close()

    @staticmethod
    def _cleanup(db, now):
        db.execute("DELETE FROM oauth_codes WHERE expires_at <= ?", (now,))
        expired = db.execute(
            "SELECT hash FROM oauth_access_tokens WHERE expires_at <= ?", (now,)
        ).fetchall()
        for row in expired:
            db.execute(
                """INSERT INTO oauth_token_revocations(hash,reason,revoked_at,expires_at)
                VALUES(?,?,?,?) ON CONFLICT(hash) DO UPDATE SET
                reason=excluded.reason,revoked_at=excluded.revoked_at,
                expires_at=excluded.expires_at""",
                (row["hash"], "expired", now, now + ACCESS_TOKEN_SECONDS),
            )
        db.execute("DELETE FROM oauth_access_tokens WHERE expires_at <= ?", (now,))
        db.execute("DELETE FROM oauth_refresh_tokens WHERE expires_at <= ?", (now,))
        db.execute("DELETE FROM oauth_token_revocations WHERE expires_at <= ?", (now,))
        db.execute(
            """DELETE FROM oauth_connections
            WHERE NOT EXISTS (
                SELECT 1 FROM oauth_access_tokens a
                WHERE a.client_id=oauth_connections.client_id
                AND a.user_id=oauth_connections.user_id AND a.expires_at>?
            ) AND NOT EXISTS (
                SELECT 1 FROM oauth_refresh_tokens r
                WHERE r.client_id=oauth_connections.client_id
                AND r.user_id=oauth_connections.user_id AND r.expires_at>?
            )""",
            (now, now),
        )
        db.execute(
            """DELETE FROM oauth_vault_grants
            WHERE NOT EXISTS (
                SELECT 1 FROM oauth_connections x
                WHERE x.client_id=oauth_vault_grants.client_id
                AND x.user_id=oauth_vault_grants.user_id
            )"""
        )

    def register_client(self, client_name, redirect_uris):
        now = utc_epoch_seconds()
        client_id = "vmc_" + secrets.token_urlsafe(24)
        with self.connection() as db:
            self._cleanup(db, now)
            db.execute(
                "INSERT INTO oauth_clients VALUES(?,?,?,?)",
                (client_id, client_name, json.dumps(redirect_uris), now),
            )
        return {
            "client_id": client_id,
            "client_id_issued_at": now,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }

    def client(self, client_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM oauth_clients WHERE client_id=?", (client_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["redirect_uris"] = json.loads(result["redirect_uris"])
        return result

    def create_code(
        self,
        *,
        client_id,
        user_id,
        redirect_uri,
        scope,
        resource,
        code_challenge,
    ):
        code = "vmc_code_" + secrets.token_urlsafe(36)
        now = utc_epoch_seconds()
        with self.connection() as db:
            self._cleanup(db, now)
            db.execute(
                """INSERT INTO oauth_codes(
                    hash,client_id,user_id,redirect_uri,scope,resource,code_challenge,expires_at
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    token_digest(code),
                    client_id,
                    user_id,
                    redirect_uri,
                    scope,
                    resource,
                    code_challenge,
                    now + AUTHORIZATION_CODE_SECONDS,
                ),
            )
        return code

    @staticmethod
    def _pkce_challenge(verifier):
        hashed = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(hashed).rstrip(b"=").decode()

    @staticmethod
    def _record_permission_event(
        db, *, user_id, client_id, client_name, before_scope, after_scope, source, now
    ):
        if before_scope == after_scope:
            return
        db.execute(
            """INSERT INTO oauth_permission_events(
                id,user_id,client_id,client_name,changed_at,before_scope,after_scope,source
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (
                f"{now:010d}-{time.time_ns():020d}-{secrets.token_hex(8)}",
                user_id,
                client_id,
                client_name,
                now,
                before_scope,
                after_scope,
                source,
            ),
        )

    @classmethod
    def _issue_tokens(
        cls, db, *, client_id, user_id, scope, resource, now, update_connection=True
    ):
        access_token = "vma_" + secrets.token_urlsafe(36)
        refresh_token = "vmr_" + secrets.token_urlsafe(40)
        db.execute(
            "INSERT INTO oauth_access_tokens VALUES(?,?,?,?,?,?,?)",
            (
                token_digest(access_token),
                client_id,
                user_id,
                scope,
                resource,
                now,
                now + ACCESS_TOKEN_SECONDS,
            ),
        )
        db.execute(
            "INSERT INTO oauth_refresh_tokens VALUES(?,?,?,?,?,?,?)",
            (
                token_digest(refresh_token),
                client_id,
                user_id,
                scope,
                resource,
                now,
                now + REFRESH_TOKEN_SECONDS,
            ),
        )
        if update_connection:
            existing = db.execute(
                """SELECT x.scope,c.client_name FROM oauth_connections x
                JOIN oauth_clients c ON c.client_id=x.client_id
                WHERE x.client_id=? AND x.user_id=?""",
                (client_id, user_id),
            ).fetchone()
            db.execute(
                """INSERT INTO oauth_connections(client_id,user_id,scope,created_at,last_used_at)
                VALUES(?,?,?,?,?) ON CONFLICT(client_id,user_id) DO UPDATE SET
                scope=excluded.scope,last_used_at=excluded.last_used_at""",
                (client_id, user_id, scope, now, now),
            )
            if existing:
                db.execute(
                    """UPDATE oauth_access_tokens SET scope=?
                    WHERE user_id=? AND client_id=?""",
                    (scope, user_id, client_id),
                )
                db.execute(
                    """UPDATE oauth_refresh_tokens SET scope=?
                    WHERE user_id=? AND client_id=?""",
                    (scope, user_id, client_id),
                )
                db.execute(
                    "DELETE FROM oauth_codes WHERE user_id=? AND client_id=?",
                    (user_id, client_id),
                )
                if "vault:read" not in scope.split():
                    db.execute(
                        "DELETE FROM oauth_vault_grants WHERE user_id=? AND client_id=?",
                        (user_id, client_id),
                    )
                cls._record_permission_event(
                    db,
                    user_id=user_id,
                    client_id=client_id,
                    client_name=existing["client_name"],
                    before_scope=existing["scope"],
                    after_scope=scope,
                    source="oauth-consent",
                    now=now,
                )
        else:
            db.execute(
                """UPDATE oauth_connections SET last_used_at=?
                WHERE client_id=? AND user_id=?""",
                (now, client_id, user_id),
            )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_SECONDS,
            "refresh_token": refresh_token,
            "scope": scope,
        }

    def exchange_code(
        self,
        *,
        code,
        client_id,
        redirect_uri,
        code_verifier,
        resource,
    ):
        now = utc_epoch_seconds()
        with self.connection() as db:
            self._cleanup(db, now)
            row = db.execute(
                "SELECT * FROM oauth_codes WHERE hash=?", (token_digest(code),)
            ).fetchone()
            if not row:
                raise OAuthError("invalid_grant", "Authorization code is invalid or expired")
            if (
                row["client_id"] != client_id
                or row["redirect_uri"] != redirect_uri
                or row["resource"] != resource
            ):
                raise OAuthError("invalid_grant", "Authorization code binding does not match")
            expected = self._pkce_challenge(code_verifier)
            if not hmac.compare_digest(expected, row["code_challenge"]):
                raise OAuthError("invalid_grant", "PKCE verification failed")
            db.execute("DELETE FROM oauth_codes WHERE hash=?", (token_digest(code),))
            return self._issue_tokens(
                db,
                client_id=row["client_id"],
                user_id=row["user_id"],
                scope=row["scope"],
                resource=row["resource"],
                now=now,
            )

    def refresh(self, *, refresh_token, client_id, resource, requested_scope=None):
        now = utc_epoch_seconds()
        with self.connection() as db:
            self._cleanup(db, now)
            digest = token_digest(refresh_token)
            row = db.execute(
                """SELECT r.*,x.scope AS connection_scope
                FROM oauth_refresh_tokens r
                JOIN oauth_connections x
                  ON x.client_id=r.client_id AND x.user_id=r.user_id
                WHERE r.hash=?""",
                (digest,),
            ).fetchone()
            if not row or row["client_id"] != client_id or row["resource"] != resource:
                raise OAuthError("invalid_grant", "Refresh token is invalid or expired")
            granted = set(row["connection_scope"].split())
            requested = set((requested_scope or row["connection_scope"]).split())
            if not requested.issubset(granted):
                raise OAuthError("invalid_scope", "Requested scope exceeds the current grant")
            db.execute("DELETE FROM oauth_refresh_tokens WHERE hash=?", (digest,))
            return self._issue_tokens(
                db,
                client_id=row["client_id"],
                user_id=row["user_id"],
                scope=" ".join(sorted(requested)),
                resource=row["resource"],
                now=now,
                update_connection=False,
            )

    def authenticate(self, token, resource):
        """Return the current principal and a non-enumerating credential status."""

        now = utc_epoch_seconds()
        digest = token_digest(token)
        with self.connection() as db:
            row = db.execute(
                """SELECT a.client_id,a.user_id,a.scope,a.resource,a.expires_at,
                    c.client_name,u.name,u.email
                FROM oauth_access_tokens a
                JOIN oauth_clients c ON c.client_id=a.client_id
                JOIN users u ON u.id=a.user_id
                WHERE a.hash=? AND a.resource=?""",
                (digest, resource),
            ).fetchone()
            if not row:
                failure = db.execute(
                    """SELECT reason FROM oauth_token_revocations
                    WHERE hash=? AND expires_at>?""",
                    (digest, now),
                ).fetchone()
                self._cleanup(db, now)
                return None, failure["reason"] if failure else "invalid"
            if row["expires_at"] <= now:
                self._cleanup(db, now)
                return None, "expired"
            db.execute(
                """UPDATE oauth_connections SET last_used_at=?
                WHERE client_id=? AND user_id=?""",
                (now, row["client_id"], row["user_id"]),
            )
            self._cleanup(db, now)
        result = dict(row)
        result["scopes"] = set(result.pop("scope").split())
        return result, "valid"

    def principal(self, token, resource):
        return self.authenticate(token, resource)[0]

    @staticmethod
    def _remember_revocations(db, rows, now):
        for row in rows:
            if row["expires_at"] > now:
                db.execute(
                    """INSERT INTO oauth_token_revocations(
                    hash,reason,revoked_at,expires_at
                    ) VALUES(?,?,?,?) ON CONFLICT(hash) DO UPDATE SET
                    reason=excluded.reason,revoked_at=excluded.revoked_at,
                    expires_at=excluded.expires_at""",
                    (row["hash"], "revoked", now, row["expires_at"]),
                )

    def revoke_token(self, token):
        digest = token_digest(token)
        now = utc_epoch_seconds()
        with self.connection() as db:
            rows = db.execute(
                """SELECT hash,expires_at FROM oauth_access_tokens WHERE hash=?
                UNION ALL SELECT hash,expires_at FROM oauth_refresh_tokens WHERE hash=?""",
                (digest, digest),
            ).fetchall()
            self._remember_revocations(db, rows, now)
            db.execute("DELETE FROM oauth_access_tokens WHERE hash=?", (digest,))
            db.execute("DELETE FROM oauth_refresh_tokens WHERE hash=?", (digest,))
            self._cleanup(db, now)

    def list_connections(self, user_id):
        now = utc_epoch_seconds()
        with self.connection() as db:
            self._cleanup(db, now)
            rows = db.execute(
                """SELECT x.client_id,c.client_name,x.scope,x.created_at,x.last_used_at
                FROM oauth_connections x JOIN oauth_clients c ON c.client_id=x.client_id
                WHERE x.user_id=? ORDER BY x.last_used_at DESC,x.client_id""",
                (user_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "scopes": row["scope"].split(),
            }
            for row in rows
        ]

    def set_connection_scopes(self, user_id, client_id, scopes):
        normalized = sorted(set(scopes))
        if not set(normalized).issubset(SUPPORTED_MCP_SCOPES):
            raise OAuthError("invalid_scope", "MCP connection scope is not supported")
        after_scope = " ".join(normalized)
        now = utc_epoch_seconds()
        with self.connection() as db:
            self._cleanup(db, now)
            row = db.execute(
                """SELECT x.scope,c.client_name FROM oauth_connections x
                JOIN oauth_clients c ON c.client_id=x.client_id
                WHERE x.user_id=? AND x.client_id=?""",
                (user_id, client_id),
            ).fetchone()
            if not row:
                raise OAuthError("not_found", "MCP connection not found")
            before_scope = row["scope"]
            db.execute(
                """UPDATE oauth_connections SET scope=?
                WHERE user_id=? AND client_id=?""",
                (after_scope, user_id, client_id),
            )
            db.execute(
                """UPDATE oauth_access_tokens SET scope=?
                WHERE user_id=? AND client_id=?""",
                (after_scope, user_id, client_id),
            )
            db.execute(
                """UPDATE oauth_refresh_tokens SET scope=?
                WHERE user_id=? AND client_id=?""",
                (after_scope, user_id, client_id),
            )
            # A pending code reflects an older approval decision. Discard it so a
            # completed stale browser flow cannot restore permissions just revoked.
            db.execute(
                "DELETE FROM oauth_codes WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            if "vault:read" not in normalized:
                db.execute(
                    "DELETE FROM oauth_vault_grants WHERE user_id=? AND client_id=?",
                    (user_id, client_id),
                )
            self._record_permission_event(
                db,
                user_id=user_id,
                client_id=client_id,
                client_name=row["client_name"],
                before_scope=before_scope,
                after_scope=after_scope,
                source="console",
                now=now,
            )
        return {"client_id": client_id, "scopes": normalized}

    def list_permission_events(self, user_id, client_id, limit=50):
        with self.connection() as db:
            connection = db.execute(
                """SELECT 1 FROM oauth_connections
                WHERE user_id=? AND client_id=?""",
                (user_id, client_id),
            ).fetchone()
            if not connection:
                raise OAuthError("not_found", "MCP connection not found")
            rows = db.execute(
                """SELECT id,client_id,client_name,changed_at,
                before_scope,after_scope,source
                FROM oauth_permission_events
                WHERE user_id=? AND client_id=?
                ORDER BY changed_at DESC,id DESC LIMIT ?""",
                (user_id, client_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "client_id": row["client_id"],
                "client_name": row["client_name"],
                "changed_at": row["changed_at"],
                "source": row["source"],
                "before_scopes": row["before_scope"].split(),
                "after_scopes": row["after_scope"].split(),
            }
            for row in rows
        ]

    def vault_grants(self, user_id, client_id):
        with self.connection() as db:
            connection = db.execute(
                """SELECT 1 FROM oauth_connections
                WHERE user_id=? AND client_id=?""",
                (user_id, client_id),
            ).fetchone()
            if not connection:
                raise OAuthError("not_found", "MCP connection not found")
            rows = db.execute(
                """SELECT name FROM oauth_vault_grants
                WHERE user_id=? AND client_id=? ORDER BY name""",
                (user_id, client_id),
            ).fetchall()
        return [row["name"] for row in rows]

    def replace_vault_grants(self, user_id, client_id, names):
        now = utc_epoch_seconds()
        with self.connection() as db:
            connection = db.execute(
                """SELECT scope FROM oauth_connections
                WHERE user_id=? AND client_id=?""",
                (user_id, client_id),
            ).fetchone()
            if not connection:
                raise OAuthError("not_found", "MCP connection not found")
            if "vault:read" not in set(connection["scope"].split()):
                raise OAuthError("invalid_scope", "MCP connection does not have vault:read")
            db.execute(
                "DELETE FROM oauth_vault_grants WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            for name in names:
                db.execute(
                    """INSERT INTO oauth_vault_grants(client_id,user_id,name,created_at)
                    VALUES(?,?,?,?)""",
                    (client_id, user_id, name, now),
                )
        return list(names)

    def revoke_connection(self, user_id, client_id):
        now = utc_epoch_seconds()
        with self.connection() as db:
            rows = db.execute(
                """SELECT hash,expires_at FROM oauth_access_tokens
                WHERE user_id=? AND client_id=? UNION ALL
                SELECT hash,expires_at FROM oauth_refresh_tokens
                WHERE user_id=? AND client_id=?""",
                (user_id, client_id, user_id, client_id),
            ).fetchall()
            self._remember_revocations(db, rows, now)
            db.execute(
                "DELETE FROM oauth_vault_grants WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            result = db.execute(
                "DELETE FROM oauth_connections WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            db.execute(
                "DELETE FROM oauth_access_tokens WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            db.execute(
                "DELETE FROM oauth_refresh_tokens WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            db.execute(
                "DELETE FROM oauth_codes WHERE user_id=? AND client_id=?",
                (user_id, client_id),
            )
            if not result.rowcount:
                raise OAuthError("not_found", "MCP connection not found")
