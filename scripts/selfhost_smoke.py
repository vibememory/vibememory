"""Smoke-test a disposable self-hosted deployment, including container replacement persistence."""

import argparse
import hashlib
import http.cookiejar
import json
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--phase", choices=["create", "verify"], default="create")
    parser.add_argument("--state-file", type=Path, default=Path("/tmp/vibe-selfhost-smoke.json"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def call(path, method="GET", data=None, key=None, binary=False, expected=200):
        headers = {"User-Agent": "VibeMemorySelfHostSmoke/1.0", "Origin": base}
        if key:
            headers["Authorization"] = "Bearer " + key
        if data is not None:
            headers["Content-Type"] = "application/octet-stream" if binary else "application/json"
        request = urllib.request.Request(
            base + path,
            method=method,
            headers=headers,
            data=data if binary else (json.dumps(data).encode() if data is not None else None),
        )
        try:
            response = opener.open(request, timeout=180)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read()
            assert response.status == expected, (path, response.status, body[:300])
            return body if binary else (json.loads(body) if body else None)

    for _ in range(120):
        try:
            if call("/health")["status"] == "ok":
                break
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.5)
    else:
        raise AssertionError("Server did not become ready")

    for path in (
        "/",
        "/login",
        "/console",
        "/assets/console.js",
        "/downloads/vibe-memory-skill.zip",
    ):
        with opener.open(base + path, timeout=20) as response:
            assert response.status == 200
            assert response.read()

    if args.phase == "create":
        assert call("/v1/records", expected=401)
        user = call(
            "/auth/signup",
            "POST",
            {
                "name": "Self-host smoke",
                "email": "smoke-" + uuid4().hex + "@example.invalid",
                "password": secrets.token_urlsafe(24),
            },
        )["user"]
        key = call("/auth/api-keys", "POST", {"name": "self-host-agent"}, expected=201)["key"]
        memory = call(
            "/v1/memories",
            "POST",
            {"content": "I prefer tea", "keywords": ["tea", "beverage"]},
            key,
            expected=201,
        )
        raw = bytes(range(256)) * 8
        file = call("/v1/files?filename=smoke.bin", "POST", raw, key, binary=True, expected=201)
        file = json.loads(file)
        document = call(
            "/v1/documents",
            "POST",
            {
                "title": "Agent prepared notes",
                "file_id": file["id"],
                "keywords": ["Python"],
                "metadata": {"summary": "Written by the agent, not the server"},
            },
            key,
            expected=201,
        )
        relation = call(
            "/v1/relations",
            "POST",
            {
                "source_id": memory["id"],
                "target_id": document["id"],
                "relation": "RELATED_TO",
                "reason": "Self-hosted persistence test",
            },
            key,
            expected=201,
        )
        assert (
            call("/v1/search", "POST", {"keywords": ["tea"], "limit": 1}, key)["hits"][0]["id"]
            == memory["id"]
        )
        feature = call(
            "/v1/feature-requests",
            "POST",
            {
                "title": "Self-host smoke",
                "description": "Integration verification",
                "agent_name": "selfhost-smoke",
                "client_request_id": "smoke-feedback-v1",
            },
            key,
            expected=201,
        )
        state = dict(
            user_id=user["id"],
            key=key,
            memory_id=memory["id"],
            document_id=document["id"],
            file_id=file["id"],
            relation_id=relation["id"],
            feature_id=feature["id"],
            file_sha256=hashlib.sha256(raw).hexdigest(),
        )
        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        args.state_file.touch(mode=0o600, exist_ok=True)
        args.state_file.chmod(0o600)
        args.state_file.write_text(json.dumps(state))
        call("/auth/logout", "POST", expected=204)
        print(
            "PASS: self-hosted console, account, agent key, keyword search, raw bytes, graph, feedback. State saved for restart verification (no key printed)."
        )
    else:
        state = json.loads(args.state_file.read_text())
        key = state["key"]
        assert call("/v1/me", key=key)["user_id"] == state["user_id"]
        assert call("/v1/records/" + state["memory_id"], key=key)["content"] == "I prefer tea"
        assert call("/v1/records/" + state["document_id"], key=key)["file_id"] == state["file_id"]
        raw = call("/v1/files/" + state["file_id"], key=key, binary=True)
        assert hashlib.sha256(raw).hexdigest() == state["file_sha256"]
        graph = call("/v1/graph/" + state["memory_id"], key=key)
        assert graph["relations"][0]["id"] == state["relation_id"]
        assert call("/v1/feature-requests/" + state["feature_id"], key=key)["status"] == "received"
        assert (
            call("/v1/search", "POST", {"keywords": ["tea"], "limit": 1}, key)["hits"][0]["id"]
            == state["memory_id"]
        )
        for id in [state["document_id"], state["file_id"], state["memory_id"]]:
            call("/v1/records/" + id, "DELETE", key=key, expected=204)
        args.state_file.unlink()
        print(
            "PASS: user/key, graph, file bytes, metadata, feedback and keyword index survive process/container replacement."
        )


if __name__ == "__main__":
    main()
