"""06 — 논문 §4.1 쿼리와 §5.1 두 평가법을 우리 KG 에 적용.

A. §4.1 Query 1·2·3 을 ourkg.nt 위에서 SPARQL 로 실행 (Table 2·3·4 대응)
B. §5.1 방법 1 — Supplement Table 1 의 20문항을 우리 KG 가 답할 수 있는지
   측면(aspect)별로 집계. 전문가 3인이 없으므로 정확도 0.95/0.90/0.95 자체는
   재현 대상이 아니다(eval/m1.py 서두와 같은 이유). 답변 가능성만 본다.
C. §5.1 방법 2 — 우리 KG 가 만든 추론 15건을 PubMed 로 검증.
   논문은 수작업 검색이었다. 여기서는 E-utilities 로 같은 판정(1/-1/0)을 자동화한다.
   1 = 두 엔티티가 함께 나오는 논문이 있음, 0 = 없음.
   (논문의 -1 '반대 증거' 는 초록 읽기가 필요해 자동 판정하지 않는다.)

출력  out/eval_*.json / out/eval_*.csv
"""
import os
import re
import sys
import json
import time
import random
import itertools
import collections

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'eval'))
from common import OUT, BASE

PART = os.environ.get('PART', 'ABC')
S = requests.Session()
S.headers['User-Agent'] = 'ourkg/1.0'

# ======================================================================
if 'A' in PART:
    from rdflib import Graph, URIRef, Literal

    print('[A] ourkg.nt 적재 (3M triple, 수 분 소요)', flush=True)
    t0 = time.time()
    g = Graph()
    g.parse(os.path.join(OUT, 'ourkg.nt'), format='nt')
    print(f'  triple {len(g):,}  {time.time()-t0:.0f}s', flush=True)

    PREFIX = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX npq:  <http://nutrition.vu.nl/pop/qualifier#>
