"""Test Bing News search (not web) + finalize engine strategy."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# === Part 1: Bing News HTML page ===
print("=== Bing News (HTML page) ===")
bing_news_urls = [
    f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&setlang=zh-Hans&cc=cn",
    f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&setmkt=zh-CN",
    f"https://cn.bing.com/news/search?q={urllib.request.quote(kw)}",
]
for url in bing_news_urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        # Look for news cards
        for sel in [".news-card", "article", ".newsitem", "[class*=newsCard]", "a.title"]:
            items = soup.select(sel)
            if len(items) >= 2:
                print(f"  URL: {url[:80]}")
                print(f"  Selector '{sel}': {len(items)} items")
                for item in items[:4]:
                    a = item.select_one("a") if item.name != "a" else item
                    t = (a.get_text(strip=True) if a else item.get_text(strip=True))[:70]
                    u = (a.get("href", "") if a else "")
                    print(f"    {t}")
                    if u: print(f"    → {u[:100]}")
                break
        else:
            # Check for ANY article-like content
            links = [a for a in soup.select("a[href]") if len(a.get_text(strip=True)) > 20]
            print(f"  URL: {url[:80]} → {len(links)} article-like links")
            for a in links[:3]:
                print(f"    {a.get_text(strip=True)[:70]}")
    except Exception as e:
        print(f"  {url[:60]}: Error: {str(e)[:60]}")

# === Part 2: Bing News RSS v2 ===
print("\n=== Bing News RSS (v2) ===")
rss_urls = [
    f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&format=RSS&setmkt=zh-CN",
    f"https://api.bing.com/news/search?q={urllib.request.quote(kw)}&mkt=zh-CN",
]
for url in rss_urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ctx)
        data = resp.read().decode("utf-8", errors="replace")
        if data.strip().startswith("<?xml") or data.strip().startswith("<rss"):
            print(f"  RSS feed found! Length: {len(data)}")
            soup = BeautifulSoup(data, "xml")
            items = soup.select("item")
            print(f"  Items: {len(items)}")
            for item in items[:4]:
                t = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
                print(f"    {t[:70]}")
        elif "{" in data[:5]:
            print(f"  JSON response: {len(data)} chars")
            d = json.loads(data)
            if "value" in d:
                print(f"  News articles: {len(d['value'])}")
                for art in d.get("value", [])[:4]:
                    print(f"    {art.get('name','')[:70]}")
        else:
            print(f"  Unknown format: {data[:200]}")
    except Exception as e:
        print(f"  {url[:60]}: Error: {str(e)[:80]}")

# === Part 3: Google News (China-friendly) ===
print("\n=== Google News RSS ===")
gn_urls = [
    f"https://news.google.com/rss/search?q={urllib.request.quote(kw)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    f"https://news.google.com/rss/search?q={urllib.request.quote(kw)}&hl=en",
]
for url in gn_urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ctx)
        data = resp.read().decode("utf-8", errors="replace")
        if data.strip().startswith("<?xml") or data.strip().startswith("<rss"):
            soup = BeautifulSoup(data, "xml")
            items = soup.select("item")
            print(f"  RSS items: {len(items)} url={url[:80]}")
            for item in items[:4]:
                t = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
                d = (item.select_one("pubDate") or "").get_text(strip=True) if item.select_one("pubDate") else ""
                print(f"    [{d[:11]}] {t[:70]}")
        else:
            print(f"  Not RSS: {data[:100]}")
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")

# === Part 4: Complete strategy summary ===
print("\n" + "="*60)
print("ENGINE STRATEGY SUMMARY")
print("="*60)
print("""
Current engines:
  1. 360 News        ✓ Working, fresh Chinese news
  2. Sogou News      ✓ Working, fresh Chinese news
  3. Bing Web Search ✗ Returns homepage descriptions, not articles
  4. Google News RSS ✓ Sometimes works (timed out often)

Issues to fix:
  A. 360kuai.com aggregator pages → Add domain filter
  B. Bing web search → Replace with proper news search or remove
  C. Need more Chinese news sources

Recommended changes:
  1. Add URL quality filter: block 360kuai.com, video sites, Q&A, wiki
  2. Keep Bing only for non-Chinese queries (site: operator)
  3. Primary: 360 News + Sogou News (both produce fresh Chinese articles)
""")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_bing_final.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_bing_final.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
