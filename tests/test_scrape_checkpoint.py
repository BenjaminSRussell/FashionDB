from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "RedditDB"))
from scrape_checkpoint import CheckpointStore


def test_checkpoint_skips_seen(tmp_path):
    store = CheckpointStore(tmp_path / "cp.sqlite")
    store.set("malefashionadvice", "t3_bbb")
    assert store.should_skip("malefashionadvice", "t3_aaa") is True
    assert store.should_skip("malefashionadvice", "t3_ccc") is False
    assert store.should_skip("malefashionadvice", "t3_aaa", full=True) is False
