"""Google Sheets MCP Server for Claude.ai"""

import json
import os

from fastmcp import FastMCP
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Config ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

mcp = FastMCP("Google Sheets")


def get_sheets_service():
    """Build Google Sheets API service from credentials."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable is not set")
    creds_info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


@mcp.tool()
def read_sheet(
    spreadsheet_id: str,
    range: str = "A1:Z1000",
    sheet_name: str = "",
) -> str:
    """Read data from a Google Spreadsheet.

    Args:
        spreadsheet_id: The ID from the spreadsheet URL
            (e.g. "1KRRjhwlpnzx1my8RGJZPLvcrIV6wZQmk8I4Qagtd4qM")
        range: Cell range to read (e.g. "A1:F100"). Defaults to "A1:Z1000".
        sheet_name: Optional sheet name. If provided, prepended to range
            (e.g. "Sheet1").
    """
    service = get_sheets_service()
    full_range = f"{sheet_name}!{range}" if sheet_name else range
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=full_range)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return "No data found."

    # Format as readable table
    lines = []
    for i, row in enumerate(values):
        lines.append(f"Row {i + 1}: {' | '.join(str(cell) for cell in row)}")
    return "\n".join(lines)


@mcp.tool()
def write_sheet(
    spreadsheet_id: str,
    range: str,
    values: list[list[str]],
    sheet_name: str = "",
) -> str:
    """Write data to a Google Spreadsheet.

    Args:
        spreadsheet_id: The ID from the spreadsheet URL.
        range: Cell range to write (e.g. "C2:E2").
        values: 2D array of values to write
            (e.g. [["Title1", "Title2", "Title3"]]).
        sheet_name: Optional sheet name.
    """
    service = get_sheets_service()
    full_range = f"{sheet_name}!{range}" if sheet_name else range
    body = {"values": values}
    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )
    return f"Updated {result.get('updatedCells', 0)} cells."


@mcp.tool()
def get_sheet_names(spreadsheet_id: str) -> str:
    """Get all sheet (tab) names in a spreadsheet.

    Args:
        spreadsheet_id: The ID from the spreadsheet URL.
    """
    service = get_sheets_service()
    result = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = result.get("sheets", [])
    names = [s["properties"]["title"] for s in sheets]
    return "\n".join(names)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
