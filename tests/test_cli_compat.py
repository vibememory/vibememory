def test_unsupported_native_cli_stops_before_data_access(client):
    response = client.get(
        "/v1/me",
        headers={"User-Agent": "VibeMemoryCLI/3.7.9"},
    )
    assert response.status_code == 426
    assert response.headers["Vibe-Memory-Minimum-CLI"] == "3.8.0"
    assert response.json()["minimum_cli_version"] == "3.8.0"


def test_supported_native_cli_and_non_cli_clients_continue(client):
    supported = client.get(
        "/v1/me",
        headers={"User-Agent": "VibeMemoryCLI/3.8.0"},
    )
    assert supported.status_code == 200
    assert supported.headers["Vibe-Memory-Minimum-CLI"] == "3.8.0"

    generic = client.get("/v1/me", headers={"User-Agent": "OtherAgent/1.0"})
    assert generic.status_code == 200


def test_distribution_paths_remain_reachable_for_cli_update(client):
    response = client.get(
        "/skills/vibe-memory/manifest.json",
        headers={"User-Agent": "VibeMemoryCLI/3.0.0"},
    )
    assert response.status_code == 200
