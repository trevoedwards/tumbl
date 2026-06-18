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
