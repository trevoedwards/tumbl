# Performance

Guidance for large Tumblr archives (roughly 5–10 GB on disk, 10k–20k posts).

## First launch

On first run, tumbl builds a JSON index of all posts. Expect:

| Archive size | Posts | Typical first index | Notes |
|--------------|-------|---------------------|-------|
| ~1 GB | ~2k | 20–30 seconds | Legacy HTML, 4 workers |
| ~5 GB | ~7k | 1–3 minutes | Depends on disk speed |
| ~10 GB | ~15k | 3–6 minutes | HTML sanitization adds overhead |

Progress is shown on the loading page via `/api/index-status`.

## Subsequent launches

The index is cached under `CACHE_DIR` (Docker default: `/app/cache`). Restarts usually load from cache in **under one second**.

The cache invalidates automatically when:

- Archive files change (fingerprint mismatch)
- Index schema version changes (see `CACHE_SCHEMA_VERSION` in `app/parser.py`)

To force a rebuild:

```bash
docker compose exec tumbl rm -f /app/cache/index-*.json /app/cache/index-*.meta.json
docker compose restart tumbl
```

## Memory and disk

| Resource | Rough estimate |
|----------|----------------|
| RAM at idle | 100–200 MB (Gunicorn worker + loaded index) |
| RAM during index build | 300–800 MB for multi-thousand post archives |
| Index cache | ~1–5 MB JSON per few thousand posts |
| Docker volume | Mount archive read-only; cache volume grows with index files |

## Lazy-loaded media

Post images include `loading="lazy"` and `decoding="async"` after sanitization, so the browser defers off-screen images on long feeds. Local media is still served from `/media/` on demand—nothing is copied into the container beyond the index cache.

## Tuning

| Variable | Default | Effect |
|----------|---------|--------|
| `INDEX_WORKERS` | `4` | Parallel parsers for legacy HTML / tumblr-utils |

Increasing workers helps CPU-bound index builds on multi-core hosts. Diminishing returns above ~8.

## Docker recommendations

- Mount the archive **read-only** (`:ro`) as in the default `docker-compose.yml`
- Use a named volume for `/app/cache` so rebuilds persist across container recreates
- Allow **60+ seconds** for the healthcheck `start_period` on first boot with large archives
