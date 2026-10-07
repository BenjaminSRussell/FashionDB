#!/usr/bin/env python3
"""Zero-shot fashion comment classifier (CLI, not a unit test).

Replaces the old Desktop-hardcoded script. Supports a stub classifier for CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

DEFAULT_LABELS = ["rules", "advice", "dos and don'ts"]


def load_comments(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"expected JSON list in {path}")
    comments: list[str] = []
    for post in data:
        for c in post.get("comments", []) if isinstance(post, dict) else []:
            body = (c or {}).get("body")
            if body and body not in ("[deleted]", "removed"):
                comments.append(body)
    return comments


def stub_classifier(text: str, labels: list[str]) -> dict[str, Any]:
    """Deterministic stub: keyword heuristics for CI without transformers."""
    lower = text.lower()
    scores = {lab: 0.1 for lab in labels}
    if any(k in lower for k in ("rule", "always", "never", "do:", "don't", "dont")):
        if "rules" in scores:
            scores["rules"] = 0.9
        if "dos and don'ts" in scores:
            scores["dos and don'ts"] = 0.8
    elif any(k in lower for k in ("should", "try", "recommend", "advice")):
        if "advice" in scores:
            scores["advice"] = 0.85
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return {"labels": [k for k, _ in ordered], "scores": [v for _, v in ordered]}


def make_hf_classifier(model: str) -> Callable[[str, list[str]], dict[str, Any]]:
    from transformers import pipeline

    clf = pipeline("zero-shot-classification", model=model)

    def _run(text: str, labels: list[str]) -> dict[str, Any]:
        return clf(text[:512], labels)

    return _run


def comment_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zero-shot classify fashion comments")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "reddit_comments_sample.json",
        help="JSON list of posts with comments[].body",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write JSONL results here")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-samples", type=int, default=10)
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Use deterministic stub classifier (no model download)",
    )
    parser.add_argument(
        "--model",
        default="typeform/distilbert-base-uncased-mnli",
        help="HF model when not using --stub",
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        default=DEFAULT_LABELS,
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    try:
        comments = load_comments(args.input)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"error: failed to load {args.input}: {e}", file=sys.stderr)
        return 2

    if not comments:
        print("error: no comments found", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    k = min(args.num_samples, len(comments))
    sample = rng.sample(comments, k)

    classify = stub_classifier if args.stub else make_hf_classifier(args.model)

    rows = []
    for comment in sample:
        result = classify(comment, list(args.labels))
        row = {
            "comment_sha": comment_sha(comment),
            "label": result["labels"][0],
            "score": float(result["scores"][0]),
        }
        rows.append(row)
        print(f"{row['comment_sha']} -> {row['label']} ({row['score']:.4f})")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
