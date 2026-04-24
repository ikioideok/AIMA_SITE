#!/usr/bin/env python3
"""Fetch Search Console Search Analytics data via Google's official API."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

warnings.filterwarnings(
    "ignore",
    message=r"urllib3 v2 only supports OpenSSL 1\.1\.1\+.*",
)

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
DEFAULT_TOKEN_FILE = ".tokens/google-readonly-combined-token.json"
FILTER_OPERATORS = {
    "contains": "contains",
    "equals": "equals",
    "notcontains": "notContains",
    "notequals": "notEquals",
    "includingregex": "includingRegex",
    "excludingregex": "excludingRegex",
}
SEARCH_TYPES = ["web", "image", "video", "news", "discover", "googleNews"]
AGGREGATION_TYPES = ["auto", "byPage", "byProperty", "byNewsShowcasePanel"]
DATA_STATES = ["final", "all", "hourly_all"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query Google Search Console Search Analytics data. "
            "Uses the official Search Console API searchanalytics.query endpoint."
        )
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="List Search Console properties visible to the authenticated account.",
    )
    parser.add_argument(
        "--site-url",
        help=(
            "Search Console property identifier, for example "
            "'https://example.com/' or 'sc-domain:example.com'."
        ),
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
        default=3,
        help=(
            "If explicit dates are omitted, end the range this many days before today. "
            "Search Console data is usually delayed. Default: 3."
        ),
    )
    parser.add_argument(
        "--dimensions",
        default="query",
        help=(
            "Comma-separated dimensions, for example 'query', 'page', "
            "'query,page', or 'date'. Default: query."
        ),
    )
    parser.add_argument(
        "--search-type",
        choices=SEARCH_TYPES,
        default="web",
        help="Search type to request. Default: web.",
    )
    parser.add_argument(
        "--aggregation",
        choices=AGGREGATION_TYPES,
        default="auto",
        help="Aggregation type. Default: auto.",
    )
    parser.add_argument(
        "--data-state",
        choices=DATA_STATES,
        default="final",
        help="Use finalized data or include fresh partial data. Default: final.",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        default=1000,
        help="Rows to fetch per request. Valid range is 1-25000. Default: 1000.",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=0,
        help="Zero-based result offset for pagination. Default: 0.",
    )
    parser.add_argument(
        "--filter",
        nargs=3,
        action="append",
        metavar=("DIMENSION", "OPERATOR", "VALUE"),
        help=(
            "Add a dimension filter. Example: "
            "--filter page contains /blog/ --filter device equals MOBILE"
        ),
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
    parser.add_argument(
        "--client-secrets",
        help=(
            "OAuth client secret JSON for a Desktop app. "
            "Can also be provided via SEARCH_CONSOLE_OAUTH_CLIENT_SECRETS."
        ),
    )
    parser.add_argument(
        "--token-file",
        default=os.environ.get("SEARCH_CONSOLE_TOKEN_FILE", DEFAULT_TOKEN_FILE),
        help=f"Where to cache the OAuth token. Default: {DEFAULT_TOKEN_FILE}",
    )
    parser.add_argument(
        "--service-account",
        help=(
            "Service account JSON file. The service account must be added as a "
            "Search Console user on the target property."
        ),
    )
    parser.add_argument(
        "--service-account-env",
        default="GOOGLE_CREDENTIALS_JSON",
        help=(
            "Environment variable containing service account JSON. "
            "Default: GOOGLE_CREDENTIALS_JSON."
        ),
    )

    args = parser.parse_args()
    validate_args(args)
    return args


def validate_args(args: argparse.Namespace) -> None:
    if not args.list_sites and not args.site_url:
        raise SystemExit("--site-url is required unless --list-sites is used.")
    if args.row_limit < 1 or args.row_limit > 25000:
        raise SystemExit("--row-limit must be between 1 and 25000.")
    if args.start_row < 0:
        raise SystemExit("--start-row must be 0 or greater.")
    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        raise SystemExit("--start-date and --end-date must be provided together.")
    if args.last_days < 1:
        raise SystemExit("--last-days must be 1 or greater.")
    if args.end_days_ago < 0:
        raise SystemExit("--end-days-ago must be 0 or greater.")


def resolve_date_range(args: argparse.Namespace) -> tuple[str, str]:
    if args.start_date and args.end_date:
        return args.start_date, args.end_date

    end_date = date.today() - timedelta(days=args.end_days_ago)
    start_date = end_date - timedelta(days=args.last_days - 1)
    return start_date.isoformat(), end_date.isoformat()


def load_credentials(args: argparse.Namespace):
    service_account_file = args.service_account or os.environ.get(
        "SEARCH_CONSOLE_SERVICE_ACCOUNT_FILE"
    )
    if service_account_file:
        return service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES
        )

    inline_service_account_json = os.environ.get(args.service_account_env)
    if inline_service_account_json:
        creds_info = json.loads(inline_service_account_json)
        if creds_info.get("type") != "service_account":
            raise SystemExit(
                f"{args.service_account_env} is set, but it does not contain service account JSON."
            )
        return service_account.Credentials.from_service_account_info(
            creds_info, scopes=SCOPES
        )

    token_path = Path(args.token_file)
    creds: Optional[UserCredentials] = None
    if token_path.exists():
        creds = UserCredentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    client_secrets = args.client_secrets or os.environ.get(
        "SEARCH_CONSOLE_OAUTH_CLIENT_SECRETS"
    )
    if not client_secrets:
        raise SystemExit(
            "No credentials found. Use an existing --token-file, provide "
            "--client-secrets for OAuth, or pass a service account."
        )

    flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(credentials):
    return build("searchconsole", "v1", credentials=credentials, cache_discovery=False)


def list_sites(service) -> Dict[str, Any]:
    response = service.sites().list().execute()
    sites = []
    for entry in response.get("siteEntry", []):
        sites.append(
            {
                "siteUrl": entry.get("siteUrl", ""),
                "permissionLevel": entry.get("permissionLevel", ""),
            }
        )
    return {"sites": sites, "count": len(sites)}


def build_dimension_filters(
    raw_filters: Optional[Iterable[List[str]]],
) -> Optional[List[Dict[str, Any]]]:
    if not raw_filters:
        return None

    filters = []
    for dimension, operator, expression in raw_filters:
        normalized_operator = FILTER_OPERATORS.get(operator.lower())
        if not normalized_operator:
            valid = ", ".join(sorted(FILTER_OPERATORS))
            raise SystemExit(
                f"Unsupported operator '{operator}'. Use one of: {valid}."
            )
        filters.append(
            {
                "dimension": dimension,
                "operator": normalized_operator,
                "expression": expression,
            }
        )
    return [{"groupType": "and", "filters": filters}]


def run_query(service, args: argparse.Namespace) -> Dict[str, Any]:
    start_date, end_date = resolve_date_range(args)
    dimensions = [item.strip() for item in args.dimensions.split(",") if item.strip()]
    body: Dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "type": args.search_type,
        "aggregationType": args.aggregation,
        "dataState": args.data_state,
        "rowLimit": args.row_limit,
        "startRow": args.start_row,
    }

    dimension_filter_groups = build_dimension_filters(args.filter)
    if dimension_filter_groups:
        body["dimensionFilterGroups"] = dimension_filter_groups

    response = (
        service.searchanalytics().query(siteUrl=args.site_url, body=body).execute()
    )
    rows = []
    for raw_row in response.get("rows", []):
        record = {}
        for index, dimension in enumerate(dimensions):
            keys = raw_row.get("keys", [])
            record[dimension] = keys[index] if index < len(keys) else ""
        record["clicks"] = raw_row.get("clicks", 0)
        record["impressions"] = raw_row.get("impressions", 0)
        record["ctr"] = raw_row.get("ctr", 0)
        record["position"] = raw_row.get("position", 0)
        rows.append(record)

    return {
        "request": {
            "siteUrl": args.site_url,
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "searchType": args.search_type,
            "aggregationType": args.aggregation,
            "dataState": args.data_state,
            "rowLimit": args.row_limit,
            "startRow": args.start_row,
            "filters": args.filter or [],
        },
        "responseAggregationType": response.get("responseAggregationType", ""),
        "rows": rows,
        "rowCount": len(rows),
    }


def format_table(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "No rows returned."

    headers = list(records[0].keys())
    display_rows: List[List[str]] = []
    widths = {header: len(header) for header in headers}

    for record in records:
        rendered_row = []
        for header in headers:
            value = record[header]
            if isinstance(value, float):
                if header == "ctr":
                    rendered = f"{value:.4%}"
                elif header == "position":
                    rendered = f"{value:.2f}"
                else:
                    rendered = f"{value:.2f}"
            else:
                rendered = str(value)
            widths[header] = max(widths[header], len(rendered))
            rendered_row.append(rendered)
        display_rows.append(rendered_row)

    lines = []
    header_line = "  ".join(header.ljust(widths[header]) for header in headers)
    divider_line = "  ".join("-" * widths[header] for header in headers)
    lines.append(header_line)
    lines.append(divider_line)
    for row in display_rows:
        lines.append(
            "  ".join(
                row[index].ljust(widths[headers[index]]) for index in range(len(headers))
            )
        )
    return "\n".join(lines)


def format_csv(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""

    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def emit_output(content: str, output_path: Optional[str]) -> None:
    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"Wrote {target}")
        return
    print(content)


def main() -> int:
    args = parse_args()
    credentials = load_credentials(args)
    service = build_service(credentials)

    if args.list_sites:
        sites_payload = list_sites(service)
        if args.output_format == "json":
            emit_output(json.dumps(sites_payload, ensure_ascii=False, indent=2), args.output)
        else:
            emit_output(format_table(sites_payload["sites"]), args.output)
        return 0

    payload = run_query(service, args)
    if args.output_format == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2)
    elif args.output_format == "csv":
        content = format_csv(payload["rows"])
    else:
        summary = (
            f"siteUrl={payload['request']['siteUrl']}  "
            f"startDate={payload['request']['startDate']}  "
            f"endDate={payload['request']['endDate']}  "
            f"rows={payload['rowCount']}"
        )
        table = format_table(payload["rows"])
        content = f"{summary}\n\n{table}"
    emit_output(content, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
