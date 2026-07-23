"""Test Zhihu search - try multiple approaches."""
import urllib.request, ssl, re, sys, json
from urllib.parse import quote
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Approach 1: API endpoint with proper headers
headers_api = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.zhihu.com/",
    "Origin": "https://www.zhihu.com",
    "x-requested-with": "fetch",
}

# Approach 2: Mobile search URL
headers_mobile = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

endpoints = [
    # Web search with full browser headers
    ("WEB", f"https://www.zhihu.com/search?type=content&q={quote('跨境电商')}", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }),
    # Zhihu API v4 search
    ("API", f"https://www.zhihu.com/api/v4/search_v3?t=general&q={quote('跨境电商')}&correction=1&offset=0&limit=10", headers_api),
    # Mobile search
    ("MOBILE", f"https://www.zhihu.com/search?type=content&q={quote('跨境电商')}", headers_mobile),
    # Zhihu topic/column search
    ("TOPIC", f"https://www.zhihu.com/api/v4/search/top_search?query={quote('跨境电商')}", {
        **headers_api,
        "x-api-version": "3.1.2",
    }),
]

for label, url, headers in endpoints:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        status = resp.status

        # Check if successful
        has_content = False
        if "application/json" in resp.getheader("Content-Type", ""):
            try:
                data = json.loads(html)
                results = data.get("data", data.get("list", []))
                print(f"[{label}] Status: {status} JSON results: {len(results)}")
                for r in results[:3]:
                    if isinstance(r, dict):
                        title = r.get("title", r.get("name", str(r)))[:80]
                        print(f"  - {title}")
                has_content = True
            except:
                pass

        if not has_content:
            content_len = len(html)
            blocked = "403" in str(status) or "安全验证" in html or "captcha" in html.lower()
            print(f"[{label}] Status: {status} Len: {content_len} Blocked: {blocked}")
            if not blocked and content_len > 1000:
                # Extract any readable text
                text = re.sub(r'<[^>]+>', ' ', html[:2000])
                text = re.sub(r'\s+', ' ', text)
                print(f"  Preview: {text[:200]}")

    except urllib.error.HTTPError as e:
        print(f"[{label}] HTTP {e.code}: {str(e)[:100]}")
    except Exception as e:
        print(f"[{label}] ERROR: {str(e)[:100]}")
