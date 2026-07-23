"""Deep dive: Cifnews HTML structure + 36Kr RSS + more sources."""
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
# 1. Cifnews - look for JSON data or API endpoints
# ═══════════════════════════════════════
print("=" * 60)
print("1. CIFNEWS DEEP DIVE")
print("=" * 60)

# Cifnews search page - extract any JSON/API data
try:
    html = fetch(f"https://www.cifnews.com/search?keyword={urllib.request.quote(kw)}")
    soup = BeautifulSoup(html, "lxml")

    # Look for __NEXT_DATA__ or similar
    for script in soup.select("script"):
        txt = script.string or ""
        if "window.__" in txt or "list" in txt.lower():
            # print first 500 chars of each script
            preview = txt.strip()[:200]
            if len(preview) > 30:
                print(f"  Script [{len(txt)} chars]: {preview}...")

    # Check for API endpoints in JS
    api_urls = re.findall(r'["\'](/api/[^"\'\s]{3,80})["\']', html)
    if api_urls:
        print(f"  API endpoints found: {api_urls[:10]}")
    else:
        print("  No API endpoints found in HTML")

    # Check for article links
    article_patterns = re.findall(r'["\']((?:https?:)?//(?:www\.)?cifnews\.com/article/\d+[^"\'\s]*)["\']', html)
    if article_patterns:
        print(f"  Article URLs in HTML: {len(article_patterns)}")
        for u in article_patterns[:5]:
            print(f"    {u}")

    # Try cifnews category/news listing pages
    print("\n  Trying listing pages...")
    for page_url in [
        "https://www.cifnews.com/news",
        "https://www.cifnews.com/article",
        "https://www.cifnews.com/category/1",
        "https://www.cifnews.com/",
    ]:
        try:
            h = fetch(page_url)
            s = BeautifulSoup(h, "lxml")
            links = [a for a in s.select("a[href*='/article/']") if len(a.get_text(strip=True)) > 10]
            print(f"    {page_url}: {len(links)} article links")
            for a in links[:3]:
                print(f"      {a.get_text(strip=True)[:70]}")
        except Exception as e:
            print(f"    {page_url}: Error: {e}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 2. 36Kr RSS - full extraction
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("2. 36KR RSS FULL EXTRACTION")
print("=" * 60)
try:
    html = fetch("https://36kr.com/feed")
    soup = BeautifulSoup(html, "xml")
    items = soup.select("item")
    print(f"  Total items: {len(items)}")
    for i, item in enumerate(items[:15]):
        title = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
        link = (item.select_one("link") or "").get_text(strip=True) if item.select_one("link") else ""
        pubdate = (item.select_one("pubDate") or "").get_text(strip=True) if item.select_one("pubDate") else ""
        desc = (item.select_one("description") or "").get_text(strip=True)[:100] if item.select_one("description") else ""
        print(f"  [{i}] {title[:80]}")
        print(f"      date={pubdate[:30]} url={link[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 3. Check if 36Kr has a search API
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("3. 36KR SEARCH")
print("=" * 60)
try:
    # 36kr search API
    search_url = f"https://www.36kr.com/search/api?q={urllib.request.quote(kw)}&page=1&per_page=10"
    req = urllib.request.Request(search_url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=12, context=ctx)
    data = resp.read().decode("utf-8", errors="replace")
    print(f"  Response: {data[:500]}")

    # Try parsing as JSON
    try:
        j = json.loads(data)
        if "data" in j:
            items = j["data"].get("items", []) or j["data"].get("list", [])
            print(f"  JSON items: {len(items)}")
            for item in items[:5]:
                t = item.get("title", "") or item.get("post_title", "") or item.get("name", "")
                u = item.get("url", "") or item.get("link", "")
                print(f"    {str(t)[:80]}")
                print(f"    url: {str(u)[:120]}")
    except:
        pass
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 4. 亿邦动力 - try different URLs
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("4. EBRUN (亿邦动力) ALTERNATIVES")
print("=" * 60)
for url in [
    "https://www.ebrun.com/",
    "https://m.ebrun.com/",
    f"https://so.ebrun.com/search?keyword={urllib.request.quote(kw)}",
]:
    try:
        html = fetch(url)
        soup = BeautifulSoup(html, "lxml")
        links = [a for a in soup.select("a[href*='html'], a[href*='article'], a[href*='/p/'], a[href*='/news/']")
                 if len(a.get_text(strip=True)) > 10]
        print(f"  {url}: {len(links)} links")
        for a in links[:3]:
            print(f"    {a.get_text(strip=True)[:70]}")
    except Exception as e:
        print(f"  {url}: Error: {str(e)[:60]}")

# ═══════════════════════════════════════
# 5. More Chinese news sources
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("5. MORE CHINESE SOURCES")
print("=" * 60)

more_tests = [
    # 凤凰网
    ("凤凰网", f"https://search.ifeng.com/sofeng/search.action?q={urllib.request.quote(kw)}&c=1"),
    # 界面新闻
    ("界面新闻", f"https://www.jiemian.com/search?keyword={urllib.request.quote(kw)}"),
    # 澎湃新闻
    ("澎湃新闻", f"https://www.thepaper.cn/searchResult?keyword={urllib.request.quote(kw)}"),
    # 环球网
    ("环球网", f"https://search.huanqiu.com/?q={urllib.request.quote(kw)}"),
    # 虎嗅
    ("虎嗅", f"https://www.huxiu.com/search.html?key={urllib.request.quote(kw)}"),
    # 品玩
    ("品玩", f"https://www.pingwest.com/search?keyword={urllib.request.quote(kw)}"),
    # 钛媒体
    ("钛媒体", f"https://www.tmtpost.com/search?q={urllib.request.quote(kw)}"),
]

for name, url in more_tests:
    try:
        html = fetch(url, 10)
        soup = BeautifulSoup(html, "lxml")
        # Generic article link detection
        links = [a for a in soup.select("a[href]")
                 if len(a.get_text(strip=True)) > 12
                 and not a.get_text(strip=True).startswith("{{")]
        # Filter to likely article links
        article_links = [a for a in links if any(
            p in a.get("href", "").lower() for p in
            ["/article/", "/news/", "/a/", "/p/", "detail", "content", "story"]
        )]
        if not article_links:
            article_links = links[:10]  # fallback

        print(f"  {name}: {len(links)} total links, {len(article_links)} article-like")
        for a in article_links[:3]:
            print(f"    {a.get_text(strip=True)[:70]}")
            print(f"    → {a.get('href','')[:100]}")
    except Exception as e:
        print(f"  {name}: Error: {str(e)[:60]}")

# ═══════════════════════════════════════
# 6. Check 跨境电商 specific sites
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("6. CROSS-BORDER E-COMMERCE SPECIFIC")
print("=" * 60)

cross_border = [
    ("AMZ123", f"https://www.amz123.com/search?keyword={urllib.request.quote(kw)}"),
    ("出海笔记", f"https://www.chuhai.biz/search?keyword={urllib.request.quote(kw)}"),
    ("跨境眼", f"https://www.kuajingyan.com/search?keyword={urllib.request.quote(kw)}"),
    ("DNY123", f"https://www.dny123.com/search?keyword={urllib.request.quote(kw)}"),
]

for name, url in cross_border:
    try:
        html = fetch(url, 10)
        soup = BeautifulSoup(html, "lxml")
        links = [a for a in soup.select("a[href]")
                 if len(a.get_text(strip=True)) > 10]
        article_links = [a for a in links if any(
            p in a.get("href", "").lower() for p in
            ["/article/", "/news/", "/a/", "/p/", "detail"]
        )] or links[:10]
        print(f"  {name}: {len(links)} total links, {len(article_links)} article-like")
        for a in article_links[:3]:
            print(f"    {a.get_text(strip=True)[:70]}")
            print(f"    → {a.get('href','')[:100]}")
    except Exception as e:
        print(f"  {name}: Error: {str(e)[:60]}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_chinese2.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_chinese2.py 2>&1')
output = stdout.read().decode('utf-8', errors='replace')
with open('chinese_sources_result2.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Saved to chinese_sources_result2.txt")
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
