#!/usr/bin/env python3
"""AI深報 記事掲載スクリプト。

記事JSON（shinpo/drafts/*.json）からテンプレートで記事HTMLを生成し、
shinpo/index.html のリスト先頭（<!-- SHINPO:LIST --> 直後）にカードを挿入する。

使い方:
  python3 scripts/shinpo_publish.py shinpo/drafts/2026-07-11-example.json
  python3 scripts/shinpo_publish.py --check shinpo/drafts/2026-07-11-example.json
  python3 scripts/shinpo_publish.py --refresh shinpo/drafts/2026-07-11-example.json

記事JSONの形式:
{
  "slug": "openai-example",            # 半角英数とハイフン
  "title": "記事タイトル",
  "category": "生成AI",                 # 企業動向 / プロダクト / 生成AI / セキュリティ / お知らせ
  "breaking": true,                    # trueで速報バッジ（黄マーカー）
  "datetime": "2026-07-11T10:30",      # JSTのローカル日時
  "description": "meta description用の1文",
  "summary": "トップページのカードに出す1行要約",
  "lead3": ["1行目", "2行目", "3行目"],  # 「3行でわかる」
  "body_html": "<h2>…</h2><p>…</p>",   # 記事本文（HTML）
  "sources": [{"label": "openai.com", "url": "https://…"}],
  "candidate_url": "https://x.com/…"     # 任意。元キュー候補URL
}
"""

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from shinpo_queue import mark_by_url

ROOT = Path(__file__).resolve().parent.parent
SHINPO = ROOT / "shinpo"
TEMPLATE = SHINPO / "post-template.html"
INDEX = SHINPO / "index.html"
SITEMAP = ROOT / "sitemap.xml"
MARKER = "<!-- SHINPO:LIST -->"

CARD_TEMPLATE = """        <a class="sh-item" href="{filename}" data-news-card data-category="{category}" data-datetime="{date_iso}">
          <span class="sh-item-category">{category_display}</span>
          <span class="sh-item-copy">
            <strong>{title}</strong>
            <small>{summary}</small>
          </span>
          <time datetime="{date_iso}">{date_day}<br>{date_time}</time>
        </a>"""

PUBLIC_CATEGORIES = (
    "企業動向",
    "プロダクト",
    "生成AI",
    "セキュリティ",
    "お知らせ",
)

CATEGORY_ALIASES = {
    "企業": "企業動向",
    "製品": "プロダクト",
    "モデル": "生成AI",
}

TITLE_MIN_LENGTH = 20
TITLE_MAX_LENGTH = 64
TITLE_RECOMMENDED_MIN = 30
TITLE_RECOMMENDED_MAX = 50


def normalize_category(value):
    return CATEGORY_ALIASES.get(value, value)


def is_valid_title_length(title):
    return TITLE_MIN_LENGTH <= len(title) <= TITLE_MAX_LENGTH


def is_recommended_title_length(title):
    return TITLE_RECOMMENDED_MIN <= len(title) <= TITLE_RECOMMENDED_MAX


def update_sitemap_contents(contents, canonical_url, date_day):
    """AI深報トップの更新日を進め、新しい記事URLを1件だけ追加する。"""
    contents = re.sub(
        r"(<loc>https://ai-and-marketing\.jp/shinpo/</loc>\s*<lastmod>)[^<]+",
        rf"\g<1>{date_day}",
        contents,
        count=1,
    )
    if canonical_url in contents:
        return contents
    entry = (
        "  <url>\n"
        f"    <loc>{html.escape(canonical_url)}</loc>\n"
        f"    <lastmod>{date_day}</lastmod>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>0.8</priority>\n"
        "  </url>\n"
    )
    return contents.replace("</urlset>", entry + "</urlset>", 1)


