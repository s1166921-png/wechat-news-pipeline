"""Extract timestamps from Sogou WeChat and test time filtering."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup
from datetime import datetime

kw = "temu"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Test 1: Extract timestamps from JavaScript
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")

# Extract all timeConvert timestamps
timestamps = re.findall(r"timeConvert\('(\d+)'\)", html)
print(f"=== Test 1: Timestamps found: {len(timestamps)} ===")
for i, ts in enumerate(timestamps):
    try:
        dt = datetime.fromtimestamp(int(ts))
        age_days = (datetime.now() - dt).days
        print(f"  [{i}] ts={ts} → {dt.strftime('%Y-%m-%d')} ({age_days}d ago)")
    except:
        print(f"  [{i}] ts={ts} → (invalid)")

# Map timestamps to article titles
items = soup.select("ul.news-list li")
print(f"\n=== Articles with dates ===")
for i, li in enumerate(items[:10]):
    h3 = li.select_one("h3")
    title = h3.get_text(strip=True) if h3 else "?"
    if len(title) < 8:
        for a in li.select("a[href]"):
            t = a.get_text(strip=True)
            if len(t) > len(title): title = t
    sp = li.select_one("div.s-p")
    src = sp.get_text(strip=True) if sp else "?"
    # Get corresponding timestamp
    ts = timestamps[i] if i < len(timestamps) else "?"
    try:
        dt = datetime.fromtimestamp(int(ts))
        date_str = dt.strftime('%Y-%m-%d')
        age = f"{(datetime.now() - dt).days}d ago"
    except:
        date_str = "?"
        age = "?"
    print(f"  [{i}] {date_str} ({age}) | {src:15s} | {title[:60]}")

# Test 2: Try ft parameter for time filtering (from_time to now)
print(f"\n=== Test 2: Time filter with ft parameter ===")
import time
# ft = 30 days ago in Unix timestamp
thirty_days_ago = int(time.time()) - 30 * 86400
for label, ft_val in [
    ("last 7 days", int(time.time()) - 7 * 86400),
    ("last 30 days", thirty_days_ago),
    ("last 90 days", int(time.time()) - 90 * 86400),
]:
    url2 = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&ft={ft_val}"
    try:
        req2 = urllib.request.Request(url2, headers=headers)
        resp2 = urllib.request.urlopen(req2, timeout=10, context=ctx)
        html2 = resp2.read().decode("utf-8", errors="replace")
        soup2 = BeautifulSoup(html2, "lxml")
        items2 = soup2.select("ul.news-list li")
        ts2 = re.findall(r"timeConvert\('(\d+)'\)", html2)
        print(f"  [{label}] ft={ft_val}: {len(items2)} items, {len(ts2)} timestamps")
        if ts2:
            dates = []
            for t in ts2[:5]:
                try:
                    dt = datetime.fromtimestamp(int(t))
                    dates.append(dt.strftime('%m-%d'))
                except: pass
            print(f"    dates: {dates}")
        if items2:
            for li in items2[:3]:
                h3 = li.select_one("h3")
                t = h3.get_text(strip=True)[:60] if h3 else "?"
                print(f"    - {t}")
    except Exception as e:
        print(f"  [{label}] Error: {e}")

# Test 3: Check if tsn with s_from=input returns different HTML
print(f"\n=== Test 3: Different tsn with s_from=input ===")
for tsn_v in ["0", "1", "2", "3"]:
    url3 = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&tsn={tsn_v}&s_from=input"
    try:
        req3 = urllib.request.Request(url3, headers=headers)
        resp3 = urllib.request.urlopen(req3, timeout=10, context=ctx)
        html3 = resp3.read().decode("utf-8", errors="replace")
        soup3 = BeautifulSoup(html3, "lxml")
        items3 = soup3.select("ul.news-list li")
        ts3 = re.findall(r"timeConvert\('(\d+)'\)", html3)
        print(f"  tsn={tsn_v}: {len(items3)} items, {len(ts3)} timestamps")
        if items3:
            for li in items3[:2]:
                h3 = li.select_one("h3")
                t = h3.get_text(strip=True)[:60] if h3 else "?"
                print(f"    - {t}")
    except Exception as e:
        print(f"  tsn={tsn_v} Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wx_time.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_wx_time.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
