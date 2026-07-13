#!/usr/bin/env python3
"""Hermes x_search から、裏付けURLのあるAIニュース候補だけを取得する。"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


HERMES_ROOT = Path.home() / ".hermes" / "hermes-agent"
HERMES_PYTHON = HERMES_ROOT / "venv" / "bin" / "python3"
X_SEARCH_MODULE = HERMES_ROOT / "tools" / "x_search_tool.py"

OFFICIAL_HANDLES = [
    "OpenAI",
    "AnthropicAI",
    "GoogleAI",
    "GoogleDeepMind",
    "xai",
    "MetaAI",
    "MistralAI",
    "huggingface",
    "NVIDIAAI",
]

QUERY = """Find the newest important AI announcements from the allowed official X accounts.
Focus on model releases, product launches, APIs, pricing, research, regulation, partnerships,
acquisitions, and changes that affect companies or people using AI at work. Ignore replies,
memes, hiring posts, event promotion, and unrelated posts. Return at most 10 items as a JSON
array. Each item must have: url, handle, posted_at, title, summary. Use the real X post URL.
Do not invent a URL or announcement."""

X_STATUS_RE = re.compile(
    r"https://(?:www\.)?x\.com/([A-Za-z0-9_]{1,15})/status/(\d+)", re.I
)


class XWatchError(RuntimeError):
    """Hermes検索を安全に候補化できなかった。"""


def _clean_url(value: str) -> str | None:
    match = X_STATUS_RE.search(value or "")
    if not match:
        return None
    return f"https://x.com/{match.group(1)}/status/{match.group(2)}"


def _collect_citation_urls(payload: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for key in ("citations", "inline_citations"):
        values = payload.get(key) or []
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str):
                url = _clean_url(value)
                if url:
                    urls.add(url)
            elif isinstance(value, dict):
                for candidate in (value.get("url"), value.get("href"), value.get("citation")):
                    if isinstance(candidate, str):
                        url = _clean_url(candidate)
                        if url:
                            urls.add(url)
    return urls


def _parse_answer_items(answer: str) -> list[dict[str, Any]]:
    text = (answer or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


def parse_hermes_result(raw: str) -> list[dict[str, Any]]:
    """Hermes応答をキュー形式に変換する。引用URLがない応答は採用しない。"""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise XWatchError("Hermesの応答がJSONではありません") from exc

    if not payload.get("success"):
        raise XWatchError(str(payload.get("error") or "Hermes x_search が失敗しました"))
    if payload.get("degraded"):
        reason = payload.get("degraded_reason") or "検索結果の裏付けがありません"
        raise XWatchError(f"Hermes検索を採用しません: {reason}")

    citation_urls = _collect_citation_urls(payload)
    citation_ids = {
        match.group(2)
        for url in citation_urls
        if (match := X_STATUS_RE.match(url)) is not None
    }
    if not citation_ids:
        raise XWatchError("Hermes検索に元ポストの引用URLがないため採用しません")

    answer_items = _parse_answer_items(str(payload.get("answer") or ""))
    details_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    for item in answer_items:
        url = _clean_url(str(item.get("url") or ""))
        match = X_STATUS_RE.match(url or "")
        if match:
            details_by_id[match.group(2)] = (url, item)

    items: list[dict[str, Any]] = []
    official_handles = {handle.lower() for handle in OFFICIAL_HANDLES}
    for status_id in sorted(citation_ids):
        # xAIの引用URLは /i/status/<id> になることがあるため、回答JSONの
        # 同じ投稿IDから本来の公式ハンドルを復元する。
        detail_entry = details_by_id.get(status_id)
        if not detail_entry:
            continue
        url, detail = detail_entry
        match = X_STATUS_RE.match(url)
        if not match:
            continue
        handle = match.group(1)
        if handle.lower() not in official_handles:
            continue
        title = str(detail.get("title") or detail.get("summary") or f"@{handle}のAI公式発表")
        summary = str(detail.get("summary") or title)
        posted_at = detail.get("posted_at") or detail.get("published") or None
        items.append(
            {
                "source": f"X @{handle}",
                "source_type": "x",
                "title": title.strip()[:240],
                "url": url,
                "published": posted_at,
                "summary": summary.strip()[:400],
                "weight": 5,
                "official": True,
                "verification_required": True,
            }
        )
    return items


def fetch_x_items(days: int = 1) -> list[dict[str, Any]]:
    if not HERMES_PYTHON.exists() or not X_SEARCH_MODULE.exists():
        raise XWatchError("Hermes x_search が見つかりません")

    today_utc = datetime.now(timezone.utc).date()
    from_date = (today_utc - timedelta(days=max(days, 1))).isoformat()
    to_date = today_utc.isoformat()
    invocation = (
        "from tools.x_search_tool import x_search_tool; "
        "print(x_search_tool("
        f"query={QUERY!r}, "
        f"allowed_x_handles={OFFICIAL_HANDLES!r}, "
        f"from_date={from_date!r}, to_date={to_date!r}))"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(HERMES_ROOT)
    try:
        result = subprocess.run(
            [str(HERMES_PYTHON), "-c", invocation],
            cwd=str(HERMES_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise XWatchError("Hermes x_search が時間切れになりました") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Hermesの実行に失敗しました").strip()
        raise XWatchError(message[:500])
    return parse_hermes_result(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="HermesからAI深報のX候補を取得")
    parser.add_argument("--days", type=int, default=1, help="検索対象の日数")
    args = parser.parse_args()
    try:
        items = fetch_x_items(days=args.days)
    except XWatchError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps({"success": True, "items": items}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
