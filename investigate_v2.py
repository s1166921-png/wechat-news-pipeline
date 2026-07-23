"""Test new engine options: Bing News, Baidu News, Toutiao."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_script = r'''
import urllib.request, ssl, re, json
from bs4 import BeautifulSoup
from datetime import datetime

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

kw = "temu 跨境电商"

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return resp.read().decode("utf-8", errors="replace")

# === Part 1: Bing News (RSS feed) ===
print("=== Bing News RSS ===")
try:
    rss_url = f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&format=RSS&setlang=zh-cn"
    html = fetch(rss_url, 15)
    soup = BeautifulSoup(html, "xml")
    items = soup.select("item")
    print(f"  Items: {len(items)}")
    for item in items[:6]:
        title = (item.select_one("title") or "").get_text(strip=True) if item.select_one("title") else ""
        link = (item.select_one("link") or "").get_text(strip=True) if item.select_one("link") else ""
        pubdate = (item.select_one("pubDate") or "").get_text(strip=True) if item.select_one("pubDate") else ""
        source = (item.select_one("source") or "").get_text(strip=True) if item.select_one("source") else ""
        print(f"    [{source}] {title[:70]}")
        print(f"    date={pubdate[:25]} link={link[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 2: Baidu News ===
print("\n=== Baidu News ===")
try:
    baidu_url = f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=20&ie=utf-8"
    html = fetch(baidu_url, 15)
    soup = BeautifulSoup(html, "lxml")

    # Baidu news uses various selectors
    items = []
    for sel in [".result", "div.result", ".news-item"]:
        items = soup.select(sel)
        if len(items) >= 3:
            break
    if not items:
        # Try finding h3 tags with links
        items = soup.select("h3.c-title a, h3 a")

    print(f"  Items: {len(items)}")
    for item in items[:6]:
        a = item.select_one("a") if item.name != "a" else item
        if not a:
            a = item
        title = a.get_text(strip=True)
        href = a.get("href", "")
        # Baidu news also shows source & date
        parent_text = item.parent.get_text(strip=True) if item.parent else ""
        date_match = re.search(r'(\d{4}年\d{2}月\d{2}日|\d+[小分天]时?前)', parent_text)
        src_match = re.search(r'([一-鿿]{2,8})(?:\s+\d|$)', parent_text)
        print(f"    {title[:70]}")
        print(f"    src={src_match.group(1) if src_match else '?'} date={date_match.group(1) if date_match else '?'} url={href[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 3: Toutiao ===
print("\n=== Toutiao ===")
try:
    toutiao_url = f"https://so.toutiao.com/search?dvpf=pc&source=input&keyword={urllib.request.quote(kw)}"
    html = fetch(toutiao_url, 15)

    # Try extracting JSON data
    json_matches = re.findall(r'"title"\s*:\s*"([^"]+)"', html)
    url_matches = re.findall(r'"article_url"\s*:\s*"([^"]+)"', html)
    # Also try HTML parsing
    soup = BeautifulSoup(html, "lxml")
    html_items = soup.select("a[href*='/article/'], a[href*='/news/'], .result a, h2 a, h3 a")

    print(f"  JSON titles: {len(json_matches)}, JSON urls: {len(url_matches)}, HTML links: {len(html_items)}")
    for i, t in enumerate(json_matches[:5]):
        u = url_matches[i] if i < len(url_matches) else "?"
        print(f"    {t[:70]}")
        print(f"    url={u[:120]}")
    if not json_matches and html_items:
        for a in html_items[:5]:
            t = a.get_text(strip=True)
            u = a.get("href", "")
            if len(t) > 10:
                print(f"    {t[:70]}")
                print(f"    url={u[:120]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 4: Check API results for video links directly ===
print("\n=== Part 4: Quick API check (shorter timeout) ===")
try:
    import urllib.request as ur
    req = ur.Request("http://127.0.0.1:8888/api/search",
        data=json.dumps({"keyword": kw, "max_results": 8, "engines": ["360search", "sogou_news"]}).encode(),
        headers={"Content-Type": "application/json"})
    resp = ur.urlopen(req, timeout=20)
    data = json.loads(resp.read().decode())
    for i, r in enumerate(data.get("results", [])[:8]):
        u = r.get("url", "")
        flags = []
        if "/video/" in u or "-video-" in u.lower(): flags.append("VIDEO")
        if any(d in u for d in ["bilibili.com", "youtube.com", "youku.com", "iqiyi.com", "v.qq.com", "haokan.baidu.com"]): flags.append("VIDEO_SITE")
        if any(d in u for d in ["zhidao.baidu.com", "wenwen.sogou.com", "ask.", "wenda."]): flags.append("Q&A")
        if any(d in u for d in ["baike.baidu.com", "baike.sogou.com", "wiki"]): flags.append("WIKI")
        if "live" in u.lower() and ("/" in u): flags.append("LIVE")
        if flags:
            print(f"  [{i}] FLAGS={flags}")
            print(f"       url={u[:130]}")
        else:
            print(f"  [{i}] OK | {r.get('source_type','?')} | {u[:100]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 5: Test Bing News HTML (not RSS) ===
print("\n=== Part 5: Bing News HTML page ===")
try:
    bing_news_url = f"https://www.bing.com/news/search?q={urllib.request.quote(kw)}&setlang=zh-cn"
    html = fetch(bing_news_url, 15)
    soup = BeautifulSoup(html, "lxml")

    # Bing news card selectors
    for sel in [".news-card", ".news-card-body", "a.title", ".news-title", "a[href*='article']"]:
        items = soup.select(sel)
        if len(items) >= 3:
            print(f"  Selector '{sel}': {len(items)} items")
            for item in items[:4]:
                t = item.get_text(strip=True)[:70]
                u = item.get("href", "")
                print(f"    {t}")
                print(f"    url={u[:120]}")
            break
    else:
        # Check if there are ANY article links
        all_links = soup.select("a[href*='http']")
        article_links = [a for a in all_links if len(a.get_text(strip=True)) > 15]
        print(f"  Article-like links: {len(article_links)}")
        for a in article_links[:5]:
            print(f"    {a.get_text(strip=True)[:70]}")
            print(f"    url={a.get('href','')[:120]}")
except Exception as e:
    print(f"  Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/investigate2.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/investigate2.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
