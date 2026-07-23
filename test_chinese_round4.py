"""Verify winners: Cifnews RSS feed + Ebrun search detail."""
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

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8", errors="replace")

# ═══════════════════════════════════════
# 1. 雨果跨境 RSS Feed!
# ═══════════════════════════════════════
print("=" * 60)
print("1. CIFNEWS RSS: YuGuo.xml")
print("=" * 60)
try:
    rss_url = "https://www.cifnews.com/xmlconfig/YuGuo.xml"
    html = fetch(rss_url)
    soup = BeautifulSoup(html, "xml")
    items = soup.select("item")
    print(f"  Total items: {len(items)}")

    # Check structure of first item
    if items:
        print(f"\n  First item full XML:")
        print(f"  {str(items[0])[:800]}")

    print(f"\n  All items:")
    for i, item in enumerate(items[:20]):
        title = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
        link = (item.select_one("link") or "").get_text(strip=True) if item.select_one("link") else ""
        pubdate = (item.select_one("pubDate") or "").get_text(strip=True) if item.select_one("pubDate") else ""
        desc = (item.select_one("description") or "").get_text(strip=True)[:100] if item.select_one("description") else ""
        print(f"  [{i}] [{pubdate[:30]}] {title[:80]}")
        print(f"      link: {link[:120]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 2. 亿邦动力 mobile - search structure
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("2. EBRUN MOBILE SEARCH - DETAIL")
print("=" * 60)
try:
    url = f"https://m.ebrun.com/search?keyword={urllib.request.quote(kw)}"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")

    # Find actual article items
    # Check what the search results look like
    print("  Checking selectors...")
    for sel in ["div.search-list li", "div.news-list li", "div.list-item", "div.item", "ul.list li", "div.article-item",
                "li", "div.result"]:
        items = soup.select(sel)
        if items:
            # Check if items have titles
            titled = 0
            for item in items:
                a = item.select_one("a")
                if a and len(a.get_text(strip=True)) > 10:
                    titled += 1
            if titled >= 2:
                print(f"    '{sel}': {len(items)} total, {titled} with titles")

    # Extract all meaningful article-like links
    all_a = soup.select("a[href]")
    articles = []
    for a in all_a:
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if len(title) > 15 and not href.startswith("javascript") and "search" not in href[:30]:
            # Prefer article links
            articles.append((title, href))

    print(f"\n  Article-like links: {len(articles)}")
    for title, href in articles[:15]:
        print(f"    {title[:90]}")
        print(f"    → {href[:130]}")

    # Also try to find date elements
    date_els = soup.select("[class*=date], [class*=time], span.date, span.time")
    if date_els:
        print(f"\n  Date elements found: {len(date_els)}")
        for el in date_els[:5]:
            print(f"    {el.get_text(strip=True)[:50]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 3. 亿邦动力 - try mobile article detail page
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("3. EBRUN ARTICLE PAGE STRUCTURE")
print("=" * 60)
try:
    # Fetch one article to see structure
    article_url = "https://m.ebrun.com/687030.html"  # the "翻倍增长背后" article
    html = fetch(article_url)
    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title = soup.select_one("h1") or soup.select_one("title") or soup.select_one(".title")
    if title:
        print(f"  Title: {(title.get_text(strip=True) if title else 'N/A')[:100]}")

    # Date
    for sel in ["span.date", "span.time", ".article-date", ".pub-date", ".info span"]:
        el = soup.select_one(sel)
        if el:
            print(f"  Date ({sel}): {el.get_text(strip=True)[:50]}")

    # Content
    content_sel = soup.select_one("div.content") or soup.select_one("div.article-content") or soup.select_one("article")
    if content_sel:
        text = content_sel.get_text(strip=True)[:500]
        print(f"  Content preview: {text}")
    else:
        # Show body text
        body = soup.select_one("body")
        if body:
            text = body.get_text(strip=True)
            # Find the article content area
            print(f"  Body text length: {len(text)}")
            # Show first 300 chars after finding "翻倍"
            idx = text.find("翻倍")
            if idx > 0:
                print(f"  Content: {text[idx:idx+400]}")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 4. 雨果跨境 - we have RSS, also check if articles are scrapable
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("4. CIFNEWS ARTICLE PAGE")
print("=" * 60)
try:
    # Get first article URL from RSS
    rss_url = "https://www.cifnews.com/xmlconfig/YuGuo.xml"
    html = fetch(rss_url)
    soup = BeautifulSoup(html, "xml")
    first_link = ""
    first_title = ""
    for item in soup.select("item"):
        link_el = item.select_one("link")
        title_el = item.select_one("title")
        if link_el and title_el:
            first_link = link_el.get_text(strip=True)
            first_title = title_el.get_text(strip=True)
            if first_link:
                break

    if first_link:
        print(f"  Fetching: {first_title[:80]}")
        print(f"  URL: {first_link[:120]}")
        html2 = fetch(first_link, 10)
        soup2 = BeautifulSoup(html2, "lxml")
        # Check if we can get article content
        # Cifnews might be JS-rendered on article pages too
        article_sel = soup2.select_one("div.article-content") or soup2.select_one("div.content") or soup2.select_one("article")
        if article_sel:
            text = article_sel.get_text(strip=True)[:500]
            print(f"  Content found! {len(text)} chars")
            print(f"  Preview: {text[:300]}")
        else:
            # Check if content is in meta or script tags
            body_text = soup2.select_one("body")
            if body_text:
                body = body_text.get_text(strip=True)
                print(f"  Body text: {len(body)} chars")
                # Search for article-like content
                if len(body) > 500:
                    print(f"  Body preview: {body[:400]}")
                else:
                    print(f"  Short body: {body[:300]}")
            else:
                print("  No body found - likely JS-rendered")
    else:
        print("  No article link found in RSS")
except Exception as e:
    print(f"  Error: {e}")

# ═══════════════════════════════════════
# 5. Same check for 36Kr article page
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("5. 36KR ARTICLE PAGE")
print("=" * 60)
try:
    test_url = "https://36kr.com/p/3901396207584902?f=rss"
    html = fetch(test_url, 10)
    soup = BeautifulSoup(html, "lxml")

    # 36Kr typically has SSR or JSON data
    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*</script>', html, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            print(f"  JSON __INITIAL_STATE__ found: {len(str(data))} chars")
            # Try to extract title and content
            if "articleDetail" in data:
                ad = data["articleDetail"]
                t = ad.get("articleDetailData", {}).get("data", {}).get("title", "")
                print(f"  Title from JSON: {t[:100]}")
        except:
            print("  JSON parse failed")

    # Also check body
    body = soup.select_one("body")
    if body:
        text = body.get_text(strip=True)
        print(f"  Body text: {len(text)} chars")
except Exception as e:
    print(f"  Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_chinese4.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_chinese4.py 2>&1')
output = stdout.read().decode('utf-8', errors='replace')
with open('chinese_sources_result4.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Saved to chinese_sources_result4.txt")
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
