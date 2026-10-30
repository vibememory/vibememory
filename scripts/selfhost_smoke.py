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

from vibe_memory.auth import totp_code


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
        password = secrets.token_urlsafe(24)
        user = call(
            "/auth/signup",
            "POST",
            {
                "name": "Self-host smoke",
                "email": "smoke-" + uuid4().hex + "@example.invalid",
                "password": password,
            },
        )["user"]
        key = call(
            "/auth/api-keys",
            "POST",
            {"name": "self-host-agent", "vault_access": True},
            expected=201,
        )["key"]
        vault = call(
            "/v1/vault/SELFHOST_SMOKE",
            "PUT",
            {"value": "selfhost-vault-secret", "description": "restart verification"},
        )
        assert vault["name"] == "SELFHOST_SMOKE" and "value" not in vault
        assert call("/v1/vault/SELFHOST_SMOKE", key=key)["value"] == "selfhost-vault-secret"
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
        batch_entity_payload = {
            "items": [
                {
                    "client_request_id": "selfhost-batch-entity-v1",
                    "name": "Self-host batch entity",
                    "entity_type": "Test",
                    "description": "PostgreSQL idempotency verification",
                    "keywords": ["self-host", "batch"],
                }
            ]
        }
        batch_entity = call("/v1/entities/batch", "POST", batch_entity_payload, key)["items"][0]
        assert batch_entity["status"] == "created"
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
        setup = call("/auth/totp/setup", "POST", {"password": password})
        recovery_codes = call("/auth/totp/enable", "POST", {"code": totp_code(setup["secret"])})[
            "recovery_codes"
        ]
        assert len(recovery_codes) == 10
        state = dict(
            user_id=user["id"],
            email=user["email"],
            password=password,
            totp_secret=setup["secret"],
            key=key,
            memory_id=memory["id"],
            document_id=document["id"],
            file_id=file["id"],
            relation_id=relation["id"],
            feature_id=feature["id"],
            batch_entity_id=batch_entity["id"],
            file_sha256=hashlib.sha256(raw).hexdigest(),
        )
        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        args.state_file.touch(mode=0o600, exist_ok=True)
        args.state_file.chmod(0o600)
        args.state_file.write_text(json.dumps(state))
        call("/auth/logout", "POST", expected=204)
        print(
            "PASS: self-hosted console, account, TOTP, scoped agent key, encrypted Vault, keyword search, raw bytes, graph, feedback. State saved for restart verification (no secret printed)."
        )
    else:
        state = json.loads(args.state_file.read_text())
        key = state["key"]
        login = call(
            "/auth/login",
            "POST",
            {"email": state["email"], "password": state["password"]},
        )
        assert login["mfa_required"] is True
        assert (
            call(
                "/auth/login/otp",
                "POST",
                {
                    "challenge_token": login["challenge_token"],
                    "code": totp_code(state["totp_secret"]),
                },
            )["user"]["id"]
            == state["user_id"]
        )
        assert call("/auth/security")["totp_enabled"] is True
        assert call("/v1/me", key=key)["user_id"] == state["user_id"]
        assert call("/v1/records/" + state["memory_id"], key=key)["content"] == "I prefer tea"
        assert call("/v1/records/" + state["document_id"], key=key)["file_id"] == state["file_id"]
        raw = call("/v1/files/" + state["file_id"], key=key, binary=True)
        assert hashlib.sha256(raw).hexdigest() == state["file_sha256"]
        graph = call("/v1/graph/" + state["memory_id"], key=key)
        assert graph["relations"][0]["id"] == state["relation_id"]
        assert call("/v1/feature-requests/" + state["feature_id"], key=key)["status"] == "received"
        batch_retry = call(
            "/v1/entities/batch",
            "POST",
            {
                "items": [
                    {
                        "client_request_id": "selfhost-batch-entity-v1",
                        "name": "Self-host batch entity",
                        "entity_type": "Test",
                        "description": "PostgreSQL idempotency verification",
                        "keywords": ["self-host", "batch"],
                    }
                ]
            },
            key,
        )["items"][0]
        assert batch_retry["status"] == "existing"
        assert batch_retry["id"] == state["batch_entity_id"]
        assert call("/v1/vault/SELFHOST_SMOKE", key=key)["value"] == "selfhost-vault-secret"
        assert (
            call("/v1/search", "POST", {"keywords": ["tea"], "limit": 1}, key)["hits"][0]["id"]
            == state["memory_id"]
        )
        for id in [
            state["batch_entity_id"],
            state["document_id"],
            state["file_id"],
            state["memory_id"],
        ]:
            call("/v1/records/" + id, "DELETE", key=key, expected=204)
        args.state_file.unlink()
        print(
            "PASS: user/TOTP/key, encrypted Vault, graph, file bytes, metadata, feedback and keyword index survive process/container replacement."
        )


if __name__ == "__main__":
    main()
