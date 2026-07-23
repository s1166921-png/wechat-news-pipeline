"""Deep analysis of WeChat search HTML + test alternative strategies."""
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

# === Part 1: Deep HTML structure ===
print("=== PART 1: HTML Structure Deep Dive ===")
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")
items = soup.select("ul.news-list li")

if items:
    li = items[0]
    # Print ALL elements with their classes
    print("All elements with classes in first <li>:")
    for el in li.find_all(True):
        cls = el.get("class")
        if cls:
            txt = el.get_text(strip=True)[:50]
            print(f"  <{el.name} class={' '.join(cls)}>: '{txt}'")

    print("\nFull raw HTML of first li:")
    print(str(li)[:1500])

# === Part 2: Try Bing with site:mp.weixin.qq.com ===
print("\n\n=== PART 2: Bing site:mp.weixin.qq.com ===")
try:
    bing_url = f"https://www.bing.com/search?q=site%3Amp.weixin.qq.com+{urllib.request.quote(kw)}&setlang=zh-cn"
    bing_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    req2 = urllib.request.Request(bing_url, headers=bing_headers)
    resp2 = urllib.request.urlopen(req2, timeout=10, context=ctx)
    bing_html = resp2.read().decode("utf-8", errors="replace")
    bing_soup = BeautifulSoup(bing_html, "lxml")

    # Bing search result selectors
    for sel in ["li.b_algo", "ol#b_results li", ".b_algo", "li.b_ans"]:
        found = bing_soup.select(sel)
        if found:
            print(f"  Selector '{sel}': {len(found)} results")
            for r in found[:3]:
                h2 = r.select_one("h2") or r.select_one("a")
                title = h2.get_text(strip=True) if h2 else "?"
                a = r.select_one("h2 a") or r.select_one("a")
                href = a.get("href", "") if a else ""
                print(f"    title={title[:80]}")
                print(f"    url={href[:100]}")
            break
except Exception as e:
    print(f"  Bing error: {e}")

# === Part 3: Try different WeChat-specific queries ===
print("\n\n=== PART 3: Broader keyword strategies ===")
for strategy, query in [
    ("News-focused", f"{kw} 最新 新闻"),
    ("Trend-focused", f"{kw} 趋势 动态"),
    ("Simple keyword", "temu"),
    ("WeChat-style", f"{kw} 分析"),
]:
    try:
        url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(query)}"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("ul.news-list li")
        print(f"  [{strategy}] '{query}': {len(items)} items")
        for li in items[:3]:
            h3 = li.select_one("h3")
            t = h3.get_text(strip=True) if h3 else ""
            if len(t) < 8:
                for a in li.select("a[href]"):
                    at = a.get_text(strip=True)
                    if len(at) > len(t):
                        t = at
            print(f"    - {t[:80]}")
    except Exception as e:
        print(f"  [{strategy}] Error: {e}")

# === Part 4: Check if Sogou WeChat has a "hot" or "trending" endpoint ===
print("\n\n=== PART 4: Alternative Sogou endpoints ===")
for label, alt_url in [
    ("No type param", f"https://weixin.sogou.com/weixin?query={urllib.request.quote(kw)}"),
    ("type=1 (accounts)", f"https://weixin.sogou.com/weixin?type=1&query={urllib.request.quote(kw)}"),
    ("pc version", f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&ie=utf8&s_from=input&_sug_=n&_sug_type_="),
]:
    try:
        req = urllib.request.Request(alt_url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("ul.news-list li")
        if not items:
            items = soup.select("li")
        if not items:
            items = soup.select("[class*=item]")
        print(f"  [{label}]: {len(items)} items, URL={alt_url[:80]}")
        for li in items[:2]:
            h3 = li.select_one("h3") or li.select_one("a")
            t = h3.get_text(strip=True)[:80] if h3 else li.get_text(strip=True)[:80]
            print(f"    - {t}")
    except Exception as e:
        print(f"  [{label}] Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wx_deep.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_wx_deep.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
