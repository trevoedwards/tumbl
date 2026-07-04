"""Generate fake Tumblr archive demo data at .demo/data (modern XML layout)."""

from __future__ import annotations

import io
import sys
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow is required: pip install Pillow", file=sys.stderr)
    raise SystemExit(1)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / ".demo" / "data"
MEDIA_DIR = OUTPUT_ROOT / "media"
POSTS_DIR = OUTPUT_ROOT / "posts"

PHOTO_IDS = [
    100002,
    100005,
    100008,
    100011,
    100014,
    100017,
    100020,
    100023,
    100026,
    100029,
    100032,
    100035,
]

PHOTO_CAPTIONS = [
    "Blorptastic evening light over the wharf district.",
    "Mood: scrambled pixels and quiet thunder.",
    "Found this corner while wandering nowhere in particular.",
    "The colors insisted on being photographed.",
    "Soft focus, loud feelings.",
    "Rain on glass, city underneath.",
    "Golden hour refuses to clock out.",
    "Shadows doing their best impression of art.",
    "A bench, a breeze, and questionable life choices.",
    "Horizon line holding the sky in place.",
    "Late summer pretending it is still June.",
    "Frame within a frame within a Tuesday.",
]

TEXT_POSTS: list[tuple[int, str, str, list[str]]] = [
    (
        100001,
        "Notes from the margins",
        "<p>Velvet syntax drifts through the archive like misplaced punctuation. "
        "Nobody asked for a manifesto, yet here we are, stacking sentences into "
        "teetering monuments of almost-meaning.</p>"
        "<p>Tomorrow might bring clarity. Today brings <em>gibberish stew</em> and "
        "a stubborn refusal to delete the draft.</p>",
        ["thoughts", "demo", "writing"],
    ),
    (
        100003,
        "",
        "<p>Current status: caffeinated, mildly feral, and reorganizing bookmarks "
        "I will never open again. The tabs multiply when unattended.</p>",
        ["personal", "demo"],
    ),
    (
        100006,
        "Weekend dispatch",
        "<p>Attempted productivity. Achieved instead a comprehensive survey of "
        "cloud shapes and the exact texture of doing nothing on purpose.</p>"
        "<p>Would recommend, with reservations.</p>",
        ["weekend", "thoughts"],
    ),
    (
        100009,
        "",
        "<p>Hot take: soup is just a beverage that got ambitious. "
        "Discuss among yourselves while I stir this metaphor too long.</p>",
        ["food", "nonsense", "demo"],
    ),
    (
        100012,
        "On keeping drafts",
        "<p>Every unpublished paragraph is a time capsule addressed to a stranger "
        "who might never arrive. I label mine <strong>maybe later</strong> and "
        "mean it every single time.</p>",
        ["writing", "archive"],
    ),
    (
        100015,
        "",
        "<p>Listening to the same song on repeat until it becomes wallpaper. "
        "The lyrics dissolve. What remains is mood, memory, and a faint "
        "suspicion that nostalgia is a skilled liar.</p>",
        ["music", "mood"],
    ),
    (
        100018,
        "Small victories",
        "<p>Inbox zero lasted eleven minutes. Still counts.</p>"
        "<p>Also: fixed the wobbly chair, answered one email, and did not "
        "spiral about the rest. Progress wears humble shoes.</p>",
        ["personal", "demo"],
    ),
    (
        100021,
        "",
        "<p>Weather report: partly metaphorical with a chance of introspection "
        "scattered across the afternoon. Carry an umbrella for unexpected "
        "feelings.</p>",
        ["thoughts", "nature"],
    ),
    (
        100024,
        "Library hours",
        "<p>Checked out three books and read the first chapters of all of them. "
        "A triptych of good intentions. The due date looms like a polite villain.</p>",
        ["books", "demo"],
    ),
    (
        100027,
        "",
        "<p>Sometimes the best plan is no plan: walk until the street names "
        "stop sounding familiar, then walk back before your phone dies.</p>",
        ["personal", "nature", "thoughts"],
    ),
]

QUOTE_POSTS: list[tuple[int, str, str, list[str]]] = [
    (
        100004,
        "The only way out is through, preferably with snacks.",
        "— A very tired philosopher, probably",
        ["quotes", "demo"],
    ),
    (
        100010,
        "We are all just walking each other home, except when we take the scenic route.",
        "— Folk wisdom, misremembered",
        ["quotes", "thoughts"],
    ),
    (
        100016,
        "Art is what you can get away with before the cat knocks it over.",
        "— Studio folklore",
        ["quotes", "art"],
    ),
    (
        100022,
        "Not all those who wander are lost, but the GPS disagrees loudly.",
        "— Travel journal, page 42",
        ["quotes", "travel"],
    ),
    (
        100028,
        "In the middle of difficulty lies opportunity, and also misplaced keys.",
        "— Attributed to everyone, confirmed by no one",
        ["quotes", "demo"],
    ),
]

