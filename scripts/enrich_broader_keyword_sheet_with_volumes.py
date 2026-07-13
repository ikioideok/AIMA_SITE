#!/usr/bin/env python3
"""Add estimated search volumes to the broader AIMA keyword Google Sheet."""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SPREADSHEET_ID = "19aR_MmRWroBievv5hfsUmu_3tZBDhZ7NnLCNuBfFoBA"
SHEET_NAME = "キーワード一覧"
SOURCE_SHEET_NAME = "取得元データ"
TOKEN_FILE = Path("/Users/mizumayuuki/Downloads/llmo_diagnoser/data/google-oauth-token.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
REPO = Path("/Users/mizumayuuki/Downloads/aima_co")
CACHE_FILE = REPO / "output" / "keyword-volume-suggest-cache-2026-05-15.json"

SEEDS = [
    "LLMO",
    "AI検索",
    "AI検索対策",
    "AI検索最適化",
    "生成AI検索",
    "AI Overview",
    "AIO対策",
    "GEO対策",
    "AEO対策",
    "SEO対策",
    "SEOコンサル",
    "SEO記事制作",
    "コンテンツマーケティング",
    "オウンドメディア",
    "BtoBマーケティング",
    "BtoB SEO",
    "リード獲得",
    "ホワイトペーパー",
    "Webサイト 問い合わせ",
    "ホームページ 集客",
    "サービスサイト 改善",
    "中小企業 AI活用",
    "生成AI マーケティング",
    "ChatGPT 導入支援",
    "製造業 SEO",
    "SaaS SEO",
    "サイテーション SEO",
    "指名検索",
    "GA4 分析",
    "Search Console 分析",
]


def load_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise SystemExit("Sheets token is not valid and cannot be refreshed.")
    return build("sheets", "v4", credentials=creds)


def normalize(text: str) -> str:
    value = text.lower().strip()
    value = value.replace("　", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def compact(text: str) -> str:
    return normalize(text).replace(" ", "")


def volume_band(volume: int | None) -> str:
    if volume is None:
        return "未取得"
    if volume >= 10000:
        return "1万以上"
    if volume >= 1000:
        return "1000-9999"
    if volume >= 100:
        return "100-999"
    if volume >= 10:
        return "10-99"
    return "10未満"


def fetch_keyword_suggestions(seed: str) -> dict[str, Any]:
    payload = json.dumps(
        {"keyword": seed, "language_code": "ja", "location_code": 2392}
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://keywordsuggest.net/api/suggest",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, context=context, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def read_keywords(service) -> list[list[str]]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A4:K500")
        .execute()
    )
    return result.get("values", [])


def load_or_fetch_suggestions() -> dict[str, Any]:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    else:
        cache = {"fetched_at": None, "seeds": {}}

    for seed in SEEDS:
        if seed in cache.get("seeds", {}):
            continue
        print(f"fetch: {seed}")
        try:
            cache["seeds"][seed] = fetch_keyword_suggestions(seed)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            cache["seeds"][seed] = {"error": f"HTTP {exc.code}", "body": body}
            if exc.code == 429:
                print("rate limit reached; stopping fetch")
                break
        except Exception as exc:  # noqa: BLE001
            cache["seeds"][seed] = {"error": str(exc)}
        cache["fetched_at"] = datetime.now().isoformat(timespec="seconds")
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(1.1)

    return cache


def build_lookup(cache: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    lookup: dict[str, dict[str, Any]] = {}
    raw: list[dict[str, Any]] = []

    def put(key: str, item: dict[str, Any]) -> None:
        current = lookup.get(key)
        if current is None or (item.get("search_volume") or 0) > (
            current.get("search_volume") or 0
        ):
            lookup[key] = item

    for seed, data in cache.get("seeds", {}).items():
        for item in data.get("suggestions", []) or []:
            record = {
                "seed": seed,
                "keyword": item.get("keyword", ""),
                "search_volume": item.get("search_volume"),
                "cpc": item.get("cpc"),
                "competition": item.get("competition"),
            }
            raw.append(record)
            keyword = record["keyword"]
            put(normalize(keyword), record)
            put(compact(keyword), record)

    return lookup, raw


def find_best(keyword: str, lookup: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    exact = lookup.get(normalize(keyword))
    if exact:
        return exact, "完全一致"
    variant = lookup.get(compact(keyword))
    if variant:
        return variant, "表記ゆれ一致"

    target = compact(keyword)
    best: dict[str, Any] | None = None
    best_score = 0.0
    for item in lookup.values():
        candidate = compact(item.get("keyword", ""))
        if not candidate:
            continue
        score = SequenceMatcher(None, target, candidate).ratio()
        if candidate in target or target in candidate:
            score += 0.12
        if score > best_score:
            best_score = score
            best = item

    if best and best_score >= 0.74:
        return best, "近い語"
    return None, "未取得"


def update_keyword_sheet(service, values: list[list[str]], lookup: dict[str, dict[str, Any]]) -> dict[str, int]:
    rows = values[1:]
    output = [
        [
            "月間検索Vol（推定）",
            "CPC（推定）",
            "広告競合性",
            "取得方法",
            "一致キーワード",
            "ボリューム帯",
            "取得メモ",
        ]
    ]

    counts = {"exact": 0, "variant": 0, "near": 0, "missing": 0}
    for row in rows:
        keyword = row[4] if len(row) > 4 else ""
        match, method = find_best(keyword, lookup)
        if match:
            volume = match.get("search_volume")
            cpc = match.get("cpc")
            competition = match.get("competition")
            matched_keyword = match.get("keyword", "")
            seed = match.get("seed", "")
            note = f"KeywordSuggest / seed: {seed}"
            if method == "完全一致":
                counts["exact"] += 1
            elif method == "表記ゆれ一致":
                counts["variant"] += 1
            else:
                counts["near"] += 1
                note += " / 正確な語ではなく近い語"
            output.append(
                [
                    volume if volume is not None else "",
                    cpc if cpc is not None else "",
                    competition if competition is not None else "",
                    method,
                    matched_keyword,
                    volume_band(volume),
                    note,
                ]
            )
        else:
            counts["missing"] += 1
            output.append(["", "", "", "未取得", "", "未取得", "無料取得元で該当なし。低ボリュームまたは表現違いの可能性"])

    end_row = 4 + len(output) - 1
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!L4:R{end_row}",
            valueInputOption="USER_ENTERED",
            body={"values": output},
        )
        .execute()
    )
    return counts


def ensure_source_sheet(service) -> int:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in meta.get("sheets", []):
        props = sheet["properties"]
        if props["title"] == SOURCE_SHEET_NAME:
            return props["sheetId"]

    response = (
        service.spreadsheets()
        .batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": SOURCE_SHEET_NAME}}}]},
        )
        .execute()
    )
    return response["replies"][0]["addSheet"]["properties"]["sheetId"]


def update_source_sheet(service, raw: list[dict[str, Any]]) -> None:
    ensure_source_sheet(service)
    rows = [["seed", "keyword", "search_volume", "cpc", "competition"]]
    dedup = {}
    for item in raw:
        key = (item["seed"], item["keyword"])
        dedup[key] = item
    for item in sorted(dedup.values(), key=lambda x: (x["seed"], -(x.get("search_volume") or 0), x["keyword"])):
        rows.append([
            item.get("seed", ""),
            item.get("keyword", ""),
            item.get("search_volume", ""),
            item.get("cpc", ""),
            item.get("competition", ""),
        ])
    (
        service.spreadsheets()
        .values()
        .clear(spreadsheetId=SPREADSHEET_ID, range=f"{SOURCE_SHEET_NAME}!A:E")
        .execute()
    )
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SOURCE_SHEET_NAME}!A1:E{len(rows)}",
            valueInputOption="USER_ENTERED",
            body={"values": rows},
        )
        .execute()
    )


