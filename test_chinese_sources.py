"""Test Chinese cross-border e-commerce news sources for scrapability."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
kw = "temu 跨境电商"

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8", errors="replace"), resp.geturl()

def try_search(site_name, url, search_selectors=None, title_selectors=None):
    """Try to search and extract results. Returns (success, result_count, sample_titles)."""
    result = {"name": site_name, "url": url, "status": "UNKNOWN", "count": 0, "samples": [], "error": ""}
    try:
        html, final_url = fetch(url, 15)
        soup = BeautifulSoup(html, "lxml")

        # Check for anti-bot
        if any(kw in html[:2000] for kw in ["验证码", "网络不给力", "稍后重试", "Access Denied", "403", "blocked"]):
            result["status"] = "ANTIBOT"
            result["error"] = "Anti-bot triggered"
            return result

        # Try search result selectors
        if search_selectors:
            for sel in search_selectors:
                items = soup.select(sel)
                if len(items) >= 2:
                    break

        # Try title/headline selectors
        if not items and title_selectors:
            for sel in title_selectors:
                items = soup.select(sel)
                if len(items) >= 2:
                    break

        # Generic fallback: look for article links with substantial text
        if not items:
            all_a = soup.select("a[href]")
            items = [a for a in all_a if len(a.get_text(strip=True)) > 15][:20]

        titles = []
        for item in items[:10]:
            if item.name == "a":
                t = item.get_text(strip=True)
                u = item.get("href", "")
            else:
                a = item.select_one("a")
                t = a.get_text(strip=True) if a else item.get_text(strip=True)
                u = a.get("href", "") if a else ""
            if len(t) > 8:
                titles.append((t[:80], u[:120]))

        if titles:
            result["status"] = "SUCCESS"
            result["count"] = len(titles)
            result["samples"] = titles[:5]
        elif len(html) > 5000:
            result["status"] = "EMPTY_HTML"
            result["error"] = f"HTML {len(html)} chars but no article links found"
        else:
            result["status"] = "EMPTY_HTML"
            result["error"] = f"Short HTML: {len(html)} chars"

        return result
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:100]
        return result

# ═══════════════════════════════════════
# Test all Chinese cross-border sources
# ═══════════════════════════════════════

tests = [
    # === 雨果跨境 ===
    ("雨果跨境-搜索", {
        "url": f"https://www.cifnews.com/search?keyword={urllib.request.quote(kw)}",
        "search_selectors": ["div.article-item", "div.search-result", "div.news-list li", "div.list-item"],
        "title_selectors": ["h2 a", "h3 a", ".title a", "a[href*='/article/']"],
    }),

    # === 雨果跨境 API (they might have a JSON API) ===
    ("雨果跨境-API尝试", {
        "url": f"https://www.cifnews.com/api/search?keyword={urllib.request.quote(kw)}&page=1&size=10",
    }),
    ("雨果跨境-API-v2", {
        "url": f"https://www.cifnews.com/api/article/search?keyword={urllib.request.quote(kw)}&pageSize=10",
    }),

    # === 亿邦动力 ===
    ("亿邦动力", {
        "url": f"https://www.ebrun.com/search?word={urllib.request.quote(kw)}",
        "search_selectors": ["div.search-result li", "div.article-list li", "div.news-item"],
        "title_selectors": ["h2 a", "h3 a", ".title a"],
    }),

    # === 跨境知道 ===
    ("跨境知道", {
        "url": f"https://www.kjzd.com/search?keyword={urllib.request.quote(kw)}",
        "search_selectors": ["div.search-result", "div.list-item", "div.article-item"],
        "title_selectors": ["h2 a", "h3 a", ".title a"],
    }),

    # === 卖家之家 ===
    ("卖家之家", {
        "url": f"https://www.mjzj.com/search?keyword={urllib.request.quote(kw)}",
        "search_selectors": ["div.list-item", "div.news-item", "div.article"],
        "title_selectors": ["h2 a", "h3 a", ".title a"],
    }),

    # === 白鲸出海 ===
    ("白鲸出海", {
        "url": f"https://www.baijing.cn/search?keyword={urllib.request.quote(kw)}",
        "search_selectors": ["div.search-list li", "div.article-item", "div.news-item"],
        "title_selectors": ["h2 a", "h3 a", ".title a"],
    }),

    # === 跨境电商-中国日报 ===
    ("中国日报-跨境", {
        "url": f"https://cn.chinadaily.com.cn/search?query={urllib.request.quote(kw)}",
        "search_selectors": ["div.search_result li", "div.result-list li"],
        "title_selectors": ["h3 a", ".title a"],
    }),

    # === 36氪 (try different endpoint) ===
    ("36氪-v2", {
        "url": f"https://www.36kr.com/search/articles/{urllib.request.quote(kw)}",
        "search_selectors": ["div.article-item", "div.search-result"],
        "title_selectors": ["a.article-item-title", "h3 a"],
    }),

    # === 搜狗微信 (what does it return now) ===
    ("搜狗微信", {
        "url": f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&ie=utf8",
        "search_selectors": ["ul.news-list li", "ul.news-list2 li"],
        "title_selectors": ["h3 a", ".txt-box h3 a"],
    }),

    # === 网易新闻搜索 ===
    ("网易新闻", {
        "url": f"https://news.163.com/search?keyword={urllib.request.quote(kw)}",
        "search_selectors": ["div.search_result div.result", "div.news-item"],
        "title_selectors": ["h2 a", "h3 a"],
    }),

    # === 搜狐新闻 ===
    ("搜狐新闻", {
        "url": f"https://search.sohu.com/?keyword={urllib.request.quote(kw)}&type=news",
        "search_selectors": ["div.result", "div.news-item", "div.search-list li"],
        "title_selectors": ["h4 a", "h3 a", ".title a"],
    }),

    # === 新浪新闻 ===
    ("新浪新闻", {
        "url": f"https://search.sina.com.cn/news?q={urllib.request.quote(kw)}&c=news",
        "search_selectors": ["div.box-result", "div.r-info", "div.result"],
        "title_selectors": ["h2 a", "h3 a"],
    }),

    # === 腾讯新闻 ===
    ("腾讯新闻", {
        "url": f"https://news.qq.com/search?query={urllib.request.quote(kw)}",
        "search_selectors": ["div.search-result li", "div.list-item"],
        "title_selectors": ["h3 a", ".title a"],
    }),
]

print("=" * 70)
print("TESTING CHINESE NEWS SOURCES")
print("=" * 70)

results_by_status = {"SUCCESS": [], "EMPTY_HTML": [], "ANTIBOT": [], "ERROR": [], "UNKNOWN": []}

for name, config in tests:
    print(f"\n--- {name} ---")
    r = try_search(name, config.get("url", ""),
                   config.get("search_selectors"),
                   config.get("title_selectors"))
    results_by_status.setdefault(r["status"], []).append(r)

    print(f"  Status: {r['status']}")
    if r["status"] == "SUCCESS":
        print(f"  Found: {r['count']} results")
        for i, (title, url) in enumerate(r["samples"][:3]):
            print(f"  [{i}] {title}")
            print(f"      url: {url}")
    elif r["error"]:
        print(f"  Error: {r['error']}")

# ═══════════════════════════════════════
# Summary
# ═══════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n✓ SUCCESS ({len(results_by_status['SUCCESS'])}):")
for r in results_by_status['SUCCESS']:
    print(f"    {r['name']:20s} → {r['count']} results")

print(f"\n✗ EMPTY/JS-RENDERED ({len(results_by_status['EMPTY_HTML'])}):")
for r in results_by_status['EMPTY_HTML']:
    print(f"    {r['name']:20s} → {r['error'][:80]}")

print(f"\n🚫 ANTIBOT ({len(results_by_status['ANTIBOT'])}):")
for r in results_by_status['ANTIBOT']:
    print(f"    {r['name']:20s} → {r['error']}")

print(f"\n❌ ERROR ({len(results_by_status['ERROR'])}):")
for r in results_by_status['ERROR']:
    print(f"    {r['name']:20s} → {r['error'][:80]}")

# Quick: test if Cifnews has a sitemap or RSS
print("\n\n=== Bonus: RSS/Sitemap checks ===")
for name, url in [
    ("雨果跨境 RSS", "https://www.cifnews.com/rss"),
    ("雨果跨境 RSS2", "https://www.cifnews.com/feed"),
    ("亿邦动力 RSS", "https://www.ebrun.com/feed"),
    ("36氪 RSS", "https://36kr.com/feed"),
    ("白鲸出海 Sitemap", "https://www.baijing.cn/sitemap.xml"),
]:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = resp.read().decode("utf-8", errors="replace")
        if data.strip().startswith("<?xml") or data.strip().startswith("<rss"):
            print(f"  {name}: RSS/XML found! {len(data)} chars")
            soup = BeautifulSoup(data, "xml")
            items = soup.select("item") or soup.select("url")
            print(f"    Items: {len(items)}")
            for item in items[:3]:
                t = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
                if t:
                    print(f"    - {t[:80]}")
        elif len(data) > 1000:
            print(f"  {name}: Not RSS (length {len(data)}, starts: {data[:80]})")
        else:
            print(f"  {name}: Empty/short ({len(data)} chars)")
    except Exception as e:
        print(f"  {name}: Error: {str(e)[:60]}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_chinese.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_chinese.py 2>&1')
output = stdout.read().decode('utf-8', errors='replace')
with open('chinese_sources_result.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Output saved to chinese_sources_result.txt")
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
