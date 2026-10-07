# FashionDB embeddings (#7)

Table: `embeddings(owner_type, owner_id, model, dim, vector BLOB)` inside `data/fashiondb.db`.

## Backends

| `FASHIONDB_EMBED_BACKEND` | Behavior |
|---------------------------|----------|
| `hash` (default) | Deterministic hash-projection vectors — works on Linux CI |
| `mlx` | Apple MLX path when installed; falls back to hash if import fails |

Model name is stored per row so you can mix versions safely.

## Demo

```bash
python -m fashiondb migrate-json tests/fixtures/rules_sample.json
python -m fashiondb embed-rules
python -m fashiondb similar "white socks with a suit" --top-k 3
```

Mac MLX setup: install `mlx` / `mlx-lm` via pip on Apple Silicon, then export `FASHIONDB_EMBED_BACKEND=mlx`.
