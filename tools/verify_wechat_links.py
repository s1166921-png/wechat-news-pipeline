#!/usr/bin/env python3
"""Batch-check WeChat article extraction quality.

Usage:
  python tools/verify_wechat_links.py URL1 URL2 ...

With no arguments, the script checks the current regression sample set.
It prints metadata only, never full article text.
"""
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402


DEFAULT_URLS = [
    "https://mp.weixin.qq.com/s/nlxlzZV4kBFMk92frmamMA",
    "https://mp.weixin.qq.com/s/O207HqidoFLAqDgu9cqdSg",
    "https://mp.weixin.qq.com/s/Koxe229F89sbcdUf7eYDcw",
]


def summarize(url):
    article = app._fetch_article_content(url)
    if not article:
        return {
            "url": url,
            "ok": False,
            "status": "none",
            "method": "",
            "title": "",
            "chars": 0,
            "quality": {"usable": False, "reasons": ["no_result"]},
        }

    quality = article.get("quality") or {}
    return {
        "url": url,
        "ok": bool(article.get("ok")),
        "status": article.get("status", ""),
        "method": article.get("extraction_method", ""),
        "title": article.get("title", ""),
        "chars": article.get("char_count", len(article.get("content") or "")),
        "quality": {
            "usable": quality.get("usable"),
            "reasons": quality.get("reasons", []),
        },
    }


def main(argv):
    urls = argv[1:] or DEFAULT_URLS
    results = [summarize(url) for url in urls]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r["ok"] and r["quality"]["usable"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
