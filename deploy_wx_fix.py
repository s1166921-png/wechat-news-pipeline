"""Deploy rewritten _search_wechat and test."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Upload
sftp = ssh.open_sftp()
sftp.put('D:/project/wechat-news-pipeline/app.py', '/opt/wechat-news-pipeline/app.py')
sftp.close()

# Restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart wechat-news && sleep 3 && echo OK')
print("Restart:", stdout.read().decode().strip())

# Test 1: WeChat search with "temu 跨境电商" (should now include quality sources via query expansion)
print("\n=== Test 1: 'temu 跨境电商' WeChat only ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu 跨境电商","max_results":10,"engines":["wechat"]}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {d.get("total", 0)}')
for i, r in enumerate(d.get('results', [])[:10]):
    print(f'  [{i}] src={r.get("source","?"):12s} | {r["title"][:80]}')

# Test 2: WeChat search with "temu" only
print("\n=== Test 2: 'temu' WeChat only ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu","max_results":10,"engines":["wechat"]}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {d.get("total", 0)}')
for i, r in enumerate(d.get('results', [])[:10]):
    print(f'  [{i}] src={r.get("source","?"):12s} | {r["title"][:80]}')

# Test 3: Check logs
print("\n=== Server logs ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u wechat-news --no-pager -n 15 2>&1')
print(stdout.read().decode()[-1500:])

ssh.close()
