"""
논문 §5.1 평가 재현
====================
논문은 두 가지 평가를 쓴다. NDCG나 순위 지표는 쓰지 않는다(확인: 논문·공식
final.py 모두 'ndcg'/'dcg' 문자열 0건. 공식 코드의 AP/hit/precision/recall은
정의만 있고 cal_results()에서 전부 주석 처리되어 있다).

  방법 1  전문가 20문항 수작업 대조 (Supplementary Table 1)
          논문 결과: 전문가 3인 대비 정확도 0.95 / 0.90 / 0.95
  방법 2  문헌 검증 15건 (Table 5)
          논문 결과: 11 confirmed / 1 contradicted / 3 unknown

재현 범위
---------
방법 1의 원형(전문가가 원본 데이터에서 손으로 답을 찾아 대조)은 재현 불가능하다.
대신 공개 KG(foodkg_triply/)에 20문항을 직접 질의해 **논문이 보고한 답이 나오는가**
(재현)와 **그 답이 질문에 맞는가**(타당)를 판정한다. 전문가 대조가 아니라 KG 답의
재현이다. 결과는 analyse/paper_eval_table1.csv.

방법 2는 문헌 검증 결과(1/-1/0)를 논문에서 그대로 받고, **우리 KG가 같은 추론을
만들어내는가**를 확인한다. PubMed 재검색은 하지 않는다.

실행: python3 eval/run_paper_eval.py
"""
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BASE)

from paper_table1 import TABLE1, PAPER_ACCURACY
from paper_table5 import TABLE5, PAPER_COUNTS
import kegg_alias

FKG = os.path.join(BASE, 'foodkg_triply')
OUT = os.path.join(BASE, 'analyse')


# ------------------------------------------------------------------
# KG 로드
# ------------------------------------------------------------------
def load_menda():
    with open(os.path.join(FKG, 'MENDA_Depression.jsonld')) as f:
        data = json.load(f)
    pos, neg = set(), set()
    for entry in data:
        for node in entry.get('@graph', []):
            for key, vals in node.items():
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        cid = v['@id'].rsplit('/', 1)[-1]
                        if cid.startswith('C'):
                            if 'PositiveAssociation' in key:
                                pos.add(cid)
                            elif 'NegativeAssociation' in key:
                                neg.add(cid)
    return pos, neg


def load_disease_bacteria():
    """bacteria URI -> {disease URI}.  knowledge_query.py와 동일한 파싱."""
    with open(os.path.join(FKG, 'Disease_Bacteria.jsonld')) as f:
        data = json.load(f)
    bac2dis = {}
    for entry in data:
        for node in entry.get('@graph', []):
            nid = node.get('@id', '')
            if not nid.startswith('http://nlp_microbe'):
                continue
            for key, vals in node.items():
                if 'hasAssociation' in key:
                    for v in (vals if isinstance(vals, list) else [vals]):
                        if isinstance(v, dict) and '@id' in v:
                            bac2dis.setdefault(nid, set()).add(v['@id'])
    return bac2dis


def load_bacteria_names():
    """bacteria URI -> label.  knowledge_query.py와 동일한 파싱."""
    names = {}
    path = os.path.join(FKG, 'Bacteria_Ontology.trig')
    with open(path, errors='ignore') as f:
        for line in f:
            if 'label' not in line:
                continue
            i = re.search(r'<(http://nlp_microbe[^>]+)>', line)
            l = re.search(r'"([^"]+)"', line)
            if i and l:
                names[i.group(1)] = l.group(1)
    return names


def load_disease_labels():
    labels = {}
    for fname in ('Mental_health.jsonld', 'MESH_Disease.jsonld'):
        p = os.path.join(FKG, fname)
        if not os.path.exists(p):
            continue
        with open(p) as f:
            data = json.load(f)
        for entry in data:
            for node in entry.get('@graph', []):
                nid = node.get('@id')
                for key, vals in node.items():
                    if key.endswith('rdf-schema#label'):
                        for v in (vals if isinstance(vals, list) else [vals]):
                            if isinstance(v, dict) and '@value' in v:
                                labels.setdefault(nid, set()).add(v['@value'])
    return labels


