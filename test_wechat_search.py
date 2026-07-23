"""Test Sogou WeChat search scraping on the server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Upload test script
test_code = '''
import requests, re, json
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
url = f"https://weixin.sogou.com/weixin?type=2&query={requests.utils.quote(kw)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

print(f"Fetching: {url}")
r = requests.get(url, headers=headers, timeout=15)
print(f"Status: {r.status_code}, Len: {len(r.text)}")

# Save HTML for analysis
with open("/tmp/wechat_search.html", "w", encoding="utf-8") as f:
    f.write(r.text)

soup = BeautifulSoup(r.text, "lxml")

# Try different selectors
selectors = [
    "div.news-box ul.news-list li",
    "ul.news-list li",
    "div.news-list li",
    "div.txt-box",
    "div.news-item",
    "li[id^=sogou]",
]

for sel in selectors:
    items = soup.select(sel)
    print(f"  {sel}: {len(items)} items")
    if items:
        for i, item in enumerate(items[:3]):
            print(f"    [{i}] {item.get_text(strip=True)[:150]}")
        break

# Also look for any link with article-like structure
all_links = soup.select("a[href^=http]")
wechat_links = [a for a in all_links if "mp.weixin.qq.com" in a.get("href", "")]
print(f"\\nWeChat article links found: {len(wechat_links)}")
for a in wechat_links[:5]:
    href = a.get("href", "")
    text = a.get_text(strip=True)
    print(f"  {text[:120]}")
    print(f"  -> {href[:120]}")

# Try to find the main content area
print("\\n=== Page structure ===")
for tag in ["div.news-box", "ul.news-list", "div.news-list", "div.results", "div#main"]:
    el = soup.select_one(tag)
    if el:
        print(f"  {tag}: FOUND, {len(el.get_text(strip=True))} chars")
        # Show first child structure
        for child in list(el.children)[:5]:
            if hasattr(child, "name"):
                print(f"    <{child.name} class={child.get('class', '')}>: {child.get_text(strip=True)[:100]}")

print("\\n=== All li elements ===")
all_li = soup.select("li")
for li in all_li[:5]:
    print(f"  id={li.get('id','')} class={li.get('class','')}: {li.get_text(strip=True)[:150]}")

print("\\nDone!")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wechat.py', 'w') as f:
    f.write(test_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /opt/wechat-news-pipeline && python3 /tmp/test_wechat.py 2>&1')
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:")
print(out[-3000:] if len(out) > 3000 else out)
if err:
    print("STDERR:", err[:1000])

ssh.close()
