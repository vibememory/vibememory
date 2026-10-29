import asyncio
import hashlib
import hmac
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

import anyio
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import COOKIE, SESSION_SECONDS, AuthStore, Credentials, KeyInput, Signup
from .config import Settings
from .embeddings import Embedder
from .files import FileStorage
from .models import (
    DocumentInput,
    EntityInput,
    FeatureRequestInput,
    KeywordUpdate,
    MemoryInput,
    RelationInput,
    RelationUpdate,
    SearchInput,
)
from .retrieval import retrieve
from .store import Conflict, DuplicateRequestConflict, FileInUse, NotFound, Store
from .web import mount_web

log = logging.getLogger(__name__)


def create_app(settings=None, embedder=None):
    settings = settings or Settings()
    settings.validate_keys()
    embedder = embedder or Embedder(settings.embedding_model, settings.embedding_cache)

    accounts = AuthStore(settings.data_dir / "auth.sqlite")
    files = FileStorage(settings.data_dir / "files", settings.upload_max_bytes)

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = Store(settings.data_dir / "graph", embedder.model_name)
        yield
        app.state.store.close()

    app = FastAPI(
        title="Vibe Memory",
        version="0.6.0",
        lifespan=lifespan,
        description="Agent-authored memory graph and keyword-only vector index. No inference or document processing.",
    )
    auth = HTTPBearer(auto_error=False)
    key_hashes = [
        (hashlib.sha256(key.encode()).digest(), owner) for key, owner in settings.api_keys.items()
    ]

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

    def owner(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(auth)):
        if credentials and credentials.scheme.lower() == "bearer":
            supplied = hashlib.sha256(credentials.credentials.encode()).digest()
            for expected, user in key_hashes:
                if hmac.compare_digest(expected, supplied):
                    return user
            dynamic_owner = accounts.user_for_key(credentials.credentials)
            if dynamic_owner:
                return dynamic_owner
        elif not request.headers.get("Authorization"):
            session_user = accounts.user_for_session(request.cookies.get(COOKIE))
            if session_user:
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    check_origin(request)
                return session_user["id"]
        raise HTTPException(
            401, "Invalid or missing API key", headers={"WWW-Authenticate": "Bearer"}
        )

    def store(request: Request):
        return request.app.state.store

    @app.middleware("http")
    async def no_private_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/v1/", "/auth/")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def signed_in(user):
        response = JSONResponse({"user": user})
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
        return {"user": user}

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
        return accounts.create_key(user["id"], data.name)

    @app.delete("/auth/api-keys/{id}", status_code=204, tags=["account"])
    def revoke_api_key(id: str, user=Depends(browser_user)):
        accounts.revoke_key(user["id"], id)

    @app.exception_handler(NotFound)
    async def missing(request, error):
        return JSONResponse(status_code=404, content={"detail": "Record or relationship not found"})

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse(
            status_code=409, content={"detail": "Version conflict; reload the relationship"}
        )

    @app.exception_handler(FileInUse)
    async def file_in_use(request, error):
        return JSONResponse(
            status_code=409,
            content={"detail": "File is referenced by a document; delete the document first"},
        )

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
    def me(user=Depends(owner)):
        return {"user_id": user, "embedding_model": embedder.model_name}

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

    @app.get("/v1/stats", tags=["memories"])
    def stats(user=Depends(owner), db=Depends(store)):
        return db.stats(user)

    @app.get("/v1/records", tags=["memories"])
    def records(
        kind: Literal["memory", "document", "entity", "file"] | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user=Depends(owner),
        db=Depends(store),
    ):
        return {"items": db.list(user, kind, limit, offset), "limit": limit, "offset": offset}

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
        id: str, depth: int = Query(default=1, ge=0, le=2), user=Depends(owner), db=Depends(store)
    ):
        seed = db.get(user, id)
        result = db.neighborhood(user, [id], depth)
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
