"""Test Zhihu search accessibility."""
import urllib.request, ssl, re, sys
from urllib.parse import quote
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

keywords = ["跨境电商", "亚马逊 FBA"]

for kw in keywords:
    url = f"https://www.zhihu.com/search?type=content&q={quote(kw)}"
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        print(f"\n[{kw}] Status: {resp.status}  Len: {len(html)}")

        if resp.status == 200 and len(html) > 500:
            # Check for blocking signals
            if "登录" in html[:1000] and len(html) < 2000:
                print("  BLOCKED: Login wall (short page)")
            elif "captcha" in html.lower():
                print("  BLOCKED: CAPTCHA")
            elif "安全验证" in html:
                print("  BLOCKED: Security check")
            else:
                # Try to find search results in the HTML
                # Zhihu search results are in various formats
                titles_found = []
                # Look for common title patterns
                for pattern in [
                    r'"title":"([^"]+)"',
                    r'<span class="Highlight">([^<]+)</span>',
                    r'<em>([^<]+)</em>',
                    r'<a[^>]*data-za-detail-view[^>]*>([^<]+)</a>',
                ]:
                    matches = re.findall(pattern, html)
                    if matches:
                        titles_found.extend(matches)

                # Also look for Content-item or SearchResult patterns
                items = re.findall(r'<div[^>]*class="[^"]*List-item[^"]*"[^>]*>', html)
                cards = re.findall(r'<div[^>]*class="[^"]*Card[^"]*"[^>]*>', html)

                print(f"  Title patterns found: {len(titles_found)}")
                print(f"  List items: {len(items)}")
                print(f"  Cards: {len(cards)}")

                # Show some titles
                unique_titles = list(set(t for t in titles_found if len(t) > 10))
                for t in unique_titles[:5]:
                    print(f"  - {t[:100]}")

                if not unique_titles:
                    # Show first 500 chars of body content
                    body_start = html.find("<body")
                    if body_start > 0:
                        snippet = re.sub(r'<[^>]+>', ' ', html[body_start:body_start+1000])
                        snippet = re.sub(r'\s+', ' ', snippet)
                        print(f"  Body snippet: {snippet[:300]}")
        else:
            print(f"  Unexpected response: {html[:200]}")
    except Exception as e:
        print(f"[{kw}] ERROR: {e}")
