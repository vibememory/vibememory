from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = "https://vibememory.io"


def test_rest_auth_context_and_capabilities_are_current_connection_only(settings):
    settings = settings.model_copy(update={"public_origin": ORIGIN, "api_keys": {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers["Origin"] = ORIGIN
        signup = client.post(
            "/auth/signup",
            json={
                "name": "Capability User",
                "email": "capability@example.com",
                "password": "a-long-test-password-123",
            },
        )
        assert signup.status_code == 200, signup.text
        created = client.post(
            "/auth/api-keys",
            json={"name": "Read only", "permissions": ["memory:read"]},
        ).json()
        headers = {"Authorization": "Bearer " + created["key"], "Origin": ""}

        response = client.get("/v1/auth-context", headers=headers)
        context = response.json()
        assert response.headers["vibe-memory-context-ref"] == context["context_ref"]
        assert response.headers["x-request-id"]
        assert context["connection"]["id"] == "key:" + created["id"]
        assert context["connection"]["transport"] == "rest"
        assert context["connection"]["credential_type"] == "api_key"
        assert context["authorization"]["grants"] == ["memory:read"]
        assert context["authorization"]["other_connections_checked"] is False
        assert context["authorization"]["permission_inheritance"] is False
        assert context["external_service_permissions"]["status"] == "not_evaluated"
        assert context["project_scope"]["status"] == "enforced"
        assert context["project_scope"]["namespace_id"] == "default"
        assert created["key"] not in str(context)

        read = client.post(
            "/v1/permission-check",
            headers=headers,
            json={"resource": "memory", "operation": "read"},
        ).json()
        write = client.post(
            "/v1/permission-check",
            headers=headers,
            json={"resource": "memory", "operation": "create"},
        ).json()
        assert read["authorization"]["status"] == "allowed"
        assert write["authorization"] == {
            "status": "denied",
            "reason_code": "PERMISSION_REQUIRED",
            "required_grant": "memory:write",
        }
        assert write["resource_existence_checked"] is False
        assert write["request_will_reauthorize"] is True

        contract = client.get("/v1/capabilities", headers=headers).json()
        assert contract["schema_version"] == "1.1"
        memory_actions = {
            item["operation"]: item["authorization"]["status"]
            for item in contract["capabilities"]
            if item["resource"] == "memory"
        }
        assert memory_actions["read"] == "allowed"
        assert memory_actions["create"] == "denied"

        denied = client.post(
            "/v1/memories",
            headers=headers,
            json={"content": "not allowed", "keywords": ["denied"]},
        )
        assert denied.status_code == 403
        error = denied.json()["error"]
        assert error["reason_code"] == "PERMISSION_REQUIRED"
        assert error["context"]["ref"] == context["context_ref"]
        assert error["request_id"] == denied.headers["x-request-id"]


def test_unknown_capability_is_not_inferred(client):
    result = client.post(
        "/v1/permission-check",
        json={"resource": "third_party_service", "operation": "publish"},
    ).json()
    assert result["feature_status"] == "unknown"
    assert result["authorization"]["status"] == "unknown"
    assert result["authorization"]["reason_code"] == "UNKNOWN_CAPABILITY"


def test_structured_validation_errors_do_not_echo_input(client):
    response = client.post(
        "/v1/permission-check",
        json={"resource": "SECRET-INPUT", "operation": "read"},
    )
    assert response.status_code == 422
    assert "SECRET-INPUT" not in response.text
    assert response.json()["error"]["reason_code"] == "INVALID_ARGUMENT"
