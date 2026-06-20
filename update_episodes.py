#!/usr/bin/env python3
"""
Daily updater for the HBS Faculty on AI podcast tracker.

What it does:
  1. Loads the current dataset from data.json (source of truth).
  2. Pulls RSS feeds for tracked podcasts, finds recent episodes that are
     (a) about AI and (b) feature an HBS faculty member.
  3. Merges any genuinely new episodes into data.json (deduped by URL).
  4. Regenerates the embedded EPISODES array inside index.html between the
     /* EPISODES_START */ ... /* EPISODES_END */ markers.

It is intentionally defensive: if a feed is unreachable, it is skipped and the
script still regenerates index.html from data.json, so a run is always safe.

New auto-added episodes have empty Chinese fields; the site falls back to the
English text until a human (or a future translation step) fills them in.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

try:
    import feedparser
except ImportError:
    sys.stderr.write("feedparser not installed; run: pip install feedparser\n")
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data.json")
HTML = os.path.join(ROOT, "index.html")

LOOKBACK_DAYS = 400  # keep ~"past year" plus a margin

# HBS faculty we track (surnames / distinctive names are enough to match).
FACULTY = [
    "Oberholzer-Gee", "Bojinov", "Christina Wallace", "Joe Fuller", "Bill Kerr",
    "Sunil Gupta", "Tsedal Neeley", "Karim Lakhani", "Raffaella Sadun",
    "Marco Iansiti", "Linda Hill", "Nien-hê Hsieh", "Nien-he Hsieh",
    "Mihir Desai", "Youngme Moon", "Amy Edmondson", "Frances Frei",
    "Rebecca Henderson", "Suraj Srinivasan", "Das Narayandas",
    "Ethan Bernstein", "Prithwiraj Choudhury", "Edward McFowland", "Feng Zhu",
    "Ranjay Gulati", "Michael Porter", "Rosabeth Moss Kanter", "Iavor Bojinov",
]

AI_KEYWORDS = [
    "artificial intelligence", " ai ", " ai,", " ai.", " ai-", "a.i.", "genai",
    "generative ai", "machine learning", "chatgpt", "llm", "large language model",
    "agentic", "ai-driven", "ai adoption", "copilot", "gen ai", "algorithm",
]

# apple_id resolves the RSS feed via the iTunes lookup API (robust to URL changes).
# require_faculty=True means a tracked faculty name must appear (for broad shows).
SOURCES = [
    {"name": "The Parlor Room", "apple_id": "1709512413", "require_faculty": False},
    {"name": "Managing the Future of Work", "apple_id": "1395603706", "require_faculty": False},
    {"name": "After Hours", "apple_id": "1363110130", "require_faculty": False},
    {"name": "HBR IdeaCast", "feed": "http://feeds.harvardbusiness.org/harvardbusiness/ideacast", "require_faculty": True},
    {"name": "Cold Call", "feed": "http://feeds.harvardbusiness.org/harvardbusiness/cold-call", "require_faculty": True},
]

UA = "Mozilla/5.0 (compatible; HBS-AI-Podcast-Tracker/1.0)"


def resolve_feed(apple_id):
    url = f"https://itunes.apple.com/lookup?id={apple_id}&entity=podcast"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data["results"][0]["feedUrl"]


def mentions_ai(text):
    t = " " + text.lower() + " "
    return any(k in t for k in AI_KEYWORDS)


def find_faculty(text):
    for name in FACULTY:
        if name.lower() in text.lower():
            return name
    return None


def entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        v = entry.get(key)
        if v:
            return datetime(*v[:6], tzinfo=timezone.utc)
    return None


def collect_new(existing_urls):
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    found = []
    for src in SOURCES:
        try:
            feed_url = src.get("feed") or resolve_feed(src["apple_id"])
            parsed = feedparser.parse(feed_url, request_headers={"User-Agent": UA})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"[skip] {src['name']}: {e}\n")
            continue
        for e in parsed.entries:
            link = (e.get("link") or "").strip()
            title = (e.get("title") or "").strip()
            summary = re.sub("<[^>]+>", " ", e.get("summary", ""))
            if not link or not title or link in existing_urls:
                continue
            d = entry_date(e)
            if not d or d < cutoff:
                continue
            blob = f"{title} {summary}"
            if not mentions_ai(blob):
                continue
            fac = find_faculty(blob)
            if src["require_faculty"] and not fac:
                continue
            found.append({
                "prof": fac or "HBS Faculty",
                "show": src["name"],
                "date": d.strftime("%Y-%m-%d"),
                "title": title,
                "desc": (summary.strip()[:300] + "…") if summary.strip() else title,
                "title_zh": "",
                "desc_zh": "",
                "url": link,
            })
            existing_urls.add(link)
    return found


def regenerate_html(episodes):
    with open(HTML, "r", encoding="utf-8") as f:
        html = f.read()
    block = (
        "/* EPISODES_START — auto-generated from data.json by "
        "scripts/update_episodes.py; do not edit by hand */\n"
        "const EPISODES = " + json.dumps(episodes, ensure_ascii=False, indent=2) +
        ";\n/* EPISODES_END */"
    )
    pat = re.compile(r"/\* EPISODES_START.*?/\* EPISODES_END \*/", re.S)
    if not pat.search(html):
        sys.stderr.write("EPISODES markers not found in index.html\n")
        sys.exit(1)
    html = pat.sub(lambda _m: block, html)
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    with open(DATA, "r", encoding="utf-8") as f:
        episodes = json.load(f)
    existing = {e["url"] for e in episodes}

    new = collect_new(existing)
    if new:
        episodes.extend(new)

    # newest first
    episodes.sort(key=lambda e: e["date"], reverse=True)

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)
        f.write("\n")

    regenerate_html(episodes)

    print(f"Added {len(new)} new episode(s); total now {len(episodes)}.")
    for e in new:
        print(f"  + [{e['date']}] {e['show']}: {e['title']}")


if __name__ == "__main__":
    main()
