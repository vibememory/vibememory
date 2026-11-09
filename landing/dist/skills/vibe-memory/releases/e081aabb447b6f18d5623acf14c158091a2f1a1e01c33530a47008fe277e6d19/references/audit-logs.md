# Per-agent operational audit logs

Use the append-only audit ledger for concise evidence that a meaningful action was attempted and what outcome was observed. Good candidates include production deployment or verification, permission and security changes, external publication, destructive maintenance, release creation, and administrator operations. Ordinary reads, internal reasoning, every shell command, and every memory write do not need an audit entry.

Submit only after the action has an observed outcome:

```sh
"$VM_CLI" audit submit release.verify "Production health and version checks passed." \
  --outcome success \
  --resource-type deployment \
  --resource-id v0.37.0 \
  --metadata '{"environment":"production","checks":3}' \
  --occurred-at 2026-11-09T01:30:00Z \
  --retry-id release-verify-v037
```

Use a stable lowercase action such as `release.publish`, `deployment.verify`, `permission.update`, or `external.post`. Choose `success`, `failure`, `denied`, or `skipped`. Keep `summary` factual and short. `occurred_at` must include an offset and is normalized to UTC; the server separately records its own receive time. Use a stable retry ID when rerunning the same submission.

Never include a secret, API key, token, password, cookie, authorization header, Vault value, full prompt, full transcript, chain-of-thought, raw environment dump, or noisy tool output. The service rejects common sensitive metadata keys, but the agent remains responsible for sanitizing both values and prose. Prefer counts, result codes, version numbers, public URLs, and non-secret resource identifiers.

`audit list` and `audit get ID` expose only entries bound to the exact authenticated agent connection. They do not prove that an agent-authored statement is true; they prove which authenticated connection submitted the claim and when the server received it. The owner console can filter all of that owner's agent entries. Records cannot be edited or deleted through the audit API.