def die(msg):
    print(f"エラー: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    check_only = len(sys.argv) == 3 and sys.argv[1] == "--check"
    refresh_only = len(sys.argv) == 3 and sys.argv[1] == "--refresh"
    if len(sys.argv) != 2 and not check_only and not refresh_only:
        die("記事JSONのパスを1つ指定してください")
    draft_path = Path(sys.argv[2] if check_only or refresh_only else sys.argv[1])
    if not draft_path.exists():
        die(f"{draft_path} が見つかりません")

    art = json.loads(draft_path.read_text())
    required = ["slug", "title", "category", "datetime", "description",
                "summary", "lead3", "body_html", "sources"]
    missing = [k for k in required if k not in art]
    if missing:
        die(f"記事JSONに必須キーがありません: {missing}")
    if not re.fullmatch(r"[a-z0-9-]+", art["slug"]):
        die("slugは半角英小文字・数字・ハイフンのみ")
    title_length = len(art["title"])
    if not is_valid_title_length(art["title"]):
        die(f"titleは20〜64文字にしてください（現在{title_length}文字）")
    if not is_recommended_title_length(art["title"]):
        print(
            f"注意: titleは30〜50文字を推奨します（現在{title_length}文字）",
            file=sys.stderr,
        )
    if len(art["lead3"]) != 3:
        die("lead3は3行ちょうどにしてください")
    if not art["sources"]:
        die("sourcesには一次情報を1件以上入れてください")
    category_display = normalize_category(art["category"])
    if category_display not in PUBLIC_CATEGORIES:
        die(
            "categoryは企業動向 / プロダクト / 生成AI / "
            "セキュリティ / お知らせのいずれかにしてください"
        )
    for source in art["sources"]:
        url = str(source.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            die(f"出典URLが不正です: {url}")

    dt = datetime.fromisoformat(art["datetime"])
    date_iso = dt.strftime("%Y-%m-%dT%H:%M")
    date_iso_with_zone = f"{date_iso}:00+09:00"
    date_display = dt.strftime("%Y.%m.%d %H:%M")
    filename = f"{dt.strftime('%Y-%m-%d')}-{art['slug']}.html"
    canonical_url = f"https://ai-and-marketing.jp/shinpo/{filename}"
    out_path = SHINPO / filename
    if check_only:
        print(f"OK: {draft_path}")
        return
    if out_path.exists() and not refresh_only:
        die(f"{filename} は既に存在します（上書きする場合は先に削除）")

    cat_class = " breaking" if art.get("breaking") else ""
    category = html.escape(category_display)
    title = html.escape(art["title"])

    lead_items = "\n".join(
        f"        <li>{html.escape(line)}</li>" for line in art["lead3"]
    )
    sources = "".join(
        f'<a class="sh-source-chip" href="{html.escape(s["url"])}" '
        f'target="_blank" rel="noopener">{html.escape(s["label"])}</a>'
        for s in art["sources"]
    )

    page = TEMPLATE.read_text()
    for key, value in {
        "{{TITLE}}": title,
        "{{DESCRIPTION}}": html.escape(art["description"]),
        "{{CANONICAL_URL}}": html.escape(canonical_url),
        "{{DATE_ISO_WITH_ZONE}}": date_iso_with_zone,
        "{{TITLE_JSON}}": json.dumps(art["title"], ensure_ascii=False),
        "{{DESCRIPTION_JSON}}": json.dumps(art["description"], ensure_ascii=False),
        "{{CATEGORY_JSON}}": json.dumps(category_display, ensure_ascii=False),
        "{{CATEGORY}}": category,
        "{{CAT_CLASS}}": cat_class,
        "{{DATE_ISO}}": date_iso,
        "{{DATE_DISPLAY}}": date_display,
        "{{LEAD_ITEMS}}": lead_items,
        "{{BODY}}": art["body_html"],
        "{{SOURCES}}": sources,
    }.items():
        page = page.replace(key, value)
    if "{{" in page:
        die("テンプレートに未置換のプレースホルダーが残っています")

    if refresh_only:
        out_path.write_text(page)
        print(f"更新: shinpo/{filename}")
        return

    card = CARD_TEMPLATE.format(
        filename=filename,
        category=category,
        category_display=category,
        date_iso=date_iso,
        date_day=dt.strftime("%Y.%m.%d"),
        date_time=dt.strftime("%H:%M"),
        title=title,
        summary=html.escape(art["summary"]),
    )

    index_html = INDEX.read_text()
    if MARKER not in index_html:
        die(f"index.html に {MARKER} がありません")
    index_html = index_html.replace(MARKER, MARKER + "\n" + card, 1)
    sitemap_html = update_sitemap_contents(
        SITEMAP.read_text(), canonical_url, dt.strftime("%Y-%m-%d")
    )

    out_path.write_text(page)
    INDEX.write_text(index_html)
    SITEMAP.write_text(sitemap_html)
    candidate_url = art.get("candidate_url")
    if candidate_url:
        if mark_by_url(candidate_url, "published"):
            print("更新: ニュースキュー（published）")
        else:
            print("注意: candidate_url はニュースキューにありません", file=sys.stderr)
    print(f"生成: shinpo/{filename}")
    print("更新: shinpo/index.html（カード挿入）")
    print("更新: sitemap.xml（記事URL追加）")


if __name__ == "__main__":
    main()
