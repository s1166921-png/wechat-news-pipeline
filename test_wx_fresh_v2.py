"""Test pagination, mobile endpoint, and alternative freshness strategies."""
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

# Test 1: Pagination - check for page parameter
print("=== Test 1: Pagination ===")
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")

# Find pagination links
print("Looking for page links...")
for a in soup.select("a"):
    href = a.get("href", "")
    txt = a.get_text(strip=True)
    if "page" in href.lower() or txt in ["1","2","3","4","5","下一页",">","»"]:
        print(f"  Page link: '{txt}' → {href[:120]}")
    if "p=" in href or "pn=" in href or "page=" in href:
        print(f"  Paged URL: {href[:150]}")

# Try page=2
for page_param in ["&page=2", "&p=2", "&pn=2", "&start=10"]:
    url2 = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}{page_param}"
    try:
        req2 = urllib.request.Request(url2, headers=headers)
        resp2 = urllib.request.urlopen(req2, timeout=10, context=ctx)
        html2 = resp2.read().decode("utf-8", errors="replace")
        items2 = BeautifulSoup(html2, "lxml").select("ul.news-list li")
        ts2 = re.findall(r"timeConvert\('(\d+)'\)", html2)
        if len(items2) > 0 or len(ts2) > 0:
            dates = []
            for t in ts2[:5]:
                try:
                    dt = datetime.fromtimestamp(int(t))
                    dates.append(dt.strftime('%Y-%m-%d'))
                except: pass
            print(f"  {page_param}: {len(items2)} items, dates={dates}")
    except Exception as e:
        print(f"  {page_param}: Error: {e}")

# Try "next page" link
next_link = soup.select_one("a#sogou_next, a.sogou_next, a:contains('下一页')")
if not next_link:
    next_links = [a for a in soup.select("a") if "下一页" in a.get_text()]
    next_link = next_links[0] if next_links else None
if next_link:
    print(f"  Next page: href={next_link.get('href','')[:150]}")

# Test 2: Mobile User-Agent endpoint
print("\n=== Test 2: Mobile endpoint ===")
mobile_headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
url_m = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
try:
    req_m = urllib.request.Request(url_m, headers=mobile_headers)
    resp_m = urllib.request.urlopen(req_m, timeout=10, context=ctx)
    html_m = resp_m.read().decode("utf-8", errors="replace")
    soup_m = BeautifulSoup(html_m, "lxml")
    items_m = soup_m.select("ul.news-list li")
    if not items_m:
        items_m = soup_m.select("[class*=item], [class*=result]")
    ts_m = re.findall(r"timeConvert\('(\d+)'\)", html_m)
    print(f"  Mobile UA: {len(items_m)} items, {len(ts_m)} timestamps")
    if ts_m:
        dates = []
        for t in ts_m[:8]:
            try:
                dt = datetime.fromtimestamp(int(t))
                dates.append(f"{dt.strftime('%Y-%m-%d')}({(datetime.now()-dt).days}d)")
            except: pass
        print(f"  dates: {dates}")
    if items_m:
        for li in items_m[:3]:
            txt = li.get_text(strip=True)[:60]
            print(f"    - {txt}")
except Exception as e:
    print(f"  Mobile Error: {e}")

# Test 3: Try Sogou News for WeChat articles (search.weixin.qq.com domain)
print("\n=== Test 3: Alternative WeChat search endpoints ===")
for label, alt_url in [
    ("weixin.sogou.com HTTPS", f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&ie=utf8"),
    ("search.weixin.qq.com", f"https://search.weixin.qq.com/cgi-bin/search?query={urllib.request.quote(kw)}&type=2"),
    ("mp.weixin.qq.com search", f"https://mp.weixin.qq.com/cgi-bin/search?action=search&query={urllib.request.quote(kw)}"),
]:
    try:
        req_a = urllib.request.Request(alt_url, headers=headers)
        resp_a = urllib.request.urlopen(req_a, timeout=10, context=ctx)
        html_a = resp_a.read().decode("utf-8", errors="replace")
        # Look for article titles
        a_items = BeautifulSoup(html_a, "lxml").select("ul.news-list li, [class*=item]")
        if not a_items:
            a_items = BeautifulSoup(html_a, "lxml").select("a[href*='mp.weixin.qq.com']")
        print(f"  [{label}]: {len(a_items)} items, {len(html_a)} chars")
        for item in a_items[:2]:
            txt = item.get_text(strip=True)[:60]
            print(f"    - {txt}")
    except Exception as e:
        print(f"  [{label}]: Error: {str(e)[:80]}")

# Test 4: Compare with 360 and Sogou News freshness
print("\n=== Test 4: Freshness comparison - ALL engines ===")
# 360 News
try:
    url_360 = f"https://news.so.com/ns?q={urllib.request.quote(kw)}&src=srp"
    req_360 = urllib.request.Request(url_360, headers=headers)
    resp_360 = urllib.request.urlopen(req_360, timeout=10, context=ctx)
    html_360 = resp_360.read().decode("utf-8", errors="replace")
    # Check for date patterns in 360 results
    date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})', html_360)[:10]
    # Also check relative dates
    rel_matches = re.findall(r'(\d+[天小时分钟]前)', html_360)[:10]
    print(f"  360 News dates: {date_matches[:5]} relative: {rel_matches[:5]}")
except Exception as e:
    print(f"  360 News Error: {e}")

# Sogou News
try:
    url_sg = f"https://news.sogou.com/news?query={urllib.request.quote(kw)}"
    req_sg = urllib.request.Request(url_sg, headers=headers)
    resp_sg = urllib.request.urlopen(req_sg, timeout=10, context=ctx)
    html_sg = resp_sg.read().decode("utf-8", errors="replace")
    date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})', html_sg)[:10]
    rel_matches = re.findall(r'(\d+[天小时分钟]前)', html_sg)[:10]
    print(f"  Sogou News dates: {date_matches[:5]} relative: {rel_matches[:5]}")
except Exception as e:
    print(f"  Sogou News Error: {e}")

# Google News RSS
try:
    url_gn = f"https://news.google.com/rss/search?q={urllib.request.quote(kw)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    req_gn = urllib.request.Request(url_gn, headers=headers)
    resp_gn = urllib.request.urlopen(req_gn, timeout=10, context=ctx)
    gn_xml = resp_gn.read().decode("utf-8", errors="replace")
    pubdates = re.findall(r'<pubDate>([^<]+)</pubDate>', gn_xml)[:5]
    print(f"  Google News pubDates: {pubdates}")
except Exception as e:
    print(f"  Google News Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wx_fresh_v2.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_wx_fresh_v2.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
