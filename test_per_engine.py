"""Test each engine individually."""
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

for eng in ['wechat', '36kr', 'ebrun']:
    for kw in ['temu 跨境电商', '亚马逊 选品']:
        body = json.dumps({'keyword': kw, 'max_results': 5, 'engines': [eng]}).encode()
        req = urllib.request.Request('http://127.0.0.1:8888/api/search',
            data=body, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=25)
        data = json.loads(resp.read().decode())
        print(f'[{eng:6s}] "{kw}" -> {data["total"]} results')
        for r in data['results'][:3]:
            print(f'         sc={r.get("score",0):2d} | {r["title"][:90]}')
        print()
