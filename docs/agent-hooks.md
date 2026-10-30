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

- `vibe-memory hook session-start` extracts only the repository directory name,
  fetches a bounded candidate set, excludes only session checkpoints whose
  server-provided `correction_status` is exactly `superseded`, and puts the
  newest current checkpoint before related facts and decisions. Conflicts,
  cycles, partial corrections, and unresolved claims remain eligible for the
  four-record output. It also checks up to four queued handoffs and injects a
  compact untrusted-data reminder before the first prompt.
- `vibe-memory hook stop` fingerprints `HEAD` plus porcelain Git status. It emits
  one checkpoint reminder when that fingerprint changes or 20 minutes elapse,
  and records its state in the local Vibe Memory config directory. An immediately
  repeated Stop event with the same state stays silent.
- `vibe-memory hook pre-compact` records a local pending marker and does not block
  compaction. Claude Code currently does not support adding model context from a
  `PreCompact` hook without using a blocking decision, so the following
  `SessionStart` event with source `compact` delivers the reminder safely.

The local hook state contains hashes, timestamps, and a boolean marker only. It
does not contain credentials or conversation text. Delete `hook-state.json` next
to `client.json` to reset deduplication without disconnecting the CLI.

## Codex, OpenClaw, Hermes, and other agents

The same CLI commands are vendor-neutral even when the host has no Claude-style
plugin system:

1. At session start, run `vibe-memory recall PROJECT "session checkpoint"` and
   `vibe-memory message inbox --status queued`.
2. At natural checkpoints, compare durable state with the latest checkpoint and
   write only a meaningful delta. Relate the new record to the previous one with
   `SUPERSEDES`.
3. Before handoff or compaction, save accepted decisions, verified milestones,
   blockers, and next actions. Never save a full transcript, secrets, hidden
   reasoning, speculation, or raw tool logs.

Hosts that expose lifecycle command hooks may invoke the three `vibe-memory hook`
subcommands with the same JSON fields used by Claude Code (`session_id`, `cwd`,
and `stop_hook_active`). Hosts without hooks follow the proactive loop in the
distributed `SKILL.md`; unavailable memory must not block the user's task.

The hook implementation performs no LLM calls or server-side inference. The
connected agent remains responsible for extracting keywords and deciding what is
durable enough to store.
