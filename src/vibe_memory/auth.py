"""Persistent browser sessions, TOTP protection, and revocable agent keys."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import struct
import threading
from contextlib import contextmanager
from typing import Literal
from urllib.parse import quote
from uuid import uuid4

import segno
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .clock import utc_epoch_seconds
from .postgres import IntegrityError, PostgresDatabase

COOKIE = "vm_session"
SESSION_SECONDS = 7 * 24 * 3600
TOTP_PERIOD = 30
TOTP_SETUP_SECONDS = 10 * 60
LOGIN_CHALLENGE_SECONDS = 5 * 60
RECOVERY_CODE_COUNT = 10

AgentPermission = Literal[
    "memory:read",
    "memory:write",
    "files:read",
    "files:write",
    "messages:read",
    "messages:write",
    "feature:write",
    "events:read",
]
DEFAULT_AGENT_PERMISSIONS: tuple[AgentPermission, ...] = (
    "memory:read",
    "memory:write",
    "files:read",
    "files:write",
    "messages:read",
    "messages:write",
    "feature:write",
    "events:read",
)
DEFAULT_AGENT_PERMISSIONS_JSON = json.dumps(
    DEFAULT_AGENT_PERMISSIONS, ensure_ascii=True, separators=(",", ":")
)


def normalize_agent_permissions(values) -> list[AgentPermission]:
    requested = set(values or [])
    return [permission for permission in DEFAULT_AGENT_PERMISSIONS if permission in requested]


def stored_agent_permissions(value) -> list[AgentPermission]:
    try:
        parsed = json.loads(value or DEFAULT_AGENT_PERMISSIONS_JSON)
    except (TypeError, ValueError):
        parsed = DEFAULT_AGENT_PERMISSIONS
    return normalize_agent_permissions(parsed)


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
    vault_access: bool = False
    permissions: list[AgentPermission] = Field(
        default_factory=lambda: list(DEFAULT_AGENT_PERMISSIONS), max_length=8
    )

    @field_validator("permissions")
    @classmethod
    def unique_permissions(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("permissions must be unique")
        return normalize_agent_permissions(value)


class DeviceStartInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    vault_access: bool = False
    expires_in: int = Field(default=300, ge=60, le=900)
    upgrade: bool = False


class KeyAccessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vault_access: bool | None = None
    permissions: list[AgentPermission] | None = Field(default=None, max_length=8)

    @field_validator("permissions")
    @classmethod
    def unique_updated_permissions(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("permissions must be unique")
        return None if value is None else normalize_agent_permissions(value)

    @model_validator(mode="after")
    def at_least_one_change(self):
        if self.vault_access is None and self.permissions is None:
            raise ValueError("vault_access or permissions is required")
        return self


class FeatureRequestOperatorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_request_operator: bool


class NamespaceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)


class NamespaceGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    namespace_id: str = Field(min_length=1, max_length=100)
    can_read: bool = True
    can_write: bool = False


class PasswordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=10, max_length=128)


class SecondFactorInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=6, max_length=32)


class LoginSecondFactor(SecondFactorInput):
    challenge_token: str = Field(min_length=40, max_length=100)


class ProtectedSecondFactor(PasswordInput, SecondFactorInput):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def _decode_totp_secret(secret):
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(secret + padding, casefold=True)


def totp_code(secret, timestamp=None):
    """Return the RFC 6238 six-digit code for tests and internal verification."""
    timestamp = utc_epoch_seconds() if timestamp is None else int(timestamp)
    counter = timestamp // TOTP_PERIOD
    digest_bytes = hmac.new(
        _decode_totp_secret(secret), struct.pack(">Q", counter), hashlib.sha1
    ).digest()
    offset = digest_bytes[-1] & 0x0F
    number = struct.unpack(">I", digest_bytes[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def _matching_totp_counter(secret, code, timestamp=None):
    timestamp = utc_epoch_seconds() if timestamp is None else int(timestamp)
    current = timestamp // TOTP_PERIOD
    for counter in (current, current - 1, current + 1):
        if hmac.compare_digest(totp_code(secret, counter * TOTP_PERIOD), code):
            return counter
    return None


def _recovery_digest(user_id, code):
    normalized = re.sub(r"[^A-Z2-9]", "", code.upper())
    return digest(user_id + "\0" + normalized)


def _recovery_codes():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return [
        "-".join(
            "".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)
        )
        for _ in range(RECOVERY_CODE_COUNT)
    ]


class AuthStore:
    def __init__(self, path, otp_cipher: AESGCM):
        self.otp_cipher = otp_cipher
        self.postgres = path if isinstance(path, PostgresDatabase) else None
        if self.postgres:
            self.path, self.lock = None, threading.RLock()
            self.dummy_salt = secrets.token_hex(16)
            self.dummy_hash = password_hash("not-a-real-password", self.dummy_salt)
            return
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
                    created_at INTEGER NOT NULL, vault_access INTEGER NOT NULL DEFAULT 0,
                    feature_request_operator INTEGER NOT NULL DEFAULT 0,
                    permissions TEXT NOT NULL DEFAULT '["memory:read","memory:write","files:read","files:write","messages:read","messages:write","feature:write","events:read"]');
                CREATE TABLE IF NOT EXISTS api_key_permission_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    api_key_id TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    key_prefix TEXT NOT NULL,
                    changed_at INTEGER NOT NULL,
                    before_permissions TEXT NOT NULL,
                    after_permissions TEXT NOT NULL,
                    before_vault_access INTEGER NOT NULL,
                    after_vault_access INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS api_key_permission_events_owner_idx
                    ON api_key_permission_events(user_id, changed_at DESC, id DESC);
                CREATE TABLE IF NOT EXISTS namespaces (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(user_id, name));
                CREATE TABLE IF NOT EXISTS api_key_namespace_grants (
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    api_key_id TEXT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
                    namespace_id TEXT NOT NULL,
                    can_read INTEGER NOT NULL DEFAULT 1,
                    can_write INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(user_id, api_key_id, namespace_id));
                CREATE TABLE IF NOT EXISTS device_logins (
                    device_hash TEXT PRIMARY KEY, user_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL, expires_at INTEGER NOT NULL, state TEXT NOT NULL,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE, polled_at INTEGER NOT NULL,
                    vault_access INTEGER NOT NULL DEFAULT 0,
                    upgrade_key_id TEXT, upgrade_user_id TEXT);
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    key TEXT PRIMARY KEY, count INTEGER NOT NULL, resets_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS user_totp (
                    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
                    enabled_at INTEGER NOT NULL, last_counter INTEGER NOT NULL DEFAULT -1);
                CREATE TABLE IF NOT EXISTS totp_setups (
                    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    nonce BLOB NOT NULL, ciphertext BLOB NOT NULL, expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS recovery_codes (
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    hash TEXT NOT NULL, created_at INTEGER NOT NULL,
                    PRIMARY KEY(user_id, hash));
                CREATE TABLE IF NOT EXISTS login_challenges (
                    hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0);
            """)
            api_columns = {row[1] for row in db.execute("PRAGMA table_info(api_keys)")}
            if "vault_access" not in api_columns:
                db.execute(
                    "ALTER TABLE api_keys ADD COLUMN vault_access INTEGER NOT NULL DEFAULT 0"
                )
            if "feature_request_operator" not in api_columns:
                db.execute(
                    "ALTER TABLE api_keys ADD COLUMN feature_request_operator "
                    "INTEGER NOT NULL DEFAULT 0"
                )
            if "permissions" not in api_columns:
                db.execute(
                    "ALTER TABLE api_keys ADD COLUMN permissions TEXT NOT NULL DEFAULT "
                    f"'{DEFAULT_AGENT_PERMISSIONS_JSON}'"
                )
            device_columns = {row[1] for row in db.execute("PRAGMA table_info(device_logins)")}
            if "vault_access" not in device_columns:
                db.execute(
                    "ALTER TABLE device_logins ADD COLUMN vault_access INTEGER NOT NULL DEFAULT 0"
                )
            if "upgrade_key_id" not in device_columns:
                db.execute("ALTER TABLE device_logins ADD COLUMN upgrade_key_id TEXT")
            if "upgrade_user_id" not in device_columns:
                db.execute("ALTER TABLE device_logins ADD COLUMN upgrade_user_id TEXT")
        path.chmod(0o600)
        self.dummy_salt = secrets.token_hex(16)
        self.dummy_hash = password_hash("not-a-real-password", self.dummy_salt)

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

    def throttle(self, identifier, limit=12):
        now = utc_epoch_seconds()
        with self.connection() as db:
            key = digest(identifier)
            db.execute("DELETE FROM auth_attempts WHERE resets_at <= ?", (now,))
            row = db.execute("SELECT count FROM auth_attempts WHERE key=?", (key,)).fetchone()
            if row and row["count"] >= limit:
                raise HTTPException(429, "시도가 너무 많습니다. 15분 뒤 다시 시도해주세요.")
            db.execute(
                """INSERT INTO auth_attempts(key,count,resets_at) VALUES(?,1,?)
                ON CONFLICT(key) DO UPDATE SET count=auth_attempts.count+1""",
                (key, now + 900),
            )

    def clear_throttle(self, identifier):
        with self.connection() as db:
            db.execute("DELETE FROM auth_attempts WHERE key=?", (digest(identifier),))

    def signup(self, data):
        salt = secrets.token_hex(16)
        user = dict(
            id=str(uuid4()), email=data.email, name=data.name, created_at=utc_epoch_seconds()
        )
        hashed = password_hash(data.password, salt)
        try:
            with self.connection() as db:
                db.execute(
                    "INSERT INTO users VALUES(?,?,?,?,?,?)",
                    (user["id"], user["email"], user["name"], salt, hashed, user["created_at"]),
                )
        except (sqlite3.IntegrityError, IntegrityError):
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

    def verify_password(self, user_id, password):
        throttle_key = "security-password:" + user_id
        self.throttle(throttle_key, 8)
        with self.connection() as db:
            row = db.execute(
                "SELECT salt,password_hash FROM users WHERE id=?", (user_id,)
            ).fetchone()
        actual = password_hash(password, row["salt"] if row else self.dummy_salt)
        if not row or not hmac.compare_digest(actual, row["password_hash"]):
            raise HTTPException(401, "현재 비밀번호가 올바르지 않습니다.")
        self.clear_throttle(throttle_key)

    @staticmethod
    def _totp_associated_data(user_id):
        return b"vibe-memory-totp-v1\0" + user_id.encode()

    def _encrypt_totp_secret(self, user_id, secret):
        nonce = os.urandom(12)
        ciphertext = self.otp_cipher.encrypt(
            nonce, secret.encode(), self._totp_associated_data(user_id)
        )
        return nonce, ciphertext

    def _decrypt_totp_secret(self, user_id, nonce, ciphertext):
        try:
            return self.otp_cipher.decrypt(
                nonce, ciphertext, self._totp_associated_data(user_id)
            ).decode()
        except (InvalidTag, UnicodeDecodeError):
            raise HTTPException(500, "OTP 보안 정보를 확인할 수 없습니다.") from None

    def totp_enabled(self, user_id):
        with self.connection() as db:
            return bool(
                db.execute("SELECT 1 FROM user_totp WHERE user_id=?", (user_id,)).fetchone()
            )

    def security(self, user_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT enabled_at FROM user_totp WHERE user_id=?", (user_id,)
            ).fetchone()
            remaining = db.execute(
                "SELECT count(*) FROM recovery_codes WHERE user_id=?", (user_id,)
            ).fetchone()[0]
        return {
            "totp_enabled": bool(row),
            "totp_enabled_at": row["enabled_at"] if row else None,
            "recovery_codes_remaining": remaining,
        }

    def start_totp_setup(self, user_id, email, password):
        self.verify_password(user_id, password)
        if self.totp_enabled(user_id):
            raise HTTPException(409, "OTP가 이미 활성화되어 있습니다.")
        secret = base64.b32encode(os.urandom(20)).decode().rstrip("=")
        nonce, ciphertext = self._encrypt_totp_secret(user_id, secret)
        expires_at = utc_epoch_seconds() + TOTP_SETUP_SECONDS
        with self.connection() as db:
            db.execute(
                """INSERT INTO totp_setups(user_id,nonce,ciphertext,expires_at)
                VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                nonce=excluded.nonce,ciphertext=excluded.ciphertext,
                expires_at=excluded.expires_at""",
                (user_id, nonce, ciphertext, expires_at),
            )
        issuer = "Vibe Memory"
        label = quote(f"{issuer}:{email}", safe="")
        uri = (
            f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer, safe='')}"
            "&algorithm=SHA1&digits=6&period=30"
        )
        qr_svg_data_uri = segno.make(uri, error="m", micro=False).svg_data_uri(
            scale=5, border=2, dark="#1d293d", light="#ffffff"
        )
        return {
            "secret": secret,
            "otpauth_uri": uri,
            "qr_svg_data_uri": qr_svg_data_uri,
            "expires_at": expires_at,
        }

    def _replace_recovery_codes(self, db, user_id):
        codes = _recovery_codes()
        now = utc_epoch_seconds()
        db.execute("DELETE FROM recovery_codes WHERE user_id=?", (user_id,))
        for code in codes:
            db.execute(
                "INSERT INTO recovery_codes(user_id,hash,created_at) VALUES(?,?,?)",
                (user_id, _recovery_digest(user_id, code), now),
            )
        return codes

    def enable_totp(self, user_id, code, current_session):
        now = utc_epoch_seconds()
        throttle_key = "totp-enable:" + user_id
        self.throttle(throttle_key, 8)
        with self.connection() as db:
            row = db.execute(
                "SELECT nonce,ciphertext,expires_at FROM totp_setups WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if not row or row["expires_at"] <= now:
                db.execute("DELETE FROM totp_setups WHERE user_id=?", (user_id,))
                raise HTTPException(410, "OTP 설정이 만료되었습니다. 다시 시작해주세요.")
            secret = self._decrypt_totp_secret(
                user_id, row["nonce"], row["ciphertext"]
            )
            if not re.fullmatch(r"\d{6}", code) or _matching_totp_counter(secret, code) is None:
                raise HTTPException(401, "인증 앱의 6자리 코드가 올바르지 않습니다.")
            db.execute(
                """INSERT INTO user_totp(
                    user_id,nonce,ciphertext,enabled_at,last_counter
                ) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                    nonce=excluded.nonce,ciphertext=excluded.ciphertext,
                    enabled_at=excluded.enabled_at,last_counter=-1""",
                (user_id, row["nonce"], row["ciphertext"], now, -1),
            )
            db.execute("DELETE FROM totp_setups WHERE user_id=?", (user_id,))
            codes = self._replace_recovery_codes(db, user_id)
            db.execute(
                "DELETE FROM sessions WHERE user_id=? AND hash<>?",
                (user_id, digest(current_session or "")),
            )
            db.execute("DELETE FROM login_challenges WHERE user_id=?", (user_id,))
        self.clear_throttle(throttle_key)
        return {"recovery_codes": codes}

    def _verify_second_factor(self, user_id, code):
        with self.connection() as db:
            row = db.execute(
                "SELECT nonce,ciphertext,last_counter FROM user_totp WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if not row:
                raise HTTPException(409, "OTP가 활성화되어 있지 않습니다.")
            normalized = code.strip().upper()
            if re.fullmatch(r"\d{6}", normalized):
                secret = self._decrypt_totp_secret(
                    user_id, row["nonce"], row["ciphertext"]
                )
                counter = _matching_totp_counter(secret, normalized)
                if counter is None or counter <= row["last_counter"]:
                    raise HTTPException(401, "OTP 코드가 올바르지 않거나 이미 사용되었습니다.")
                updated = db.execute(
                    """UPDATE user_totp SET last_counter=?
                    WHERE user_id=? AND last_counter<?""",
                    (counter, user_id, counter),
                )
                if not updated.rowcount:
                    raise HTTPException(401, "OTP 코드가 이미 사용되었습니다.")
                return "totp"
            code_hash = _recovery_digest(user_id, normalized)
            consumed = db.execute(
                "DELETE FROM recovery_codes WHERE user_id=? AND hash=?",
                (user_id, code_hash),
            )
            if not consumed.rowcount:
                raise HTTPException(401, "OTP 또는 복구 코드가 올바르지 않습니다.")
            return "recovery"

    def begin_login_challenge(self, user_id):
        token = secrets.token_urlsafe(36)
        now = utc_epoch_seconds()
        with self.connection() as db:
            db.execute("DELETE FROM login_challenges WHERE expires_at<=?", (now,))
            db.execute(
                "INSERT INTO login_challenges(hash,user_id,expires_at,attempts) VALUES(?,?,?,0)",
                (digest(token), user_id, now + LOGIN_CHALLENGE_SECONDS),
            )
        return token

    def complete_login_challenge(self, token, code):
        token_hash = digest(token)
        now = utc_epoch_seconds()
        with self.connection() as db:
            row = db.execute(
                "SELECT user_id,expires_at,attempts FROM login_challenges WHERE hash=?",
                (token_hash,),
            ).fetchone()
        if not row or row["expires_at"] <= now or row["attempts"] >= 5:
            with self.connection() as db:
                db.execute("DELETE FROM login_challenges WHERE hash=?", (token_hash,))
            raise HTTPException(401, "로그인 인증이 만료되었습니다. 다시 로그인해주세요.")
        try:
            self._verify_second_factor(row["user_id"], code)
        except HTTPException:
            with self.connection() as db:
                db.execute(
                    "UPDATE login_challenges SET attempts=attempts+1 WHERE hash=?",
                    (token_hash,),
                )
            raise
        with self.connection() as db:
            db.execute("DELETE FROM login_challenges WHERE hash=?", (token_hash,))
        return self.user(row["user_id"])

    def regenerate_recovery_codes(self, user_id, password, code):
        self.verify_password(user_id, password)
        throttle_key = "security-otp:" + user_id
        self.throttle(throttle_key, 8)
        self._verify_second_factor(user_id, code)
        with self.connection() as db:
            codes = self._replace_recovery_codes(db, user_id)
        self.clear_throttle(throttle_key)
        return {"recovery_codes": codes}

    def disable_totp(self, user_id, password, code, current_session):
        self.verify_password(user_id, password)
        throttle_key = "security-otp:" + user_id
        self.throttle(throttle_key, 8)
        self._verify_second_factor(user_id, code)
        with self.connection() as db:
            db.execute("DELETE FROM user_totp WHERE user_id=?", (user_id,))
            db.execute("DELETE FROM totp_setups WHERE user_id=?", (user_id,))
            db.execute("DELETE FROM recovery_codes WHERE user_id=?", (user_id,))
            db.execute("DELETE FROM login_challenges WHERE user_id=?", (user_id,))
            db.execute(
                "DELETE FROM sessions WHERE user_id=? AND hash<>?",
                (user_id, digest(current_session or "")),
            )
        self.clear_throttle(throttle_key)

    def session(self, user_id):
        token = secrets.token_urlsafe(36)
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (utc_epoch_seconds(),))
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?)",
                (digest(token), user_id, utc_epoch_seconds() + SESSION_SECONDS),
            )
        return token

    def user_for_session(self, token):
        if not token:
            return None
        with self.connection() as db:
            row = db.execute(
                """SELECT u.id,u.email,u.name,u.created_at FROM users u
                JOIN sessions s ON u.id=s.user_id WHERE s.hash=? AND s.expires_at>?""",
                (digest(token), utc_epoch_seconds()),
            ).fetchone()
        return dict(row) if row else None

    def user(self, user_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT id,email,name,created_at FROM users WHERE id=?", (user_id,)
            ).fetchone()
        return dict(row) if row else None

    def admin_users(self, query="", limit=50, offset=0):
        needle = f"%{query.strip().casefold()}%"
        now = utc_epoch_seconds()
        with self.connection() as db:
            total = db.execute(
                """SELECT count(*) FROM users
                WHERE ?='' OR lower(email) LIKE ? OR lower(name) LIKE ?""",
                (query.strip(), needle, needle),
            ).fetchone()[0]
            rows = db.execute(
                """SELECT u.id,u.email,u.name,u.created_at,
                (SELECT count(*) FROM api_keys k WHERE k.user_id=u.id) AS api_key_count,
                (SELECT count(*) FROM sessions s
                 WHERE s.user_id=u.id AND s.expires_at>?) AS active_session_count,
                EXISTS(SELECT 1 FROM user_totp t WHERE t.user_id=u.id) AS totp_enabled
                FROM users u
                WHERE ?='' OR lower(u.email) LIKE ? OR lower(u.name) LIKE ?
                ORDER BY u.created_at DESC,u.id LIMIT ? OFFSET ?""",
                (now, query.strip(), needle, needle, limit, offset),
            ).fetchall()
        items = [{**dict(row), "totp_enabled": bool(row["totp_enabled"])} for row in rows]
        return {"items": items, "total": total}

    def logout(self, token):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE hash=?", (digest(token or ""),))

    def user_for_key(self, token):
        principal = self.principal_for_key(token)
        return principal["user_id"] if principal else None

    def principal_for_key(self, token):
        with self.connection() as db:
            row = db.execute(
                """SELECT id,user_id,name,vault_access,feature_request_operator,permissions
                FROM api_keys WHERE hash=?""",
                (digest(token),),
            ).fetchone()
        if not row:
            return None
        return {
            "key_id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "vault_access": bool(row["vault_access"]),
            "feature_request_operator": bool(row["feature_request_operator"]),
            "permissions": stored_agent_permissions(row["permissions"]),
            "namespace_grants": self.key_namespace_grants(row["user_id"], row["id"]),
        }

    def list_keys(self, user_id):
        with self.connection() as db:
            rows = db.execute(
                """SELECT id,name,prefix,created_at,vault_access,feature_request_operator,permissions
                FROM api_keys
                WHERE user_id=? ORDER BY created_at DESC,id""",
                (user_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "vault_access": bool(row["vault_access"]),
                "feature_request_operator": bool(row["feature_request_operator"]),
                "permissions": stored_agent_permissions(row["permissions"]),
                "namespace_grants": self.key_namespace_grants(user_id, row["id"]),
            }
            for row in rows
        ]

    def create_key(self, user_id, name, vault_access=False, permissions=None):
        token = "vm_" + secrets.token_urlsafe(36)
        permissions = normalize_agent_permissions(
            DEFAULT_AGENT_PERMISSIONS if permissions is None else permissions
        )
        record = dict(
            id=str(uuid4()),
            name=name,
            prefix=token[:10] + "…",
            created_at=utc_epoch_seconds(),
            vault_access=bool(vault_access),
            feature_request_operator=False,
            permissions=permissions,
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
                """INSERT INTO api_keys(
                    id,user_id,hash,name,prefix,created_at,vault_access,permissions
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    record["id"],
                    user_id,
                    digest(token),
                    name,
                    record["prefix"],
                    record["created_at"],
                    bool(record["vault_access"]),
                    json.dumps(permissions, separators=(",", ":")),
                ),
            )
        return {**record, "key": token}

    def list_namespaces(self, user_id):
        with self.connection() as db:
            rows = db.execute(
                "SELECT id,name,created_at FROM namespaces WHERE user_id=? ORDER BY created_at,id",
                (user_id,),
            ).fetchall()
        return [
            {"id": "default", "name": "Default", "created_at": None, "legacy": True},
            *[{**dict(row), "legacy": False} for row in rows],
        ]

    def create_namespace(self, user_id, name):
        record = {"id": str(uuid4()), "name": name.strip(), "created_at": utc_epoch_seconds()}
        try:
            with self.connection() as db:
                db.execute(
                    "INSERT INTO namespaces(id,user_id,name,created_at) VALUES(?,?,?,?)",
                    (record["id"], user_id, record["name"], record["created_at"]),
                )
        except (sqlite3.IntegrityError, IntegrityError):
            raise HTTPException(409, "같은 이름의 namespace가 이미 있습니다.") from None
        return {**record, "legacy": False}

    def namespace_exists(self, user_id, namespace_id):
        if namespace_id == "default":
            return True
        with self.connection() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM namespaces WHERE user_id=? AND id=?",
                    (user_id, namespace_id),
                ).fetchone()
            )

    def key_namespace_grants(self, user_id, key_id):
        with self.connection() as db:
            rows = db.execute(
                """SELECT namespace_id,can_read,can_write FROM api_key_namespace_grants
                WHERE user_id=? AND api_key_id=? ORDER BY namespace_id""",
                (user_id, key_id),
            ).fetchall()
        if not rows:
            return [{"namespace_id": "default", "can_read": True, "can_write": True}]
        return [
            {
                "namespace_id": row["namespace_id"],
                "can_read": bool(row["can_read"]),
                "can_write": bool(row["can_write"]),
            }
            for row in rows
        ]

    def replace_key_namespace_grants(self, user_id, key_id, grants):
        with self.connection() as db:
            if not db.execute(
                "SELECT 1 FROM api_keys WHERE id=? AND user_id=?", (key_id, user_id)
            ).fetchone():
                raise HTTPException(404, "키를 찾을 수 없습니다.")
            for grant in grants:
                if not self.namespace_exists(user_id, grant.namespace_id):
                    raise HTTPException(422, "존재하지 않는 namespace입니다.")
                if grant.can_write and not grant.can_read:
                    raise HTTPException(422, "write 권한은 read 권한과 함께 부여해야 합니다.")
            db.execute(
                "DELETE FROM api_key_namespace_grants WHERE user_id=? AND api_key_id=?",
                (user_id, key_id),
            )
            effective_grants = grants or [
                NamespaceGrant(namespace_id="default", can_read=False, can_write=False)
            ]
            for grant in effective_grants:
                db.execute(
                    """INSERT INTO api_key_namespace_grants(
                    user_id,api_key_id,namespace_id,can_read,can_write
                    ) VALUES(?,?,?,?,?)""",
                    (user_id, key_id, grant.namespace_id, grant.can_read, grant.can_write),
                )
        return self.key_namespace_grants(user_id, key_id)

    def set_key_access(self, user_id, id, vault_access=None, permissions=None):
        with self.connection() as db:
            row = db.execute(
                """SELECT name,prefix,vault_access,permissions FROM api_keys
                WHERE id=? AND user_id=?""",
                (id, user_id),
            ).fetchone()
            if not row:
                raise HTTPException(404, "키를 찾을 수 없습니다.")
            before_permissions = stored_agent_permissions(row["permissions"])
            after_permissions = (
                before_permissions
                if permissions is None
                else normalize_agent_permissions(permissions)
            )
            before_vault = bool(row["vault_access"])
            after_vault = before_vault if vault_access is None else bool(vault_access)
            db.execute(
                """UPDATE api_keys SET vault_access=?,permissions=?
                WHERE id=? AND user_id=?""",
                (
                    after_vault,
                    json.dumps(after_permissions, separators=(",", ":")),
                    id,
                    user_id,
                ),
            )
            if before_permissions != after_permissions or before_vault != after_vault:
                db.execute(
                    """INSERT INTO api_key_permission_events(
                    id,user_id,api_key_id,key_name,key_prefix,changed_at,
                    before_permissions,after_permissions,before_vault_access,after_vault_access
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid4()),
                        user_id,
                        id,
                        row["name"],
                        row["prefix"],
                        utc_epoch_seconds(),
                        json.dumps(before_permissions, separators=(",", ":")),
                        json.dumps(after_permissions, separators=(",", ":")),
                        before_vault,
                        after_vault,
                    ),
                )
        return {"id": id, "vault_access": after_vault, "permissions": after_permissions}

    def list_key_permission_events(self, user_id, id, limit=50):
        with self.connection() as db:
            if not db.execute(
                "SELECT 1 FROM api_keys WHERE id=? AND user_id=?", (id, user_id)
            ).fetchone():
                raise HTTPException(404, "키를 찾을 수 없습니다.")
            rows = db.execute(
                """SELECT id,api_key_id,key_name,key_prefix,changed_at,
                before_permissions,after_permissions,before_vault_access,after_vault_access
                FROM api_key_permission_events WHERE user_id=? AND api_key_id=?
                ORDER BY changed_at DESC,id DESC LIMIT ?""",
                (user_id, id, limit),
            ).fetchall()
        return [
            {
                **dict(row),
                "before_permissions": stored_agent_permissions(row["before_permissions"]),
                "after_permissions": stored_agent_permissions(row["after_permissions"]),
                "before_vault_access": bool(row["before_vault_access"]),
                "after_vault_access": bool(row["after_vault_access"]),
            }
            for row in rows
        ]

    def set_key_feature_request_operator(self, user_id, id, enabled):
        with self.connection() as db:
            result = db.execute(
                """UPDATE api_keys SET feature_request_operator=?
                WHERE id=? AND user_id=?""",
                (bool(enabled), id, user_id),
            )
            if not result.rowcount:
                raise HTTPException(404, "에이전트 연결을 찾을 수 없습니다.")
        return {"id": id, "feature_request_operator": bool(enabled)}

    def start_device(
        self,
        name,
        vault_access=False,
        expires_in=300,
        upgrade_key_id=None,
        upgrade_user_id=None,
    ):
        device = secrets.token_urlsafe(36)
        code = secrets.token_hex(5).upper()
        expires_in = max(60, min(int(expires_in), 900))
        expires = utc_epoch_seconds() + expires_in
        with self.connection() as db:
            db.execute("DELETE FROM device_logins WHERE expires_at <= ?", (utc_epoch_seconds(),))
            db.execute(
                """INSERT INTO device_logins(
                    device_hash,user_hash,name,expires_at,state,user_id,polled_at,vault_access,
                    upgrade_key_id,upgrade_user_id
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    digest(device),
                    digest(code),
                    name,
                    expires,
                    "pending",
                    None,
                    0,
                    bool(vault_access),
                    upgrade_key_id,
                    upgrade_user_id,
                ),
            )
        return {
            "device_code": device,
            "user_code": code,
            "expires_in": expires_in,
            "interval": 3,
            "upgrade": bool(upgrade_key_id),
        }

    def device_info(self, code, user_id=None):
        with self.connection() as db:
            row = db.execute(
                """SELECT name,expires_at,state,vault_access,upgrade_key_id,upgrade_user_id
                FROM device_logins
                WHERE user_hash=?""",
                (digest(code.upper()),),
            ).fetchone()
        if not row or row["expires_at"] <= utc_epoch_seconds():
            raise HTTPException(410, "연결 요청이 만료되었거나 존재하지 않습니다.")
        if row["upgrade_user_id"] and row["upgrade_user_id"] != user_id:
            raise HTTPException(403, "이 권한 변경 요청은 다른 계정에 연결되어 있습니다.")
        return {
            "name": row["name"],
            "expires_at": row["expires_at"],
            "state": row["state"],
            "vault_access": bool(row["vault_access"]),
            "upgrade": bool(row["upgrade_key_id"]),
        }

    def approve_device(self, user_id, code, approved, vault_access=None):
        with self.connection() as db:
            row = db.execute(
                """SELECT vault_access,upgrade_user_id FROM device_logins
                WHERE user_hash=? AND state='pending' AND expires_at>?""",
                (digest(code.upper()), utc_epoch_seconds()),
            ).fetchone()
            if not row:
                raise HTTPException(410, "이미 처리되었거나 만료된 연결 요청입니다.")
            if row["upgrade_user_id"] and row["upgrade_user_id"] != user_id:
                raise HTTPException(403, "이 권한 변경 요청은 다른 계정에 연결되어 있습니다.")
            granted_vault_access = bool(row["vault_access"])
            if vault_access is not None:
                granted_vault_access = bool(vault_access) and granted_vault_access
            result = db.execute(
                """UPDATE device_logins SET state=?,user_id=?,vault_access=? WHERE user_hash=?
                AND state='pending' AND expires_at>?""",
                (
                    "approved" if approved else "denied",
                    user_id,
                    granted_vault_access,
                    digest(code.upper()),
                    utc_epoch_seconds(),
                ),
            )
            if not result.rowcount:
                raise HTTPException(410, "이미 처리되었거나 만료된 연결 요청입니다.")
        return {
            "state": "approved" if approved else "denied",
            "vault_access": granted_vault_access if approved else False,
        }

    def poll_device(self, device):
        now = utc_epoch_seconds()
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
            if row["upgrade_key_id"]:
                result = db.execute(
                    """UPDATE api_keys SET vault_access=?
                    WHERE id=? AND user_id=?""",
                    (bool(row["vault_access"]), row["upgrade_key_id"], row["user_id"]),
                )
                if not result.rowcount:
                    raise HTTPException(410, "Agent connection no longer exists")
                db.execute(
                    "UPDATE device_logins SET state='used' WHERE device_hash=?",
                    (digest(device),),
                )
                return {
                    "state": "connected",
                    "key_id": row["upgrade_key_id"],
                    "upgraded": True,
                    "vault_access": bool(row["vault_access"]),
                }
            if db.execute("SELECT count(*) FROM api_keys WHERE user_id=?", (row["user_id"],)).fetchone()[0] >= 30:
                raise HTTPException(422, "Too many agent keys; revoke an unused key in the console")
            token = "vm_" + secrets.token_urlsafe(36)
            key_id = str(uuid4())
            db.execute(
                """INSERT INTO api_keys(
                    id,user_id,hash,name,prefix,created_at,vault_access
                ) VALUES(?,?,?,?,?,?,?)""",
                (
                    key_id,
                    row["user_id"],
                    digest(token),
                    row["name"],
                    token[:10] + "…",
                    now,
                    row["vault_access"],
                ),
            )
            db.execute("UPDATE device_logins SET state='used' WHERE device_hash=?", (digest(device),))
        return {
            "state": "connected",
            "key": token,
            "key_id": key_id,
            "upgraded": False,
            "vault_access": bool(row["vault_access"]),
        }

    def revoke_key(self, user_id, id):
        with self.connection() as db:
            result = db.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (id, user_id))
            if not result.rowcount:
                raise HTTPException(404, "키를 찾을 수 없습니다.")
