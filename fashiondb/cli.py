"""fashiondb CLI entrypoints."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fashiondb.check import REPORT_SCHEMA, check_wardrobe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fashiondb", description="FashionDB operator CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check_p = sub.add_parser("check", help="Check a wardrobe CSV against rules")
    check_p.add_argument("--wardrobe", required=True, type=Path, help="Wardrobe CSV path")
    check_p.add_argument("--rules", required=True, type=Path, help="Rules JSON/JSONL/SQLite path")
    check_p.add_argument("--json", action="store_true", help="Emit JSON report to stdout")
    check_p.add_argument("--schema", action="store_true", help="Print report JSON schema and exit")

    args = parser.parse_args(argv)
    if args.cmd == "check":
        if args.schema:
            print(json.dumps(REPORT_SCHEMA, indent=2))
            return 0
        report = check_wardrobe(args.wardrobe, args.rules)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"checked={report['checked']} violations={len(report['violations'])} ok={report['ok']}")
            for v in report["violations"]:
                print(f"- [{v['rule_id']}] {v['item']}: {v['message']}")
        return 0 if report["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
