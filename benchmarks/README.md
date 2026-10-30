# Deterministic handoff benchmark

The fixture is synthetic and contains no personal data. Agent A stores decisions, failures, corrections and todos; Agent B searches with supplied keywords and checks stable evidence IDs. The deterministic runner measures fixture recall, HTTP latency, and response bytes. Model-generated keyword/query evaluation, stale-claim adjudication, and quality scoring are separate opt-in profiles and never run in the deterministic benchmark.

Run it only with a disposable account:

```sh
python3 benchmarks/run.py --base-url http://localhost:8000 --token DISPOSABLE_TOKEN
```

The runner reports deterministic recall, mean/p95 HTTP latency and response bytes. It deliberately does not call an LLM or claim to measure model-side keyword extraction.
