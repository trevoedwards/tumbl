# WordPress export

tumbl can optionally generate a [WordPress WXR](https://developer.wordpress.org/advanced-administration/wordpress/import/) (Extended RSS) import file from your Tumblr archive. This is useful if you exported your blog to a ZIP (or legacy HTML backup) and want to migrate to WordPress.com or self-hosted WordPress without a live Tumblr account.

The export feature is **disabled by default** so local-only users pay no overhead.

## Enable export

Set these environment variables (see [`.env.example`](../.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `WORDPRESS_EXPORT_ENABLED` | `false` | Set to `true` to enable `/export/wordpress.xml` and the Settings download link |
| `WORDPRESS_EXPORT_AUTHOR` | `admin` | WordPress author login assigned to imported posts |
| `WORDPRESS_EXPORT_SITE_URL` | `https://example.wordpress.com` | Target site URL used in post links and GUIDs |
| `WORDPRESS_EXPORT_MEDIA_BASE_URL` | _(empty)_ | Optional public base URL for archive media (see below) |

Example `.env` block:

```bash
WORDPRESS_EXPORT_ENABLED=true
WORDPRESS_EXPORT_AUTHOR=admin
WORDPRESS_EXPORT_SITE_URL=https://myblog.wordpress.com
# Optional — only if media is reachable at a public URL:
# WORDPRESS_EXPORT_MEDIA_BASE_URL=https://cdn.example.com/tumblr-media
```

Restart tumbl after changing env vars.

## Download the export

1. Open tumbl Settings (gear icon) or visit `/export/wordpress.xml` directly.
2. Save `tumblr-wordpress-export.xml`.

## Import into WordPress

1. In WordPress admin, go to **Tools → Import**.
2. Choose **WordPress** (install the importer plugin if prompted).
3. Upload the downloaded XML file.
4. Map authors when asked (create or assign to an existing user).
5. If you configured `WORDPRESS_EXPORT_MEDIA_BASE_URL`, check **Download and import file attachments**.

WordPress.com users: see [Import from Tumblr](https://wordpress.com/support/import/import-from-tumblr/) for the official live-account importer. The tumbl WXR export is an alternative when you only have an offline backup.

## What gets exported

Each Tumblr post becomes a WordPress `post` with:

- HTML body content (same sanitized HTML shown in tumbl)
- Tags as WordPress post tags
- Publish date from the archive timestamp
- Slug `tumblr-{postId}`
- Custom post meta: Tumblr source URL, reblog parent, post type, submission flag

## Media limitations

WXR does **not** embed media files. WordPress imports attachments by downloading each `wp:attachment_url` from a URL it can reach.

| Scenario | Result |
|----------|--------|
| No `WORDPRESS_EXPORT_MEDIA_BASE_URL` | Posts import; `/media/...` links in HTML stay relative and won't resolve on WordPress |
| Media hosted at a public HTTPS URL | Set `WORDPRESS_EXPORT_MEDIA_BASE_URL` to that base; tumbl rewrites `/media/file.jpg` to absolute URLs and emits attachment items |
| `localhost` or private LAN URLs | WordPress.com and most hosts **reject** fetching local/private URLs for security (SSRF protection) |

**Workarounds for local archives:**

- Upload your archive's `media/` folder to temporary public storage (S3, Cloudflare R2, a static file host, or a tunnel like ngrok) and set `WORDPRESS_EXPORT_MEDIA_BASE_URL` to that base URL during export.
- Import posts first without attachments, then upload media manually or fix links later.
- Leave existing Tumblr CDN URLs in post HTML when the export still references them.

## Supported archive formats

WXR export works from any format tumbl can index: legacy HTML, modern XML, and tumblr-utils backups.
