"""Gradio wardrobe / rules explorer (#3)."""
from __future__ import annotations

from pathlib import Path

from fashiondb.db import connect, count_rules, export_rules_json
from fashiondb.embeddings import embed_rules_from_db, similar
from fashiondb.migrate_json import migrate_file


def _ensure_sample_db(db_path: Path) -> None:
    conn = connect(db_path)
    if count_rules(conn) == 0:
        sample = Path("tests/fixtures/rules_sample.json")
        if sample.exists():
            migrate_file(conn, sample, "rules_sample")
            conn.commit()
    conn.close()
    embed_rules_from_db(db_path)


def build_app(db_path: str | Path | None = None):
    import gradio as gr

    db = Path(db_path) if db_path else Path("data") / "fashiondb.db"
    _ensure_sample_db(db)

    def list_filtered(category: str, min_conf: float, q: str):
        conn = connect(db)
        rows = export_rules_json(conn)["rules"]
        conn.close()
        out = []
        for r in rows:
            if category and category != "all" and (r.get("category") or "") != category:
                continue
            conf = float(r.get("confidence") or 0)
            if conf < min_conf:
                continue
            if q and q.lower() not in (r.get("claim") or "").lower():
                continue
            out.append(
                [
                    r.get("id"),
                    r.get("category"),
                    r.get("claim"),
                    conf,
                    r.get("polarity"),
                ]
            )
        return out or [["", "", "No rules match", "", ""]]

    def outfit_test(items: str):
        conn = connect(db)
        hits = similar(conn, items or "outfit", owner_type="rule", top_k=5)
        # join claims
        claims = {
            r["id"]: r["claim"]
            for r in export_rules_json(conn)["rules"]
        }
        conn.close()
        return [[h["owner_id"], claims.get(h["owner_id"], ""), round(h["score"], 4), h["model"]] for h in hits]

    cats = ["all", "socks", "fit", "color", "style", "formality", "accessories"]
    with gr.Blocks(title="FashionDB Explorer") as demo:
        gr.Markdown("# FashionDB rule explorer\nFilter scraped rules and test outfit text against embeddings.")
        with gr.Tab("Rules"):
            cat = gr.Dropdown(cats, value="all", label="Category")
            conf = gr.Slider(0, 1, value=0.0, step=0.05, label="Min confidence")
            query = gr.Textbox(label="Search claim text")
            btn = gr.Button("Filter")
            table = gr.Dataframe(headers=["id", "category", "claim", "confidence", "polarity"], interactive=False)
            btn.click(list_filtered, [cat, conf, query], table)
            demo.load(lambda: list_filtered("all", 0.0, ""), outputs=table)
        with gr.Tab("Outfit match"):
            items = gr.Textbox(label="Wardrobe items / outfit description", lines=3)
            go = gr.Button("Find related rules")
            hits = gr.Dataframe(headers=["rule_key", "claim", "score", "model"], interactive=False)
            go.click(outfit_test, items, hits)
    return demo


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Launch FashionDB Gradio explorer")
    ap.add_argument("--db", default=None)
    ap.add_argument("--share", action="store_true")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args(argv)
    demo = build_app(args.db)
    demo.launch(share=args.share, server_port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
