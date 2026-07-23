# Export formats

tumbl supports three Tumblr backup layouts. Use the summary table in the [README](../README.md#supported-export-formats) to identify which one you have; the sections below describe each layout in detail.

## Legacy HTML backup (Format A)

Tumblr's early automated export, often unzipped to a `.tumblrbackup`-style folder:

```
archive/
├── media/                  # {postId}.jpg, {postId}_0.gif, etc.
├── conversations/          # HTML conversations (optional)
└── posts/
    ├── style.css
    ├── posts_index.html
    └── html/
        ├── {postId}.html
        └── submissions/
            └── {postId}.html
```

Timestamps and tags are parsed from each post HTML file's footer (the **last** `#footer` / `<footer>` in the file — reblogs embed the parent post's footer first). Submission posts live under `posts/html/submissions/`.

**Known export quirk:** Some legacy exports write the same wrong local media path (often another post's `{postId}.png`) into many unrelated post HTML files. tumbl corrects this at index time when matching `{postId}.*` files exist in `media/`—including photosets where every `<img>` was given the same placeholder path. Posts with no `{postId}.*` file on disk keep the export's original reference; a fresh full extract from the original ZIP may recover missing files if the export itself is complete.

**Omitted `<img>` tags:** Many legacy photo, link, and Instagram posts ship with a caption or empty link wrapper but no `<img>` in the HTML, even when `media/{postId}.*` exists on disk. tumbl injects those local files into the post body at index time (same behavior as the modern XML parser), so the viewer and WordPress export include the image.

**If images are still wrong after indexing:** Extract the original Tumblr backup ZIP into a clean folder (do not merge with an old extract), mount that folder as `ARCHIVE_PATH`, and delete the index cache so tumbl rebuilds:

```bash
docker compose exec tumbl rm -f /app/cache/index-*.json /app/cache/index-*.meta.json
docker compose restart tumbl
```

Compare `media/` file counts before and after. If a post still has no `{postId}.*` file after a fresh extract, the export did not include that media.

## Modern official export (Format B)

Tumblr's current export from [**Settings → Export**](https://help.tumblr.com/export-your-blog/). After downloading the ZIP, extract it fully—including nested `posts.zip`:

```
export-folder/
├── media/
├── messages.xml            # conversations (not yet displayed)
└── posts/
    ├── posts.xml           # canonical structured post data
    └── html/
        └── {postId}.html
```

tumbl reads `posts.xml` as the source of truth and serves images from the local `media/` folder, falling back to Tumblr CDN URLs when a file is missing.

**`posts.zip`:** tumbl auto-extracts this on startup when needed. You can also extract it manually before launch.

Extraction limits (path traversal is rejected): up to **100,000** files and **10 GB** uncompressed total. Large Tumblr exports (~5 GB, ~15k files) fit comfortably within these caps.

> **Hybrid archives:** If both `posts/posts.xml` and `posts/html/*.html` are present, tumbl will refuse to start. Remove one layout—keep XML for the modern export, or keep HTML for the legacy layout.

## tumblr-utils backup (Format C)

Community backups from [bbolli/tumblr-utils](https://github.com/bbolli/tumblr-utils) / `tumblr-backup`:

```
export-folder/
├── index.html
├── media/
└── posts/
    └── {postId}.html
```

Each post is read from `posts/{id}.html`. Local media is resolved from the `media/` folder.

## Out of scope

The privacy/account JSON download from Tumblr settings is **not** supported—tumbl expects a full blog media export with HTML or XML post data.

## Exporting to WordPress

All three supported input formats can be converted to a WordPress WXR import file when optional export is enabled. This is useful if you have an offline backup but no live Tumblr account for WordPress.com's [Tumblr importer](https://wordpress.com/support/import/import-from-tumblr/).

**Structure:** each Tumblr post becomes an individual WordPress **Post** (not one Page). Media is imported via a public HTTPS base URL for your archive `media/` folder.

See **[WordPress export](wordpress-export.md)** for what you get in WordPress, the full import walkthrough, and media staging — or the [quick start](wordpress-export-quickstart.md) for a condensed version.
