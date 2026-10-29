"""Owner-scoped encrypted secrets with no plaintext listing or storage."""

import os
import sqlite3
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException


class VaultNotFound(Exception):
    pass


class VaultIntegrityError(Exception):
    pass


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
                """
            )
        path.chmod(0o600)

    @contextmanager
    def connection(self):
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
                FROM vault_secrets WHERE user_id=? ORDER BY name COLLATE NOCASE""",
                (user_id,),
            ).fetchall()
        return [self._metadata(row) for row in rows]

    def set(self, user_id: str, name: str, value: str, description: str):
        now = int(time.time())
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
                (int(time.time()), user_id, name),
            )
        return {"name": name, "value": value}

    def delete(self, user_id: str, name: str):
        with self.connection() as db:
            result = db.execute(
                "DELETE FROM vault_secrets WHERE user_id=? AND name=?", (user_id, name)
            )
            if not result.rowcount:
                raise VaultNotFound()