PREFIX mpq:  <http://nlp_microbe.ccnu.edu.cn/pop/qualifier#>
PREFIX our:  <http://nutrition.vu.nl/ourkg/>
PREFIX ent:  <http://nutrition.vu.nl/entity#>
"""

    # 논문 Supplementary Query 1 을 그대로 쓰면 음식 라벨 regex 가 중량 노드 76만 개와
    # 조인되어 끝나지 않는다(논문 자신도 Q1 이 폭발한다 — eval/paper_sparql.py 참조).
    # 먼저 라벨로 음식 URI 를 싸게 찾고, 그 결과를 VALUES 로 주입해 본 쿼리를 돌린다.
    # 질문의 의미는 같고, 바뀐 것은 조인 순서뿐이다.
    def find_foods(pattern, limit=6):
        q = PREFIX + f"""select ?f ?l where {{
          ?f rdf:type ent:Food ; rdfs:label ?l .
          filter regex(?l, "{pattern}", "i")
        }} limit {limit}"""
        return [(r[0], str(r[1])) for r in g.query(q)]

    def values(var, uris):
        return 'values ?%s { %s }' % (var, ' '.join(f'<{u}>' for u in uris))

    res = {}

    # --- Q1 (§4.1.1) 혼합 식단의 영양소 흡수량 (Table 2 대응)
    eggs = find_foods('^Egg, whole')
    milks = find_foods('^Milk, whole|^Milk, reduced fat')
    t0 = time.time()
    q1 = PREFIX + f"""select ?eggname ?milkname ?cname (?ew + ?mw as ?total) where {{
      {values('egg', [u for u, _ in eggs])}
      {values('milk', [u for u, _ in milks])}
      ?egg rdfs:label ?eggname ; npq:hasNutrientWeights ?eu .
      ?eu npq:ofCompound ?c ; rdf:value ?ew .
      ?milk rdfs:label ?milkname ; npq:hasNutrientWeights ?mu .
      ?mu npq:ofCompound ?c ; rdf:value ?mw .
      ?c rdfs:label ?cname .
      filter regex(?cname, "Riboflavin|Thiamin|Niacin", "i")
    }} order by desc(?total) limit 8"""
    rows = [[str(x) for x in r] for r in g.query(q1)]
    res['Q1'] = rows
    print(f'\n  --- Q1 (Table 2 대응)  음식 {len(eggs)}x{len(milks)}  '
          f'{len(rows)}행  {time.time()-t0:.1f}s', flush=True)
    for r in rows:
        print('     ', ' | '.join(v[:40] for v in r), flush=True)

    # --- Q2 (§4.1.1) 음식 → 성분 → 장내세균 → 우울증 (Table 3 대응)
    t0 = time.time()
    q2 = PREFIX + """select ?cname ?microbe ?rel (count(?f) as ?nfood) where {
      ?c rdfs:label ?cname ; ?rel <http://id.nlm.nih.gov/mesh/D003865> .
      filter(?rel in (npq:hasPositiveAssociation, npq:hasNegativeAssociation))
      ?m mpq:hasMetabolites ?c ; rdfs:label ?microbe .
      ?f npq:hasNutrients ?c .
    } group by ?cname ?microbe ?rel order by desc(?nfood) limit 10"""
    rows = [[str(x) for x in r] for r in g.query(q2)]
    res['Q2'] = rows
    print(f'\n  --- Q2 (Table 3 대응)  {len(rows)}행  {time.time()-t0:.1f}s', flush=True)
    for r in rows:
        print('     ', ' | '.join(v.split("#")[-1][:40] for v in r), flush=True)

    # --- Q3 (§4.1.1) 우울증과 그 합병증에 동시에 작용하는 성분 (Table 4 대응)
    t0 = time.time()
    q3 = PREFIX + """select distinct ?cname ?microbe ?disease where {
      ?c rdfs:label ?cname ; ?rel <http://id.nlm.nih.gov/mesh/D003865> .
      filter(?rel in (npq:hasPositiveAssociation, npq:hasNegativeAssociation))
      ?m mpq:hasMetabolites ?c ; rdfs:label ?microbe ; mpq:hasAssociation ?d .
      ?d rdfs:subClassOf ent:MentalDisorder ; rdfs:label ?disease .
      filter(?d != <http://id.nlm.nih.gov/mesh/D003865>)
    } limit 20"""
    rows = [[str(x) for x in r] for r in g.query(q3)]
    res['Q3'] = rows
    print(f'\n  --- Q3 (Table 4 대응)  {len(rows)}행  {time.time()-t0:.1f}s', flush=True)
    for r in rows[:10]:
        print('     ', ' | '.join(v[:40] for v in r), flush=True)

    json.dump(res, open(os.path.join(OUT, 'eval_sparql.json'), 'w'),
              ensure_ascii=False, indent=1)

# ======================================================================
if 'B' in PART:
    import paper_data

    print('\n[B] §5.1 방법 1 — 20문항 답변 가능성')
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str})
    md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})

    # 측면별로 우리 KG 가 그 질문 유형을 답하는 데 필요한 축을 갖고 있는가
    # 논문의 여섯 측면별로, 우리 KG 가 그 질문 유형을 답할 축을 갖췄는가.
    # 온톨로지 축(FoodOn·중국 식품 온톨로지·SNOMED CT)은 통합하지 않았으므로
    # 분류 계층을 요구하는 두 측면은 부분 답변(△)이다.
    HAVE = {
        'food categories': ('△', f'FDC {len(foods):,} 음식 / SR 27군. '
                                 'FoodOn·Chinese Food Ontology 미통합이라 '
                                 '온톨로지 계층 질문은 답하지 못한다'),
        'weight calculation': ('O', f'성분 중량 {len(long):,} 건 (g/100g)'),
        'compounds categories': ('O', f'KEGG compound {long["kegg"].nunique()}'),
        'compounds in food and gut': ('O', 'FDC 성분 + KEGG compound-미생물 경로'),
        'bacteria taxonomy': ('O', f'NCBI taxonomy {len(mic)} 종 (학명·계통·rank 갱신)'),
        'disease classification': ('△', f'MeSH tree number {md.mesh_id.nunique()} 질환. '
                                        'SNOMED CT 미통합'),
    }
    rows = []
    for no, q, aspect, ans, v0, v1, v2 in paper_data.TABLE1:
        key = next((k for k in HAVE if k == aspect.lower().strip()), None)
        mark, why = HAVE.get(key, ('?', f'측면 미분류: {aspect}'))
        rows.append({'no': no, 'aspect': aspect, 'question': q,
                     'paper_answer': ans, 'ourkg': mark, 'basis': why,
                     'expert_consensus': int(v0 + v1 + v2 == 3)})
    b = pd.DataFrame(rows)
    b.to_csv(os.path.join(OUT, 'eval_method1.csv'), index=False)
    print(b.groupby(['aspect', 'ourkg']).size().to_string())
    print(f"  답변 가능 {int((b.ourkg == 'O').sum())}/20, 부분 {int((b.ourkg == '△').sum())}, "
          f"불가 {int((b.ourkg == 'X').sum())}")

# ======================================================================
if 'C' in PART:
    print('\n[C] §5.1 방법 2 — 추론 15건 PubMed 검증')
    md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str}
                      ).set_index('taxid')['name'].to_dict()
    mdis = pd.read_csv(os.path.join(OUT, 'microbe_disease_mikg.csv'))
    rec = pd.read_csv(os.path.join(OUT, 'recommendation.csv'))
    E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv')).set_index('food_key')

    random.seed(0)
    infs = []

    # 추론 (a) Complication — 같은 미생물을 공유하는 두 정신질환 (논문 §3.3)
    by_mic = collections.defaultdict(set)
    for _, r in mdis.iterrows():
        by_mic[r['microbe']].add(r['disease'])
    pairs = collections.Counter()
    for m, ds in by_mic.items():
        for a, b in itertools.combinations(sorted(ds), 2):
            pairs[(a, b)] += 1
    for (a, b), n in pairs.most_common(40):
        shared = sorted(m for m, ds in by_mic.items() if a in ds and b in ds)
        # 공유 미생물이 여럿이면 시드 고정 난수로 하나를 고른다. 문헌이 가장 잘
        # 붙는 것을 고르면 검증이 아니라 확증 편향이 된다.
        infs.append({'type': 'Complication', 'q': f'{a} and {b}',
                     'evidence': random.choice(shared), 'n_shared_microbe': n,
                     'terms': [a, b]})

    # 추론 (b) Diet recommendation — 상·하위 음식과 그 근거 compound
    def basis(fk):
        sub = long[long.food_key == fk].copy()
        sub['e'] = sub['kegg'].map(E['e_shrunk']).fillna(0)
        sub['w'] = sub['amount_g'] * sub['e']
        if sub.empty or sub['w'].abs().max() == 0:
            return None
        row = sub.loc[sub['w'].abs().idxmax()]
        return str(E['name'].get(row['kegg'], row['kegg']))

    for fk in list(rec.head(20)['food_key']) + list(rec.tail(20)['food_key']):
        c = basis(fk)
        if not c:
            continue
        nm = foods.loc[fk, 'food_name']
        infs.append({'type': 'Diet recommendation',
                     'q': f'{nm} and depression', 'evidence': c,
                     'terms': [re.split(r'[,(]', str(nm))[0].strip(), 'depression']})

    sample = random.sample(infs, 15)

    def pubmed(terms, extra=None):
        q = ' AND '.join(f'"{t}"' for t in terms if t)
        if extra:
            q += f' AND "{extra}"'
        r = S.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
                  params={'db': 'pubmed', 'term': q, 'retmax': 3, 'retmode': 'json'},
                  timeout=60)
        time.sleep(0.4)
        try:
            d = r.json()['esearchresult']
            return int(d['count']), d.get('idlist', [])
        except Exception:
            return 0, []

    rows = []
    for i, inf in enumerate(sample, 1):
        # 판정은 '두 엔티티 + KG 가 댄 근거' 세 항이 모두 함께 나오는 논문이
        # 있는가로 한다. 질환 이름 두 개만으로 검색하면 anxiety+depression 처럼
        # 1만 건이 나와 아무것도 검증하지 못한다(그 수치는 참고용으로만 남긴다).
        n, ids = pubmed(inf['terms'], inf['evidence'])
        n_pair, _ = pubmed(inf['terms'])
        rows.append({'no': i - 1, 'question': inf['q'], 'attributes': inf['type'],
                     'ourkg': inf['evidence'], 'pubmed': ';'.join(ids[:2]),
                     'n_hits_with_evidence': n, 'n_hits_pair_only': n_pair,
                     'result': 1 if n else 0})
        print(f"  {i:2d}. {inf['q'][:48]:50s} {inf['evidence'][:22]:24s} "
              f"근거포함={n:5d}  두항만={n_pair:6d}  -> {'1' if n else '0'}")
    t5 = pd.DataFrame(rows)
    t5.to_csv(os.path.join(OUT, 'eval_method2.csv'), index=False)
    print(f"\n  확인됨(1) {int((t5.result == 1).sum())}/15, "
          f"미확인(0) {int((t5.result == 0).sum())}/15   "
          f"(논문 Table 5: 11 / 3 / 반대 1)")
