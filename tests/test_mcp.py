import base64
import hashlib
import re
from urllib.parse import parse_qs, urlsplit

from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "http://testserver"
RESOURCE = ORIGIN + "/mcp"
REDIRECT = "https://client.example/oauth/callback"


def challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def signup(client, email="mcp@example.invalid"):
    response = client.post(
        "/auth/signup",
        headers={"Origin": ORIGIN},
        json={"name": "MCP User", "email": email, "password": "long-enough-password"},
    )
    assert response.status_code == 200, response.text


def register(client, name="Claude"):
    response = client.post(
        "/oauth/register",
        json={
            "client_name": name,
            "redirect_uris": [REDIRECT],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def authorize(client, registration, scopes="memory:read memory:write feature:write"):
    verifier = "p" * 64
    params = {
        "response_type": "code",
        "client_id": registration["client_id"],
        "redirect_uri": REDIRECT,
        "scope": scopes,
        "state": "state-value",
        "resource": RESOURCE,
        "code_challenge": challenge(verifier),
        "code_challenge_method": "S256",
    }
    consent = client.get("/oauth/authorize", params=params, follow_redirects=False)
    assert consent.status_code == 200, consent.text
    assert registration["client_name"] in consent.text
    consent_token = re.search(
        r'name="consent_token" value="([0-9a-f]{64})"', consent.text
    )
    assert consent_token
    approved = client.post(
        "/oauth/authorize",
        data={**params, "decision": "approve", "consent_token": consent_token.group(1)},
        follow_redirects=False,
    )
    assert approved.status_code == 303, approved.text
    redirect = urlsplit(approved.headers["location"])
    assert redirect.scheme + "://" + redirect.netloc + redirect.path == REDIRECT
    query = parse_qs(redirect.query)
    assert query["state"] == ["state-value"]
    return query["code"][0], verifier


def token(client, registration, code, verifier):
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": registration["client_id"],
            "redirect_uri": REDIRECT,
            "code": code,
            "code_verifier": verifier,
            "resource": RESOURCE,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def mcp(client, access_token, id_value, method, params=None):
    payload = {"jsonrpc": "2.0", "id": id_value, "method": method}
    if params is not None:
        payload["params"] = params
    response = client.post(
        "/mcp",
        headers={"Authorization": "Bearer " + access_token},
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_chatgpt_login_redirect_and_consent_round_trip(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN})
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        registration = register(client, "ChatGPT")
        verifier = "r" * 64
        params = {
            "response_type": "code",
            "client_id": registration["client_id"],
            "redirect_uri": REDIRECT,
            "scope": "feature:write memory:read memory:write",
            "state": "chatgpt-state",
            "resource": RESOURCE,
            "code_challenge": challenge(verifier),
            "code_challenge_method": "S256",
            "ui_locales": "ko-KR",
        }
        start = client.get("/oauth/authorize", params=params, follow_redirects=False)
        assert start.status_code == 302
        login_redirect = urlsplit(start.headers["location"])
        assert login_redirect.path == "/login"
        next_path = parse_qs(login_redirect.query)["next"][0]
        assert next_path.startswith("/oauth/authorize?")

        signup(client, "chatgpt-redirect@example.invalid")
        consent = client.get(next_path)
        assert consent.status_code == 200, consent.text
        assert (
            "form-action 'self' https://client.example"
            in consent.headers["content-security-policy"]
        )
        token_match = re.search(
            r'name="consent_token" value="([0-9a-f]{64})"', consent.text
        )
        assert token_match

        rejected = client.post(
            "/oauth/authorize",
            data={**params, "decision": "approve", "consent_token": "tampered"},
            follow_redirects=False,
        )
        assert rejected.status_code == 403

        approved = client.post(
            "/oauth/authorize",
            data={
                **params,
                "decision": "approve",
                "consent_token": token_match.group(1),
            },
            follow_redirects=False,
        )
        assert approved.status_code == 303, approved.text
        callback = urlsplit(approved.headers["location"])
        assert callback.scheme + "://" + callback.netloc + callback.path == REDIRECT
        callback_query = parse_qs(callback.query)
        assert callback_query["state"] == ["chatgpt-state"]
        assert callback_query["code"][0].startswith("vmc_code_")


def test_mcp_oauth_pkce_tools_and_revocation(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN})
    embedder = SpyEmbedder()
    with TestClient(create_app(settings, embedder)) as client:
        metadata = client.get("/.well-known/oauth-protected-resource/mcp").json()
        assert metadata["resource"] == RESOURCE
        assert metadata["authorization_servers"] == [ORIGIN]
        server = client.get("/.well-known/oauth-authorization-server").json()
        assert server["code_challenge_methods_supported"] == ["S256"]
        assert server["registration_endpoint"] == ORIGIN + "/oauth/register"

        unauthenticated = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert unauthenticated.status_code == 401
        assert "oauth-protected-resource/mcp" in unauthenticated.headers["www-authenticate"]

        signup(client)
        registration = register(client)
        code, verifier = authorize(client, registration)
        credentials = token(client, registration, code, verifier)
        assert credentials["access_token"].startswith("vma_")
        assert credentials["refresh_token"].startswith("vmr_")
        assert (
            client.post(
                "/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": registration["client_id"],
                    "redirect_uri": REDIRECT,
                    "code": code,
                    "code_verifier": verifier,
                    "resource": RESOURCE,
                },
            ).status_code
            == 400
        )

        initialized = mcp(
            client,
            credentials["access_token"],
            1,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        )
        assert initialized["result"]["serverInfo"]["name"] == "vibe-memory"
        assert "timestamps use UTC" in initialized["result"]["instructions"]

        tools = mcp(client, credentials["access_token"], 2, "tools/list")["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert {
            "profile_get",
            "memory_search",
            "memory_create",
            "entity_create",
            "document_create",
            "relation_create",
            "record_update",
            "record_archive",
            "record_restore",
            "record_merge",
            "relation_update",
            "events_poll",
            "feature_requests_list",
            "feature_request_submit",
        }.issubset(names)
        assert "vault_get" not in names and "file_upload" not in names

        created = mcp(
            client,
            credentials["access_token"],
            3,
            "tools/call",
            {
                "name": "memory_create",
                "arguments": {
                    "content": "사용자는 녹차를 선호한다",
                    "kind": "preference",
                    "keywords": ["녹차", "음료 선호"],
                    "source": "Claude MCP",
                },
            },
        )["result"]["structuredContent"]["record"]
        assert embedder.calls == [["녹차", "음료 선호"]]

        found = mcp(
            client,
            credentials["access_token"],
            4,
            "tools/call",
            {
                "name": "memory_search",
                "arguments": {"keywords": ["녹차"], "scope": "memories", "limit": 5},
            },
        )["result"]["structuredContent"]
        assert found["hits"][0]["id"] == created["id"]
        assert embedder.calls[-1] == ["녹차"]

        events = mcp(
            client,
            credentials["access_token"],
            5,
            "tools/call",
            {"name": "events_poll", "arguments": {"after": 0}},
        )["result"]["structuredContent"]
        assert events["items"][0]["data"] == {
            "record_id": created["id"],
            "kind": "memory",
        }

        connections = client.get("/auth/mcp-connections").json()
        assert connections["server_url"] == RESOURCE
        assert connections["items"][0]["client_name"] == "Claude"
        revoked = client.delete(
            "/auth/mcp-connections/" + registration["client_id"],
            headers={"Origin": ORIGIN},
        )
        assert revoked.status_code == 204
        assert (
            client.post(
                "/mcp",
                headers={"Authorization": "Bearer " + credentials["access_token"]},
                json={"jsonrpc": "2.0", "id": 6, "method": "ping"},
            ).status_code
            == 401
        )


