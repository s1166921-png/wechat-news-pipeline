"""Deploy app.py to server and test search results."""
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Upload
sftp = ssh.open_sftp()
sftp.put('D:/project/wechat-news-pipeline/app.py', '/opt/wechat-news-pipeline/app.py')
sftp.close()
print('[OK] app.py uploaded')

# Restart
stdin, stdout, stderr = ssh.exec_command('systemctl restart wechat-news && sleep 2 && systemctl is-active wechat-news')
status = stdout.read().decode().strip()
print(f'Service status: {status}')

# Test search API - save raw JSON to file to avoid encoding issues
stdin, stdout, stderr = ssh.exec_command(
    'curl -s "http://127.0.0.1:8888/api/search" '
    '-H "Content-Type: application/json" '
    '-d \'{"keyword":"temu","engines":["360"]}\''
)
resp = json.loads(stdout.read().decode())
results = resp.get('results', [])

# Write results to file as UTF-8
with open('D:/project/wechat-news-pipeline/test_results.json', 'w', encoding='utf-8') as f:
    json.dump([{'title': r['title'], 'title_len': len(r['title']), 'source': r.get('source','?')} for r in results[:8]], f, ensure_ascii=False, indent=2)

print(f'Total results: {len(results)}')
for i, r in enumerate(results[:8]):
    t = r['title']
    src = r.get('source', '?')
    print(f'[{i}] len={len(t):3} src={src}')
    print(f'    {t[:120]}')
    if len(t) > 120:
        print(f'    ...{t[-40:]}')
    print()

ssh.close()
print('Done!')
