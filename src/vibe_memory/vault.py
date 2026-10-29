"""Owner-scoped encrypted secrets with no plaintext listing or storage."""

import hashlib
import os
import secrets
import sqlite3
import stat
import threading
from contextlib import contextmanager
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from .clock import utc_epoch_seconds
from .postgres import PostgresDatabase


class VaultNotFound(Exception):
    pass


class VaultIntegrityError(Exception):
    pass


class VaultCaptureNotFound(Exception):
    pass


class VaultCaptureExpired(Exception):
    pass


class VaultCaptureConsumed(Exception):
    pass


def _capture_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _associated_data(user_id: str, name: str) -> bytes:
    return b"vibe-memory-vault-v1\0" + user_id.encode() + b"\0" + name.encode()


def _load_or_create_key(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        descriptor = None
    if descriptor is not None:
        key = AESGCM.generate_key(bit_length=256)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(key)
            destination.flush()
            os.fsync(destination.fileno())
    details = path.lstat()
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise RuntimeError("Vault key must be a regular file")
    path.chmod(0o600)
    key = path.read_bytes()
    if len(key) != 32:
        raise RuntimeError("Vault key must contain exactly 32 bytes")
    return key


class VaultStore:
    def __init__(self, path: Path, key_path: Path):
        self.postgres = path if isinstance(path, PostgresDatabase) else None
        if self.postgres:
            self.path, self.lock = None, threading.RLock()
            self.cipher = AESGCM(_load_or_create_key(key_path))
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        self.cipher = AESGCM(_load_or_create_key(key_path))
        with self.connection() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS vault_secrets (
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_accessed_at INTEGER,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(user_id, name)
                );
                CREATE TABLE IF NOT EXISTS vault_captures (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    requester_agent_id TEXT NOT NULL,
                    requester_agent_name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    consumed_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS vault_captures_owner_idx
                    ON vault_captures(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS vault_access_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    accessed_at INTEGER NOT NULL,
                    outcome TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS vault_access_audit_owner_idx
                    ON vault_access_audit(user_id, accessed_at DESC, id DESC);
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
            try:
                with db:
                    yield db
            finally:
                db.close()

    @staticmethod
    def _metadata(row):
        return {
            key: row[key]
            for key in (
                "name",
                "description",
                "created_at",
                "updated_at",
                "last_accessed_at",
                "access_count",
            )
        }

    def list(self, user_id: str):
        with self.connection() as db:
            rows = db.execute(
                """SELECT name,description,created_at,updated_at,last_accessed_at,access_count
                FROM vault_secrets WHERE user_id=? ORDER BY name""",
                (user_id,),
            ).fetchall()
        return [self._metadata(row) for row in rows]

    def set(self, user_id: str, name: str, value: str, description: str):
        now = utc_epoch_seconds()
        nonce = os.urandom(12)
        ciphertext = self.cipher.encrypt(
            nonce, value.encode(), _associated_data(user_id, name)
        )
        with self.connection() as db:
            if (
                db.execute(
                    "SELECT count(*) FROM vault_secrets WHERE user_id=?", (user_id,)
                ).fetchone()[0]
                >= 100
                and not db.execute(
                    "SELECT 1 FROM vault_secrets WHERE user_id=? AND name=?", (user_id, name)
                ).fetchone()
            ):
                raise HTTPException(422, "Vault entries are limited to 100 per account")
            db.execute(
                """INSERT INTO vault_secrets(
                    user_id,name,description,nonce,ciphertext,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(user_id,name) DO UPDATE SET
                    description=excluded.description,
                    nonce=excluded.nonce,
                    ciphertext=excluded.ciphertext,
                    updated_at=excluded.updated_at""",
                (user_id, name, description, nonce, ciphertext, now, now),
            )
            row = db.execute(
                """SELECT name,description,created_at,updated_at,last_accessed_at,access_count
                FROM vault_secrets WHERE user_id=? AND name=?""",
                (user_id, name),
            ).fetchone()
        return self._metadata(row)

    def get(self, user_id: str, name: str):
        with self.connection() as db:
            row = db.execute(
                "SELECT nonce,ciphertext FROM vault_secrets WHERE user_id=? AND name=?",
                (user_id, name),
            ).fetchone()
            if not row:
                raise VaultNotFound()
            try:
                value = self.cipher.decrypt(
                    row["nonce"], row["ciphertext"], _associated_data(user_id, name)
                ).decode()
            except (InvalidTag, UnicodeDecodeError):
                raise VaultIntegrityError() from None
            db.execute(
                """UPDATE vault_secrets SET last_accessed_at=?,access_count=access_count+1
                WHERE user_id=? AND name=?""",
                (utc_epoch_seconds(), user_id, name),
            )
        return {"name": name, "value": value}

    def audit_access(self, user_id: str, client_id: str, name: str, outcome: str):
        with self.connection() as db:
            db.execute(
                """INSERT INTO vault_access_audit(
                    user_id,client_id,name,accessed_at,outcome
                ) VALUES(?,?,?,?,?)""",
                (user_id, client_id, name, utc_epoch_seconds(), outcome),
            )

    def access_audit(self, user_id: str, limit: int = 100):
        with self.connection() as db:
            rows = db.execute(
                """SELECT client_id,name,accessed_at,outcome
                FROM vault_access_audit WHERE user_id=?
                ORDER BY accessed_at DESC,id DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, user_id: str, name: str):
        with self.connection() as db:
            result = db.execute(
                "DELETE FROM vault_secrets WHERE user_id=? AND name=?", (user_id, name)
            )
            if not result.rowcount:
                raise VaultNotFound()

    @staticmethod
    def _capture_metadata(row):
        return {
            key: row[key]
            for key in (
                "id",
                "name",
                "description",
                "requester_agent_id",
                "requester_agent_name",
                "created_at",
                "expires_at",
                "consumed_at",
            )
        }

    def create_capture(
        self,
        user_id: str,
        name: str,
        description: str,
        requester_agent_id: str,
        requester_agent_name: str,
        expires_in: int,
    ):
        now = utc_epoch_seconds()
        token = secrets.token_urlsafe(32)
        capture_id = secrets.token_hex(16)
        with self.connection() as db:
            db.execute(
                "DELETE FROM vault_captures WHERE expires_at < ? AND created_at < ?",
                (now - 86400, now - 86400),
            )
            active = db.execute(
                """SELECT count(*) FROM vault_captures
                WHERE user_id=? AND consumed_at IS NULL AND expires_at>?""",
                (user_id, now),
            ).fetchone()[0]
            if active >= 20:
                raise HTTPException(422, "Active Vault capture links are limited to 20")
            db.execute(
                """INSERT INTO vault_captures(
                    id,user_id,token_hash,name,description,requester_agent_id,
                    requester_agent_name,created_at,expires_at,consumed_at
                ) VALUES(?,?,?,?,?,?,?,?,?,NULL)""",
                (
                    capture_id,
                    user_id,
                    _capture_digest(token),
                    name,
                    description,
                    requester_agent_id,
                    requester_agent_name,
                    now,
                    now + expires_in,
                ),
            )
            row = db.execute(
                """SELECT id,name,description,requester_agent_id,requester_agent_name,
                created_at,expires_at,consumed_at FROM vault_captures WHERE id=?""",
                (capture_id,),
            ).fetchone()
        return token, self._capture_metadata(row)

    def inspect_capture(self, user_id: str, token: str):
        now = utc_epoch_seconds()
        with self.connection() as db:
            row = db.execute(
                """SELECT id,name,description,requester_agent_id,requester_agent_name,
                created_at,expires_at,consumed_at FROM vault_captures
                WHERE user_id=? AND token_hash=?""",
                (user_id, _capture_digest(token)),
            ).fetchone()
        if not row:
            raise VaultCaptureNotFound()
        if row["consumed_at"] is not None:
            raise VaultCaptureConsumed()
        if row["expires_at"] <= now:
            raise VaultCaptureExpired()
        return self._capture_metadata(row)

    def submit_capture(self, user_id: str, token: str, value: str):
        now = utc_epoch_seconds()
        token_hash = _capture_digest(token)
        with self.connection() as db:
            row = db.execute(
                """SELECT id,name,description,requester_agent_id,requester_agent_name,
                created_at,expires_at,consumed_at FROM vault_captures
                WHERE user_id=? AND token_hash=?""",
                (user_id, token_hash),
            ).fetchone()
            if not row:
                raise VaultCaptureNotFound()
            if row["consumed_at"] is not None:
                raise VaultCaptureConsumed()
            if row["expires_at"] <= now:
                raise VaultCaptureExpired()
            reserved = db.execute(
                """UPDATE vault_captures SET consumed_at=?
                WHERE user_id=? AND token_hash=? AND consumed_at IS NULL AND expires_at>?""",
                (now, user_id, token_hash, now),
            )
            if not reserved.rowcount:
                raise VaultCaptureConsumed()
        try:
            saved = self.set(user_id, row["name"], value, row["description"])
        except Exception:
            with self.connection() as db:
                db.execute(
                    """UPDATE vault_captures SET consumed_at=NULL
                    WHERE user_id=? AND token_hash=? AND consumed_at=?""",
                    (user_id, token_hash, now),
                )
            raise
        return {
            "name": saved["name"],
            "captured_at": now,
            "requester_agent_name": row["requester_agent_name"],
        }
