#!/usr/bin/env python3
"""Refresh the latest Musings for the Mental posts from the Substack RSS feed."""

from __future__ import annotations

import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path


FEED_URL = "https://edwardyaeger.substack.com/feed"
POST_LIMIT = 6
START_MARKER = "          <!-- SUBSTACK_POSTS_START -->"
END_MARKER = "          <!-- SUBSTACK_POSTS_END -->"
ROOT = Path(__file__).resolve().parents[1]
MUSING_PAGE = ROOT / "musing.html"
SUMMARY_OVERRIDES = {
    "https://edwardyaeger.substack.com/p/feelings-vs-emotions":
        "A concise distinction between two terms that are often used interchangeably.",
    "https://edwardyaeger.substack.com/p/your-overthinking-is-not-only-counterproductive-102":
        "The clinical view: what repetitive thought is doing, what it is avoiding, and why more thinking rarely resolves it.",
    "https://edwardyaeger.substack.com/p/your-overthinking-is-not-only-counterproductive":
        "On the cultural elevation of overthinking into a personality, a virtue, and sometimes a performance.",
    "https://edwardyaeger.substack.com/p/if-i-earned-a-dime-for-everyone-who":
        "Introducing the next theme: why self-possession and emotional processing are not the same thing.",
    "https://edwardyaeger.substack.com/p/how-to-instantly-feel-better":
        "A compact set of prompts for moving emotion through rather than merely thinking around it.",
}
GENERIC_DESCRIPTIONS = {
    "FIELD NOTES",
    "CLINIC NOTES",
    "CHEATSHEET OF THE WEEK",
}


def text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    return (child.text or "").strip() if child is not None else ""


def post_type(description: str) -> str:
    normalized = re.sub(r"\s+", " ", description).strip()
    labels = {
        "FIELD NOTES": "Field Notes",
        "CLINIC NOTES": "Clinic Notes",
        "CHEATSHEET OF THE WEEK": "Cheatsheet",
    }
    return labels.get(normalized.upper(), "Musing")


def post_date(raw_date: str) -> str:
    parsed = parsedate_to_datetime(raw_date)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


def render_post(item: ET.Element) -> str:
    title = text(item, "title")
    link = text(item, "link")
    description = text(item, "description")
    published = text(item, "pubDate")
    category = text(item, "category")
    label = category or post_type(description)
    summary = SUMMARY_OVERRIDES.get(link, description)
    if summary.upper() in GENERIC_DESCRIPTIONS:
        summary = ""
    summary_markup = (
        f'\n              <p class="post-summary">{html.escape(summary)}</p>'
        if summary
        else ""
    )

    return f"""          <a class="post-row" href="{html.escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">
            <div class="post-meta">
              <span class="post-type">{html.escape(label)}</span>
              <span>{html.escape(post_date(published))}</span>
            </div>
            <div class="post-copy">
              <h3 class="post-title">{html.escape(title)}</h3>{summary_markup}
            </div>
            <span class="post-arrow" aria-hidden="true">&rarr;</span>
          </a>"""


def fetch_feed() -> bytes:
    request = urllib.request.Request(
        FEED_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> int:
    root = ET.fromstring(fetch_feed())
    items = root.findall("./channel/item")[:POST_LIMIT]
    if len(items) != POST_LIMIT:
        raise RuntimeError(f"Expected {POST_LIMIT} feed items, found {len(items)}")

    current = MUSING_PAGE.read_text(encoding="utf-8")
    if current.count(START_MARKER) != 1 or current.count(END_MARKER) != 1:
        raise RuntimeError("Substack post markers are missing or duplicated")

    posts = "\n\n".join(render_post(item) for item in items)
    replacement = f"{START_MARKER}\n{posts}\n          {END_MARKER.strip()}"
    updated = re.sub(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        replacement,
        current,
        count=1,
        flags=re.DOTALL,
    )

    if updated == current:
        print("Substack posts are already current.")
        return 0

    MUSING_PAGE.write_text(updated, encoding="utf-8")
    print(f"Updated {MUSING_PAGE.name} with {len(items)} posts at {datetime.now().isoformat(timespec='seconds')}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Substack update failed: {exc}", file=sys.stderr)
        raise
