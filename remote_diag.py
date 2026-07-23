"""Fetch and analyze 360 search result HTML structure."""
import sys, re, json
from bs4 import BeautifulSoup
import requests

url = 'https://news.so.com/ns?q=temu'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
html = requests.get(url, headers=headers, timeout=15).text

soup = BeautifulSoup(html, 'lxml')
wrap = soup.select_one('div.result_wrap')
if wrap:
    items = wrap.select('a[href^=http]')
else:
    items = soup.select('li.res-list a[href^=http]')

print(f'Total items: {len(items)}')
for i, a in enumerate(items[:6]):
    link_text = a.get_text(strip=True)
    href = a.get('href', '')

    # Show full HTML of the <a> tag
    a_html = str(a)

    # Check for any attributes that might contain the title
    attrs = dict(a.attrs)

    # Check parent elements for additional data
    parent_texts = []
    p = a.parent
    for _ in range(4):
        if p:
            parent_texts.append(f'  <{p.name} class={p.get("class",[])})>: {p.get_text(strip=True)[:120]}')
            p = p.parent

    print(f'\n{"="*60}')
    print(f'[{i}] HREF: {href[:100]}')
    print(f'    ATTRS: {json.dumps(attrs, ensure_ascii=False)}')
    print(f'    LINK_TEXT ({len(link_text)}c):')
    print(f'    {link_text}')
    print(f'    HTML: {a_html[:400]}')
    print(f'    PARENTS:')
    for pt in parent_texts:
        print(pt)
