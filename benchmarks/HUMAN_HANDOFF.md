# Human handoff effort benchmark

This opt-in offline protocol compares the same task under three conditions:

1. one agent;
2. multiple agents with chat-only handoff;
3. multiple agents with Vibe Memory handoff.

It measures human re-explanation, reassignment, and correction minutes separately
from intervention count, wall time, completion, the shared completion criteria, and
rework. It does not call a server or model, add telemetry, or infer timer values.

Before any run, freeze the task fixture and hash, model/version, tools, permissions,
inputs, completion criteria, repetition count, and assignment policy. Randomize or
rotate arm order when practical. A person starts and stops the timer only while
actively re-explaining, reassigning, or correcting work. Record zero explicitly;
do not estimate missing timings after the fact. Keep failed and low-quality runs.

Copy `fixtures/human-handoff.json`, replace its clearly marked synthetic values with
observed runs, set `synthetic` to false, and run:

```sh
python3 benchmarks/human_handoff.py \
  --input .data/experiments/human-handoff.json \
  --output .data/experiments/human-handoff-report.json
```

The report gives per-arm means and Vibe Memory deltas against both baselines.
`human_minutes_saved` is positive when the Vibe Memory arm used less human time;
`human_time_change_percent` uses the baseline as denominator. A time reduction is
not a win if completion or criteria pass rates fall, so those deltas and rework are
reported alongside it. The included fixture is only a format example and must not
be cited as product performance.

The runner requires the same repetition numbers in every arm and hashes the exact
input file for reproducibility. The JSON shape is documented in
`benchmarks/human-handoff.schema.json`.
