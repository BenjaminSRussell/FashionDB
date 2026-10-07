
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Data Analysis" / "src"))

import Spell_check as sc


class FakeModel:
    def get_topic_info(self):
        return [{"topic_id": 0, "count": 2, "top_terms": "loafer oxford"}]

    def get_topic(self, _tid):
        return [("loafer", 0.5), ("oxford", 0.4)]


def test_spell_map_and_out(tmp_path):
    data = {
        "menswear": [
            {
                "title": "beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beutiful beautiful beautiful beautiful beautiful beautiful beautiful beautiful beautiful",
                "comments": [{"body": "nice shoes"}],
            },
            {"title": "oxford oxford oxford", "comments": []},
        ]
    }
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps(data))
    map_csv = tmp_path / "map.csv"
    changes = tmp_path / "changes.csv"
    out = tmp_path / "topics.csv"

    def fake_fit(docs):
        assert len(docs) >= 2
        return FakeModel(), [0] * len(docs)

    result = sc.run(
        input_path=str(inp),
        out=str(out),
        map_csv=str(map_csv),
        changes_csv=str(changes),
        top_k=20,
        min_misspell=5,
        min_ratio=3,
        min_sim=0.7,
        min_topic_size=2,
        fit_transform=fake_fit,
    )
    assert map_csv.exists() and changes.exists() and out.exists()
    assert "beutiful" in map_csv.read_text()
    assert "topic_id" in out.read_text()
    assert result["docs"] >= 2
