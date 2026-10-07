import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"


def test_check_passes_clean_wardrobe():
    from fashiondb.check import check_wardrobe
    report = check_wardrobe(FIX / "wardrobe_ok.csv", FIX / "rules.jsonl")
    assert report["ok"] is True
    assert report["checked"] == 2
    assert report["violations"] == []
    assert report["schema"] == "fashiondb.check.report.v1"


def test_check_fails_on_violation_and_exit_code():
    from fashiondb.check import check_wardrobe
    report = check_wardrobe(FIX / "wardrobe_bad.csv", FIX / "rules.jsonl")
    assert report["ok"] is False
    assert any(v["rule_id"] == "r_socks" for v in report["violations"])

    proc = subprocess.run(
        [sys.executable, "-m", "fashiondb", "check",
         "--wardrobe", str(FIX / "wardrobe_bad.csv"),
         "--rules", str(FIX / "rules.jsonl"), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
