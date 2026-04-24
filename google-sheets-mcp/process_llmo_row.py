#!/usr/bin/env python3
"""Safely process one LLMO keyword row in a Google Sheet.

This avoids lossy parsing of newline-containing cells by using the Sheets API
directly for both reads and writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_SPREADSHEET_ID = "1KRRjhwlpnzx1my8RGJZPLvcrIV6wZQmk8I4Qagtd4qM"
DEFAULT_SHEET_NAME = "keywords"
DEFAULT_SHEET_ID = 0


@dataclass
class RowData:
    row_number: int
    keyword: str
    target_length: str
    status: str
    created_at: str
    title_text: str
    outline_text: str


def load_credentials(creds_path: str | None) -> Credentials:
    if creds_path:
        return Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        return Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)

    raise SystemExit(
        "Missing credentials. Pass --creds-file or set GOOGLE_CREDENTIALS_JSON."
    )


def build_service(creds_path: str | None):
    creds = load_credentials(creds_path)
    return build("sheets", "v4", credentials=creds)


def get_sheet_metadata(service, spreadsheet_id: str) -> dict[str, Any]:
    return service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()


def read_rows(service, spreadsheet_id: str, sheet_name: str, cell_range: str) -> list[list[str]]:
    return (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{cell_range}")
        .execute()
        .get("values", [])
    )


def get_row(service, spreadsheet_id: str, sheet_name: str, row_number: int) -> RowData:
    values = read_rows(service, spreadsheet_id, sheet_name, f"A{row_number}:F{row_number}")
    row = values[0] if values else []
    padded = row + [""] * (6 - len(row))
    return RowData(
        row_number=row_number,
        keyword=padded[0],
        target_length=padded[1],
        status=padded[2],
        created_at=padded[3],
        title_text=padded[4],
        outline_text=padded[5],
    )


def find_first_eligible_row(rows: list[list[str]]) -> RowData | None:
    for index, row in enumerate(rows[1:], start=2):
        padded = row + [""] * (6 - len(row))
        candidate = RowData(
            row_number=index,
            keyword=padded[0],
            target_length=padded[1],
            status=padded[2],
            created_at=padded[3],
            title_text=padded[4],
            outline_text=padded[5],
        )
        if (
            candidate.keyword
            and candidate.status in ("", "未処理")
            and candidate.title_text == ""
            and candidate.outline_text == ""
        ):
            return candidate
    return None


def verify_target_row(row: RowData) -> None:
    if not row.keyword:
        raise SystemExit(f"Row {row.row_number} has no keyword.")
    if row.status not in ("", "未処理"):
        raise SystemExit(
            f"Row {row.row_number} is no longer eligible: status={row.status!r}."
        )
    if row.title_text or row.outline_text:
        raise SystemExit(
            f"Row {row.row_number} is no longer eligible: E/F already populated."
        )


def batch_update(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    row_number: int,
    title_text: str,
    outline_text: str,
    processed_status: str,
) -> dict[str, Any]:
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"{sheet_name}!E{row_number}:F{row_number}", "values": [[title_text, outline_text]]},
            {"range": f"{sheet_name}!C{row_number}", "values": [[processed_status]]},
        ],
    }
    return (
        service.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
        .execute()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME)
    parser.add_argument("--expected-sheet-id", type=int, default=DEFAULT_SHEET_ID)
    parser.add_argument("--creds-file", default=None)
    parser.add_argument("--titles-file", required=True)
    parser.add_argument("--outline-file", required=True)
    parser.add_argument("--processed-status", default="処理済み")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = build_service(args.creds_file)
    metadata = get_sheet_metadata(service, args.spreadsheet_id)

    target_sheet = None
    for sheet in metadata.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == args.sheet_name:
            target_sheet = props
            break

    if not target_sheet:
        raise SystemExit(f"Sheet {args.sheet_name!r} not found.")
    if target_sheet.get("sheetId") != args.expected_sheet_id:
        raise SystemExit(
            f"Unexpected sheetId for {args.sheet_name!r}: {target_sheet.get('sheetId')}"
        )

    rows = read_rows(service, args.spreadsheet_id, args.sheet_name, "A1:F200")
    target = find_first_eligible_row(rows)
    if not target:
        print(json.dumps({"ok": False, "reason": "no_eligible_row"}, ensure_ascii=False))
        return

    fresh = get_row(service, args.spreadsheet_id, args.sheet_name, target.row_number)
    verify_target_row(fresh)

    title_text = Path(args.titles_file).read_text().strip()
    outline_text = Path(args.outline_file).read_text().strip()

    result: dict[str, Any] = {
        "ok": True,
        "spreadsheet_title": metadata.get("properties", {}).get("title"),
        "sheet_name": args.sheet_name,
        "sheet_id": target_sheet.get("sheetId"),
        "target_row": fresh.row_number,
        "keyword": fresh.keyword,
        "target_length": fresh.target_length,
    }

    if args.dry_run:
        result["dry_run"] = True
        print(json.dumps(result, ensure_ascii=False))
        return

    write_result = batch_update(
        service,
        args.spreadsheet_id,
        args.sheet_name,
        fresh.row_number,
        title_text,
        outline_text,
        args.processed_status,
    )
    after = get_row(service, args.spreadsheet_id, args.sheet_name, fresh.row_number)
    result["write_result"] = write_result
    result["after"] = {
        "status": after.status,
        "title_filled": bool(after.title_text),
        "outline_filled": bool(after.outline_text),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