def test_mcp_read_only_scope_and_oauth_validation(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN})
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        signup(client, "readonly@example.invalid")
        assert (
            client.post(
                "/oauth/register",
                json={
                    "client_name": "Bad",
                    "redirect_uris": ["http://evil.example/callback"],
                },
            ).status_code
            == 400
        )
        registration = register(client, "ChatGPT")
        code, verifier = authorize(client, registration, "memory:read")
        credentials = token(client, registration, code, verifier)
        tools = mcp(client, credentials["access_token"], 1, "tools/list")["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert "memory_search" in names
        assert "memory_create" not in names
        denied = mcp(
            client,
            credentials["access_token"],
            2,
            "tools/call",
            {
                "name": "memory_create",
                "arguments": {"content": "no", "keywords": ["no"]},
            },
        )
        assert denied["result"]["isError"] is True
        assert "memory:write" in denied["result"]["content"][0]["text"]

        refreshed = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registration["client_id"],
                "refresh_token": credentials["refresh_token"],
                "resource": RESOURCE,
                "scope": "memory:read",
            },
        )
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["refresh_token"] != credentials["refresh_token"]
        replay = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registration["client_id"],
                "refresh_token": credentials["refresh_token"],
                "resource": RESOURCE,
            },
        )
        assert replay.status_code == 400
