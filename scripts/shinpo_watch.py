#!/usr/bin/env python3
"""AI深報 情報収集スクリプト。

公式ブログRSS・Hacker News・Reddit・Hermes X検索から新着を収集し、
重要度スコア順に並べて data/shinpo_queue.json に書き出す。
候補は7日間キューに保持し、下書き化・却下・公開の状態を管理する。

使い方:
  python3 scripts/shinpo_watch.py            # 新着を収集して表示
  python3 scripts/shinpo_watch.py --all      # 既読も含めて表示（デバッグ用）
  python3 scripts/shinpo_watch.py --skip-x   # RSS等だけを収集
  python3 scripts/shinpo_watch.py --x-only   # Hermes X検索だけを実行

外部ライブラリ不要（標準ライブラリのみ）。
フィードの追加・削除はこのファイル冒頭の FEEDS を編集する。
"""

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from shinpo_x_watch import XWatchError, fetch_x_items

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEEN_PATH = DATA_DIR / "shinpo_seen.json"
QUEUE_PATH = DATA_DIR / "shinpo_queue.json"

UA = "Mozilla/5.0 (compatible; AIShinpoWatch/0.1; +https://ai-and-marketing.jp)"
TIMEOUT = 12

# (名前, URL, ソース重み) — 重みが高いほど一次情報として重要
FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml", 5),
    ("Google AI", "https://blog.google/technology/ai/rss/", 5),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", 4),
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml", 3),
    ("Publickey", "https://www.publickey1.jp/atom.xml", 3),
]

REDDIT_SUBS = [
    ("r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/hot.json?limit=25", 2),
    ("r/MachineLearning", "https://www.reddit.com/r/MachineLearning/hot.json?limit=25", 2),
]

HN_URL = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30"

# AI関連判定キーワード（HN・Publickeyなど総合系フィードの絞り込みに使用）
AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic", "deepmind",
    "llama", "mistral", "grok", "xai", "copilot", "chatgpt", "生成ai", "人工知能",
    "機械学習", "machine learning", "deep learning", "transformer", "diffusion",
    "agent", "エージェント", "rag", "fine-tun", "sota", "benchmark", "nvidia",
    "hugging face", "perplexity", "sora", "notebooklm", "cursor",
]

# 重要度加点キーワード（発表・リリース系）
HOT_KEYWORDS = [
    "発表", "リリース", "公開", "提供開始", "買収", "提携", "資金調達", "値下げ",
    "無料", "オープンソース", "open source", "open-source", "release", "launch",
    "announc", "introduc", "acqui", "funding", "raises", "available", "ga ",
    "preview", "new model", "新モデル", "api",
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return res.read()


def text_of(el, *names):
    """名前空間の揺れを吸収して最初に見つかった子要素のテキストを返す。"""
    if el is None:
        return ""
    for child in el.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and (child.text or "").strip():
            return child.text.strip()
    return ""


def parse_feed(name, raw, weight):
    """RSS2.0 / Atom の両対応で (title, url, published, summary) を返す。"""
    items = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return items

    # RSS 2.0
    for item in root.iter():
        tag = item.tag.rsplit("}", 1)[-1].lower()
        if tag not in ("item", "entry"):
            continue
        title = text_of(item, "title")
        summary = text_of(item, "description", "summary")
        url = ""
        published = None

        for child in item:
            ctag = child.tag.rsplit("}", 1)[-1].lower()
            if ctag == "link":
                url = (child.text or "").strip() or child.attrib.get("href", "")
                if child.attrib.get("rel") == "alternate":
                    url = child.attrib.get("href", url)
            elif ctag in ("pubdate", "published", "updated", "date"):
                published = parse_date((child.text or "").strip())

        if title and url:
            items.append({
                "source": name,
                "title": title,
                "url": url,
                "published": published.isoformat() if published else None,
                "summary": re.sub(r"<[^>]+>", "", summary)[:200],
                "weight": weight,
            })
    return items


def parse_date(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:25] if "Z" not in s else s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def fetch_hn():
    items = []
    try:
        data = json.loads(fetch(HN_URL))
    except Exception as e:
        print(f"  ! Hacker News 取得失敗: {e}", file=sys.stderr)
        return items
    for hit in data.get("hits", []):
        title = hit.get("title") or ""
        if not is_ai_related(title):
            continue
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        items.append({
            "source": "Hacker News",
            "title": title,
            "url": url,
            "published": hit.get("created_at"),
            "summary": f"{hit.get('points', 0)} points / {hit.get('num_comments', 0)} comments",
            "weight": 3,
        })
    return items


def fetch_reddit():
    items = []
    for name, url, weight in REDDIT_SUBS:
        try:
            data = json.loads(fetch(url))
        except Exception as e:
            print(f"  ! {name} 取得失敗: {e}", file=sys.stderr)
            continue
        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})
            if d.get("stickied") or d.get("score", 0) < 200:
                continue
            created = datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc)
            items.append({
                "source": name,
                "title": d.get("title", ""),
                "url": "https://www.reddit.com" + d.get("permalink", ""),
                "published": created.isoformat(),
                "summary": f"{d.get('score', 0)} upvotes",
                "weight": weight,
            })
    return items


