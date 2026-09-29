"""
Food4healthKG Knowledge Query 구현
====================================
논문 Section 4.1의 3가지 Knowledge Query를 Python으로 구현.
SPARQL 대신 JSON-LD/TTL 직접 파싱.

Query Type 1: food × nutrient → gut metabolite (Table 2)
Query Type 2: food → compound → bacteria → depression (Table 3) ★ 핵심
Query Type 3: food → compound → bacteria → depression + complications (Table 4)

결과: compound별 incidence (+1/-1)를 데이터 기반으로 결정하여 weight.csv 업데이트

실행: knowledge_inference_v3.py 대신 이 파일 사용 가능
  python3 knowledge_query.py
"""

import json, re
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MIKG_DIR = os.path.join(BASE_DIR, 'MiKG-JAIMS')
if not os.path.exists(MIKG_DIR):
    MIKG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'MiKG-JAIMS')

# ============================================================
# KG 데이터 로드 (공통)
# ============================================================
print("[1/7] KG 데이터 로드...")

# --- MENDA: compound ↔ depression (+/-) ---
with open(os.path.join(BASE_DIR, 'foodkg_triply/MENDA_Depression.jsonld')) as f:
    menda = json.load(f)

menda_pos, menda_neg = set(), set()
menda_compound_disease = []  # (compound, direction, disease_uri)
for entry in menda:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            for v in (vals if isinstance(vals, list) else [vals]):
                if isinstance(v, dict) and '@id' in v:
                    cid = v['@id'].split('/')[-1]
                    if cid.startswith('C'):
                        if 'Positive' in key:
                            menda_pos.add(cid)
                            menda_compound_disease.append((cid, +1))
                        elif 'Negative' in key:
                            menda_neg.add(cid)
                            menda_compound_disease.append((cid, -1))

print(f"  MENDA: pos={len(menda_pos)}, neg={len(menda_neg)}")

# --- KEGG_Compound_Bacteria: bacteria → compounds (hasMetabolites) ---
with open(os.path.join(BASE_DIR, 'foodkg_triply/KEGG_Compound_Bacteria.jsonld')) as f:
    cb = json.load(f)

bact_to_compounds = {}  # bacteria_id → set(kegg_ids)
compound_to_bacts = {}  # kegg_id → set(bacteria_ids)
for entry in cb:
    for node in entry.get('@graph', []):
        bid = node.get('@id', '')
        for key, vals in node.items():
            if 'hasMetabolites' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        cid = v['@id'].split('/')[-1]
                        bact_to_compounds.setdefault(bid, set()).add(cid)
                        compound_to_bacts.setdefault(cid, set()).add(bid)

print(f"  CB: {len(bact_to_compounds)} bacteria, {len(compound_to_bacts)} compounds")

# --- Disease_Bacteria: bacteria → disease (hasAssociation) ---
with open(os.path.join(BASE_DIR, 'foodkg_triply/Disease_Bacteria.jsonld')) as f:
    db = json.load(f)

bact_to_diseases = {}
disease_to_bacts = {}
for entry in db:
    for node in entry.get('@graph', []):
        nid = node.get('@id', '')
        if not nid.startswith('http://nlp_microbe'):
            continue
        for key, vals in node.items():
            if 'hasAssociation' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        did = v['@id']
                        bact_to_diseases.setdefault(nid, set()).add(did)
                        disease_to_bacts.setdefault(did, set()).add(nid)

print(f"  DB: {len(bact_to_diseases)} bacteria → diseases")

# --- Bacteria_Ontology: entity_id → name ---
bact_id_to_name = {}
bact_name_to_ids = {}
with open(os.path.join(BASE_DIR, 'foodkg_triply/Bacteria_Ontology.trig')) as f:
    for line in f:
        if 'label' in line:
            id_m = re.search(r'<(http://nlp_microbe[^>]+)>', line)
            label_m = re.search(r'"([^"]+)"', line)
            if id_m and label_m:
                eid = id_m.group(1)
                name = label_m.group(1)
                bact_id_to_name[eid] = name
                bact_name_to_ids.setdefault(name.lower(), []).append(eid)

print(f"  Bacteria names: {len(bact_id_to_name)}")

# --- Food nutrient data ---
df_fn = pd.read_csv(os.path.join(BASE_DIR, 'food_nutrient.csv'), low_memory=False)
kegg_names = df_fn[df_fn['nutrient_kegg'].astype(str).str.startswith('C')][
    ['nutrient_name', 'nutrient_kegg']
].drop_duplicates().groupby('nutrient_kegg')['nutrient_name'].apply(lambda x: x.iloc[0]).to_dict()

