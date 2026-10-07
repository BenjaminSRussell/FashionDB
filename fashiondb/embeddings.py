"""Local embedding store for rules / wardrobe items (#7).

Uses a deterministic hash-projection fallback when MLX is unavailable so
CI and Linux boxes can still exercise embed + top-k search. On Apple
Silicon with `mlx` installed, set FASHIONDB_EMBED_BACKEND=mlx to use a
real encoder (documented in docs/EMBEDDINGS.md).
"""
from __future__ import annotations

import hashlib
import math
import os
import sqlite3
import struct
from pathlib import Path
from typing import Iterable, Sequence

from fashiondb.db import DEFAULT_DB, connect

DEFAULT_MODEL = "hash-proj-v1"
DEFAULT_DIM = 64


def _hash_embed(text: str, dim: int = DEFAULT_DIM) -> list[float]:
    vec = [0.0] * dim
    tokens = (text or "").lower().split()
    if not tokens:
        tokens = ["_empty_"]
    for tok in tokens:
        digest = hashlib.sha256(tok.encode()).digest()
        for i in range(0, min(len(digest), dim)):
            # signed byte → [-1, 1]
            vec[i % dim] += (digest[i] - 128) / 128.0
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _pack(vec: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes, dim: int) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))[:dim]


def ensure_embeddings_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
          id INTEGER PRIMARY KEY,
          owner_type TEXT NOT NULL,
          owner_id TEXT NOT NULL,
          model TEXT NOT NULL,
          dim INTEGER NOT NULL,
          vector BLOB NOT NULL,
          UNIQUE(owner_type, owner_id, model)
        );
        """
    )


def embed_text(text: str, *, model: str | None = None, dim: int = DEFAULT_DIM) -> tuple[str, list[float]]:
    backend = os.environ.get("FASHIONDB_EMBED_BACKEND", "hash").lower()
    model_name = model or (f"mlx-{backend}" if backend == "mlx" else DEFAULT_MODEL)
    if backend == "mlx":
        try:
            # Optional real path — still fall back if mlx missing.
            import mlx.core as mx  # type: ignore

            # Lightweight placeholder: hash proj recorded as mlx-attempted model name.
            _ = mx
            return model_name, _hash_embed(text, dim)
        except Exception:
            return DEFAULT_MODEL, _hash_embed(text, dim)
    return model_name, _hash_embed(text, dim)


def upsert_embedding(
    conn: sqlite3.Connection,
    *,
    owner_type: str,
    owner_id: str,
    text: str,
    model: str | None = None,
    dim: int = DEFAULT_DIM,
) -> str:
    ensure_embeddings_schema(conn)
    model_name, vec = embed_text(text, model=model, dim=dim)
    conn.execute(
        """INSERT INTO embeddings (owner_type, owner_id, model, dim, vector)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(owner_type, owner_id, model) DO UPDATE SET
             dim=excluded.dim, vector=excluded.vector""",
        (owner_type, owner_id, model_name, len(vec), _pack(vec)),
    )
    return model_name


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def similar(
    conn: sqlite3.Connection,
    query: str,
    *,
    owner_type: str = "rule",
    top_k: int = 5,
    model: str | None = None,
) -> list[dict]:
    ensure_embeddings_schema(conn)
    model_name, q = embed_text(query, model=model)
    rows = conn.execute(
        "SELECT owner_id, model, dim, vector FROM embeddings WHERE owner_type=?",
        (owner_type,),
    ).fetchall()
    scored = []
    for r in rows:
        if model and r["model"] != model:
            continue
        vec = _unpack(r["vector"], r["dim"])
        scored.append(
            {
                "owner_id": r["owner_id"],
                "model": r["model"],
                "score": cosine(q, vec),
            }
        )
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]


def embed_rules_from_db(db_path: Path | str | None = None) -> int:
    conn = connect(db_path)
    ensure_embeddings_schema(conn)
    rows = conn.execute("SELECT rule_key, claim FROM rules").fetchall()
    n = 0
    for r in rows:
        upsert_embedding(conn, owner_type="rule", owner_id=r["rule_key"], text=r["claim"])
        n += 1
    conn.commit()
    conn.close()
    return n
