#!/usr/bin/env python3
"""Query Google Analytics 4 via the Admin and Data API REST endpoints."""

from __future__ import annotations

import argparse
import csv
import json
import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, List, Optional

warnings.filterwarnings(
    "ignore",
    message=r"urllib3 v2 only supports OpenSSL 1\.1\.1\+.*",
)

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials

DEFAULT_TOKEN_FILE = ".tokens/google-readonly-combined-token.json"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
STRING_MATCH_TYPES = {
    "exact": "EXACT",
    "contains": "CONTAINS",
    "beginswith": "BEGINS_WITH",
    "endswith": "ENDS_WITH",
    "fullregexp": "FULL_REGEXP",
    "partialregexp": "PARTIAL_REGEXP",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query GA4 with the Analytics Admin API and Analytics Data API. "
            "Uses an OAuth token file with analytics.readonly."
        )
    )
    parser.add_argument(
        "--list-properties",
        action="store_true",
        help="List visible GA4 properties via the Admin API.",
    )
    parser.add_argument(
        "--property-id",
        help="GA4 property ID, for example 523694776.",
    )
    parser.add_argument("--start-date", help="Start date in YYYY-MM-DD.")
    parser.add_argument("--end-date", help="End date in YYYY-MM-DD.")
    parser.add_argument(
        "--last-days",
        type=int,
        default=28,
        help=(
            "If explicit dates are omitted, fetch this many days ending "
            "'--end-days-ago' days before today. Default: 28."
        ),
    )
    parser.add_argument(
        "--end-days-ago",
        type=int,
        default=1,
        help=(
            "If explicit dates are omitted, end the range this many days before today. "
            "Default: 1."
        ),
    )
    parser.add_argument(
        "--dimensions",
        default="sessionSource",
        help="Comma-separated GA4 dimensions. Default: sessionSource.",
    )
    parser.add_argument(
        "--metrics",
        default="sessions",
        help="Comma-separated GA4 metrics. Default: sessions.",
    )
    parser.add_argument(
        "--filter",
        nargs=3,
        action="append",
        metavar=("FIELD", "OPERATOR", "VALUE"),
        help=(
            "Add a string filter. Example: "
            "--filter sessionSource exact chatgpt.com "
            "--filter pagePath contains /blog/"
        ),
    )
    parser.add_argument(
        "--order-by",
        help=(
            "Field name to sort by. Use a dimension or metric name already present "
            "in --dimensions or --metrics."
        ),
    )
    parser.add_argument(
        "--desc",
        action="store_true",
        help="Sort in descending order when --order-by is set.",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        default=100,
        help="Rows to fetch. Valid range is 1-250000. Default: 100.",
    )
    parser.add_argument(
        "--token-file",
        default=DEFAULT_TOKEN_FILE,
        help=f"Authorized user token JSON. Default: {DEFAULT_TOKEN_FILE}",
    )
    parser.add_argument(
        "--output-format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format. Default: table.",
    )
    parser.add_argument(
        "--output",
        help="Optional output file path. If omitted, prints to stdout.",
    )

    args = parser.parse_args()
    validate_args(args)
    return args


def validate_args(args: argparse.Namespace) -> None:
    if not args.list_properties and not args.property_id:
        raise SystemExit("--property-id is required unless --list-properties is used.")
    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        raise SystemExit("--start-date and --end-date must be provided together.")
    if args.last_days < 1:
        raise SystemExit("--last-days must be 1 or greater.")
    if args.end_days_ago < 0:
        raise SystemExit("--end-days-ago must be 0 or greater.")
    if args.row_limit < 1 or args.row_limit > 250000:
        raise SystemExit("--row-limit must be between 1 and 250000.")


def load_credentials(token_file: str) -> Credentials:
    token_path = Path(token_file)
    if not token_path.exists():
        raise SystemExit(
            f"Token file not found: {token_path}. "
            "Use docs/google-api-auth.md to find the canonical GA4 token path."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    raise SystemExit(
        f"Token file exists but cannot be refreshed: {token_path}. "
        "Re-authorize the account before retrying."
    )


def resolve_date_range(args: argparse.Namespace) -> tuple[str, str]:
    if args.start_date and args.end_date:
        return args.start_date, args.end_date

    end_date = date.today() - timedelta(days=args.end_days_ago)
    start_date = end_date - timedelta(days=args.last_days - 1)
    return start_date.isoformat(), end_date.isoformat()


def emit_output(content: str, output_path: Optional[str]) -> None:
    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"Wrote {target}")
        return
    print(content)


def format_table(records: List[dict[str, Any]]) -> str:
    if not records:
        return "No rows returned."

    headers = list(records[0].keys())
    widths = {header: len(header) for header in headers}
    rendered_rows: list[list[str]] = []

    for record in records:
        row: list[str] = []
        for header in headers:
            value = "" if record.get(header) is None else str(record[header])
            widths[header] = max(widths[header], len(value))
            row.append(value)
        rendered_rows.append(row)

    lines = []
    lines.append("  ".join(header.ljust(widths[header]) for header in headers))
    lines.append("  ".join("-" * widths[header] for header in headers))
    for row in rendered_rows:
        lines.append(
            "  ".join(
                row[index].ljust(widths[headers[index]]) for index in range(len(headers))
            )
        )
    return "\n".join(lines)


