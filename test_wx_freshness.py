"""Investigate Sogou WeChat time-sort and freshness."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup

kw = "temu"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_and_parse(url, label):
    """Fetch URL and extract items with all metadata."""
    print(f"\n=== {label} ===")
    print(f"URL: {url[:120]}")
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("ul.news-list li")
        print(f"Items: {len(items)}")

        for i, li in enumerate(items[:5]):
            h3 = li.select_one("h3")
            title = h3.get_text(strip=True) if h3 else "?"
            if len(title) < 8:
                for a in li.select("a[href]"):
                    t = a.get_text(strip=True)
                    if len(t) > len(title): title = t

            # Source
            sp = li.select_one("div.s-p")
            src = sp.get_text(strip=True) if sp else "?"

            # Date: check ALL possible elements
            date_info = []
            for el_name in ["span.s2", "span.s3", "time", "[class*=time]", "[class*=date]", "[class*=day]"]:
                for el in li.select(el_name):
                    txt = el.get_text(strip=True)
                    tit = el.get("title", "")
                    if txt or tit:
                        date_info.append(f"{el_name}: txt='{txt}' title='{tit}'")

            # Check data attributes with timestamps
            data_attrs = {}
            for el in li.find_all(True):
                for attr in el.attrs:
                    if 'time' in attr.lower() or 'date' in attr.lower() or 'ts' in attr.lower():
                        data_attrs[attr] = el[attr]

            txt = li.get_text(strip=True)[:200]
            print(f"  [{i}] {title[:60]}")
            print(f"       src='{src}' dates={date_info}")
            if data_attrs:
                print(f"       data_attrs={data_attrs}")
        return soup
    except Exception as e:
        print(f"  Error: {e}")
        return None

# Test 1: Default URL
soup1 = fetch_and_parse(
    f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}",
    "Default (type=2)"
)

# Test 2: Check for hidden pagination/sort links
if soup1:
    print("\n=== All links with '时间' or '排序' ===")
    for a in soup1.select("a"):
        txt = a.get_text(strip=True)
        href = a.get("href", "")
        if "时间" in txt or "排序" in txt or "最新" in txt or "time" in str(a.get("class", "")):
            print(f"  '{txt}' → {href[:100]}")

    print("\n=== All script tags (might contain sort logic) ===")
    for s in soup1.select("script"):
        st = s.get_text()
        if "sort" in st.lower() or "tsn" in st.lower() or "time" in st.lower() or "page" in st.lower():
            print(f"  script: {st[:200]}")

# Test 3: Check if tsn parameter changes the page structure (not just returns 0 items)
for tsn_val, tsn_label in [("0", "tsn=0"), ("1", "tsn=1"), ("2", "tsn=2"), ("4", "tsn=4")]:
    url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}&tsn={tsn_val}"
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        # Check ALL li elements, not just ul.news-list
        all_li = soup.select("li")
        news_li = soup.select("ul.news-list li")
        # Also check for different container structures
        alt_containers = soup.select("[class*=result], [class*=item], [class*=article]")
        print(f"[{tsn_label}] news-list li={len(news_li)}, all li={len(all_li)}, alt_containers={len(alt_containers)}")
        if len(news_li) == 0 and len(all_li) > 0:
            for li in all_li[:3]:
                print(f"  all-li: {li.get_text(strip=True)[:80]}")
        # Check body class
        body = soup.select_one("body")
        if body:
            print(f"  body class: {body.get('class','')}")
    except Exception as e:
        print(f"[{tsn_label}] Error: {e}")

# Test 4: Look for "latest" or "hot" endpoint patterns in the page
print("\n=== Test 4: Search for hidden API endpoints ===")
try:
    url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    # Look for JavaScript variables/API calls
    api_patterns = re.findall(r'["\'](https?://[^"\']*(?:api|ajax|search|query|list)[^"\']*)["\']', html)
    print(f"  API endpoints found: {len(api_patterns)}")
    for api in api_patterns[:5]:
        print(f"    {api[:150]}")
    # Check meta tags
    soup = BeautifulSoup(html, "lxml")
    for meta in soup.select("meta"):
        if meta.get("name") in ["description", "keywords"]:
            print(f"  meta {meta.get('name')}: {meta.get('content','')[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# Test 5: Check if Bing can find RECENT WeChat articles
print("\n=== Test 5: Bing fresh WeChat articles ===")
try:
    bing_url = f"https://www.bing.com/search?q={urllib.request.quote(kw)}+site:mp.weixin.qq.com&filters=ex1:\"ez1\"&setlang=zh-cn"
    bing_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    req2 = urllib.request.Request(bing_url, headers=bing_headers)
    resp2 = urllib.request.urlopen(req2, timeout=10, context=ctx)
    bing_html = resp2.read().decode("utf-8", errors="replace")
    bing_soup = BeautifulSoup(bing_html, "lxml")
    for sel in ["li.b_algo", ".b_algo h2"]:
        found = bing_soup.select(sel)
        if found:
            print(f"  Selector '{sel}': {len(found)}")
            for r in found[:3]:
                a = r.select_one("a") if r.name != "a" else r
                if a:
                    print(f"    {a.get_text(strip=True)[:80]}")
except Exception as e:
    print(f"  Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wx_fresh.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_wx_fresh.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
