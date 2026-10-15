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
OUT = Path(__file__).parent / "docs" / "feed.xml"
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


def main():
    items = collect()
    if not items:
        sys.exit("게시물을 하나도 못 찾음 - 사이트 구조 변경 또는 차단 확인 필요")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(build_rss(items), encoding="utf-8")
    print(f"{len(items)} items -> {OUT}")


if __name__ == "__main__":
    main()
