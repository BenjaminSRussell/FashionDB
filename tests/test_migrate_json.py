from pathlib import Path

from fashiondb.db import connect, count_rules, export_rules_json
from fashiondb.migrate_json import migrate_file


def test_migrate_sample_roundtrip(tmp_path):
    db = tmp_path / "f.db"
    conn = connect(db)
    sample = Path("tests/fixtures/rules_sample.json")
    n = migrate_file(conn, sample, "rules_sample")
    conn.commit()
    assert n == 2
    assert count_rules(conn) == 2
    # re-migrate is idempotent by rule_key
    migrate_file(conn, sample, "rules_sample")
    conn.commit()
    assert count_rules(conn) == 2
    exported = export_rules_json(conn)
    claims = {r["claim"] for r in exported["rules"]}
    assert "Never wear white socks with a business suit" in claims
    conn.close()


def test_beans_fixture_migrates(tmp_path):
    db = tmp_path / "f.db"
    conn = connect(db)
    sample = Path("Beans/data/fixtures/sample_rules.json")
    n = migrate_file(conn, sample, "beans_sample")
    conn.commit()
    assert n == 2
    assert count_rules(conn) == 2
    conn.close()
