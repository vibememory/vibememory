import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path


def load_runner():
    path = Path(__file__).parents[1] / "conformance" / "run.py"
    spec = importlib.util.spec_from_file_location("vibe_conformance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_conformance_fixture_and_status_reporting(tmp_path):
    runner = load_runner()
    assert len(runner.fixture_hash()) == 64
    assert runner.check("pass", lambda: True)["status"] == "passed"

    def unsupported():
        raise runner.Unsupported("OAuth token required")

    skipped = runner.check("mcp", unsupported, capability="mcp")
    assert skipped["status"] == "unsupported"
    assert skipped["reason"] == "OAuth token required"

    report = tmp_path / "conformance.xml"
    runner.write_junit(
        report,
        [
            runner.check("pass", lambda: True),
            skipped,
            runner.check("fail", lambda: False),
        ],
    )
    suite = ET.parse(report).getroot()
    assert suite.attrib == {
        "name": "vibe-memory-black-box",
        "tests": "3",
        "failures": "1",
        "skipped": "1",
    }
