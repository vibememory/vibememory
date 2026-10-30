import base64
import hashlib
import re
import sqlite3
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
    consent_token = re.search(r'name="consent_token" value="([0-9a-f]{64})"', consent.text)
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
        token_match = re.search(r'name="consent_token" value="([0-9a-f]{64})"', consent.text)
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
            "auth_context",
            "capabilities_get",
            "permission_check",
            "profile_get",
            "memory_search",
            "memory_create",
            "entity_create",
            "entity_create_many",
            "document_create",
            "relation_create",
            "relation_create_many",
            "record_update",
            "record_update_many",
            "record_security_update",
            "record_archive",
            "record_restore",
            "record_merge",
            "relation_update",
            "context_bundle_get",
            "graph_audit",
            "graph_diff",
            "graph_apply",
            "events_poll",
            "quarantine_list",
            "feature_requests_list",
            "feature_request_submit",
            "agents_list",
            "message_inbox",
            "message_sent",
            "message_get",
            "message_send",
            "message_ack",
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

        bundle = mcp(
            client,
            credentials["access_token"],
            31,
            "tools/call",
            {
                "name": "context_bundle_get",
                "arguments": {"record_ids": [created["id"]], "byte_limit": 10000},
            },
        )["result"]["structuredContent"]
        assert bundle["llm_calls"] == 0
        assert bundle["items"][0]["id"] == created["id"]
        assert "content" not in bundle["items"][0]
        assert embedder.calls == [["녹차", "음료 선호"]]

        audit = mcp(
            client,
            credentials["access_token"],
            32,
            "tools/call",
            {"name": "graph_audit", "arguments": {}},
        )["result"]["structuredContent"]
        assert audit["llm_calls"] == 0
        assert audit["content_included"] is False

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
        auth_result = mcp(
            client,
            credentials["access_token"],
            21,
            "tools/call",
            {"name": "auth_context", "arguments": {}},
        )["result"]
        auth_context = auth_result["structuredContent"]["auth_context"]
        assert auth_context["connection"]["id"] == "oauth:" + registration["client_id"]
        assert auth_context["connection"]["transport"] == "mcp"
        assert auth_context["connection"]["credential_type"] == "oauth"
        assert auth_context["authorization"]["grants"] == [
            "feature:write",
            "memory:read",
            "memory:write",
        ]
        assert auth_context["external_service_permissions"]["status"] == "not_evaluated"
        assert auth_result["_meta"]["vibememory/contextRef"] == auth_context["context_ref"]

        preflight = mcp(
            client,
            credentials["access_token"],
            22,
            "tools/call",
            {
                "name": "permission_check",
                "arguments": {"resource": "vault", "operation": "read"},
            },
        )["result"]["structuredContent"]
        assert preflight["authorization"]["status"] == "denied"
        assert preflight["authorization"]["required_grant"] == "vault:read"
        assert preflight["resource_existence_checked"] is False

        external = mcp(
            client,
            credentials["access_token"],
            50,
            "tools/call",
            {
                "name": "memory_create",
                "arguments": {
                    "content": "quoted browser result",
                    "kind": "fact",
                    "keywords": ["browser result"],
                    "provenance": {
                        "source_type": "external",
                        "origin_agent": "browser-agent",
                        "origin_url": "https://example.test/result",
                    },
                },
            },
        )["result"]["structuredContent"]["record"]
        assert external["security_state"] == "quarantined"
        quarantined = mcp(
            client,
            credentials["access_token"],
            51,
            "tools/call",
            {"name": "quarantine_list", "arguments": {}},
        )["result"]["structuredContent"]["items"]
        assert [item["id"] for item in quarantined] == [external["id"]]
        hidden = mcp(
            client,
            credentials["access_token"],
            52,
            "tools/call",
            {
                "name": "memory_search",
                "arguments": {"keywords": ["browser result"], "match_mode": "exact"},
            },
        )["result"]["structuredContent"]
        assert hidden["hits"] == []
        released = mcp(
            client,
            credentials["access_token"],
            53,
            "tools/call",
            {
                "name": "record_security_update",
                "arguments": {
                    "id": external["id"],
                    "expected_version": 1,
                    "trust_level": "trusted",
                    "state": "active",
                    "scan_verdict": "safe",
                    "scan_evidence": ["reviewed exact content"],
                    "reason": "explicit agent review",
                },
            },
        )["result"]["structuredContent"]["record"]
        assert released["security_state"] == "active"

        batch_entities = mcp(
            client,
            credentials["access_token"],
            54,
            "tools/call",
            {
                "name": "entity_create_many",
                "arguments": {
                    "items": [
                        {
                            "client_request_id": "mcp-entity-a",
                            "name": "MCP A",
                            "entity_type": "Project",
                            "keywords": ["mcp-a"],
                        },
                        {
                            "client_request_id": "mcp-entity-b",
                            "name": "MCP B",
                            "entity_type": "Project",
                            "keywords": ["mcp-b"],
                        },
                    ]
                },
            },
        )["result"]["structuredContent"]
        assert batch_entities["counts"] == {"created": 2}
        entity_ids = [item["id"] for item in batch_entities["items"]]
        repeated = mcp(
            client,
            credentials["access_token"],
            55,
            "tools/call",
            {
                "name": "entity_create_many",
                "arguments": {
                    "items": [
                        {
                            "client_request_id": "mcp-entity-a",
                            "name": "MCP A",
                            "entity_type": "Project",
                            "keywords": ["mcp-a"],
                        }
                    ]
                },
            },
        )["result"]["structuredContent"]
        assert repeated["items"][0]["status"] == "existing"
        relation_batch = mcp(
            client,
            credentials["access_token"],
            56,
            "tools/call",
            {
                "name": "relation_create_many",
                "arguments": {
                    "items": [
                        {
                            "client_request_id": "mcp-relation-a-b",
                            "source_id": entity_ids[0],
                            "target_id": entity_ids[1],
                            "relation": "RELATED_TO",
                            "reason": "batch test",
                            "confidence": 0.75,
                        }
                    ]
                },
            },
        )["result"]["structuredContent"]
        assert relation_batch["items"][0]["status"] == "created"
        manifest = {
            "items": [
                {
                    "client_request_id": "mcp-reviewed-edge",
                    "source_id": entity_ids[1],
                    "target_id": entity_ids[0],
                    "relation": "CONTEXT_FOR",
                    "reason": "reviewed MCP graph manifest",
                }
            ]
        }
        dry_run = mcp(
            client,
            credentials["access_token"],
            58,
            "tools/call",
            {"name": "graph_diff", "arguments": manifest},
        )["result"]["structuredContent"]
        assert dry_run["items"][0]["classification"] == "create"
        applied = mcp(
            client,
            credentials["access_token"],
            59,
            "tools/call",
            {
                "name": "graph_apply",
                "arguments": {
                    **manifest,
                    "approved_diff_hash": dry_run["diff_hash"],
                    "approved_create_client_ids": ["mcp-reviewed-edge"],
                    "approved_retract_ids": [],
                    "reason": "approved after exact dry-run review",
                },
            },
        )["result"]["structuredContent"]
        assert applied["created"][0]["status"] == "created"
        compact_relations = mcp(
            client,
            credentials["access_token"],
            57,
            "tools/call",
            {
                "name": "relations_list",
                "arguments": {
                    "source_id": entity_ids[0],
                    "limit": 1,
                    "fields": ["source_id", "target_id", "relation"],
                    "include_history": False,
                },
            },
        )["result"]["structuredContent"]
        assert compact_relations["items"][0] == {
            "id": relation_batch["items"][0]["id"],
            "source_id": entity_ids[0],
            "target_id": entity_ids[1],
            "relation": "RELATED_TO",
        }

        agent_data = mcp(
            client,
            credentials["access_token"],
            6,
            "tools/call",
            {"name": "agents_list", "arguments": {}},
        )["result"]["structuredContent"]
        assert agent_data["self"]["id"].startswith("oauth:")
        queued = mcp(
            client,
            credentials["access_token"],
            7,
            "tools/call",
            {
                "name": "message_send",
                "arguments": {
                    "recipient_agent_id": agent_data["self"]["id"],
                    "body": "MCP handoff",
                    "kind": "notification",
                },
            },
        )["result"]["structuredContent"]["message"]
        inbox = mcp(
            client,
            credentials["access_token"],
            8,
            "tools/call",
            {"name": "message_inbox", "arguments": {"after": 0}},
        )["result"]["structuredContent"]
        assert inbox["items"][0]["id"] == queued["id"]
        acknowledged = mcp(
            client,
            credentials["access_token"],
            9,
            "tools/call",
            {
                "name": "message_ack",
                "arguments": {"id": queued["id"], "status": "acked"},
            },
        )["result"]["structuredContent"]["message"]
        assert acknowledged["status"] == "acked"

        connections = client.get("/auth/mcp-connections").json()
        assert connections["server_url"] == RESOURCE
        assert connections["items"][0]["client_name"] == "Claude"
        revoked = client.delete(
            "/auth/mcp-connections/" + registration["client_id"],
            headers={"Origin": ORIGIN},
        )
        assert revoked.status_code == 204
        assert client.get("/v1/agents").json()["items"] == []
        revoked_call = client.post(
            "/mcp",
            headers={"Authorization": "Bearer " + credentials["access_token"]},
            json={"jsonrpc": "2.0", "id": 6, "method": "ping"},
        )
        assert revoked_call.status_code == 401
        assert revoked_call.json()["reason_code"] == "AUTHENTICATION_REVOKED"


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
        denied_error = denied["result"]["structuredContent"]["error"]
        assert denied_error["reason_code"] == "PERMISSION_REQUIRED"
        assert denied_error["context"]["ref"] == "connection:oauth:" + registration["client_id"]
        assert denied_error["operation"] == "memory_create"

        with sqlite3.connect(settings.data_dir / "auth.sqlite") as db:
            db.execute("UPDATE oauth_access_tokens SET expires_at=0")
        expired = client.post(
            "/mcp",
            headers={"Authorization": "Bearer " + credentials["access_token"]},
            json={"jsonrpc": "2.0", "id": 3, "method": "ping"},
        )
        assert expired.status_code == 401
        assert expired.json()["reason_code"] == "AUTHENTICATION_EXPIRED"

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