def format_csv(records: List[dict[str, Any]]) -> str:
    if not records:
        return ""

    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def build_string_filter_expression(
    raw_filters: Optional[Iterable[list[str]]],
) -> Optional[dict[str, Any]]:
    if not raw_filters:
        return None

    expressions = []
    for field_name, operator, value in raw_filters:
        match_type = STRING_MATCH_TYPES.get(operator.lower())
        if not match_type:
            valid = ", ".join(sorted(STRING_MATCH_TYPES))
            raise SystemExit(
                f"Unsupported operator '{operator}'. Use one of: {valid}."
            )
        expressions.append(
            {
                "filter": {
                    "fieldName": field_name,
                    "stringFilter": {
                        "matchType": match_type,
                        "value": value,
                        "caseSensitive": False,
                    },
                }
            }
        )

    if len(expressions) == 1:
        return expressions[0]

    return {"andGroup": {"expressions": expressions}}


def list_properties(session: AuthorizedSession) -> dict[str, Any]:
    response = session.get(
        "https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=200"
    )
    response.raise_for_status()
    payload = response.json()
    records: list[dict[str, Any]] = []
    for account_summary in payload.get("accountSummaries", []):
        account_name = account_summary.get("displayName", "")
        account_id = account_summary.get("account", "").split("/")[-1]
        for property_summary in account_summary.get("propertySummaries", []):
            property_name = property_summary.get("displayName", "")
            property_id = property_summary.get("property", "").split("/")[-1]
            records.append(
                {
                    "accountName": account_name,
                    "accountId": account_id,
                    "propertyName": property_name,
                    "propertyId": property_id,
                    "propertyType": property_summary.get("propertyType", ""),
                }
            )
    return {"properties": records, "count": len(records)}


def run_report(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    start_date, end_date = resolve_date_range(args)
    dimensions = [item.strip() for item in args.dimensions.split(",") if item.strip()]
    metrics = [item.strip() for item in args.metrics.split(",") if item.strip()]

    body: dict[str, Any] = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensions": [{"name": name} for name in dimensions],
        "metrics": [{"name": name} for name in metrics],
        "limit": args.row_limit,
    }

    filter_expression = build_string_filter_expression(args.filter)
    if filter_expression:
        body["dimensionFilter"] = filter_expression

    if args.order_by:
        if args.order_by in metrics:
            body["orderBys"] = [
                {"metric": {"metricName": args.order_by}, "desc": args.desc}
            ]
        elif args.order_by in dimensions:
            body["orderBys"] = [
                {"dimension": {"dimensionName": args.order_by}, "desc": args.desc}
            ]
        else:
            raise SystemExit(
                f"--order-by '{args.order_by}' must match one of the requested "
                "dimensions or metrics."
            )

    response = session.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{args.property_id}:runReport",
        json=body,
    )
    response.raise_for_status()
    payload = response.json()

    records: list[dict[str, Any]] = []
    for row in payload.get("rows", []):
        record: dict[str, Any] = {}
        for index, header in enumerate(payload.get("dimensionHeaders", [])):
            values = row.get("dimensionValues", [])
            record[header.get("name", f"dimension{index}")] = (
                values[index].get("value", "") if index < len(values) else ""
            )
        for index, header in enumerate(payload.get("metricHeaders", [])):
            values = row.get("metricValues", [])
            record[header.get("name", f"metric{index}")] = (
                values[index].get("value", "") if index < len(values) else ""
            )
        records.append(record)

    return {
        "request": {
            "propertyId": args.property_id,
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "metrics": metrics,
            "filters": args.filter or [],
            "orderBy": args.order_by or "",
            "desc": args.desc,
            "limit": args.row_limit,
        },
        "metadata": payload.get("metadata", {}),
        "rowCount": payload.get("rowCount", len(records)),
        "rows": records,
    }


def main() -> int:
    args = parse_args()
    credentials = load_credentials(args.token_file)
    session = AuthorizedSession(credentials)

    if args.list_properties:
        payload = list_properties(session)
        if args.output_format == "json":
            content = json.dumps(payload, ensure_ascii=False, indent=2)
        elif args.output_format == "csv":
            content = format_csv(payload["properties"])
        else:
            content = format_table(payload["properties"])
        emit_output(content, args.output)
        return 0

    payload = run_report(session, args)
    if args.output_format == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2)
    elif args.output_format == "csv":
        content = format_csv(payload["rows"])
    else:
        summary = (
            f"propertyId={payload['request']['propertyId']}  "
            f"startDate={payload['request']['startDate']}  "
            f"endDate={payload['request']['endDate']}  "
            f"rows={payload['rowCount']}"
        )
        table = format_table(payload["rows"])
        content = f"{summary}\n\n{table}"
    emit_output(content, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
