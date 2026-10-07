"""python -m fashiondb <command>"""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: python -m fashiondb check|export|migrate-json|…")
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
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
