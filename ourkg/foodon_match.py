"""FoodOn 매칭 규칙 (OLS 캐시 기반).

논문 §3.1 은 FoodOn 을 쓴다고 하지만 배포 KG 의 `Food_Ontology.jsonld` 는
12,913 노드짜리 부분집합이고 `soy milk` 가 없으며 상위 노드의 라벨조차 빠져 있다.
그래서 EBI OLS 에서 FOODON 클래스 28,685 개와 매칭된 클래스의 조상 계층을 받아
`ourkg/cache/` 에 캐시한다 (KEGG·NCBI·MeSH 와 같은 '실시간 API + 캐시' 방식).

매칭은 **이름 일치**만 쓴다. 세 가지 함정을 검수로 찾아 막았다.
  · 공백 무시는 한 글자 토큰이 없을 때만 — 색소 `Green S` 가 `greens` 로 무너진다
  · EFSA FoodEx2 코드 클래스(`40330 - …`) 제외 — 동의어 `snacks` 로 걸린다
  · `black or white pepper product` 제외 — 동의어 `pepper` 로 피망이 후추가 된다
커버리지: 음식 8,165 / 14,886 (54.9%), 클래스 1,096.
"""
import json, os, re
import pandas as pd
from common import OUT, BASE, normkey as base
SING=lambda b: ' '.join(re.sub(r'(?<=[a-z]{2})s$','',w) for w in b.split())
SAFE=lambda b: not re.search(r'\b[a-z0-9]\b', b)
EFSA=re.compile(r'^\d{4,6}\s*-\s')
BLOCK={'black or white pepper product'}
def keyset(s):
    b=base(s)
    if not b: return []
    out=[('exact',b)]
    if SAFE(b): out.append(('ns',b.replace(' ','')))
    out.append(('sing',SING(b)))
    if SAFE(b): out.append(('sing_ns',SING(b).replace(' ','')))
    return out
def build_index(terms):
    idx={}
    for oid,v in terms.items():
        if EFSA.match(str(v['label'])) or v['label'] in BLOCK: continue
        for nmn in [v['label']]+list(v.get('syn') or []):
            for lvl,k in keyset(nmn): idx.setdefault((lvl,k),oid)
    return idx
def cands(n):
    segs=[s.strip() for s in str(n).split(',') if s.strip()]
    return [', '.join(segs[:i]) for i in range(len(segs),0,-1)]
def match(name, idx):
    for c in cands(name):
        for lvl,k in keyset(c):
            if (lvl,k) in idx: return idx[(lvl,k)]
    return None


def link_table(meta):
    """음식 -> FoodOn 클래스 + 조상 (build.py 가 out/food_foodon.csv 로 쓴다)."""
    d = os.path.join(BASE, 'ourkg', 'cache')
    try:
        T = json.load(open(os.path.join(d, 'foodon_terms.json')))
        A = json.load(open(os.path.join(d, 'foodon_ancestors.json')))
    except FileNotFoundError:
        return None
    idx, rows = build_index(T), []
    for fk, nm in zip(meta['food_key'], meta['food_name']):
        oid = match(nm, idx)
        if oid:
            rows.append((fk, oid, T[oid]['label'], 'class'))
            rows += [(fk, a['id'], a['label'], 'ancestor') for a in A.get(oid, [])]
    return pd.DataFrame(rows, columns=['food_key', 'foodon', 'foodon_label', 'rel'])


def labels_by_food():
    """food_key -> FoodOn 라벨 집합 (analyze.py 의 카테고리 축)."""
    p = os.path.join(OUT, 'food_foodon.csv')
    if not os.path.exists(p):
        return {}
    d = pd.read_csv(p).dropna(subset=['foodon_label'])
    return d.groupby('food_key')['foodon_label'].apply(set).to_dict()
