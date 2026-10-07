#!/usr/bin/env python3
import json, sys, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "data_analysis" / "src"))
from fashion_rule_extractor import load_posts
def main():
    nested = {"malefashionadvice": [{"id": "t1", "title": "White socks?", "selftext": "x", "comments": []}]}
    unique = [{"id": "t1", "title": "White socks?", "selftext": "x", "comments": []}]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td/"n.json").write_text(json.dumps(nested))
        (td/"u.json").write_text(json.dumps(unique))
        assert len(load_posts(td/"n.json"))==1
        assert len(load_posts(td/"u.json"))==1
        print("ok")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