# ------------------------------------------------------------------
# 방법 2 — Table 5 추론 재현
# ------------------------------------------------------------------
def eval_table5():
    print('=' * 74)
    print('방법 2 — 문헌 검증 대상 추론 15건 (논문 Table 5)')
    print('=' * 74)
    print('  논문 보고: confirmed 11 / contradicted 1 / unknown 3')
    print('  여기서 보는 것: 우리 KG가 같은 추론을 만들어내는가')
    print()

    bac_names = load_bacteria_names()
    name2bac = {}
    for bid, nm in bac_names.items():
        name2bac.setdefault(nm.strip().lower(), set()).add(bid)
    bac2dis = load_disease_bacteria()
    dis_labels = load_disease_labels()

    weight = pd.read_csv(os.path.join(OUT, 'weight.csv'))
    E = {c: (1 if weight[c].iloc[0] > 0 else (-1 if weight[c].iloc[1] > 0 else 0))
         for c in weight.columns}
    p85 = pd.read_csv(os.path.join(OUT, 'paper85_compounds.csv'))
    name2kegg = {str(n).strip().lower(): k for k, n in zip(p85.kegg, p85['name'])}
    # Table 5의 표기 흔들림 보정
    name2kegg.setdefault('threonine', 'C00188')
    name2kegg.setdefault('l-threonine', 'C00188')
    name2kegg.setdefault('ascorbate', 'C00072')
    name2kegg.setdefault('nicotinic acid', 'C00253')
    name2kegg.setdefault('alpha-tocopherol', 'C02477')

    rows = []
    for no, q, attr, ev, pmid, result in TABLE5:
        evl = ev.strip().lower()
        if attr == 'Complication':
            bids = name2bac.get(evl, set())
            n_dis = sum(len(bac2dis.get(b, ())) for b in bids)
            ok = bool(bids) and n_dis > 0
            detail = (f'KG에 세균 {"있음" if bids else "없음"}, '
                      f'연결된 질병 {n_dis}건')
        else:
            kegg = name2kegg.get(evl)
            if kegg is None or kegg not in E:
                # 논문 Table 3/5의 compound가 Fig.4(c)의 85 목록에 없는 경우.
                # 논문 내부 불일치이지 우리 KG의 실패가 아니다(§4 참조).
                ok = False
                detail = f'{kegg or "?"} — 85 목록 밖 (논문 내부 불일치)'
            else:
                d = E[kegg]
                ok = d != 0
                detail = (f'{kegg} incidence='
                          f'{"+" if d > 0 else ("-" if d < 0 else "0")}')
        rows.append(dict(no=no, attribute=attr, question=q, evidence=ev,
                         paper=result, reproduced=ok, detail=detail))

    df = pd.DataFrame(rows)
    for _, r in df.iterrows():
        mark = 'O' if r.reproduced else 'X'
        lab = {1: 'confirmed', -1: 'contradicted', 0: 'unknown'}[r.paper]
        print(f'  {mark} #{r.no:<2d} [{r.attribute[:12]:12s}] {r.question[:38]:39s} '
              f'{lab:12s} {r.detail}')

    n = len(df)
    rep = int(df.reproduced.sum())
    print()
    outside = int((df.detail.str.contains('85 목록 밖')).sum())
    print(f'  KG 추론 재현: {rep}/{n}'
          + (f'   (실패 {n-rep}건 중 {outside}건은 compound가 85 목록 밖)'
             if outside else ''))
    for lab, val in ((1, 'confirmed'), (-1, 'contradicted'), (0, 'unknown')):
        sub = df[df.paper == lab]
        print(f'    {val:12s} 논문 {PAPER_COUNTS[lab]}건 중 재현 '
              f'{int(sub.reproduced.sum())}건')
    return df


# ------------------------------------------------------------------
# 방법 1 — Table 1 20문항
# ------------------------------------------------------------------
# 전문가 3인의 수작업 대조는 재현할 수 없다. 대신 공개된 KG(foodkg_triply/)에
# 20문항을 직접 질의해 두 가지를 판정한다.
#
#   재현  공개 KG 에서 논문이 보고한 답이 나오는가
#   타당  그 답이 질문에 실제로 맞는가
#
# 둘을 나누는 이유: 논문 답 일부는 Supplementary Query 1 의 결함으로 만들어졌다.
#   (1) 음식을 라벨 부분 문자열로 찾는다 — regex(?milkname, "Milk", "i").
#       "Ricotta cheese, whole milk" 가 milk 로 잡힌다.
#   (2) ?milkunit 이 ?milk 에 묶여 있지 않다. 두 번째 음식의 성분량이 실제로는
#       '그 성분의 아무 음식 값' 이 된다 (Table 2 의 B6 6.591 = 달걀 0.151 +
#       Kellogg's Special K 6.44. 실제 Milk, whole 의 B6 는 0.061).
#
# KG 의 성분량은 mg/100g 이다 (µg 성분도 mg 로 환산되어 있다).
NUT = dict(lysine=1214, folate_dfe=1190, retinol=1105, citric=1032, vitc=1162,
           potassium=1092, b12=1178, b6=1175)


