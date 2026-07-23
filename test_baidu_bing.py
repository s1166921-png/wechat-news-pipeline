"""Test: 1) Find video links, 2) Implement Baidu News parsing."""
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

# === Part 1: Check search results WITH Bing for video links ===
print("=== Part 1: Search with ALL engines (check for video links) ===")
try:
    import urllib.request as ur
    req = ur.Request("http://127.0.0.1:8888/api/search",
        data=json.dumps({"keyword": kw, "max_results": 15}).encode(),
        headers={"Content-Type": "application/json"})
    resp = ur.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())
    for i, r in enumerate(data.get("results", [])[:15]):
        u = r.get("url", "")
        t = r.get("title", "")
        st = r.get("source_type", "")
        # Detailed video detection
        flags = []
        if "/video/" in u.lower() or "/v/" in u.lower(): flags.append("VIDEO_URL")
        if any(d in u.lower() for d in ["bilibili", "youtube", "youku", "iqiyi", "haokan", "v.qq.com", "tv.sohu", "mgtv"]): flags.append("VIDEO_SITE")
        if any(d in u.lower() for d in ["live.", "/live/", "zhibo"]): flags.append("LIVE")
        if "360kuai.com/pc/" in u: flags.append("360KUAI(maybe_video)")
        if "video" in t.lower() or "视频" in t: flags.append("TITLE_HAS_VIDEO")
        if any(d in u.lower() for d in ["zhidao.baidu", "wenwen.sogou", "ask.", "wenda.", "zhidao."]): flags.append("Q&A")
        if any(d in u.lower() for d in ["baike.baidu", "baike.sogou", "wiki"]): flags.append("WIKI")
        print(f"  [{i:2d}] type={st:12s} {'⚠️ '+','.join(flags) if flags else '✅'}")
        if flags:
            print(f"       title={t[:80]}")
            print(f"       url={u[:130]}")
except Exception as e:
    print(f"  Error: {e}")

# === Part 2: Baidu News - full parsing with dates ===
print("\n=== Part 2: Baidu News full parsing ===")
def search_baidu_news(kw, max_results=10):
    results = []
    try:
        url = f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn={max_results}&ie=utf-8"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        # Baidu news uses div.result for each item
        items = soup.select("div.result")
        if not items:
            items = soup.select("div.news-item, div[class*=result]")

        for item in items[:max_results]:
            # Title: h3 > a
            h3 = item.select_one("h3")
            if not h3:
                continue
            a = h3.select_one("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")

            if len(title) < 8:
                continue

            # Source and date: look in the result text
            full_text = item.get_text(strip=True)

            # Date patterns: "2026年07月20日" or "3小时前" or "1天前"
            date_str = ""
            abs_date = re.search(r'(\d{4}年\d{2}月\d{2}日)', full_text)
            rel_date = re.search(r'(\d+[小分天]时?前)', full_text)
            if abs_date:
                date_str = abs_date.group(1)
            elif rel_date:
                date_str = rel_date.group(1)

            # Source: usually before the date, 2-8 Chinese chars
            source = ""
            # Baidu puts source in <span class="c-author"> or similar
            author_el = item.select_one("span.c-author, span.author, p.c-author")
            if author_el:
                source = author_el.get_text(strip=True)
            if not source:
                src_match = re.search(r'([一-鿿]{2,8})\s*' + (re.escape(date_str) if date_str else r'\d'), full_text)
                if src_match:
                    source = src_match.group(1)

            # Snippet
            snippet_el = item.select_one("span.c-summary, div.c-summary, p.c-summary")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            if not snippet:
                snippet = full_text[len(title):][:200]

            results.append({
                "title": title,
                "url": href,
                "source": source if source else "百度新闻",
                "date": date_str,
                "source_type": "baidu_news",
                "snippet": snippet[:200],
            })

        return results
    except Exception as e:
        print(f"  Baidu News Error: {e}")
        return []

results = search_baidu_news(kw, 8)
print(f"  Results: {len(results)}")
for i, r in enumerate(results):
    print(f"  [{i}] date={r['date']:12s} src={r['source']:10s} | {r['title'][:70]}")

# === Part 3: Deep dive into Baidu News HTML structure ===
print("\n=== Part 3: Baidu News HTML structure ===")
try:
    url = f"https://news.baidu.com/ns?word={urllib.request.quote(kw)}&pn=0&cl=2&ct=1&tn=newstitle&rn=5&ie=utf-8"
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=12, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("div.result")
    if items:
        li = items[0]
        print("  First result HTML structure:")
        for el in li.find_all(True, limit=30):
            cls = " ".join(el.get("class", [])) if el.get("class") else ""
            txt = el.get_text(strip=True)[:60]
            if cls or el.name in ["h3", "a", "span", "div", "p"]:
                print(f"    <{el.name} class='{cls}'> {txt}")
except Exception as e:
    print(f"  Error: {e}")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_baidu.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_baidu.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])
ssh.close()
