"""Test WeChat search with multiple keywords."""
import urllib.request, json
import sys
sys.stdout.reconfigure(encoding='utf-8')

keywords = ["跨境电商", "temu", "亚马逊 FBA", "TikTok Shop"]

for kw in keywords:
    body = json.dumps({"keyword": kw, "max_results": 8, "engines": ["wechat"]}).encode()
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())
    print(f"\n{'='*60}")
    print(f"Keyword: {kw} | Total: {data['total']}")
    print(f"{'='*60}")
    for r in data["results"][:6]:
        sc = r.get("score", 0)
        dt = r.get("date", "?")
        src = r.get("source", "微信公众号")[:15]
        print(f"  sc={sc:2d} date={dt:12s} src={src:16s} | {r['title'][:90]}")