def test_existing_mcp_connection_permissions_can_be_added_and_revoked(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client, "managed-mcp@example.invalid")
        registration = register(client, "Managed MCP")
        code, verifier = authorize(client, registration, "memory:read")
        credentials = token(client, registration, code, verifier)
        path = f"/auth/mcp-connections/{registration['client_id']}"

        initial_tools = mcp(client, credentials["access_token"], 1, "tools/list")["result"]["tools"]
        assert "memory_create" not in {tool["name"] for tool in initial_tools}

        expanded = client.patch(
            path,
            json={
                "scopes": [
                    "memory:read",
                    "memory:write",
                    "feature:write",
                    "vault:read",
                ]
            },
        )
        assert expanded.status_code == 200, expanded.text
        assert set(expanded.json()["scopes"]) == {
            "memory:read",
            "memory:write",
            "feature:write",
            "vault:read",
        }
        expanded_tools = mcp(client, credentials["access_token"], 2, "tools/list")["result"][
            "tools"
        ]
        expanded_names = {tool["name"] for tool in expanded_tools}
        assert {"memory_create", "feature_request_submit", "vault_get"}.issubset(expanded_names)

        assert (
            client.put(
                "/v1/vault/SCOPED_TOKEN",
                json={"value": "secret", "description": "permission test"},
            ).status_code
            == 200
        )
        grants_path = path + "/vault"
        assert client.put(grants_path, json={"names": ["SCOPED_TOKEN"]}).status_code == 200

        reduced = client.patch(path, json={"scopes": ["memory:read"]})
        assert reduced.status_code == 200, reduced.text
        reduced_tools = mcp(client, credentials["access_token"], 3, "tools/list")["result"]["tools"]
        reduced_names = {tool["name"] for tool in reduced_tools}
        assert "memory_search" in reduced_names
        assert not {"memory_create", "feature_request_submit", "vault_get"} & reduced_names
        assert all(not item["granted"] for item in client.get(grants_path).json()["items"])

        history = client.get(path + "/permission-events?limit=5")
        assert history.status_code == 200, history.text
        events = history.json()["items"]
        assert len(events) == 2
        assert set(events[0]["before_scopes"]) == {
            "memory:read",
            "memory:write",
            "feature:write",
            "vault:read",
        }
        assert events[0]["after_scopes"] == ["memory:read"]
        assert all(event["source"] == "console" for event in events)

        refreshed = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": registration["client_id"],
                "refresh_token": credentials["refresh_token"],
                "resource": RESOURCE,
            },
        )
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["scope"] == "memory:read"

        client.post("/auth/logout")
        signup(client, "managed-mcp-other@example.invalid")
        assert client.patch(path, json={"scopes": ["memory:read"]}).status_code == 404
        assert client.get(path + "/permission-events").status_code == 404


