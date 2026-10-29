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
from contextlib import contextmanager

from .clock import utc_epoch_seconds
from .postgres import PostgresDatabase

ACCESS_TOKEN_SECONDS = 3600
REFRESH_TOKEN_SECONDS = 30 * 24 * 3600
AUTHORIZATION_CODE_SECONDS = 300


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
                CREATE TABLE IF NOT EXISTS oauth_connections (
                    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    scope TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_used_at INTEGER NOT NULL,
                    PRIMARY KEY(client_id, user_id)
                );
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
        db.execute("DELETE FROM oauth_access_tokens WHERE expires_at <= ?", (now,))
        db.execute("DELETE FROM oauth_refresh_tokens WHERE expires_at <= ?", (now,))
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
    def _issue_tokens(db, *, client_id, user_id, scope, resource, now):
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
        db.execute(
            """INSERT INTO oauth_connections(client_id,user_id,scope,created_at,last_used_at)
            VALUES(?,?,?,?,?) ON CONFLICT(client_id,user_id) DO UPDATE SET
            scope=excluded.scope,last_used_at=excluded.last_used_at""",
            (client_id, user_id, scope, now, now),
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
                "SELECT * FROM oauth_refresh_tokens WHERE hash=?", (digest,)
            ).fetchone()
            if not row or row["client_id"] != client_id or row["resource"] != resource:
                raise OAuthError("invalid_grant", "Refresh token is invalid or expired")
            granted = set(row["scope"].split())
            requested = set((requested_scope or row["scope"]).split())
            if not requested or not requested.issubset(granted):
                raise OAuthError("invalid_scope", "Requested scope exceeds the original grant")
            db.execute("DELETE FROM oauth_refresh_tokens WHERE hash=?", (digest,))
            return self._issue_tokens(
                db,
                client_id=row["client_id"],
                user_id=row["user_id"],
                scope=" ".join(sorted(requested)),
                resource=row["resource"],
                now=now,
            )

    def principal(self, token, resource):
        now = utc_epoch_seconds()
        with self.connection() as db:
            self._cleanup(db, now)
            row = db.execute(
                """SELECT a.client_id,a.user_id,a.scope,a.resource,a.expires_at,
                    c.client_name,u.name,u.email
                FROM oauth_access_tokens a
                JOIN oauth_clients c ON c.client_id=a.client_id
                JOIN users u ON u.id=a.user_id
                WHERE a.hash=? AND a.expires_at>? AND a.resource=?""",
                (token_digest(token), now, resource),
            ).fetchone()
            if not row:
                return None
            db.execute(
                """UPDATE oauth_connections SET last_used_at=?
                WHERE client_id=? AND user_id=?""",
                (now, row["client_id"], row["user_id"]),
            )
        result = dict(row)
        result["scopes"] = set(result.pop("scope").split())
        return result

    def revoke_token(self, token):
        digest = token_digest(token)
        with self.connection() as db:
            db.execute("DELETE FROM oauth_access_tokens WHERE hash=?", (digest,))
            db.execute("DELETE FROM oauth_refresh_tokens WHERE hash=?", (digest,))
            self._cleanup(db, utc_epoch_seconds())

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

    def revoke_connection(self, user_id, client_id):
        with self.connection() as db:
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
