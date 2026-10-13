"""
공개 KG 로 논문의 SPARQL 쿼리를 그대로 실행
==============================================
`foodkg_triply/` 11개 파일(+ MiKG)을 SPARQL 저장소에 올리고, 보충자료
(Supplements.docx)의 Query 1·2·3 으로 논문 Table 2·3·4·5 가 나오는지 본다.
REPRODUCTION.md §16.9, §16.10.

쿼리는 보충자료 원문이다. 바꾼 곳은 표시해 두었다.
  - HTML 엔티티를 풀었다.
  - 접두사는 논문 Fig. 1 과 데이터의 실제 IRI 에 맞췄다.
  - Query 3 의 SNOMED 절: 공개 KG 에 SNOMED CT 가 없다. SNOMED ID 의 이름과
    "mental disorder" 분류는 논문이 출처로 든 MiKG 에 있으므로 거기서 가져온다
    (wasp:hasEnglishLabel -> rdfs:label, SNOMED 노드 -> MiKG 노드 한 단계 추가).
  - Query 1 은 원문이 끝나지 않는다(묶이지 않은 변수로 조인이 폭발). 같은 결과를
    내는 작은 질의로 나눠 계산한다.

필요: pyoxigraph  (uv pip install pyoxigraph)
실행: python3 eval/paper_sparql.py        약 5분
"""
import os
import sys
import time

import pandas as pd
import pyoxigraph as ox

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from paper_table5 import TABLE5  # noqa: E402

FKG = os.path.join(BASE, 'foodkg_triply')
MIKG = os.path.join(BASE, 'MiKG-JAIMS', 'MiKG_Schema_Data_20201007.ttl')
OUT = os.path.join(BASE, 'analyse')
XD = '<http://www.w3.org/2001/XMLSchema#double>'

