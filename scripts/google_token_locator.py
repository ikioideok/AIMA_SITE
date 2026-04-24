#!/usr/bin/env python3
"""Print the canonical Google OAuth token locations for this workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TOKEN_MAP = {
    "analytics-read": {
        "purpose": "Google Analytics 4 read access used by local reporting scripts",
        "path": ROOT / ".tokens/google-readonly-combined-token.json",
        "expected_scopes": [
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    },
    "sheets-write": {
        "purpose": (
            "Google Sheets write access for values.update and batchUpdate "
            "including addSheet"
        ),
        "path": Path("/Users/mizumayuuki/Downloads/llmo_diagnoser/data/google-oauth-token.json"),
        "expected_scopes": [
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    },
    "docs-read": {
        "purpose": "Google Docs plus Drive read-only access used by local docs MCP tooling",
        "path": Path("/Users/mizumayuuki/.codex/tools/google-docs-mcp/token.json"),
        "expected_scopes": [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ],
    },
    "search-console": {
        "purpose": "Search Console API token cache used by local reporting scripts",
        "path": ROOT / ".tokens/search-console-token.json",
        "expected_scopes": [
            "https://www.googleapis.com/auth/webmasters.readonly",
        ],
    },
    "search-analytics-combined": {
        "purpose": "Combined Search Console + GA4 read-only token used by local reporting scripts",
        "path": ROOT / ".tokens/google-readonly-combined-token.json",
        "expected_scopes": [
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    },
}


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def normalize_scopes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [part for part in value.split() if part]
    return []


def build_entry(name: str) -> dict[str, Any]:
    config = TOKEN_MAP[name]
    path = Path(config["path"]).expanduser()
    payload = read_json(path)
    scopes: list[str] = []
    if payload:
        scopes = normalize_scopes(payload.get("scopes") or payload.get("scope"))
    return {
        "name": name,
        "purpose": config["purpose"],
        "path": str(path),
        "exists": path.exists(),
        "expected_scopes": list(config["expected_scopes"]),
        "actual_scopes": scopes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show the canonical Google OAuth token files for this workspace."
    )
    parser.add_argument(
        "--purpose",
        choices=sorted(TOKEN_MAP.keys()),
        help="Show only one canonical token entry.",
    )
    parser.add_argument(
        "--path-only",
        action="store_true",
        help="Print only the resolved token path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of plain text.",
    )
    args = parser.parse_args()

    names = [args.purpose] if args.purpose else sorted(TOKEN_MAP.keys())
    entries = [build_entry(name) for name in names]

    if args.path_only:
        for entry in entries:
            print(entry["path"])
        return 0

    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0

    for entry in entries:
        print(f"[{entry['name']}]")
        print(f"purpose: {entry['purpose']}")
        print(f"path: {entry['path']}")
        print(f"exists: {'yes' if entry['exists'] else 'no'}")
        print("expected_scopes:")
        for scope in entry["expected_scopes"]:
            print(f"  - {scope}")
        print("actual_scopes:")
        if entry["actual_scopes"]:
            for scope in entry["actual_scopes"]:
                print(f"  - {scope}")
        else:
            print("  - (unavailable)")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
