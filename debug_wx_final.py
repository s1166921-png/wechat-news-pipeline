"""Full debug: run search and check all logs."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.106.189.214', username='root', password='Yzc12345', timeout=15)

# Trigger search
stdin, stdout, stderr = ssh.exec_command(
    """curl -s "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"temu 跨境电商","max_results":10,"engines":["wechat"]}' > /dev/null && sleep 1"""
)
stdout.read()

# Check ALL recent logs
stdin, stdout, stderr = ssh.exec_command('journalctl -u wechat-news --no-pager -n 40 2>&1')
print("=== ALL LOGS ===")
print(stdout.read().decode()[-3000:])

# Also run the function directly with the correct Python env
stdin, stdout, stderr = ssh.exec_command(
    'cd /opt/wechat-news-pipeline && python3 -c "'
    'import sys; sys.path.insert(0,\".\"); '
    'from app import _search_wechat; '
    'r = _search_wechat(\"temu 跨境电商\", max_results=10); '
    'print(f\"Direct call: {len(r)} results\"); '
    'for i,x in enumerate(r): print(f\"  [{i}] ({len(x[chr(116)+chr(105)+chr(116)+chr(108)+chr(101)])}c) {x[chr(116)+chr(105)+chr(116)+chr(108)+chr(101)][:80]}\")'
    '" 2>&1'
)
print("\n=== Direct function call ===")
print(stdout.read().decode())
print(stderr.read().decode()[:500])

ssh.close()
