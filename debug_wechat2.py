"""Debug WeChat - check HTML structure of first item."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

sftp = ssh.open_sftp()
debug_code = '''
import urllib.request, ssl
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10, context=ctx)
html = resp.read().decode("utf-8", errors="replace")
soup = BeautifulSoup(html, "lxml")
items = soup.select("ul.news-list li")

for i, li in enumerate(items[:3]):
    print(f"\\n=== Item {i} ===")
    # Show full HTML of the li
    li_html = str(li)
    print(f"LI HTML (first 800c): {li_html[:800]}")

    # Check for nested elements inside <a>
    a_tags = li.select("a")
    for j, a in enumerate(a_tags):
        print(f"  A[{j}] href={a.get('href','')[:80]}")
        print(f"  A[{j}] text='{a.get_text(strip=True)[:120]}'")
        # Check children
        for child in a.children:
            if hasattr(child, 'name'):
                print(f"    Child <{child.name}>: '{child.get_text(strip=True)[:120]}'")

    # Try to find title in any element
    for sel in ["h3", ".tit", ".title", "[class*=title]", "[class*=tit]"]:
        el = li.select_one(sel)
        if el:
            print(f"  {sel}: '{el.get_text(strip=True)[:120]}'")

    # Get all text nodes
    print(f"  Full LI text: '{li.get_text(strip=True)[:200]}'")
'''
with sftp.file('/tmp/debug_wechat2.py', 'w') as f:
    f.write(debug_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/debug_wechat2.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:500])

ssh.close()