PREFIX = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX pq: <http://nutrition.vu.nl/pop/qualifier#>
PREFIX npq: <http://nlp_microbe.ccnu.edu.cn/pop/qualifier#>
PREFIX entity: <http://nlp_microbe.ccnu.edu.cn/entity#>
PREFIX wasp: <http://wasp.cs.vu.nl/KG#>
"""

# 논문 Table 1 의 소스별 트리플 수 -> 공개 KG 의 해당 파일
PAPER_TRIPLES = [
    ('FoodData Central', 2332603, ['Food_Nutrient.trig']),
    ('FoodOn', 79769, ['Food_Ontology.jsonld']),
    ('Chinese Food Ontology', 215863, ['Food_Chinese.jsonld']),
    ('KEGG', 74286, ['KEGG_Compound.jsonld', 'KEGG_Compound_Bacteria.jsonld']),
    ('NCBI taxonomy', 1306152, ['Bacteria_Ontology.trig']),
    ('MENDA', 5675, ['MENDA_Depression.jsonld']),
    ('MiKG', 1234, ['Mental_health.jsonld']),
    ('SNOMED CT', 4291226, []),
    ('MESH', 261556, ['MESH_Disease.jsonld']),
]

# ---- 보충자료 원문 ----------------------------------------------------
Q2 = """select distinct ?foodname?foodclassname?compoundname?weight?bacname
where {
    ?depression npq:hasNegativeAssociation ?compound;
    rdfs:label ?depressionname.
    ?compound rdfs:label ?compoundname.
    ?nutrition owl:sameAs ?compound;
               pq:hasNutrientWeights ?unit.
    {?food pq:hasNutrients ?nutrient;
           pq:hasNutrientWeights ?unit;
        rdfs:label ?foodname.}
    ?unit rdf:value ?weight.
    ?food rdf:type ?foodclass.
    ?foodclass rdfs:label ?foodclassname.
    ?depression npq:hasPositiveAssociation ?bac.
    ?bac npq:hasMetabolites ?compound.
    ?bac rdfs:label ?bacname.
    filter regex(?depressionname,"depression | depressive | depressed","i")
}"""
# Table 3 의 0~2행은 세균이 우울증과 neg 연관이다. 세균 조건만 바꾼 것.
Q2_BAC_NEG = Q2.replace('?depression npq:hasPositiveAssociation ?bac.',
                        '?depression npq:hasNegativeAssociation ?bac.')

Q3 = """select distinct ?food?compound?bacteria?disease
where {
    {?depression npq:hasNegativeAssociation ?compound;
                 rdfs:label ?depressionname.}
    ?nutrition owl:sameAs ?compound.
    ?compound rdfs:label ?compoundname;
              rdf:type entity:Compounds
    {?food pq:hasNutrients ?nutrient;
        rdfs:label ?foodname.}
    {?bacteria npq:hasMetabolites ?compound;
              rdfs:label ?bacterianame;
              npq:hasAssociation ?disease.}
    ?dissnomed owl:sameAs ?disease;
               wasp:hasEnglishLabel ?disname;
     rdfs:subClassOf ?disclass.
    ?disclass wasp:hasEnglishLabel ?disclassname.
    filter regex(?disclassname,"mental disorder","i")
    filter regex(?depressionname,"depression| depressive | depressed","i")
}"""
# SNOMED 이름·분류를 MiKG 에서 가져온다. %(food)s 는 ?nutrient(원문) 또는
# ?nutrition(음식과 성분을 묶음). Table 4 의 세 음식으로 범위를 좁힌다.
Q3_MIKG = """select distinct ?foodname ?compoundname ?bacterianame ?disname
where {
    {?depression npq:hasNegativeAssociation ?compound;
                 rdfs:label ?depressionname.}
    ?nutrition owl:sameAs ?compound.
    ?compound rdfs:label ?compoundname;
              rdf:type entity:Compounds .
    {?food pq:hasNutrients %(food)s;
        rdfs:label ?foodname.}
    {?bacteria npq:hasMetabolites ?compound;
              rdfs:label ?bacterianame;
              npq:hasAssociation ?disease.}
    ?dissnomed owl:sameAs ?disease.
    ?mikg owl:sameAs ?dissnomed;
          rdfs:label ?disname;
          rdfs:subClassOf ?disclass.
    ?disclass rdfs:label ?disclassname.
    filter regex(str(?disclassname),"mental disorder","i")
    filter (lang(?disname) = "en")
    filter regex(?depressionname,"depression| depressive | depressed","i")
    filter regex(?foodname,"^(Peaches|MILK, 2%%|Hot dogs, beef)","i")
}"""

TABLE2 = [  # (egg, milk, nutrient label, 논문 값 mg/200g)
    ('Potato salad with egg', 'MILK, 1%', 'Vitamin B-12', 0.082),
    ('Egg omelet or scrambled egg', 'Milk, skim', 'Vitamin B-12', 0.071),
    ('Goose egg, cooked', 'Milk, skim', 'Vitamin B-12', 0.074),
    ('Roll, egg bread', 'Soy milk, light', 'Vitamin B-12', 0.082),
    ('Egg, whole, fried with butter', 'Milk, whole', 'Vitamin B-6', 6.591),
    ('Shrimp-egg patty', 'Chocolate milk', 'Vitamin B-6', 6.766),
    ('Shrimp-egg patty', 'Almond milk, sweetened', 'Vitamin B-6', 2.656),
    ('Egg, whole, boiled or poached', 'Yogurt, coconut milk', 'Vitamin B-6', 6.602),
]
TABLE3 = [  # (food 패턴, compound 패턴, 논문 mg/100g, bacteria)
    ('FLOUR, SOY', 'Glutam', 8870, 'Enterococcus faecalis'),
    ('Broccoli, raw', 'Glycine', 89, 'Enterococcus faecalis'),
    ('Grape juice', 'Citr', 216.7, 'Adlercreutzia equolifaciens'),
    ('Kiwi', 'Ascorb', 84, 'Bifidobacterium longum'),
    ('Lettuce, Romaine', 'Ascorb', 7.5, 'Bifidobacterium longum'),
    ('BEEF BREAKFAST SAUSAGE|Beef sausage', 'Threonine', 500, 'Bacteroides ovatus'),
    ('BEEF BREAKFAST SAUSAGE|Beef sausage', 'Threonine', 500, 'Bacteroides vulgatus'),
    ('Whole wheat bread', 'Choline', 27.2, 'Bifidobacterium longum'),
]
TABLE4 = [  # (food, compound 패턴, bacteria, MiKG 질병명 패턴, 논문 표기)
    ('Peaches', 'Pantothen', 'Bacteroides vulgatus', 'Autistic', 'Autistic disorder'),
    ('Peaches', 'Pantothen', 'Bacteroides fragilis', 'Bipolar', 'Bipolar disorder'),
    ('MILK, 2%', 'Lysine', 'Escherichia coli', 'Learning', 'Intellectual disability'),
    ('MILK, 2%', 'Glutam', 'Lactobacillus plantarum', 'Learning', 'Intellectual disability'),
    ('Hot dogs, beef', 'Threonine', 'Fusobacterium varium', 'Bipolar', 'Bipolar disorder'),
]
T5_DISEASE = {'autistic disorder': 'autis', 'autism': 'autis', 'depression': 'depress',
              'parkinson disorder': 'parkinson', 'learning disabilities': 'learning',
              'anxiety': 'anxiety', 'bipolar disorder': 'bipolar',
              'alzheimer disease': 'alzheimer'}
T5_COMPOUND = {'Threonine': 'C00188', 'L-Threonine': 'C00188', 'alpha-Tocopherol': 'C02477',
               'Cystine': 'C01420', 'Nicotinic acid': 'C00253', 'Ascorbate': 'C00072'}
T5_FOOD = {'Garlic': 'garlic', 'Milk': '^milk', 'Egg products': 'egg', 'Coffee': 'coffee',
           'Lettuce': 'lettuce', 'Sweets': None, 'Onion': 'onion'}


class Store:
    def __init__(self):
        self.st, self.n = ox.Store(), {}
        for fn in sorted(os.listdir(FKG)):
            if not fn.endswith(('.trig', '.jsonld')):
                continue
            before = len(self.st)
            if fn.endswith('.trig'):
                self.st.bulk_load(path=os.path.join(FKG, fn), format=ox.RdfFormat.TRIG)
            else:
                self.st.bulk_load(path=os.path.join(FKG, fn), format=ox.RdfFormat.JSON_LD,
                                  to_graph=ox.NamedNode('file://' + fn))
            self.n[fn] = len(self.st) - before
        self.kg_total = len(self.st)
        self.st.bulk_load(path=MIKG, format=ox.RdfFormat.TURTLE,
                          to_graph=ox.NamedNode('file://MiKG'))

    def q(self, sparql):
        res = self.st.query(PREFIX + sparql, use_default_graph_as_union=True)
        return [[x.value if x is not None else None for x in row] for row in res]

    def df(self, sparql, cols):
        return pd.DataFrame(self.q(sparql), columns=cols)


def stats(S):
    print('[Table 1] 소스별 트리플 수')
    for name, paper, files in PAPER_TRIPLES:
        ours = sum(S.n.get(f, 0) for f in files)
        mark = '일치' if ours == paper else ('없음' if ours == 0 else '다름')
        print(f'  {name:24s} 논문 {paper:>10,d}  공개 KG {ours:>10,d}  {mark}')
    print(f'  합계: 논문 13,346,991 (추론 4,741,023 포함) / 공개 KG {S.kg_total:,d}')


def table2(S):
    """Query 1 은 ?milkunit 이 ?milk 에 묶여 있지 않다. 결과의 Weight 는
    '달걀의 성분량 + 그 성분의 아무 음식 성분량' 이다. 그 집합에 논문 값이 있는지,
    그리고 우유 자신의 성분량으로 더한 올바른 합은 얼마인지 본다."""
    print('\n[Query 1 → Table 2] 묶이지 않은 변수')
    def own(food, nut):
        return [float(w) for (w,) in S.q(
            'select ?w where {?n rdfs:label "%s"; pq:hasNutrientWeights ?u. '
            '?f pq:hasNutrientWeights ?u; rdfs:label ?l. ?u rdf:value ?w. filter(?f != ?n) '
            'filter(strstarts(lcase(?l), "%s"))}' % (nut, food.lower()))]
    every = {}
    hit = 0
    for egg, milk, nut, paper in TABLE2:
        if nut not in every:
            every[nut] = S.q('select ?w ?l where {?n rdfs:label "%s"; pq:hasNutrientWeights ?u.'
                             ' ?f pq:hasNutrientWeights ?u; rdfs:label ?l. ?u rdf:value ?w. '
                             'filter(?f != ?n)}' % nut)
        e, m = own(egg, nut), own(milk, nut)
        src = next(((a, float(w), l) for a in e for w, l in every[nut]
                    if round(a + float(w), 3) == paper and float(w) > a), None)
        true = sorted({round(a + b, 4) for a in e for b in m})
        hit += src is not None
        print(f'  {egg[:27]:27s} + {milk[:22]:22s} 논문 {paper:<6g} 올바른 합 '
              f'{true[0]:g}~{true[-1]:g}  | 논문 값 = '
              + (f'달걀 {src[0]:g} + "{src[2][:30]}" {src[1]:g}' if src else '조합 없음'))
    print(f'  논문 값이 "달걀 + 다른 음식" 으로 나오는 행: {hit}/{len(TABLE2)}')
    return hit


def table3(S):
    print('\n[Query 2 → Table 3]')
    cols = ['food', 'cls', 'compound', 'weight', 'bac']
    t = time.time()
    A = S.df(Q2, cols)
    print(f'  원문 Query 2: {len(A):,d}행, 세균 {sorted(A.bac.unique())}  ({time.time()-t:.0f}s)')
    B = S.df(Q2_BAC_NEG, cols)
    print(f'  세균 조건 neg: {len(B):,d}행, 세균 {sorted(B.bac.unique())}')
    hit = 0
    for food, comp, w, bac in TABLE3:
        def has(d):
            x = d[d.food.str.contains(food, case=False, regex=True)
                  & d['compound'].str.contains(comp, case=False)
                  & (d.bac == bac) & ((d.weight.astype(float) - w).abs() < 0.06)]
            return len(x) > 0
        a, b = has(A), has(B)
        hit += a or b
        print(f'  {food.split("|")[-1][:20]:20s} {comp:10s} {w:<7g} {bac:28s} '
              f'{"원문" if a else ("세균 neg" if b else "없음")}')
    print(f'  재현: {hit}/{len(TABLE3)}')
    return hit


def table4(S):
    print('\n[Query 3 → Table 4]')
    n0 = len(S.q(Q3))
    print(f'  원문 Query 3: {n0}행 (공개 KG 에 SNOMED 이름·계층이 없다)')
    cols = ['food', 'compound', 'bac', 'dis']
    A = S.df(Q3_MIKG % dict(food='?nutrient'), cols)
    L = S.df(Q3_MIKG % dict(food='?nutrition'), cols)
    print(f'  SNOMED 이름을 MiKG 에서: 원문대로 {len(A):,d}행 / 음식–성분을 묶으면 {len(L):,d}행')
    ha = hl = 0
    for food, comp, bac, dis, paper in TABLE4:
        def has(d):
            return bool(len(d[d.food.str.lower().str.startswith(food.lower())
                              & d['compound'].str.contains(comp, case=False)
                              & (d.bac == bac) & d.dis.str.contains(dis, case=False)]))
        a, b = has(A), has(L)
        ha += a
        hl += b
        print(f'  {food:15s} {comp:10s} {bac:24s} {paper:24s} 원문대로 {"O" if a else "X"}'
              f'  묶으면 {"O" if b else "X"}')
    print(f'  재현: 원문대로 {ha}/{len(TABLE4)}, 음식–성분을 묶으면 {hl}/{len(TABLE4)}')
    return ha, hl


def table5(S):
    """엄격 기준. Complication: 그 세균이 두 질병 모두에 연결되는가.
    Diet: 음식에 그 성분 기록(>0)이 있고, 성분→세균→질병 경로가 있는가."""
    print('\n[Table 5] 엄격 기준')
    dis = {}
    for m, l in S.q('select distinct ?d ?l where {?b npq:hasAssociation ?d. ?d rdfs:label ?l}'):
        dis.setdefault(l.lower(), set()).add(m)
    for m, l in S.q('select distinct ?mesh ?l where {?s owl:sameAs ?mesh. ?x owl:sameAs ?s; '
                    'rdfs:label ?l. filter(lang(?l)="en") '
                    'filter(strstarts(str(?mesh),"http://id.nlm.nih.gov/mesh/D"))}'):
        dis.setdefault(l.lower(), set()).add(m)
    dis.setdefault('depression', set()).add('http://id.nlm.nih.gov/mesh/D003865')

    def mesh_of(name):
        return set().union(*[v for k, v in dis.items() if T5_DISEASE[name.lower()] in k])

    b2d = {}
    for l, d in S.q('select ?l ?d where {?b npq:hasAssociation ?d; rdfs:label ?l}'):
        b2d.setdefault(l, set()).add(d)
    for d, l in S.q('select ?d ?l where {?d ?p ?b. ?b rdfs:label ?l; npq:isChildOf ?par. '
                    'filter(?p in (npq:hasPositiveAssociation, npq:hasNegativeAssociation))}'):
        b2d.setdefault(l, set()).add(d)

    rows, strict, loose = [], 0, 0
    for no, qn, attr, ev, pmid, res in TABLE5:
        a, b = [x.strip() for x in qn.split(' and ')]
        if attr == 'Complication':
            D = b2d.get(ev, set())
            ra, rb = bool(D & mesh_of(a)), bool(D & mesh_of(b))
            ok = ok_loose = ra and rb
            why = f'{a}: {"O" if ra else "X"}, {b}: {"O" if rb else "X"}'
        else:
            c = f'<https://www.kegg.jp/entry/{T5_COMPOUND[ev]}>'
            base = (f'?nu owl:sameAs {c}; pq:hasNutrientWeights ?u. ?f pq:hasNutrientWeights ?u;'
                    f' rdfs:label ?fl. ?u rdf:value ?w. filter(?f != ?nu) filter({XD}(?w) > 0)')
            cond = (f'filter regex(?fl, "{T5_FOOD[a]}", "i")' if T5_FOOD[a]
                    else '?f a ?cat. ?cat rdfs:label "Sweets".')
            nfood = int(S.q(f'select (count(distinct ?f) as ?n) where {{{base} {cond}}}')[0][0])
            mb = {x[0] for x in S.q(f'select distinct ?l where {{?b npq:hasMetabolites {c}; '
                                    f'rdfs:label ?l}}')}
            path = len(mb & {l for l, ds in b2d.items() if ds & mesh_of(b)})
            ok_loose = path > 0          # Query 3 처럼 음식과 성분을 묶지 않으면
            ok = ok_loose and nfood > 0
            why = f'{a} 중 {ev} 기록 있는 음식 {nfood}, 성분→세균→{b} 경로 {path}'
        strict += ok
        loose += ok_loose
        rows.append(dict(no=no, attribute=attr, question=qn, evidence=ev, paper=res,
                         strict=ok, unlinked=ok_loose, detail=why))
        print(f'  #{no:<2d} {qn[:36]:36s} {ev[:22]:22s} {"O" if ok else "X"}'
              f'{" (묶지 않으면 O)" if ok_loose and not ok else ""}  {why}')
    nc = sum(1 for r in rows if r['attribute'] == 'Complication')
    sc = sum(r['strict'] for r in rows if r['attribute'] == 'Complication')
    print(f'  Complication {sc}/{nc}, Diet recommendation {strict - sc}/{len(rows) - nc} '
          f'(음식–성분을 묶지 않으면 {loose - sc}/{len(rows) - nc})')
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'paper_sparql_table5.csv'), index=False)
    return sc, strict - sc, loose - sc


def main():
    t = time.time()
    S = Store()
    print(f'KG 적재 {S.kg_total:,d} 트리플 + MiKG  ({time.time()-t:.0f}s)\n')
    stats(S)
    r2 = table2(S)
    r3 = table3(S)
    r4 = table4(S)
    r5 = table5(S)
    print('\n' + '=' * 70)
    print('요약 — 공개 KG(+MiKG)로 논문 쿼리를 돌렸을 때')
    print('=' * 70)
    print(f'  Table 2 (Query 1)  논문 값이 나오는 행 {r2}/8 — 단, 질문의 음식이 아닌 값이다')
    print(f'  Table 3 (Query 2)  {r3}/8')
    print(f'  Table 4 (Query 3)  원문대로 {r4[0]}/5, 음식–성분을 묶으면 {r4[1]}/5')
    print(f'  Table 5            Complication {r5[0]}/8, Diet {r5[1]}/7 '
          f'(묶지 않으면 {r5[2]}/7)')
    print(f'  총 {time.time()-t:.0f}s')


if __name__ == '__main__':
    main()
