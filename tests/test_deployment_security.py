from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app


def test_https_hsts_and_admin_routes_hidden_from_public_openapi(settings):
    secure = settings.model_copy(
        update={
            "public_origin": "https://memory.example.com",
            "hsts_max_age": 12345,
            "hsts_include_subdomains": True,
        }
    )
    with TestClient(create_app(secure, SpyEmbedder()), base_url=secure.public_origin) as client:
        health = client.get("/health")
        assert health.headers["strict-transport-security"] == "max-age=12345; includeSubDomains"
        paths = client.get("/openapi.json").json()["paths"]
        assert not any(path.startswith("/v1/admin/") for path in paths)
        assert client.get("/v1/admin/users").status_code == 401


def test_admin_schema_can_be_enabled_for_private_deployments(settings):
    private = settings.model_copy(update={"public_openapi_include_admin": True})
    with TestClient(create_app(private, SpyEmbedder())) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/v1/admin/users" in paths
