# Agent lifecycle hooks

Vibe Memory ships a Claude Code marketplace plugin and matching native CLI hook
commands. The hooks never send a transcript, hidden reasoning, file contents, or
environment variables to the service. They use only the project directory name,
the local Git state fingerprint, compact search results, and queued handoffs.

## Claude Code plugin

Install the current native CLI first and make the verified `vibe-memory` binary
available on `PATH`. Then, inside Claude Code 2.1.275 or later, open the plugin
review screen directly:

```text
/plugin install vibe-memory --marketplace vibememory/vibememory
```

Choose user, project, or local scope in Claude Code's review UI. On older Claude
Code versions, register the marketplace and install in two steps:

```text
/plugin marketplace add vibememory/vibememory
/plugin install vibe-memory@vibe-memory
```

The plugin packages `SessionStart`, `Stop`, and `PreCompact` command hooks using
Claude Code's standard `hooks/hooks.json` layout. A missing CLI, expired login,
network failure, timeout, or malformed hook input is logged and exits successfully;
it never blocks a response, tool call, or compaction.

If marketplace plugins are unavailable, merge the following entries into the
existing top-level `hooks` object in `~/.claude/settings.json` (user scope) or
`.claude/settings.json` (project scope). Do not replace unrelated existing hook
arrays; append the Vibe Memory groups for the same event instead.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "vibe-memory",
            "args": ["hook", "session-start"],
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "vibe-memory",
            "args": ["hook", "stop"],
            "timeout": 5
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "vibe-memory",
            "args": ["hook", "pre-compact"],
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

The plugin and manual configuration are alternatives. Do not enable both, or
each lifecycle event will run twice.

### Hook behavior

- `vibe-memory hook session-start` derives the repository directory name and,
  when available, the local branch and abbreviated commit as search keywords,
  then fetches a bounded candidate set. It excludes only session checkpoints whose
  server-provided `correction_status` is exactly `superseded`, and puts the
  newest current checkpoint before related facts and decisions. Conflicts,
  cycles, partial corrections, and unresolved claims remain eligible for the
  four-record output. It also checks up to four queued handoffs and injects a
  compact untrusted-data reminder before the first prompt.
- `vibe-memory hook stop` fingerprints `HEAD` plus porcelain Git status. It emits
  one checkpoint reminder with the local branch, abbreviated commit, and
  clean/dirty state when that fingerprint changes or 20 minutes elapse,
  and records its state in the local Vibe Memory config directory. An immediately
  repeated Stop event with the same state stays silent.
- `vibe-memory hook pre-compact` records a local pending marker and does not block
  compaction. Claude Code currently does not support adding model context from a
  `PreCompact` hook without using a blocking decision, so the following
  `SessionStart` event with source `compact` delivers the reminder safely.

The reminder makes the boundary explicit: Git cannot recover uncommitted content,
and no file content is read or copied by the hook. The local hook state contains
hashes, timestamps, and a boolean marker only. It
does not contain credentials or conversation text. Delete `hook-state.json` next
to `client.json` to reset deduplication without disconnecting the CLI.

## Codex

Codex CLI/Desktop 0.166.0 or later discovers user hooks at
`~/.codex/hooks.json` and project hooks at `.codex/hooks.json`. Copy or merge
`agent-adapters/codex/hooks.json` into one of those locations after putting the
verified `vibe-memory` binary on `PATH`. Do not overwrite unrelated hook groups.

Open `/hooks` in Codex, review the exact definitions, and trust the three Vibe
Memory hooks. `SessionStart`, `Stop`, and `PreCompact` map directly to the CLI
contract. Disable or remove individual entries in `/hooks`, or delete only the
Vibe Memory groups from the chosen file, to opt out. Re-copy the shipped file
after an upgrade and review its new hash. Command hooks require local execution;
they do not run in Work Cloud without local access.

## Hermes Agent

Hermes Agent 0.22.5 is the verified floor; an earlier first release for every
required shell-hook event has not been established. Copy
`agent-adapters/hermes/vibe_memory_hook.py` to an operator-reviewed path and
merge the entries from `config.example.yaml` into the active Hermes profile.
Replace `/ABSOLUTE/PATH` first. Keep `hooks_auto_accept: false`: Hermes will ask
for first-use consent for each `(event, command)` pair.

The adapter maps `pre_llm_call` to first-turn or post-compaction recall,
`pre_verify` to a coding checkpoint pass, `post_compaction` to a pending marker,
and `on_session_finalize` to a user-visible final reminder. Observation-only
Hermes session-end events cannot force another model pass, so a non-coding delta
may be handled on the next prompt. Set `VIBE_MEMORY_PROJECT_ROOTS` to an
OS-path-separated allowlist when hooks must be restricted to selected roots.

Use `hermes hooks list`, `hermes hooks doctor`, and `hermes hooks test EVENT` to
inspect activity. Update by replacing the adapter file and re-running `doctor`.
Remove its four config entries and run `hermes hooks revoke COMMAND` for each
approved command to uninstall it.

## OpenClaw

OpenClaw 2026.10.9 or later can review and link the native plugin:

```text
openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities
openclaw plugins enable vibe-memory-hooks
```

Then explicitly allow the prompt/finalization hooks in `openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "vibe-memory-hooks": {
        "enabled": true,
        "hooks": {
          "allowConversationAccess": true,
          "allowPromptInjection": true
        },
        "config": {
          "autoRecall": true,
          "autoCheckpoint": true,
          "projectRoots": ["/absolute/project/root"]
        }
      }
    }
  }
}
```

`before_prompt_build` recalls once per session, `before_agent_finalize` requests
at most one checkpoint revision, and `before_compaction` leaves a pending marker.
The `--accept-capabilities` flag acknowledges that this locally reviewed native
plugin registers prompt and finalization hooks; the separate configuration grant
below still controls conversation access and prompt injection. The plugin passes
only sanitized lifecycle metadata to the CLI. Verify loaded
registrations with `openclaw plugins inspect vibe-memory-hooks --runtime --json`.
Use `openclaw plugins reload vibe-memory-hooks` after updates, or
`openclaw plugins uninstall vibe-memory-hooks` to remove it. Harnesses that do
not emit `before_agent_finalize` cannot force the final checkpoint pass.

## MCP and fallback behavior

MCP is available independently of lifecycle hooks. Hermes can configure the
remote URL under `mcp_servers`; OpenClaw can run
`openclaw mcp add vibe-memory --url https://vibememory.io/mcp --transport streamable-http`;
Codex and Claude can use their existing MCP connection flows. OAuth approval is
handled by the host. Hook adapters do not require or introduce SSE.

When a lifecycle adapter is unavailable, follow the proactive loop in the
distributed `SKILL.md`: recall before substantial work, compare against the
latest valid checkpoint, and store only a meaningful durable delta related with
`SUPERSEDES`. The implementation performs no server-side LLM or Git work. See
[the common adapter contract](agent-hook-adapter-spec.md) and the generated
[support matrix](agent-support.md).
