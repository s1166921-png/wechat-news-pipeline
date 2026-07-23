"""Test Sogou WeChat search - deep dive into structure."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

test_code = '''
import requests, re, json
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
url = f"https://weixin.sogou.com/weixin?type=2&query={requests.utils.quote(kw)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

r = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(r.text, "lxml")

# Get li items from news-list
items = soup.select("ul.news-list li")
print(f"Total items: {len(items)}\\n")

for i, li in enumerate(items[:8]):
    # Get all links
    links = li.select("a")
    print(f"--- Item {i} ---")
    print(f"  LI HTML (first 500c): {str(li)[:500]}")

    # Get title from h3 or first link
    title_el = li.select_one("h3 a, h4 a, .txt-box h3 a, a[href*=weixin]")
    if not title_el:
        # Find the main title link
        for a in links:
            txt = a.get_text(strip=True)
            href = a.get("href", "")
            if len(txt) >= 10:
                title_el = a
                break

    if title_el:
        print(f"  Title: {title_el.get_text(strip=True)[:120]}")
        print(f"  HREF: {title_el.get('href', '')[:120]}")

    # Get source (公众号名称)
    src_el = li.select_one(".s-p, .account, .wx-name, span[class*=account]")
    if not src_el:
        # Try to find source from text pattern
        full_text = li.get_text(strip=True)
        # Source is usually at the end: "...公众号名 日期"
        src_match = re.search(r'([一-鿿\w]{2,20})\s*(\d+天前|\d+小时前|\d{4}-\d{2}-\d{2})', full_text)
        if src_match:
            print(f"  Source (regex): {src_match.group(1)} | Date: {src_match.group(2)}")

    # Get snippet/description
    desc_el = li.select_one(".txt-info, .s-p, p[class*=desc], p[class*=summary]")
    if desc_el:
        print(f"  Desc: {desc_el.get_text(strip=True)[:150]}")

    # Full text
    print(f"  Full text: {li.get_text(strip=True)[:200]}")

    # Check for any mp.weixin.qq.com URLs
    for a in links:
        href = a.get("href", "")
        if "mp.weixin.qq.com" in href:
            print(f"  DIRECT WX URL: {href}")

    # Check data-src or other attrs
    for attr in ["data-url", "data-href", "data-link"]:
        val = li.get(attr, "")
        if val:
            print(f"  {attr}: {val[:120]}")

    print()

print("\\n=== Check for anti-bot / captcha ===")
if "请输入验证码" in r.text or "antibot" in r.text.lower():
    print("  CAPTCHA detected!")
else:
    print("  No captcha detected")

# Save full HTML for deeper analysis
with open("/tmp/wechat_search_full.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("\\nFull HTML saved to /tmp/wechat_search_full.html")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_wechat2.py', 'w') as f:
    f.write(test_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /opt/wechat-news-pipeline && python3 /tmp/test_wechat2.py 2>&1')
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:500])

ssh.close()
