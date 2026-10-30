import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "check_plugin_submission.py"


def run_checker(*args):
    return subprocess.run(
        [sys.executable, str(CHECKER), "--site-dir", str(ROOT / "landing" / "dist"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_submission_source_is_valid_with_explicit_external_blockers(tmp_path):
    report = tmp_path / "report.json"
    result = run_checker("--acknowledge-blockers", "--report-json", str(report))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(report.read_text())
    assert payload["errors"] == []
    assert payload["ready"] is False
    assert {item["code"] for item in payload["blockers"]} == {
        "privacyPolicyURL",
        "termsOfServiceURL",
        "demo_recording_url",
        "reviewer_access",
        "portal_identity",
        "portal_countries",
    }


def test_submission_archive_is_refused_until_external_gates_are_complete(tmp_path):
    archive = tmp_path / "plugin.zip"
    result = run_checker("--archive", str(archive))
    assert result.returncode == 1
    assert "BLOCKED 6 public-submission prerequisite" in result.stdout
    assert not archive.exists()
