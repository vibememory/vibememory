import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def load_python_client():
    path = ROOT / "sdk" / "python" / "vibememory" / "client.py"
    spec = importlib.util.spec_from_file_location("vibememory_public_client", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_sdk_structured_error_cancellation_and_pages():
    module = load_python_client()
    body = json.dumps(
        {
            "error": {
                "reason_code": "VERSION_CONFLICT",
                "retryable": False,
                "request_id": "request-1",
            }
        }
    )
    error = module.VibeMemoryError(409, body)
    assert error.code == "VERSION_CONFLICT"
    assert error.retryable is False
    assert error.request_id == "request-1"

    client = module.VibeMemoryClient("https://example.test", "test-token")
    with pytest.raises(module.VibeMemoryCancelled):
        client.get("record", cancelled=lambda: True)

    pages = iter(
        [
            {"items": [{"id": "one"}, {"id": "two"}], "limit": 2, "offset": 0},
            {"items": [{"id": "three"}], "limit": 2, "offset": 2},
        ]
    )
    def list_page(limit, offset, cancelled=None):
        return next(pages)

    client.list = list_page
    assert [page["offset"] for page in client.iter_records(limit=2)] == [0, 2]


def test_sdk_package_versions_and_typescript_contract():
    python_package = tomllib.loads(
        (ROOT / "sdk" / "python" / "pyproject.toml").read_text(encoding="utf-8")
    )
    typescript_package = json.loads(
        (ROOT / "sdk" / "typescript" / "package.json").read_text(encoding="utf-8")
    )
    typescript_source = (ROOT / "sdk" / "typescript" / "src" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert python_package["project"]["version"] == "0.2.0"
    assert typescript_package["version"] == "0.2.0"
    for exported in ("VibeMemoryError", "RequestOptions", "BatchResult", "async *records"):
        assert exported in typescript_source