# compound 집합은 food.csv(논문 85개, 논문 열 순서)를 따른다.
# reconstruct.py가 만들어 둔 것을 그대로 쓰므로 weight.csv와 열이 항상 일치한다.
_food_csv = os.path.join(BASE_DIR, 'analyse/food.csv')
food_kegg = [c for c in pd.read_csv(_food_csv, nrows=0).columns if str(c).startswith('C')]

# 논문과 우리 데이터의 KEGG ID 차이 (reconstruct.py의 KEGG_ALIAS와 동일).
# MENDA/KEGG 조회 시 두 ID를 모두 확인하기 위한 표.
import kegg_alias
KEGG_ALIAS = kegg_alias.FOOD_ALIAS
def kegg_keys(c):
    """compound c를 조회할 때 확인할 KEGG ID 집합 (food/incidence alias 모두)."""
    return kegg_alias.incidence_keys(c)

for _pk, _ours in KEGG_ALIAS.items():
    if _pk in kegg_names or _ours not in kegg_names:
        continue
    kegg_names[_pk] = kegg_names[_ours]

print(f"  Food KEGG compounds: {len(food_kegg)}")

# --- MiKG: bacteria → neurotransmitter → depression ---
mikg_path = os.path.join(MIKG_DIR, 'MiKG_Schema_Data_20201007.ttl')
mikg_ntm_precursors = {}
if os.path.exists(mikg_path):
    with open(mikg_path) as f:
        mikg_content = f.read()
    dep_ntm = re.findall(
        r'hasNeurotransmitter\s+mikg:(\S+)\s*;\s*\n\s*mikg:hasMentalDisorder\s+mikg:Depressive-disorder',
        mikg_content
    )
    # neurotransmitter → precursor (KEGG)
    ntm_precursor_map = {
        'Serotonin': [('C00806', 'Tryptophan')],
        'Dopamine': [('C01536', 'Tyrosine'), ('C02057', 'Phenylalanine')],
        'Norepinephrine': [('C01536', 'Tyrosine'), ('C00072', 'Vitamin C')],
        'GABA': [('C00025', 'Glutamic acid'), ('C05776', 'Vitamin B-12')],
        'Histamine': [('C00768', 'Histidine')],
        'Acetylcholine': [('C00114', 'Choline'), ('C00588', 'Phosphocholine'), ('C00670', 'GPC')],
    }
    for ntm in dep_ntm:
        if ntm in ntm_precursor_map:
            for kegg_id, name in ntm_precursor_map[ntm]:
                mikg_ntm_precursors[kegg_id] = (ntm, name)
    print(f"  MiKG: {len(dep_ntm)} depression NTMs, {len(mikg_ntm_precursors)} precursors")
else:
    print(f"  MiKG: 파일 없음 ({mikg_path})")

# --- Mental health disease URIs ---
dep_mesh = 'http://id.nlm.nih.gov/mesh/D003865'

# Mental_health.jsonld에서 depression sameAs
with open(os.path.join(BASE_DIR, 'foodkg_triply/Mental_health.jsonld')) as f:
    mh = json.load(f)

dep_uris = {dep_mesh}
for entry in mh:
    for node in entry.get('@graph', []):
        if node.get('@id') == dep_mesh:
            for key, vals in node.items():
                if 'sameAs' in key:
                    for v in (vals if isinstance(vals, list) else [vals]):
                        if isinstance(v, dict) and '@id' in v:
                            dep_uris.add(v['@id'])

# hasAssociation으로 연결된 모든 mental disorder URI도 수집
all_mental_uris = set()
for entry in mh:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            if 'hasAssociation' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        all_mental_uris.add(v['@id'])

print(f"  Depression URIs: {len(dep_uris)}, All mental URIs: {len(all_mental_uris)}")

# ============================================================
# Query Type 2: food → compound → bacteria → depression
# 논문 Table 3 재현 — 핵심 incidence 추출
# ============================================================
print(f"\n{'='*70}")
print("[2/7] Query Type 2: compound → bacteria → depression")
print(f"{'='*70}")

# 경로: compound가 bacteria에 의해 대사됨 (CB)
#       + 그 bacteria가 depression과 연관됨 (DB)
# → compound는 depression과 간접 연관

