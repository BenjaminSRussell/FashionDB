from pathlib import Path
from fashiondb.db import connect
from fashiondb.embeddings import embed_rules_from_db, similar
from fashiondb.migrate_json import migrate_file

def test_embed_and_similar(tmp_path):
    db = tmp_path / "f.db"
    conn = connect(db)
    migrate_file(conn, Path("tests/fixtures/rules_sample.json"), "sample")
    conn.commit(); conn.close()
    assert embed_rules_from_db(db) == 2
    conn = connect(db)
    hits = similar(conn, "white socks business suit", top_k=2)
    conn.close()
    assert hits and hits[0]["score"] > 0
