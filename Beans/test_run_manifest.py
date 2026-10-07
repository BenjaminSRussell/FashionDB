import json
from pathlib import Path

from run import write_run_manifest


def test_write_run_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = write_run_manifest({"status": "ok", "input": "fixture"}, path="data/run_manifest.json")
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["status"] == "ok"
    assert data["input"] == "fixture"
