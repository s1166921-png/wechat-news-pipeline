"""Test improved WeChat search with date extraction + query expansion."""
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

def search_wx(query, max_results=8):
    url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(query)}"
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("ul.news-list li")
    results = []
    for li in items[:max_results]:
        # Title from h3
        h3 = li.select_one("h3")
        title = h3.get_text(strip=True) if h3 else ""
        href = ""
        if h3:
            a = h3.select_one("a")
            if a:
                href = a.get("href", "")
        if len(title) < 8:
            for a in li.select("a[href]"):
                at = a.get_text(strip=True)
                if len(at) > len(title):
                    title = at
                    href = a.get("href", "")
        if len(title) < 8:
            continue

        if href.startswith("/"):
            href = "https://weixin.sogou.com" + href

        # Source from div.s-p
        source_el = li.select_one("div.s-p")
        source = source_el.get_text(strip=True) if source_el else ""

        # Date from span.s2
        date_el = li.select_one("span.s2")
        date_str = date_el.get_text(strip=True) if date_el else ""
        # Also check title attribute
        if not date_str and date_el:
            date_str = date_el.get("title", "")

        # Snippet from p.txt-info
        snippet_el = li.select_one("p.txt-info")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        results.append({
            "title": title, "url": href, "source": source,
            "date": date_str, "snippet": snippet,
        })
    return results

# Test 1: Check date extraction
print("=== Test 1: Date extraction from span.s2 ===")
results = search_wx("temu", max_results=6)
for i, r in enumerate(results):
    print(f"  [{i}] date='{r['date']}' src='{r['source']}'")
    print(f"       title='{r['title'][:80]}'")
print()

# Test 2: Multi-query strategy - broader + narrower
print("=== Test 2: Query expansion strategy ===")
all_results = {}
for strategy, query in [
    ("original", "temu 跨境电商"),
    ("broad", "temu"),
    ("news", "temu 跨境电商 最新"),
    ("analysis", "temu 分析"),
]:
    results = search_wx(query, max_results=5)
    titles = [r['title'][:70] for r in results]
    print(f"  [{strategy}] '{query}': {len(results)} items")
    for t in titles:
        print(f"    - {t}")
    all_results[strategy] = results

# Test 3: Check span.s2 more carefully
print("\n=== Test 3: Span.s2 deep dive ===")
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote('temu')}"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")
items = soup.select("ul.news-list li")

# Check ALL elements that might contain date in first 3 items
for i, li in enumerate(items[:3]):
    print(f"\n  Item {i}:")
    # All spans
    for span in li.select("span"):
        cls = span.get("class", "")
        txt = span.get_text(strip=True)
        attrs = dict(span.attrs)
        print(f"    <span class={cls}> text='{txt}' all_attrs={attrs}")
    # All divs with class
    for div in li.select("div[class]"):
        cls = " ".join(div.get("class", []))
        txt = div.get_text(strip=True)[:80]
        print(f"    <div class='{cls}'> text='{txt}'")
    # All time elements
    for time_el in li.select("time"):
        print(f"    <time> text='{time_el.get_text(strip=True)}'")
    # Look for data attributes with time
    for el in li.select("[data-*], [data-time]"):
        pass  # no universal selector for data-*

# Test 4: Check if there's pagination / "more results"
print("\n=== Test 4: Check page structure ===")
# Check for "下一页" link
next_links = soup.select("a:contains('下一页')")
if not next_links:
    next_links = soup.select("a")
    for a in next_links:
        if "下一页" in a.get_text() or "next" in str(a.get("class", "")).lower():
            next_links = [a]
            break
    else:
        next_links = []
print(f"  Next page links found: {len(next_links)}")
for a in next_links:
    print(f"    href='{a.get('href','')}' text='{a.get_text(strip=True)}'")

# Check for sort/filter options
for sel in soup.select("a[href*='tsn'], a[href*='sort'], [class*=sort], [class*=filter]"):
    txt = sel.get_text(strip=True)[:60]
    href = sel.get("href", "")
    cls = " ".join(sel.get("class", [])) if sel.get("class") else ""
    print(f"    sort/filter: class='{cls}' href='{href[:80]}' text='{txt}'")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wx_improve.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_wx_improve.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
