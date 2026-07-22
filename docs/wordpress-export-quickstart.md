# WordPress export: quick start

Condensed steps for migrating a Tumblr archive into an **existing** WordPress site. Full details, troubleshooting, and edge cases: [WordPress export guide](wordpress-export.md).

**What you'll get:** one WordPress **Post** per Tumblr post (not one Page), with tags, dates, and HTML content. Media is optional and requires a public URL (step 3).

---

## 1. Enable export

Add to your `.env` and restart tumbl:

```bash
WORDPRESS_EXPORT_ENABLED=true
WORDPRESS_EXPORT_AUTHOR=admin
WORDPRESS_EXPORT_SITE_URL=https://usersite.com
```

## 2. Back up your WordPress site

Back up the database and `wp-content/uploads` before importing anything.

## 3. (For media) Stage `media/` on a public URL

WXR can't embed files — WordPress downloads media from a URL it can reach.

1. Upload your archive's `media/` folder somewhere public over HTTPS — often your WordPress host's own storage (e.g. Hostinger), or S3/R2/a static host.
2. Add to `.env` and restart tumbl:

   ```bash
   WORDPRESS_EXPORT_MEDIA_BASE_URL=https://usersite.com/tumblr-media
   ```

Skip this step if you only need text/tags — images/video will stay broken without it.

## 4. Download the export

In tumbl: **Settings → WordPress export → Download WordPress export (.xml)**.

(Or fetch `/export/wordpress.xml` directly.)

## 5. Import into WordPress

1. WordPress admin → **Tools → Import → WordPress** (install the importer plugin if prompted).
2. Upload the `.xml` file → **Upload file and import**.
3. Author mapping: **assign posts to an existing user** (recommended).
4. Check **Download and import file attachments** only if you set up step 3.
5. Click **Submit** and wait.

## 6. Verify

- **Posts → All Posts** — one row per Tumblr post
- **Media → Library** — attachments present (if imported)
- Open a few posts on the front end — content, tags, and images look right

---

Need custom permalinks, theme color/font matching, minimal branding, or troubleshooting? See the [full WordPress export guide](wordpress-export.md).
