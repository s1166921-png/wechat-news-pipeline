"""Deploy and test all changes."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Upload
sftp = ssh.open_sftp()
for f in ['app.py', 'frontend/app.js', 'frontend/style.css', 'frontend/index.html']:
    local = f'D:/project/wechat-news-pipeline/{f}'
    remote = f'/opt/wechat-news-pipeline/{f}'
    sftp.put(local, remote)
    print(f'[OK] {f}')
sftp.close()

# Restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart wechat-news && sleep 3 && systemctl is-active wechat-news')
print(f'Service: {stdout.read().decode().strip()}')

def api_test(desc, body):
    stdin, stdout, stderr = ssh.exec_command(
        f'curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d \'{json.dumps(body)}\''
    )
    d = json.loads(stdout.read().decode())
    results = d.get('results', [])
    print(f'\n=== {desc} ({len(results)} results) ===')
    for i, r in enumerate(results[:5]):
        st = r.get('source_type', '?')
        src = r.get('source', '?')
        t = r['title']
        print(f'  [{i}] ({st} | {src}) ({len(t)}c) {t[:120]}')

# Test 1: Default
api_test('Default engines', {"keyword": "temu", "max_results": 5})

# Test 2: WeChat only
api_test('WeChat only', {"keyword": "temu 跨境电商", "max_results": 5, "engines": ["wechat"]})

# Test 3: 360 only
api_test('360 only', {"keyword": "temu", "max_results": 3, "engines": ["360search"]})

# Test 4: All engines including WeChat
api_test('All engines', {"keyword": "temu", "max_results": 5, "engines": ["all"]})

ssh.close()
print('\nDone!')
