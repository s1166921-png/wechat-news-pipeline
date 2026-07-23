"""Diagnose search for keyword '出口退税慢'."""
import urllib.request, json

keyword = "出口退税慢"

# Test each engine individually
engines = ["360search", "sogou_news", "ebrun", "36kr", "bing", "google_news"]

print(f"=== Diagnosing: '{keyword}' ===\n")

for eng in engines:
    try:
        body = json.dumps({"keyword": keyword, "max_results": 8, "engines": [eng]}).encode()
        req = urllib.request.Request("http://127.0.0.1:8888/api/search",
            data=body, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read().decode())
        count = data.get("total", 0)
        print(f"[{eng}] {count} results")
        for r in data.get("results", [])[:5]:
            print(f"  sc={r.get('score','?')} date={r.get('date','?'):12s} | {r['title'][:90]}")
    except Exception as e:
        print(f"[{eng}] ERROR: {e}")
    print()

# Also test what _build_search_queries does
print("=== Query Expansion ===")
from app import _build_search_queries
for q, eng in _build_search_queries(keyword):
    print(f"  → '{q}' ({eng})")
