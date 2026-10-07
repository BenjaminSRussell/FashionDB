import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data_analysis" / "src"))

from reddit_unique_records import DATA_DIR as UNIQUE_DIR
from fashion_rule_extractor import DATA_DIR as EXTRACT_DIR, load_posts


def test_default_data_dirs_are_repo_root_data():
    assert UNIQUE_DIR.resolve() == (ROOT / "data").resolve()
    assert EXTRACT_DIR.resolve() == (ROOT / "data").resolve()


def test_load_posts_accepts_list_and_nested_dict(tmp_path):
    nested = {"mfa": [{"id": "1", "title": "a", "comments": []}]}
    flat = [{"id": "2", "title": "b", "comments": []}]
    p1 = tmp_path / "n.json"
    p2 = tmp_path / "f.json"
    p1.write_text(json.dumps(nested))
    p2.write_text(json.dumps(flat))
    assert len(load_posts(p1)) == 1
    assert len(load_posts(p2)) == 1
