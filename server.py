import json
import re
import time
from datetime import datetime, timezone, timedelta

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

# Beijing timezone
TZ = timezone(timedelta(hours=8))

AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "GPT", "ChatGPT", "LLM",
    "机器学习", "深度学习", "神经网络", "生成式", "AIGC",
    "OpenAI", "Claude", "DeepSeek", "文心", "通义", "智谱",
    "百川", "Kimi", "豆包", "Copilot", "Agent",
    "具身智能", "机器人", "自动驾驶", "元宝", "Gemini",
    "Grok", "智能", "模型", "提示词", "token",
    "强化学习", "扩散模型", "多模态", "RAG", "微调",
]

cache = {"data": None, "timestamp": 0}
CACHE_TTL = 300


def is_ai_related(title):
    t = title.lower()
    return any(kw.lower() in t for kw in AI_KEYWORDS)


def safe_fetch(url, label):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[{label}] fetch error: {e}")
        return None


def parse_items(raw_data, platform, max_items=30):
    if not raw_data:
        return []
    items = []
    data_list = raw_data.get("data", raw_data) if isinstance(raw_data, dict) else raw_data
    if isinstance(data_list, dict):
        data_list = data_list.get("list", data_list.get("items", []))
    if not isinstance(data_list, list):
        return []
    for i, item in enumerate(data_list[:max_items]):
        title = item.get("title", item.get("word", item.get("keyword", "")))
        if not title:
            continue
        hot = item.get("hot", item.get("hot_value", item.get("heat_score", "")))
        url = item.get("url", item.get("mobileUrl", item.get("link", "")))
        extra = item.get("extra") if isinstance(item.get("extra"), dict) else None
        owner = ""
        if extra and isinstance(extra.get("owner"), dict):
            owner = extra["owner"].get("name", "")
        items.append({
            "rank": len(items) + 1,
            "title": title,
            "hot_value": str(hot) if hot else "",
            "platform": platform,
            "is_ai": is_ai_related(title),
            "url": url,
            "owner": owner,
        })
    return items


def fetch_bilibili():
    raw = safe_fetch("https://uapis.cn/api/v1/misc/hotboard?type=bilibili", "bilibili")
    if not raw:
        # Fallback to B站 official hotword API
        raw = safe_fetch("https://s.search.bilibili.com/main/hotword", "bilibili-fallback")
        if raw:
            # Normalize B站 official format to match uapis format
            b_list = raw.get("list", [])
            raw = {"list": [
                {"index": i+1, "title": it.get("keyword", ""),
                 "hot_value": str(it.get("heat_score", "")),
                 "url": f"https://search.bilibili.com/all?keyword={it.get('keyword', '')}"}
                for i, it in enumerate(b_list)
            ]}
    return parse_items(raw, "bilibili")


def fetch_weibo():
    raw = safe_fetch("https://uapis.cn/api/v1/misc/hotboard?type=weibo", "weibo")
    return parse_items(raw, "weibo")


def fetch_douyin():
    raw = safe_fetch("https://uapis.cn/api/v1/misc/hotboard?type=douyin", "douyin")
    return parse_items(raw, "douyin")


def refresh_cache():
    global cache
    platforms = {
        "bilibili": fetch_bilibili(),
        "weibo": fetch_weibo(),
        "douyin": fetch_douyin(),
    }
    # Round-robin interleave: bilibili[0], weibo[0], douyin[0], bilibili[1], ...
    all_items = []
    lists = [platforms["bilibili"], platforms["weibo"], platforms["douyin"]]
    max_len = max(len(lst) for lst in lists)
    for i in range(max_len):
        for lst in lists:
            if i < len(lst):
                all_items.append(lst[i])

    cache["data"] = {
        "updated_at": datetime.now(TZ).isoformat(),
        "platforms": platforms,
        "all": all_items,
        "ai_count": sum(1 for it in all_items if it["is_ai"]),
        "total_count": len(all_items),
    }
    cache["timestamp"] = time.time()


@app.route("/api/hot")
def api_hot():
    ai_only = request.args.get("ai_only", "false").lower() == "true"
    if cache["data"] is None or (time.time() - cache["timestamp"]) > CACHE_TTL:
        refresh_cache()
    data = json.loads(json.dumps(cache["data"]))  # deep copy
    if ai_only:
        data["platforms"] = {
            k: [it for it in v if it["is_ai"]] for k, v in data["platforms"].items()
        }
        data["all"] = [it for it in data["all"] if it["is_ai"]]
    return jsonify(data)


@app.route("/api/refresh")
def api_refresh():
    refresh_cache()
    return jsonify({"ok": True, "updated_at": cache["data"]["updated_at"]})


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    PORT = 8765
    print(f"Tank - 热点关注面板 starting on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
