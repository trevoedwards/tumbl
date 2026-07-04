# Demo archive

Fake Tumblr export data for trying tumbl without a real backup. Contains **35 posts** (2 feed pages at 20 posts/page) with stock photos, quotes, gibberish text, asks, links, and chats.

## Layout

```
data/
├── media/           # WebP images for photo posts
└── posts/
    └── posts.xml    # Modern official export format
```

## Run locally

```bash
# Windows
set ARCHIVE_PATH=.demo/data
set BLOG_TITLE=Archive Demo

# macOS / Linux
export ARCHIVE_PATH=.demo/data
export BLOG_TITLE="Archive Demo"
```

Then start the app (`python -m app.main`, `flask run`, or Docker with `ARCHIVE_PATH` overridden).

Open [http://localhost:8862](http://localhost:8862).

If you previously indexed a different archive, delete the cache so tumbl rebuilds:

```bash
# Windows
del .cache\index-*.json .cache\index-*.meta.json

# macOS / Linux
rm -f .cache/index-*.json .cache/index-*.meta.json
```

## Regenerate

Requires [Pillow](https://pypi.org/project/Pillow/) and network access to download stock images:

```bash
pip install Pillow
python scripts/generate_demo_archive.py
```

Images are downloaded from [Lorem Picsum](https://picsum.photos/), converted to WebP, and saved under `data/media/`.
