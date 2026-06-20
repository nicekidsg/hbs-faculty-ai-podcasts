# HBS Faculty on AI — Podcast Tracker

An interactive, bilingual (English / 中文) single-page directory of podcast episodes from the past year in which **Harvard Business School faculty** discuss artificial intelligence and its impact on strategy, work, and business.

## Features

- 🌐 **EN / 中文** language toggle — full UI plus every episode title and summary
- 🔎 Live search across professors, topics, and shows
- 🏷️ Filter by professor or by show
- ↕️ Sort by date (newest/oldest) or professor name
- 🤖 **Auto-updates daily** — a GitHub Action checks tracked podcast feeds each morning and adds new AI episodes by HBS faculty
- 📄 No build step — pure HTML/CSS/JS, served via GitHub Pages

## How the daily update works

1. `.github/workflows/daily-update.yml` runs every day at **06:00 UTC** (and on-demand from the Actions tab).
2. It runs `scripts/update_episodes.py`, which pulls RSS feeds for tracked shows (The Parlor Room, Managing the Future of Work, After Hours, HBR IdeaCast, Cold Call), keeps episodes that mention AI **and** a tracked HBS faculty member, and merges new ones into `data.json`.
3. The script regenerates the episode list embedded in `index.html` (between the `EPISODES_START` / `EPISODES_END` markers).
4. If anything changed, the Action commits and pushes — GitHub Pages redeploys automatically.

The workflow pushes using the built-in `GITHUB_TOKEN`, so **no personal token or secret needs to be stored** in the repo.

New auto-added episodes appear in English first; their Chinese fields are left blank and the site shows the English text until a translation is added to `data.json`.

## Project structure

```
index.html                      # the site (data embedded for offline-friendly preview)
data.json                       # source of truth for episodes
scripts/update_episodes.py      # daily updater / regenerator
.github/workflows/daily-update.yml
```

## Editing or adding episodes by hand

Edit `data.json`, then run `python scripts/update_episodes.py` to re-embed the data into `index.html`. (Requires `pip install feedparser`.)

## Notes

A curated directory for educational reference. Titles, dates, and links point to the original publishers (HBS Online, HBR, MIT Sloan Management Review, CXOTalk, and others). Not affiliated with or endorsed by Harvard Business School.
