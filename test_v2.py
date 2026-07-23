"""E2E test: individual + multi-engine comparison."""
import urllib.request, json, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

keywords = ["temu 跨境电商", "亚马逊 选品"]

for kw in keywords:
    # Multi-engine (all defaults)
    body = json.dumps({"keyword": kw, "max_results": 12}).encode()
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=90)
    data = json.loads(resp.read().decode())
    types = Counter(r["source_type"] for r in data["results"])

    print(f"\n{'='*60}")
    print(f"Keyword: {kw} | Total: {data['total']} | By type: {dict(types)}")
    print(f"{'='*60}")
    for r in data["results"]:
        sc = r.get("score", 0)
        st = r["source_type"]
        dt = r.get("date", "?")[:12]
        src = r.get("source", "")[:16]
        print(f"  sc={sc:2d} {st:12s} date={dt:12s} src={src:16s} | {r['title'][:90]}")
