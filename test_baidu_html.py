"""Deep dive into Baidu News HTML + quick video link check."""
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
kw = "temu 跨境电商"

# === Part 1: Baidu News raw HTML structure ===
print("=== Part 1: Baidu News HTML ===")
url = f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=5&ie=utf-8"
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=12, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")

# Find all result containers
for sel in ["div.result", "div.news-item", "div.result-op"]:
    items = soup.select(sel)
    if len(items) >= 3:
        print(f"Selector '{sel}': {len(items)} items")
        # Print first item's structure
        item = items[0]
        print(f"\n  First item classes: {item.get('class','')}")
        print(f"  First item HTML (first 1200 chars):")
        print(f"  {str(item)[:1200]}")

        # Second item for comparison
        item2 = items[1]
        print(f"\n  Second item HTML (first 800 chars):")
        print(f"  {str(item2)[:800]}")
        break
else:
    # No results found. Print the raw HTML for debugging
    print("No result containers found. Printing body snippet:")
    body = soup.select_one("body")
    if body:
        print(body.get_text(strip=True)[:500])

# === Part 2: Bing web search - check for video links ===
print("\n=== Part 2: Bing search directly (check for video links) ===")
bing_url = f"https://www.bing.com/search?q={urllib.request.quote(kw)}&setlang=zh-cn&count=20"
try:
    req2 = urllib.request.Request(bing_url, headers=headers)
    resp2 = urllib.request.urlopen(req2, timeout=12, context=ctx)
    html2 = resp2.read().decode("utf-8", errors="replace")
    soup2 = BeautifulSoup(html2, "lxml")
    items2 = soup2.select("li.b_algo")
    print(f"  Bing results: {len(items2)}")
    video_count = 0
    for i, li in enumerate(items2[:15]):
        a = li.select_one("h2 a") or li.select_one("a")
        href = a.get("href", "") if a else ""
        title = a.get_text(strip=True) if a else ""

        flags = []
        if "/video/" in href.lower() or "/v/" in href.lower(): flags.append("VIDEO_PATH")
        if any(d in href.lower() for d in ["bilibili", "youtube", "youku", "iqiyi", "haokan", "v.qq.com", "tv.sohu"]): flags.append("VIDEO_DOMAIN")
        if any(w in title.lower() for w in ["视频", "video", "直播", "live"]): flags.append("TITLE_VIDEO")

        if flags:
            video_count += 1
            print(f"  [{i}] {'|'.join(flags)} | {title[:60]}")
            print(f"       url={href[:120]}")
    if video_count == 0:
        print("  No video links found in Bing results")
except Exception as e:
    print(f"  Error: {e}")

# === Part 3: 360 News - check for video links ===
print("\n=== Part 3: 360 News direct (check for video links) ===")
url360 = f"https://news.so.com/ns?q={urllib.request.quote(kw)}&src=srp"
try:
    req3 = urllib.request.Request(url360, headers=headers)
    resp3 = urllib.request.urlopen(req3, timeout=12, context=ctx)
    html3 = resp3.read().decode("utf-8", errors="replace")
    soup3 = BeautifulSoup(html3, "lxml")
    items3 = soup3.select("ul.result li, div.result")
    print(f"  360 items: {len(items3)}")
    video_count = 0
    for i, li in enumerate(items3[:15]):
        a = li.select_one("a")
        href = a.get("href", "") if a else ""
        title = a.get("title", "") or a.get_text(strip=True) if a else ""

        flags = []
        if "360kuai.com/pc/" in href and "video" in href.lower(): flags.append("KUAIVIDEO")
        elif "360kuai.com/pc/" in href: flags.append("360KUAI")
        if any(d in href.lower() for d in ["/video/", "bilibili", "youtube", "youku", "iqiyi", "haokan", "v.qq.com"]): flags.append("VIDEO")

        if flags:
            video_count += 1
            print(f"  [{i}] {'|'.join(flags)} | {title[:60]}")
            print(f"       url={href[:120]}")
    if video_count == 0:
        print("  No video links found")
except Exception as e:
    print(f"  Error: {e}")

# === Part 4: Test 360kuai link specifically ===
print("\n=== Part 4: Check a 360kuai article URL ===")
test_url = "https://www.360kuai.com/pc/933d34e0b3062ee79?cota=3&kuai_so=1&refer_scene=so_3&sign=360_da20e874"
try:
    req4 = urllib.request.Request(test_url, headers=headers)
    resp4 = urllib.request.urlopen(req4, timeout=10, context=ctx)
    html4 = resp4.read().decode("utf-8", errors="replace")
    # Check if it's a video page
    is_video = "video" in html4[:2000].lower() or "播放" in html4[:2000] or "player" in html4[:2000].lower()
    # Check for actual article content
    has_article = "article" in html4[:3000].lower() or "content" in html4[:3000].lower() or "正文" in html4[:3000]
    print(f"  is_video_page={is_video}, has_article_content={has_article}")
    # Get title
    title_match = re.search(r'<title>([^<]+)</title>', html4)
    if title_match:
        print(f"  page title: {title_match.group(1)[:80]}")
except Exception as e:
    print(f"  Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_baidu_html.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_baidu_html.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
