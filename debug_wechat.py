"""Debug WeChat search directly on server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

sftp = ssh.open_sftp()
debug_code = '''
import urllib.request, ssl, re
from bs4 import BeautifulSoup

kw = "temu 跨境电商"
url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.request.quote(kw)}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    html = resp.read().decode("utf-8", errors="replace")
    print(f"Status: {resp.status}, HTML len: {len(html)}")
    print(f"First 500 chars: {html[:500]}")
    print(f"Contains 'news-list': {'news-list' in html}")
    print(f"Contains 'news-box': {'news-box' in html}")
    print(f"Contains '验证码': {'验证码' in html}")
    print(f"Contains 'antibot': {'antibot' in html.lower()}")

    soup = BeautifulSoup(html, "lxml")

    # Try all possible selectors
    for sel in ["ul.news-list li", "div.news-box li", "div.txt-box li", "li[id^=sogou]", "div.news-list li", "li"]:
        items = soup.select(sel)
        if items:
            print(f"  {sel}: {len(items)} items")
            li = items[0]
            print(f"    LI text: {li.get_text(strip=True)[:120]}")
            a = li.select_one("a")
            if a:
                print(f"    A href: {a.get('href', '')[:100]}")
                print(f"    A text: {a.get_text(strip=True)[:120]}")
            break
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
'''
with sftp.file('/tmp/debug_wechat.py', 'w') as f:
    f.write(debug_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/debug_wechat.py 2>&1')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:500])

ssh.close()
