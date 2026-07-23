"""Deploy all changes and test."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

sftp = ssh.open_sftp()
files = [
    ('D:/project/wechat-news-pipeline/app.py', '/opt/wechat-news-pipeline/app.py'),
    ('D:/project/wechat-news-pipeline/frontend/app.js', '/opt/wechat-news-pipeline/frontend/app.js'),
    ('D:/project/wechat-news-pipeline/frontend/style.css', '/opt/wechat-news-pipeline/frontend/style.css'),
    ('D:/project/wechat-news-pipeline/frontend/index.html', '/opt/wechat-news-pipeline/frontend/index.html'),
]
for local, remote in files:
    sftp.put(local, remote)
    print(f'[OK] {local.split("/")[-1]}')
sftp.close()

# Restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart wechat-news && sleep 2 && systemctl is-active wechat-news')
print(f'Service: {stdout.read().decode().strip()}')

# Test search
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://127.0.0.1:8888/api/search" '
    '-H "Content-Type: application/json" '
    '-d \'{"keyword":"temu","engines":["360"]}\''
)
resp = json.loads(stdout.read().decode())
results = resp.get('results', [])
print(f'\n=== {len(results)} results for "temu" ===')
for i, r in enumerate(results[:5]):
    t = r['title']
    print(f'[{i}] ({len(t)}c) {t[:120]}')

# Test refresh mode
print('\n=== Refresh mode test ===')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://127.0.0.1:8888/api/search" '
    '-H "Content-Type: application/json" '
    '-d \'{"keyword":"temu","engines":["360"],"refresh":true}\''
)
resp2 = json.loads(stdout.read().decode())
results2 = resp2.get('results', [])
for i, r in enumerate(results2[:5]):
    t = r['title']
    print(f'[{i}] ({len(t)}c) {t[:120]}')

ssh.close()
print('\nDone!')