def test_mcp_vault_requires_scope_and_per_entry_grant(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client, "vault-mcp@example.invalid")
        assert (
            client.put(
                "/v1/vault/MOLTBOOK_API_KEY",
                json={"value": "moltbook-secret", "description": "Moltbook posting"},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/v1/vault/OTHER_TOKEN",
                json={"value": "other-secret", "description": "Not granted"},
            ).status_code
            == 200
        )

        registration = register(client, "Vault client")
        code, verifier = authorize(client, registration, "memory:read vault:read")
        credentials = token(client, registration, code, verifier)
        tools = mcp(client, credentials["access_token"], 1, "tools/list")["result"]["tools"]
        assert {"vault_list", "vault_get"}.issubset({tool["name"] for tool in tools})

        empty = mcp(
            client,
            credentials["access_token"],
            2,
            "tools/call",
            {"name": "vault_list", "arguments": {}},
        )["result"]["structuredContent"]
        assert empty == {"items": []}
        denied = mcp(
            client,
            credentials["access_token"],
            3,
            "tools/call",
            {"name": "vault_get", "arguments": {"name": "MOLTBOOK_API_KEY"}},
        )["result"]
        assert denied["isError"] is True

        grants_path = f"/auth/mcp-connections/{registration['client_id']}/vault"
        available = client.get(grants_path).json()["items"]
        assert {item["name"] for item in available} == {"MOLTBOOK_API_KEY", "OTHER_TOKEN"}
        assert all("value" not in item for item in available)
        granted = client.put(grants_path, json={"names": ["MOLTBOOK_API_KEY"]})
        assert granted.status_code == 200, granted.text

        listed = mcp(
            client,
            credentials["access_token"],
            4,
            "tools/call",
            {"name": "vault_list", "arguments": {}},
        )["result"]["structuredContent"]["items"]
        assert [item["name"] for item in listed] == ["MOLTBOOK_API_KEY"]
        assert "value" not in listed[0]
        secret = mcp(
            client,
            credentials["access_token"],
            5,
            "tools/call",
            {"name": "vault_get", "arguments": {"name": "MOLTBOOK_API_KEY"}},
        )["result"]["structuredContent"]["secret"]
        assert secret == {"name": "MOLTBOOK_API_KEY", "value": "moltbook-secret"}
        denied_other = mcp(
            client,
            credentials["access_token"],
            6,
            "tools/call",
            {"name": "vault_get", "arguments": {"name": "OTHER_TOKEN"}},
        )["result"]
        assert denied_other["isError"] is True

        audit = client.get("/v1/vault-access-audit").json()["items"]
        assert {item["outcome"] for item in audit} >= {
            "success",
            "denied_grant",
            "list_success",
        }
        assert all("moltbook-secret" not in str(item) for item in audit)

        assert client.put(grants_path, json={"names": []}).status_code == 200
        revoked = mcp(
            client,
            credentials["access_token"],
            7,
            "tools/call",
            {"name": "vault_get", "arguments": {"name": "MOLTBOOK_API_KEY"}},
        )["result"]
        assert revoked["isError"] is True

        client.post("/auth/logout")
        signup(client, "vault-other@example.invalid")
        assert client.get(grants_path).status_code == 404


