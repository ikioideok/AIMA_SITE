#!/usr/bin/env python3
"""AI深報のSEO向け派生ファイルと静的導線を再構築する。"""

import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHINPO = ROOT / "shinpo"
BASE = "https://ai-and-marketing.jp"
JST = timezone(timedelta(hours=9))
CATEGORIES = {
    "企業動向": "company",
    "プロダクト": "product",
    "生成AI": "generative-ai",
    "セキュリティ": "security",
    "お知らせ": "notice",
}


def extract(pattern, source, default=""):
    match = re.search(pattern, source, re.S)
    return html.unescape(match.group(1).strip()) if match else default


def articles():
    result = []
    for path in sorted(SHINPO.glob("20??-??-??-*.html")):
        source = path.read_text()
        title = extract(r"<h1>(.*?)</h1>", source)
        description = extract(r'<meta name="description" content="([^"]*)">', source)
        category = extract(r'<span class="sh-cat[^\"]*">(.*?)</span>', source)
        published = extract(r'<meta property="article:published_time" content="([^"]+)">', source)
        modified = extract(r'<meta property="article:modified_time" content="([^"]+)">', source, published)
        summary = " ".join(re.findall(r"<li>(.*?)</li>", extract(r'<div class="sh-lead">(.*?)</div>', source)))
        result.append({
            "path": path,
            "filename": path.name,
            "title": re.sub(r"<[^>]+>", "", title),
            "description": description,
            "summary": re.sub(r"<[^>]+>", "", summary) or description,
            "category": category,
            "published": published,
            "modified": modified,
            "image": f"{BASE}/images/shinpo/articles/{path.stem}.webp",
            "url": f"{BASE}/shinpo/{path.name}",
        })
    return sorted(result, key=lambda item: item["published"], reverse=True)


def latest_html(items, current=None, limit=5):
    rows = []
    for item in (x for x in items if x["filename"] != current):
        dt = datetime.fromisoformat(item["published"])
        rows.append(
            f'<a class="sh-latest-entry" href="{item["filename"]}">'
            f'<time datetime="{item["published"]}">{dt:%m.%d}</time>'
            f'<strong>{html.escape(item["title"])}</strong></a>'
        )
        if len(rows) == limit:
            break
    return "\n        ".join(rows)


def related_html(items, current):
    same = [x for x in items if x["filename"] != current["filename"] and x["category"] == current["category"]]
    others = [x for x in items if x["filename"] != current["filename"] and x not in same]
    chosen = (same + others)[:3]
    links = "\n".join(
        f'        <a href="{x["filename"]}"><span>{html.escape(x["category"])}</span>'
        f'<strong>{html.escape(x["title"])}</strong></a>' for x in chosen
    )
    return (
        '<!-- SHINPO:RELATED:START -->\n'
        '    <section class="sh-related" aria-labelledby="related-title">\n'
        '      <h2 id="related-title">関連記事</h2>\n'
        '      <div class="sh-related-list">\n'
        f'{links}\n'
        '      </div>\n'
        '    </section>\n'
        '    <!-- SHINPO:RELATED:END -->'
    )


def static_footer():
    category_links = "".join(
        f'<a href="category-{slug}.html">{html.escape(label)}</a>'
        for label, slug in CATEGORIES.items()
    )
    return f'''<footer class="sh-footer">
  <div class="sh-footer-main">
    <div class="sh-footer-brand"><a href="./" class="sh-footer-logo">AI深報</a><p>どこよりも早く、AIの重要ニュースを。</p><span>POWERED BY AIMA</span></div>
    <div class="sh-footer-links">
      <div><strong>AI深報</strong><a href="./">トップ</a>{category_links}<a href="feed.xml">RSS</a></div>
      <div><strong>運営情報</strong><a href="editorial-policy.html">編集方針・訂正ポリシー</a><a href="../company.html">会社概要</a><a href="../privacy.html">プライバシーポリシー</a></div>
    </div>
  </div>
  <div class="sh-footer-bottom"><small>© 株式会社AIMA</small><span>AI SHINPO — FASTEST AI NEWS</span></div>
</footer>'''


