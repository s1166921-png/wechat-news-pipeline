"""Final round: fix Cifnews RSS + Ebrun date extraction + integration plan."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json, time
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
kw = "temu 跨境电商"

def fetch(url, timeout=12, extra_headers=None):
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if extra_headers:
        h.update(extra_headers)
    req = urllib.request.Request(url, headers=h)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8", errors="replace"), resp.geturl()

# ═══════════════════════════════════════
# 1. Cifnews RSS - try multiple approaches
# ═══════════════════════════════════════
print("=" * 60)
print("1. CIFNEWS RSS - MULTIPLE APPROACHES")
print("=" * 60)

rss_attempts = [
    ("YuGuo.xml (Accept: xml)", "https://www.cifnews.com/xmlconfig/YuGuo.xml",
     {"Accept": "application/rss+xml, application/xml, text/xml"}),
    ("YuGuo.xml (Accept: */*)", "https://www.cifnews.com/xmlconfig/YuGuo.xml",
     {"Accept": "*/*"}),
    ("index.xml", "https://www.cifnews.com/xmlconfig/index.xml", {}),
    ("rss.xml", "https://www.cifnews.com/xmlconfig/rss.xml", {}),
    ("/feed", "https://www.cifnews.com/feed", {}),
    ("/api/rss", "https://www.cifnews.com/api/rss", {}),
    # Try with referer
    ("YuGuo.xml (with Referer)", "https://www.cifnews.com/xmlconfig/YuGuo.xml",
     {"Referer": "https://www.cifnews.com/rss", "Accept": "application/xml,text/xml"}),
]

for name, url, extra_h in rss_attempts:
    try:
        data, final_url = fetch(url, 10, extra_h)
        if data.strip().startswith("<?xml") or data.strip().startswith("<rss"):
            soup = BeautifulSoup(data, "xml")
            items = soup.select("item")
            print(f"  {name}: ✓ RSS! {len(items)} items")
            for item in items[:3]:
                t = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
                l = (item.select_one("link") or "").get_text(strip=True) if item.select_one("link") else ""
                d = (item.select_one("pubDate") or "").get_text(strip=True) if item.select_one("pubDate") else ""
                print(f"    [{d[:25]}] {t[:80]}")
        elif len(data) < 200:
            print(f"  {name}: Short ({len(data)}): {data[:150]}")
        else:
            print(f"  {name}: Not RSS ({len(data)} chars)")
    except Exception as e:
        print(f"  {name}: Error: {str(e)[:60]}")

# ═══════════════════════════════════════
# 2. Ebrun - extract dates from search results
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("2. EBRUN DATE EXTRACTION")
print("=" * 60)

try:
    url = f"https://m.ebrun.com/search?keyword={urllib.request.quote(kw)}"
    data, _ = fetch(url)
    soup = BeautifulSoup(data, "lxml")

    # Find the search result container and examine structure
    # Look for date patterns near article links
    body = soup.select_one("body")
    if body:
        # Look for date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{2}-\d{2}\s+\d{2}:\d{2}',
            r'\d+[天小时分]前',
            r'\d+月\d+日',
        ]
        for pat in date_patterns:
            matches = re.findall(pat, body.get_text() if body else "")
            if matches:
                print(f"  Dates matching '{pat}': {matches[:10]}")

    # Also check individual article items for date spans
    # Look at the HTML around article links
    for a in soup.select("a[href*='ebrun.com/']")[:3]:
        parent_text = a.parent.get_text(strip=True) if a.parent else ""
        # Look for date in parent
        date_in_parent = re.findall(r'(\d{4}-\d{2}-\d{2})', parent_text)
        if date_in_parent:
            print(f"  Date near '{a.get_text(strip=True)[:50]}...': {date_in_parent}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 3. Ebrun - check article page for date
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("3. EBRUN ARTICLE DATE (from detail page)")
print("=" * 60)

try:
    for test_url in [
        "https://m.ebrun.com/688435.html",
        "https://m.ebrun.com/687154.html",
    ]:
        data, _ = fetch(test_url)
        soup = BeautifulSoup(data, "lxml")
        # Find date in meta, time element, or text
        for sel in ["time", "span.date", "span.time", ".article-date", ".article-time", ".info-time"]:
            el = soup.select_one(sel)
            if el:
                print(f"  {test_url[-15:]}: {sel} = {el.get_text(strip=True)[:50]}")

        # Look for date in text near title
        for pat in [r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', r'\d{4}-\d{2}-\d{2}',
                     r'\d{4}年\d{2}月\d{2}日', r'\d+天前']:
            matches = re.findall(pat, data[:5000])
            if matches:
                print(f"  {test_url[-15:]}: '{pat}' = {matches[:5]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 4. Test: can we use 360 News to search within cifnews.com?
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("4. 360 NEWS SITE: CIFNEWS")
print("=" * 60)

try:
    url = f"https://news.so.com/ns?q=site:cifnews.com+{urllib.request.quote(kw)}&src=srp&pn=0&rn=10"
    data, _ = fetch(url)
    soup = BeautifulSoup(data, "lxml")
    for sel in ["ul.result li", "div.result", "div.res-list li", "li"]:
        items = soup.select(sel)
        if len(items) >= 2:
            titled = sum(1 for i in items if i.select_one("a") and len(i.select_one("a").get_text(strip=True)) > 10)
            if titled >= 2:
                print(f"  '{sel}': {len(items)} items, {titled} with titles")
                for item in items[:5]:
                    a = item.select_one("a")
                    if a and len(a.get_text(strip=True)) > 10:
                        print(f"    {a.get_text(strip=True)[:80]}")
                        print(f"    → {a.get('href','')[:120]}")
                break
    else:
        print("  No results found")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 5. Ebrun - test multiple keywords to verify search quality
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("5. EBRUN MULTI-KEYWORD TEST")
print("=" * 60)

for test_kw in ["亚马逊 运营", "TikTok Shop 美国", "独立站 出海", "SHEIN 上市"]:
    try:
        url = f"https://m.ebrun.com/search?keyword={urllib.request.quote(test_kw)}"
        data, _ = fetch(url, 8)
        soup = BeautifulSoup(data, "lxml")
        links = [a for a in soup.select("a[href*='ebrun.com/']")
                 if len(a.get_text(strip=True)) > 15
                 and not a.get_text(strip=True).startswith("{{")]
        print(f"  '{test_kw}': {len(links)} results")
        for a in links[:3]:
            print(f"    {a.get_text(strip=True)[:80]}")
    except Exception as e:
        print(f"  '{test_kw}': Error: {str(e)[:50]}")

# ═══════════════════════════════════════
# 6. Summary: what we can integrate
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("6. INTEGRATION PLAN")
print("=" * 60)
print("""
✓ CAN INTEGRATE:
  [1] 亿邦动力 (m.ebrun.com)
      - Search: m.ebrun.com/search?keyword=XXX
      - Articles: m.ebrun.com/{id}.html (full text accessible)
      - E-commerce focused, high relevance
      - Need to solve: date extraction from article pages

  [2] 36Kr RSS (36kr.com/feed)
      - 30 fresh items per fetch
      - General tech/business, some cross-border coverage
      - Date in RSS pubDate field
      - Cannot search by keyword (must filter from feed)

  [3] 雨果跨境 Homepage (cifnews.com)
      - 55 articles on homepage
      - RSS feed blocked (405)
      - JS-rendered search page
      - Can scrape homepage for latest articles

✗ CANNOT:
  - 雨果跨境 RSS (405 Not Allowed)
  - Baidu News (ANTIBOT)
  - Bing News (JS-rendered)
  - Most Chinese portals (JS-rendered)

CURRENT ENGINES: 360 News + Sogou News + Bing Web + Google News
NEW ENGINES TO ADD: 亿邦动力 + 36Kr RSS + 雨果跨境首页
""")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_chinese5.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_chinese5.py 2>&1')
output = stdout.read().decode('utf-8', errors='replace')
with open('chinese_sources_result5.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Saved to chinese_sources_result5.txt")
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
