"""Debug WeChat - why only 1 result?"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

stdin, stdout, stderr = ssh.exec_command('journalctl -u wechat-news --no-pager -n 30 2>&1')
print("=== Server Logs ===")
print(stdout.read().decode())

# Also run the search function directly
sftp = ssh.open_sftp()
debug_code = '''
import sys
sys.path.insert(0, '/opt/wechat-news-pipeline')
from app import _search_wechat

results = _search_wechat("temu 跨境电商", max_results=10)
print(f"\\n=== Direct _search_wechat() results: {len(results)} ===")
for i, r in enumerate(results):
    print(f"  [{i}] ({len(r['title'])}c) {r['title'][:100]}")
    print(f"       src={r.get('source','?')} url={r.get('url','')[:80]}")
'''
with sftp.file('/tmp/debug_wechat3.py', 'w') as f:
    f.write(debug_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /opt/wechat-news-pipeline && python3 /tmp/debug_wechat3.py 2>&1')
print("\n=== Direct function call ===")
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err[:1000])

ssh.close()
