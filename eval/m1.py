"""
논문 §5.1 방법 1 (Human annotation) — 재실행 가능한 형태
=========================================================
논문 §5.1:
  "This evaluation method involves designing 20 specific questions (see
   Supplement Materials Table 1) and inviting three domain experts to manually
   answer these questions based on the original data sources. The questions
   cover six aspects... The accuracy of our results against the gold standard
   answers of the three experts are found to be 0.95, 0.9, and 0.95."

이 모듈은 그 20문항을 **(질문, 논문이 보고한 정답, 검증쿼리)** 삼중항으로 고정한다.

  질문      Supplement Table 1 의 Questions 열 (paper_data.TABLE1, 전사 원본)
  정답      같은 표의 Food4healthKG 열 — 논문이 자기 KG 로 얻었다고 보고한 답
  검증쿼리  QUERY[no] — 공개 KG(foodkg_triply/)에 같은 질문을 던지는 함수

재현 범위 (논문 그대로 복제할 수 없는 부분)
-------------------------------------------
논문의 정확도 0.95/0.90/0.95 는 **전문가 3인이 원본 데이터에서 손으로 찾은 답**과
KG 답의 일치율이다. 전문가가 없으므로 이 수치 자체는 재현 대상이 아니다.
Table 1 의 V0/V1/V2 열은 논문이 공개한 전문가 판정이므로, 전사가 맞는지만 검산한다
(transcript_accuracy).

대신 검증쿼리가 판정하는 것은 두 가지다.

  재현(reproduced)  공개 KG 에 같은 질문을 던지면 논문이 보고한 답이 나오는가
  타당(valid)       그 답이 질문에 실제로 맞는가

전문가 답변은 공개되지 않았다
-----------------------------
Supplements.docx 의 Table 1 컬럼은 No / Questions / Attributes / Food4healthKG /
V0 / V1 / V2 뿐이다. Food4healthKG 열은 KG 의 답이고, V0~V2 는 전문가 3인이 그 답에
동의했는가를 나타내는 1/0 플래그다. 전문가가 원본 데이터에서 찾은 답(gold standard
answer) 자체는 본문·부록·공식 repo(ccszbd/Food4healthKG) 어디에도 없다. 따라서
'전문가 답과 우리 답의 비교'는 원리적으로 불가능하다.

다만 V0=V1=V2=1 인 문항은 '논문 답 = 전문가 답'이 논문 자체 근거로 확정된다. 이를
consensus(전원 동의) 로 표시하고, 그 16문항에 한정한 재현율을 따로 집계한다. 공개된
데이터로 전문가 기준에 가장 가까이 갈 수 있는 형태다. 이견 문항(V 합 < 3)은 전문가가
무엇이라 답했는지 알 수 없으므로 이 집계에서 분리한다.

둘을 나누는 이유는 논문 답 일부가 Supplementary Query 1 의 결함으로 만들어졌기
때문이다.
  (1) 음식을 라벨 부분 문자열로 찾는다 — regex(?milkname, "Milk", "i").
      "Ricotta cheese, whole milk" 가 milk 로 잡힌다.
  (2) ?milkunit 이 ?milk 에 묶여 있지 않다. 두 번째 음식의 성분량이 실제로는
      '그 성분의 아무 음식 값' 이 된다 (Table 2 의 B6 6.591 = 달걀 0.151 +
      Kellogg's Special K 6.44. 실제 Milk, whole 의 B6 는 0.061).
논문 답이 재현되면서 타당하지 않다면, 그것은 우리 재현의 실패가 아니라 논문 쿼리의
결함이다.

KG 의 성분량 단위는 mg/100g 이다 (µg 성분도 mg 로 환산되어 있다).

실행: python3 eval/m1.py     (방법 1 20문항 + 방법 2 추론 재현)
"""
import collections
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from paper_data import PAPER_COUNTS, PAPER_ACCURACY, TABLE1, TABLE5

# ------------------------------------------------------------------
# 공개 KG 공통 로더
# 파싱 규칙은 knowledge_query.py 와 동일하다.
# ------------------------------------------------------------------
import json
import os
import re

