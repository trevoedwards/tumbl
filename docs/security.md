# Security

tumbl is designed for **local, private use**. Treat it like any self-hosted service: bind to localhost or place it behind a reverse proxy if you expose it beyond your machine.

## Protections

| Area | Measure |
|------|---------|
| Post HTML | Bleach allowlist sanitization on index build and cache load (`app/html_sanitize.py`) |
| Zip extraction | Path traversal checks; limits of **100k files** / **10 GB** uncompressed (`app/archive_prepare.py`) |
| XML parsing | `posts.xml` size cap (512 MB) before parse |
| Media files | Filename sanitization + resolved path must stay under `media/` |
| Background image | File paths restricted to archive or app root; URLs must be `http`/`https` |
| HTTP responses | CSP (`script-src 'self'`), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` |
| Errors | Public API/UI messages are generic; details logged server-side only |
| Client settings | Background image URLs validated in browser before applying to CSS |

Post HTML is still rendered with Jinja's `| safe` filter, but content is sanitized first. Unusual markup (inline styles, uncommon tags) may be stripped.

All page JavaScript lives in `app/static/` (`early-init.js`, `tumbl.js`) so CSP can keep `script-src 'self'` without `'unsafe-inline'`.

## Residual risk

- **No authentication** — anyone who can reach the port can browse the mounted archive.
- **CSP allows remote media/embeds** — required for Tumblr CDN images and YouTube iframes in posts.
- **Archive trust** — you are viewing your own export; a malicious zip could still waste CPU/disk during extraction before limits trigger.

## Running tests

```bash
docker compose exec tumbl python -m unittest discover -s tests -v
```

Security-focused tests: `tests/test_html_sanitize.py`, `tests/test_security.py`, `tests/test_archive_prepare.py`.
