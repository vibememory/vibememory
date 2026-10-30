#!/usr/bin/env python3
"""Fail-open Cursor adapter for the native Vibe Memory lifecycle hooks."""

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


def hook_cwd(payload: dict) -> Path:
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        roots = payload.get("workspace_roots")
        if isinstance(roots, list) and roots and isinstance(roots[0], str):
            cwd = roots[0]
    return Path(cwd or os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd()).resolve()


def allowed_cwd(cwd: Path) -> bool:
    configured = os.environ.get("VIBE_MEMORY_PROJECT_ROOTS", "").strip()
    if not configured:
        return True
    for item in configured.split(os.pathsep):
        if not item.strip():
            continue
        root = Path(item).expanduser().resolve()
        if cwd == root or root in cwd.parents:
            return True
    return False


def session_id(payload: dict) -> str:
    return str(payload.get("session_id") or payload.get("conversation_id") or "unknown-session")


def state_marker(payload: dict, cwd: Path) -> Path:
    digest = hashlib.sha256(f"{session_id(payload)}\0{cwd}".encode()).hexdigest()
    home = Path(os.environ.get("CURSOR_HOME") or Path.home() / ".cursor")
    return home / "vibe-memory-hooks" / f"{digest}.compact"


def cli_payload(payload: dict, cwd: Path, source: str = "startup") -> dict:
    # Deliberately omit prompts, transcripts, model output, tool data, user email,
    # environment variables, and every other Cursor event field.
    return {
        "session_id": session_id(payload),
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
    cwd = hook_cwd(payload)
    if not allowed_cwd(cwd):
        return {}
    marker = state_marker(payload, cwd)

    if event == "session-start":
        context = additional_context(call_cli("session-start", payload, cwd))
        return {"additional_context": context} if context else {}

    if event == "pre-compact":
        call_cli("pre-compact", payload, cwd, "compact")
        marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker.touch(mode=0o600, exist_ok=True)
        return {}

    if event != "stop" or payload.get("status") not in (None, "completed"):
        return {}
    if int(payload.get("loop_count") or 0) >= 1:
        return {}

    contexts: list[str] = []
    if marker.exists():
        recalled = additional_context(call_cli("session-start", payload, cwd, "compact"))
        if recalled:
            contexts.append(recalled)
        marker.unlink(missing_ok=True)
    checkpoint = additional_context(call_cli("stop", payload, cwd))
    if checkpoint:
        contexts.append(checkpoint)
    return {"followup_message": "\n\n".join(contexts)} if contexts else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", choices=("session-start", "stop", "pre-compact"))
    args = parser.parse_args()
    try:
        result = handle(args.event, read_payload())
    except Exception as error:  # Cursor hooks must fail open.
        print(f"Vibe Memory Cursor hook skipped: {error}", file=sys.stderr)
        result = {}
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
