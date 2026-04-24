#!/usr/bin/env python3
"""Report prefecture-specific blog article coverage for this workspace."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BLOG_INDEX = ROOT / "blog.html"
ARTICLE_GLOB = "blog-*-llmo-kaisha.html"

PREFECTURES = (
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
)

TITLE_PATTERN = re.compile(
    r'<h1[^>]*class=["\'][^"\']*post-title[^"\']*["\'][^>]*>(.*?)</h1>',
    re.DOTALL,
)
FALLBACK_TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")
HREF_PATTERN = re.compile(r'href="(blog-[^"]+\.html)"')
ITEMLIST_URL_PATTERN = re.compile(
    r'"url"\s*:\s*"https://ai-and-marketing\.jp/(blog-[^"]+\.html)"'
)


@dataclass(frozen=True)
class PrefectureConfig:
    prefecture: str
    slug: str
    label: str


@dataclass(frozen=True)
class ArticleRecord:
    prefecture: str
    label: str
    slug: str
    article: str
    title: str


PREFECTURE_CONFIGS = (
    PrefectureConfig("北海道", "hokkaido", "北海道"),
    PrefectureConfig("青森県", "aomori", "青森"),
    PrefectureConfig("岩手県", "iwate", "岩手"),
    PrefectureConfig("宮城県", "miyagi", "宮城"),
    PrefectureConfig("秋田県", "akita", "秋田"),
    PrefectureConfig("山形県", "yamagata", "山形"),
    PrefectureConfig("福島県", "fukushima", "福島"),
    PrefectureConfig("茨城県", "ibaraki", "茨城"),
    PrefectureConfig("栃木県", "tochigi", "栃木"),
    PrefectureConfig("群馬県", "gunma", "群馬"),
    PrefectureConfig("埼玉県", "saitama", "埼玉"),
    PrefectureConfig("千葉県", "chiba", "千葉"),
    PrefectureConfig("東京都", "tokyo", "東京"),
    PrefectureConfig("神奈川県", "kanagawa", "神奈川"),
    PrefectureConfig("新潟県", "niigata", "新潟"),
    PrefectureConfig("富山県", "toyama", "富山"),
    PrefectureConfig("石川県", "ishikawa", "石川"),
    PrefectureConfig("福井県", "fukui", "福井"),
    PrefectureConfig("山梨県", "yamanashi", "山梨"),
    PrefectureConfig("長野県", "nagano", "長野"),
    PrefectureConfig("岐阜県", "gifu", "岐阜"),
    PrefectureConfig("静岡県", "shizuoka", "静岡"),
    PrefectureConfig("愛知県", "aichi", "愛知"),
    PrefectureConfig("三重県", "mie", "三重"),
    PrefectureConfig("滋賀県", "shiga", "滋賀"),
    PrefectureConfig("京都府", "kyoto", "京都"),
    PrefectureConfig("大阪府", "osaka", "大阪"),
    PrefectureConfig("兵庫県", "hyogo", "兵庫"),
    PrefectureConfig("奈良県", "nara", "奈良"),
    PrefectureConfig("和歌山県", "wakayama", "和歌山"),
    PrefectureConfig("鳥取県", "tottori", "鳥取"),
    PrefectureConfig("島根県", "shimane", "島根"),
    PrefectureConfig("岡山県", "okayama", "岡山"),
    PrefectureConfig("広島県", "hiroshima", "広島"),
    PrefectureConfig("山口県", "yamaguchi", "山口"),
    PrefectureConfig("徳島県", "tokushima", "徳島"),
    PrefectureConfig("香川県", "kagawa", "香川"),
    PrefectureConfig("愛媛県", "ehime", "愛媛"),
    PrefectureConfig("高知県", "kochi", "高知"),
    PrefectureConfig("福岡県", "fukuoka", "福岡"),
    PrefectureConfig("佐賀県", "saga", "佐賀"),
    PrefectureConfig("長崎県", "nagasaki", "長崎"),
    PrefectureConfig("熊本県", "kumamoto", "熊本"),
    PrefectureConfig("大分県", "oita", "大分"),
    PrefectureConfig("宮崎県", "miyazaki", "宮崎"),
    PrefectureConfig("鹿児島県", "kagoshima", "鹿児島"),
    PrefectureConfig("沖縄県", "okinawa", "沖縄"),
)

PREFECTURE_BY_NAME = {
    config.prefecture: config for config in PREFECTURE_CONFIGS
}


def prefecture_aliases(name: str) -> tuple[str, ...]:
    aliases = [name]
    if name != "北海道" and name[-1] in "都道府県":
        aliases.append(name[:-1])
    return tuple(dict.fromkeys(aliases))


PREFECTURE_ALIASES = {
    config.prefecture: tuple(
        dict.fromkeys(
            [
                *prefecture_aliases(config.prefecture),
                config.label,
            ]
        )
    )
    for config in PREFECTURE_CONFIGS
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_tags(value: str) -> str:
    return re.sub(TAG_PATTERN, "", value).strip()


def extract_title(html: str) -> str:
    match = TITLE_PATTERN.search(html) or FALLBACK_TITLE_PATTERN.search(html)
    if not match:
        return ""
    return strip_tags(match.group(1))


def detect_prefecture(title: str) -> str | None:
    matches: list[str] = []
    for prefecture, aliases in PREFECTURE_ALIASES.items():
        if any(alias in title for alias in aliases):
            matches.append(prefecture)
    if len(matches) == 1:
        return matches[0]
    return None


def prefecture_payload(config: PrefectureConfig) -> dict[str, str]:
    return {
        "prefecture": config.prefecture,
        "label": config.label,
        "slug": config.slug,
        "article": f"blog-{config.slug}-llmo-kaisha.html",
    }


def collect_articles() -> tuple[list[ArticleRecord], list[str], dict[str, list[str]]]:
    records: list[ArticleRecord] = []
    skipped_files: list[str] = []
    duplicates: dict[str, list[str]] = defaultdict(list)

    for path in sorted(ROOT.glob(ARTICLE_GLOB)):
        title = extract_title(read_text(path))
        prefecture = detect_prefecture(title)
        if prefecture is None:
            skipped_files.append(path.name)
            continue
        config = PREFECTURE_BY_NAME[prefecture]
        records.append(
            ArticleRecord(
                prefecture=prefecture,
                label=config.label,
                slug=config.slug,
                article=path.name,
                title=title,
            )
        )
        duplicates[prefecture].append(path.name)

    duplicate_records = {
        prefecture: files for prefecture, files in duplicates.items() if len(files) > 1
    }
    return records, skipped_files, duplicate_records


def unique_in_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def blog_index_links() -> tuple[list[str], list[str]]:
    html = read_text(BLOG_INDEX)
    href_links = unique_in_order(HREF_PATTERN.findall(html))
    itemlist_links = unique_in_order(ITEMLIST_URL_PATTERN.findall(html))
    return href_links, itemlist_links


def build_warnings(
    records: list[ArticleRecord],
    duplicates: dict[str, list[str]],
    card_links: list[str],
    itemlist_links: list[str],
) -> list[str]:
    warnings: list[str] = []
    prefecture_files = {record.article for record in records}
    card_link_set = set(card_links)
    itemlist_link_set = set(itemlist_links)

    for prefecture, files in sorted(duplicates.items()):
        joined = ", ".join(sorted(files))
        warnings.append(f"{prefecture} の記事が重複しています: {joined}")

    for article in sorted(prefecture_files - card_link_set):
        warnings.append(f"{article} が blog.html のカードリンクに出ていません")

    for article in sorted(prefecture_files - itemlist_link_set):
        warnings.append(f"{article} が blog.html の ItemList JSON-LD に出ていません")

    for article in card_links:
        if not (ROOT / article).exists():
            warnings.append(f"blog.html のカードリンク先が存在しません: {article}")

    for article in itemlist_links:
        if not (ROOT / article).exists():
            warnings.append(f"blog.html の ItemList JSON-LD のリンク先が存在しません: {article}")

    if card_links != itemlist_links:
        warnings.append("blog.html のカード順と ItemList JSON-LD の順番が一致していません")

    return warnings


def build_report() -> dict[str, Any]:
    records, skipped_files, duplicates = collect_articles()
    card_links, itemlist_links = blog_index_links()
    covered = sorted(
        records,
        key=lambda record: PREFECTURES.index(record.prefecture),
    )
    covered_names = {record.prefecture for record in covered}
    missing = [prefecture for prefecture in PREFECTURES if prefecture not in covered_names]
    missing_details = [prefecture_payload(PREFECTURE_BY_NAME[name]) for name in missing]
    warnings = build_warnings(covered, duplicates, card_links, itemlist_links)

    return {
        "covered": [asdict(record) for record in covered],
        "missing": missing,
        "missing_details": missing_details,
        "skipped_files": skipped_files,
        "blog_index": {
            "card_links": sorted(card_links),
            "itemlist_links": sorted(itemlist_links),
        },
        "warnings": warnings,
    }


def print_plain(report: dict[str, Any]) -> None:
    covered = report["covered"]
    missing = report["missing"]
    warnings = report["warnings"]

    print(f"都道府県別記事: {len(covered)}件")
    for entry in covered:
        print(f"- {entry['prefecture']}: {entry['article']}")
    print()

    print(f"未掲載: {len(missing)}件")
    print("、".join(missing))
    print()

    print("blog.html 連携状況")
    print(
        f"- カードリンク: {len(report['blog_index']['card_links'])}件"
    )
    print(
        f"- ItemList JSON-LD: {len(report['blog_index']['itemlist_links'])}件"
    )
    print()

    if warnings:
        print("警告")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("警告なし")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show which prefecture-specific blog articles exist in this workspace."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when blog index consistency warnings are found.",
    )
    parser.add_argument(
        "--next-missing",
        action="store_true",
        help="Print only the next missing prefecture article target.",
    )
    args = parser.parse_args()

    report = build_report()
    next_missing = report["missing_details"][0] if report["missing_details"] else None

    if args.next_missing:
        if args.json:
            print(json.dumps(next_missing, ensure_ascii=False, indent=2))
        elif next_missing:
            print(
                f"{next_missing['prefecture']} "
                f"{next_missing['label']} "
                f"{next_missing['slug']} "
                f"{next_missing['article']}"
            )
        else:
            print("なし")
    elif args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_plain(report)

    if args.strict and report["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