class KG:
    """foodkg_triply/ 를 20문항에 필요한 만큼만 읽는다."""

    def __init__(self):
        import collections
        dd = collections.defaultdict
        self.food, self.w, self.nut2kegg = {}, dd(dict), {}
        for line in open(os.path.join(FKG, 'Food_Nutrient.trig'), errors='ignore'):
            m = re.match(r'\s*<http://nutrition.vu.nl/weight_id/(\d+)_(\d+)> '
                         r'rdf:value ([-0-9.E]+)', line)
            if m:
                self.w[int(m[2])][int(m[1])] = float(m[3])
                continue
            m = re.match(r'\s*<http://nutrition.vu.nl/fdc_id/(\d+)> rdfs:label "(.*)" \.', line)
            if m:
                self.food[int(m[1])] = m[2]
                continue
            m = re.match(r'\s*<http://nutrition.vu.nl/nutrient_id/(\d+)> owl:sameAs '
                         r'<https://www.kegg.jp/entry/(C\d+)>', line)
            if m:
                self.nut2kegg[int(m[1])] = m[2]

        self.f2c, self.clab, self.csub = dd(set), {}, dd(set)
        for n in self._nodes('Food_Category.jsonld'):
            for k, vs in n.items():
                if k.endswith('#type') and 'fdc_id' in n['@id']:
                    self.f2c[int(n['@id'].rsplit('/', 1)[1])] |= {v['@id'] for v in vs}
                elif k.endswith('label'):
                    self.clab[n['@id']] = vs[0]['@value']
                elif k.endswith('subClassOf'):
                    self.csub[n['@id']] |= {v['@id'] for v in vs}

        self.klab, self.ksub, self.ktype = {}, dd(set), dd(set)
        for n in self._nodes('KEGG_Compound.jsonld'):
            for k, vs in n.items():
                if k.endswith('label'):
                    self.klab[n['@id']] = vs[0]['@value']
                elif k.endswith('subClassOf'):
                    self.ksub[n['@id']] |= {v['@id'] for v in vs}
                elif k.endswith('#type'):
                    self.ktype[n['@id'].rsplit('/', 1)[-1]] |= {v['@id'] for v in vs}

        self.b2c = dd(set)
        for n in self._nodes('KEGG_Compound_Bacteria.jsonld'):
            for k, vs in n.items():
                if k.endswith('hasMetabolites'):
                    self.b2c[n['@id']] |= {v['@id'].rsplit('/', 1)[-1] for v in vs}

        self.dlab = {}
        for n in self._nodes('Disease_Bacteria.jsonld'):
            for k, vs in n.items():
                if k.endswith('label'):
                    self.dlab[n['@id']] = vs[0]['@value']
        self.b2d = load_disease_bacteria()
        self.bname = load_bacteria_names()
        self.menda = set().union(*load_menda())

        self.bpar, cur = {}, None
        for line in open(os.path.join(FKG, 'Bacteria_Ontology.trig'), errors='ignore'):
            m = re.match(r'\s*<(http://nlp_microbe.ccnu.edu.cn/entity/\d+)> '
                         r'<http://nlp_microbe.ccnu.edu.cn/pop/qualifier#isChildOf>', line)
            if m:
                cur = m[1]
            elif cur:
                m = re.search(r'<(http://nlp_microbe.ccnu.edu.cn/entity/\d+)>', line)
                if m:
                    self.bpar[cur] = m[1]
                cur = None

    @staticmethod
    def _nodes(fname):
        with open(os.path.join(FKG, fname)) as f:
            return [n for e in json.load(f) for n in e.get('@graph', [])]

    def cats(self, fdc):
        """음식의 카테고리 라벨 (상위 포함)."""
        out, todo = set(), list(self.f2c.get(fdc, ()))
        while todo:
            c = todo.pop()
            if c not in out:
                out.add(c)
                todo += self.csub.get(c, ())
        return {self.clab.get(c, c) for c in out}

    def foods(self, pat):
        return [f for f, l in self.food.items() if re.search(pat, l, re.I)]

    def has(self, nut, value, pat=None, tol=5e-4):
        """그 값을 가진 음식 라벨 (라벨 패턴으로 제한 가능)."""
        return [self.food[f] for f, v in self.w[NUT[nut]].items()
                if abs(v - value) <= tol and (pat is None or re.search(pat, self.food[f], re.I))]

    def vals(self, nut, pat):
        return sorted(v for f, v in self.w[NUT[nut]].items()
                      if re.search(pat, self.food[f], re.I))

    def kdesc(self, label):
        """라벨이 label 인 KEGG 클래스와 그 하위 클래스."""
        out = {c for c, l in self.klab.items() if l == label and 'Class' in c}
        grew = True
        while grew:
            grew = False
            for c, ps in self.ksub.items():
                if c not in out and ps & out:
                    out.add(c)
                    grew = True
        return out

    def compounds_in(self, label):
        cl = self.kdesc(label)
        return {k for k, ts in self.ktype.items() if ts & cl}

    def metabolizes(self, bac_name, kegg):
        return any(kegg in cs for b, cs in self.b2c.items()
                   if self.bname.get(b, '') == bac_name)


