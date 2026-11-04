"""
논문 §3.1 Table 1 검증 — Relation · Entity 열
==============================================
논문 Table 1 "Statistics of integrated knowledge in Food4healthKG" 은 소스마다
Relation / Entity / Triples 세 수치를 싣는다. 이 중 Triples 열은
eval/paper_sparql.py 의 stats() 가 이미 대조한다(공개 KG 9개 소스 중 7개 일치).
이 모듈은 나머지 두 열과 §3.1 본문 수치를 본다.

측정 정의 (논문이 정의를 적지 않아 우리가 고정한다)
---------------------------------------------------
파싱은 pyoxigraph 로 한다. 정규식·JSON 키 세기는 틀린다 — trig 에서 목적어를 predicate
로 세거나(NCBI 5 → 12), JSON-LD 의 `@type`(= rdf:type)을 빠뜨린다(FoodOn 56 → 53).
2026-11-03 에 이 오류를 고쳤다 (§17.9).

  relation  소스의 고유 predicate 수. 두 가지로 센다.
              sum   소스에 속한 파일별 predicate 수의 **합** (파일 간 중복을 그대로 둔다)
              uniq  소스 전체에서 중복을 제거한 수
            논문 값은 sum 과 맞는다 (8/8). Total 행 140 은 반대로 중복을 제거한 값으로
            보인다 — 논문 Relation 열의 합은 156 이다.
  entity    |고유 주어| + |고유 URI 목적어| + |고유 리터럴 목적어| 를 파일별로 더한다.
            합집합이 아니다 — 주어와 목적어 양쪽에 나오는 노드는 두 번 세고, 리터럴도
            개체로 센다. 이 정의에서 논문 값과 8/8 정확히 일치한다 (§17.10).
            FDC 는 Triples 열과 같이 Food_Nutrient.trig 단독이다.

§3.1 본문 수치
  FDC          34,250 food samples
  KEGG            230 metabolites
  NCBI taxonomy 322,917 gut microbes

§3.2 Entity linking (LINKING)
  논문이 정규화 결과로 제시한 네 수치를, 논문이 적은 정규화 규칙을 그대로 적용해
  확인한다. 규칙은 §3.2 본문에 글로만 적혀 있다.
    food      FDC 고유 식별자 기준. 라벨을 쉼표로 끊어 첫 쉼표 뒤를 버리고, 같은 라벨을
              병합. 복수→단수, 대문자→소문자. 카테고리 중복은 self-defined 매핑
    compound  KEGG 라벨로 링크. 대소문자·단복수·어순을 무시하되 그리스 문자는 구분
    disorder  MeSH + SNOMED CT 라벨. 대소문자·단복수 무시
  수치가 한 정의에서도 나오지 않으면 그 자체가 결과다(§3.1 Entity 열과 같은 성격).

§3.3 Knowledge representation (RELATIONS)
  논문이 세 유형으로 나눈 관계가 공개 KG 에 실제로 있는지 본다.
    self-defined  hasAssociation, 그 하위관계 hasPositiveAssociation·hasNegativeAssociation
    predefined    rdfs:subClassOf, rdf:type, owl:sameAs
    inferred      4,741,023 statements
  어휘의 존재 여부, 논문이 "subrelations ... both categorized under the main relation
  hasAssociation" 라고 적은 포함관계가 KG 에 선언돼 있는지, 그리고 세 관계가 실제로
  포함관계와 맞게 쓰이는지(주어·목적어 유형과 방향)를 본다 (§17.13).

전제: 공개 KG(foodkg_triply/)는 논문이 배포한 그 데이터다. Triples 열이 9개 소스 중
7개에서 정확히 일치하므로 파일 자체는 맞다. 따라서 Relation·Entity 열이 어긋난다면
그것은 파일이 다른 것이 아니라 논문 표 자체의 문제다.

실행: python3 eval/paper_kg_stats.py
"""
import collections
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from m1 import FKG, OUT
from paper_data import TABLE5 as PAPER_TABLE5

CSV = os.path.join(OUT, 'paper_eval_kg_stats.csv')
CSV_LINK = os.path.join(OUT, 'paper_eval_linking.csv')
CSV_REL = os.path.join(OUT, 'paper_eval_relations.csv')

# 논문 Table 1 — (source, relation, entity, triples, 공개 KG 파일)
# 파일 대응은 eval/paper_sparql.py 의 PAPER_TRIPLES 와 같아야 한다(거기서 이것을 import 한다).
TABLE1 = [
    ('FoodData Center',       9, 1220480, 2332603, ['Food_Nutrient.trig']),
    ('FoodOn',               56,   56079,   79769, ['Food_Ontology.jsonld']),
    ('Chinese Food Ontology', 7,  160802,  215863, ['Food_Chinese.jsonld']),
    ('KEGG',                  5,   23212,   74286, ['KEGG_Compound.jsonld',
                                                    'KEGG_Compound_Bacteria.jsonld']),
    ('NCBI taxonomy',         5,  984031, 1306152, ['Bacteria_Ontology.trig']),
    ('MENDA',                 5,    2367,    5675, ['MENDA_Depression.jsonld']),
    ('MiKG',                  3,    1138,    1234, ['Mental_health.jsonld']),
    ('SNOMED CT',            63, 2064178, 4291226, []),
    ('MESH',                  3,  483663,  261556, ['MESH_Disease.jsonld']),
]
PAPER_TOTAL = dict(relation=140, entity=1637915, triples=13346991, inferred=4741023)

# §3.1 본문 수치 — (이름, 논문 값, 측정 함수 키)
BODY = [('FDC food samples',      34250, 'fdc_food'),
        ('KEGG metabolites',        230, 'kegg_metabolite'),
        ('NCBI gut microbes',    322917, 'ncbi_microbe')]
# NCBI 322,917 은 공개 KG 의 326,533~326,845 와 1.2% 차이다. 어떤 술어로 세도 맞지
# 않지만, NCBI taxonomy 스냅샷 차이로 설명될 수 있는 크기라 '결함' 으로 보지 않는다.

# Table 1 의 Triples 열과 Relation 열이 가리키는 파일이 다르다 (§17.9).
#   Triples  FoodData Center 2,332,603 = Food_Nutrient.trig 단독 (정확히 일치)
#   Entity   FoodData Center 1,220,480 = Food_Nutrient.trig 단독 (정확히 일치)
#   Relation FoodData Center 9         = Food_Nutrient(5) + Food_Category(4)
# TABLE1 의 files 는 Triples·Entity 기준이고(eval/paper_sparql.py 가 그대로 쓴다),
# relation 만 아래 덮어쓰기를 적용한다.
REL_FILES = {'FoodData Center': ['Food_Nutrient.trig', 'Food_Category.jsonld']}

# Table 1 에 대응이 없는 공개 KG 파일 (참고용으로 따로 센다)
UNMAPPED = ['Disease_Bacteria.jsonld']

# §3.2 가 제시한 정규화 결과 — (항목, 논문 값)
LINKING = [('food entities',    1220480),
           ('food categories',      128),
           ('compounds',          23212),
           ('gut microbiota',    984031),
           ('mental disorders',    3505)]