ASK_POSTS: list[tuple[int, str, str, list[str]]] = [
    (
        100007,
        "<p>What is your favorite kind of weather for thinking?</p>",
        "<p>Overcast with a light wind. Enough drama for atmosphere, not enough "
        "to ruin the notebook.</p>",
        ["ask", "personal"],
    ),
    (
        100013,
        "<p>Any tips for organizing a digital archive?</p>",
        "<p>Start with consistent names, back up twice, and accept that you will "
        "still search by vague memory instead of filenames.</p>",
        ["ask", "archive", "demo"],
    ),
    (
        100019,
        "<p>What song is on repeat right now?</p>",
        "<p>Whatever was playing in the cafe when I sat down. I have made it "
        "my entire personality for the next forty minutes.</p>",
        ["ask", "music"],
    ),
]

LINK_POSTS: list[tuple[int, str, str, list[str]]] = [
    (
        100025,
        "A Field Guide to Cloud Shapes",
        "https://example.com/cloud-field-guide",
        ["links", "nature", "demo"],
    ),
    (
        100031,
        "How to Read a City by Its Sidewalk Cracks",
        "https://example.com/sidewalk-cartography",
        ["links", "urban", "thoughts"],
    ),
]

CHAT_POSTS: list[tuple[int, str, list[tuple[str, str]], list[str]]] = [
    (
        100030,
        "Kitchen negotiations",
        [
            ("Me", "We have ingredients for either pasta or salad."),
            ("Roommate", "Pasta is a salad if you believe hard enough."),
            ("Me", "That is not how belief works."),
            ("Roommate", "Watch me boil lettuce."),
        ],
        ["chat", "food", "demo"],
    ),
    (
        100033,
        "Late night brainstorm",
        [
            ("Me", "What if the moon is just the sun's backup file?"),
            ("Friend", "Restore when?"),
            ("Me", "Full moon. Obviously."),
            ("Friend", "I'm going back to sleep."),
        ],
        ["chat", "nonsense", "thoughts"],
    ),
]

REBLOG_POST = (
    100034,
    "<p>Reblogging this because it still rings true: the best archives are the "
    "ones you can browse at 2am without regret.</p>",
    "March 12th, 2024 9:15pm",
    ["reblog", "archive", "demo"],
)

TIMESTAMPS: dict[int, str] = {
    100035: "July 4th, 2025 11:42am",
    100034: "March 12th, 2024 9:15pm",
    100033: "February 8th, 2024 1:03am",
    100032: "January 19th, 2024 5:20pm",
    100031: "December 3rd, 2023 8:47am",
    100030: "November 14th, 2023 10:11pm",
    100029: "October 2nd, 2023 4:55pm",
    100028: "September 21st, 2023 7:30am",
    100027: "August 7th, 2023 6:18pm",
    100026: "July 22nd, 2023 2:44pm",
    100025: "June 5th, 2023 9:02am",
    100024: "May 17th, 2023 8:33pm",
    100023: "April 9th, 2023 3:16pm",
    100022: "March 28th, 2023 11:50am",
    100021: "February 14th, 2023 7:05pm",
    100020: "January 30th, 2023 12:22am",
    100019: "December 11th, 2022 4:40pm",
    100018: "November 2nd, 2022 9:14am",
    100017: "October 18th, 2022 6:27pm",
    100016: "September 4th, 2022 1:58pm",
    100015: "August 20th, 2022 10:03pm",
    100014: "July 7th, 2022 5:45am",
    100013: "June 23rd, 2022 2:11pm",
    100012: "May 9th, 2022 8:29pm",
    100011: "April 1st, 2022 3:37pm",
    100010: "March 15th, 2022 11:08am",
    100009: "February 27th, 2022 7:52pm",
    100008: "January 12th, 2022 4:16pm",
    100007: "December 29th, 2021 9:33pm",
    100006: "November 8th, 2021 1:20pm",
    100005: "October 24th, 2021 6:05am",
    100004: "September 10th, 2021 8:41pm",
    100003: "August 3rd, 2021 12:14pm",
    100001: "July 4th, 2020 2:30pm",
    100002: "June 18th, 2021 5:50pm",
}


def _add_tags(post_el: ET.Element, tags: list[str]) -> None:
    for tag in tags:
        tag_el = ET.SubElement(post_el, "tag")
        tag_el.text = tag


