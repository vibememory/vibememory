import asyncio
import hashlib
import hmac
import html
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import anyio
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from .auth import (
    COOKIE,
    SESSION_SECONDS,
    AuthStore,
    Credentials,
    KeyAccessUpdate,
    KeyInput,
    Signup,
)
from .config import Settings
from .embeddings import Embedder
from .files import FileStorage
from .mcp import LATEST_PROTOCOL, MCPHandler
from .models import (
    AgentMessageAck,
    AgentMessageInput,
    DocumentInput,
    EntityInput,
    FeatureRequestInput,
    FeatureRequestUpdate,
    KeywordUpdate,
    MemoryInput,
    RecordArchive,
    RecordMerge,
    RecordSecurityUpdate,
    RecordUpdate,
    RelationInput,
    RelationUpdate,
    SearchInput,
    VaultCaptureRequest,
    VaultCaptureSubmit,
    VaultInput,
)
from .oauth import OAuthError, OAuthStore
from .postgres import PostgresDatabase
from .postgres_store import PostgresStore
from .retrieval import retrieve
from .security import SecurityPolicyError, prepare_record_security
from .store import Conflict, DuplicateRequestConflict, FileInUse, NotFound, Store
from .vault import (
    VaultCaptureConsumed,
    VaultCaptureExpired,
    VaultCaptureNotFound,
    VaultIntegrityError,
    VaultNotFound,
    VaultStore,
)
from .web import mount_web

log = logging.getLogger(__name__)


