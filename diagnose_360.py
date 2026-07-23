"""Diagnose 360 search result HTML structure on the server."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Fetch raw 360 HTML and analyze
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "https://news.so.com/ns?q=temu" -H "User-Agent: Mozilla/5.0" | '
    'python3 -c "'
    'import sys, re;'
    'from bs4 import BeautifulSoup;'
    'html = sys.stdin.read();'
    'soup = BeautifulSoup(html, \"lxml\");'
    'wrap = soup.select_one(\"div.result_wrap\");'
    'items = wrap.select(\"a[href^=http]\") if wrap else [];'
    'print(f\"Total items: {len(items)}\");'
    'for i, a in enumerate(items[:5]):'
    '    print(f\"\\\\n=== Item {i} ===\");'
    '    print(f\"HREF: {a.get(chr(104)+chr(114)+chr(101)+chr(102), chr(63))[:100]}\");'
    '    print(f\"TEXT: {a.get_text(strip=True)[:200]}\");'
    '    print(f\"HTML: {str(a)[:500]}\");'
    '    # Check parent structure'
    '    p = a.parent;'
    '    for _ in range(3):'
    '        if p:'
    '            cls = p.get(\"class\",[]);'
    '            tag = p.name;'
    '            txt = p.get_text(strip=True)[:150];'
    '            print(f\"PARENT <{tag} class={cls}>: {txt}\");'
    '            p = p.parent;'
    '"'
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:500])

ssh.close()
