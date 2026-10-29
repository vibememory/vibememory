"""Opaque raw-byte storage. No multipart parsing, document extraction, or embedding."""

import hashlib
from pathlib import Path
from uuid import uuid4

import anyio
from fastapi import HTTPException, Request


class FileStorage:
    def __init__(self, root: Path, max_bytes: int):
        self.root = root
        self.max_bytes = max_bytes
        root.mkdir(parents=True, exist_ok=True)

    def path(self, id):
        # IDs are server-generated, never a client filename or an arbitrary path.
        from uuid import UUID

        try:
            canonical = str(UUID(id))
        except ValueError:
            raise HTTPException(404, "File not found") from None
        return self.root / (canonical + ".blob")

    async def upload(self, request: Request, db, owner, filename):
        if (
            request.headers.get("content-type", "").split(";")[0].strip().lower()
            != "application/octet-stream"
        ):
            raise HTTPException(
                415,
                "Send raw bytes as application/octet-stream; multipart/form-data is not supported",
            )
        length = request.headers.get("content-length")
        if length is not None:
            try:
                length = int(length)
            except ValueError:
                raise HTTPException(400, "Invalid Content-Length") from None
            if length < 0:
                raise HTTPException(400, "Invalid Content-Length")
            if length > self.max_bytes:
                raise HTTPException(413, "File exceeds upload size limit")
        id = str(uuid4())
        path = self.path(id)
        temporary = path.with_suffix(".part")
        size, digest, committed = 0, hashlib.sha256(), False
        try:
            async with await anyio.open_file(temporary, "xb") as target:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise HTTPException(413, "File exceeds upload size limit")
                    digest.update(chunk)
                    await target.write(chunk)
            if length is not None and size != length:
                raise HTTPException(400, "Body size differs from Content-Length")
            temporary.replace(path)
            result = await anyio.to_thread.run_sync(
                lambda: db.insert(
                    owner,
                    "file",
                    "",
                    filename,
                    "",
                    [],
                    "application/octet-stream",
                    [],
                    {"size_bytes": size, "sha256": digest.hexdigest()},
                    [],
                    record_id=id,
                )
            )
            committed = True
            return result
        finally:
            temporary.unlink(missing_ok=True)
            if not committed:
                path.unlink(missing_ok=True)
