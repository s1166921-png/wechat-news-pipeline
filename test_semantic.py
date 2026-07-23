"""Test semantic matching: keywords with qualifiers."""
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

# Test keywords where qualifier words matter
tests = [
    "退税慢",      # should find "why slow", not just "退税"
    "出口退税慢",   # same but longer
    "物流贵",      # should find "expensive logistics", not just "物流"
]

for kw in tests:
    body = json.dumps({"keyword": kw, "max_results": 10}).encode()
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode())

    print(f"\n{'='*60}")
    print(f"Keyword: {kw}  |  Total: {data['total']}")
    print(f"{'='*60}")
    for r in data["results"]:
        sc = r.get("score", 0)
        st = r["source_type"]
        hl = ""
        if kw.replace(" ", "") in r["title"].replace(" ", ""):
            hl = " ★ EXACT"
        print(f"  {sc:2d} {st:12s} | {r['title'][:90]}{hl}")
