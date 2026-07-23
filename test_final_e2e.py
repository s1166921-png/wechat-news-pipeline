"""Final E2E test: all engines together."""
import urllib.request, json

def test_search(keyword, engines=None):
    body = {"keyword": keyword, "max_results": 15}
    if engines is not None:
        body["engines"] = engines
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode())

    # Count by source type
    from collections import Counter
    types = Counter(r["source_type"] for r in data["results"])

    print(f"\n{'='*60}")
    print(f"Keyword: {keyword}")
    print(f"Engines: {engines or 'default (all)'}")
    print(f"Total: {data['total']}")
    print(f"By source: {dict(types)}")
    print(f"{'='*60}")
    for i, r in enumerate(data["results"][:12]):
        sc = r.get("score", 0)
        print(f"  [{i:2d}] sc={sc:2d} {r['source_type']:12s} date={r.get('date','?'):12s} | {r['title'][:85]}")

# Test with all default engines
test_search("temu 跨境电商")

# Test with only Chinese engines
test_search("独立站 出海", ["360search", "sogou_news", "ebrun"])
