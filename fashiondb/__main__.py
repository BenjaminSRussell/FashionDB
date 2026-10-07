"""python -m fashiondb <command>"""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: python -m fashiondb check|export|migrate-json|embed-rules|similar|explore|…")
        return 2
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "check":
        from fashiondb.check import main as check_main

        return check_main(rest)
    if cmd == "export":
        from fashiondb.export_parquet import main as export_main

        return export_main(rest)
    if cmd in {"migrate-json", "migrate_json"}:
        from fashiondb.migrate_json import main as migrate_main

        return migrate_main(rest)
    if cmd in {"embed-rules", "embed_rules"}:
        from fashiondb.embeddings import embed_rules_from_db

        n = embed_rules_from_db()
        print(f"embedded {n} rules")
        return 0
    if cmd == "similar":
        import argparse
        from fashiondb.db import connect
        from fashiondb.embeddings import similar

        ap = argparse.ArgumentParser()
        ap.add_argument("query")
        ap.add_argument("--top-k", type=int, default=5)
        ns = ap.parse_args(rest)
        conn = connect()
        for hit in similar(conn, ns.query, top_k=ns.top_k):
            print(f"{hit['score']:.4f}\t{hit['owner_id']}\t{hit['model']}")
        conn.close()
        return 0
    if cmd == "explore":
        from fashiondb.explorer import main as explore_main

        return explore_main(rest)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