def retrofit_article(item, items):
    path = item["path"]
    source = path.read_text()
    source = re.sub(r'<meta name="robots"[^>]*>\n?', '', source)
    source = source.replace('<meta name="viewport" content="width=device-width, initial-scale=1.0">', '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<meta name="robots" content="index,follow,max-image-preview:large">')
    if 'type="application/rss+xml"' not in source:
        source = source.replace('<link rel="canonical"', '<link rel="alternate" type="application/rss+xml" title="AI深報 RSS" href="https://ai-and-marketing.jp/shinpo/feed.xml">\n<link rel="canonical"')
    source = re.sub(r'https://ai-and-marketing\.jp/images/shinpo/ogp\.png', item["image"], source)
    source = source.replace('https://ai-and-marketing.jp/shinpo/images/ai-shinpo-logo.png', 'https://ai-and-marketing.jp/shinpo/images/ai-shinpo-logo.webp')
    source = re.sub(r'<meta property="og:image:alt" content="[^"]*">', f'<meta property="og:image:alt" content="{html.escape(item["title"])}">', source)
    source = re.sub(r'<meta name="twitter:image:alt" content="[^"]*">', f'<meta name="twitter:image:alt" content="{html.escape(item["title"])}">', source)
    source = re.sub(r'"author"\s*:\s*\{.*?\}', '"author": {"@type":"Person","name":"水間 雄紀","url":"https://ai-and-marketing.jp/company.html"}', source, count=1, flags=re.S)
    breadcrumb = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "AI深報", "item": f"{BASE}/shinpo/"},
            {"@type": "ListItem", "position": 2, "name": item["category"], "item": f"{BASE}/shinpo/category-{CATEGORIES.get(item['category'], 'news')}.html"},
            {"@type": "ListItem", "position": 3, "name": item["title"], "item": item["url"]},
        ],
    }, ensure_ascii=False, separators=(",", ":"))
    source = re.sub(r'<script type="application/ld\+json" data-shinpo-breadcrumb>.*?</script>\n?', '', source, flags=re.S)
    source = source.replace('</head>', f'<script type="application/ld+json" data-shinpo-breadcrumb>{breadcrumb}</script>\n</head>')
    crumb = f'<nav class="sh-breadcrumb" aria-label="パンくず"><a href="./">AI深報</a><span>›</span><a href="category-{CATEGORIES.get(item["category"], "news")}.html">{html.escape(item["category"])}</a><span>›</span><span aria-current="page">この記事</span></nav>'
    source = re.sub(r'<nav class="sh-breadcrumb".*?</nav>\n?', '', source, flags=re.S)
    source = source.replace('<article class="sh-article">', '<article class="sh-article">\n    ' + crumb)
    if 'class="sh-article-image"' not in source:
        image = f'<figure class="sh-article-image"><img src="../images/shinpo/articles/{path.stem}.webp" alt="{html.escape(item["title"])}" width="1200" height="630" fetchpriority="high" decoding="async"></figure>'
        source = source.replace('</h1>', '</h1>\n\n    ' + image, 1)
    source = re.sub(r'<!-- SHINPO:RELATED:START -->.*?<!-- SHINPO:RELATED:END -->', related_html(items, item), source, flags=re.S)
    if '<!-- SHINPO:RELATED:START -->' not in source:
        source = source.replace('    <a class="sh-back"', related_html(items, item) + '\n\n    <a class="sh-back"')
    source = re.sub(r'<div class="sh-latest-list" data-latest-list>.*?</div>', f'<div class="sh-latest-list" data-latest-list>\n        {latest_html(items, item["filename"])}\n      </div>', source, flags=re.S)
    source = re.sub(r'<footer class="sh-footer">.*?</footer>', static_footer(), source, flags=re.S)
    source = source.replace('href="index.html', 'href="./')
    source = re.sub(r'shinpo\.css\?v=\d+', 'shinpo.css?v=6', source)
    source = re.sub(r'shinpo\.js\?v=\d+', 'shinpo.js?v=3', source)
    source = re.sub(r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\n?', '', source)
    source = re.sub(r'<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\n?', '', source)
    source = re.sub(r'<link href="https://fonts\.googleapis\.com/[^"]+" rel="stylesheet">\n?', '', source)
    path.write_text(source)


def write_feed(items):
    rows = []
    for item in items[:50]:
        pub = datetime.fromisoformat(item["published"]).strftime("%a, %d %b %Y %H:%M:%S %z")
        rows.append(f'''  <item>
    <title>{html.escape(item["title"])}</title><link>{item["url"]}</link>
    <guid isPermaLink="true">{item["url"]}</guid><pubDate>{pub}</pubDate>
    <category>{html.escape(item["category"])}</category><description>{html.escape(item["description"])}</description>
  </item>''')
    updated = datetime.now(JST).strftime("%a, %d %b %Y %H:%M:%S %z")
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
  <title>AI深報</title><link>{BASE}/shinpo/</link><description>どこよりも早く、AIの重要ニュースを。</description>
  <language>ja</language><lastBuildDate>{updated}</lastBuildDate>
  <atom:link href="{BASE}/shinpo/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(rows)}
</channel></rss>
'''
    (SHINPO / "feed.xml").write_text(xml)


def write_news_sitemap(items):
    cutoff = datetime.now(JST) - timedelta(days=2)
    current = [x for x in items if datetime.fromisoformat(x["published"]) >= cutoff]
    rows = []
    for item in current:
        rows.append(f'''  <url><loc>{item["url"]}</loc><news:news>
    <news:publication><news:name>AI深報</news:name><news:language>ja</news:language></news:publication>
    <news:publication_date>{item["published"]}</news:publication_date><news:title>{html.escape(item["title"])}</news:title>
  </news:news></url>''')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + '\n'.join(rows) + '\n</urlset>\n'
    (ROOT / "news-sitemap.xml").write_text(xml)


def update_main_sitemap():
    path = ROOT / "sitemap.xml"
    source = path.read_text()
    urls = [
        (f"{BASE}/shinpo/category-{slug}.html", "weekly", "0.7")
        for slug in CATEGORIES.values()
    ] + [(f"{BASE}/shinpo/editorial-policy.html", "monthly", "0.5")]
    today = datetime.now(JST).date().isoformat()
    for url, frequency, priority in urls:
        if f"<loc>{url}</loc>" in source:
            continue
        entry = f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>{frequency}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n"
        source = source.replace("</urlset>", entry + "</urlset>", 1)
    path.write_text(source)


def write_category_pages(items):
    template = (SHINPO / "index.html").read_text()
    for label, slug in CATEGORIES.items():
        cards = re.findall(r'<a class="sh-item".*?</a>', template, re.S)
        cards = [card for card in cards if f'data-category="{label}"' in card]
        page = re.sub(r'<title>.*?</title>', f'<title>{label}のAIニュース｜AI深報</title>', template, count=1)
        page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{label}に関する最新AIニュースを一覧で紹介します。">', page, count=1)
        page = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{BASE}/shinpo/category-{slug}.html">', page, count=1)
        page = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{label}のAIニュース｜AI深報">', page, count=1)
        page = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{BASE}/shinpo/category-{slug}.html">', page, count=1)
        page = re.sub(r'<section class="sh-top-grid".*?</section>', '', page, count=1, flags=re.S)
        page = re.sub(r'<h2 id="latest-news-title">.*?</h2>', f'<h1 id="latest-news-title">{label}のニュース</h1>', page, count=1)
        page = re.sub(r'<!-- SHINPO:LIST -->.*?</div>\s*<p class="sh-empty"', '<!-- SHINPO:LIST -->\n' + '\n'.join(cards) + '\n      </div>\n      <p class="sh-empty"', page, count=1, flags=re.S)
        page = re.sub(r'<script type="application/ld\+json">.*?</script>', '', page, count=1, flags=re.S)
        page = re.sub(r'\n[ \t]+\n', '\n\n', page)
        (SHINPO / f"category-{slug}.html").write_text(page)


def retrofit_index(items):
    path = SHINPO / "index.html"
    source = path.read_text()
    source = re.sub(r'<div class="sh-latest-list" data-latest-list>.*?</div>', f'<div class="sh-latest-list" data-latest-list>\n        {latest_html(items)}\n      </div>', source, flags=re.S)
    source = re.sub(r'<footer class="sh-footer">.*?</footer>', static_footer(), source, flags=re.S)
    source = source.replace('href="index.html', 'href="./')
    source = re.sub(r'shinpo\.css\?v=\d+', 'shinpo.css?v=6', source)
    source = re.sub(r'shinpo\.js\?v=\d+', 'shinpo.js?v=3', source)
    path.write_text(source)


def rebuild():
    items = articles()
    for item in items:
        retrofit_article(item, items)
    retrofit_index(items)
    write_feed(items)
    write_news_sitemap(items)
    write_category_pages(items)
    update_main_sitemap()
    print(f"更新: {len(items)}記事 / feed.xml / news-sitemap.xml / カテゴリ{len(CATEGORIES)}ページ")


if __name__ == "__main__":
    rebuild()
