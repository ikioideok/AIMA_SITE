#!/usr/bin/env python3
"""AI深報の公開前SEO検査。問題があれば終了コード1を返す。"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHINPO = ROOT / "shinpo"
errors = []


def need(condition, message):
    if not condition:
        errors.append(message)


for xml_path in (SHINPO / "feed.xml", ROOT / "news-sitemap.xml", ROOT / "sitemap.xml"):
    try:
        ET.parse(xml_path)
    except Exception as exc:
        errors.append(f"XMLが壊れています: {xml_path.name}: {exc}")

articles = sorted(SHINPO.glob("20??-??-??-*.html"))
need(bool(articles), "記事がありません")
for path in articles:
    source = path.read_text()
    prefix = path.name
    need('max-image-preview:large' in source, f"{prefix}: 大きい画像プレビュー設定がありません")
    need('type="application/rss+xml"' in source, f"{prefix}: RSS案内がありません")
    need('class="sh-article-image"' in source, f"{prefix}: 記事画像がありません")
    need('class="sh-related"' in source, f"{prefix}: 関連記事がありません")
    need('class="sh-breadcrumb"' in source, f"{prefix}: パンくずがありません")
    need('index.html?category=' not in source, f"{prefix}: 古いカテゴリURLが残っています")
    image = ROOT / "images/shinpo/articles" / f"{path.stem}.webp"
    need(image.exists(), f"{prefix}: 固有画像ファイルがありません")
    for raw in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', source, re.S):
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{prefix}: 構造化データが壊れています: {exc}")

for label in ("company", "product", "generative-ai", "security", "notice"):
    need((SHINPO / f"category-{label}.html").exists(), f"カテゴリページがありません: {label}")

for public in (SHINPO / "editorial-policy.html", ROOT / "llms.txt", ROOT / "images/apple-touch-icon.png"):
    need(public.exists(), f"公開ファイルがありません: {public.name}")

if errors:
    print("AI深報 SEO検査: NG", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)
print(f"AI深報 SEO検査: OK（{len(articles)}記事）")
