"""Run the distributable agent helper against a real server on a private random port."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from conftest import KEY_A

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/vibe-memory/scripts/memory.py"


def test_agent_helper_roundtrip(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "MEMORY_DATA_DIR": str(tmp_path / "data"),
        "MEMORY_EMBEDDING_CACHE": str(ROOT / ".data/models"),
        "MEMORY_API_KEYS": json.dumps({KEY_A: "agent-user"}),
        "MEMORY_URL": url,
        "MEMORY_API_KEY": KEY_A,
    }
    with (tmp_path / "server.log").open("w+") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "vibe_memory.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=env,
            stdout=output,
            stderr=output,
        )
        try:
            for _ in range(200):
                assert process.poll() is None, "server exited; inspect " + str(output.name)
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1):
                        break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.05)
            else:
                raise AssertionError("server startup timeout")

            def helper(*args, expected=0):
                result = subprocess.run(
                    [sys.executable, str(HELPER), *args],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                assert result.returncode == expected, result.stderr
                return json.loads(result.stdout) if expected == 0 else result.stderr

            saved = helper(
                "remember",
                "나는 녹차를 좋아한다",
                "--kind",
                "preference",
                "--source",
                "agent-one",
                "--keyword",
                "녹차",
            )
            assert helper("get", saved["id"])["content"] == saved["content"]
            raw_file = tmp_path / "원본.bin"
            raw_file.write_bytes(bytes(range(256)) * 300)
            uploaded = helper("upload", str(raw_file))
            assert uploaded["metadata"]["size_bytes"] == raw_file.stat().st_size
            binary_request = urllib.request.Request(
                url + "/v1/files/" + uploaded["id"], headers={"Authorization": "Bearer " + KEY_A}
            )
            with urllib.request.urlopen(binary_request) as response:
                assert response.read() == raw_file.read_bytes()
            helper("forget", uploaded["id"])
            chunked_request = urllib.request.Request(
                url + "/v1/files?filename=chunked.bin",
                data=iter([b"first-part", b"second-part"]),
                method="POST",
                headers={
                    "Authorization": "Bearer " + KEY_A,
                    "Content-Type": "application/octet-stream",
                },
            )
            with urllib.request.urlopen(chunked_request) as response:
                chunked = json.load(response)
            assert chunked["metadata"]["size_bytes"] == len(b"first-partsecond-part")
            helper("forget", chunked["id"])
            note = tmp_path / "document.json"
            note.write_text(
                json.dumps(
                    {
                        "title": "notes.md",
                        "keywords": ["기억숲"],
                        "metadata": {
                            "summary": "에이전트가 분석한 프로젝트",
                            "mime_type": "text/markdown",
                        },
                    }
                ),
                encoding="utf-8",
            )
            document = helper("ingest", str(note))
            helper(
                "relate",
                saved["id"],
                document["id"],
                "--relation",
                "RELATED_TO",
                "--reason",
                "프로필",
            )
            assert len(helper("graph", saved["id"])["nodes"]) == 2
            assert helper("recall", "녹차", "--limit", "1")["hits"][0]["id"] == saved["id"]
            feature_payload = tmp_path / "feature.json"
            feature_payload.write_text(
                json.dumps(
                    {
                        "title": "Batch relationships",
                        "description": "Store many relations at once",
                        "agent_name": "integration-agent",
                        "client_request_id": "batch-v1",
                    }
                ),
                encoding="utf-8",
            )
            feature = helper("request-feature", str(feature_payload))
            assert feature["status"] == "received"
            assert helper("request-feature", str(feature_payload))["id"] == feature["id"]
            assert helper("feature-request", feature["id"])["title"] == "Batch relationships"
            assert helper("feature-requests")["items"][0]["id"] == feature["id"]
            assert len(helper("list")["items"]) == 2
            assert helper("forget", saved["id"])["deleted"] is True
            assert "HTTP 404" in helper("get", saved["id"], expected=1)
            assert helper("graph", document["id"])["relations"] == []
        finally:
            process.terminate()
            process.wait(timeout=10)
