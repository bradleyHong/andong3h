#!/usr/bin/env python3
"""본사(3h.co.kr) ↔ 우리 홈페이지 비교 점검.

- 지압침대 카테고리 제품: 가격 변동 / 신제품 / 본사에서 빠진 제품
- 언론보도: 우리 '최신 소식'에 없는 새 글

사용법:
  python3 scripts/hq_sync.py            # 비교 결과만 출력
  python3 scripts/hq_sync.py --apply    # 가격 변동을 index.html·llms.txt에 반영
결과 JSON은 scripts/hq_sync_report.json 에 저장된다. 변경이 없으면 종료 코드 0, 있으면 10.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HQ = 'https://www.3h.co.kr'
UA = 'Mozilla/5.0 (3H Andong sync)'


def fetch(path):
    return subprocess.run(['curl', '-sL', '--max-time', '25', '--retry', '2', '-A', UA, HQ + path],
                          capture_output=True, text=True).stdout


def text(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def hq_products():
    """지압침대 카테고리 제품 {idx: {name, price, code}}"""
    lst = fetch('/sub/02_product/product_01.php?listCnt=99999&orderBy=sort')
    idxs = list(dict.fromkeys(re.findall(r'product_01_V\.php\?idx=(\d+)', lst)))
    print(f'본사 목록: 상품 {len(idxs)}개, 목록 페이지 {len(lst)}바이트', flush=True)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        pages = dict(zip(idxs, ex.map(lambda i: fetch(f'/sub/02_product/product_01_V.php?idx={i}'), idxs)))
    out = {}
    for idx in idxs:
        h = pages[idx]
        i = h.find('<div class="con_top">')
        top = h[i:h.find('<div class="con_botm">', i)]
        if '3H지압침대' not in top:
            continue
        name = text(re.search(r'<div class="title[^"]*">(.*?)</div>', top, re.S).group(1))
        m = re.search(r'([\d,]+)원', text(top))
        code = re.search(r'상품코드</span>\s*<span[^>]*>(.*?)</span>', top, re.S)
        out[idx] = {'name': name, 'price': int(m.group(1).replace(',', '')) if m else None,
                    'code': text(code.group(1)) if code else ''}
    return out


def hq_news(limit_pages=2):
    items = []
    for p in range(1, limit_pages + 1):
        h = fetch(f'/sub/04_media/media_01.php?page={p}')
        for m in re.finditer(r'media_01_V\.php\?idx=(\d+)">(.*?)</a>', h, re.S):
            cells = [c for c in re.split(r'\s*\|\s*', text(re.sub(r'</li>', ' | ', m.group(2)))) if c]
            if len(cells) >= 3:
                items.append({'idx': int(m.group(1)), 'title': cells[1], 'date': cells[2]})
    return items


def main():
    apply = '--apply' in sys.argv
    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    ours = {idx: {'name': n, 'price': int(p)} for n, p, idx in
            re.findall(r"name:'([^']+)',model:'[^']+',size:'[^']+',img:'[^']+',rental:(?:true|false),price:(\d+),idx:(\d+)", index)}
    hq = hq_products()
    if len(hq) < max(5, len(ours) // 2):
        # 본사 접속 실패(차단·점검 등)로 목록을 못 읽은 경우. 절대 반영하지 않는다.
        print(f'본사 제품을 {len(hq)}종만 읽음. 접속 실패로 보고 중단 (반영 없음).')
        diag = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-w', 'http=%{http_code}', '--max-time', '20',
                               '-A', UA, HQ + '/sub/02_product/product_01.php'], capture_output=True, text=True)
        print('진단:', diag.stdout.strip(), diag.stderr.strip()[:200])
        body = fetch('/sub/02_product/product_01.php?listCnt=99999&orderBy=sort')
        title = re.search(r'<title>(.*?)</title>', body, re.S)
        print('진단: 목록 길이', len(body), '제목', title.group(1).strip()[:60] if title else None,
              '제품링크', len(re.findall(r'product_01_V\.php\?idx=', body)))
        print('진단: 본문 앞부분', text(body)[:300])
        if re.findall(r'product_01_V\.php\?idx=(\d+)', body):
            i = re.findall(r'product_01_V\.php\?idx=(\d+)', body)[0]
            h = fetch(f'/sub/02_product/product_01_V.php?idx={i}')
            print('진단: 상세', i, '길이', len(h), 'con_top' in h, '3H지압침대' in h)
        sys.exit(2)

    changes = {'price': [], 'new_products': [], 'removed_products': [], 'new_news': []}
    for idx, h in hq.items():
        if idx not in ours:
            changes['new_products'].append({'idx': idx, **h})
        elif h['price'] and h['price'] != ours[idx]['price']:
            changes['price'].append({'idx': idx, 'name': ours[idx]['name'], 'old': ours[idx]['price'], 'new': h['price']})
    for idx, o in ours.items():
        if idx not in hq:
            changes['removed_products'].append({'idx': idx, **o})

    known_news = set(int(x) for x in re.findall(r'media_01_V\.php\?idx=(\d+)', index))
    news_titles = index
    for n in hq_news():
        if n['idx'] > 101 and n['idx'] not in known_news and n['title'][:12] not in news_titles:
            changes['new_news'].append(n)

    if apply and changes['price']:
        llms = (ROOT / 'llms.txt').read_text(encoding='utf-8')
        for c in changes['price']:
            old, new = c['old'], c['new']
            index = index.replace(f"price:{old},idx:{c['idx']}", f"price:{new},idx:{c['idx']}")
            index = index.replace(f'"price": {old}, "priceCurrency": "KRW", "itemOffered": {{"@type": "Product", "name": "{c["name"]}"',
                                  f'"price": {new}, "priceCurrency": "KRW", "itemOffered": {{"@type": "Product", "name": "{c["name"]}"')
            llms = re.sub(rf'(\| {re.escape(c["name"])} \|[^\n]*\| ){old:,}원', rf'\g<1>{new:,}원', llms)
        (ROOT / 'index.html').write_text(index, encoding='utf-8')
        (ROOT / 'llms.txt').write_text(llms, encoding='utf-8')

    (ROOT / 'scripts' / 'hq_sync_report.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(len(v) for v in changes.values())
    print(f'본사 지압침대 {len(hq)}종 / 우리 {len(ours)}종 비교')
    for k, v in changes.items():
        print(f'- {k}: {len(v)}')
        for x in v:
            print('   ', json.dumps(x, ensure_ascii=False))
    sys.exit(10 if total else 0)


if __name__ == '__main__':
    main()
