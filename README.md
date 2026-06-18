# tumbl

Self-hosted viewer for Tumblr blog backup exports. 

Point it at an archive folder and browse your posts locally in a classic Tumblr-style theme. 

No account required, no data sent anywhere.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<p align="center">
  <img src="docs/demo.gif" alt="Browsing a Tumblr archive in tumbl" width="800">
</p>

## Features

- Paginated feed, full-text search, tag cloud, and date archive
- Post type filters (photo, audio, video, text) and photo lightbox
- Permalink pages, tag filtering, and classic Tumblr UI
- Legacy, modern, and tumblr-utils export formats
- Auto-extract `posts.zip`, background indexing with progress, persistent cache
- Docker-first, fully offline

## Supported export formats

| Format | Source | Layout signature | Status |
|--------|--------|------------------|--------|
| Legacy HTML backup | Tumblr (early export) | `posts/html/*.html` + `media/` | Supported |
| Official Tumblr ZIP | [Settings → Export](https://help.tumblr.com/export-your-blog/) | `posts/posts.xml` + `media/` | Supported |
| tumblr-utils | [bbolli/tumblr-utils](https://github.com/bbolli/tumblr-utils) | `index.html` + `posts/*.html` | Supported |
| Privacy data JSON | Account settings download | JSON account dump | Out of scope |

Directory layouts, extraction notes, and format-specific behavior are documented in **[Export formats](docs/export-formats.md)**.

## Quick start

**Prerequisites:** [Docker](https://www.docker.com/get-started/) and Docker Compose

1. **Export your blog** — Follow [Tumblr's export guide](https://help.tumblr.com/export-your-blog/), download the ZIP, and extract it (including `posts.zip` → `posts/` if present).
2. **Mount the archive** — Place the extracted folder at `.tumblrbackup/` in this repo, or update the volume path in `docker-compose.yml`.
3. **Run** — `docker compose up --build`
4. **Open** — [http://localhost:8862](http://localhost:8862)

First launch indexes posts in the background (often 20–30 seconds for a few thousand posts). Later starts load from cache in under a second.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ARCHIVE_PATH` | `/archive` | Path to the backup inside the container |
| `CACHE_DIR` | `/app/cache` | Writable directory for the JSON index cache |
| `BLOG_TITLE` | `MyBlog` | Default blog title (overridable in Settings) |
| `INDEX_WORKERS` | `4` | Parallel workers when building the index |

```yaml
services:
  tumbl:
    volumes:
      - /path/to/my/export:/archive:ro
    environment:
      - BLOG_TITLE=My Cool Blog
```

## How it works

```mermaid
flowchart TD
    Archive["Tumblr backup folder"] --> Detect["archive_detect.py"]
    Detect --> Legacy["legacy_html parser"]
    Detect --> Modern["modern_xml parser"]
    Detect --> Utils["tumblr_utils parser"]
    Legacy --> Index["PostMeta index"]
    Modern --> Index
    Utils --> Index
    Index --> Cache["JSON cache volume"]
    Index --> Flask["Flask + Gunicorn"]
    Flask --> Feed["Feed, search, tags, archive"]
    Flask --> Media["/media/ static files"]
```

On startup, tumbl detects the export format, builds a normalized post index (cached to disk), and serves paginated views plus local media from the archive.

## Development

**Local run (no Docker):**

```bash
pip install -r requirements.txt
set ARCHIVE_PATH=.tumblrbackup   # Windows
export ARCHIVE_PATH=.tumblrbackup  # macOS/Linux
python -m flask --app app.main run --debug
```

**Force index rebuild** — delete cache files and restart:

```bash
docker compose exec tumbl rm -f /app/cache/index-*.json /app/cache/index-*.meta.json
docker compose restart tumbl
```

Cache filenames are format-specific (`index-legacy_html.json`, `index-modern_xml.json`, etc.).

## Roadmap

- [ ] Messaging / conversations viewer (`messages.xml`)
- [ ] Open Graph images on permalink pages
- [ ] Random post (`/random`)
- [x] Full-text search, tag cloud, date archive
- [x] tumblr-utils support, auto-extract `posts.zip`, photo lightbox
- [x] Post type filters, async indexing, theme customization

## Contributing

Issues and pull requests are welcome. For larger changes, open an issue first to discuss approach.

## License

[MIT](LICENSE)

## Acknowledgements

Export format research informed by [TEV](https://github.com/tiyb/tev) and [tumblr-utils](https://github.com/bbolli/tumblr-utils). Not affiliated with Tumblr or Automattic.
