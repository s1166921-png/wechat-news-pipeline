"""Quick test of new engines locally."""
import urllib.request, json

def test_search(keyword, engines):
    body = json.dumps({"keyword": keyword, "max_results": 10, "engines": engines}).encode()
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())
    print(f"\nKeyword: {keyword} | Engines: {engines} | Total: {data['total']}")
    for i, r in enumerate(data["results"][:10]):
        print(f"  [{i}] {r['source_type']:10s} date={r.get('date','?'):12s} | {r['title'][:90]}")

# Test 1: Ebrun + 36kr
test_search("temu 跨境电商", ["ebrun", "36kr"])

# Test 2: All default engines (includes ebrun + 36kr now)
test_search("亚马逊 运营", [])

# Test 3: Just 360 + ebrun (most Chinese-focused)
test_search("TikTok Shop", ["360search", "ebrun"])
