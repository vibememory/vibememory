"""Persistent browser sessions and revocable agent keys; no credentials in browser storage."""

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

COOKIE = "vm_session"
SESSION_SECONDS = 7 * 24 * 3600


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_address(cls, value):
        value = value.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("올바른 이메일 주소를 입력해주세요.")
        return value


class Signup(Credentials):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def name_value(cls, value):
        if not value.strip():
            raise ValueError("이름을 입력해주세요.")
        return value.strip()


class KeyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


class AuthStore:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.lock = path, threading.RLock()
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                    salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    hash TEXT UNIQUE NOT NULL, name TEXT NOT NULL, prefix TEXT NOT NULL,
                    created_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS device_logins (
                    device_hash TEXT PRIMARY KEY, user_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL, expires_at INTEGER NOT NULL, state TEXT NOT NULL,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE, polled_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    key TEXT PRIMARY KEY, count INTEGER NOT NULL, resets_at INTEGER NOT NULL);
            """)
        path.chmod(0o600)
        self.dummy_salt = secrets.token_hex(16)
        self.dummy_hash = password_hash("not-a-real-password", self.dummy_salt)

    @contextmanager
    def connection(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=10)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            try:
                with db:
                    yield db
            finally:
                db.close()

    def throttle(self, identifier, limit=12):
        now = int(time.time())
        with self.connection() as db:
            key = digest(identifier)
            db.execute("DELETE FROM auth_attempts WHERE resets_at <= ?", (now,))
            row = db.execute("SELECT count FROM auth_attempts WHERE key=?", (key,)).fetchone()
            if row and row["count"] >= limit:
                raise HTTPException(429, "시도가 너무 많습니다. 15분 뒤 다시 시도해주세요.")
            db.execute(
                """INSERT INTO auth_attempts(key,count,resets_at) VALUES(?,1,?)
                ON CONFLICT(key) DO UPDATE SET count=count+1""",
                (key, now + 900),
            )

    def signup(self, data):
        salt = secrets.token_hex(16)
        user = dict(id=str(uuid4()), email=data.email, name=data.name, created_at=int(time.time()))
        hashed = password_hash(data.password, salt)
        try:
            with self.connection() as db:
                db.execute(
                    "INSERT INTO users VALUES(?,?,?,?,?,?)",
                    (user["id"], user["email"], user["name"], salt, hashed, user["created_at"]),
                )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "이미 등록된 이메일입니다. 로그인해주세요.") from None
        return user

    def login(self, data):
        self.throttle("login:" + data.email)
        with self.connection() as db:
            row = db.execute("SELECT * FROM users WHERE email=?", (data.email,)).fetchone()
        actual = password_hash(data.password, row["salt"] if row else self.dummy_salt)
        if (
            not hmac.compare_digest(actual, row["password_hash"] if row else self.dummy_hash)
            or not row
        ):
            raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
        with self.connection() as db:
            db.execute("DELETE FROM auth_attempts WHERE key=?", (digest("login:" + data.email),))
        return {k: row[k] for k in ("id", "email", "name", "created_at")}

    def session(self, user_id):
        token = secrets.token_urlsafe(36)
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?)",
                (digest(token), user_id, int(time.time()) + SESSION_SECONDS),
            )
        return token

    def user_for_session(self, token):
        if not token:
            return None
        with self.connection() as db:
            row = db.execute(
                """SELECT u.id,u.email,u.name,u.created_at FROM users u
                JOIN sessions s ON u.id=s.user_id WHERE s.hash=? AND s.expires_at>?""",
                (digest(token), int(time.time())),
            ).fetchone()
        return dict(row) if row else None

    def logout(self, token):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE hash=?", (digest(token or ""),))

    def user_for_key(self, token):
        with self.connection() as db:
            row = db.execute(
                "SELECT user_id FROM api_keys WHERE hash=?", (digest(token),)
            ).fetchone()
        return row["user_id"] if row else None

    def list_keys(self, user_id):
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    """SELECT id,name,prefix,created_at FROM api_keys
                WHERE user_id=? ORDER BY created_at DESC,id""",
                    (user_id,),
                )
            ]

    def create_key(self, user_id, name):
        token = "vm_" + secrets.token_urlsafe(36)
        record = dict(
            id=str(uuid4()), name=name, prefix=token[:10] + "…", created_at=int(time.time())
        )
        with self.connection() as db:
            if (
                db.execute("SELECT count(*) FROM api_keys WHERE user_id=?", (user_id,)).fetchone()[
                    0
                ]
                >= 30
            ):
                raise HTTPException(
                    422, "키는 최대 30개까지 만들 수 있습니다. 사용하지 않는 키를 삭제해주세요."
                )
            db.execute(
                "INSERT INTO api_keys VALUES(?,?,?,?,?,?)",
                (
                    record["id"],
                    user_id,
                    digest(token),
                    name,
                    record["prefix"],
                    record["created_at"],
                ),
            )
        return {**record, "key": token}

    def start_device(self, name):
        device = secrets.token_urlsafe(36)
        code = secrets.token_hex(5).upper()
        expires = int(time.time()) + 300
        with self.connection() as db:
            db.execute("DELETE FROM device_logins WHERE expires_at <= ?", (int(time.time()),))
            db.execute("INSERT INTO device_logins VALUES(?,?,?,?,?,?,?)",
                       (digest(device), digest(code), name, expires, "pending", None, 0))
        return {"device_code": device, "user_code": code, "expires_in": 300, "interval": 3}

    def device_info(self, code):
        with self.connection() as db:
            row = db.execute(
                "SELECT name,expires_at,state FROM device_logins WHERE user_hash=?",
                (digest(code.upper()),),
            ).fetchone()
        if not row or row["expires_at"] <= int(time.time()):
            raise HTTPException(410, "연결 요청이 만료되었거나 존재하지 않습니다.")
        return dict(row)

    def approve_device(self, user_id, code, approved):
        with self.connection() as db:
            result = db.execute(
                """UPDATE device_logins SET state=?,user_id=? WHERE user_hash=?
                AND state='pending' AND expires_at>?""",
                ("approved" if approved else "denied", user_id, digest(code.upper()), int(time.time())),
            )
            if not result.rowcount:
                raise HTTPException(410, "이미 처리되었거나 만료된 연결 요청입니다.")
        return {"state": "approved" if approved else "denied"}

    def poll_device(self, device):
        now = int(time.time())
        with self.connection() as db:
            row = db.execute("SELECT * FROM device_logins WHERE device_hash=?",
                             (digest(device),)).fetchone()
            if not row or row["expires_at"] <= now or row["state"] == "used":
                raise HTTPException(410, "Connection request expired or already consumed")
            if row["state"] == "denied":
                raise HTTPException(403, "Connection request denied")
            if now - row["polled_at"] < 2:
                raise HTTPException(429, "Poll no more than once every 3 seconds")
            db.execute("UPDATE device_logins SET polled_at=? WHERE device_hash=?", (now, digest(device)))
            if row["state"] == "pending":
                return {"state": "pending"}
            if db.execute("SELECT count(*) FROM api_keys WHERE user_id=?", (row["user_id"],)).fetchone()[0] >= 30:
                raise HTTPException(422, "Too many agent keys; revoke an unused key in the console")
            token = "vm_" + secrets.token_urlsafe(36)
            key_id = str(uuid4())
            db.execute("INSERT INTO api_keys VALUES(?,?,?,?,?,?)",
                       (key_id, row["user_id"], digest(token), row["name"], token[:10] + "…", now))
            db.execute("UPDATE device_logins SET state='used' WHERE device_hash=?", (digest(device),))
        return {"state": "connected", "key": token, "key_id": key_id}

    def revoke_key(self, user_id, id):
        with self.connection() as db:
            result = db.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (id, user_id))
            if not result.rowcount:
                raise HTTPException(404, "키를 찾을 수 없습니다.")
