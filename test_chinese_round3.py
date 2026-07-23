"""Test winners: 亿邦动力 mobile search, 雨果跨境 alternatives, more RSS."""
import paramiko

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
    return resp.read().decode("utf-8", errors="replace")

# ═══════════════════════════════════════
# 1. 亿邦动力 Mobile - deep explore
# ═══════════════════════════════════════
print("=" * 60)
print("1. EBRUN MOBILE DEEP")
print("=" * 60)

# m.ebrun.com homepage - extract article list structure
try:
    html = fetch("https://m.ebrun.com/")
    soup = BeautifulSoup(html, "lxml")

    # Find article links with titles
    article_links = []
    for a in soup.select("a[href]"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if len(title) > 12 and any(p in href.lower() for p in ["/article/", "/news/", "/detail/", "/p/", "html"]):
            article_links.append((title, href))

    print(f"  Article links found: {len(article_links)}")
    for title, href in article_links[:10]:
        print(f"    {title[:80]}")
        print(f"    → {href[:120]}")

    # Try search URL patterns
    print("\n  Trying search patterns...")
    search_patterns = [
        f"https://m.ebrun.com/search?keyword={urllib.request.quote(kw)}",
        f"https://m.ebrun.com/search?q={urllib.request.quote(kw)}",
        f"https://m.ebrun.com/search/{urllib.request.quote(kw)}",
        f"https://m.ebrun.com/so?q={urllib.request.quote(kw)}",
    ]
    for url in search_patterns:
        try:
            h = fetch(url, 8)
            s = BeautifulSoup(h, "lxml")
            links = [a for a in s.select("a[href]") if len(a.get_text(strip=True)) > 10]
            print(f"    {url[:70]}: {len(links)} links")
            for a in links[:3]:
                print(f"      {a.get_text(strip=True)[:70]}")
        except Exception as e:
            print(f"    {url[:70]}: {str(e)[:50]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 2. 雨果跨境 - try search via Google/Bing site: operator
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("2. CIFNEWS VIA SEARCH ENGINES")
print("=" * 60)

# Use 360 search with site:cifnews.com
try:
    url = f"https://news.so.com/ns?q=site:cifnews.com+{urllib.request.quote(kw)}&src=srp"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("ul.result li, div.result, div.res-list li")
    print(f"  360 site:cifnews.com results: {len(items)}")
    for item in items[:5]:
        a = item.select_one("a")
        if a:
            t = a.get_text(strip=True)
            u = a.get("href", "")
            if len(t) > 8:
                print(f"    {t[:80]}")
                print(f"    → {u[:130]}")
except Exception as e:
    print(f"  Error: {e}")

# Use Sogou with site:cifnews.com
print()
try:
    url = f"https://news.sogou.com/news?query=site:cifnews.com+{urllib.request.quote(kw)}"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("div.result, div.news-item, ul.news-list li")
    print(f"  Sogou site:cifnews.com results: {len(items)}")
    for item in items[:5]:
        a = item.select_one("a") or item.select_one("h3 a")
        if a:
            t = a.get_text(strip=True)
            u = a.get("href", "")
            if len(t) > 8:
                print(f"    {t[:80]}")
                print(f"    → {u[:130]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 3. 雨果跨境 - try the RSS page scraping
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("3. CIFNEWS RSS PAGE PARSE")
print("=" * 60)
try:
    html = fetch("https://www.cifnews.com/rss")
    soup = BeautifulSoup(html, "lxml")
    # This is an HTML page listing RSS categories
    # Extract actual RSS feed URLs
    rss_links = soup.select("a[href*='rss'], a[href*='feed'], a[href*='xml']")
    print(f"  RSS-related links: {len(rss_links)}")
    for a in rss_links[:10]:
        print(f"    {a.get_text(strip=True)[:60]} → {a.get('href','')[:100]}")

    # Also look for category feed links
    feed_links = re.findall(r'["\']((?:https?:)?//(?:www\.)?cifnews\.com/[^"\'\s]*(?:rss|feed|xml)[^"\'\s]*)["\']', html)
    if feed_links:
        print(f"  Feed URLs from HTML: {feed_links[:10]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 4. 36Kr - search via RSS content filter
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("4. 36KR SEARCH VIA RSS (keyword filter)")
print("=" * 60)
try:
    html = fetch("https://36kr.com/feed")
    soup = BeautifulSoup(html, "xml")
    items = soup.select("item")
    # Filter items where title or description contains keyword parts
    kw_parts = ["temu", "跨境", "电商", "出海", "Temu", "TEMU"]
    matched = []
    for item in items:
        title = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
        desc = (item.select_one("description") or "").get_text(strip=True) if item.select_one("description") else ""
        combined = title + " " + desc
        if any(p in combined for p in kw_parts):
            link = (item.select_one("link") or "").get_text(strip=True) if item.select_one("link") else ""
            pubdate = (item.select_one("pubDate") or "").get_text(strip=True) if item.select_one("pubDate") else ""
            matched.append((title, link, pubdate))

    print(f"  Matched {len(matched)}/{len(items)} items for '{kw}'")
    for title, link, date in matched[:8]:
        print(f"    [{date[:25]}] {title[:80]}")
        print(f"    → {link[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 5. Try some RSS feeds directly
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("5. MORE RSS FEEDS")
print("=" * 60)

rss_tests = [
    ("亿邦动力 RSS", "https://www.ebrun.com/feed"),
    ("亿邦动力 RSS2", "https://m.ebrun.com/feed"),
    ("凤凰网科技 RSS", "https://tech.ifeng.com/rss.xml"),
    ("澎湃新闻 RSS", "https://www.thepaper.cn/rss.xml"),
    ("界面新闻 RSS", "https://www.jiemian.com/rss"),
    ("品玩 RSS", "https://www.pingwest.com/feed"),
    ("环球网 RSS", "https://www.huanqiu.com/rss"),
    ("雨果跨境 sitemap", "https://www.cifnews.com/sitemap.xml"),
    ("雨果跨境 category feeds", "https://www.cifnews.com/rss/1"),
]

for name, url in rss_tests:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=8, context=ctx)
        data = resp.read().decode("utf-8", errors="replace")
        if data.strip().startswith("<?xml") or data.strip().startswith("<rss"):
            soup = BeautifulSoup(data, "xml")
            items = soup.select("item") or soup.select("entry")
            print(f"  {name}: ✓ RSS/XML, {len(items)} items")
            for item in items[:3]:
                t = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
                d = (item.select_one("pubDate") or item.select_one("published") or "").get_text(strip=True) if (item.select_one("pubDate") or item.select_one("published")) else ""
                print(f"    [{d[:25]}] {t[:80]}")
        elif "rss" in data[:200].lower() or "feed" in data[:200].lower():
            print(f"  {name}: ? Possible feed, {len(data)} chars")
            print(f"    Starts: {data[:150]}")
        else:
            print(f"  {name}: ✗ Not feed ({len(data)} chars, starts: {data[:60]})")
    except Exception as e:
        print(f"  {name}: Error: {str(e)[:60]}")

# ═══════════════════════════════════════
# 6. Try Bing/ChatGPT to find better sources
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("6. BING SITE: SEARCH FOR CROSS-BORDER NEWS")
print("=" * 60)

# Use Bing to search within known cross-border sites
cross_border_sites = [
    "cifnews.com",
    "ebrun.com",
    "kjzd.com",
    "baijing.cn",
    "dny123.com",
    "amz123.com",
]

for site in cross_border_sites:
    try:
        url = f"https://www.bing.com/search?q=site:{site}+{urllib.request.quote(kw)}&count=5"
        html = fetch(url, 10)
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("li.b_algo")
        print(f"  site:{site}: {len(items)} results")
        for li in items[:3]:
            a = li.select_one("h2 a") or li.select_one("a")
            if a:
                print(f"    {a.get_text(strip=True)[:70]}")
    except Exception as e:
        print(f"  site:{site}: Error: {str(e)[:50]}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_chinese3.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_chinese3.py 2>&1')
output = stdout.read().decode('utf-8', errors='replace')
with open('chinese_sources_result3.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Saved to chinese_sources_result3.txt")
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
