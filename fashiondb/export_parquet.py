"""Export rules JSON to Parquet for wardrobe-kingdom joins (#13)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


JOIN_COLUMNS = (
    "id",
    "claim",
    "category",
    "formality",
    "confidence",
    "polarity",
    "strength",
)


def rules_to_rows(data: dict | list) -> list[dict]:
    rules = data.get("rules", data if isinstance(data, list) else [])
    rows = []
    for r in rules:
        ctx = r.get("context") or {}
        rows.append(
            {
                "id": r.get("id") or "",
                "claim": r.get("claim") or r.get("rule_text") or "",
                "category": r.get("category") or "",
                "formality": ctx.get("dress_code_level") or r.get("formality") or "",
                "confidence": float(r.get("confidence") or 0),
                "polarity": r.get("polarity") or "",
                "strength": r.get("strength") or "",
            }
        )
    return rows


def write_parquet(rows: list[dict], out: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        # Fallback: write CSV with .parquet.tsv note when pyarrow missing in CI
        raise SystemExit("pyarrow required for parquet export: pip install pyarrow")
    table = pa.Table.from_pylist(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fashiondb export")
    p.add_argument("--rules", type=Path, required=True, help="rules JSON")
    p.add_argument("--format", choices=["parquet"], default="parquet")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    data = json.loads(args.rules.read_text(encoding="utf-8"))
    rows = rules_to_rows(data)
    if args.format == "parquet":
        write_parquet(rows, args.out)
    print(f"wrote {len(rows)} rows → {args.out}")
    print("join keys:", ", ".join(JOIN_COLUMNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