LINKING_TOTAL = 1637915

# §3.2 의 다섯 수치는 모두 설명됐다 (§17.12). 남은 것은 합계뿐이다.
UNRESOLVED = {
    'total 1,637,915': (
        '§3.2 는 "combining the normalized compounds, gut microbiota, food categories, '
        'and mental disorders" 의 합이라고 적지만 그 넷을 더하면 1,010,876 이다. '
        'Table 1 Entity 열 전체 합(4,995,950)도 아니고, 9개 소스 Entity 값의 어떤 '
        '부분집합 합도 아니다. 공개 8개 소스의 고유 주어 합이 1,242,314 이므로 '
        'SNOMED 이 395,601 개 주어를 더하면 맞아떨어지는데(SNOMED CT 개념 수와 같은 '
        '자릿수다), SNOMED 이 배포되지 않아 확인할 수 없다.'),
}
GREEK = ('alpha', 'beta', 'gamma', 'delta', 'epsilon', 'omega')

# §3.3 이 든 관계 — (유형, 관계 이름)
RELATIONS = [('self-defined', 'hasAssociation'),
             ('self-defined', 'hasPositiveAssociation'),
             ('self-defined', 'hasNegativeAssociation'),
             ('predefined',   'subClassOf'),
             ('predefined',   'type'),
             ('predefined',   'sameAs')]
INFERRED_PAPER = 4741023
NPQ = 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#'
HIER = {NPQ + 'hasAssociation': 'hasAssociation',
        NPQ + 'hasPositiveAssociation': 'hasPositiveAssociation',
        NPQ + 'hasNegativeAssociation': 'hasNegativeAssociation'}


# ------------------------------------------------------------------
# 파일 단위 측정
# ------------------------------------------------------------------
def _store(fname):
    import pyoxigraph as ox          # 이 모듈에서만 필요하다
    st = ox.Store()
    if fname.endswith('.trig'):
        st.bulk_load(path=os.path.join(FKG, fname), format=ox.RdfFormat.TRIG)
    else:
        st.bulk_load(path=os.path.join(FKG, fname), format=ox.RdfFormat.JSON_LD,
                     to_graph=ox.NamedNode('file://' + fname))
    return st, ox


def scan(fname):
    """파일 하나 -> (predicate, subject, objectURI, objectLiteral) 집합."""
    st, ox = _store(fname)
    pred, subj, obj, lit = set(), set(), set(), set()
    for q in st:
        pred.add(str(q.predicate.value))
        subj.add(str(q.subject.value))
        if isinstance(q.object, ox.NamedNode):
            obj.add(str(q.object.value))
        else:
            lit.add(str(q.object))
    del st
    return pred, subj, obj, lit


def scan_all(files=None):
    """파일 -> (pred, subj, objURI, objLit) 집합. 파일마다 한 번만 읽는다 (약 1분)."""
    files = files or sorted(f for f in os.listdir(FKG)
                            if f.endswith(('.jsonld', '.trig')))
    return {f: scan(f) for f in files}


# ------------------------------------------------------------------
# §3.1 본문 수치
# ------------------------------------------------------------------
def body_counts(scanned):
    """본문에 적힌 세 수치를 공개 KG 에서 센다."""
    out = {}
    fdc = scanned.get('Food_Nutrient.trig')
    out['fdc_food'] = len({u for u in fdc[1] | fdc[2]
                           if '/fdc_id/' in u}) if fdc else None
    # §3.1 "we included 230 metabolites and leveraged the compound ontology from KEGG
    # compounds" — 230 은 KEGG compound 전체가 아니라 **음식에 실제로 붙은 영양소**의
    # 수다. pq:hasNutrients 의 고유 목적어가 정확히 230 이다 (§17.14).
    import pyoxigraph as ox
    st, _ = _store('Food_Nutrient.trig')
    PQ = 'http://nutrition.vu.nl/pop/qualifier#hasNutrients'
    out['kegg_metabolite'] = len({str(q.object.value) for q in st
                                  if str(q.predicate.value) == PQ})
    del st
    kc = scanned.get('KEGG_Compound.jsonld')
    out['kegg_compound_all'] = len({u for u in kc[1] if '/entry/C' in u}) if kc else None
    bac = scanned.get('Bacteria_Ontology.trig')
    out['ncbi_microbe'] = len({u for u in bac[1]
                               if '/entity/' in u}) if bac else None
    return out


# ------------------------------------------------------------------
# §3.2 Entity linking
# ------------------------------------------------------------------
def _norm_food(label):
    """§3.2 food 규칙: 첫 쉼표 뒤를 버리고, 소문자화, 복수→단수."""
    s = label.split(',')[0].strip().lower()
    s = re.sub(r'\b(\w+?)ies\b', r'\1y', s)
    return re.sub(r'\b(\w+?)s\b', r'\1', s)


