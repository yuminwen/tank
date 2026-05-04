# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the server (port 8765, debug mode)
python3 server.py
```

No build step, no linting, no tests. The frontend is a single vanilla HTML file with no bundler.

## Architecture

A Flask app that aggregates trending/hot topics from Bilibili, Weibo, and Douyin into a single "AI 雷达" dashboard. Everything lives in two files:

### Backend — `server.py`

- **`/`** — serves the static `index.html`
- **`/api/hot?ai_only=true|false`** — returns cached data; auto-refreshes cache if older than 5 minutes (CACHE_TTL = 300s). Responds with `platforms` (raw per-platform lists), `all` (round-robin interleaved), `ai_count`, `total_count`, `updated_at`.
- **`/api/refresh`** — force-refreshes the cache immediately

Data fetching: `fetch_bilibili()`, `fetch_weibo()`, `fetch_douyin()` each call `safe_fetch()` against uapis.cn. Bilibili has a fallback to `s.search.bilibili.com/main/hotword`. Results are normalized via `parse_items()` into a common shape: `{rank, title, hot_value, platform, is_ai, url, owner}`.

AI detection: `is_ai_related()` does case-insensitive keyword matching against a hardcoded list (~35 Chinese/English AI terms in `AI_KEYWORDS`). This runs on every item during parse, not lazily.

Cache: single in-process dict (`cache = {"data": ..., "timestamp": ...}`) with a deep copy on read. No concurrency handling — single-user development server.

### Frontend — `static/index.html`

Single file, no framework. Dark theme with CSS variables. Key behaviors:
- Platform tabs filter client-side (`all` / `bilibili` / `weibo` / `douyin`)
- AI-only toggle (`aiOnly` boolean) layered on top of platform filter
- 5-minute countdown timer; auto-re-fetches `/api/hot` when it hits zero
- Manual refresh calls `/api/refresh` first, then re-fetches
- AI items get a purple left-border highlight and an "AI" badge

### External API dependency

The app depends on `uapis.cn/api/v1/misc/hotboard` for all three platforms. If this API goes down or changes shape, only Bilibili has a fallback. Weibo and Douyin would return empty lists.

### Screenshot reference

`screenshot-20260504-122637.png` (2352x1290) in the project root is the reference design for the frontend. The frontend should visually match this screenshot.