class DevicePoll(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_code: str = Field(min_length=40, max_length=100)


class DeviceApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_code: str = Field(pattern=r"^[A-Fa-f0-9]{10}$")
    approved: bool


class OAuthRegistration(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    redirect_uris: list[str] = Field(min_length=1, max_length=10)
    client_name: str = Field(default="MCP client", min_length=1, max_length=100)
    token_endpoint_auth_method: str = "none"
    grant_types: list[str] = Field(
        default_factory=lambda: ["authorization_code", "refresh_token"]
    )
    response_types: list[str] = Field(default_factory=lambda: ["code"])


def create_app(settings=None, embedder=None):
    settings = settings or Settings()
    settings.validate_keys()
    embedder = embedder or Embedder(settings.embedding_model, settings.embedding_cache)

    database = (
        PostgresDatabase(
            settings.database_url,
            embedder.model_name,
            settings.embedding_dimension,
            settings.database_pool_size,
        )
        if settings.database_url
        else None
    )
    account_storage = database or settings.data_dir / "auth.sqlite"
    accounts = AuthStore(account_storage)
    oauth = OAuthStore(account_storage)
    files = FileStorage(settings.data_dir / "files", settings.upload_max_bytes)
    vault = VaultStore(
        database or settings.data_dir / "vault.sqlite",
        settings.vault_key_file or settings.data_dir / "vault.key",
    )

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = (
            PostgresStore(database)
            if database
            else Store(settings.data_dir / "graph", embedder.model_name)
        )
        try:
            yield
        finally:
            app.state.store.close()
            if database:
                database.close()

    app = FastAPI(
        title="Vibe Memory",
        version="0.12.0",
        lifespan=lifespan,
        description="Agent-authored memory graph and keyword-only vector index. No inference or document processing.",
    )
    auth = HTTPBearer(auto_error=False)
    mcp_handler = MCPHandler(embedder)
    public_origin = settings.public_origin.rstrip("/")
    oauth_issuer = public_origin
    mcp_resource = public_origin + "/mcp"
    oauth_scopes = {"memory:read", "memory:write", "feature:write"}
    scope_labels = {
        "memory:read": "기억·문서·관계 조회",
        "memory:write": "기억·엔티티·문서·관계 저장",
        "feature:write": "기능 요청 제출",
    }
    key_hashes = [
        (hashlib.sha256(key.encode()).digest(), owner) for key, owner in settings.api_keys.items()
    ]

    def bind_agent(request, user, agent_id, name, transport):
        request.state.agent_id = agent_id
        request.state.agent_name = name
        request.state.agent_transport = transport
        request.app.state.store.register_agent(user, agent_id, name, transport)
        return user

    def check_origin(request):
        if request.headers.get("origin") != settings.public_origin.rstrip("/"):
            raise HTTPException(403, "이 페이지에서 다시 로그인해주세요.")

    def browser_user(request: Request):
        user = accounts.user_for_session(request.cookies.get(COOKIE))
        if not user:
            raise HTTPException(401, "로그인이 필요합니다.")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_origin(request)
        return user

    def is_admin(user):
        return user["email"].casefold() in settings.admin_emails

    def admin_user(user=Depends(browser_user)):
        if not is_admin(user):
            raise HTTPException(403, "관리자 권한이 필요합니다.")
        return user

    def owner(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(auth)):
        request.state.vault_access = False
        request.state.auth_kind = "none"
        if credentials and credentials.scheme.lower() == "bearer":
            supplied = hashlib.sha256(credentials.credentials.encode()).digest()
            for expected, user in key_hashes:
                if hmac.compare_digest(expected, supplied):
                    request.state.auth_kind = "legacy-key"
                    return bind_agent(
                        request, user, "legacy:" + expected.hex()[:24],
                        "Legacy API agent", "legacy-key"
                    )
            principal = accounts.principal_for_key(credentials.credentials)
            if principal:
                request.state.vault_access = principal["vault_access"]
                request.state.auth_kind = "agent-key"
                request.state.key_id = principal["key_id"]
                return bind_agent(
                    request, principal["user_id"], "key:" + principal["key_id"],
                    principal["name"], "api-key"
                )
        elif not request.headers.get("Authorization"):
            session_user = accounts.user_for_session(request.cookies.get(COOKIE))
            if session_user:
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    check_origin(request)
                request.state.vault_access = True
                request.state.auth_kind = "browser-session"
                return bind_agent(
                    request, session_user["id"], "browser:" + session_user["id"],
                    session_user["name"], "browser"
                )
        raise HTTPException(
            401, "Invalid or missing API key", headers={"WWW-Authenticate": "Bearer"}
        )

    def vault_user(request: Request, user=Depends(owner)):
        if not request.state.vault_access:
            raise HTTPException(403, "This agent connection does not have Vault access")
        return user

    def store(request: Request):
        return request.app.state.store

    def valid_redirect_uri(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 2048:
            return False
        if re.search(r"[\x00-\x20\x7f]", value):
            return False
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return False
        if not parsed.scheme or not parsed.netloc or parsed.fragment or parsed.username or parsed.password:
            return False
        if parsed.scheme == "https":
            return True
        return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1", "localhost"} and port is not None

    def oauth_error_response(error, description, status=400):
        return JSONResponse(
            {"error": error, "error_description": description},
            status_code=status,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    async def oauth_form(request):
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
        if content_type != "application/x-www-form-urlencoded":
            raise HTTPException(415, "OAuth requests must use application/x-www-form-urlencoded")
        body = await request.body()
        if len(body) > 32768:
            raise HTTPException(413, "OAuth request is too large")
        try:
            parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
        except (UnicodeDecodeError, ValueError):
            raise HTTPException(400, "Malformed OAuth form") from None
        return {key: values[-1] for key, values in parsed.items()}

    def normalize_scopes(value):
        scopes = set((value or " ".join(sorted(oauth_scopes))).split())
        if not scopes or not scopes.issubset(oauth_scopes):
            raise OAuthError("invalid_scope", "Requested OAuth scope is not supported")
        return " ".join(sorted(scopes))

    def authorize_parameters(params):
        client_id = params.get("client_id", "")
        client = oauth.client(client_id)
        if not client:
            raise OAuthError("invalid_request", "Unknown OAuth client")
        redirect_uri = params.get("redirect_uri", "")
        if redirect_uri not in client["redirect_uris"]:
            raise OAuthError("invalid_request", "redirect_uri is not registered")
        if params.get("response_type") != "code":
            raise OAuthError("unsupported_response_type", "Only authorization code is supported")
        challenge = params.get("code_challenge", "")
        if params.get("code_challenge_method") != "S256" or not re.fullmatch(
            r"[A-Za-z0-9_-]{43,128}", challenge
        ):
            raise OAuthError("invalid_request", "A valid S256 PKCE challenge is required")
        state = params.get("state", "")
        if len(state) > 2048:
            raise OAuthError("invalid_request", "OAuth state is too long")
        resource = params.get("resource") or mcp_resource
        if resource != mcp_resource:
            raise OAuthError("invalid_target", "OAuth resource does not match this MCP server")
        return {
            "client": client,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": normalize_scopes(params.get("scope", "")),
            "state": state,
            "resource": resource,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "response_type": "code",
        }

    def redirect_with_query(uri, values):
        parsed = urlsplit(uri)
        query = parse_qs(parsed.query, keep_blank_values=True)
        for key, value in values.items():
            if value != "":
                query[key] = [value]
        encoded = urlencode([(key, item) for key, items in query.items() for item in items])
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, encoded, parsed.fragment))

    def oauth_consent_token(session_token, params):
        """Bind consent to the browser session and exact OAuth authorization request."""
        message = "\0".join(
            str(params[key])
            for key in (
                "client_id",
                "redirect_uri",
                "scope",
                "state",
                "resource",
                "code_challenge",
                "code_challenge_method",
                "response_type",
            )
        )
        return hmac.new(
            session_token.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    def mcp_challenge():
        metadata = public_origin + "/.well-known/oauth-protected-resource/mcp"
        return {
            "WWW-Authenticate": (
                f'Bearer resource_metadata="{metadata}", '
                f'scope="{" ".join(sorted(oauth_scopes))}"'
            ),
            "Cache-Control": "no-store",
        }

    def mcp_principal(request):
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not token:
            return None
        return oauth.principal(token, mcp_resource)

    @app.middleware("http")
    async def no_private_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/v1/", "/auth/", "/oauth/", "/mcp", "/.well-known/")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def signed_in(user):
        response = JSONResponse({"user": user, "is_admin": is_admin(user)})
        response.set_cookie(
            COOKIE,
            accounts.session(user["id"]),
            max_age=SESSION_SECONDS,
            httponly=True,
            secure=settings.public_origin.startswith("https://"),
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/auth/device/start", tags=["account"])
    def start_device(data: KeyInput, request: Request):
        accounts.throttle("device:" + (request.client.host if request.client else "unknown"), 20)
        result = accounts.start_device(data.name, data.vault_access)
        result["verification_uri_complete"] = (
            settings.public_origin.rstrip("/") + "/connect?code=" + result["user_code"]
        )
        return result

    @app.post("/auth/device/poll", tags=["account"])
    def poll_device(data: DevicePoll):
        return accounts.poll_device(data.device_code)

    @app.get("/auth/device", tags=["account"])
    def device_info(code: str = Query(pattern=r"^[A-Fa-f0-9]{10}$"), user=Depends(browser_user)):
        return accounts.device_info(code)

    @app.post("/auth/device/approve", tags=["account"])
    def approve_device(data: DeviceApproval, user=Depends(browser_user)):
        return accounts.approve_device(user["id"], data.user_code, data.approved)

    @app.post("/auth/signup", tags=["account"])
    def signup(data: Signup, request: Request):
        check_origin(request)
        if not settings.signup_enabled:
            raise HTTPException(403, "현재 회원가입을 받지 않고 있습니다.")
        accounts.throttle("signup:" + (request.client.host if request.client else "unknown"), 20)
        return signed_in(accounts.signup(data))

    @app.post("/auth/login", tags=["account"])
    def login(data: Credentials, request: Request):
        check_origin(request)
        return signed_in(accounts.login(data))

    @app.get("/auth/me", tags=["account"])
    def account(user=Depends(browser_user)):
        return {"user": user, "is_admin": is_admin(user)}

    @app.post("/auth/logout", status_code=204, tags=["account"])
    def logout(request: Request):
        check_origin(request)
        accounts.logout(request.cookies.get(COOKIE))
        from fastapi import Response

        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE,
            path="/",
            secure=settings.public_origin.startswith("https://"),
            httponly=True,
            samesite="lax",
        )
        return response

    @app.get("/auth/api-keys", tags=["account"])
    def api_keys(user=Depends(browser_user)):
        return {"items": accounts.list_keys(user["id"])}

    @app.post("/auth/api-keys", status_code=201, tags=["account"])
    def create_api_key(data: KeyInput, user=Depends(browser_user)):
        return accounts.create_key(user["id"], data.name, data.vault_access)

    @app.patch("/auth/api-keys/{id}", tags=["account"])
    def update_api_key(id: str, data: KeyAccessUpdate, user=Depends(browser_user)):
        return accounts.set_key_vault_access(user["id"], id, data.vault_access)

    @app.delete("/auth/api-keys/{id}", status_code=204, tags=["account"])
    def revoke_api_key(id: str, user=Depends(browser_user), db=Depends(store)):
        accounts.revoke_key(user["id"], id)
        db.deactivate_agent(user["id"], "key:" + id)

    @app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
    @app.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
    def oauth_protected_resource():
        return {
            "resource": mcp_resource,
            "authorization_servers": [oauth_issuer],
            "scopes_supported": sorted(oauth_scopes),
            "bearer_methods_supported": ["header"],
            "resource_documentation": public_origin + "/guide#mcp",
        }

    @app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
    def oauth_server_metadata():
        return {
            "issuer": oauth_issuer,
            "authorization_endpoint": public_origin + "/oauth/authorize",
            "token_endpoint": public_origin + "/oauth/token",
            "registration_endpoint": public_origin + "/oauth/register",
            "revocation_endpoint": public_origin + "/oauth/revoke",
            "scopes_supported": sorted(oauth_scopes),
            "response_types_supported": ["code"],
            "response_modes_supported": ["query"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["none"],
            "revocation_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
            "service_documentation": public_origin + "/guide#mcp",
        }

    @app.post("/oauth/register", status_code=201, tags=["MCP OAuth"])
    def oauth_register(data: OAuthRegistration, request: Request):
        accounts.throttle(
            "oauth-register:" + (request.client.host if request.client else "unknown"), 50
        )
        if data.token_endpoint_auth_method != "none":
            return oauth_error_response(
                "invalid_client_metadata", "Only public PKCE clients are supported"
            )
        if re.search(r"[\x00-\x1f\x7f]", data.client_name):
            return oauth_error_response(
                "invalid_client_metadata", "Client name contains control characters"
            )
        if "authorization_code" not in data.grant_types or any(
            grant not in {"authorization_code", "refresh_token"} for grant in data.grant_types
        ):
            return oauth_error_response(
                "invalid_client_metadata", "Unsupported OAuth grant type"
            )
        if data.response_types != ["code"]:
            return oauth_error_response(
                "invalid_client_metadata", "Only the code response type is supported"
            )
        redirect_uris = list(dict.fromkeys(data.redirect_uris))
        if not all(valid_redirect_uri(uri) for uri in redirect_uris):
            return oauth_error_response(
                "invalid_redirect_uri",
                "Redirect URIs must use HTTPS or an explicit localhost loopback port",
            )
        return JSONResponse(
            oauth.register_client(data.client_name, redirect_uris),
            status_code=201,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/oauth/authorize", response_class=HTMLResponse, tags=["MCP OAuth"])
    def oauth_authorize(request: Request):
        try:
            params = authorize_parameters(request.query_params)
        except OAuthError as error:
            return oauth_error_response(error.code, error.description)
        session_token = request.cookies.get(COOKIE, "")
        user = accounts.user_for_session(session_token)
        if not user:
            next_path = request.url.path + ("?" + request.url.query if request.url.query else "")
            return RedirectResponse("/login?" + urlencode({"next": next_path}), status_code=302)
        hidden = "".join(
            f'<input type="hidden" name="{html.escape(key, quote=True)}" '
            f'value="{html.escape(str(value), quote=True)}">'
            for key, value in params.items()
            if key != "client"
        )
        hidden += (
            '<input type="hidden" name="consent_token" value="'
            + oauth_consent_token(session_token, params)
            + '">'
        )
        permissions = "".join(
            f"<li>{html.escape(scope_labels[scope])}</li>" for scope in params["scope"].split()
        )
        client_name = html.escape(params["client"]["client_name"])
        account = html.escape(user["email"])
        redirect = urlsplit(params["redirect_uri"])
        redirect_origin = urlunsplit((redirect.scheme, redirect.netloc, "", "", ""))
        page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>MCP 연결 승인 — Vibe Memory</title><link rel="icon" href="/assets/favicon.svg">
<style>*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;
padding:24px;background:#f6f7fa;color:#263147;font-family:Arial,sans-serif}}main{{width:min(520px,100%);
padding:34px;border:1px solid #e0e5ef;border-radius:16px;background:#fff;box-shadow:0 24px 70px
rgba(31,45,75,.08)}}.brand{{display:flex;align-items:center;gap:10px;margin-bottom:28px;color:#263147;
font-size:19px;font-weight:700;text-decoration:none}}.brand img{{width:30px}}.eyebrow{{color:#315bfb;
font-size:10px;letter-spacing:1.2px}}h1{{margin:9px 0 10px;font-size:25px}}p,li{{color:#68758b;
font-size:13px;line-height:1.75}}ul{{margin:20px 0;padding:16px 16px 16px 34px;border-radius:10px;
background:#f5f7ff}}.account{{padding:12px 14px;border:1px solid #e5e8ef;border-radius:9px;
background:#fafbfc}}.actions{{display:flex;gap:9px;margin-top:24px}}button{{flex:1;padding:12px;border-radius:8px;
font-size:13px;font-weight:650;cursor:pointer}}.approve{{border:0;background:#315bfb;color:#fff}}.deny{{border:1px
solid #dfe3eb;background:#fff;color:#68758b}}small{{display:block;margin-top:18px;color:#98a1af;
font-size:10px;line-height:1.65}}</style></head><body><main><a class="brand" href="/"><img
src="/assets/favicon.svg" alt="">vibememory</a><p class="eyebrow">CONNECT REMOTE MCP</p>
<h1>{client_name} 연결을 승인할까요?</h1><p>GPT 또는 Claude가 다음 작업을 내 Vibe Memory에서
수행할 수 있습니다.</p><ul>{permissions}</ul><p class="account">연결 계정 · <strong>{account}</strong></p>
<form method="post" action="/oauth/authorize">{hidden}<div class="actions"><button class="deny"
name="decision" value="deny" type="submit">거절</button><button class="approve" name="decision"
value="approve" type="submit">연결 승인</button></div></form><small>원본 파일 업로드와 Vault 비밀값은
이 연결에 포함되지 않습니다. 연결은 콘솔에서 언제든 철회할 수 있습니다.</small></main></body></html>"""
        return HTMLResponse(
            page,
            headers={
                "Content-Security-Policy": (
                    "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
                    f"form-action 'self' {redirect_origin}; base-uri 'none'; "
                    "frame-ancestors 'none'"
                ),
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
            },
        )

    @app.post("/oauth/authorize", tags=["MCP OAuth"])
    async def oauth_authorize_decision(request: Request):
        session_token = request.cookies.get(COOKIE, "")
        user = accounts.user_for_session(session_token)
        if not user:
            return oauth_error_response("access_denied", "Login session expired", 401)
        form = await oauth_form(request)
        try:
            params = authorize_parameters(form)
        except OAuthError as error:
            return oauth_error_response(error.code, error.description)
        expected_consent = oauth_consent_token(session_token, params)
        if not hmac.compare_digest(form.get("consent_token", ""), expected_consent):
            return oauth_error_response(
                "access_denied", "OAuth consent request is invalid or expired", 403
            )
        if form.get("decision") != "approve":
            location = redirect_with_query(
                params["redirect_uri"],
                {"error": "access_denied", "state": params["state"]},
            )
            return RedirectResponse(location, status_code=303)
        code = oauth.create_code(
            client_id=params["client_id"],
            user_id=user["id"],
            redirect_uri=params["redirect_uri"],
            scope=params["scope"],
            resource=params["resource"],
            code_challenge=params["code_challenge"],
        )
        location = redirect_with_query(
            params["redirect_uri"], {"code": code, "state": params["state"]}
        )
        return RedirectResponse(location, status_code=303)

    @app.post("/oauth/token", tags=["MCP OAuth"])
    async def oauth_token(request: Request):
        form = await oauth_form(request)
        client_id = form.get("client_id", "")
        if not oauth.client(client_id):
            return oauth_error_response("invalid_client", "Unknown OAuth client", 401)
        resource = form.get("resource") or mcp_resource
        if resource != mcp_resource:
            return oauth_error_response("invalid_target", "OAuth resource does not match")
        try:
            if form.get("grant_type") == "authorization_code":
                verifier = form.get("code_verifier", "")
                if not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier):
                    raise OAuthError("invalid_grant", "A valid PKCE verifier is required")
                result = oauth.exchange_code(
                    code=form.get("code", ""),
                    client_id=client_id,
                    redirect_uri=form.get("redirect_uri", ""),
                    code_verifier=verifier,
                    resource=resource,
                )
            elif form.get("grant_type") == "refresh_token":
                scope = form.get("scope")
                if scope:
                    scope = normalize_scopes(scope)
                result = oauth.refresh(
                    refresh_token=form.get("refresh_token", ""),
                    client_id=client_id,
                    resource=resource,
                    requested_scope=scope,
                )
            else:
                raise OAuthError("unsupported_grant_type", "Unsupported OAuth grant type")
        except OAuthError as error:
            return oauth_error_response(error.code, error.description)
        return JSONResponse(
            result, headers={"Cache-Control": "no-store", "Pragma": "no-cache"}
        )

    @app.post("/oauth/revoke", status_code=200, tags=["MCP OAuth"])
    async def oauth_revoke(request: Request):
        form = await oauth_form(request)
        oauth.revoke_token(form.get("token", ""))
        return Response(status_code=200, headers={"Cache-Control": "no-store"})

    @app.get("/auth/mcp-connections", tags=["account"])
    def mcp_connections(user=Depends(browser_user)):
        return {"items": oauth.list_connections(user["id"]), "server_url": mcp_resource}

    @app.delete("/auth/mcp-connections/{client_id}", status_code=204, tags=["account"])
    def revoke_mcp_connection(
        client_id: str, user=Depends(browser_user), db=Depends(store)
    ):
        try:
            oauth.revoke_connection(user["id"], client_id)
            db.deactivate_agent(user["id"], "oauth:" + client_id)
        except OAuthError:
            raise HTTPException(404, "MCP 연결을 찾을 수 없습니다.") from None

    @app.post("/mcp", tags=["MCP"])
    async def mcp_endpoint(request: Request):
        principal = mcp_principal(request)
        if not principal:
            return JSONResponse(
                {"error": "unauthorized", "error_description": "OAuth login is required"},
                status_code=401,
                headers=mcp_challenge(),
            )
        principal["agent_id"] = "oauth:" + principal["client_id"]
        principal["agent_name"] = principal["client_name"]
        request.app.state.store.register_agent(
            principal["user_id"], principal["agent_id"], principal["agent_name"], "oauth"
        )
        body = await request.body()
        if len(body) > 1024 * 1024:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Request too large"}},
                status_code=413,
            )
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )
        db = request.app.state.store
        if isinstance(payload, list):
            if not payload:
                return JSONResponse(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}},
                    status_code=400,
                )
            results = [mcp_handler.dispatch(item, principal, db) for item in payload]
            results = [item for item in results if item is not None]
            if not results:
                return Response(status_code=202)
            response = JSONResponse(results)
        else:
            result = mcp_handler.dispatch(payload, principal, db)
            if result is None:
                return Response(status_code=202)
            response = JSONResponse(result)
        response.headers["MCP-Protocol-Version"] = LATEST_PROTOCOL
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/mcp", include_in_schema=False)
    def mcp_event_stream(request: Request):
        if not mcp_principal(request):
            return Response(status_code=401, headers=mcp_challenge())
        return Response(
            status_code=405,
            headers={"Allow": "POST", "Cache-Control": "no-store"},
        )

    @app.options("/mcp", include_in_schema=False)
    def mcp_options():
        return Response(
            status_code=204,
            headers={"Allow": "POST, GET, OPTIONS", "Cache-Control": "no-store"},
        )

    @app.exception_handler(NotFound)
    async def missing(request, error):
        return JSONResponse(status_code=404, content={"detail": "Record or relationship not found"})

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse(
            status_code=409, content={"detail": "Version conflict; reload the current resource"}
        )

    @app.exception_handler(FileInUse)
    async def file_in_use(request, error):
        return JSONResponse(
            status_code=409,
            content={"detail": "File is referenced by a document; delete the document first"},
        )

    @app.exception_handler(SecurityPolicyError)
    async def security_policy_error(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(VaultNotFound)
    async def vault_missing(request, error):
        return JSONResponse(status_code=404, content={"detail": "Vault entry not found"})

    @app.exception_handler(VaultIntegrityError)
    async def vault_integrity(request, error):
        log.error("Vault ciphertext authentication failed")
        return JSONResponse(status_code=500, content={"detail": "Vault entry cannot be decrypted"})

    @app.exception_handler(VaultCaptureNotFound)
    async def vault_capture_missing(request, error):
        return JSONResponse(status_code=404, content={"detail": "Vault capture link not found"})

    @app.exception_handler(VaultCaptureExpired)
    async def vault_capture_expired(request, error):
        return JSONResponse(status_code=410, content={"detail": "Vault capture link expired"})

    @app.exception_handler(VaultCaptureConsumed)
    async def vault_capture_consumed(request, error):
        return JSONResponse(status_code=409, content={"detail": "Vault capture link already used"})

    @app.post("/v1/vault/captures", status_code=201, tags=["vault"])
    def create_vault_capture(
        data: VaultCaptureRequest,
        request: Request,
        user=Depends(vault_user),
    ):
        user_id = user["id"] if isinstance(user, dict) else user
        token, result = vault.create_capture(
            user_id,
            data.name,
            data.description,
            request.state.agent_id,
            request.state.agent_name,
            data.expires_in,
        )
        # Keep the short-lived capability in the URL fragment so browsers never
        # send it in an HTTP request, referrer, or access log.
        result["capture_url"] = public_origin + "/capture#token=" + token
        return result

    @app.get("/v1/vault/captures/{token}", tags=["vault"])
    def inspect_vault_capture(token: str, user=Depends(browser_user)):
        return vault.inspect_capture(user["id"], token)

    @app.put("/v1/vault/captures/{token}", tags=["vault"])
    def submit_vault_capture(
        data: VaultCaptureSubmit,
        token: str,
        user=Depends(browser_user),
    ):
        return vault.submit_capture(user["id"], token, data.value)

    @app.get("/v1/vault", tags=["vault"])
    def vault_entries(user=Depends(vault_user)):
        return {"items": vault.list(user)}

    @app.get("/v1/vault/{name}", tags=["vault"])
    def read_vault_entry(
        name: str = Path(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$"),
        user=Depends(vault_user),
    ):
        return vault.get(user, name)

    @app.put("/v1/vault/{name}", tags=["vault"])
    def set_vault_entry(
        data: VaultInput,
        name: str = Path(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$"),
        user=Depends(browser_user),
    ):
        return vault.set(user["id"], name, data.value, data.description)

    @app.delete("/v1/vault/{name}", status_code=204, tags=["vault"])
    def delete_vault_entry(
        name: str = Path(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$"),
        user=Depends(browser_user),
    ):
        vault.delete(user["id"], name)

    @app.post(
        "/v1/files",
        status_code=201,
        tags=["files"],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
    )
    async def upload_file(
        request: Request,
        filename: str = Query(default="file", min_length=1, max_length=255),
        user=Depends(owner),
        db=Depends(store),
    ):
        return await files.upload(request, db, user, filename)

    @app.get("/v1/files/{id}", tags=["files"])
    def download_file(id: str, user=Depends(owner), db=Depends(store)):
        record = db.get(user, id)
        if record["kind"] != "file" or not files.path(id).is_file():
            raise NotFound()
        return FileResponse(
            files.path(id),
            media_type="application/octet-stream",
            filename=record["title"],
            content_disposition_type="attachment",
        )

    def remove_record(db, user, id):
        with db.lock:
            record = db.get(user, id)
            db.delete(user, id)
            if record["kind"] == "file":
                files.path(id).unlink(missing_ok=True)

    @app.delete("/v1/files/{id}", status_code=204, tags=["files"])
    def delete_file(id: str, user=Depends(owner), db=Depends(store)):
        with db.lock:
            if db.get(user, id)["kind"] != "file":
                raise NotFound()
            remove_record(db, user, id)

    @app.get("/health", tags=["service"])
    def health():
        return {"status": "ok"}

    @app.get("/v1/events", tags=["service"])
    async def events(
        request: Request,
        after: int = Query(default=0, ge=0, le=9223372036854775807),
        seconds: int = Query(default=25, ge=1, le=60),
        user=Depends(owner), db=Depends(store),
    ):
        last_id = request.headers.get("Last-Event-ID")
        if last_id is not None:
            try:
                after = int(last_id)
                if not 0 <= after <= 9223372036854775807:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, "Last-Event-ID must be a nonnegative integer") from None

        async def stream():
            cursor = after
            deadline = time.monotonic() + seconds
            heartbeat = 0
            yield "retry: 1000\n\n"
            while time.monotonic() < deadline:
                if await request.is_disconnected():
                    return
                # Revoked credentials and expired/logged-out sessions must lose live access too.
                credentials = await auth(request)
                try:
                    current = await anyio.to_thread.run_sync(owner, request, credentials)
                except HTTPException:
                    return
                if current != user:
                    return
                batch = await anyio.to_thread.run_sync(db.events, user, cursor)
                for event in batch:
                    cursor = event["id"]
                    payload = json.dumps(event["data"], ensure_ascii=False)
                    yield f"id: {cursor}\nevent: {event['event']}\ndata: {payload}\n\n"
                if time.monotonic() >= heartbeat:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic() + 10
                if not batch:
                    await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={
            "Cache-Control": "no-store", "X-Accel-Buffering": "no",
        })

    @app.get("/v1/me", tags=["service"])
    def me(request: Request, user=Depends(owner)):
        return {
            "user_id": user,
            "embedding_model": embedder.model_name,
            "vault_access": bool(request.state.vault_access),
            "agent": {
                "id": request.state.agent_id,
                "name": request.state.agent_name,
                "transport": request.state.agent_transport,
            },
        }

    @app.get("/v1/agents", tags=["agent messages"])
    def agents(request: Request, user=Depends(owner), db=Depends(store)):
        return {
            "self": {
                "id": request.state.agent_id,
                "name": request.state.agent_name,
                "transport": request.state.agent_transport,
            },
            "items": db.list_agents(user),
        }

    @app.post(
        "/v1/agent-messages",
        status_code=201,
        tags=["agent messages"],
        responses={
            200: {"description": "Previously queued message (idempotent retry)"},
            409: {"description": "Client request ID reused with different content"},
        },
    )
    def send_agent_message(
        data: AgentMessageInput,
        request: Request,
        user=Depends(owner),
        db=Depends(store),
    ):
        try:
            message, created = db.send_message(
                user, request.state.agent_id, request.state.agent_name, data
            )
        except DuplicateRequestConflict:
            raise HTTPException(
                409, "client_request_id already used with different content"
            ) from None
        return JSONResponse(
            status_code=201 if created else 200,
            content=message,
            headers={"Location": f"/v1/agent-messages/{message['id']}"},
        )

    @app.get("/v1/agent-messages/inbox", tags=["agent messages"])
    def agent_message_inbox(
        request: Request,
        after: int = Query(default=0, ge=0, le=9223372036854775807),
        limit: int = Query(default=50, ge=1, le=100),
        status: Literal["queued", "delivered", "read", "acked"] | None = None,
        user=Depends(owner),
        db=Depends(store),
    ):
        items = db.inbox_messages(user, request.state.agent_id, after, limit, status)
        cursor = items[-1]["sequence"] if items else after
        return {"items": items, "cursor": cursor, "limit": limit}

    @app.get("/v1/agent-messages/sent", tags=["agent messages"])
    def agent_message_sent(
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user=Depends(owner),
        db=Depends(store),
    ):
        return {
            "items": db.sent_messages(user, request.state.agent_id, limit, offset),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/v1/agent-messages/stream", tags=["agent messages"])
    async def agent_message_stream(
        request: Request,
        after: int = Query(default=0, ge=0, le=9223372036854775807),
        seconds: int = Query(default=25, ge=1, le=60),
        user=Depends(owner),
        db=Depends(store),
    ):
        last_id = request.headers.get("Last-Event-ID")
        if last_id is not None:
            try:
                after = int(last_id)
                if not 0 <= after <= 9223372036854775807:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, "Last-Event-ID must be a nonnegative integer") from None
        recipient = request.state.agent_id

        async def stream_messages():
            cursor = after
            deadline = time.monotonic() + seconds
            heartbeat = 0
            yield "retry: 1000\n\n"
            while time.monotonic() < deadline:
                if await request.is_disconnected():
                    return
                credentials = await auth(request)
                try:
                    current = await anyio.to_thread.run_sync(owner, request, credentials)
                except HTTPException:
                    return
                if current != user or request.state.agent_id != recipient:
                    return
                batch = await anyio.to_thread.run_sync(
                    db.inbox_messages, user, recipient, cursor, 100, None
                )
                for message in batch:
                    cursor = message["sequence"]
                    payload = json.dumps(message, ensure_ascii=False)
                    yield f"id: {cursor}\nevent: agent.message\ndata: {payload}\n\n"
                if time.monotonic() >= heartbeat:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic() + 10
                if not batch:
                    await asyncio.sleep(0.5)

        return StreamingResponse(
            stream_messages(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.get("/v1/agent-messages/{id}", tags=["agent messages"])
    def agent_message(id: str, request: Request, user=Depends(owner), db=Depends(store)):
        return db.get_message(user, request.state.agent_id, id)

    @app.post("/v1/agent-messages/{id}/ack", tags=["agent messages"])
    def acknowledge_agent_message(
        id: str,
        data: AgentMessageAck,
        request: Request,
        user=Depends(owner),
        db=Depends(store),
    ):
        return db.ack_message(user, request.state.agent_id, id, data.status)

    def vectors_for(keywords):
        try:
            return embedder.keywords(keywords)
        except Exception:
            log.exception("Keyword embedding failed")
            raise HTTPException(503, "Keyword embedding unavailable; nothing was saved") from None

    def ingest(db, user, kind, data):
        if kind == "document" and data.file_id:
            if db.get(user, data.file_id)["kind"] != "file":
                raise NotFound()
        vectors = vectors_for(data.keywords)
        if kind == "entity":
            content, title, subtype = data.description, data.name, data.entity_type
        elif kind == "document":
            content, title, subtype = data.content, data.title, "text"
        else:
            content, title, subtype = data.content, data.content[:100], data.kind
        security = prepare_record_security(title, content, data.provenance)
        return db.insert(
            user,
            kind,
            content,
            title,
            data.source,
            data.tags,
            subtype,
            data.keywords,
            data.metadata,
            vectors,
            file_id=(data.file_id or "") if kind == "document" else "",
            security=security,
        )

    @app.post(
        "/v1/feature-requests",
        status_code=201,
        tags=["feature requests"],
        responses={
            200: {"description": "Previously received request (idempotent retry)"},
            409: {"description": "Client request ID reused with different content"},
        },
    )
    def submit_feature_request(data: FeatureRequestInput, user=Depends(owner), db=Depends(store)):
        try:
            record, created = db.add_feature_request(user, data)
        except DuplicateRequestConflict:
            raise HTTPException(
                409, "client_request_id already used with different content"
            ) from None
        return JSONResponse(
            status_code=201 if created else 200,
            content=record,
            headers={"Location": f"/v1/feature-requests/{record['id']}"},
        )

    @app.get("/v1/feature-requests", tags=["feature requests"])
    def feature_requests(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user=Depends(owner),
        db=Depends(store),
    ):
        return {
            "items": db.list_feature_requests(user, limit, offset),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/v1/feature-requests/{id}", tags=["feature requests"])
    def feature_request(id: str, user=Depends(owner), db=Depends(store)):
        return db.get_feature_request(user, id)

    def admin_request_record(record):
        requester = accounts.user(record["owner_id"])
        return {
            **record,
            "requester": (
                {"name": requester["name"], "email": requester["email"]}
                if requester
                else {"name": "Legacy workspace", "email": ""}
            ),
        }

    @app.get("/v1/admin/feature-requests", tags=["admin"])
    def admin_feature_requests(
        status: Literal[
            "received", "reviewing", "planned", "in_progress", "completed", "declined"
        ]
        | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        _admin=Depends(admin_user),
        db=Depends(store),
    ):
        counts = {
            name: 0
            for name in (
                "received",
                "reviewing",
                "planned",
                "in_progress",
                "completed",
                "declined",
            )
        }
        counts.update(db.feature_request_status_counts())
        return {
            "items": [
                admin_request_record(record)
                for record in db.admin_feature_requests(status or "", limit, offset)
            ],
            "counts": counts,
            "total": sum(counts.values()),
            "limit": limit,
            "offset": offset,
        }

    @app.patch("/v1/admin/feature-requests/{owner_id}/{id}", tags=["admin"])
    def admin_update_feature_request(
        owner_id: str,
        id: str,
        data: FeatureRequestUpdate,
        _admin=Depends(admin_user),
        db=Depends(store),
    ):
        record = db.update_feature_request(owner_id, id, data)
        return admin_request_record({**record, "owner_id": owner_id})

    @app.post("/v1/memories", status_code=201, tags=["memories"])
    def add_memory(data: MemoryInput, user=Depends(owner), db=Depends(store)):
        return ingest(db, user, "memory", data)

    @app.post("/v1/documents", status_code=201, tags=["documents"])
    def add_document(data: DocumentInput, user=Depends(owner), db=Depends(store)):
        return ingest(db, user, "document", data)

    @app.post("/v1/entities", status_code=201, tags=["entities"])
    def add_entity(data: EntityInput, user=Depends(owner), db=Depends(store)):
        return ingest(db, user, "entity", data)

    @app.put("/v1/records/{id}/keywords", tags=["memories"])
    def update_keywords(id: str, data: KeywordUpdate, user=Depends(owner), db=Depends(store)):
        db.get(user, id)
        return db.update_keywords(user, id, data.keywords, vectors_for(data.keywords))

    @app.patch("/v1/records/{id}", tags=["memories"])
    def update_record(id: str, data: RecordUpdate, user=Depends(owner), db=Depends(store)):
        vectors = vectors_for(data.keywords) if data.keywords is not None else None
        return db.update_record(user, id, data, vectors)

    @app.patch("/v1/records/{id}/security", tags=["memories"])
    def update_record_security(
        id: str, data: RecordSecurityUpdate, user=Depends(owner), db=Depends(store)
    ):
        return db.update_security(user, id, data)

    @app.post("/v1/records/{id}/archive", tags=["memories"])
    def archive_record(id: str, data: RecordArchive, user=Depends(owner), db=Depends(store)):
        return db.archive(user, id, data.expected_version, data.reason)

    @app.post("/v1/records/{id}/restore", tags=["memories"])
    def restore_record(id: str, data: RecordArchive, user=Depends(owner), db=Depends(store)):
        return db.restore(user, id, data.expected_version, data.reason)

    @app.get("/v1/trash", tags=["memories"])
    def trash(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user=Depends(owner),
        db=Depends(store),
    ):
        return {"items": db.archived(user, limit, offset), "limit": limit, "offset": offset}

    @app.get("/v1/quarantine", tags=["memories"])
    def quarantine(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user=Depends(owner),
        db=Depends(store),
    ):
        return {"items": db.quarantined(user, limit, offset), "limit": limit, "offset": offset}

    @app.post("/v1/records/merge", tags=["memories"])
    def merge_records(data: RecordMerge, user=Depends(owner), db=Depends(store)):
        return db.merge(user, data)

    @app.get("/v1/stats", tags=["memories"])
    def stats(user=Depends(owner), db=Depends(store)):
        return db.stats(user)

    @app.get("/v1/records", tags=["memories"])
    def records(
        kind: Literal["memory", "document", "entity", "file"] | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        include_untrusted: bool = False,
        include_quarantined: bool = False,
        user=Depends(owner),
        db=Depends(store),
    ):
        if include_quarantined and not include_untrusted:
            raise HTTPException(422, "include_quarantined requires include_untrusted")
        return {
            "items": db.list(
                user,
                kind,
                limit,
                offset,
                include_untrusted,
                include_quarantined,
            ),
            "limit": limit,
            "offset": offset,
        }

    @app.get("/v1/records/{id}", tags=["memories"])
    def get_record(id: str, user=Depends(owner), db=Depends(store)):
        return db.get(user, id)

    @app.delete("/v1/records/{id}", status_code=204, tags=["memories"])
    def delete_record(id: str, user=Depends(owner), db=Depends(store)):
        remove_record(db, user, id)

    @app.post("/v1/relations", status_code=201, tags=["graph"])
    def add_relation(data: RelationInput, user=Depends(owner), db=Depends(store)):
        try:
            return db.link(user, data)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.get("/v1/relations", tags=["graph"])
    def relations(
        status: Literal["active", "retracted", "all"] = "active",
        user=Depends(owner),
        db=Depends(store),
    ):
        return {"items": db.relations(user, status)}

    @app.patch("/v1/relations/{id}", tags=["graph"])
    def update_relation(id: str, data: RelationUpdate, user=Depends(owner), db=Depends(store)):
        return db.update_link(user, id, data)

    @app.get("/v1/graph/{id}", tags=["graph"])
    def graph(
        id: str,
        depth: int = Query(default=1, ge=0, le=2),
        include_untrusted: bool = False,
        include_quarantined: bool = False,
        user=Depends(owner),
        db=Depends(store),
    ):
        if include_quarantined and not include_untrusted:
            raise HTTPException(422, "include_quarantined requires include_untrusted")
        seed = db.get(user, id)
        result = db.neighborhood(
            user, [id], depth, include_untrusted, include_quarantined
        )
        result["nodes"].insert(0, seed)
        return result

    @app.post("/v1/search", tags=["retrieval"])
    def search(data: SearchInput, user=Depends(owner), db=Depends(store)):
        try:
            # A consistent snapshot prevents concurrent index replacement during scoring.
            with db.lock:
                return retrieve(db, embedder, user, data)
        except (NotFound, Conflict):
            raise
        except Exception:
            log.exception("Retrieval failed")
            raise HTTPException(503, "Retrieval unavailable") from None

    mount_web(app, settings.web_dir)
    return app
