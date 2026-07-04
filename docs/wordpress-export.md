# WordPress export guide

tumbl can generate a [WordPress WXR](https://developer.wordpress.org/advanced-administration/wordpress/import/) (Extended RSS) import file from your Tumblr archive. Use this when you have an offline backup and want to migrate posts into an **existing** WordPress site — self-hosted or WordPress.com — without a live Tumblr account.

The export feature is **disabled by default** so local-only users pay no overhead.

---

## Quick start checklist

1. [Enable export](#1-enable-export) in your tumbl environment
2. [Configure your existing WordPress site URL](#2-configure-your-existing-wordpress-site)
3. [Download the export](#3-download-the-export) from Settings or `/export/wordpress.xml`
4. [Import into WordPress](#4-import-into-wordpress)
5. (Optional) [Apply theme matching CSS](#5-optional-match-colors-and-fonts)
6. (Optional) [Troubleshoot media](#media-limitations) if images are missing after import

---

## 1. Enable export

Set these environment variables (see [`.env.example`](../.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `WORDPRESS_EXPORT_ENABLED` | `false` | Set to `true` to enable export routes and the Settings download panel |
| `WORDPRESS_EXPORT_AUTHOR` | `admin` | WordPress author login assigned to imported posts |
| `WORDPRESS_EXPORT_SITE_URL` | `https://example.com` | Root URL of your **existing** WordPress site |

Restart tumbl after changing environment variables.

Example `.env` block:

```bash
WORDPRESS_EXPORT_ENABLED=true
WORDPRESS_EXPORT_AUTHOR=admin
WORDPRESS_EXPORT_SITE_URL=https://usersite.com
```

---

## 2. Configure your existing WordPress site

### Site URL

`WORDPRESS_EXPORT_SITE_URL` should be the root of your live WordPress site (no path), for example:

- `https://myblog.wordpress.com`
- `https://usersite.com`

tumbl uses this URL for channel metadata, theme color/font fetching, and as the `{site_url}` placeholder in post links.

### Post URL template

By default, each exported post is assigned a link that matches a paginated blog feed:

```
{site_url}/blog/?page={page}#post-{id}
```

For `WORDPRESS_EXPORT_SITE_URL=https://usersite.com`, the newest post might get:

```
https://usersite.com/blog/?page=1#post-12345
```

The 21st newest post (with 20 posts per page) gets `?page=2`, and so on.

#### Placeholders

| Placeholder | Meaning |
|-------------|---------|
| `{site_url}` | Value of `WORDPRESS_EXPORT_SITE_URL` |
| `{page}` | 1-based feed page number (newest posts = page 1) |
| `{id}` | Tumblr post ID from the archive |
| `{slug}` | WordPress slug (`tumblr-{id}` or `post-{id}` in minimal mode) |
| `{index}` | 0-based position in the export (0 = newest) |

#### Customize the template

If your blog lives at a different path, set `WORDPRESS_EXPORT_URL_TEMPLATE`:

```bash
# Journal instead of /blog/
WORDPRESS_EXPORT_URL_TEMPLATE={site_url}/journal/?page={page}#post-{id}

# Pretty permalinks (individual post URLs)
WORDPRESS_EXPORT_URL_TEMPLATE={site_url}/{slug}/
```

You can also change the template per download from **Settings → WordPress export** without restarting tumbl.

#### Posts per page

`WORDPRESS_EXPORT_POSTS_PER_PAGE` controls how `{page}` is calculated. Default is `20` (same as tumbl's feed). Set this to match your WordPress blog's posts-per-page if you use paginated feed URLs.

```bash
WORDPRESS_EXPORT_POSTS_PER_PAGE=10
```

### Post anchors

Exported post HTML is wrapped in `<div id="post-{id}" class="tumblr-archive-post">` so `#post-{id}` anchors in the URL template resolve to the correct post content after import.

---

## 3. Download the export

### From Settings

1. Open tumbl **Settings** (gear icon).
2. Scroll to **WordPress export**.
3. Adjust options if needed:
   - **Post URL template** — customize link format
   - **Posts per page** — for `{page}` calculation
   - **Match target site colors and fonts** — fetch theme styles; enables a companion `.css` download
   - **Minimal export** — strip Tumblr/tumbl branding from metadata
4. Click **Download WordPress export (.xml)**.
5. If theme matching is enabled, also download **theme stylesheet (.css)**.

### Direct URL

| URL | Description |
|-----|-------------|
| `/export/wordpress.xml` | WXR import file |
| `/export/wordpress-theme.css` | Companion stylesheet (only when `match_theme=1`) |

Query parameters override env defaults for a single download:

```
/export/wordpress.xml?minimal=1&match_theme=1&posts_per_page=10&url_template=...
```

| Query param | Effect |
|-------------|--------|
| `minimal=1` | Strip branding (neutral slugs, no Tumblr meta, no generator) |
| `match_theme=1` | Fetch target site colors/fonts; wrap posts with theme fallback |
| `posts_per_page=N` | Override pagination size for `{page}` |
| `url_template=...` | URL-encoded template override |

---

## 4. Import into WordPress

### Before you import

- **Back up your existing WordPress site** (database + uploads) before importing.
- Confirm `WORDPRESS_EXPORT_AUTHOR` matches an existing user, or plan to create/assign one during import.
- If you need images in WordPress, set up [media hosting](#media-limitations) first.

### Import steps

1. Log in to your WordPress admin dashboard.
2. Go to **Tools → Import**.
3. Choose **WordPress** (install the official importer plugin if prompted).
4. Click **Choose File** and upload the downloaded `.xml` file.
5. Click **Upload file and import**.
6. On the author mapping screen:
   - **Import author** — create the author from the export, or
   - **Assign posts to an existing user** — recommended for existing sites
7. Check **Download and import file attachments** only if you configured `WORDPRESS_EXPORT_MEDIA_BASE_URL` and media is publicly reachable (see [Media](#media-limitations)).
8. Click **Submit** and wait for the import to finish.

### After import

- Browse your site and confirm posts appear with correct dates, tags, and content.
- WordPress may assign its own permalinks based on your site's permalink settings; the URLs in the WXR file are used for GUIDs and reference during import.
- If you enabled **minimal export**, imported posts will not include `_tumblr_*` custom fields or tumbl generator metadata.

### WordPress.com

WordPress.com users can use **Tools → Import → WordPress** on eligible plans. The tumbl WXR export is an alternative to the [official Tumblr importer](https://wordpress.com/support/import/import-from-tumblr/) when you only have an offline backup.

---

## 5. (Optional) Match colors and fonts

When **Match target site colors and fonts** is enabled, tumbl fetches your WordPress site's homepage and extracts typography and color tokens (from block-theme global styles or classic theme CSS).

### What you get

1. **WXR file** — each post is wrapped in `<div class="tumblr-archive-post">` with inline `font-family` and `color` as a fallback.
2. **Companion CSS file** (`wordpress-export-theme.css`) — scoped styles for links, blockquotes, captions, and media.

### Apply the stylesheet

1. Download both the `.xml` and `.css` files.
2. Import the XML as described above.
3. In WordPress admin, go to **Appearance → Customize → Additional CSS**.
4. Paste the contents of `wordpress-export-theme.css`.
5. Click **Publish**.

Post HTML structure is unchanged — only colors and fonts are adjusted to better match your existing theme.

If theme fetch fails (site unreachable, blocked, etc.), tumbl exports without theme styles and logs a warning.

---

## 6. Minimal export

Enable **Minimal export** (or `WORDPRESS_EXPORT_MINIMAL=true` / `?minimal=1`) for a neutral import without Tumblr/tumbl branding:

| Field | Standard export | Minimal export |
|-------|-----------------|----------------|
| Post slug | `tumblr-{id}` | `post-{id}` |
| Fallback title | `Tumblr post {id}` | `Post {id}` |
| Channel description | `Tumblr archive export for {title}` | `{blog_title}` only |
| Generator | tumbl GitHub URL | omitted |
| `_tumblr_*` post meta | included | omitted |
| Download filename | `tumblr-wordpress-export.xml` | `wordpress-export.xml` |

Post HTML content is identical in both modes.

---

## What gets exported

Each Tumblr post becomes a WordPress `post` with:

- HTML body content (same sanitized HTML shown in tumbl, wrapped with `id="post-{id}"`)
- Tags as WordPress post tags
- Publish date from the archive timestamp
- Unique WordPress slug (`wp:post_name`)
- Link and GUID from your URL template
- Custom Tumblr meta (unless minimal mode): source URL, reblog parent, post type, submission flag

---

## Media limitations

WXR does **not** embed media files. WordPress imports attachments by downloading each `wp:attachment_url` from a URL it can reach.

| Variable | Description |
|----------|-------------|
| `WORDPRESS_EXPORT_MEDIA_BASE_URL` | Public HTTPS base URL for your archive's `media/` folder |

| Scenario | Result |
|----------|--------|
| No `WORDPRESS_EXPORT_MEDIA_BASE_URL` | Posts import; `/media/...` links in HTML stay relative and won't resolve on WordPress |
| Media hosted at a public HTTPS URL | Set `WORDPRESS_EXPORT_MEDIA_BASE_URL`; tumbl rewrites `/media/file.jpg` to absolute URLs and emits attachment items |
| `localhost` or private LAN URLs | WordPress.com and most hosts **reject** fetching local/private URLs (SSRF protection) |

Example:

```bash
WORDPRESS_EXPORT_MEDIA_BASE_URL=https://cdn.example.com/tumblr-media
```

### Workarounds for local archives

1. Upload your archive's `media/` folder to temporary public storage (S3, Cloudflare R2, a static file host, or a tunnel like ngrok).
2. Set `WORDPRESS_EXPORT_MEDIA_BASE_URL` to that base URL during export.
3. Import with **Download and import file attachments** checked.
4. Remove or rotate the public media hosting after import if desired.

Alternative: import posts first without attachments, then upload media manually or fix links later. Posts that still reference Tumblr CDN URLs in the HTML may keep working if those URLs are live.

---

## Full environment reference

| Variable | Default | Description |
|----------|---------|-------------|
| `WORDPRESS_EXPORT_ENABLED` | `false` | Enable export routes |
| `WORDPRESS_EXPORT_AUTHOR` | `admin` | Author login for imported posts |
| `WORDPRESS_EXPORT_SITE_URL` | `https://example.com` | Existing site root URL |
| `WORDPRESS_EXPORT_URL_TEMPLATE` | `{site_url}/blog/?page={page}#post-{id}` | Post link/GUID template |
| `WORDPRESS_EXPORT_POSTS_PER_PAGE` | `20` | Posts per feed page for `{page}` |
| `WORDPRESS_EXPORT_MEDIA_BASE_URL` | _(empty)_ | Public base URL for archive media |
| `WORDPRESS_EXPORT_MATCH_THEME` | `false` | Fetch target site colors/fonts by default |
| `WORDPRESS_EXPORT_MINIMAL` | `false` | Strip branding by default |

---

## Supported archive formats

WXR export works from any format tumbl can index:

- Legacy HTML backup (`posts/html/*.html` + `media/`)
- Official Tumblr ZIP export (`posts/posts.xml` + `media/`)
- tumblr-utils backup (`index.html` + `posts/*.html`)

---

## Troubleshooting

| Problem | Things to try |
|---------|---------------|
| Export link missing | Set `WORDPRESS_EXPORT_ENABLED=true` and restart tumbl |
| Wrong post URLs after import | WordPress generates permalinks from site settings; URL template affects WXR metadata, not necessarily final permalinks |
| Theme CSS download 404 | Enable **Match target site colors and fonts** or add `?match_theme=1`; site must be reachable from tumbl |
| Images broken after import | Set `WORDPRESS_EXPORT_MEDIA_BASE_URL` to a public URL; re-export and re-import attachments, or fix links manually |
| Import times out | Large archives may need increased PHP `max_execution_time` on self-hosted WordPress |
| Duplicate posts on re-import | WordPress importer may create duplicates; use a fresh site or delete previously imported posts first |

---

## See also

- [Export formats](export-formats.md) — Tumblr backup layouts tumbl accepts
- [README](../README.md) — Environment variable summary
