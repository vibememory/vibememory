# ChatGPT public plugin submission readiness

This document prepares the existing `vibe-memory` package for public review. It does not claim that the package has been uploaded, reviewed, approved, or launched.

## Reproducible checks

Run the source and local-page check used by CI:

```bash
uv run python scripts/check_plugin_submission.py \
  --site-dir landing/dist \
  --acknowledge-blockers \
  --report-json dist/plugin-readiness.json
```

`--acknowledge-blockers` accepts only the external gaps recorded in `plugins/vibe-memory/submission-readiness.json`; ordinary validation errors still fail. A public upload ZIP is deliberately unavailable until every blocker is resolved. When the policy pages, demo, reviewer account, and portal checks are complete, remove the resolved blockers and run:

```bash
uv run python scripts/check_plugin_submission.py \
  --network \
  --archive dist/vibe-memory-plugin.zip \
  --report-json dist/plugin-readiness.json
```

The archive command inspects the live content and purpose of all four listing URLs, refuses root `.app.json` and app declarations, verifies the PNG, checks the five positive and three negative cases, imports the server source to verify boolean MCP annotations, and reopens the ZIP to verify its exact inventory. It never packages credentials, local hooks, `submission-readiness.json`, or unrelated source files.

## Review fixture

Create a dedicated reviewer account in a non-production workspace. Never place credentials in the repository or upload ZIP. The secure Developer Portal reviewer-access field must contain the login URL, workspace, sign-in method, and credentials. The account must contain only synthetic data:

- memory: `Review project uses UTC`, keywords `review project`, `UTC`, tag `plugin-review`;
- memory: `Review deploys on Friday`, keywords `review deployment`, `Friday`, tag `plugin-review`;
- a second related review-project record and explicit evidence-backed relationship for the Context Bundle case;
- fake Vault entry `REVIEW_SAMPLE_TOKEN`, explicitly granted to the submitted MCP connection, with a non-sensitive test value.

The eight cases in `plugin.json` cover keyword recall, durable creation, evidence-preserving correction, bounded Context Bundle handoff, Vault metadata, file-analysis boundaries, owner isolation, and refusal to execute purchases. Record each run here or in an attached reviewer worksheet as **Passed**, **Failed**, **Blocked**, or **Not run**. Current status: all cases are **Not run** because the dedicated reviewer access has not been verified.

## Demo recording order

1. Show the packaged version and the dedicated review workspace, without exposing credentials.
2. Connect through `https://vibememory.io/mcp` and complete OAuth consent.
3. Run the UTC recall case and show the supporting stored record.
4. Run the compact-JSON creation case and show the returned record ID.
5. Run the Thursday correction case and show the retained correction history.
6. Run the bounded Context Bundle case and show only explicit stored relationships.
7. Run the Vault metadata-only case without revealing its value.
8. Run one negative case and show that no prohibited tool call or fabricated success occurs.

Play back the real recording, verify readability and absence of secrets, host it at a reviewer-accessible HTTPS URL, then add the verified URL to `extensions.com.openai.review.demo_recording_url`. A script, screenshots, or a local recording does not complete this requirement.

## Publication declarations and remaining gates

- Intended verified publisher: `SEOKSONG SONG`; confirm the selected identity after saving in the Developer Portal.
- Country targeting: all supported countries. The manifest uses an explicit empty `publication.countries` list; inspect the saved portal value.
- Commerce: no payments and no purchases. Confirm the portal declaration.
- Privacy and terms: collect the operator decisions in `docs/plugin-policy-inputs.md`, obtain review, publish each page, and inspect the live content before adding its URL.
- Reviewer access: provide only through secure portal fields, never the package.
- Submission: do not mark uploaded, submitted, approved, or launched until that exact portal stage has actually completed.