# depression 관련 bacteria (depression URI + sameAs + complications)
dep_bacteria = set()
for d_uri in dep_uris:
    dep_bacteria.update(disease_to_bacts.get(d_uri, set()))

# 더 넓은 범위: all mental health diseases의 bacteria도 포함
mental_bacteria = set()
for d_uri in all_mental_uris:
    mental_bacteria.update(disease_to_bacts.get(d_uri, set()))

# 전체 diseases에서 depression 관련만 필터 (label 기반)
for entry in db:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            if 'label' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict):
                        lbl = v.get('@value', '').lower()
                        if any(w in lbl for w in ['depress', 'anxiety', 'bipolar', 'autism',
                                                    'schizo', 'mood', 'obsessive', 'panic',
                                                    'stress', 'anorexia', 'bulimia', 'adhd']):
                            nid = node.get('@id', '')
                            mental_bacteria.update(disease_to_bacts.get(nid, set()))

print(f"  Depression bacteria (strict): {len(dep_bacteria)}")
print(f"  Mental health bacteria (broad): {len(mental_bacteria)}")

# compound → bacteria path 추출
query2_results = []

for compound in food_kegg:
    # 이 compound를 대사하는 bacteria
    metabolizers = compound_to_bacts.get(compound, set())
    
    # 그 중 depression/mental health 연관 bacteria
    dep_metabolizers = metabolizers & dep_bacteria
    mental_metabolizers = metabolizers & mental_bacteria
    
    if dep_metabolizers or mental_metabolizers:
        for bid in (dep_metabolizers | mental_metabolizers):
            bname = bact_id_to_name.get(bid, bid.split('/')[-1])
            diseases = bact_to_diseases.get(bid, set())
            is_dep = bool(diseases & dep_uris)
            
            query2_results.append({
                'compound': compound,
                'compound_name': kegg_names.get(compound, '?'),
                'bacteria_id': bid,
                'bacteria_name': bname,
                'is_depression': is_dep,
                'diseases': diseases,
            })

df_q2 = pd.DataFrame(query2_results)
print(f"  Query Type 2 결과: {len(df_q2)} paths")
print(f"  Unique compounds with bacteria path: {df_q2['compound'].nunique()}")

# compound별 경로 수 집계
if len(df_q2) > 0:
    compound_paths = df_q2.groupby('compound').agg(
        n_bacteria=('bacteria_id', 'nunique'),
        n_dep_bacteria=('is_depression', 'sum'),
    ).sort_values('n_bacteria', ascending=False)
    print(f"\n  Top compound-bacteria paths:")
    for c, row in compound_paths.head(20).iterrows():
        print(f"    {c} ({kegg_names.get(c, '?'):30s}) → {int(row['n_bacteria'])} bacteria ({int(row['n_dep_bacteria'])} depression)")

# ============================================================
# Query Type 3: depression + complications (inference)
# 논문 Table 4 재현
# ============================================================
print(f"\n{'='*70}")
print("[3/7] Query Type 3: depression + complications (inference)")
print(f"{'='*70}")

# 논문 Section 4.1: "depression and anxiety are both mood disorders
# with shared associations with the same gut microbiota
# → infer implicit relationship as complications"

# depression bacteria와 같은 bacteria를 공유하는 다른 disease = complication 후보
complication_diseases = set()
for bid in dep_bacteria | mental_bacteria:
    diseases = bact_to_diseases.get(bid, set())
    complication_diseases.update(diseases)

complication_diseases -= dep_uris  # depression 자체 제외

# MeSH label로 확인
mesh_labels = {}
with open(os.path.join(BASE_DIR, 'foodkg_triply/MESH_Disease.jsonld')) as f:
    md = json.load(f)
for entry in md:
    for node in entry.get('@graph', []):
        nid = node.get('@id', '')
        for key, vals in node.items():
            if 'label' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@value' in v:
                        mesh_labels[nid] = v['@value']

# Disease_Bacteria에서도 label 추출
for entry in db:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            if 'label' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@value' in v:
                        mesh_labels[node.get('@id', '')] = v['@value']

print(f"  Depression complications (shared bacteria): {len(complication_diseases)}")
mental_complications = []
for d in complication_diseases:
    label = mesh_labels.get(d, '?')
    if any(w in label.lower() for w in ['disorder', 'disease', 'syndrome', 'anxiety',
                                          'bipolar', 'autism', 'schizo', 'depress',
                                          'dementia', 'alzheimer', 'parkinson', 'adhd',
                                          'obsessive', 'ptsd', 'anorexia', 'insomnia']):
        shared = len(disease_to_bacts.get(d, set()) & (dep_bacteria | mental_bacteria))
        mental_complications.append((d, label, shared))

