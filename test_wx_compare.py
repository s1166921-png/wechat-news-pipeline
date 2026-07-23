"""Compare different WeChat search strategies on the server."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup
import sys

kw = "temu 跨境电商"

# Test different search URLs
tests = [
    ("Current (type=2)", f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"),
    ("TimeSort (tsn=1)", f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&tsn=1&s_from=input"),
    ("Relevance+s_from", f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&s_from=input"),
    ("tsn=3 (hot)", f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&tsn=3&s_from=input"),
]

for label, url in tests:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("ul.news-list li")

        titles = []
        dates = []
        for li in items[:8]:
            h3 = li.select_one("h3")
            t = h3.get_text(strip=True) if h3 else ""
            if len(t) < 8:
                for a in li.select("a[href]"):
                    at = a.get_text(strip=True)
                    if len(at) > len(t):
                        t = at
            titles.append(t[:80])

            txt = li.get_text(strip=True)
            dm = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', txt)
            rm = re.search(r'(\d{1,2}(小时|天|分钟|月)前)', txt)
            dates.append(dm.group(1) if dm else (rm.group(1) if rm else "?"))

        print(f"[{label}] {len(items)} items")
        for i, (t, d) in enumerate(zip(titles, dates)):
            print(f"  [{i}] {d} | {t}")
        print()
    except Exception as e:
        print(f"[{label}] Error: {e}")
        print()

# Also check what HTML classes/attrs are available for date extraction
print("=== HTML structure deep dive ===")
try:
    url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&tsn=1&s_from=input"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("ul.news-list li")

    # Print first item's HTML structure
    if items:
        li = items[0]
        # Find all elements with class or id
        for el in li.select("[class], [id]"):
            print(f"  <{el.name} class='{el.get('class','')}' id='{el.get('id','')}'> text='{el.get_text(strip=True)[:60]}'")

        # Print raw HTML of first li
        print("\n  RAW HTML (first 1000 chars):")
        print(f"  {str(li)[:1000]}")
except Exception as e:
    print(f"Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wx_compare.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_wx_compare.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
