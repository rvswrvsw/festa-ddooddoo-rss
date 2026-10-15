#!/usr/bin/env python3
"""차 없는 잠수교 뚜벅뚜벅 축제 공지사항 -> RSS 2.0 (표준 라이브러리만 사용)."""
import html
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin
from xml.sax.saxutils import escape

BASE = "https://www.festa-ddooddoo.com/board/"
LIST_URL = BASE + "board.asp?BoardID=Notice&searchtext=&page={page}"
PAGES = 2  # 페이지당 10개
OUT_DIR = Path(__file__).parent / "public"
FEED_URL = "https://rvswrvsw.github.io/festa-ddooddoo-rss/feed.xml"
KST = timezone(timedelta(hours=9))

# WebKnight 방화벽이 브라우저 헤더 없는 요청은 406으로 막음
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

ROW_RE = re.compile(
    r"<td class='tline'><a href='(board_view\.asp\?[^']*SNO=(\d+))'>(.*?)</a></td>"
    r"\s*<td class='m_date'>(\d{4}-\d{2}-\d{2})</td>",
    re.S,
)
CONTENT_RE = re.compile(r'class="conbox rino">(.*?)</td>\s*</tr>\s*</tbody>', re.S)


def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"retry {url}: {e}", file=sys.stderr)
            time.sleep(3)


def clean_content(raw):
    # 본문에 수백 KB짜리 base64 이미지가 박혀 있어 제거
    raw = re.sub(r"<img[^>]*src=[\"']data:[^>]*>", "", raw, flags=re.I)
    raw = re.sub(r"\s(style|align|class)=(\"[^\"]*\"|'[^']*')", "", raw)
    raw = re.sub(
        r"(src|href)=([\"'])(?!https?:|mailto:|#)([^\"']*)\2",
        lambda m: f'{m[1]}="{urljoin(BASE, m[3])}"',
        raw,
    )
    raw = re.sub(r"(<p>(&nbsp;|\s|<span>(&nbsp;|\s)*</span>)*</p>)+", "", raw)
    return raw.strip()


def collect():
    items = {}
    for page in range(1, PAGES + 1):
        for href, sno, title, date in ROW_RE.findall(fetch(LIST_URL.format(page=page))):
            if sno in items:  # 상단 고정 공지는 매 페이지 반복됨
                continue
            title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
            link = urljoin(BASE, href.replace("&page=" + str(page), "&page=1"))
            items[sno] = {"sno": sno, "title": title, "link": link, "date": date}

    for it in items.values():
        m = CONTENT_RE.search(fetch(it["link"]))
        body = clean_content(m[1]) if m else ""
        if not re.sub(r"<[^>]+>|&nbsp;|\s", "", body):
            body = "<p>(이미지 공지입니다. 원문에서 확인하세요.)</p>"
        it["body"] = body
        time.sleep(0.5)

    return sorted(items.values(), key=lambda x: (x["date"], int(x["sno"])), reverse=True)


def build_rss(items):
    now = format_datetime(datetime.now(KST))
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        "<title>차 없는 잠수교 뚜벅뚜벅 축제 공지사항</title>",
        f"<link>{escape(BASE + 'board.asp')}</link>",
        f'<atom:link href="{escape(FEED_URL)}" rel="self" type="application/rss+xml"/>',
        "<description>festa-ddooddoo.com 공지사항 비공식 RSS</description>",
        "<language>ko</language>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]
    for it in items:
        pub = format_datetime(datetime.strptime(it["date"], "%Y-%m-%d").replace(tzinfo=KST))
        out += [
            "<item>",
            f"<title>{escape(it['title'])}</title>",
            f"<link>{escape(it['link'])}</link>",
            f'<guid isPermaLink="false">festa-ddooddoo-notice-{it["sno"]}</guid>',
            f"<pubDate>{pub}</pubDate>",
            f"<description><![CDATA[{it['body'].replace(']]>', ']]&gt;')}]]></description>",
            "</item>",
        ]
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)