def is_ai_related(text):
    t = text.lower()
    for keyword in AI_KEYWORDS:
        # "ai" を単純な部分一致にすると snails / said / mail まで拾う。
        if keyword == "ai":
            if re.search(r"(?<![a-z0-9])ai(?![a-z0-9])", t):
                return True
            continue
        if keyword in t:
            return True
    return False


def score(item):
    s = item["weight"] * 2
    t = (item["title"] + " " + item.get("summary", "")).lower()
    s += min(sum(2 for k in HOT_KEYWORDS if k in t), 6)
    published = parse_date(item.get("published") or "")
    if published:
        age_h = (datetime.now(timezone.utc) - published).total_seconds() / 3600
        if age_h < 2:
            s += 4
        elif age_h < 6:
            s += 2
        elif age_h > 48:
            s -= 4
    return s


def main():
    show_all = "--all" in sys.argv
    skip_x = "--skip-x" in sys.argv
    x_only = "--x-only" in sys.argv
    DATA_DIR.mkdir(exist_ok=True)
    seen = set()
    if SEEN_PATH.exists():
        seen = set(json.loads(SEEN_PATH.read_text()))

    existing_items = []
    if QUEUE_PATH.exists():
        try:
            existing_items = json.loads(QUEUE_PATH.read_text()).get("items", [])
        except (json.JSONDecodeError, AttributeError):
            existing_items = []

    collected = []
    print("収集中…", file=sys.stderr)
    if not x_only:
        for name, url, weight in FEEDS:
            try:
                raw = fetch(url)
                got = parse_feed(name, raw, weight)
                # 総合系フィードはAIキーワードで絞る
                if name in ("Publickey",):
                    got = [i for i in got if is_ai_related(i["title"])]
                collected += got
                print(f"  ✓ {name}: {len(got)}件", file=sys.stderr)
            except Exception as e:
                print(f"  ! {name} 取得失敗: {e}", file=sys.stderr)
        collected += fetch_hn()
        collected += fetch_reddit()

    if not skip_x:
        try:
            x_items = fetch_x_items()
            collected += x_items
            print(f"  ✓ Hermes X: {len(x_items)}件", file=sys.stderr)
        except XWatchError as e:
            # X側が不調でもRSS収集は止めない。裏付けのないX結果も採用しない。
            print(f"  ! Hermes X 採用見送り: {e}", file=sys.stderr)

    # 7日以内の候補を、既存ステータスを保ったままキューへマージする。
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    def is_recent(item):
        published = parse_date(item.get("published") or item.get("first_seen_at") or "")
        return published is None or (now - published).days < 7

    existing_by_url = {
        item.get("url"): item
        for item in existing_items
        if item.get("url")
        and not (item.get("source_type") == "x" and not item.get("official"))
        and not (
            item.get("source") == "Hacker News"
            and not is_ai_related(item.get("title", ""))
        )
    }
    merged_by_url = {
        url: item
        for url, item in existing_by_url.items()
        if item.get("status", "new") in ("new", "drafted") and is_recent(item)
    }
    new_urls = set()
    for item in collected:
        url = item.get("url")
        if not url or not is_recent(item):
            continue
        previous = existing_by_url.get(url)
        if previous and previous.get("status", "new") in ("dismissed", "published"):
            continue
        if previous:
            status_fields = {
                key: previous[key]
                for key in ("status", "first_seen_at", "status_updated_at", "draft_path")
                if key in previous
            }
            previous.update(item)
            previous.update(status_fields)
            previous["score"] = score(previous)
            merged_by_url[url] = previous
            continue
        if not show_all and url in seen:
            continue
        item["score"] = score(item)
        item["status"] = "new"
        item["first_seen_at"] = now_iso
        merged_by_url[url] = item
        new_urls.add(url)

    queue_items = list(merged_by_url.values())
    queue_items.sort(
        key=lambda item: (
            item.get("status", "new") == "new",
            item.get("score", 0),
            item.get("published") or item.get("first_seen_at") or "",
        ),
        reverse=True,
    )

    # 既読に記録（今回収集した全URL）
    seen |= {i["url"] for i in collected if i.get("url")}
    SEEN_PATH.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=1) + "\n")

    QUEUE_PATH.write_text(json.dumps({
        "generated_at": now_iso,
        "new_count": len(new_urls),
        "items": queue_items,
    }, ensure_ascii=False, indent=2) + "\n")

    if not new_urls:
        pending = sum(i.get("status", "new") == "new" for i in queue_items)
        print(f"新着なし。未処理候補は{pending}件。")
        return
    fresh = [i for i in queue_items if i.get("url") in new_urls]
    print(f"\n新着 {len(fresh)}件（スコア順）→ {QUEUE_PATH.relative_to(ROOT)}\n")
    for i in fresh[:20]:
        pub = (i.get("published") or "")[:16].replace("T", " ")
        print(f"[{i['score']:>2}] {i['source']:<16} {pub}  {i['title'][:70]}")
        print(f"     {i['url']}")


if __name__ == "__main__":
    main()
