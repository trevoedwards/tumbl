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

Timestamps and tags are parsed from each post HTML file's footer. Submission posts live under `posts/html/submissions/`.

**Known export quirk:** Some legacy exports write the same wrong local media path (often another post's `{postId}.png`) into many unrelated post HTML files. tumbl corrects this at index time when matching `{postId}.*` files exist in `media/`—including photosets where every `<img>` was given the same placeholder path. Posts with no `{postId}.*` file on disk keep the export's original reference; a fresh full extract from the original ZIP may recover missing files if the export itself is complete.

**If images are still wrong after indexing:** Extract the original Tumblr backup ZIP into a clean folder (do not merge with an old extract), mount that folder as `ARCHIVE_PATH`, and delete the index cache so tumbl rebuilds:

```bash
docker compose exec tumbl rm -f /app/cache/index-*.json /app/cache/index-*.meta.json
docker compose restart tumbl
```

Compare `media/` file counts before and after. If a post still has no `{postId}.*` file after a fresh extract, the export did not include that media.

**Quote posts:** Legacy exports do not record post type in metadata. tumbl detects native quote posts heuristically (top-level `<blockquote>` or plain text with an attribution `.caption`) and normalizes them to the same quote markup used by modern XML exports. Reblogs, photos, and submissions are excluded from quote detection.

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

**Quote posts:** When `posts.xml` contains `<post type="quote">`, tumbl uses the structured `quote-text` and `quote-source` fields directly. This is the authoritative quote source when both XML and HTML are present in the export layout.

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

**Quote posts:** tumblr-utils exports mark quote posts with `<article class="quote">` (or `data-type="quote"`). tumbl reads that metadata and normalizes the body for quote styling. Legacy-style blockquote markup in other formats is also detected when article metadata is absent.

## Out of scope

The privacy/account JSON download from Tumblr settings is **not** supported—tumbl expects a full blog media export with HTML or XML post data.

## Exporting to WordPress

All three supported input formats can be converted to a WordPress WXR import file when optional export is enabled. This is useful if you have an offline backup but no live Tumblr account for WordPress.com's [Tumblr importer](https://wordpress.com/support/import/import-from-tumblr/).

See **[WordPress export](wordpress-export.md)** for configuration, import steps, and media limitations.
