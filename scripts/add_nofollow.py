#!/usr/bin/env python3
"""
Add rel="nofollow" to external links in blog-*.html, except for authoritative domains.

Whitelist (kept as follow):
- *.go.jp, *.lg.jp, *.or.jp, *.ac.jp (Japanese gov/industry/academic)
- pref.*.jp, city.*.jp, metro.tokyo.jp (prefecture/city sites without lg.jp)
- google.com, openai.com, bing.com, microsoft.com (platform docs)
- forrester.com (research)
- arte.aomori.jp (prefectural museum)
- ai-and-marketing.jp (own domain — ignored anyway as not external)
- fonts.googleapis.com, googletagmanager.com, schema.org (CDN/spec)

For all other external https?:// links:
- If <a> has rel attribute, ensure "nofollow" is included
- If no rel attribute, add rel="nofollow noopener"
"""
import re
import sys
from pathlib import Path

WHITELIST_SUFFIXES = (
    ".go.jp",
    ".lg.jp",
    ".or.jp",
    ".ac.jp",
)

WHITELIST_HOSTS = {
    "developers.google.com",
    "support.google.com",
    "blogs.bing.com",
    "developers.openai.com",
    "help.openai.com",
    "about.ads.microsoft.com",
    "www.forrester.com",
    "arte.aomori.jp",
    # prefecture/city without .lg.jp suffix
    "www.pref.aichi.jp",
    "www.pref.iwate.jp",
    "www.pref.kanagawa.jp",
    "www.pref.miyagi.jp",
    "www.pref.yamagata.jp",
    "www2.pref.iwate.jp",
    "www.city.nagoya.jp",
    "www.toukei.metro.tokyo.lg.jp",
}

IGNORE_HOSTS_SUBSTR = (
    "ai-and-marketing.jp",
    "fonts.googleapis.com",
    "googletagmanager.com",
    "schema.org",
)


def is_whitelisted(host: str) -> bool:
    if host in WHITELIST_HOSTS:
        return True
    for suf in WHITELIST_SUFFIXES:
        if host.endswith(suf):
            return True
    return False


def is_ignored(host: str) -> bool:
    return any(s in host for s in IGNORE_HOSTS_SUBSTR)


# Match <a ...href="https://..." ...>
A_TAG_RE = re.compile(r'<a\b([^>]*?)>', re.IGNORECASE)
HREF_RE = re.compile(r'href=(["\'])(https?://[^"\']+)\1', re.IGNORECASE)
REL_RE = re.compile(r'rel=(["\'])([^"\']*)\1', re.IGNORECASE)
HOST_RE = re.compile(r'^https?://([^/]+)')


def transform_a_tag(match: re.Match) -> str:
    attrs = match.group(1)
    href_m = HREF_RE.search(attrs)
    if not href_m:
        return match.group(0)
    url = href_m.group(2)
    host_m = HOST_RE.match(url)
    if not host_m:
        return match.group(0)
    host = host_m.group(1).lower()
    if is_ignored(host) or is_whitelisted(host):
        return match.group(0)

    rel_m = REL_RE.search(attrs)
    if rel_m:
        existing = rel_m.group(2)
        tokens = existing.split()
        if "nofollow" in tokens:
            return match.group(0)
        new_rel_value = " ".join(["nofollow"] + tokens)
        new_attrs = (
            attrs[: rel_m.start()]
            + f'rel="{new_rel_value}"'
            + attrs[rel_m.end():]
        )
    else:
        # Insert rel right after href
        href_end = href_m.end()
        new_attrs = (
            attrs[:href_end]
            + ' rel="nofollow noopener"'
            + attrs[href_end:]
        )

    return f"<a{new_attrs}>"


def process_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    new_text, _n = A_TAG_RE.subn(transform_a_tag, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        # count actual nofollow additions
        return new_text.count('rel="nofollow') - text.count('rel="nofollow')
    return 0


def main():
    files = sorted(Path(".").glob("blog-*.html"))
    files = [f for f in files if f.name != "blog-post.html"]
    total = 0
    for f in files:
        added = process_file(f)
        total += added
        print(f"{f.name}: +{added} nofollow")
    print(f"---\ntotal: +{total}")


if __name__ == "__main__":
    main()
