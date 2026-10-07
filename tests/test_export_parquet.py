import json
from pathlib import Path
import sys
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pyarrow = pytest.importorskip("pyarrow")
from fashiondb.export_parquet import main as export_main, rules_to_rows


def test_export_parquet(tmp_path):
    src = ROOT / "tests/fixtures/rules_sample.json"
    out = tmp_path / "rules.parquet"
    rc = export_main(["--rules", str(src), "--out", str(out)])
    assert rc == 0 and out.exists()
    import pyarrow.parquet as pq
    table = pq.read_table(out)
    assert table.num_rows == 2
    assert "category" in table.column_names