def _norm_compound(label):
    """§3.2 compound 규칙: 대소문자·단복수·어순 무시, 그리스 문자는 구분."""
    s = label.lower().strip()
    keep = tuple(g for g in GREEK if g in s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return (' '.join(sorted(t.rstrip('s') for t in s.split() if t)), keep)


def _labels(fname, id_filter=None):
    """노드 URI -> label."""
    out = {}
    if fname.endswith('.jsonld'):
        for n in _jsonld_nodes(fname):
            nid = n.get('@id', '')
            if id_filter and id_filter not in nid:
                continue
            for k, vs in n.items():
                if not k.startswith('@') and k.endswith('label'):
                    out[nid] = vs[0]['@value']
    else:
        with open(os.path.join(FKG, fname), errors='ignore') as f:
            for line in f:
                if 'label' not in line:
                    continue
                i = re.search(r'<(http[^>]+)>', line)
                l = re.search(r'"([^"]+)"', line)
                if i and l and (not id_filter or id_filter in i.group(1)):
                    out[i.group(1)] = l.group(1)
    return out


def _jsonld_nodes(fname):
    with open(os.path.join(FKG, fname)) as f:
        return [n for e in json.load(f) for n in e.get('@graph', [])]


def _entity(scanned, files):
    """§17.10 에서 찾은 Table 1 Entity 정의."""
    return sum(len(scanned[f][1]) + len(scanned[f][2]) + len(scanned[f][3]) for f in files)


def linking(scanned=None):
    """§3.2 다섯 수치를 정의별로 센다 -> DataFrame."""
    rows = []

    def add(item, paper, defs):
        for d in defs:
            name, val = d[0], d[1]
            conf = d[2] if len(d) > 2 else '확정'
            rows.append(dict(item=item, paper=paper, definition=name, value=val,
                             match=(val == paper), confidence=conf))

    # --- food ---
    cat_nodes = _jsonld_nodes('Food_Category.jsonld')
    clab, csub, used = {}, set(), set()
    for n in cat_nodes:
        nid = n['@id']
        for k, vs in n.items():
            if k.startswith('@'):
                continue
            if k.endswith('label'):
                clab[nid] = vs[0]['@value']
            elif k.endswith('subClassOf'):
                csub.add(nid)
            elif k.endswith('#type') and 'fdc_id' in nid:
                used |= {v['@id'] for v in vs}
    fdc = {n['@id'] for n in cat_nodes if 'fdc_id' in n.get('@id', '')}
    add('food entities', 1220480, [
        ('FDC 인스턴스(fdc_id)', len(fdc)),
        ('Table 1 Entity 정의 (§17.10)',
         _entity(scanned, ['Food_Nutrient.trig']) if scanned else None)])
    n_root = len([c for c in clab if c not in csub])
    add('food categories', 128, [
        ('§3.2 서술대로 병합 (subClassOf 롤업)', n_root),
        ('  └ ×2 (Entity 열 계수 규약 적용 — 추정)', 2 * n_root, '추정'),
        ('병합 전 (라벨 보유 카테고리 전체)', len(clab)),
        ('  └ §3.2 라벨 정규화 후', len({_norm_food(v) for v in clab.values()})),
        ('FDC 원본 legacy 카테고리 (KG 음식이 쓰는 것)', 18),
        ('FDC 원본 food_category_id 전체 (2026 판)', 645)])

    # --- compound ---
    klab = _labels('KEGG_Compound.jsonld', '/entry/C')
    add('compounds', 23212, [
        ('Table 1 Entity 정의 (§17.10)',
         _entity(scanned, ['KEGG_Compound.jsonld', 'KEGG_Compound_Bacteria.jsonld'])
         if scanned else None),
        ('KEGG C* 노드', len(klab)),
        ('라벨 원문 고유', len(set(klab.values()))),
        ('  └ §3.2 정규화 후', len({_norm_compound(v) for v in klab.values()}))])

    # --- microbiota ---
    blab = _labels('Bacteria_Ontology.trig', '/entity/')
    bac = set()
    with open(os.path.join(FKG, 'Bacteria_Ontology.trig'), errors='ignore') as f:
        for line in f:
            m = re.search(r'<(http://nlp_microbe\.ccnu\.edu\.cn/entity/\d+)>', line)
            if m:
                bac.add(m.group(1))
    add('gut microbiota', 984031, [
        ('Table 1 Entity 정의 (§17.10)',
         _entity(scanned, ['Bacteria_Ontology.trig']) if scanned else None),
        ('NCBI taxon 노드', len(bac)),
        ('라벨 고유', len(set(blab.values())))])

    # --- mental disorder ---
    mh = _jsonld_nodes('Mental_health.jsonld')
    uris = set()
    for n in mh:
        uris.add(n.get('@id', ''))
        for k, vs in n.items():
            if k.startswith('@'):
                continue
            for v in (vs if isinstance(vs, list) else [vs]):
                if isinstance(v, dict) and '@id' in v:
                    uris.add(v['@id'])
    sct = {m.group(1) for u in uris if (m := re.search(r'SCT_(\d+)', u))}
    msh = {m.group(1) for u in uris if (m := re.search(r'mesh/(D\d+)', u))}
    add('mental disorders', 3505, [
        ('Table 1 MENDA + MiKG entity',
         _entity(scanned, ['MENDA_Depression.jsonld', 'Mental_health.jsonld'])
         if scanned else None),
        ('Table 1 MiKG entity 단독',
         _entity(scanned, ['Mental_health.jsonld']) if scanned else None),
        ('Disease_Bacteria 주어∪목적어', 3586),
        ('Mental_health 노드', len(mh)),
        ('SNOMED 개념 참조', len(sct)),
        ('MeSH D* 참조', len(msh)),
        ('SNOMED ∪ MeSH', len(sct | msh))])
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# §3.3 Knowledge representation
# ------------------------------------------------------------------
def relations():
    """§3.3 의 관계 어휘가 공개 KG 에 있는가 -> DataFrame."""
    want = [r for _, r in RELATIONS]
    hits = {r: collections.Counter() for r in want}
    subprop = []
    for fname in sorted(os.listdir(FKG)):
        path = os.path.join(FKG, fname)
        if fname.endswith('.jsonld'):
            for node in _jsonld_nodes(fname):
                for k, vs in node.items():
                    if k.startswith('@'):
                        continue
                    short = k.rsplit('#', 1)[-1].rsplit('/', 1)[-1]
                    n = len(vs) if isinstance(vs, list) else 1
                    if short in hits:
                        hits[short][fname] += n
                    if short == 'subPropertyOf':
                        for v in (vs if isinstance(vs, list) else [vs]):
                            subprop.append((node.get('@id', '').rsplit('/', 1)[-1],
                                            v.get('@id', '').rsplit('/', 1)[-1]))
        elif fname.endswith('.trig'):
            with open(path, errors='ignore') as f:
                for line in f:
                    for r in want:
                        if re.search(r'[:#/]' + r + r'\b', line):
                            hits[r][fname] += 1
                    if 'subPropertyOf' in line:
                        subprop.append((fname, 'trig'))
    rows = [dict(category=cat, relation=r, count=sum(hits[r].values()),
                 present=bool(hits[r]), files=';'.join(sorted(hits[r])[:3]))
            for cat, r in RELATIONS]
    df = pd.DataFrame(rows)
    # 논문이 적은 hasAssociation ⊃ hasPositive/Negative 포함관계가 선언돼 있는가
    df.attrs['subproperty_decl'] = [sp for sp in subprop
                                    if 'Association' in sp[0] or 'Association' in sp[1]]
    df.attrs['subproperty_total'] = len(subprop)
    return df


def _uri_kind(u):
    if re.search(r'/C\d+$', u) or 'kegg.jp/entry' in u:
        return 'KEGG compound'
    if '/mesh/' in u:
        return 'MeSH disease'
    if '/entity/' in u:
        return 'nlp_microbe entity'
    return u.rsplit('/', 1)[0]


def relation_hierarchy():
    """세 association 관계가 실제로 포함관계와 맞게 쓰이는가 (§17.13)."""
    use = {n: dict(pairs=set(), files=set(),
                   skind=collections.Counter(), okind=collections.Counter())
           for n in HIER.values()}
    for fname in sorted(os.listdir(FKG)):
        if not fname.endswith(('.jsonld', '.trig')):
            continue
        st, ox = _store(fname)
        for q in st:
            n = HIER.get(str(q.predicate.value))
            if not n:
                continue
            sub, obj = str(q.subject.value), str(q.object.value)
            u = use[n]
            u['pairs'].add((sub, obj))
            u['files'].add(fname)
            u['skind'][_uri_kind(sub)] += 1
            u['okind'][_uri_kind(obj)] += 1
        del st
    A = use['hasAssociation']['pairs']
    P = use['hasPositiveAssociation']['pairs']
    N = use['hasNegativeAssociation']['pairs']
    # 논문은 "associations between A and B" 로 무방향으로 쓴다. 방향을 무시하고도
    # 같은 쌍을 가리키는 경우가 있는지 본다.
    S = P | N
    undirected = len({(s, o) for s, o in A if (o, s) in S or (s, o) in S})
    # 우울증 하나로 좁힌 대조 — 일반관계와 하위관계가 모두 쓰이는 유일한 질병
    DEP = 'http://id.nlm.nih.gov/mesh/D003865'
    dep_generic = {s for s, o in A if o == DEP}
    dep_sub = {o for s, o in S if s == DEP and '/entity/' in o}
    return dict(use=use, generic_sub_overlap=len(A & S),
                subject_overlap=len({s for s, _ in A} & {s for s, _ in S}),
                undirected_overlap=undirected,
                dep_generic=len(dep_generic), dep_sub=len(dep_sub),
                dep_shared=len(dep_generic & dep_sub),
                pos_neg_overlap=len(P & N))


# ------------------------------------------------------------------
# §3.3 (3) Knowledge inference — 규칙 (a) 전이 추론 재구현 (§17.20)
# ------------------------------------------------------------------
# 논문 §3.3:
#   "considering that both saturated and unsaturated fatty acids are subclasses
#    of fatty acids and fatty acids are a subclass of lipids, we can logically
#    infer that instances of saturated fatty acids also belong to the classes of
#    fatty acids and lipids."
# 두 가지를 말한다.
#   (a1) 계층 전이        A ⊑ B, B ⊑ C  ⊢  A ⊑ C
#   (a2) 타입 전파        x type A, A ⊑ B  ⊢  x type B
# 배포 KG 의 계층 간선은 rdfs:subClassOf 와 npq:isChildOf(NCBI 계통수) 두 가지다.
HIER_PREDS = ('subClassOf', 'isChildOf')
INFER_CACHE = os.path.join(OUT, 'paper_eval_inference.json')
COMPL_CACHE = os.path.join(OUT, 'paper_eval_complication.json')
COV_CACHE = os.path.join(OUT, 'paper_eval_coverage.json')


def inference(verbose=True):
    """규칙 (a) 를 배포 KG 에 적용해 생성되는 트리플 수를 센다."""
    import collections
    idx = {}

    def nid(u):
        return idx.setdefault(u, len(idx))

    par = collections.defaultdict(set)      # child -> parents
    typ = collections.defaultdict(set)      # instance -> classes
    src = {}                                # child -> 처음 본 파일
    for fname in sorted(os.listdir(FKG)):
        if not fname.endswith(('.jsonld', '.trig')):
            continue
        st, ox = _store(fname)
        for q in st:
            if not isinstance(q.object, ox.NamedNode):
                continue
            p = str(q.predicate.value).rsplit('#', 1)[-1].rsplit('/', 1)[-1]
            a, b = nid(str(q.subject.value)), nid(str(q.object.value))
            if p in HIER_PREDS:
                par[a].add(b)
                src.setdefault(a, fname)
            elif p == 'type':
                typ[a].add(b)
        del st

    # 조상 집합 — 위상정렬(Kahn)로 부모를 먼저 처리한다. O(V+E+Σ|anc|).
    # 이전 판은 스택 재방문마다 todo 를 다시 만들어 사실상 2차였다(20분+ 미완).
    children = collections.defaultdict(list)
    indeg = collections.Counter()
    nodes = set(par)
    for c, ps in par.items():
        for q_ in ps:
            children[q_].append(c)
            nodes.add(q_)
        indeg[c] = len(ps)
    queue = collections.deque(n for n in nodes if indeg[n] == 0)
    anc = {}
    while queue:
        x = queue.popleft()
        a_ = set()
        for q_ in par.get(x, ()):
            a_.add(q_)
            a_ |= anc.get(q_) or set()
        anc[x] = a_
        for c in children.get(x, ()):
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    for x in nodes:                      # 순환에 걸려 남은 노드
        if x not in anc:
            a_ = set()
            for q_ in par.get(x, ()):
                a_.add(q_)
                a_ |= anc.get(q_) or set()
            a_.discard(x)
            anc[x] = a_

    hier_new = {x: len(anc[x]) - len(par[x]) for x in par}
    n_hier = sum(v for v in hier_new.values() if v > 0)

    n_type = 0
    for i, cs in typ.items():
        up = set()
        for c in cs:
            up |= anc.get(c, set())
        n_type += len(up - cs)

    by_src = collections.Counter()
    for x, v in hier_new.items():
        if v > 0:
            by_src[src.get(x, '?')] += v

    out = dict(nodes=len(par), edges=sum(len(v) for v in par.values()),
               multi_parent=sum(1 for v in par.values() if len(v) > 1),
               inferred_hierarchy=n_hier, inferred_type=n_type,
               inferred_total=n_hier + n_type,
               paper_inferred=INFERRED_PAPER,
               by_source=dict(by_src.most_common()))
    json.dump(out, open(INFER_CACHE, 'w'), indent=1)
    if verbose:
        print('=' * 86)
        print('논문 §3.3 (3) Knowledge inference — 규칙 (a) 전이 추론 (§17.20)')
        print('=' * 86)
        print(f'  계층 간선 {out["edges"]:,d}개 / 노드 {out["nodes"]:,d}개 '
              f'(다부모 {out["multi_parent"]:,d})')
        print(f'  (a1) 계층 전이로 생성   {n_hier:>10,d}')
        print(f'  (a2) 타입 전파로 생성   {n_type:>10,d}')
        print(f'  합계                    {n_hier + n_type:>10,d}   '
              f'논문 {INFERRED_PAPER:,d}  '
              f'({(n_hier + n_type) / INFERRED_PAPER * 100:.1f}%)')
        print()
        print('  소스별 (a1) 기여')
        for f, v in out['by_source'].items():
            print(f'    {f:32s} {v:>10,d}')
        print(f'\n  저장: {INFER_CACHE}')
    return out


# ---------------------------------------------------------------- 규칙 (b)
# 논문 §3.3:
#   "when observing that depression and anxiety are both mood disorders with
#    shared associations with the same gut microbiota, we can infer an implicit
#    relationship between depression and anxiety as 'complications'"
# 조건 두 개다 — (1) 같은 gut microbiota 를 공유 (2) 같은 상위 분류(mood disorders).
MIKG_TTL = os.path.join(os.path.dirname(FKG), 'MiKG-JAIMS',
                        'MiKG_Schema_Data_20201007.ttl')
NPQ_ASSOC = 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#hasAssociation'
SAMEAS = 'http://www.w3.org/2002/07/owl#sameAs'
SUBCLS = 'http://www.w3.org/2000/01/rdf-schema#subClassOf'
RDFS_LABEL = 'http://www.w3.org/2000/01/rdf-schema#label'
MENTAL = 'http://ztonebv.com/MiKG#mentalDisorder'

# 논문 Table 5 의 Complication 행 — eval/paper_data.py 의 TABLE5 에서 끌어온다.
# 베껴 적지 않는다 (§17.19). (질병 A, 질병 B, 근거 세균)
T5_COMPL = [tuple(q.split(' and ')) + (ev,)
            for _, q, attr, ev, _, _ in PAPER_TABLE5 if attr == 'Complication']
assert len(T5_COMPL) == 8 and all(len(t) == 3 for t in T5_COMPL)

# Table 5 가 근거로 든 세균의 NCBI taxon id (배포 KG 는 세균을 taxon id 로만 쓴다)
T5_EVIDENCE_TAXON = {
    'Bifidobacterium longum': '216816', 'Streptococcus mutans': '1309',
    'Escherichia coli': '562', 'Lactobacillus plantarum': '1590',
    'Bacillus cereus': '1396', 'Lactobacillus reuteri': '1598',
    'Bacteroides fragilis': '817',
}

# 논문 Table 4 가 depression 의 합병증으로 추론했다고 적은 것 (§4.1.2)
T4_COMPL = [('Autistic disorder', 'depression'), ('Bipolar disorder', 'depression'),
            ('Learning disabilities', 'depression')]
# 논문 표기 → KG 질병 라벨 패턴
COMPL_NAME = {'autistic disorder': 'autistic', 'autism': 'autistic',
              'depression': 'depressive', 'anxiety': 'anxiety',
              'bipolar disorder': 'bipolar', 'learning disabilities': 'learning',
              'parkinson disorder': 'parkinson', 'alzheimer disease': 'alzheimer'}


# 배포 KG 에는 우울증 노드가 둘이고 그 사이에 owl:sameAs 가 없다 —
#   D003865  MENDA 가 하위관계(hasPositive/NegativeAssociation)로 쓰는 쪽
#   D003866  MiKG 가 hasAssociation 으로 쓰는 쪽 (= MiKG#Depressive-disorder)
# 둘을 한 개념으로 볼지는 KG 가 정해 주지 않는다. 우리의 가정이고, 여기서 드러낸다.
# eval/paper_sparql.py 의 table5() 도 같은 병합을 한다 (§17.26).
MERGE_ASSUMED = [('http://id.nlm.nih.gov/mesh/D003865',
                  'http://id.nlm.nih.gov/mesh/D003866')]


def _canon_mesh(u):
    """MiKG 는 MeSH 를 /mesh/2020/D... 로, 배포 KG 는 /mesh/D... 로 쓴다."""
    return u.replace('/mesh/2020/', '/mesh/')


def complication(verbose=True):
    """§3.3 규칙 (b) 를 배포 KG 에 적용한다."""
    import pyoxigraph as ox

    uf = {}

    def find(x):
        uf.setdefault(x, x)
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb

    # MiKG — 클래스 계층과 영어 라벨, MeSH/SNOMED 로의 sameAs
    mikg_label, mikg_mental = {}, set()
    st = ox.Store()
    st.bulk_load(path=MIKG_TTL, format=ox.RdfFormat.TURTLE)
    for q in st:
        p, sub = str(q.predicate.value), _canon_mesh(str(q.subject.value))
        if p == SAMEAS and isinstance(q.object, ox.NamedNode):
            union(sub, _canon_mesh(str(q.object.value)))
        elif p == SUBCLS and str(q.object.value) == MENTAL:
            mikg_mental.add(sub)
        elif p == RDFS_LABEL and getattr(q.object, 'language', None) == 'en':
            mikg_label.setdefault(sub, q.object.value)

    # 배포 KG — 세균(NCBI taxon) → 질병, 그리고 질병 식별자 간 sameAs
    # 정신질환은 Mental_health.jsonld, 그 밖의 질병은 Disease_Bacteria.jsonld 에 있다.
    # Table 5 의 Parkinson·Alzheimer 는 후자에 있다 (§17.24).
    bac2dis = collections.defaultdict(set)
    in_mental = set()
    for fn in ('Mental_health.jsonld', 'Disease_Bacteria.jsonld'):
        for n in _jsonld_nodes(fn):
            for v in n.get(NPQ_ASSOC, []):
                d = _canon_mesh(v['@id'])
                bac2dis[n['@id']].add(d)
                if fn == 'Mental_health.jsonld':
                    in_mental.add(d)
    # §3.3: "subrelations ... both categorized under the main relation hasAssociation".
    # MENDA 는 하위관계를 쓰고 **방향이 반대**다 (질병 → 세균, §17.13). 포함관계가 KG 에
    # 선언돼 있지는 않지만 논문 서술대로 규칙 (b) 의 입력에 함께 넣는다. 이것을 빼면
    # Bifidobacterium longum–우울증 처럼 MENDA 로만 이어진 연결을 놓친다 (§17.26).
    # 세균 노드는 microbe 네임스페이스의 숫자 taxon id 다. 계통수는 .trig 에 있어서
    # isChildOf 유무로 판별하면 Bacteria_Ontology.trig 를 놓친다.
    is_taxon = re.compile(r'/entity/\d+$').search
    for fn in sorted(os.listdir(FKG)):
        if not fn.endswith('.jsonld'):
            continue
        for n in _jsonld_nodes(fn):
            for k, vs in n.items():
                if not (k.endswith('hasPositiveAssociation')
                        or k.endswith('hasNegativeAssociation')):
                    continue
                for v in (vs if isinstance(vs, list) else [vs]):
                    if isinstance(v, dict) and is_taxon(v.get('@id', '')):
                        bac2dis[v['@id']].add(_canon_mesh(n['@id']))
    # 라벨: MiKG(영어) 를 우선하고, 없으면 MeSH/Disease_Bacteria 의 rdfs:label
    kg_label = {}
    for fn in ('MESH_Disease.jsonld', 'Disease_Bacteria.jsonld'):
        for n in _jsonld_nodes(fn):
            vs = n.get(RDFS_LABEL)
            if not vs:
                continue
            vs = vs if isinstance(vs, list) else [vs]
            val = vs[0].get('@value') if isinstance(vs[0], dict) else vs[0]
            if isinstance(val, str):
                kg_label.setdefault(_canon_mesh(n['@id']), val)
    for fn in ('Mental_health.jsonld', 'MESH_Disease.jsonld'):
        for n in _jsonld_nodes(fn):
            for v in n.get(SAMEAS, []):
                if isinstance(v, dict) and '@id' in v:
                    union(_canon_mesh(n['@id']), _canon_mesh(v['@id']))

    for x, y in MERGE_ASSUMED:
        union(x, y)

    dis2bac = collections.defaultdict(set)
    for b, ds in bac2dis.items():
        for d in ds:
            dis2bac[find(d)].add(b)

    info = {}
    for d in dis2bac:
        ids = {u for u in uf if find(u) == d}
        lab = (next((mikg_label[u] for u in sorted(ids) if u in mikg_label), None)
               or next((kg_label[u] for u in sorted(ids) if u in kg_label), None))
        info[d] = dict(label=lab or d.rsplit('/', 1)[-1],
                       mental=bool(ids & mikg_mental) or d in in_mental,
                       n_bac=len(dis2bac[d]),
                       ids=sorted(u.rsplit('/', 1)[-1] for u in ids) or
                           [d.rsplit('/', 1)[-1]])

    ds = sorted(dis2bac)
    # 세균 → 질병 역색인으로 공유 쌍을 뽑는다 (263종 전수 비교를 피한다)
    import itertools
    b2d = collections.defaultdict(set)
    for d in ds:
        for b in dis2bac[d]:
            b2d[b].add(d)
    shared_pairs = set()
    for b, dd in b2d.items():
        shared_pairs.update(itertools.combinations(sorted(dd), 2))
    pairs = [dict(a=a, b=b, shared=len(dis2bac[a] & dis2bac[b]),
                  same_class=info[a]['mental'] and info[b]['mental'])
             for a, b in shared_pairs]

    ment = [d for d in ds if info[d]['mental']]
    n_pair_m = len(ment) * (len(ment) - 1) // 2
    cond1_m = sum(1 for p in pairs if info[p['a']]['mental'] and info[p['b']]['mental'])
    n_pair = len(ds) * (len(ds) - 1) // 2
    cond1 = len(pairs)
    cond12 = cond1_m

    # 논문 표기 → 개념
    def resolve(name):
        pat = COMPL_NAME[name.lower()]
        return next((d for d in ds if pat in info[d]['label'].lower()), None)

    P1 = {(p['a'], p['b']) for p in pairs}
    P1 |= {(b, a) for a, b in P1}
    P2 = {(p['a'], p['b']) for p in pairs if p['same_class']}
    P2 |= {(b, a) for a, b in P2}

    def _taxon(d):
        """그 질병에 붙은 세균의 taxon id 집합."""
        return {u.rsplit('/', 1)[-1] for u in dis2bac[d]}

    def check(table):
        """조건(1) 쌍이 세균을 공유하는가, 조건(1)+(2) 둘 다 정신질환인가,
        ev 논문이 근거로 든 **바로 그 세균**이 두 질병 모두에 붙는가.
        마지막 것이 eval/paper_sparql.py 의 table5() 와 같은 기준이다."""
        rows, c1, c2, ce = [], 0, 0, 0
        for item in table:
            a, b = item[0], item[1]
            ev = item[2] if len(item) > 2 else ''
            da, db = resolve(a), resolve(b)
            if da is None or db is None:
                rows.append((a, b, ev, None, None, None,
                             f'KG 에 없는 질병: {a if da is None else b}'))
                continue
            s1, s2 = (da, db) in P1, (da, db) in P2
            tx = T5_EVIDENCE_TAXON.get(ev)
            se = None if not ev else bool(tx and tx in _taxon(da) and tx in _taxon(db))
            c1 += s1
            c2 += s2
            ce += bool(se)
            rows.append((a, b, ev, s1, s2, se, ''))
        return rows, c1, c2, ce

    t5rows, t5c1, t5c2, t5ce = check(T5_COMPL)
    t4rows, t4c1, t4c2, _ = check(T4_COMPL)

    out = dict(n_disease=len(ds), n_pair_possible=n_pair,
               n_mental=len(ment), n_pair_mental=n_pair_m,
               cond1=cond1, cond1_2=cond12,
               triples=cond12 * 2, triples_all=cond1 * 2,
               t5_total=len(T5_COMPL), t5_cond1=t5c1, t5_cond1_2=t5c2,
               t5_evidence=t5ce,
               t4_total=len(T4_COMPL), t4_cond1=t4c1, t4_cond1_2=t4c2,
               diseases=[info[d] for d in sorted(ds, key=lambda x: -info[x]['n_bac'])])
    json.dump(out, open(COMPL_CACHE, 'w'), indent=1, ensure_ascii=False)

    if verbose:
        print('=' * 86)
        print('논문 §3.3 규칙 (b) — 합병증 추론')
        print('=' * 86)
        print('  규칙: 같은 gut microbiota 를 공유 ∧ 같은 상위 분류 → complication')
        print(f'\n  세균 연결이 있는 질병 개념 {len(ds)}개 '
              f'(그중 정신질환 {len(ment)}개 — 나머지는 Disease_Bacteria.jsonld)')
        for d in sorted(ment, key=lambda x: -info[x]['n_bac']):
            i = info[d]
            print(f'    {i["label"][:26]:28s} 세균 {i["n_bac"]:3d}  '
                  f'mentalDisorder={str(i["mental"]):5s} {i["ids"]}')
        print(f'\n  범위 A — 정신질환 {len(ment)}종만 (논문 조건 (2) 를 지킨 경우)')
        print(f'    조건 (1) 세균 공유 {cond1_m}/{n_pair_m} 쌍 '
              f'→ 트리플 {cond12 * 2}개 (양방향)')
        print(f'  범위 B — 세균 연결이 있는 질병 {len(ds)}종 전체 (조건 (2) 를 뺀 경우)')
        print(f'    조건 (1) 세균 공유 {cond1:,d}/{n_pair:,d} 쌍 '
              f'→ 트리플 {cond1 * 2:,d}개 (양방향)')
        for name, rows, c1, c2 in (('Table 5 Complication', t5rows, t5c1, t5c2),
                                   ('Table 4 Complication', t4rows, t4c1, t4c2)):
            print(f'\n  논문 {name} 재현')
            for a, b, ev, s1, s2, se, why in rows:
                if why:
                    print(f'    {a:22s} {b:12s} {ev:24s} {why}')
                    continue
                tail = '' if se is None else f'  근거세균 양쪽에 {"O" if se else "X"}'
                print(f'    {a:22s} {b:12s} {ev:24s} '
                      f'조건(1) {"O" if s1 else "X"}  조건(1)+(2) {"O" if s2 else "X"}{tail}')
            print(f'    → 조건(1) {c1}/{len(rows)},  조건(1)+(2) {c2}/{len(rows)}'
                  + (f',  논문이 든 근거 세균까지 {t5ce}/{len(rows)}'
                     if name.startswith('Table 5') else ''))
        print('\n  세 수치는 서로 다른 질문이다 —')
        print('    조건(1)        규칙 (b) 가 그 쌍을 **생성할 수 있는가**')
        print('    조건(1)+(2)    논문이 적은 분류 조건까지 지키는가')
        print('    근거 세균      논문이 Table 5 에 적은 **그 세균**이 두 질병에 붙는가')
        print('                   (eval/paper_sparql.py 의 table5() 와 같은 기준)')
        print(f'\n  저장: {COMPL_CACHE}')
    return out


NPQ_METAB = 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#hasMetabolites'
# Table 5 Diet recommendation 행이 쓰는 성분 — (이름, KEGG, 분류)
COV_COMPOUNDS = [('Threonine', 'C00188', 'amino'), ('Cystine', 'C01420', 'amino'),
                 ('Lysine', 'C00047', 'amino'), ('Glutamate', 'C00025', 'amino'),
                 ('alpha-Tocopherol', 'C02477', 'vitamin'), ('Niacin', 'C00253', 'vitamin'),
                 ('Ascorbate', 'C00072', 'vitamin')]


def coverage(verbose=True):
    """Table 5 Diet 행이 왜 성립하지 않는지의 두 원인을 센다 (§17.25).
    (1) 성분별 측정 음식 수 — 아미노산이 비타민보다 훨씬 희소한가
    (2) 대사(hasMetabolites) 세균과 질병연관(hasAssociation) 세균의 겹침
    """
    import pyoxigraph as ox

    # (1) KEGG id 별로, 그 성분이 >0 으로 기록된 음식 수
    nut_of = {}          # nutrient 노드 -> kegg id
    want = {k for _, k, _ in COV_COMPOUNDS}
    unit_nut, unit_food = collections.defaultdict(set), collections.defaultdict(set)
    pos_unit = set()
    for fname in sorted(os.listdir(FKG)):
        if not fname.endswith(('.jsonld', '.trig')):
            continue
        st, oxm = _store(fname)
        for q in st:
            p_ = str(q.predicate.value).rsplit('#', 1)[-1].rsplit('/', 1)[-1]
            sub = str(q.subject.value)
            if p_ == 'sameAs' and isinstance(q.object, oxm.NamedNode):
                kid = str(q.object.value).rsplit('/', 1)[-1]
                if kid in want:
                    nut_of[sub] = kid
            elif p_ == 'hasNutrientWeights' and isinstance(q.object, oxm.NamedNode):
                u = str(q.object.value)
                unit_nut[u].add(sub)
                unit_food[u].add(sub)
            elif p_ == 'value':
                try:
                    if float(q.object.value) > 0:
                        pos_unit.add(sub)
                except (TypeError, ValueError):
                    pass
    per = {}
    for name, kid, kind in COV_COMPOUNDS:
        nodes = {n for n, k in nut_of.items() if k == kid}
        units = {u for u in unit_nut if unit_nut[u] & nodes} & pos_unit
        foods = set()
        for u in units:
            foods |= (unit_food[u] - nodes)
        per[name] = dict(kegg=kid, kind=kind, n_food=len(foods))

    # (2) 대사 세균 ∩ 질병연관 세균
    met, asc = set(), set()
    for fname in sorted(os.listdir(FKG)):
        if not fname.endswith(('.jsonld', '.trig')):
            continue
        st, _ = _store(fname)
        for q in st:
            p_ = str(q.predicate.value)
            if p_ == NPQ_METAB:
                met.add(str(q.subject.value))
            elif p_ == NPQ_ASSOC:
                asc.add(str(q.subject.value))

    amino = [v['n_food'] for v in per.values() if v['kind'] == 'amino']
    vit = [v['n_food'] for v in per.values() if v['kind'] == 'vitamin']
    out = dict(per_compound=per,
               amino_max=max(amino), vitamin_min=min(vit),
               ratio=round(min(vit) / max(max(amino), 1), 1),
               n_metabolism=len(met), n_association=len(asc),
               n_both=len(met & asc))
    json.dump(out, open(COV_CACHE, 'w'), indent=1, ensure_ascii=False)
    if verbose:
        print('=' * 86)
        print('Table 5 Diet 행이 성립하지 않는 두 원인 (§17.25)')
        print('=' * 86)
        print('  (1) 성분이 >0 으로 기록된 음식 수')
        for name, kid, kind in COV_COMPOUNDS:
            print(f'      {name:18s} {kind:8s} {per[name]["n_food"]:>7,d}')
        print(f'      → 아미노산 최대 {out["amino_max"]:,d} vs 비타민 최소 '
              f'{out["vitamin_min"]:,d}  ({out["ratio"]}배)')
        print(f'  (2) 대사 세균 {len(met)} · 질병연관 세균 {len(asc)} · '
              f'둘 다 {len(met & asc)}')
        print(f'      → 음식–성분–세균–질병 4단 경로를 완성할 수 있는 세균은 '
              f'{len(met & asc)}종뿐')
        print(f'\n  저장: {COV_CACHE}')
    return out


def load_cached_coverage():
    if not os.path.exists(COV_CACHE):
        return None
    return json.load(open(COV_CACHE))


def load_cached_complication():
    if not os.path.exists(COMPL_CACHE):
        return None
    return json.load(open(COMPL_CACHE))


def relations_summary(dr):
    return dict(n=len(dr), present=int(dr.present.sum()),
                self_defined=int(dr[dr.category == 'self-defined'].present.sum()),
                predefined=int(dr[dr.category == 'predefined'].present.sum()),
                subproperty_decl=len(dr.attrs.get('subproperty_decl', [])),
                inferred_paper=INFERRED_PAPER, inferred_kg=0)


# ------------------------------------------------------------------
# 실행 · 집계
# ------------------------------------------------------------------
def run(scanned=None):
    scanned = scanned or scan_all()
    rows = []
    for name, rel, ent, tri, files in TABLE1:
        rel_files = REL_FILES.get(name, files)
        if not files:
            rows.append(dict(source=name, paper_relation=rel, paper_entity=ent,
                             rel_sum=None, rel_uniq=None, entity=None, present=False))
            continue
        rows.append(dict(
            source=name, paper_relation=rel, paper_entity=ent,
            rel_sum=sum(len(scanned[f][0]) for f in rel_files),
            rel_uniq=len(set().union(*(scanned[f][0] for f in rel_files))),
            entity=sum(len(scanned[f][1]) + len(scanned[f][2]) + len(scanned[f][3])
                       for f in files),
            present=True))
    return pd.DataFrame(rows)


def summary(df, scanned=None):
    got = df[df.present]
    return dict(
        n_source=len(df), n_present=int(df.present.sum()),
        relation_match=int((got.rel_sum == got.paper_relation).sum()),
        entity_match=int((got.entity == got.paper_entity).sum()),
        relation_total_sum=int(got.rel_sum.sum()),
        entity_total=int(got.entity.sum()),
        paper=PAPER_TOTAL,
        paper_relation_colsum=sum(r for _, r, _, _, _ in TABLE1),
        paper_entity_colsum=sum(e for _, _, e, _, _ in TABLE1),
    )


def linking_summary(dl):
    got = dl.dropna(subset=['value'])
    hit = got[got.match]
    conf = got[got.match & (got.get('confidence', '확정') == '확정')]
    return dict(n_item=dl.item.nunique(),
                n_item_match=hit.item.nunique(),
                n_item_confirmed=conf.item.nunique(),
                n_def=len(got), n_def_match=int(got.match.sum()),
                paper_total=LINKING_TOTAL)


def load_cached():
    if not os.path.exists(CSV):
        return None
    return pd.read_csv(CSV)


def load_cached_linking():
    if not os.path.exists(CSV_LINK):
        return None
    return pd.read_csv(CSV_LINK)


def load_cached_inference():
    if not os.path.exists(INFER_CACHE):
        return None
    return json.load(open(INFER_CACHE))


def load_cached_relations():
    if not os.path.exists(CSV_REL):
        return None
    return pd.read_csv(CSV_REL)


def report(save=True):
    scanned = scan_all()
    df = run(scanned)
    s = summary(df)
    body = body_counts(scanned)

    print('=' * 86)
    print('논문 §3.1 Table 1 — Relation · Entity 열  (Triples 열은 eval/paper_sparql.py)')
    print('=' * 86)
    print(f'  {"Source":24s} {"Relation (논문/합/중복제거)":>24s}   {"Entity (논문 / 공개 KG)":>30s}')
    for _, r in df.iterrows():
        if not r.present:
            print(f'  {r.source:24s} {r.paper_relation:>6d} /   없음 /   없음   '
                  f'{r.paper_entity:>11,d} /      없음')
            continue
        rs, ru, en = int(r.rel_sum), int(r.rel_uniq), int(r.entity)
        rm = '일치' if rs == r.paper_relation else ''
        em = '일치' if en == r.paper_entity else ''
        print(f'  {r.source:24s} {r.paper_relation:>6d} / {rs:>6d} / {ru:>6d} {rm:4s} '
              f'{r.paper_entity:>11,d} / {en:>11,d} {em}')
    print()
    print(f'  relation 일치 {s["relation_match"]}/{s["n_present"]} 소스 (합 정의)   '
          f'공개 KG 합 {s["relation_total_sum"]}')
    print(f'  entity   일치 {s["entity_match"]}/{s["n_present"]} 소스   '
          f'공개 KG 합 {s["entity_total"]:,d}')
    print()
    print('  Total 행은 두 열 모두 자기 열의 합이 아니다')
    print(f'    relation  열 합 {s["paper_relation_colsum"]} / Total 행 '
          f'{PAPER_TOTAL["relation"]}   (Total 만 중복 제거로 보인다)')
    print(f'    entity    열 합 {s["paper_entity_colsum"]:,d} / Total 행 '
          f'{PAPER_TOTAL["entity"]:,d}   (Total 은 §3.2 의 normalized 수치다)')
    print()
    print('  Table 1 에 대응이 없는 공개 KG 파일')
    for f in UNMAPPED + ['Food_Category.jsonld']:
        pr, su, ob, lt = scanned[f]
        print(f'    {f:30s} relation {len(pr):3d}  entity {len(su)+len(ob)+len(lt):>7,d}'
              + ('   ※ relation 은 FDC row 에 포함되지만 entity·triples 는 아니다'
                 if f == 'Food_Category.jsonld' else ''))
    print()
    print('  §3.1 본문 수치')
    for label, paper, key in BODY:
        ours = body[key]
        print(f'    {label:22s} 논문 {paper:>9,d}  공개 KG {ours:>9,d}  '
              f'{"일치" if ours == paper else ""}')
        if key == 'kegg_metabolite':
            print(f'    {"  └ 정의: pq:hasNutrients 의 고유 목적어 (§17.14)":46s}')
            print(f'    {"  └ 참고: KEGG compound 전체":22s} {"":>9s}  공개 KG '
                  f'{body["kegg_compound_all"]:>9,d}')
    # ---- §3.2 Entity linking ----
    dl = linking(scanned)
    sl = linking_summary(dl)

    print()
    print('=' * 86)
    print('논문 §3.2 Entity linking — 정규화 결과 수치')
    print('=' * 86)
    for item in [i for i, _ in LINKING]:
        sub = dl[dl.item == item]
        paper = int(sub.paper.iloc[0])
        print(f'  {item:20s} 논문 {paper:>9,d}')
        for _, r in sub.iterrows():
            v = '측정 불가' if pd.isna(r.value) else f'{int(r.value):>9,d}'
            mark = ('일치' if r.get('confidence', '확정') == '확정' else '일치(추정)') \
                if r.match else ''
            print(f'      {r.definition:40s} {v}  {mark}')
    print()
    print(f'  일치한 항목 {sl["n_item_match"]}/{sl["n_item"]}   '
          f'(그중 확정 {sl["n_item_confirmed"]}, 추정 '
          f'{sl["n_item_match"] - sl["n_item_confirmed"]})   '
          f'시도한 정의 {sl["n_def"]}개')
    print(f'  논문 합계 {LINKING_TOTAL:,d} — Table 1 의 Entity Total 행과 같은 값이다.')
    print('    다만 §3.2 자신의 네 수치를 더해도(128+23,212+984,031+3,505=1,010,876),')
    print('    Table 1 Entity 열을 더해도(4,995,950) 그 값이 나오지 않는다')
    print()
    print('  남은 것 — 합계뿐이다 (§17.12)')
    for item, why in UNRESOLVED.items():
        print(f'    [{item}]')
        for line in __import__('textwrap').wrap(why, 78):
            print(f'      {line}')


    # ---- §3.3 Knowledge representation ----
    dr = relations()
    sr = relations_summary(dr)
    print()
    print('=' * 86)
    print('논문 §3.3 Knowledge representation — 관계 유형 세 가지')
    print('=' * 86)
    for cat in ('self-defined', 'predefined'):
        print(f'  [{cat}]')
        for _, r in dr[dr.category == cat].iterrows():
            print(f'    {r.relation:26s} {r["count"]:>9,d}  '
                  f'{"있음" if r.present else "없음"}  {r.files}')
    print('  [inferred]')
    print(f'    {"추론 statements":26s} {sr["inferred_kg"]:>9,d}  없음  '
          f'논문 {INFERRED_PAPER:,d} (§17.1 — 배포본에서 제외됐다)')
    print()
    print(f'  어휘 존재 {sr["present"]}/{sr["n"]}'
          f'  (self-defined {sr["self_defined"]}/3, predefined {sr["predefined"]}/3)')
    print(f'  hasAssociation ⊃ hasPositive/NegativeAssociation 포함관계 선언: '
          f'{sr["subproperty_decl"]}건'
          + ('  ← 논문 §3.3 의 서술이 KG 에 선언돼 있지 않다'
             if sr['subproperty_decl'] == 0 else ''))
    print(f'    (KG 전체 subPropertyOf {dr.attrs["subproperty_total"]}건, '
          f'전부 FoodOn 내부 관계)')
    print()
    print('  세 관계가 실제로 어떻게 쓰이는가')
    h = relation_hierarchy()
    for n, u in h['use'].items():
        sk = ', '.join(f'{k} {v:,d}' for k, v in u['skind'].most_common(2))
        ok = ', '.join(f'{k} {v:,d}' for k, v in u['okind'].most_common(3))
        print(f'    {n:24s} {len(u["pairs"]):>5,d}쌍  {sorted(u["files"])}')
        print(f'    {"":24s}   주어  {sk}')
        print(f'    {"":24s}   목적어 {ok}')
    print(f'    일반↔하위 (주어,목적어) 쌍 겹침 {h["generic_sub_overlap"]}건, '
          f'주어 집합 겹침 {h["subject_overlap"]}건')
    print(f'    방향을 무시해도 같은 쌍을 가리키는 경우 {h["undirected_overlap"]}건'
          + ('  ← 두 층이 같은 사실을 기술한 적이 한 번도 없다'
             if h['undirected_overlap'] == 0 else ''))
    print(f'    우울증(D003865) 한정 — 일반관계로 연결된 미생물 {h["dep_generic"]}종, '
          f'하위관계로 연결된 미생물 {h["dep_sub"]}종, 공통 {h["dep_shared"]}종')
    print(f'    hasPositive ∩ hasNegative {h["pos_neg_overlap"]}쌍'
          + ('  — KG 는 방향을 특정하지 않는다 (§4.2.1 의 E 는 ±1 하나를 요구한다)'
             if h['pos_neg_overlap'] else ''))

    if save:
        df.to_csv(CSV, index=False)
        dl.to_csv(CSV_LINK, index=False)
        dr.to_csv(CSV_REL, index=False)
        print()
        print(f'저장: {CSV}')
        print(f'저장: {CSV_LINK}')
        print(f'저장: {CSV_REL}')
    return df, dl, dr


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'complication':
        complication()
    elif len(sys.argv) > 1 and sys.argv[1] == 'coverage':
        coverage()
    else:
        report()
        print()
        complication()
        print()
        coverage()
