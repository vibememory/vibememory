# Black-box conformance profile

Run the core REST profile only against a disposable account. The runner creates retained test data and performs no LLM calls:

```sh
python3 conformance/run.py \
  --base-url http://localhost:8080 \
  --token DISPOSABLE_TOKEN \
  --junit conformance-results.xml
```

The current core profile checks create, explicit idempotency, exact keyword search, stable IDs and initial optimistic versioning. The JSON result is written to stdout; `--junit` adds a CI-readable report. Namespace, portable-archive, valid-time and MCP behavior are advertised extensions and must not be reported as core support unless discovery exposes them.