def _download_and_convert_webp(post_id: int, dest: Path) -> None:
    url = f"https://picsum.photos/seed/tumbl-demo-{post_id}/900/675.jpg"
    request = urllib.request.Request(url, headers={"User-Agent": "tumbl-demo-generator/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()

    image = Image.open(io.BytesIO(raw))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    elif image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background

    max_width = 900
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, format="WEBP", quality=82, method=6)
    print(f"  wrote {dest.relative_to(REPO_ROOT)} ({dest.stat().st_size // 1024} KB)")


def _build_posts_xml() -> str:
    posts_el = ET.Element("posts")

    for post_id, title, body, tags in TEXT_POSTS:
        post_el = ET.SubElement(
            posts_el,
            "post",
            {"id": str(post_id), "type": "regular", "date": TIMESTAMPS[post_id]},
        )
        _add_tags(post_el, tags)
        if title:
            title_el = ET.SubElement(post_el, "regular-title")
            title_el.text = title
        body_el = ET.SubElement(post_el, "regular-body")
        body_el.text = body

    for index, post_id in enumerate(PHOTO_IDS):
        post_el = ET.SubElement(
            posts_el,
            "post",
            {"id": str(post_id), "type": "photo", "date": TIMESTAMPS[post_id]},
        )
        _add_tags(
            post_el,
            ["photography", "demo", "nature"] if index % 2 == 0 else ["photography", "mood"],
        )
        caption_el = ET.SubElement(post_el, "photo-caption")
        caption_el.text = f"<p>{PHOTO_CAPTIONS[index]}</p>"

    for post_id, quote, source, tags in QUOTE_POSTS:
        post_el = ET.SubElement(
            posts_el,
            "post",
            {"id": str(post_id), "type": "quote", "date": TIMESTAMPS[post_id]},
        )
        _add_tags(post_el, tags)
        quote_el = ET.SubElement(post_el, "quote-text")
        quote_el.text = quote
        source_el = ET.SubElement(post_el, "quote-source")
        source_el.text = source

    for post_id, question, answer, tags in ASK_POSTS:
        post_el = ET.SubElement(
            posts_el,
            "post",
            {"id": str(post_id), "type": "answer", "date": TIMESTAMPS[post_id]},
        )
        _add_tags(post_el, tags)
        question_el = ET.SubElement(post_el, "question")
        question_el.text = question
        answer_el = ET.SubElement(post_el, "answer")
        answer_el.text = answer

    for post_id, text, url, tags in LINK_POSTS:
        post_el = ET.SubElement(
            posts_el,
            "post",
            {"id": str(post_id), "type": "link", "date": TIMESTAMPS[post_id]},
        )
        _add_tags(post_el, tags)
        text_el = ET.SubElement(post_el, "link-text")
        text_el.text = text
        url_el = ET.SubElement(post_el, "link-url")
        url_el.text = url

    for post_id, title, lines, tags in CHAT_POSTS:
        post_el = ET.SubElement(
            posts_el,
            "post",
            {"id": str(post_id), "type": "conversation", "date": TIMESTAMPS[post_id]},
        )
        _add_tags(post_el, tags)
        title_el = ET.SubElement(post_el, "conversation-title")
        title_el.text = title
        conv_el = ET.SubElement(post_el, "conversation")
        for name, content in lines:
            ET.SubElement(conv_el, "line", {"name": name, "label": name}).text = content

    reblog_id, reblog_body, reblog_date, reblog_tags = REBLOG_POST
    reblog_el = ET.SubElement(
        posts_el,
        "post",
        {
            "id": str(reblog_id),
            "type": "regular",
            "date": reblog_date,
            "url": "https://demo-blog.tumblr.com/post/1234567890123456789/100034",
        },
    )
    _add_tags(reblog_el, reblog_tags)
    reblog_body_el = ET.SubElement(reblog_el, "regular-body")
    reblog_body_el.text = reblog_body
    parent_url_el = ET.SubElement(reblog_el, "reblogged-from-url")
    parent_url_el.text = "https://original-poster.tumblr.com/post/9876543210987654321/100012"
    parent_name_el = ET.SubElement(reblog_el, "reblogged-from-name")
    parent_name_el.text = "original-poster"

    tumblr_root = ET.Element("tumblr", {"version": "1.0"})
    tumblr_root.append(posts_el)

    xml_body = ET.tostring(tumblr_root, encoding="unicode")
    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        {xml_body}
        """
    )


def generate() -> None:
    print(f"Generating demo archive at {OUTPUT_ROOT.relative_to(REPO_ROOT)}/")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading and converting photo media...")
    for post_id in PHOTO_IDS:
        dest = MEDIA_DIR / f"{post_id}.webp"
        _download_and_convert_webp(post_id, dest)

    posts_xml = _build_posts_xml()
    posts_path = POSTS_DIR / "posts.xml"
    posts_path.write_text(posts_xml, encoding="utf-8")
    print(f"  wrote {posts_path.relative_to(REPO_ROOT)}")

    print("Done.")


if __name__ == "__main__":
    generate()
