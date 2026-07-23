"""Quick test of WeChat search."""
import urllib.request, json
import sys
sys.stdout.reconfigure(encoding='utf-8')

body = json.dumps({"keyword": "出口退税", "max_results": 5, "engines": ["wechat"]}).encode()
req = urllib.request.Request("http://127.0.0.1:8888/api/search",
    data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=25)
data = json.loads(resp.read().decode())
print(f"Total: {data['total']}")
for r in data["results"]:
    print(f"  sc={r.get('score','?')} {r['source_type']:8s} date={r.get('date','?')} | {r['title'][:100]}")
