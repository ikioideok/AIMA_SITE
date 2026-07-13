#!/usr/bin/env python3
"""企業サイト共通ヘッダー・フッターを対象HTMLへ同期する。"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
PARTIALS = ROOT / "partials"

BLOCKS = {
    "head": (
        re.compile(r"<!-- SITE_SHELL_HEAD_START -->.*?<!-- SITE_SHELL_HEAD_END -->", re.S),
        PARTIALS / "site-shell-head.html",
        "SITE_SHELL_HEAD",
    ),
    "header": (
        re.compile(r"<!-- SITE_HEADER_START -->.*?<!-- SITE_HEADER_END -->", re.S),
        PARTIALS / "site-header.html",
        "SITE_HEADER",
    ),
    "footer": (
        re.compile(r"<!-- SITE_FOOTER_START -->.*?<!-- SITE_FOOTER_END -->", re.S),
        PARTIALS / "site-footer.html",
        "SITE_FOOTER",
    ),
}


def wrapped(marker: str, content: str) -> str:
    return f"<!-- {marker}_START -->\n{content.strip()}\n<!-- {marker}_END -->"


def main() -> None:
    check_only = "--check" in sys.argv
    partial_text = {
        key: wrapped(marker, path.read_text(encoding="utf-8"))
        for key, (_, path, marker) in BLOCKS.items()
    }

    targets = []
    for path in sorted(ROOT.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        if "<!-- SITE_HEADER_START -->" in text or "<!-- SITE_FOOTER_START -->" in text:
            targets.append(path)

    updated = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        new_text = text
        for key, (pattern, _, marker) in BLOCKS.items():
            if not pattern.search(new_text):
                sys.exit(f"{path.name}: {marker} ブロックがありません")
            new_text = pattern.sub(lambda _: partial_text[key], new_text, count=1)

        if new_text != text:
            updated.append(path.name)
            if not check_only:
                path.write_text(new_text, encoding="utf-8")

    print(("差分あり" if check_only else "更新") + f": {len(updated)}件")
    for name in updated:
        print(f"  - {name}")
    print(f"対象: {len(targets)}件")

    if check_only and updated:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
