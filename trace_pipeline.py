"""Trace full pipeline for WeChat search."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Write trace script to server
trace = '''
import json, urllib.request, ssl, re
from bs4 import BeautifulSoup

def _simple_get(url, timeout=15):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    GN_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=GN_HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8", errors="replace")

# Simulate the full flow
import sys
sys.path.insert(0, "/opt/wechat-news-pipeline")

# We can't import app directly due to flask deps, so let's manually trace
# by calling _simple_get and parsing

kw = "temu 跨境电商"
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
wx_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers=wx_headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")
items = soup.select("ul.news-list li")
print(f"Raw items: {len(items)}")

# Count how many have valid titles
valid = 0
for li in items[:10]:
    title = ""
    h3 = li.select_one("h3")
    if h3:
        title = h3.get_text(strip=True)
    if len(title) < 8:
        best_len = 0
        for a in li.select("a[href]"):
            a_text = a.get_text(strip=True)
            if len(a_text) > best_len:
                best_len = len(a_text)
                title = a_text
    if len(title) < 8:
        print(f"  SKIP: title too short ({len(title)}c): '{title}'")
    else:
        valid += 1
        print(f"  OK ({len(title)}c): {title[:60]}")

print(f"\\nValid titles: {valid}/{len(items)}")

# Now check what happens when we call the API
print("\\n=== API Call ===")
import urllib.request as ur
req2 = ur.Request("http://127.0.0.1:8888/api/search",
    data=json.dumps({"keyword":"temu 跨境电商","max_results":10,"engines":["wechat"]}).encode(),
    headers={"Content-Type": "application/json"})
resp2 = ur.urlopen(req2, timeout=30)
data = json.loads(resp2.read().decode())
print(f"API total: {data.get('total', 0)}")
for i, r in enumerate(data.get("results", [])[:10]):
    print(f"  [{i}] type={r.get('source_type','?')} score={r.get('score','?')} {r['title'][:80]}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/trace_pipeline.py', 'w') as f:
    f.write(trace)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/trace_pipeline.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])

ssh.close()