mental_complications.sort(key=lambda x: -x[2])
print(f"  Mental health complications: {len(mental_complications)}")
for d, label, shared in mental_complications[:15]:
    print(f"    {label:40s} (shared bacteria: {shared})")

# ============================================================
# Query Type 1: food → nutrient → gut metabolite
# ============================================================
print(f"\n{'='*70}")
print("[4/7] Query Type 1: food → nutrient weight (Table 2 검증)")
print(f"{'='*70}")

# p5_foodname.txt 음식들의 compound weight 검증
with open(os.path.join(BASE_DIR, 'analyse/p5_foodname.txt')) as f:
    p5_foods = [l.strip() for l in f if l.strip()]

# 비타민 B12 (C05776) 예시
b12 = df_fn[
    (df_fn['nutrient_kegg'] == 'C05776') & 
    (df_fn['food_name'].str.lower().str.contains('milk|egg', na=False))
].head(10)
print(f"  비타민 B-12 in milk/egg products (논문 Table 2 재현):")
print(f"  {'Food':<40s} {'Amount':>10s}")
for _, row in b12.iterrows():
    print(f"  {row['food_name'][:40]:<40s} {row['amount']:>10.3f} {row['nutrient_unit']}")

# ============================================================
# Incidence 통합: Query 결과 기반
# ============================================================
print(f"\n{'='*70}")
print("[5/7] Incidence 통합 (Knowledge Query 기반)")
print(f"{'='*70}")

# 우선순위:
# 1. MENDA direct (+/-)
# 2. Query Type 2: bacteria path → depression (KG 데이터 기반)
# 3. MiKG neurotransmitter precursor
# 4. Ontology inference
# 5. Literature

# Query Type 2에서 추출한 compound set
q2_compounds = set(df_q2['compound'].unique()) if len(df_q2) > 0 else set()

# Ontology rules (이전과 동일)
# P4/P5 규칙은 논문에 근거가 없는 수동 입력이다. A/B 비교를 위해 끌 수 있게 한다.
#   ontology : KG의 subClassOf 체인을 모사한 부모-자식 매핑 (구조적 추론)
#   literature: 문헌에서 직접 읽은 방향값 (완전 수동)
USE_ONTOLOGY   = os.environ.get('USE_ONTOLOGY',   '1') == '1'
# literature 규칙은 논문에 근거가 없는 수동 입력이라 기본 OFF.
# 대신 아래 GROUP_PRIOR(논문 §4.2.3 인용)를 쓴다.
USE_LITERATURE = os.environ.get('USE_LITERATURE', '0') == '1'
# full    : Trace/Macro = -1, Carb/Vit = +1  (§4.2.3 전체)
# carbvit : Carb/Vit = +1 만            (미네랄은 근거 없음 -> 0 유지)
# none    : 끔
# 'carbvit' 채택. tools/ab.py fallback 재측정(2026-09-29, 순위 지표):
#   A literature     Spearman +0.159  Top30 10/30  gold 7/9   (수동값 21개)
#   B group_full     Spearman -0.029  Top30  3/30  gold 8/9
#   C group_carbvit  Spearman -0.063  Top30  5/30  gold 8/9   <- 채택
#   D none           Spearman -0.303  Top30  6/30  gold 7/9   (구 기본값)
# 구 기본값 D 는 A 에 모든 지표에서 지배당한다. C 는 독립 기준(gold)이 최고이고
# 수동 입력값이 없으며 논문 §4.2.3 을 인용할 수 있다.
# A 가 순위는 가장 좋지만 출처 불명의 수동값 21개에 의존한다.
GROUP_PRIOR_MODE = os.environ.get('GROUP_PRIOR_MODE', 'carbvit')
# MENDA에 pos/neg가 동시에 존재할 때 근거 없이 +1을 줄 것인가 (구 동작)
MENDA_BOTH_DEFAULT_POS = os.environ.get('MENDA_BOTH_DEFAULT_POS', '0') == '1'
# hasPositiveAssociation 을 '완화'로 읽을 것인가(구 동작) '질병과 양의 상관'으로
# 읽을 것인가(교정). 기본은 교정. 근거는 아래 P1 주석 참조.
# 기본 1 = 논문 동작. 논문 §4.2.1 은 "a value of 1 indicates a positive
# relationship ... (relieving the disease)" 라고 적어 hasPositiveAssociation 을
# +1 로 쓴다. 그런데 그 목록은 MENDA 의 'Up'(우울증에서 증가)이다(Jaccard 0.981).
# 즉 논문 자신이 반전 오류를 범했고, 재현하려면 논문을 따라야 한다.
#   0 으로 두면 과학적으로 옳은 극성이 되지만 gold 8/9 -> 7/9,
#   Spearman -0.063 -> -0.155 로 논문에서 멀어진다 (REPRODUCTION.md §13).
MENDA_POS_MEANS_RELIEF = os.environ.get('MENDA_POS_MEANS_RELIEF', '1') == '1'

