import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERMES_ADAPTER = ROOT / "agent-adapters/hermes/vibe_memory_hook.py"


def make_fake_cli(tmp_path: Path) -> tuple[Path, Path]:
    capture = tmp_path / "capture.jsonl"
    executable = tmp_path / "fake-vibe-memory"
    executable.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

payload = json.loads(sys.stdin.read())
capture = Path(os.environ["FAKE_VIBE_MEMORY_CAPTURE"])
with capture.open("a") as output:
    output.write(json.dumps({"args": sys.argv[1:], "payload": payload}) + "\\n")
command = sys.argv[-1]
context = "recalled context" if command == "session-start" else "checkpoint instruction"
if command == "pre-compact":
    print("{}")
else:
    print(json.dumps({"hookSpecificOutput": {"additionalContext": context}}))
"""
    )
    executable.chmod(0o755)
    return executable, capture


def run_hermes(event: str, payload: dict, env: dict) -> tuple[dict, subprocess.CompletedProcess]:
    completed = subprocess.run(
        [sys.executable, str(HERMES_ADAPTER), event],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return json.loads(completed.stdout), completed


def test_codex_hooks_use_only_fixed_cli_commands():
    manifest = json.loads((ROOT / "agent-adapters/codex/hooks.json").read_text())
    expected = {
        "SessionStart": "vibe-memory hook session-start",
        "Stop": "vibe-memory hook stop",
        "PreCompact": "vibe-memory hook pre-compact",
    }
    assert set(manifest["hooks"]) == set(expected)
    for event, command in expected.items():
        hook = manifest["hooks"][event][0]["hooks"][0]
        assert hook["type"] == "command"
        assert hook["command"] == command
        assert hook["timeout"] <= 10


def test_hermes_adapter_recall_checkpoint_and_input_minimization(tmp_path):
    executable, capture = make_fake_cli(tmp_path)
    env = {
        **os.environ,
        "VIBE_MEMORY_CLI": str(executable),
        "FAKE_VIBE_MEMORY_CAPTURE": str(capture),
        "HERMES_HOME": str(tmp_path / "hermes-home"),
    }
    payload = {
        "session_id": "session-1",
        "cwd": str(tmp_path),
        "extra": {"is_first_turn": True},
        "user_message": "must not be forwarded",
        "conversation_history": ["must not be forwarded"],
        "secret": "must not be forwarded",
    }

    recalled, completed = run_hermes("pre_llm_call", payload, env)
    assert completed.returncode == 0
    assert recalled == {"context": "recalled context"}

    checkpoint, completed = run_hermes("pre_verify", payload, env)
    assert completed.returncode == 0
    assert checkpoint == {"action": "continue", "message": "checkpoint instruction"}

    calls = [json.loads(line) for line in capture.read_text().splitlines()]
    assert calls[0]["args"] == ["hook", "session-start"]
    assert calls[1]["args"] == ["hook", "stop"]
    assert set(calls[0]["payload"]) == {"session_id", "cwd", "source", "stop_hook_active"}
    assert "user_message" not in json.dumps(calls)
    assert "conversation_history" not in json.dumps(calls)
    assert "secret" not in json.dumps(calls)


def test_hermes_adapter_recalls_after_compaction_and_fails_open(tmp_path):
    executable, capture = make_fake_cli(tmp_path)
    env = {
        **os.environ,
        "VIBE_MEMORY_CLI": str(executable),
        "FAKE_VIBE_MEMORY_CAPTURE": str(capture),
        "HERMES_HOME": str(tmp_path / "hermes-home"),
    }
    payload = {"session_id": "session-2", "cwd": str(tmp_path), "extra": {}}
    result, _ = run_hermes("post_compaction", payload, env)
    assert result == {}
    result, _ = run_hermes("pre_llm_call", payload, env)
    assert result == {"context": "recalled context"}
    calls = [json.loads(line) for line in capture.read_text().splitlines()]
    assert calls[-1]["payload"]["source"] == "compact"

    failed, completed = run_hermes(
        "pre_llm_call",
        {**payload, "extra": {"is_first_turn": True}},
        {**env, "VIBE_MEMORY_CLI": str(tmp_path / "missing")},
    )
    assert completed.returncode == 0
    assert failed == {}


def test_openclaw_bridge_contract():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is not installed")
    completed = subprocess.run(
        [node, "--test", str(ROOT / "agent-adapters/openclaw/bridge.test.mjs")],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_openclaw_manifest_and_typed_hooks_are_pinned():
    package = json.loads((ROOT / "agent-adapters/openclaw/package.json").read_text())
    manifest = json.loads((ROOT / "agent-adapters/openclaw/openclaw.plugin.json").read_text())
    source = (ROOT / "agent-adapters/openclaw/index.ts").read_text()
    assert package["openclaw"]["extensions"] == ["./index.ts"]
    assert manifest["id"] == "vibe-memory-hooks"
    assert package["name"] == manifest["id"]
    assert manifest["configSchema"]["additionalProperties"] is False
    for hook in ("before_prompt_build", "before_agent_finalize", "before_compaction", "session_end"):
        assert f'api.on("{hook}"' in source
    assert "ctx?.workspaceDir" in source
    assert "messages" not in (ROOT / "agent-adapters/openclaw/bridge.mjs").read_text()
    docs = (ROOT / "docs/agent-hooks.md").read_text()
    assert "--force --accept-capabilities" in docs
