# WordPress export guide

tumbl can generate a [WordPress WXR](https://developer.wordpress.org/advanced-administration/wordpress/import/) (Extended RSS) import file from your Tumblr archive. Use this when you have an offline backup and want to migrate posts into an **existing** WordPress site — self-hosted or WordPress.com — without a live Tumblr account.

The export feature is **disabled by default** so local-only users pay no overhead.

In a hurry? See the [quick start](wordpress-export-quickstart.md) for a condensed step-by-step version of this guide.

---

## What you get in WordPress (structure)

**Each Tumblr post becomes its own WordPress Post — not one Page.**

Import does **not** dump the archive into a single WordPress Page. WordPress creates many separate blog posts, the same way a normal WordPress blog stores entries under **Posts → All Posts**.

| Tumblr / export | After WordPress import | Where to look in WP admin |
|-----------------|------------------------|---------------------------|
| One Tumblr post | One **Post** (`post_type=post`, published) | **Posts → All Posts** |
| Post HTML body | That post’s content | Open the post in the editor or on the front end |
| Tags | WordPress **post tags** | Post editor → Tags, or **Posts → Tags** |
| Archive timestamp | Post date (and usually the post title) | Posts list / post editor |
| Slug `tumblr-{id}` (or `post-{id}` in minimal mode) | Post slug (`wp:post_name`) | Often part of the permalink |
| Media file (when media base URL is set) | **Attachment** in the Media Library, parented to that post | **Media → Library** |
| Whole archive | Many posts (+ optional attachments) | Not a single Page |

**Not created:** WordPress Pages, menus, categories (tags only), comments, drafts, or a single “archive dump” page.

### Hierarchy at a glance

```text
Tumblr archive
├── Post A  ──►  WordPress Post A  (+ optional Media attachments)
├── Post B  ──►  WordPress Post B  (+ optional Media attachments)
└── Post C  ──►  WordPress Post C  (+ optional Media attachments)
```

After import you should see roughly one new row in **Posts → All Posts** per Tumblr post in the archive (plus attachment rows in **Media → Library** if you imported file attachments).

### Titles and content

- **Title** is usually the archive timestamp string when present; otherwise `Tumblr post {id}` / `Post {id}` (minimal mode).
- **Content** is the same sanitized HTML tumbl shows in the archive viewer, wrapped in `<div id="post-{id}" class="tumblr-archive-post">`.
- **Comments** are closed on imported posts.

### URL template vs real permalinks

The export’s **Post URL template** only fills link/GUID fields inside the WXR file. It does **not** mean WordPress puts every Tumblr post on one paginated page.

The default template looks like a feed with anchors:

```text
{site_url}/blog/?page={page}#post-{id}
```

That can be misleading. WordPress still creates **individual Posts**. After import, front-end URLs almost always follow your site’s **Settings → Permalinks** (for example `/tumblr-12345/` or `/2020/01/05/tumblr-12345/`), not necessarily the template string.

Use a pretty-permalink style template if you want WXR metadata to resemble per-post URLs:

```bash
WORDPRESS_EXPORT_URL_TEMPLATE={site_url}/{slug}/
```

See [Post URL template](#post-url-template) for placeholders and options.

---

## Quick start checklist

1. [Enable export](#1-enable-export) in your tumbl environment
2. [Configure your existing WordPress site URL](#2-configure-your-existing-wordpress-site)
3. (Recommended) [Stage media](#3-stage-media-on-public-https) on public HTTPS (often your WordPress host’s storage)
4. [Download the export](#4-download-the-export) from Settings or `/export/wordpress.xml`
5. [Import into WordPress](#5-import-into-wordpress) (end-to-end)
6. (Optional) [Apply theme matching CSS](#6-optional-match-colors-and-fonts)
7. (Optional) [Troubleshoot](#troubleshooting) if images or URLs look wrong

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

By default, each exported post is assigned a **metadata** link that looks like a paginated blog feed:

```
{site_url}/blog/?page={page}#post-{id}
```

For `WORDPRESS_EXPORT_SITE_URL=https://usersite.com`, the newest post’s WXR link might be:

```
https://usersite.com/blog/?page=1#post-12345
```

Remember: this does **not** merge posts onto one WordPress Page. Each Tumblr post is still a separate WordPress Post after import. See [URL template vs real permalinks](#url-template-vs-real-permalinks).

#### Placeholders

| Placeholder | Meaning |
|-------------|---------|
| `{site_url}` | Value of `WORDPRESS_EXPORT_SITE_URL` |
| `{page}` | 1-based feed page number (newest posts = page 1) |
| `{id}` | Tumblr post ID from the archive |
| `{slug}` | WordPress slug (`tumblr-{id}` or `post-{id}` in minimal mode) |
| `{index}` | 0-based position in the export (0 = newest) |

#### Customize the template

```bash
# Journal instead of /blog/ — quote values that contain # (dotenv comment rules)
WORDPRESS_EXPORT_URL_TEMPLATE="{site_url}/journal/?page={page}#post-{id}"

# Pretty permalinks (individual post URLs in WXR metadata)
WORDPRESS_EXPORT_URL_TEMPLATE={site_url}/{slug}/
```

You can also change the template per download from **Settings → WordPress export** without restarting tumbl.

#### Posts per page

`WORDPRESS_EXPORT_POSTS_PER_PAGE` controls how `{page}` is calculated when your template uses `{page}`. Default is `20` (same as tumbl's feed).

```bash
WORDPRESS_EXPORT_POSTS_PER_PAGE=10
```

### Post anchors

Exported post HTML is wrapped in `<div id="post-{id}" class="tumblr-archive-post">` so a `#post-{id}` fragment in a URL template can target that post’s own HTML. That wrapper lives **inside each individual post’s content**; it is not evidence that all posts share one Page.

---

## 3. Stage media on public HTTPS

Tumblr archives are media-heavy. WXR does **not** embed image/video/audio files. WordPress imports attachments by downloading each `wp:attachment_url` from a URL it can reach.

### Recommended: use your WordPress host’s storage

If your WordPress plan already includes substantial disk space (for example Hostinger or similar shared hosting), upload the archive `media/` folder to a publicly reachable location on that same host, then point tumbl at it:

```bash
# Example: media staged under your site
WORDPRESS_EXPORT_MEDIA_BASE_URL=https://usersite.com/tumblr-media
```

A multi‑GB archive is often fine relative to plans that offer tens or hundreds of GB. After import, WordPress will have copied attachments into its Media Library; you can delete the temporary staging folder if you no longer need it.

### Other staging options

- Object storage / CDN (S3, Cloudflare R2, etc.)
- Any static HTTPS file host
- A temporary tunnel (for example ngrok) only while importing — localhost/LAN URLs are usually **rejected** by WordPress SSRF protections

### Without a media base URL

Posts still import, but `/media/...` links in HTML stay relative and will not resolve on WordPress. Stage media before export if you want images and video to survive migration.

Full matrix and edge cases: [Media details](#media-details).

---

## 4. Download the export

### From Settings

1. Open tumbl **Settings** (gear icon).
2. Scroll to **WordPress export**.
3. Adjust options if needed:
   - **Post URL template** — WXR link/GUID metadata only (see [URL template vs real permalinks](#url-template-vs-real-permalinks))
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

## 5. Import into WordPress

This is the full process from a staged archive to verified posts.

### Before you import

1. **Back up** your existing WordPress site (database + `wp-content/uploads`).
2. Confirm `WORDPRESS_EXPORT_AUTHOR` matches a user you will map to, or plan to create/assign one during import.
3. If you need images/video: finish [staging media](#3-stage-media-on-public-https) and set `WORDPRESS_EXPORT_MEDIA_BASE_URL`, then re-download the WXR so attachment URLs are included.
4. Optionally review **Settings → Permalinks** on WordPress so you know how new posts will be addressed on the front end.

### Import steps

1. Log in to your WordPress admin dashboard.
2. Go to **Tools → Import**.
3. Choose **WordPress** (install the official importer plugin if prompted).
4. Click **Choose File** and upload the downloaded `.xml` file.
5. Click **Upload file and import**.
6. On the author mapping screen:
   - **Import author** — create the author from the export, or
   - **Assign posts to an existing user** — recommended for existing sites
7. Check **Download and import file attachments** only if you configured `WORDPRESS_EXPORT_MEDIA_BASE_URL` and that URL is publicly reachable from WordPress.
8. Click **Submit** and wait for the import to finish. Large archives may need a higher PHP `max_execution_time` on self-hosted WordPress.

### After import — verify structure

1. Open **Posts → All Posts**. You should see **one new post per Tumblr post**, not a single Page holding everything.
2. Open several posts and confirm dates, tags, and HTML content look right.
3. If you imported attachments: open **Media → Library** and confirm files arrived; open a photo/video post on the front end and confirm media loads.
4. Spot-check front-end permalinks — they follow WordPress permalink settings, not necessarily the export URL template.
5. If you used theme matching, paste the companion CSS (next section).
6. Optionally remove the temporary public `media/` staging folder once attachments live in the Media Library.

### WordPress.com

WordPress.com users can use **Tools → Import → WordPress** on eligible plans. The tumbl WXR export is an alternative to the [official Tumblr importer](https://wordpress.com/support/import/import-from-tumblr/) when you only have an offline backup.

---

## 6. (Optional) Match colors and fonts

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

## 7. Minimal export

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

Each Tumblr post becomes a WordPress **Post** with:

- HTML body content (same sanitized HTML shown in tumbl, wrapped with `id="post-{id}"`)
- Tags as WordPress post tags
- Publish date from the archive timestamp
- Unique WordPress slug (`wp:post_name`) — `tumblr-{tumblrId}` or `post-{tumblrId}` in minimal mode
- Safe sequential WordPress post ID (`wp:post_id` = 1, 2, 3, …) so Gutenberg can edit posts; original Tumblr ID stored in `_tumblr_post_id` meta
- Link and GUID from your URL template (metadata only; see [permalinks](#url-template-vs-real-permalinks))
- Custom Tumblr meta (unless minimal mode): source URL, reblog parent, post type, submission flag

When `WORDPRESS_EXPORT_MEDIA_BASE_URL` is set, referenced `/media/` files also become WXR **attachment** items so WordPress can download them into the Media Library.

---

## Media details

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
WORDPRESS_EXPORT_MEDIA_BASE_URL=https://usersite.com/tumblr-media
```

### Typical workflow on WordPress hosting

1. Upload your archive's `media/` folder to a public path on your WordPress host (or CDN).
2. Set `WORDPRESS_EXPORT_MEDIA_BASE_URL` to that base URL and restart tumbl if needed.
3. Re-download the WXR so attachment URLs are present.
4. Import with **Download and import file attachments** checked.
5. Remove or keep the staging copy after import as you prefer.

Alternative: import posts first without attachments, then upload media manually or fix links later. Posts that still reference Tumblr CDN URLs in the HTML may keep working if those URLs are live.

---

## Full environment reference

| Variable | Default | Description |
|----------|---------|-------------|
| `WORDPRESS_EXPORT_ENABLED` | `false` | Enable export routes |
| `WORDPRESS_EXPORT_AUTHOR` | `admin` | Author login for imported posts |
| `WORDPRESS_EXPORT_SITE_URL` | `https://example.com` | Existing site root URL |
| `WORDPRESS_EXPORT_URL_TEMPLATE` | `{site_url}/blog/?page={page}#post-{id}` | Post link/GUID template (not final WP structure) |
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
| Expected one Page, got many Posts | That is correct — see [What you get in WordPress](#what-you-get-in-wordpress-structure) |
| Wrong post URLs after import | WordPress generates permalinks from **Settings → Permalinks**; the URL template only affects WXR metadata |
| Theme CSS download 404 | Enable **Match target site colors and fonts** or add `?match_theme=1`; site must be reachable from tumbl |
| Import says missing/invalid WXR version | Re-download after updating tumbl — older exports could emit duplicate `xmlns:*` attributes (invalid XML). Also raise PHP `upload_max_filesize` / `post_max_size` above the `.xml` size (Hostinger is often 8–16M; media-heavy exports can be larger) |
| Images broken after import | Set `WORDPRESS_EXPORT_MEDIA_BASE_URL` to a public URL; re-export and re-import attachments, or fix links manually |
| Import times out | Large archives may need increased PHP `max_execution_time` on self-hosted WordPress |
| Duplicate posts on re-import | WordPress importer may create duplicates; use a fresh site or delete previously imported posts first |
| Need to fix media-only posts after a tumbl upgrade | Do **not** re-import the full WXR. Use the [content patch](#fix-orphan-media-posts-without-re-importing) scripts below |
| "You attempted to edit an item that doesn't exist" in Gutenberg | Older tumbl exports used Tumblr snowflake IDs as `wp:post_id`, which exceed JavaScript's safe integer limit. See [Remap unsafe post IDs](#remap-unsafe-post-ids-on-an-existing-site) |
| Cannot create new posts after import | `wp_posts` AUTO_INCREMENT may be stuck at a huge Tumblr ID; run the remapper below |

---

## Remap unsafe post IDs on an existing site

**Symptom:** Some imported posts open on the front end but fail in the block editor with *"You attempted to edit an item that doesn't exist."* This affects posts whose WordPress `ID` is a 16-digit Tumblr snowflake (above `9007199254740991`). Older posts with shorter IDs are unaffected.

**Cause:** Early tumbl WXR exports wrote the Tumblr ID into `wp:post_id`. Gutenberg rounds those IDs in JavaScript and the REST API returns 404.

**Fix:** Remap unsafe IDs to safe sequential values. Slugs (`tumblr-{id}`) and front-end URLs stay the same.

1. **Back up** your WordPress database.
2. Copy [`scripts/remap_wordpress_unsafe_ids.php`](../scripts/remap_wordpress_unsafe_ids.php) to your server.
3. Dry-run, then apply:

```bash
# WP-CLI (from WordPress root):
wp eval-file /path/to/remap_wordpress_unsafe_ids.php -- --dry-run
wp eval-file /path/to/remap_wordpress_unsafe_ids.php -- --apply
```

**Without SSH:** upload the file to `wp-content/mu-plugins/`, then visit (while logged in as admin):

```
/wp-admin/?tumbl_remap_unsafe_ids=1&dry_run=1&_wpnonce=NONCE
/wp-admin/?tumbl_remap_unsafe_ids=1&apply=1&_wpnonce=NONCE
```

Replace `NONCE` with the value WordPress prints if the nonce is missing. Delete the mu-plugin file after a successful run.

4. Confirm a previously broken post opens in the editor.
5. Confirm **Posts → Add New** still works.

Future WXR exports from tumbl use safe sequential IDs automatically; re-import is not required.

---

## Fix orphan-media posts without re-importing

If posts already exist in WordPress but are missing images that tumbl now injects from `media/`, update **only those posts** in place:

1. Rebuild tumbl's index (restart, or delete `cache/index-*.json`) so the fix is live.
2. Confirm `WORDPRESS_EXPORT_MEDIA_BASE_URL` still points at your public staged `media/` folder.
3. Export a patch of affected posts only:

```bash
# Docker (recommended if local Python is older than 3.12):
docker compose -f docker-compose.dev.yml run --rm --no-deps \
  -v "${PWD}:/work" -w /work tumbl \
  python scripts/export_wordpress_content_patch.py

# Smoke-test a single post first:
docker compose -f docker-compose.dev.yml run --rm --no-deps \
  -v "${PWD}:/work" -w /work tumbl \
  python scripts/export_wordpress_content_patch.py --ids 123456789012
```

4. Create a WordPress **Application Password** (Users → Profile).
5. Dry-run, then apply via the REST API:

```bash
set WP_URL=https://blog.example.com
set WP_USER=your_username
set WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

python scripts/apply_wordpress_content_patch.py --dry-run --limit 1
python scripts/apply_wordpress_content_patch.py --limit 1   # verify that one post in WP
python scripts/apply_wordpress_content_patch.py             # remaining ~1.8k posts
```

The applicator looks up each post by slug (`tumblr-{id}` or `post-{id}` in minimal mode) and overwrites `content` only. Unaffected posts are never touched. Images load from `WORDPRESS_EXPORT_MEDIA_BASE_URL` in the updated HTML (Media Library re-import is not required if that URL is still public).

---

## Fix wrong tags on reblog posts without re-importing

**Symptom:** Posts show unrelated tags (e.g. a Batman comic tagged `quotes` and `raymond chandler` from an embedded quote reblog).

**Cause:** Legacy HTML and tumblr-utils backups embed the parent post's full HTML, including its footer. Older tumbl builds read tags from the **first** footer instead of this post's own footer at the end of the file.

**Fix in tumbl:** Rebuild the index (cache schema bump or delete `cache/index-*.json`), then export and apply a tags patch:

```bash
python scripts/export_wordpress_tags_patch.py
python scripts/apply_wordpress_tags_patch.py --dry-run --limit 1
python scripts/apply_wordpress_tags_patch.py
```

The applicator replaces each post's `post_tag` terms by slug. Future WXR exports use the corrected tags automatically.

---

## See also

- [Quick start](wordpress-export-quickstart.md) — condensed step-by-step version of this guide
- [Export formats](export-formats.md) — Tumblr backup layouts tumbl accepts
- [README](../README.md) — Environment variable summary