# MENDA 에 pos/neg 가 동시에 있는 compound 를 MENDA 원본(menda.xlsx)의
# study 단위 카운트로 가를 것인가.
#   'none'  미확정으로 두고 step4 ProMENDA 가 채움 (구 동작)
#   'orig'  MENDA 원본 down:up 을 마진으로 판정 (논문이 실제로 쓴 소스)
# 극성은 위 MENDA_POS_MEANS_RELIEF 와 일관되게 맞춘다.
MENDA_BOTH_TIEBREAK = os.environ.get('MENDA_BOTH_TIEBREAK', 'orig')
MENDA_ORIG_MARGIN = float(os.environ.get('MENDA_ORIG_MARGIN', '0.10'))

_MENDA_ORIG = {}
if MENDA_BOTH_TIEBREAK == 'orig':
    _mo_path = os.path.join(BASE_DIR, 'menda.xlsx')
    if os.path.exists(_mo_path):
        _mo = pd.read_excel(_mo_path, sheet_name='Metabolite')
        _mo['k'] = _mo['KEGG'].astype(str).str.extract(r'(C\d{5})')[0]
        _rr = _mo['Up/Down_regulated '].astype(str).str.strip().str.lower()
        _mo['u'] = _rr.str.startswith(('up', 'increas', 'higher'))
        _mo['d'] = _rr.str.startswith(('down', 'decreas', 'lower'))
        _g = _mo.dropna(subset=['k']).groupby('k').agg(
            up=('u', 'sum'), down=('d', 'sum'))
        _MENDA_ORIG = {k: (int(r['up']), int(r['down']))
                       for k, r in _g.iterrows()}
        print(f"  MENDA 원본 tie-break 로드: {len(_MENDA_ORIG)}종")
    else:
        print("  ⚠ menda.xlsx 없음 — MENDA_both tie-break 비활성")


def menda_orig_dir(ks):
    """MENDA 원본 study 카운트로 방향 판정. 없거나 마진 미달이면 0."""
    for k in ks:
        if k in _MENDA_ORIG:
            up, dn = _MENDA_ORIG[k]
            t = up + dn
            if t < 2 or abs(up - dn) / t < MENDA_ORIG_MARGIN:
                return 0
            # 논문 극성과 일관: up(질병에서 증가) 이 hasPositiveAssociation 이고
            # 논문은 그것을 +1 로 쓴다.
            hi = +1 if up > dn else -1
            return hi if MENDA_POS_MEANS_RELIEF else -hi
    return 0

# 논문 §4.2.3 (Fig. 4(c) 해설):
#   "the recommended foods are rich in essential nutrients that may have positive
#    effects on managing depression. On the other hand, the nonrecommended foods
#    seem to contain higher levels of trace elements and macronutrients that might
#    not be beneficial for individuals with depression."
#   "...significant differences in compound composition between the two groups,
#    particularly in most of the carbohydrates and vitamins."
#
# 즉 논문은 Fig. 4(c)의 6개 biological group 중 4개에 방향을 부여한다.
# Amino acid / Lipids는 "nonsignificant differences"라 했으므로 제외한다.
#
# 이 규칙은 MENDA/ProMENDA/MiKG/ontology 어디서도 근거를 못 얻은 compound에만
# fallback으로 적용한다. 특히 미네랄 10종(Trace Elements 5 + Macronutrient 5)은
# 대사체 데이터베이스가 원소를 측정하지 않아 ProMENDA 행이 0이다.
_GROUP_PRIOR_FULL = {
    'Trace Elements':         -1,
    'Macronutrient':          -1,
    'Carbohydrates':          +1,
    'Vitamins and cofactors': +1,
}
if GROUP_PRIOR_MODE == 'full':
    GROUP_PRIOR = _GROUP_PRIOR_FULL
