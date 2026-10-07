"""BERTopic pass + optional spell-map / changes CSVs for fashion Reddit text.

Flags that used to no-op (`--map-csv`, `--changes-csv`, `--out`, thresholds)
now write real artifacts. Topic fitting is injectable for offline tests.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\\-]{1,}")


def load_docs(data: dict[str, Any]) -> list[str]:
    docs: list[str] = []
    for _cat, posts in data.items():
        if not isinstance(posts, list):
            continue
        for p in posts:
            if p.get("title"):
                docs.append(str(p["title"]))
            for c in p.get("comments", []) or []:
                if c.get("body"):
                    docs.append(str(c["body"]))
    return docs


def tokenize(docs: list[str]) -> list[str]:
    words: list[str] = []
    for doc in docs:
        words.extend(WORD_RE.findall(doc))
    return words


def build_spell_map(
    words: list[str],
    *,
    top_k: int = 200,
    min_misspell: int = 15,
    min_ratio: int = 8,
    min_sim: float = 0.85,
) -> tuple[list[tuple[str, str, float, int, int]], list[tuple[str, str, float]]]:
    """Return (map_rows, change_rows).

    map_rows: misspelling, correction, similarity, misspell_count, correct_count
    change_rows: original, replacement, similarity (one per applied substitution)
    """
    counts = Counter(w.lower() for w in words)
    # Prefer title-case / original casing by picking most common surface form
    surface: dict[str, str] = {}
    surface_counts: Counter[str] = Counter()
    for w in words:
        key = w.lower()
        surface_counts[w] += 1
        if key not in surface or surface_counts[w] > surface_counts.get(surface[key], 0):
            surface[key] = w

    vocab = [w for w, c in counts.most_common(max(top_k * 5, 500))]
    # Candidates for "correct" forms: frequent enough words
    correct_pool = [w for w in vocab if counts[w] >= min_ratio]
    map_rows: list[tuple[str, str, float, int, int]] = []
    seen_miss: set[str] = set()

    for miss, miss_n in counts.most_common(top_k * 2):
        if miss_n < min_misspell:
            continue
        if miss in seen_miss:
            continue
        best = None
        best_sim = 0.0
        for cand in correct_pool:
            if cand == miss:
                continue
            if counts[cand] < miss_n * (min_ratio / max(min_misspell, 1)):
                # correction should be clearly more common when possible
                if counts[cand] < counts[miss]:
                    continue
            sim = SequenceMatcher(None, miss, cand).ratio()
            if sim >= min_sim and sim > best_sim and abs(len(miss) - len(cand)) <= 3:
                best, best_sim = cand, sim
        if best is None:
            continue
        seen_miss.add(miss)
        map_rows.append((miss, best, round(best_sim, 4), miss_n, counts[best]))
        if len(map_rows) >= top_k:
            break

    changes: list[tuple[str, str, float]] = []
    for miss, corr, sim, _mn, _cn in map_rows:
        changes.append((surface.get(miss, miss), surface.get(corr, corr), sim))
    return map_rows, changes


def write_map_csv(path: str | Path, rows: list[tuple[str, str, float, int, int]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["misspelling", "correction", "similarity", "misspell_count", "correct_count"])
        w.writerows(rows)


def write_changes_csv(path: str | Path, rows: list[tuple[str, str, float]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["original", "replacement", "similarity"])
        w.writerows(rows)


def write_topics_out(path: str | Path, topic_info, topic0) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # topic_info may be a DataFrame or list of dicts
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["topic_id", "count", "top_terms"])
        if hasattr(topic_info, "iterrows"):
            for _, row in topic_info.iterrows():
                tid = row.get("Topic", row.get("topic_id", ""))
                cnt = row.get("Count", row.get("count", ""))
                name = row.get("Name", row.get("top_terms", ""))
                w.writerow([tid, cnt, name])
        else:
            for row in topic_info:
                w.writerow([row.get("topic_id"), row.get("count"), row.get("top_terms")])
        if topic0 is not None:
            f.write(f"# topic_0_terms\t{topic0}\n")


def default_fit_transform(docs: list[str], *, min_topic_size: int = 150):
    from bertopic import BERTopic

    model = BERTopic(
        n_gram_range=(1, 2),
        min_topic_size=min_topic_size,
        calculate_probabilities=False,
        verbose=True,
        seed_topic_list=None,
    )
    topics, _ = model.fit_transform(docs)
    return model, topics


def run(
    *,
    input_path: str,
    out: str | None = None,
    map_csv: str | None = None,
    changes_csv: str | None = None,
    top_k: int = 200,
    min_misspell: int = 15,
    min_ratio: int = 8,
    min_sim: float = 0.85,
    min_topic_size: int = 150,
    fit_transform: Callable | None = None,
) -> dict[str, Any]:
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    docs = load_docs(data)
    words = tokenize(docs)

    map_rows, change_rows = build_spell_map(
        words,
        top_k=top_k,
        min_misspell=min_misspell,
        min_ratio=min_ratio,
        min_sim=min_sim,
    )
    if map_csv:
        write_map_csv(map_csv, map_rows)
    if changes_csv:
        write_changes_csv(changes_csv, change_rows)

    fitter = fit_transform or (lambda d: default_fit_transform(d, min_topic_size=min_topic_size))
    model, _topics = fitter(docs)
    info = model.get_topic_info()
    topic0 = model.get_topic(0)
    if out:
        write_topics_out(out, info, topic0)
    else:
        # keep previous stdout behaviour when --out omitted
        head = info.head(15) if hasattr(info, "head") else info[:15]
        print(head)
        print(topic0)

    return {
        "docs": len(docs),
        "map_rows": len(map_rows),
        "change_rows": len(change_rows),
        "out": out,
        "map_csv": map_csv,
        "changes_csv": changes_csv,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="BERTopic on fashion JSON plus optional spell-map CSVs."
    )
    parser.add_argument("--input", type=str, required=True, help="Input JSON file path")
    parser.add_argument("--out", type=str, help="Write topic id/count/terms CSV here")
    parser.add_argument("--map-csv", type=str, help="Path to spellmap CSV")
    parser.add_argument("--changes-csv", type=str, help="Path to spell changes CSV")
    parser.add_argument("--top-k", type=int, default=200, help="Max spell-map rows")
    parser.add_argument("--min-misspell", type=int, default=15, help="Min count for misspelling")
    parser.add_argument("--min-ratio", type=int, default=8, help="Min count for correction")
    parser.add_argument("--min-sim", type=float, default=0.85, help="Min similarity")
    parser.add_argument(
        "--min-topic-size",
        type=int,
        default=150,
        help="BERTopic min_topic_size (lower for small fixtures)",
    )
    args = parser.parse_args(argv)
    run(
        input_path=args.input,
        out=args.out,
        map_csv=args.map_csv,
        changes_csv=args.changes_csv,
        top_k=args.top_k,
        min_misspell=args.min_misspell,
        min_ratio=args.min_ratio,
        min_sim=args.min_sim,
        min_topic_size=args.min_topic_size,
    )


if __name__ == "__main__":
    main()