def format_sheet(service, keyword_row_count: int, source_sheet_id: int) -> None:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    keyword_sheet_id = next(
        sheet["properties"]["sheetId"]
        for sheet in meta.get("sheets", [])
        if sheet["properties"]["title"] == SHEET_NAME
    )
    requests: list[dict[str, Any]] = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": keyword_sheet_id,
                    "startRowIndex": 3,
                    "endRowIndex": 4,
                    "startColumnIndex": 11,
                    "endColumnIndex": 18,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": keyword_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 11,
                    "endIndex": 18,
                },
                "properties": {"pixelSize": 150},
                "fields": "pixelSize",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": keyword_sheet_id,
                    "startRowIndex": 4,
                    "endRowIndex": keyword_row_count + 4,
                    "startColumnIndex": 11,
                    "endColumnIndex": 14,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "#,##0.##"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 5,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.12, "green": 0.16, "blue": 0.23},
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
    ]
    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()


def main() -> None:
    service = load_service()
    values = read_keywords(service)
    if not values or values[0][4] != "キーワード":
        raise SystemExit("Could not read keyword sheet headers.")

    cache = load_or_fetch_suggestions()
    lookup, raw = build_lookup(cache)
    counts = update_keyword_sheet(service, values, lookup)
    update_source_sheet(service, raw)
    source_sheet_id = ensure_source_sheet(service)
    format_sheet(service, len(values) - 1, source_sheet_id)

    summary = {
        "spreadsheet_id": SPREADSHEET_ID,
        "keyword_rows": len(values) - 1,
        "source_suggestions": len(raw),
        "counts": counts,
        "cache_file": str(CACHE_FILE),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
