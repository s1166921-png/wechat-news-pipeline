"""Standalone WeChat search test - upload and run on server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Write standalone test script
test = '''import urllib.request, ssl, re, json
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")
items = soup.select("ul.news-list li")
print(f"Items found: {len(items)}")

results = []
for li in items[:10]:
    # Use exact same logic as _search_wechat
    title = ""
    href = ""
    h3 = li.select_one("h3")
    if h3:
        title = h3.get_text(strip=True)
        title_a = h3.select_one("a") or h3.find_parent("a")
        if not title_a:
            title_a = li.select_one("a[href]")
        if title_a:
            href = title_a.get("href", "")

    if len(title) < 8:
        best_len = 0
        for a in li.select("a[href]"):
            a_text = a.get_text(strip=True)
            if len(a_text) > best_len:
                best_len = len(a_text)
                title = a_text
                href = a.get("href", "")

    if len(title) < 8:
        print(f"  SKIP [{len(title)}c]: title too short")
        continue

    if href.startswith("/"):
        href = "https://weixin.sogou.com" + href

    full_text = li.get_text(strip=True)
    source = ""
    src_match = re.search(r'([一-鿿\w]{2,20})\s*$', full_text)
    if src_match:
        candidate = src_match.group(1)
        if not any(kw in candidate for kw in ["阅读", "点赞", "在看", "全文", "更多", "相关"]):
            source = candidate

    results.append({"title": title, "url": href, "source": source, "source_type": "wechat"})
    print(f"  [{len(results)-1}] ({len(title)}c) src={source} {title[:80]}")

print(f"\\nTotal results: {len(results)}")

# Now simulate _search_multi_engine filtering
def _clean_url(url):
    url = url.split("#")[0]
    for param in ("?utm_source", "&utm_source", "?ref=", "?source=", "?from=", "?spm=", "?track="):
        if param in url:
            url = url[:url.index(param)]
    return url.rstrip("?&")

seen = set()
final = []
for r in results:
    clean = _clean_url(r["url"])
    ok = clean not in seen and len(r.get("title", "")) >= 8
    seen.add(clean)
    if ok:
        final.append(r)
    else:
        print(f"  FILTERED: {clean[:80]} (seen={clean in seen})")

print(f"\\nAfter filtering: {len(final)}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/standalone_wx.py', 'w') as f:
    f.write(test)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/standalone_wx.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])

ssh.close()