HTML_HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>뚜벅뚜벅 축제 공지</title>
<link rel="alternate" type="application/rss+xml" title="뚜벅뚜벅 축제 공지사항" href="feed.xml">
<style>
:root {
  --bg: #f6f7f9; --card: #fff; --text: #1d2129; --muted: #6b7280;
  --line: #e5e7eb; --accent: #2563eb; --accent-bg: #eff4ff;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111317; --card: #1b1e24; --text: #e6e8eb; --muted: #9aa1ac;
    --line: #2c313a; --accent: #7aa7ff; --accent-bg: #1e2a44;
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
    "Pretendard", "Noto Sans KR", "Malgun Gothic", sans-serif;
  word-break: keep-all; overflow-wrap: anywhere;
}
.wrap { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }
header { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; justify-content: space-between; margin-bottom: 20px; }
h1 { font-size: 1.35rem; margin: 0; line-height: 1.3; }
.sub { color: var(--muted); font-size: .85rem; margin: 4px 0 0; }
.rss {
  display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px;
  border-radius: 999px; background: var(--accent-bg); color: var(--accent);
  font-weight: 600; font-size: .9rem; text-decoration: none; white-space: nowrap;
}
.rss svg { width: 16px; height: 16px; fill: currentColor; }
.list { display: grid; gap: 10px; }
details { background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
summary { list-style: none; cursor: pointer; padding: 14px 44px 14px 16px; position: relative; }
summary::-webkit-details-marker { display: none; }
summary::after {
  content: ""; position: absolute; right: 18px; top: 50%; width: 8px; height: 8px;
  border-right: 2px solid var(--muted); border-bottom: 2px solid var(--muted);
  transform: translateY(-70%) rotate(45deg); transition: transform .15s;
}
details[open] summary::after { transform: translateY(-30%) rotate(-135deg); }
summary:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.date { display: block; color: var(--muted); font-size: .8rem; font-variant-numeric: tabular-nums; }
.title { display: block; font-weight: 600; margin-top: 2px; }
.body { padding: 4px 16px 16px; border-top: 1px solid var(--line); font-size: .95rem; }
.body img { max-width: 100%; height: auto; }
.body table { display: block; overflow-x: auto; border-collapse: collapse; max-width: 100%; }
.body td, .body th { border: 1px solid var(--line); padding: 4px 8px; }
.body a { color: var(--accent); }
.orig { display: inline-block; margin-top: 12px; color: var(--accent); font-size: .9rem; font-weight: 600; text-decoration: none; }
footer { margin-top: 28px; color: var(--muted); font-size: .8rem; text-align: center; }
footer a { color: inherit; }
</style>
</head>
"""

RSS_ICON = ('<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="3" cy="13" r="2"/>'
            '<path d="M1 6.5v2A6.5 6.5 0 0 1 7.5 15h2A8.5 8.5 0 0 0 1 6.5zm0-5v2A11.5 11.5 0 0 1 '
            '12.5 15h2A13.5 13.5 0 0 0 1 1.5z"/></svg>')


def build_html(items):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    cards = []
    for it in items:
        cards.append(
            "<details>"
            f'<summary><time class="date" datetime="{it["date"]}">{it["date"]}</time>'
            f'<span class="title">{escape(it["title"])}</span></summary>'
            f'<div class="body">{it["body"]}'
            f'<a class="orig" href="{escape(it["link"])}" target="_blank" rel="noopener">원문 보기 →</a>'
            "</div></details>"
        )
    return (
        HTML_HEAD
        + '<body><div class="wrap"><header><div>'
        + "<h1>차 없는 잠수교 뚜벅뚜벅 축제 공지사항</h1>"
        + f'<p class="sub">최근 {len(items)}개 · {now} KST 갱신</p></div>'
        + f'<a class="rss" href="feed.xml">{RSS_ICON}RSS 구독</a></header>'
        + '<main class="list">' + "\n".join(cards) + "</main>"
        + f'<footer>비공식 미러 · 출처 <a href="{escape(BASE + "board.asp")}">festa-ddooddoo.com</a></footer>'
        + "</div></body></html>\n"
    )


def main():
    items = collect()
    if not items:
        sys.exit("게시물을 하나도 못 찾음 - 사이트 구조 변경 또는 차단 확인 필요")
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "feed.xml").write_text(build_rss(items), encoding="utf-8")
    (OUT_DIR / "index.html").write_text(build_html(items), encoding="utf-8")
    print(f"{len(items)} items -> {OUT_DIR}/feed.xml, index.html")


if __name__ == "__main__":
    main()