elif GROUP_PRIOR_MODE == 'carbvit':
    GROUP_PRIOR = {k: v for k, v in _GROUP_PRIOR_FULL.items() if v > 0}
else:
    GROUP_PRIOR = {}

_p85 = pd.read_csv(os.path.join(BASE_DIR, 'analyse/paper85_compounds.csv'))
COMPOUND_GROUP = dict(zip(_p85['kegg'], _p85['group']))

ontology_rules = {
    'C02483': ('C02477', 'Vitamin E'), 'C14151': ('C02477', 'Vitamin E'),
    'C14152': ('C02477', 'Vitamin E'), 'C14153': ('C02477', 'Vitamin E'),
    'C14154': ('C02477', 'Vitamin E'), 'C14155': ('C02477', 'Vitamin E'),
    'C14156': ('C02477', 'Vitamin E'),
    'C00440': ('C00504', 'Folate'), 'C03479': ('C00504', 'Folate'),
    # Sugar 그룹은 아래에서 논문 Carbohydrates 그룹으로부터 유도한다.
    # (수작업 목록에는 Maltose/Fructose/Lactose/Galactose만 있고 가장 기본인
    #  D-Glucose가 빠져 있었다. 손으로 한 종을 끼워넣는 대신 그룹에서 만든다.)
    'C05776': ('C00253', 'B-vitamin'),
    'C02094': ('C00473', 'Carotenoid'), 'C05433': ('C00473', 'Carotenoid'),
    'C05432': ('C00473', 'Carotenoid'), 'C08591': ('C00473', 'Carotenoid'),
    'C06098': ('C00473', 'Carotenoid'), 'C08601': ('C00473', 'Carotenoid'),
    'C20484': ('C00473', 'Carotenoid'), 'C15858': ('C00473', 'Carotenoid'),
    'C15981': ('C00473', 'Carotenoid'), 'C05414': ('C00473', 'Carotenoid'),
    'C05421': ('C00473', 'Carotenoid'),
    'C05441': ('C05443', 'Vitamin D'), 'C05443': ('C05443', 'Vitamin D'),
}

# Literature rules
# 논문 Carbohydrates 그룹(Fig. 4(c)) -> 부모 C00089 Sucrose.
# Sucrose는 MENDA에서 pos에만 속해 방향이 확정되는 유일한 당류다
# (tools/diag_table3_signs.py). 나머지 당류가 이를 상속한다.
for _c, _g in COMPOUND_GROUP.items():
    if _g == 'Carbohydrates' and _c != 'C00089':
        ontology_rules.setdefault(_c, ('C00089', 'Sugar'))

literature_rules = {
    'C00023': +1, 'C00038': +1, 'C00305': +1, 'C01529': +1,
    'C00076': +1, 'C00238': +1, 'C01330': -1, 'C00473': +1,
    'C05443': +1, 'C02385': +1, 'C07481': -1, 'C01733': +1,
    'C00716': +1,
    'C00034': 0, 'C00070': 0, 'C00087': 0, 'C00150': 0, 'C00175': 0,
    'C00291': 0, 'C06262': 0, 'C06266': 0, 'C00742': 0, 'C01382': 0,
    'C07480': 0, 'C00369': 0, 'C00828': 0, 'C01628': 0, 'C02059': 0,
    'C01753': 0, 'C01789': 0, 'C05442': 0,
    'C16433': 0, 'C16434': 0, 'C16435': 0, 'C16436': 0,
    'C01401': 0, 'C00736': 0,
}

incidence = {}
source_info = {}

