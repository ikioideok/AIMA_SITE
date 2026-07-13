#!/usr/bin/env python3
"""ブログ共通ヘッダー/フッターの同期スクリプト。

blog-post.html を唯一の正（テンプレート）として、
<header class="media-site-header">...</header> と
<footer class="blog-footer">...</footer> または
<footer class="corporate-footer">...</footer> のブロックを
blog.html とすべての blog-*.html に反映する。

使い方:
    python3 scripts/sync_blog_layout.py          # 反映
    python3 scripts/sync_blog_layout.py --check  # 差分確認のみ（書き換えない）
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "blog-post.html")
EXCLUDE = {"blog-post.html", "blog-redesign-v6.html"}

HEADER_RE = re.compile(r'<header class="media-site-header">.*?</header>', re.S)
FOOTER_RE = re.compile(r'<footer class="(?:blog-footer|corporate-footer)">.*?</footer>', re.S)


def main():
    check_only = "--check" in sys.argv

    template = open(TEMPLATE, encoding="utf-8").read()
    header_m = HEADER_RE.search(template)
    footer_m = FOOTER_RE.search(template)
    if not header_m or not footer_m:
        sys.exit("blog-post.html に media-site-header / blog-footer または corporate-footer が見つかりません")
    canonical_header = header_m.group(0)
    canonical_footer = footer_m.group(0)

    targets = sorted(
        set(glob.glob(os.path.join(ROOT, "blog-*.html"))
            + [os.path.join(ROOT, "blog.html")])
    )
    updated, in_sync, skipped = [], [], []
    for path in targets:
        name = os.path.basename(path)
        if name in EXCLUDE:
            continue
        text = open(path, encoding="utf-8").read()
        if not HEADER_RE.search(text) or not FOOTER_RE.search(text):
            skipped.append(name)
            continue
        new_text = HEADER_RE.sub(lambda _: canonical_header, text, count=1)
        new_text = FOOTER_RE.sub(lambda _: canonical_footer, new_text, count=1)
        if new_text == text:
            in_sync.append(name)
        else:
            updated.append(name)
            if not check_only:
                open(path, "w", encoding="utf-8").write(new_text)

    label = "差分あり" if check_only else "更新"
    print(f"{label}: {len(updated)}件")
    for name in updated:
        print(f"  - {name}")
    print(f"同期済み: {len(in_sync)}件")
    if skipped:
        print(f"対象ブロックなし（スキップ）: {skipped}")
    if check_only and updated:
        sys.exit(1)


if __name__ == "__main__":
    main()
