"""Test full multi-engine search with WeChat."""
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

keywords = ["TikTok Shop", "亚马逊 FBA", "出口退税"]

for kw in keywords:
    body = json.dumps({"keyword": kw, "max_results": 12}).encode()
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode())

    # Count by source type
    from collections import Counter
    types = Counter(r["source_type"] for r in data["results"])

    print(f"\n{'='*60}")
    print(f"Keyword: {kw} | Total: {data['total']} | By type: {dict(types)}")
    print(f"{'='*60}")
    for r in data["results"]:
        sc = r.get("score", 0)
        st = r["source_type"]
        dt = r.get("date", "?")[:12]
        print(f"  sc={sc:2d} {st:12s} date={dt:12s} | {r['title'][:95]}")
