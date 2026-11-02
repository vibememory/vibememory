# Black-box conformance profile

Run the core REST profile only against a disposable account. The runner creates retained test data and performs no LLM calls:

```sh
python3 conformance/run.py \
  --base-url http://localhost:8080 \
  --token DISPOSABLE_TOKEN \
  --contract-version 1.1 \
  --junit conformance-results.xml \
  --output conformance-results.json
```

The profile checks public contract discovery and version negotiation, create and explicit idempotency conflict behavior, exact keyword search, stable IDs, optimistic version conflicts, authenticated writer attribution, quarantine defaults, correction semantics, batch partial success and basic pagination. Output includes contract/server versions, UTC execution time, a deterministic fixture SHA-256 and per-capability `passed`, `failed` or `unsupported` states. `--junit` adds a CI-readable report.

MCP uses a separately authorized OAuth access token. Supply `--mcp-token` to verify initialize/tool discovery and the capability mapping; otherwise the MCP item is explicitly `unsupported` and the report sets `complete=false` instead of claiming a false pass. Namespace administration, portable file archives and historical recorded-time reconstruction remain advertised extensions and require dedicated disposable fixtures.

The runner retains synthetic data. Never point it at a personal or production account. A passing report covers only the advertised contract checks, not security certification, search-ranking equivalence or model behavior.
