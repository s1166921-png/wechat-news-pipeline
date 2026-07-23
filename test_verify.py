"""Quick verification of all 4 fixes."""
import urllib.request, json, collections, re, sys
sys.stdout.reconfigure(encoding='utf-8')

for kw in ["跨境电商", "亚马逊 FBA"]:
    body = json.dumps({"keyword": kw, "max_results": 15}).encode()
    req = urllib.request.Request("http://127.0.0.1:8888/api/search",
        data=body, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=90)
    data = json.loads(resp.read().decode())

    domains = collections.Counter()
    types = collections.Counter()
    for r in data["results"]:
        m = re.search(r'https?://([^/:]+)', r["url"])
        domains.update([m.group(1) if m else "unknown"])
        types.update([r["source_type"]])

    scores = [r.get("score", 0) for r in data["results"]]

    print(f"\n{'='*60}")
    print(f"Keyword: {kw}")
    print(f"Total: {data['total']}  |  Domains: {len(domains)}  |  Score: {min(scores)}-{max(scores)}")
    print(f"By type: {dict(types)}")
    print(f"By domain: {dict(domains.most_common())}")
    print(f"{'='*60}")

    for r in data["results"]:
        sc = r.get("score", 0)
        st = r["source_type"]
        dt = r.get("date", "?")[:12]
        # Show if URL is Google News redirect or direct
        url_type = " [GN redirect]" if "news.google.com/rss" in r.get("url", "") else ""
        print(f"  {sc:2d} {st:12s} date={dt:12s} | {r['title'][:85]}{url_type}")
