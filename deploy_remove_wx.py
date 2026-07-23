"""Deploy: remove WeChat search engine."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Upload all changed files
sftp = ssh.open_sftp()
for local, remote in [
    ('D:/project/wechat-news-pipeline/app.py', '/opt/wechat-news-pipeline/app.py'),
    ('D:/project/wechat-news-pipeline/frontend/index.html', '/opt/wechat-news-pipeline/frontend/index.html'),
    ('D:/project/wechat-news-pipeline/frontend/style.css', '/opt/wechat-news-pipeline/frontend/style.css'),
]:
    print(f"Uploading {local}...")
    sftp.put(local, remote)
sftp.close()

# Restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart wechat-news && sleep 3 && echo OK')
print("Restart:", stdout.read().decode().strip())

# Quick test
print("\n=== Test: 'temu' search (no wechat engine) ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu","max_results":8}'"""
)
d = json.loads(stdout.read().decode())
print(f'Total: {d.get("total", 0)}')
for i, r in enumerate(d.get('results', [])[:8]):
    print(f'  [{i}] type={r.get("source_type","?"):12s} date={r.get("date","?")[:10]:10s} | {r["title"][:70]}')

print("\nDone! Open http://47.106.189.214/news/ to verify.")
ssh.close()
