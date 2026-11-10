#!/usr/bin/env python3
"""Summarize opt-in, manually timed human effort across three agent conditions."""

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

CONDITIONS = ("single_agent", "multi_agent_chat", "multi_agent_vibe_memory")
INTERVENTION_KINDS = {"re_explanation", "reassignment", "correction"}


def _number(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a nonnegative number")
    return float(value)


def validate(experiment):
    if experiment.get("profile") != "human-handoff-effort-v1":
        raise ValueError("profile must be human-handoff-effort-v1")
    controls = experiment.get("controls")
    required_controls = {
        "task_fixture",
        "task_fixture_sha256",
        "model",
        "tools",
        "permissions",
        "inputs",
        "completion_criteria",
    }
    if not isinstance(controls, dict) or not required_controls <= set(controls):
        raise ValueError("controls must record task, model, tools, permissions, inputs, and criteria")
    if not isinstance(experiment.get("runs"), list) or not experiment["runs"]:
        raise ValueError("runs must be a non-empty array")

    repetitions = defaultdict(set)
    for index, run in enumerate(experiment["runs"]):
        condition = run.get("condition")
        if condition not in CONDITIONS:
            raise ValueError(f"runs[{index}].condition is unsupported")
        repetition = run.get("repetition")
        if not isinstance(repetition, int) or isinstance(repetition, bool) or repetition < 1:
            raise ValueError(f"runs[{index}].repetition must be a positive integer")
        if repetition in repetitions[condition]:
            raise ValueError(f"duplicate repetition {repetition} for {condition}")
        repetitions[condition].add(repetition)
        _number(run.get("wall_time_minutes"), f"runs[{index}].wall_time_minutes")
        rework = run.get("rework_events")
        if not isinstance(rework, int) or isinstance(rework, bool) or rework < 0:
            raise ValueError(f"runs[{index}].rework_events must be a nonnegative integer")
        if not isinstance(run.get("completed"), bool):
            raise ValueError(f"runs[{index}].completed must be boolean")
        if not isinstance(run.get("completion_criteria_passed"), bool):
            raise ValueError(f"runs[{index}].completion_criteria_passed must be boolean")
        interventions = run.get("human_interventions")
        if not isinstance(interventions, list):
            raise ValueError(f"runs[{index}].human_interventions must be an array")
        for item_index, item in enumerate(interventions):
            if item.get("kind") not in INTERVENTION_KINDS:
                raise ValueError(
                    f"runs[{index}].human_interventions[{item_index}].kind is unsupported"
                )
            _number(
                item.get("minutes"),
                f"runs[{index}].human_interventions[{item_index}].minutes",
            )
    expected = repetitions[CONDITIONS[0]]
    if not expected or any(repetitions[condition] != expected for condition in CONDITIONS[1:]):
        raise ValueError("all three conditions must contain the same repetition numbers")


def _run_metrics(run):
    interventions = run["human_interventions"]
    by_kind = {
        kind: sum(float(item["minutes"]) for item in interventions if item["kind"] == kind)
        for kind in sorted(INTERVENTION_KINDS)
    }
    return {
        "human_minutes": sum(by_kind.values()),
        "human_minutes_by_kind": by_kind,
        "interventions": len(interventions),
        "wall_time_minutes": float(run["wall_time_minutes"]),
        "completion_rate": 1.0 if run["completed"] else 0.0,
        "criteria_pass_rate": 1.0 if run["completion_criteria_passed"] else 0.0,
        "rework_events": run["rework_events"],
    }


def summarize(experiment, source_bytes=None):
    validate(experiment)
    grouped = defaultdict(list)
    for run in experiment["runs"]:
        grouped[run["condition"]].append(_run_metrics(run))

    conditions = {}
    for condition in CONDITIONS:
        rows = grouped[condition]
        conditions[condition] = {
            "runs": len(rows),
            **{
                field: round(statistics.mean(row[field] for row in rows), 3)
                for field in (
                    "human_minutes",
                    "interventions",
                    "wall_time_minutes",
                    "completion_rate",
                    "criteria_pass_rate",
                    "rework_events",
                )
            },
            "human_minutes_by_kind": {
                kind: round(
                    statistics.mean(row["human_minutes_by_kind"][kind] for row in rows), 3
                )
                for kind in sorted(INTERVENTION_KINDS)
            },
        }

    vibe = conditions["multi_agent_vibe_memory"]
    comparisons = {}
    for baseline_name in ("single_agent", "multi_agent_chat"):
        baseline = conditions[baseline_name]
        baseline_minutes = baseline["human_minutes"]
        saved = baseline_minutes - vibe["human_minutes"]
        comparisons[f"vibe_memory_vs_{baseline_name}"] = {
            "human_minutes_saved": round(saved, 3),
            "human_time_change_percent": (
                None if baseline_minutes == 0 else round(saved / baseline_minutes * 100, 3)
            ),
            "intervention_change": round(vibe["interventions"] - baseline["interventions"], 3),
            "wall_time_change_minutes": round(
                vibe["wall_time_minutes"] - baseline["wall_time_minutes"], 3
            ),
            "completion_rate_change": round(
                vibe["completion_rate"] - baseline["completion_rate"], 3
            ),
            "criteria_pass_rate_change": round(
                vibe["criteria_pass_rate"] - baseline["criteria_pass_rate"], 3
            ),
            "rework_change": round(vibe["rework_events"] - baseline["rework_events"], 3),
        }

    canonical = source_bytes or json.dumps(
        experiment, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "profile": "human-handoff-effort-report-v1",
        "experiment_id": experiment.get("experiment_id", ""),
        "synthetic": bool(experiment.get("synthetic", False)),
        "input_sha256": hashlib.sha256(canonical).hexdigest(),
        "controls": experiment["controls"],
        "conditions": conditions,
        "comparisons": comparisons,
        "quality_warning": (
            "Vibe Memory condition did not pass the same completion criteria in every run."
            if vibe["criteria_pass_rate"] < 1
            else None
        ),
        "measurement": "voluntary_manual_timer",
        "server_llm_calls": 0,
        "default_telemetry": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Summarize manually timed single-agent and handoff experiment runs"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.input.read_bytes()
    report = summarize(json.loads(source), source)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
