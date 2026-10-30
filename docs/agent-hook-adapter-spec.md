# Vibe Memory Hook Adapter Contract

The common adapter contract maps host lifecycle events to the released native
CLI. Adapters do not call the REST API directly, run an LLM, summarize a
transcript, or execute Git on the server. Any local Git fingerprint used for
deduplication runs inside the user's CLI environment.

## CLI boundary

An adapter may invoke only these fixed commands, without a shell:

- `vibe-memory hook session-start`
- `vibe-memory hook stop`
- `vibe-memory hook pre-compact`

Each command receives one JSON object on stdin. The adapter forwards only
`session_id`, `cwd`, `source`, and `stop_hook_active`. It must omit prompts,
transcripts, assistant messages, tool inputs and results, hidden reasoning,
environment variables, and credentials. Input and output are capped at 64 KiB;
timeouts are at most 10 seconds; every operational error fails open.

After receiving this metadata, the local CLI may derive a repository directory,
branch, abbreviated commit, and a one-way Git-state fingerprint. It never reads
file contents for the hook; the server never executes Git. `session-start` can
return `hookSpecificOutput.additionalContext` containing a
bounded recall result. `stop` can return the same field containing a
deduplicated instruction for the connected agent to select and save a durable
delta. `pre-compact` writes only a private local pending marker and returns no
model context.

## Common lifecycle mapping

| Common event | Meaning | CLI action |
| --- | --- | --- |
| `on_session_start` / `before_prompt` | A fresh or compacted context is about to reach the model | `session-start` |
| `after_turn` / `on_session_end` | A host is about to accept or leave a completed turn | `stop` |
| `before_compact` / committed compaction | Context is about to be or has been compacted | `pre-compact`, then recall on the next prompt |

Hosts with an observation-only end hook move the checkpoint reminder to their
next prompt or a supported finalization gate. That limitation must be visible in
the shared support matrix.

## Consent and scope

Adapters are disabled until the user installs and trusts the relevant hook or
plugin. User/project hook scope, Cursor hook files, Muse workspace trust, Hermes
profiles, OpenClaw `projectRoots`, or an equivalent host setting limits where the
adapter runs. Users can disable recall
and checkpoint hooks independently where the host supports it. Host hook
inspection and activity logs remain the source of truth; Vibe Memory does not
add a second telemetry stream or require SSE.

The checkpoint instruction is not authority to store a conversation. The
connected agent still excludes secrets, full transcripts, incidental personal
data, hidden reasoning, speculative conclusions, and raw tool output. Vault
values, SSH keys, tokens, and local environment variables are never hook input.
