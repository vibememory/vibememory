import asyncio
import hashlib

import pytest
from conftest import KEY_A, KEY_B, SpyEmbedder
from fastapi.testclient import TestClient
from starlette.requests import ClientDisconnect, Request

from vibe_memory.app import create_app
from vibe_memory.files import FileStorage

RAW = {"Content-Type": "application/octet-stream"}


def upload(client, content=b"\x00\xfffile\r\n", filename="original.bin"):
    response = client.post("/v1/files", params={"filename": filename}, content=content, headers=RAW)
    assert response.status_code == 201, response.text
    return response.json()


def test_raw_byte_roundtrip_metadata_and_no_embeddings(client, embedder):
    data = bytes(range(256)) * 1000
    record = upload(client, data, "../한글.bin")
    assert record["metadata"] == {
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    assert record["kind"] == "file" and record["keywords"] == []
    response = client.get("/v1/files/" + record["id"])
    assert response.content == data
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert not embedder.calls
    assert client.get("/v1/records/" + record["id"]).status_code == 200
    schema = client.get("/openapi.json").json()
    content = schema["paths"]["/v1/files"]["post"]["requestBody"]["content"]
    assert set(content) == {"application/octet-stream"}
    assert content["application/octet-stream"]["schema"]["format"] == "binary"


def test_reject_form_json_and_unauthenticated_upload(client, settings, embedder):
    assert client.post("/v1/files", files={"file": ("a.txt", b"hello")}).status_code == 415
    assert client.post("/v1/files", json={"file": "data"}).status_code == 415
    assert (
        client.post("/v1/files", content=b"data", headers={**RAW, "Authorization": ""}).status_code
        == 401
    )
    assert client.get("/v1/records").json()["items"] == []
    assert list((settings.data_dir / "files").iterdir()) == []
    assert not embedder.calls


def test_chunked_stream_limit_and_cleanup(settings):
    settings = settings.model_copy(update={"upload_max_bytes": 8})
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        client.headers["Authorization"] = "Bearer " + KEY_A
        # Generator uses Transfer-Encoding: chunked, without Content-Length.
        assert (
            client.post("/v1/files", content=iter([b"1234", b"56789"]), headers=RAW).status_code
            == 413
        )
        assert client.post("/v1/files", content=b"123456789", headers=RAW).status_code == 413
        assert (
            client.post(
                "/v1/files", content=b"12", headers={**RAW, "Content-Length": "3"}
            ).status_code
            == 400
        )
        assert list((settings.data_dir / "files").iterdir()) == []
        assert client.get("/v1/records").json()["items"] == []
        result = upload(client, iter([b"1234", b"5678"]))
        assert client.get("/v1/files/" + result["id"]).content == b"12345678"
        empty = upload(client, b"")
        assert empty["metadata"]["size_bytes"] == 0


def test_file_ownership_attachment_and_delete(client, embedder, settings):
    record = upload(client)
    client.headers["Authorization"] = "Bearer " + KEY_B
    assert client.get("/v1/files/" + record["id"]).status_code == 404
    assert client.delete("/v1/files/" + record["id"]).status_code == 404
    assert (
        client.post(
            "/v1/documents", json={"title": "not mine", "keywords": ["x"], "file_id": record["id"]}
        ).status_code
        == 404
    )
    assert not embedder.calls
    client.headers["Authorization"] = "Bearer " + KEY_A
    document = client.post(
        "/v1/documents",
        json={
            "title": "agent analyzed original",
            "file_id": record["id"],
            "keywords": ["차"],
            "metadata": {"summary": "agent-made summary"},
        },
    )
    assert document.status_code == 201, document.text
    document = document.json()
    assert document["file_id"] == record["id"]
    assert embedder.calls == [["차"]]
    assert client.delete("/v1/files/" + record["id"]).status_code == 409
    assert client.delete("/v1/records/" + record["id"]).status_code == 409
    assert client.delete("/v1/files/" + document["id"]).status_code == 404
    assert client.delete("/v1/records/" + document["id"]).status_code == 204
    assert client.delete("/v1/files/" + record["id"]).status_code == 204
    assert client.get("/v1/files/" + record["id"]).status_code == 404
    assert list((settings.data_dir / "files").iterdir()) == []


def test_disconnect_discards_partial_file(settings):
    storage = FileStorage(settings.data_dir / "files", 1024)
    messages = iter(
        [
            {"type": "http.request", "body": b"partial", "more_body": True},
            {"type": "http.disconnect"},
        ]
    )

    async def receive():
        return next(messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/files",
            "headers": [(b"content-type", b"application/octet-stream")],
        },
        receive,
    )
    with pytest.raises(ClientDisconnect):
        asyncio.run(storage.upload(request, None, "alice", "partial.bin"))
    assert list(storage.root.iterdir()) == []


def test_failed_graph_write_cleans_blob(client, settings, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("disk error")

    monkeypatch.setattr(client.app.state.store, "insert", fail)
    with pytest.raises(RuntimeError, match="disk error"):
        client.post("/v1/files", content=b"data", headers=RAW)
    assert list((settings.data_dir / "files").iterdir()) == []


def test_file_restart_persistence(settings):
    for index in range(2):
        with TestClient(create_app(settings, SpyEmbedder())) as client:
            client.headers["Authorization"] = "Bearer " + KEY_A
            if index == 0:
                record = upload(client, b"persist original bytes")
            else:
                assert client.get("/v1/files/" + record["id"]).content == b"persist original bytes"
                assert client.delete("/v1/records/" + record["id"]).status_code == 204
                assert list((settings.data_dir / "files").iterdir()) == []
