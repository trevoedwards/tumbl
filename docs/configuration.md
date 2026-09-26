# Configuration

tumbl is configured entirely through environment variables. Docker Compose reads a `.env` file in the repo root automatically for `${VAR}` substitution. Copy [`.env.example`](../.env.example) to `.env` to get started.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARCHIVE_PATH` | `/archive` | Path to the backup inside the container |
| `CACHE_DIR` | `/app/cache` | Writable directory for the JSON index cache |
| `BLOG_TITLE` | `MyBlog` | Default blog title (overridable in Settings) |
| `INDEX_WORKERS` | `4` | Parallel workers when building the index (capped at 4) |
| `BACKGROUND_IMAGE` | _(empty)_ | Optional default background: HTTPS URL or file path under the archive/app root |
| `TAG_EDITING_ENABLED` | `true` | Allow editing tags on permalink pages (saved to `CACHE_DIR`; the original backup is never changed) |

Restart tumbl after changing environment variables.

Defaults shown are for Docker. When running locally with `flask run`, `ARCHIVE_PATH` defaults to `.tumblrbackup` and `CACHE_DIR` to `.cache` in the repo root (see [Development](development.md)).

## Mounting your archive

The default [`docker-compose.yml`](../docker-compose.yml) mounts `./.tumblrbackup` read-only at `/archive`. To use a different folder, change the left side of the volume:

```yaml
volumes:
  - /path/to/your/export:/archive:ro
  - tumbl-cache:/app/cache
```

Keep the archive mount read-only (`:ro`). The index cache lives in the `tumbl-cache` named volume so it survives container recreates.

## WordPress export

Optional WordPress WXR export is **disabled by default** (`WORDPRESS_EXPORT_ENABLED=false`). Each Tumblr post imports as an individual WordPress Post (not one Page). The `WORDPRESS_EXPORT_*` variables are documented in the [WordPress export guide](wordpress-export.md#full-environment-reference), and a commented example lives in [`docker-compose.yml`](../docker-compose.yml).

## See also

- [Performance](performance.md) — tuning `INDEX_WORKERS` and cache behavior for large archives
- [Security](security.md) — how `BACKGROUND_IMAGE` paths and URLs are validated