BASE = os.path.dirname(HERE)
FKG = os.path.join(BASE, 'foodkg_triply')
OUT = os.path.join(BASE, 'analyse')


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
    """bacteria URI -> {disease URI}."""
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
    """bacteria URI -> label."""
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


CSV = os.path.join(OUT, 'paper_eval_table1.csv')

# 검증쿼리가 쓰는 FDC nutrient_id
NUT = dict(lysine=1214, folate_dfe=1190, retinol=1105, citric=1032, vitc=1162,
           potassium=1092, b12=1178, b6=1175)


# ==================================================================
# KG — 20문항에 필요한 만큼만 읽는다
# ==================================================================
class KG:
    def __init__(self):
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

    def unlinked(self, nut, target, first_pat, real_pat, digits=3):
        """Query 1 처럼 첫 음식 값 + '아무 음식 값' 으로 target 이 나오는가."""
        W = self.w[NUT[nut]]
        for f in self.foods(first_pat):
            a = W.get(f)
            if a is None:
                continue
            for g, b in W.items():
                if round(a + b, digits) == target and b > a:
                    real = self.vals(nut, real_pat)
                    return (self.food[f], a, self.food[g], b,
                            a + (real[len(real) // 2] if real else 0))
        return None


# ==================================================================
# 검증쿼리 — 문항 하나당 함수 하나
#   반환 (재현, 타당, 근거).  O / △ / X,  타당 '-' 는 판정 대상 아님.
# ==================================================================
def q00_lysine_fruits(kg):
    fruits = {re.split(r'[, ]', kg.food[f])[0].lower() for f in kg.food
              if 'Fruits and Fruit Juices' in kg.cats(f)
              and kg.w[NUT['lysine']].get(f, 0) > 0}
    straw = kg.vals('lysine', 'strawberr')
    return ('O' if {'melons', 'oranges'} <= fruits and straw else 'X',
            '△' if not any(straw) else 'O',
            f'Lysine>0 인 과일 {len(fruits)}종에 melons·oranges 포함. '
            f'strawberries 는 Lysine 기록 {len(straw)}건이 전부 0')


def _beverage_subclass(pat, key):
    """#1, #2 — Beverages 아래 특정 하위 카테고리에 속하는가."""
    def run(kg):
        by = collections.Counter(' / '.join(sorted(kg.cats(f))) for f in kg.foods(pat))
        good = lambda c: 'Beverages' in c and key in c
        n_ok = sum(n for c, n in by.items() if good(c))
        other = [(c, n) for c, n in by.most_common() if not good(c)]
        return ('O' if n_ok else 'X',
                'O' if n_ok and not other else ('△' if n_ok else 'X'),
                f'Beverages 아래 "{key}" 계열에 속하는 음식 {n_ok}개'
                + (f'. 같은 이름의 다른 카테고리 음식도 있다: {other[:2]}' if other else ''))
    return run


# 라벨 부분 문자열로 찾으면 'cola' 가 'Chocolate' 에 걸린다. 콜라는 접두로 찾는다.
q01_cola_category = _beverage_subclass(r'^Soft drink, cola', 'oft drinks')
q02_soymilk_category = _beverage_subclass(r'soy ?milk', 'Milk substitutes')


def q03_baby_food(kg):
    baby = kg.foods(r'baby food')
    ok = bool(kg.foods(r'^Carrots, baby food')) and bool(kg.foods(r'^Plums, baby food'))
    return ('O' if ok else 'X', 'O' if ok else 'X',
            f'baby food {len(baby)}종, Carrots·Plums 포함')


def q04_peach_pie_folate(kg):
    hit = kg.has('folate_dfe', 0.046, r'^Pie, peach')
    return ('O' if hit else 'X', 'O' if hit else 'X',
            f'{hit[0] if hit else "없음"} 의 Folate, DFE = 0.046')


def q05_retinol_milk_yogurt(kg):
    m, y = kg.has('retinol', 0.127, 'milk'), kg.has('retinol', 0.702, 'yogurt')
    real_m, real_y = kg.vals('retinol', r'^Milk, whole'), kg.vals('retinol', r'^Yogurt')
    return ('O' if m and y else 'X', 'X',
            f'0.127 = "{m[0] if m else "?"}", 0.702 = "{y[0] if y else "?"}" — 라벨 부분 '
            f'문자열 매칭. 실제 Milk, whole {real_m[0]:.3f}~{real_m[-1]:.3f}, '
            f'Yogurt {real_y[0]:.3f}~{real_y[-1]:.3f}')


def _food_compound_bacteria(nut, val, pat, bac, kegg, tol=0.05):
    """#6, #7 — 음식의 성분량 + 그 성분을 그 세균이 대사하는가."""
    def run(kg):
        hit, link = kg.has(nut, val, pat, tol=tol), kg.metabolizes(bac, kegg)
        return ('O' if hit and link else ('△' if hit else 'X'),
                'O' if hit and link else '△',
                f'"{hit[0][:42] if hit else "없음"}" = {val:g}, '
                f'{bac} 의 {kegg} 대사 경로 {"있음" if link else "없음"}')
    return run


q06_grapejuice_citric = _food_compound_bacteria(
    'citric', 309.0, 'grape juice', 'Adlercreutzia equolifaciens', 'C00158')
q07_lettuce_ascorbic = _food_compound_bacteria(
    'vitc', 15.0, 'lettuce', 'Bifidobacterium longum', 'C00072')


def q08_potassium_rank(kg):
    K = kg.w[NUT['potassium']]
    top = sorted(K, key=K.get, reverse=True)[:3]
    return ('△', '△',
            f'순위 범위가 문항에 없다. KG 전체 1~3위는 {[kg.food[f][:22] for f in top]}. '
            f'Beans 최대 {kg.vals("potassium", "^Beans")[-1]:g}, Egg whites '
            f'{kg.vals("potassium", "Egg whites")[-1]:g}, Almonds '
            f'{kg.vals("potassium", "Almond")[-1]:g}')


def _mixed_diet(nut, tgt, first, real):
    """#9, #10 — Query 1 의 미결합 ?unit 결함을 그대로 재연한다."""
    def run(kg):
        r = kg.unlinked(nut, tgt, first, real)
        return ('O' if r else 'X', 'X',
                (f'{tgt} = "{r[0][:24]}" {r[1]:g} + "{r[2][:28]}" {r[3]:g} — 두 번째 값이 '
                 f'질문의 음식이 아니다(Query 1 결함). 실제 합 ≈ {r[4]:.3f}') if r
                else '합이 나오는 조합 없음')
    return run


q09_orange_sausage_b12 = _mixed_diet('b12', 0.072, r'^Orange', r'sausage')
q10_egg_milk_b6 = _mixed_diet('b6', 6.591, r'^Egg, whole, fried', r'^Milk, whole$')


def q11_microbial_disorders(kg):
    d2b = {}
    for b, ds in kg.b2d.items():
        for x in ds:
            d2b.setdefault(x, set()).add(b)
    got = {l: len(d2b.get(i, ())) for i, l in kg.dlab.items()
           if re.search('autis|developmental', l, re.I) and d2b.get(i)}
    return ('O' if len(got) >= 2 else 'X', 'O' if len(got) >= 2 else 'X',
            f'세균 연관이 있는 질병: {got}')


def _mikg_mental_disorders():
    """MiKG 의 mentalDisorder 하위 질병 이름."""
    mikg = os.path.join(BASE, 'MiKG-JAIMS', 'MiKG_Schema_Data_20201007.ttl')
    out = []
    if os.path.exists(mikg):
        for block in open(mikg).read().split('\n\n'):
            if 'rdfs:subClassOf <http://ztonebv.com/MiKG#mentalDisorder>' in block:
                m = re.search(r'rdfs:label "([^"]+)"@en', block)
                if m:
                    out.append(m[1])
    return out


def q12_depression_vs_autism(kg):
    # 공개 KG 에는 SNOMED CT 계층이 없다 (Mental_health.jsonld 는 SCT ID 와 sameAs 뿐,
    # MESH_Disease.jsonld 는 C 트리만). 논문이 출처로 든 MiKG 에도 mentalDisorder
    # 한 단계밖에 없어 Mood / developmental 구분을 답할 수 없다.
    return ('X', '-', 'Mood disorder / developmental disorder 같은 상위 분류는 SNOMED CT '
                      '계층에만 있다. MiKG 는 mental disorder 한 단계뿐. 답할 수 없음')


def q13_mental_disorder_list(kg):
    # 기본은 MiKG 원본 TTL 이다. 다른 KG 로 이 질의를 돌릴 때(ourkg 어댑터 등)
    # 그 KG 가 mental_disorders() 를 주면 그쪽을 쓴다 — 질의가 평가 대상 KG 를
    # 거치지 않고 파일을 직접 읽으면 남의 답을 자기 답으로 세게 된다.
    get = getattr(kg, 'mental_disorders', None)
    mental, src = (get(), 'KG') if get else (_mikg_mental_disorders(), 'MiKG 원본')
    ok = any('Eating' in x for x in mental) and any('Bipolar' in x for x in mental)
    return ('O' if ok else 'X', 'O' if ok else '-',
            f'{src} 의 mentalDisorder 하위 {len(mental)}종: {sorted(mental)}')


def q14_vitamins_depression(kg):
    vit = kg.compounds_in('Vitamins') | kg.compounds_in('Vitamins and Cofactors')
    hitv = sorted(kg.klab['https://www.kegg.jp/entry/' + k] for k in vit & kg.menda
                  if 'Vitamin' in kg.klab['https://www.kegg.jp/entry/' + k])
    need = ('B1', 'B3', 'B5', 'Vitamin C', 'Vitamin E')
    ok = all(any(x in h for h in hitv) for x in need)
    return ('O' if ok else '△', 'O' if ok else '△',
            f'MENDA 우울증 연관 비타민: {[h.split("(")[-1].rstrip(")") for h in hitv]}')


def q15_alkaloids(kg):
    alk = kg.compounds_in('Alkaloids') & set(kg.nut2kegg.values())
    al = sorted(kg.klab['https://www.kegg.jp/entry/' + k] for k in alk)
    ok = {'Caffeine', 'Theobromine'} <= set(al)
    return ('O' if ok else 'X', 'O' if ok else 'X', f'음식 성분 중 alkaloid: {al}')


def q16_compound_categories(kg):
    cls = {l for c, l in kg.klab.items() if 'Class' in c}
    ok = {'Peptides', 'Alkaloids'} <= cls
    return ('O' if ok else 'X', 'O' if ok else 'X',
            f'KEGG 클래스 {len(cls)}개에 Peptides·Alkaloids 포함')


def q17_bacteroides_depression(kg):
    bact = sorted({kg.bname[b] for b, cs in kg.b2c.items()
                   if kg.bname.get(b, '').startswith('Bacteroides') and cs & kg.menda})
    ok = bact == ['Bacteroides fragilis', 'Bacteroides ovatus', 'Bacteroides vulgatus']
    return ('O' if ok else '△', 'O' if ok else '△',
            f'MENDA 우울증 화합물을 대사하는 Bacteroides: {[b.split()[1] for b in bact]}')


def q18_ecoli_taxonomy(kg):
    ecoli = next(b for b, n in kg.bname.items() if n == 'Escherichia coli')
    chain, x = [], ecoli
    while x in kg.bpar and len(chain) < 12:
        x = kg.bpar[x]
        chain.append(kg.bname.get(x, '?'))
    ok = chain[:2] == ['Escherichia', 'Enterobacteriaceae']
    return ('O' if ok else 'X', 'O' if ok else 'X', ' → '.join(chain))


def q19_top3_genus(kg):
    g = collections.Counter()
    for b, ds in kg.b2d.items():
        if b in kg.bname:
            g[kg.bname[b].split()[0]] += len(ds)
    top3 = [n for n, _ in g.most_common(3)]
    ok = top3 == ['Streptococcus', 'Bacteroides', 'Prevotella']
    return ('O' if ok else '△', 'O' if ok else '△',
            f'질병 연결 수 상위 속: {g.most_common(3)}')


QUERY = {
    0: q00_lysine_fruits,          1: q01_cola_category,
    2: q02_soymilk_category,       3: q03_baby_food,
    4: q04_peach_pie_folate,       5: q05_retinol_milk_yogurt,
    6: q06_grapejuice_citric,      7: q07_lettuce_ascorbic,
    8: q08_potassium_rank,         9: q09_orange_sausage_b12,
    10: q10_egg_milk_b6,          11: q11_microbial_disorders,
    12: q12_depression_vs_autism, 13: q13_mental_disorder_list,
    14: q14_vitamins_depression,  15: q15_alkaloids,
    16: q16_compound_categories,  17: q17_bacteroides_depression,
    18: q18_ecoli_taxonomy,       19: q19_top3_genus,
}

# (질문, 정답, 검증쿼리) 삼중항 — 이 리스트가 M1 의 고정 정의다.
M1 = [dict(no=no, question=q, attribute=attr, paper_answer=expected,
           v0=v0, v1=v1, v2=v2, vsum=v0 + v1 + v2, consensus=(v0 + v1 + v2) == 3,
           query=QUERY[no], query_name=QUERY[no].__name__)
      for no, q, attr, expected, v0, v1, v2 in TABLE1]

assert len(M1) == 20, 'Supplement Table 1 은 20문항이어야 한다'
assert len({t['attribute'] for t in M1}) == 6, '논문 §5.1 은 six aspects 라고 적었다'


# ==================================================================
# 실행 · 집계
# ==================================================================
def transcript_accuracy():
    """Table 1 의 V0/V1/V2 전사가 논문 보고값 0.95/0.90/0.95 와 맞는가."""
    return tuple(sum(t[f'v{i}'] for t in M1) / len(M1) for i in range(3))


def run(kg=None):
    """20문항을 공개 KG 에 질의한다 -> DataFrame."""
    kg = kg or KG()
    rows = []
    for t in M1:
        rep, val, why = t['query'](kg)
        rows.append(dict(no=t['no'], attribute=t['attribute'], question=t['question'],
                         paper_answer=t['paper_answer'], query=t['query_name'],
                         vsum=t['vsum'], consensus=t['consensus'],
                         reproduced=rep, valid=val, evidence=why))
    return pd.DataFrame(rows)


def summary(df):
    """scorecard 가 쓰는 집계값."""
    n = len(df)
    rc, vc = df.reproduced.value_counts(), df.valid.value_counts()
    by_aspect = {}
    for attr, sub in df.groupby('attribute', sort=False):
        by_aspect[attr] = (int((sub.reproduced == 'O').sum()), len(sub))
    con, dis = df[df.consensus], df[~df.consensus]
    cell = lambda sub: dict(n=len(sub),
                            reproduced=int((sub.reproduced == 'O').sum()),
                            both=int(((sub.reproduced == 'O') & (sub.valid == 'O')).sum()))
    return dict(
        n=n,
        consensus=cell(con),
        dissent=cell(dis),
        dissent_no=[int(x) for x in dis.no],
        consensus_gap=[int(r.no) for _, r in con.iterrows()
                       if not (r.reproduced == 'O' and r.valid == 'O')],
        reproduced=int((df.reproduced == 'O').sum()),
        reproduced_partial=int(rc.get('△', 0)),
        reproduced_fail=int(rc.get('X', 0)),
        valid=int((df.valid == 'O').sum()),
        valid_partial=int(vc.get('△', 0)),
        valid_fail=int(vc.get('X', 0)),
        valid_na=int(vc.get('-', 0)),
        both=int(((df.reproduced == 'O') & (df.valid == 'O')).sum()),
        by_aspect=by_aspect,
        paper_accuracy=PAPER_ACCURACY,
        transcript_accuracy=transcript_accuracy(),
    )


def load_cached():
    """scorecard 용 — 저장된 결과를 읽는다. 없으면 None."""
    if not os.path.exists(CSV):
        return None
    df = pd.read_csv(CSV)
    if 'consensus' not in df.columns:   # 구버전 캐시 -> 다시 질의하게 둔다
        return None
    return df


# ==================================================================
# 방법 2 (Table 5) — 우리 KG 가 **같은 추론을 만들어내는가**
# ------------------------------------------------------------------
# eval/paper_sparql.py 의 table5() 와 묻는 것이 다르다.
#   paper_sparql.table5()  논문이 든 근거가 KG 에서 **엄격히** 성립하는가
#                          (Complication 7/8, Diet 2/7)
#   여기 table5_inference() 그 추론을 우리 KG 가 **생성할 수 있는가** (11/15)
# 옛 eval/run_paper_eval.py 에 있던 것을 2026-11-09 에 여기로 합쳤다.
# ==================================================================
def table5_inference(save=True):
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
    if save:
        out = os.path.join(OUT, 'paper_eval_table5.csv')
        df.to_csv(out, index=False)
        print(f'  저장: {out}')
    return df


def report(df=None, save=True):
    df = run() if df is None else df
    s = summary(df)
    print()
    print('=' * 74)
    print('방법 1 — 전문가 20문항 (논문 Supplementary Table 1)')
    print('=' * 74)
    for i, nm in enumerate(('V0', 'V1', 'V2')):
        acc = s['transcript_accuracy'][i]
        flag = 'OK' if abs(acc - PAPER_ACCURACY[i]) < 1e-9 else 'MISMATCH'
        print(f'  전사 확인 {nm}: {acc:.2f} / 논문 보고 {PAPER_ACCURACY[i]:.2f}  {flag}')
    print()
    print('  공개 KG 에 20문항을 직접 질의 (전문가 대조가 아니라 KG 답의 재현)')
    print('  재현 = 논문이 보고한 답이 공개 KG 에서 나오는가 / 타당 = 그 답이 질문에 맞는가')
    print()
    for _, r in df.iterrows():
        print(f'  #{r.no:<2d} 재현 {r.reproduced}  타당 {r.valid}  {r.question[:58]}')
        print(f'        논문 답: {r.paper_answer}')
        print(f'        검증쿼리: {r["query"]}()')
        print(f'        근거   : {r.evidence}')
    print()
    print(f'  재현: O {s["reproduced"]} / △ {s["reproduced_partial"]} / X {s["reproduced_fail"]}'
          f'   (전체 {s["n"]})')
    print(f'  타당: O {s["valid"]} / △ {s["valid_partial"]} / X {s["valid_fail"]}'
          + (f' / 판정 제외 {s["valid_na"]}' if s['valid_na'] else '')
          + f'   (전체 {s["n"]})')
    print(f'  재현되고 타당한 문항: {s["both"]}/{s["n"]}')
    print()
    print('  전문가 판정(V0/V1/V2) 기준 분리')
    print('    전문가 답은 공개되지 않았다. V=1,1,1 인 문항만 "논문 답 = 전문가 답"이 확정된다.')
    c, d = s['consensus'], s['dissent']
    print(f'    전원동의 {c["n"]:2d}문항  재현 {c["reproduced"]}/{c["n"]}   '
          f'재현∧타당 {c["both"]}/{c["n"]}   <- 전문가 기준에 가장 가까운 수치')
    print(f'    이견     {d["n"]:2d}문항  재현 {d["reproduced"]}/{d["n"]}   '
          f'재현∧타당 {d["both"]}/{d["n"]}   '
          f'(#{", #".join(map(str, s["dissent_no"]))} — 전문가 답 불명)')
    if s['consensus_gap']:
        print(f'    전원동의인데 재현∧타당이 아닌 문항: '
              f'#{", #".join(map(str, s["consensus_gap"]))}')
    print()
    print('  aspect 별 재현 (논문 §5.1 "six aspects")')
    for attr, (ok, tot) in s['by_aspect'].items():
        print(f'    {attr:28s} {ok}/{tot}')
    if save:
        df.to_csv(CSV, index=False)
        print()
        print(f'저장: {CSV}')
    return df


if __name__ == '__main__':
    report()
    print()
    table5_inference()
