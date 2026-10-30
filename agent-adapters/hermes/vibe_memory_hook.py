#!/usr/bin/env python3
"""Fail-open Hermes shell-hook adapter for the native Vibe Memory CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 64 * 1024


def read_payload() -> dict:
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("hook payload exceeds 64 KiB")
    value = json.loads(raw or b"{}")
    if not isinstance(value, dict):
        raise ValueError("hook payload must be an object")
    return value


def allowed_cwd(cwd: Path) -> bool:
    configured = os.environ.get("VIBE_MEMORY_PROJECT_ROOTS", "").strip()
    if not configured:
        return True
    resolved = cwd.resolve()
    for item in configured.split(os.pathsep):
        if not item.strip():
            continue
        root = Path(item).expanduser().resolve()
        if resolved == root or root in resolved.parents:
            return True
    return False


def state_marker(payload: dict, cwd: Path) -> Path:
    session = str(payload.get("session_id") or "unknown-session")
    digest = hashlib.sha256(f"{session}\0{cwd}".encode()).hexdigest()
    home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
    return home / "vibe-memory-hooks" / f"{digest}.compact"


def cli_payload(payload: dict, cwd: Path, source: str = "startup") -> dict:
    # Deliberately omit user_message, conversation_history, model output, environment,
    # and every other Hermes event field.
    return {
        "session_id": str(payload.get("session_id") or "unknown-session"),
        "cwd": str(cwd),
        "source": source,
        "stop_hook_active": False,
    }


def call_cli(command: str, payload: dict, cwd: Path, source: str = "startup") -> dict | None:
    executable = os.environ.get("VIBE_MEMORY_CLI", "vibe-memory")
    completed = subprocess.run(
        [executable, "hook", command],
        input=json.dumps(cli_payload(payload, cwd, source)).encode(),
        capture_output=True,
        check=False,
        timeout=10,
        cwd=cwd,
        env=os.environ.copy(),
    )
    if completed.returncode != 0 or not completed.stdout:
        return None
    if len(completed.stdout) > MAX_BYTES:
        raise ValueError("Vibe Memory hook output exceeds 64 KiB")
    value = json.loads(completed.stdout)
    return value if isinstance(value, dict) else None


def additional_context(value: dict | None) -> str:
    if not value:
        return ""
    specific = value.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return ""
    context = specific.get("additionalContext")
    return context.strip() if isinstance(context, str) else ""


def handle(event: str, payload: dict) -> dict:
    cwd = Path(str(payload.get("cwd") or os.getcwd())).expanduser().resolve()
    if not allowed_cwd(cwd):
        return {}
    marker = state_marker(payload, cwd)
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}

    if event == "post_compaction":
        call_cli("pre-compact", payload, cwd, "compact")
        marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker.touch(mode=0o600, exist_ok=True)
        return {}

    if event == "pre_verify":
        context = additional_context(call_cli("stop", payload, cwd))
        return {"action": "continue", "message": context} if context else {}

    if event == "on_session_finalize":
        context = additional_context(call_cli("stop", payload, cwd))
        return {"message": context} if context else {}

    if event != "pre_llm_call":
        return {}

    contexts: list[str] = []
    first_turn = bool(extra.get("is_first_turn"))
    after_compaction = marker.exists()
    if first_turn or after_compaction:
        source = "compact" if after_compaction else "startup"
        recalled = additional_context(call_cli("session-start", payload, cwd, source))
        if recalled:
            contexts.append(recalled)
        if after_compaction:
            marker.unlink(missing_ok=True)
    elif context := additional_context(call_cli("stop", payload, cwd)):
        contexts.append(context)
    return {"context": "\n\n".join(contexts)} if contexts else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "event",
        choices=("pre_llm_call", "pre_verify", "post_compaction", "on_session_finalize"),
    )
    args = parser.parse_args()
    try:
        result = handle(args.event, read_payload())
    except Exception as error:  # Shell hooks must never block the agent loop.
        print(f"Vibe Memory Hermes hook skipped: {error}", file=sys.stderr)
        result = {}
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
