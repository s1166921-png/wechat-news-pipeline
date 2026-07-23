"""Fix Baidu News access with different headers/approaches."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Test different header/URL combinations for Baidu News
tests = [
    ("Default UA + news.baidu.com", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }, f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=5&ie=utf-8"),

    ("Baidu spider UA", {
        "User-Agent": "Baiduspider/2.0",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }, f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=5&ie=utf-8"),

    ("Mobile UA + www.baidu.com/s", {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }, f"https://www.baidu.com/s?wd={urllib.request.quote(kw)}&tn=news&rtt=1"),

    ("Chrome + www.baidu.com/s?tn=news", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.baidu.com/",
    }, f"https://www.baidu.com/s?wd={urllib.request.quote(kw)}&tn=news&rtt=1&ie=utf-8"),

    ("With cookies + baidu news", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": "BAIDUID=test; BAIDUPSID=test",
    }, f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=5&ie=utf-8"),
]

for label, hdrs, url in tests:
    try:
        req = urllib.request.Request(url, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("div.result, div.news-item, div.result-op, h3 a")
        if not items:
            items = soup.select("h3.c-title a, h3.news-title a, h3.t a")
        # Check for "网络不给力" anti-bot message
        has_antibody = "网络不给力" in html or "请输入验证码" in html
        # Check for actual titles
        titles = []
        for item in items[:5]:
            a = item.select_one("a") if item.name != "a" else item
            t = (a.get_text(strip=True) if a else item.get_text(strip=True))[:60]
            if len(t) > 8:
                titles.append(t)
        status = "ANTIBOT" if has_antibody else f"{len(items)} items, {len(titles)} titles"
        print(f"  [{label[:25]:25s}] {status}")
        for t in titles[:3]:
            print(f"    - {t}")
    except Exception as e:
        print(f"  [{label[:25]:25s}] Error: {str(e)[:60]}")

# === Also test: Cifnews (雨果跨境) direct search ===
print("\n=== Cifnews search ===")
try:
    url = f"https://www.cifnews.com/search?keyword={urllib.request.quote(kw)}"
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "zh-CN,zh;q=0.9"}
    req = urllib.request.Request(url, headers=hdrs)
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    # Check for article links
    soup = BeautifulSoup(html, "lxml")
    article_links = soup.select("a[href*='/article/'], h2 a, h3 a, .title a")
    print(f"  Article links: {len(article_links)}")
    for a in article_links[:5]:
        t = a.get_text(strip=True)
        u = a.get("href", "")
        if len(t) > 10:
            print(f"    {t[:70]}")
            print(f"    url={u[:120]}")
except Exception as e:
    print(f"  Error: {e}")

# === Test: 36Kr search ===
print("\n=== 36Kr search ===")
try:
    url = f"https://www.36kr.com/search?q={urllib.request.quote(kw)}"
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "zh-CN,zh;q=0.9"}
    req = urllib.request.Request(url, headers=hdrs)
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    # 36Kr renders with JS, but data might be in JSON
    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*</script>', html, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(1))
        print(f"  JSON data found with {len(str(data))} chars")
    else:
        soup = BeautifulSoup(html, "lxml")
        links = soup.select("a[href*='/p/'], a.article-title, h3 a")
        print(f"  HTML links: {len(links)}")
        for a in links[:5]:
            t = a.get_text(strip=True)
            if len(t) > 10:
                print(f"    {t[:70]}")
except Exception as e:
    print(f"  Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_baidu_fix.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_baidu_fix.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
