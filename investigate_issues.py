"""Investigate: 1) video links, 2) Bing quality, 3) new engine feasibility."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

kw = "temu 跨境电商"

# === Part 1: Check current results for video URLs ===
print("=== Part 1: Check for video URLs in current results ===")
import urllib.request as ur
req = ur.Request("http://127.0.0.1:8888/api/search",
    data=json.dumps({"keyword": kw, "max_results": 15}).encode(),
    headers={"Content-Type": "application/json"})
resp = ur.urlopen(req, timeout=30)
data = json.loads(resp.read().decode())
for i, r in enumerate(data.get("results", [])[:15]):
    url = r.get("url", "")
    title = r.get("title", "")
    st = r.get("source_type", "")
    # Detect video/forum/low-quality URLs
    flags = []
    if "/video/" in url or "/v/" in url: flags.append("VIDEO_PATH")
    if "video" in url.lower() and "/video" not in url: flags.append("VIDEO_WORD")
    if any(d in url for d in ["bilibili.com", "youtube.com", "youku.com", "iqiyi.com", "v.qq.com"]): flags.append("VIDEO_SITE")
    if any(d in url for d in ["zhidao.baidu.com", "wenwen.sogou.com", "zhidao.", "ask."]): flags.append("Q&A")
    if any(d in url for d in ["baike.baidu.com", "baike.sogou.com", "wikipedia.org", "wiki."]): flags.append("WIKI")
    if flags:
        print(f"  [{i}] FLAGS={flags} | type={st}")
        print(f"       url={url[:120]}")
        print(f"       title={title[:80]}")

# === Part 2: Test Bing News (not web search) ===
print("\n=== Part 2: Bing News search ===")
bing_news_url = f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&format=rss"
try:
    req2 = urllib.request.Request(bing_news_url, headers=headers)
    resp2 = urllib.request.urlopen(req2, timeout=10, context=ctx)
    html2 = resp2.read().decode("utf-8", errors="replace")
    # Bing news RSS
    soup2 = BeautifulSoup(html2, "xml" if html2.strip().startswith("<?xml") else "lxml")
    items = soup2.select("item") or soup2.select("entry")
    if not items:
        items = soup2.select(".news-card, [class*=news]")
    print(f"  Bing News RSS items: {len(items)}")
    for item in items[:5]:
        title_el = item.select_one("title")
        link_el = item.select_one("link")
        pubdate_el = item.select_one("pubDate")
        t = title_el.get_text(strip=True) if title_el else item.get_text(strip=True)[:80]
        u = link_el.get_text(strip=True) if link_el else (link_el.get("href","") if link_el else "")
        d = pubdate_el.get_text(strip=True) if pubdate_el else ""
        print(f"    {t[:70]}")
        print(f"    date={d[:20]} url={u[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# Also try Bing News HTML page
bing_news_html = f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&qft=interval%3d%227%22"
try:
    req3 = urllib.request.Request(bing_news_html, headers=headers)
    resp3 = urllib.request.urlopen(req3, timeout=10, context=ctx)
    html3 = resp3.read().decode("utf-8", errors="replace")
    soup3 = BeautifulSoup(html3, "lxml")
    items3 = soup3.select(".news-card, article, [class*=newsCard]")
    if not items3:
        items3 = soup3.select("a[href*='http']")
        items3 = [a for a in items3 if len(a.get_text(strip=True)) > 15][:10]
    print(f"\n  Bing News HTML items: {len(items3)}")
    for item in items3[:5]:
        t = item.get_text(strip=True)[:80]
        u = item.get("href", "")
        print(f"    {t}")
        print(f"    url={u[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 3: Test Baidu News ===
print("\n=== Part 3: Baidu News search ===")
baidu_url = f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=20&ie=utf-8&bt=0&et=0"
try:
    req4 = urllib.request.Request(baidu_url, headers=headers)
    resp4 = urllib.request.urlopen(req4, timeout=10, context=ctx)
    html4 = resp4.read().decode("utf-8", errors="replace")
    soup4 = BeautifulSoup(html4, "lxml")
    # Baidu news result selectors
    for sel in [".result", ".news-item", "[class*=result]"]:
        items4 = soup4.select(sel)
        if len(items4) > 3:
            print(f"  Selector '{sel}': {len(items4)} results")
            break
    if len(items4) <= 3:
        items4 = soup4.select("h3 a")[:10]
    print(f"  Items: {len(items4)}")
    for item in items4[:5]:
        a = item.select_one("a") or item
        t = a.get_text(strip=True)[:80]
        u = a.get("href", "")
        print(f"    {t}")
        print(f"    url={u[:120]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 4: Test Toutiao search ===
print("\n=== Part 4: Toutiao search ===")
toutiao_url = f"https://so.toutiao.com/search?dvpf=pc&source=input&keyword={urllib.request.quote(kw)}"
try:
    req5 = urllib.request.Request(toutiao_url, headers=headers)
    resp5 = urllib.request.urlopen(req5, timeout=10, context=ctx)
    html5 = resp5.read().decode("utf-8", errors="replace")
    # Check if we got results
    if len(html5) > 500:
        # Look for article titles/links
        titles = re.findall(r'"title"\s*:\s*"([^"]+)"', html5)[:5]
        urls = re.findall(r'"article_url"\s*:\s*"([^"]+)"', html5)[:5]
        print(f"  JSON titles found: {len(titles)}")
        for t, u in zip(titles[:5], urls[:5]):
            print(f"    {t[:80]}")
            print(f"    url={u[:120]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 5: Bing search with site: filters for quality ===
print("\n=== Part 5: Quality filter test - known cross-border e-commerce sites ===")
quality_sites = [
    "cifnews.com", "36kr.com", "ebrun.com", "dny123.com",
    "kuajingyan.com", "amz123.com",
]
for site in quality_sites:
    try:
        url = f"https://www.bing.com/search?q=site:{site}+{urllib.request.quote(kw)}&setlang=zh-cn&count=3"
        req6 = urllib.request.Request(url, headers=headers)
        resp6 = urllib.request.urlopen(req6, timeout=8, context=ctx)
        html6 = resp6.read().decode("utf-8", errors="replace")
        soup6 = BeautifulSoup(html6, "lxml")
        items6 = soup6.select("li.b_algo")
        print(f"  site:{site}: {len(items6)} results")
        for item in items6[:2]:
            h2 = item.select_one("h2")
            t = h2.get_text(strip=True) if h2 else "?"
            print(f"    {t[:70]}")
    except Exception as e:
        print(f"  site:{site}: Error: {str(e)[:50]}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/investigate.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/investigate.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
