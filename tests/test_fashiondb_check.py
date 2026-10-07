import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fashiondb.check import main as check_main


def test_check_passes_ok_wardrobe(tmp_path):
    report = tmp_path / "r.json"
    rc = check_main([
        "--wardrobe", str(ROOT / "tests/fixtures/wardrobe_ok.csv"),
        "--rules", str(ROOT / "tests/fixtures/rules.db"),
        "--json-report", str(report),
    ])
    assert rc == 0
    assert json.loads(report.read_text())["ok"] is True


def test_check_fails_on_violation(tmp_path):
    report = tmp_path / "r.json"
    rc = check_main([
        "--wardrobe", str(ROOT / "tests/fixtures/wardrobe_bad.csv"),
        "--rules", str(ROOT / "tests/fixtures/rules_sample.json"),
        "--json-report", str(report),
    ])
    assert rc == 1
    data = json.loads(report.read_text())
    assert data["ok"] is False and data["violations"]
