#!/usr/bin/env python3
"""AI深報の候補キューを一覧・状態更新する小さな管理ツール。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "data" / "shinpo_queue.json"
STATUSES = {"new", "drafted", "dismissed", "published"}


def load_queue() -> dict[str, Any]:
    if not QUEUE_PATH.exists():
        return {"generated_at": None, "items": []}
    return json.loads(QUEUE_PATH.read_text())


def save_queue(data: dict[str, Any]) -> None:
    QUEUE_PATH.parent.mkdir(exist_ok=True)
    tmp = QUEUE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(QUEUE_PATH)


def mark_by_url(url: str, status: str, draft_path: str | None = None) -> bool:
    if status not in STATUSES:
        raise ValueError(f"不正な状態です: {status}")
    data = load_queue()
    for item in data.get("items", []):
        if item.get("url") != url:
            continue
        item["status"] = status
        item["status_updated_at"] = datetime.now(timezone.utc).isoformat()
        if draft_path:
            item["draft_path"] = draft_path
        save_queue(data)
        return True
    return False


def list_items(status: str | None, limit: int) -> list[dict[str, Any]]:
    items = load_queue().get("items", [])
    if status:
        items = [item for item in items if item.get("status", "new") == status]
    return items[: max(limit, 0)]


def main() -> None:
    parser = argparse.ArgumentParser(description="AI深報ニュースキュー管理")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="候補を表示")
    list_parser.add_argument("--status", choices=sorted(STATUSES))
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")

    mark_parser = sub.add_parser("mark", help="候補の状態を変更")
    mark_parser.add_argument("url")
    mark_parser.add_argument("status", choices=sorted(STATUSES))
    mark_parser.add_argument("--draft-path")

    args = parser.parse_args()
    if args.command == "list":
        items = list_items(args.status, args.limit)
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
            return
        for index, item in enumerate(items, 1):
            print(
                f"{index:>2}. [{item.get('score', 0):>2}] "
                f"{item.get('status', 'new'):<9} {item.get('source', '')} "
                f"{item.get('title', '')}"
            )
            print(f"    {item.get('url', '')}")
        return

    changed = mark_by_url(args.url, args.status, args.draft_path)
    if not changed:
        print("指定URLはキューにありません", file=sys.stderr)
        sys.exit(1)
    print(f"更新: {args.status} {args.url}")


if __name__ == "__main__":
    main()
