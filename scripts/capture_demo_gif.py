"""Capture a slow-scrolling demo GIF of the tumbl feed."""

from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

URL = os.environ.get("DEMO_URL", "http://host.docker.internal:8862")
PAGE = os.environ.get("DEMO_PAGE", "").strip()
OUTPUT = Path(os.environ.get("OUTPUT", "docs/demo.gif"))
WIDTH = int(os.environ.get("DEMO_WIDTH", "800"))
HEIGHT = int(os.environ.get("DEMO_HEIGHT", "500"))
FRAMES = int(os.environ.get("DEMO_FRAMES", "48"))
FRAME_MS = int(os.environ.get("DEMO_FRAME_MS", "130"))
SCROLL_PX = int(os.environ.get("DEMO_SCROLL_PX", "1800"))
PALETTE_COLORS = int(os.environ.get("DEMO_PALETTE_COLORS", "64"))


def _build_palette(source: Image.Image) -> Image.Image:
    sample = source.copy()
    sample.thumbnail((320, 200))
    return sample.convert("P", palette=Image.Palette.ADAPTIVE, colors=PALETTE_COLORS)


def _target_url() -> str:
    base = URL.rstrip("/")
    if not PAGE:
        return base + "/"
    return f"{base}/?page={PAGE}"


def capture() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.goto(_target_url(), wait_until="load", timeout=60_000)
        page.wait_for_timeout(2500)

        for index in range(FRAMES):
            scroll_y = 0 if FRAMES <= 1 else int((index / (FRAMES - 1)) * SCROLL_PX)
            page.evaluate("(y) => window.scrollTo(0, y)", scroll_y)
            page.wait_for_timeout(80)
            png = page.screenshot(type="png")
            frames.append(Image.open(io.BytesIO(png)).convert("RGB"))

        browser.close()

    palette = _build_palette(frames[len(frames) // 3])
    optimized = [frame.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for frame in frames]
    optimized[0].save(
        OUTPUT,
        save_all=True,
        append_images=optimized[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB, {FRAMES} frames)")


if __name__ == "__main__":
    capture()
