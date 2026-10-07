import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Data Analysis" / "src" / "zsc_test.py"
FIXTURE = ROOT / "Data Analysis" / "tests" / "fixtures" / "reddit_comments_sample.json"


def test_stub_deterministic(tmp_path):
    out1 = tmp_path / "a.jsonl"
    out2 = tmp_path / "b.jsonl"
    for out in (out1, out2):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--stub", "--seed", "7", "--out", str(out), "--input", str(FIXTURE)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
    assert out1.read_text() == out2.read_text()
    rows = [json.loads(l) for l in out1.read_text().splitlines() if l.strip()]
    assert rows and "label" in rows[0] and "comment_sha" in rows[0]


def test_missing_input_exits_2():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stub", "--input", "/no/such/file.json"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