def answer_table1(kg):
    """문항 번호 -> (재현, 타당, 근거).  O / △ / X,  타당 '-' 는 판정 대상 아님."""
    A = {}
    w, name = kg.w, kg.food

    fruits = {re.split(r'[, ]', name[f])[0].lower() for f in name
              if 'Fruits and Fruit Juices' in kg.cats(f)
              and w[NUT['lysine']].get(f, 0) > 0}
    straw = kg.vals('lysine', 'strawberr')
    A[0] = ('O' if {'melons', 'oranges'} <= fruits and straw else 'X',
            '△' if not any(straw) else 'O',
            f'Lysine>0 인 과일 {len(fruits)}종에 melons·oranges 포함. '
            f'strawberries 는 Lysine 기록 {len(straw)}건이 전부 0')

    import collections
    # 라벨 부분 문자열로 찾으면 'cola' 가 'Chocolate' 에 걸린다. 콜라는 접두로 찾는다.
    for no, pat, key in ((1, r'^Soft drink, cola', 'oft drinks'),
                         (2, r'soy ?milk', 'Milk substitutes')):
        by = collections.Counter(' / '.join(sorted(kg.cats(f))) for f in kg.foods(pat))
        good = lambda c: 'Beverages' in c and key in c
        n_ok = sum(n for c, n in by.items() if good(c))
        other = [(c, n) for c, n in by.most_common() if not good(c)]
        A[no] = ('O' if n_ok else 'X', 'O' if n_ok and not other else ('△' if n_ok else 'X'),
                 f'Beverages 아래 "{key}" 계열에 속하는 음식 {n_ok}개'
                 + (f'. 같은 이름의 다른 카테고리 음식도 있다: {other[:2]}' if other else ''))

    baby = kg.foods(r'baby food')
    ok = bool(kg.foods(r'^Carrots, baby food')) and bool(kg.foods(r'^Plums, baby food'))
    A[3] = ('O' if ok else 'X', 'O' if ok else 'X',
            f'baby food {len(baby)}종, Carrots·Plums 포함')

    hit = kg.has('folate_dfe', 0.046, r'^Pie, peach')
    A[4] = ('O' if hit else 'X', 'O' if hit else 'X',
            f'{hit[0] if hit else "없음"} 의 Folate, DFE = 0.046')

    m, y = kg.has('retinol', 0.127, 'milk'), kg.has('retinol', 0.702, 'yogurt')
    real_m, real_y = kg.vals('retinol', r'^Milk, whole'), kg.vals('retinol', r'^Yogurt')
    A[5] = ('O' if m and y else 'X', 'X',
            f'0.127 = "{m[0] if m else "?"}", 0.702 = "{y[0] if y else "?"}" — 라벨 부분 '
            f'문자열 매칭. 실제 Milk, whole {real_m[0]:.3f}~{real_m[-1]:.3f}, '
            f'Yogurt {real_y[0]:.3f}~{real_y[-1]:.3f}')

    for no, nut, val, pat, bac, kegg in (
            (6, 'citric', 309.0, 'grape juice', 'Adlercreutzia equolifaciens', 'C00158'),
            (7, 'vitc', 15.0, 'lettuce', 'Bifidobacterium longum', 'C00072')):
        hit, link = kg.has(nut, val, pat, tol=0.05), kg.metabolizes(bac, kegg)
        A[no] = ('O' if hit and link else ('△' if hit else 'X'),
                 'O' if hit and link else '△',
                 f'"{hit[0][:42] if hit else "없음"}" = {val:g}, '
                 f'{bac} 의 {kegg} 대사 경로 {"있음" if link else "없음"}')

    K = w[NUT['potassium']]
    top = sorted(K, key=K.get, reverse=True)[:3]
    A[8] = ('△', '△',
            f'순위 범위가 문항에 없다. KG 전체 1~3위는 {[name[f][:22] for f in top]}. '
            f'Beans 최대 {kg.vals("potassium", "^Beans")[-1]:g}, Egg whites '
            f'{kg.vals("potassium", "Egg whites")[-1]:g}, Almonds '
            f'{kg.vals("potassium", "Almond")[-1]:g}')

    def unlinked(nut, target, first_pat, real_pat, digits=3):
        """Query 1 처럼 첫 음식 값 + '아무 음식 값' 으로 target 이 나오는가."""
        W = w[NUT[nut]]
        for f in kg.foods(first_pat):
            a = W.get(f)
            if a is None:
                continue
            for g, b in W.items():
                if round(a + b, digits) == target and b > a:
                    real = kg.vals(nut, real_pat)
                    return (name[f], a, name[g], b, a + (real[len(real) // 2] if real else 0))
        return None

    for no, nut, tgt, first, real in ((9, 'b12', 0.072, r'^Orange', r'sausage'),
                                      (10, 'b6', 6.591, r'^Egg, whole, fried', r'^Milk, whole$')):
        r = unlinked(nut, tgt, first, real)
        A[no] = ('O' if r else 'X', 'X',
                 (f'{tgt} = "{r[0][:24]}" {r[1]:g} + "{r[2][:28]}" {r[3]:g} — 두 번째 값이 '
                  f'질문의 음식이 아니다(Query 1 결함). 실제 합 ≈ {r[4]:.3f}') if r
                 else '합이 나오는 조합 없음')

    d2b = {}
    for b, ds in kg.b2d.items():
        for x in ds:
            d2b.setdefault(x, set()).add(b)
    got = {l: len(d2b.get(i, ())) for i, l in kg.dlab.items()
           if re.search('autis|developmental', l, re.I) and d2b.get(i)}
    A[11] = ('O' if len(got) >= 2 else 'X', 'O' if len(got) >= 2 else 'X',
             f'세균 연관이 있는 질병: {got}')

    # 공개 KG 에는 SNOMED CT 계층이 없다 (Mental_health.jsonld 는 SCT ID 와 sameAs 뿐,
    # MESH_Disease.jsonld 는 C 트리만). 논문이 출처로 든 MiKG 에 mentalDisorder 의
    # 하위 질병 10종이 이름과 함께 있다 (eval/paper_sparql.py 의 Query 3 도 이것을 쓴다).
    mikg = os.path.join(BASE, 'MiKG-JAIMS', 'MiKG_Schema_Data_20201007.ttl')
    mental = []
    if os.path.exists(mikg):
        for block in open(mikg).read().split('\n\n'):
            if 'rdfs:subClassOf <http://ztonebv.com/MiKG#mentalDisorder>' in block:
                m = re.search(r'rdfs:label "([^"]+)"@en', block)
                if m:
                    mental.append(m[1])
    A[12] = ('X', '-', 'Mood disorder / developmental disorder 같은 상위 분류는 SNOMED CT '
                       '계층에만 있다. MiKG 는 mental disorder 한 단계뿐. 답할 수 없음')
    ok = any('Eating' in x for x in mental) and any('Bipolar' in x for x in mental)
    A[13] = ('O' if ok else 'X', 'O' if ok else '-',
             f'MiKG 의 mentalDisorder 하위 {len(mental)}종: {sorted(mental)}')

    vit = kg.compounds_in('Vitamins') | kg.compounds_in('Vitamins and Cofactors')
    hitv = sorted(kg.klab['https://www.kegg.jp/entry/' + k] for k in vit & kg.menda
                  if 'Vitamin' in kg.klab['https://www.kegg.jp/entry/' + k])
    need = ('B1', 'B3', 'B5', 'Vitamin C', 'Vitamin E')
    ok = all(any(x in h for h in hitv) for x in need)
    A[14] = ('O' if ok else '△', 'O' if ok else '△',
             f'MENDA 우울증 연관 비타민: {[h.split("(")[-1].rstrip(")") for h in hitv]}')

    alk = kg.compounds_in('Alkaloids') & set(kg.nut2kegg.values())
    al = sorted(kg.klab['https://www.kegg.jp/entry/' + k] for k in alk)
    ok = {'Caffeine', 'Theobromine'} <= set(al)
    A[15] = ('O' if ok else 'X', 'O' if ok else 'X', f'음식 성분 중 alkaloid: {al}')

    cls = {l for c, l in kg.klab.items() if 'Class' in c}
    ok = {'Peptides', 'Alkaloids'} <= cls
    A[16] = ('O' if ok else 'X', 'O' if ok else 'X',
             f'KEGG 클래스 {len(cls)}개에 Peptides·Alkaloids 포함')

    bact = sorted({kg.bname[b] for b, cs in kg.b2c.items()
                   if kg.bname.get(b, '').startswith('Bacteroides') and cs & kg.menda})
    ok = bact == ['Bacteroides fragilis', 'Bacteroides ovatus', 'Bacteroides vulgatus']
    A[17] = ('O' if ok else '△', 'O' if ok else '△',
             f'MENDA 우울증 화합물을 대사하는 Bacteroides: {[b.split()[1] for b in bact]}')

    ecoli = next(b for b, n in kg.bname.items() if n == 'Escherichia coli')
    chain, x = [], ecoli
    while x in kg.bpar and len(chain) < 12:
        x = kg.bpar[x]
        chain.append(kg.bname.get(x, '?'))
    ok = chain[:2] == ['Escherichia', 'Enterobacteriaceae']
    A[18] = ('O' if ok else 'X', 'O' if ok else 'X', ' → '.join(chain))

    g = collections.Counter()
    for b, ds in kg.b2d.items():
        if b in kg.bname:
            g[kg.bname[b].split()[0]] += len(ds)
    top3 = [n for n, _ in g.most_common(3)]
    ok = top3 == ['Streptococcus', 'Bacteroides', 'Prevotella']
    A[19] = ('O' if ok else '△', 'O' if ok else '△',
             f'질병 연결 수 상위 속: {g.most_common(3)}')
    return A


def eval_table1():
    print()
    print('=' * 74)
    print('방법 1 — 전문가 20문항 (논문 Supplementary Table 1)')
    print('=' * 74)
    for i, nm in enumerate(('V0', 'V1', 'V2')):
        acc = sum(r[4 + i] for r in TABLE1) / len(TABLE1)
        flag = 'OK' if abs(acc - PAPER_ACCURACY[i]) < 1e-9 else 'MISMATCH'
        print(f'  전사 확인 {nm}: {acc:.2f} / 논문 보고 {PAPER_ACCURACY[i]:.2f}  {flag}')
    print()
    print('  공개 KG 에 20문항을 직접 질의 (전문가 대조가 아니라 KG 답의 재현)')
    print('  재현 = 논문이 보고한 답이 공개 KG 에서 나오는가 / 타당 = 그 답이 질문에 맞는가')
    print()
    A = answer_table1(KG())
    rows = []
    for no, q, attr, expected, *_ in TABLE1:
        rep, val, why = A[no]
        rows.append(dict(no=no, attribute=attr, question=q, paper_answer=expected,
                         reproduced=rep, valid=val, evidence=why))
        print(f'  #{no:<2d} 재현 {rep}  타당 {val}  {q[:58]}')
        print(f'        논문 답: {expected}')
        print(f'        근거   : {why}')
    df = pd.DataFrame(rows)
    n = len(df)
    print()
    for col, lab in (('reproduced', '재현'), ('valid', '타당')):
        c = df[col].value_counts()
        print(f'  {lab}: O {c.get("O", 0)} / △ {c.get("△", 0)} / X {c.get("X", 0)}'
              + (f' / 판정 제외 {c.get("-", 0)}' if c.get('-', 0) else '') + f'   (전체 {n})')
    both = int(((df.reproduced == 'O') & (df.valid == 'O')).sum())
    print(f'  재현되고 타당한 문항: {both}/{n}')
    return df


if __name__ == '__main__':
    df = eval_table5()
    df1 = eval_table1()
    print()
    for d, fn in ((df, 'paper_eval_table5.csv'), (df1, 'paper_eval_table1.csv')):
        out = os.path.join(OUT, fn)
        d.to_csv(out, index=False)
        print(f'저장: {out}')
