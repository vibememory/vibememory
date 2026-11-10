import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "benchmarks" / "human_handoff.py"
FIXTURE = ROOT / "benchmarks" / "fixtures" / "human-handoff.json"


def module():
    spec = importlib.util.spec_from_file_location("human_handoff", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_human_handoff_report_compares_both_baselines_without_telemetry():
    experiment = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = module().summarize(experiment)
    assert report["synthetic"] is True
    assert report["server_llm_calls"] == 0
    assert report["default_telemetry"] is False
    assert report["conditions"]["multi_agent_vibe_memory"]["human_minutes"] == 1
    assert report["comparisons"]["vibe_memory_vs_single_agent"][
        "human_minutes_saved"
    ] == 1
    assert report["comparisons"]["vibe_memory_vs_multi_agent_chat"][
        "human_minutes_saved"
    ] == 5


def test_human_handoff_requires_matched_repetitions_and_quality_fields():
    experiment = json.loads(FIXTURE.read_text(encoding="utf-8"))
    experiment["runs"].pop()
    with pytest.raises(ValueError, match="same repetition"):
        module().summarize(experiment)
