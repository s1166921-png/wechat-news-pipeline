"""Deploy and test freshness improvements."""
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

# Test 1: WeChat only - check freshness
print("\n=== Test 1: 'temu 跨境电商' WeChat only (freshness check) ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu 跨境电商","max_results":10,"engines":["wechat"]}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {d.get("total", 0)}')
for i, r in enumerate(d.get('results', [])[:10]):
    date = r.get('date', '?')
    score = r.get('score', 0)
    print(f'  [{i}] date={date:10s} score={score:3d} | src={r.get("source","?"):15s} | {r["title"][:80]}')

# Test 2: 360 + Sogou only - check freshness
print("\n=== Test 2: 'temu 跨境电商' 360+Sogou (freshness check) ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu 跨境电商","max_results":10,"engines":["360search","sogou_news"]}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {d.get("total", 0)}')
for i, r in enumerate(d.get('results', [])[:10]):
    date = r.get('date', '?')
    score = r.get('score', 0)
    print(f'  [{i}] date={date:10s} score={score:3d} | src={r.get("source_type","?"):12s} | {r["title"][:80]}')

# Test 3: All engines - check freshness mix
print("\n=== Test 3: 'temu 跨境电商' ALL engines ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu 跨境电商","max_results":15}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {d.get("total", 0)}')
for i, r in enumerate(d.get('results', [])[:15]):
    date = r.get('date', '?')
    score = r.get('score', 0)
    st = r.get('source_type', '?')
    print(f'  [{i:2d}] date={str(date):10s} score={score:3d} | type={st:12s} | {r["title"][:75]}')

# Check server logs
print("\n=== Server logs (WeChat lines) ===")
stdin, stdout, stderr = ssh.exec_command('journalctl -u wechat-news --no-pager -n 30 2>&1 | grep -E "\\[WeChat\\]|\\[search\\]"')
print(stdout.read().decode())

ssh.close()