def test_mcp_vault_grants_reject_connection_without_scope(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client, "vault-scope@example.invalid")
        assert (
            client.put(
                "/v1/vault/API_TOKEN", json={"value": "secret", "description": "API"}
            ).status_code
            == 200
        )
        registration = register(client, "Read only")
        code, verifier = authorize(client, registration, "memory:read")
        credentials = token(client, registration, code, verifier)
        tools = mcp(client, credentials["access_token"], 1, "tools/list")["result"]["tools"]
        assert "vault_get" not in {tool["name"] for tool in tools}
        response = client.put(
            f"/auth/mcp-connections/{registration['client_id']}/vault",
            json={"names": ["API_TOKEN"]},
        )
        assert response.status_code == 422


def test_mcp_namespace_write_boundary_and_vault_grants_are_independent(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup(client, "namespace-mcp@example.invalid")
        namespace = client.post("/auth/namespaces", json={"name": "Read only project"}).json()
        client.put(
            "/v1/vault/API_TOKEN",
            json={"value": "secret", "description": "independence test"},
        )
        registration = register(client, "Namespace MCP")
        code, verifier = authorize(
            client, registration, "memory:read memory:write vault:read"
        )
        credentials = token(client, registration, code, verifier)
        connection = f"/auth/mcp-connections/{registration['client_id']}"
        grants = [{"namespace_id": namespace["id"], "can_read": True, "can_write": False}]
        assert client.put(connection + "/namespaces", json={"grants": grants}).status_code == 200
        assert (
            client.put(connection + "/vault", json={"names": ["API_TOKEN"]}).status_code
            == 200
        )
        listed = client.get("/auth/mcp-connections").json()["items"][0]
        assert listed["namespace_grants"] == grants

        response = client.post(
            "/mcp",
            headers={
                "Authorization": "Bearer " + credentials["access_token"],
                "X-Vibe-Memory-Namespace": namespace["id"],
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "record_update_many", "arguments": {"items": []}},
            },
        )
        assert response.status_code == 403

        denied = client.put(connection + "/namespaces", json={"grants": []}).json()
        assert denied["grants"] == [
            {"namespace_id": "default", "can_read": False, "can_write": False}
        ]
        assert client.post(
            "/mcp",
            headers={"Authorization": "Bearer " + credentials["access_token"]},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ).status_code == 403
