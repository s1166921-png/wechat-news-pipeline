"""Quick fix test."""
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
print(stdout.read().decode().strip())

# Test WeChat search - check raw response and logs
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu","max_results":10,"engines":["wechat"]}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {len(d.get("results",[]))}')
for i, r in enumerate(d.get('results', [])[:10]):
    print(f'  [{i}] ({r.get("source_type","?")}) src={r.get("source","?")} title={r["title"][:100]}')

# Also check server logs
stdin, stdout, stderr = ssh.exec_command('journalctl -u wechat-news --no-pager -n 20 2>&1 | grep -E "\\[WeChat\\]|\\[search\\]"')
print('\nLogs:')
print(stdout.read().decode())

ssh.close()
