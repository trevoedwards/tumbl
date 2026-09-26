# Development

## Local run (no Docker)

Requires Python 3.12+.

```bash
pip install -r requirements.txt
pip install python-dotenv   # optional: load .env automatically
```

Point `ARCHIVE_PATH` at your extracted backup, either in `.env` (copy [`.env.example`](../.env.example)) or in your shell:

```bash
# Windows
set ARCHIVE_PATH=.tumblrbackup

# macOS / Linux
export ARCHIVE_PATH=.tumblrbackup
```

Then start the dev server:

```bash
python -m flask --app app.main run --debug
```

With the `.env.example` values (`FLASK_RUN_PORT=8862`), open [http://localhost:8862](http://localhost:8862). Without it, Flask uses port 5000.

## Docker for development

[`docker-compose.dev.yml.example`](../docker-compose.dev.yml.example) bind-mounts `./.cache` (so you can wipe the cache without pruning volumes) and enables all optional settings from `.env`:

```bash
cp docker-compose.dev.yml.example docker-compose.dev.yml
docker compose -f docker-compose.dev.yml up --build
```

`docker-compose.dev.yml` is gitignored, so edit it freely. Uncomment the `./app:/app/app` volume to live-edit app code without rebuilding.

## Demo archive

[`.demo/`](../.demo/README.md) contains a fake 35-post archive for trying tumbl without a real backup. Set `ARCHIVE_PATH=.demo/data` and start the app. See the [demo README](../.demo/README.md) for details and how to regenerate it.

## Force an index rebuild

The index cache invalidates automatically when archive files or the cache schema change. To force a rebuild, delete the cache files and restart:

```bash
docker compose exec tumbl rm -f /app/cache/index-*.json /app/cache/index-*.meta.json
docker compose restart tumbl
```

Cache filenames are format-specific (`index-legacy_html.json`, `index-modern_xml.json`, etc.). For a local run, delete `.cache/index-*.json` instead.

## Tests

```bash
docker compose exec tumbl python -m unittest discover -s tests -v
```

CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) builds the Docker image and runs the same suite on every push and pull request to `main`.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_demo_archive.py` | Regenerate the `.demo/` archive |
| `scripts/capture_demo_gif.py` | Record `docs/demo.gif` (Playwright + Pillow) |
| `scripts/export_wordpress_*_patch.py`, `scripts/apply_wordpress_*_patch.py` | Patch already-imported WordPress posts in place ([guide](wordpress-export.md#fix-orphan-media-posts-without-re-importing)) |
| `scripts/remap_wordpress_unsafe_ids.php` | Fix unsafe post IDs from older WXR exports ([guide](wordpress-export.md#remap-unsafe-post-ids-on-an-existing-site)) |

## Roadmap

- [ ] Messaging / conversations viewer (`messages.xml`)

## Contributing

Issues and pull requests are welcome. For larger changes, open an issue first to discuss approach.