for c in food_kegg:
    ks = kegg_keys(c)   # 논문 ID + alias ID 둘 다 확인
    menda_unresolved = False
    # P1: MENDA direct
    in_pos = bool(set(ks) & menda_pos)
    in_neg = bool(set(ks) & menda_neg)
    if in_pos or in_neg:
        # ★ MENDA 극성 (tools/diag.py menda_orig 로 확인, 2026-09-29)
        # KG 의 hasPositiveAssociation 목록 = MENDA 원본의 'Up'(우울증에서 증가)
        # 대사체다. Jaccard 0.981 / 0.982 로 일치한다.
        # 즉 'positive association' 은 논문 §4.2.1 이 말하는 '완화'가 아니라
        # 역학의 통상 의미인 '질병과 양의 상관'이다.
        # Supplementary Query 2 가 hasNegativeAssociation compound 를 뽑는 것도
        # 같은 이야기다 — 우울증에서 '감소한' = 결핍된 = 보충할 가치가 있는 성분.
        #   hasPositiveAssociation (up in depression)   -> E = -1
        #   hasNegativeAssociation (down in depression) -> E = +1
        # 이전에는 이를 반대로 읽어 E 전체가 뒤집혀 있었다.
        _up, _down = (+1, -1) if MENDA_POS_MEANS_RELIEF else (-1, +1)
        if in_pos and not in_neg:
            incidence[c] = _up; source_info[c] = 'MENDA_pos'
        elif in_neg and not in_pos:
            incidence[c] = _down; source_info[c] = 'MENDA_neg'
        else:
            # Both → Query Type 2로 tie-break
            if set(ks) & set(q2_compounds):
                incidence[c] = +1; source_info[c] = 'MENDA_both+Q2_bacteria'
            elif set(ks) & set(mikg_ntm_precursors):
                incidence[c] = +1; source_info[c] = 'MENDA_both+MiKG'
            else:
                # MENDA에 pos/neg가 동시에 있고 Q2·MiKG 근거도 없다 = 방향 미확정.
                # 과거에는 +1을 기본값으로 줬으나, 이는 아미노산 11종을 모두 +1로
                # 만들어 육류를 추천 상위로 밀어올렸다(아미노산 u 기여 2.505 vs
                # 과일·채소·어류 0.005). ProMENDA도 이들에 대해 마진 0.011~0.119로
                # 사실상 50:50이라 방향 근거가 없다.
                # 논문 §4.2.3도 "nonsignificant differences in certain amino acids"
                # 라고 적는다. 근거가 없으면 0으로 둔다.
                # (step4가 ProMENDA 마진 >= MARGIN이면 채운다)
                _od = menda_orig_dir(ks) if _MENDA_ORIG else 0
                if _od:
                    incidence[c] = _od
                    source_info[c] = 'MENDA_both+orig'
                elif MENDA_BOTH_DEFAULT_POS:
                    incidence[c] = +1; source_info[c] = 'MENDA_both→pos'
                else:
                    # 여기서 끊지 않고 P4(ontology) / P5 / P6으로 내려보낸다.
                    # MENDA가 모순된 근거를 주었을 뿐, 다른 소스가 답할 수 있다.
                    # 예: C00031 D-Glucose는 sugar 온톨로지로 부모(Sucrose,
                    # MENDA_pos)에서 +1을 받을 수 있다.
                    menda_unresolved = True
        if not menda_unresolved:
            continue

    # P2: Query Type 2 (bacteria path)
    if set(ks) & set(q2_compounds):
        incidence[c] = +1; source_info[c] = 'Q2_bacteria_path'
        continue

    # P3: MiKG precursor
    if set(ks) & set(mikg_ntm_precursors):
        _k = next(k for k in ks if k in mikg_ntm_precursors)
        ntm, name = mikg_ntm_precursors[_k]
        incidence[c] = +1; source_info[c] = f'MiKG({ntm}→{name})'
        continue

    # P4: Ontology
    if USE_ONTOLOGY and (set(ks) & set(ontology_rules)):
        _k = next(k for k in ks if k in ontology_rules)
        parent_id, parent_name = ontology_rules[_k]
        if parent_id in menda_pos:
            incidence[c] = +1
        elif parent_id in menda_neg:
            incidence[c] = -1
        elif USE_LITERATURE and parent_id in literature_rules:
            incidence[c] = literature_rules[parent_id]
        else:
            incidence[c] = +1
        source_info[c] = f'ontology({parent_name})'
        continue

    # P5: Literature (기본 OFF — 논문 근거 없음)
    if USE_LITERATURE and (set(ks) & set(literature_rules)):
        _k = next(k for k in ks if k in literature_rules)
        incidence[c] = literature_rules[_k]
        source_info[c] = 'literature'
        continue

    # P6: Group prior (논문 §4.2.3)
    if GROUP_PRIOR:
        g = COMPOUND_GROUP.get(c)
        if g in GROUP_PRIOR:
            incidence[c] = GROUP_PRIOR[g]
            source_info[c] = f'group_prior({g})'
            continue

    incidence[c] = 0
    source_info[c] = 'MENDA_both→unresolved' if menda_unresolved else 'unknown'

# ============================================================
# 통계 + 논문 대비 체크
# ============================================================
print(f"\n{'='*70}")
print("[6/7] 결과 통계 + 논문 체크")
print(f"{'='*70}")

assigned = sum(1 for v in incidence.values() if v != 0)
print(f"  Assigned (≠0): {assigned}/{len(food_kegg)}")
print(f"  Positive: {sum(1 for v in incidence.values() if v > 0)}")
print(f"  Negative: {sum(1 for v in incidence.values() if v < 0)}")
print(f"  Neutral:  {sum(1 for v in incidence.values() if v == 0)}")

src_counts = {}
for s in source_info.values():
    key = s.split('(')[0].split('→')[0]
    src_counts[key] = src_counts.get(key, 0) + 1
print(f"\n  Source별:")
for s, cnt in sorted(src_counts.items(), key=lambda x: -x[1]):
    print(f"    {s:30s}: {cnt}")

# 논문 Table 3 검증
print(f"\n  === 논문 Table 3 재현 검증 ===")
table3_check = {
    'C00025': ('+', 'Glutamic acid'),
    'C00037': ('+', 'Glycine'),
    'C00072': ('+', 'Ascorbic acid'),
    'C00188': ('-', 'L-Threonine'),
    'C00114': ('-', 'Choline'),
}
for kegg_id, (paper_dir, name) in table3_check.items():
    our_dir = '+' if incidence.get(kegg_id, 0) > 0 else ('-' if incidence.get(kegg_id, 0) < 0 else '0')
    match = '✅' if our_dir == paper_dir else '❌'
    print(f"    {kegg_id} ({name:15s}): 논문={paper_dir}, 우리={our_dir} {match} [{source_info.get(kegg_id, '?')}]")

# 논문 Table 5 검증 (inferred results)
print(f"\n  === 논문 Table 5 재현 검증 ===")
table5_check = [
    ('Garlic → Alzheimer', 'Threonine (C00188)', 'Diet recommendation'),
    ('Coffee → Parkinson', 'Threonine (C00188)', 'Diet recommendation'),
    ('Lettuce → Anxiety', 'Nicotinic acid (C00253)', 'Diet recommendation'),
    ('Sweets → Depression', 'L-Threonine (C00188)', 'Diet recommendation'),
    ('Onion → Depression', 'Ascorbate (C00072)', 'Diet recommendation'),
]
for question, compound_info, attr in table5_check:
    kegg = compound_info.split('(')[1].rstrip(')')
    our_dir = '+' if incidence.get(kegg, 0) > 0 else ('-' if incidence.get(kegg, 0) < 0 else '0')
    in_q2 = kegg in q2_compounds
    print(f"    {question:30s} {compound_info:25s} inc={our_dir} Q2={in_q2}")

# ============================================================
# weight.csv 생성
# ============================================================
print(f"\n{'='*70}")
print("[7/7] weight.csv 생성")
print(f"{'='*70}")

# infer 행(0, 1)만 쓴다. faecal / type1 / type2 는 step3 가 ProMENDA 부분집합에서
# 독립 집계한다 (kegg_alias.INFER_SCALE 주석 참조).
# 이전 구현은 infer 값을 근거 없는 배율(예: MENDA 1.0/0.8/0.9/1.1)로 네 행에
# 복사해, 네 소스의 부호가 85종 전부 같은 이름만 다른 복사본이었다.
n = len(food_kegg)
W = np.zeros((8, n))
for j, c in enumerate(food_kegg):
    w = kegg_alias.infer_scale(source_info[c])
    W[0, j] = max(incidence[c], 0) * w
    W[1, j] = max(-incidence[c], 0) * w

df_weight = pd.DataFrame(W, columns=food_kegg)
weight_path = os.path.join(BASE_DIR, 'analyse/weight.csv')
df_weight.to_csv(weight_path, index=False)

print(f"  저장: {weight_path}")
print(f"  shape: {df_weight.shape}")
print(f"  non-zero per row: {[(W[i] != 0).sum() for i in range(8)]}")

# 전체 결과 테이블 저장
results_path = os.path.join(BASE_DIR, 'analyse/knowledge_query_results.csv')
df_results = pd.DataFrame([
    {'compound': c, 'name': kegg_names.get(c, '?'), 'incidence': incidence[c],
     'source': source_info[c], 'in_Q2': c in q2_compounds,
     'in_MENDA_pos': c in menda_pos, 'in_MENDA_neg': c in menda_neg}
    for c in food_kegg
])
df_results.to_csv(results_path, index=False)
print(f"  결과 테이블: {results_path}")

print(f"\n✅ Knowledge Query 완료")
print(f"   다음: python3 map_promenda.py → python3 run_recommendation.py")
