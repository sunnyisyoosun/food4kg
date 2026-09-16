"""
Food4healthKG Knowledge Inference
=====================================
모든 KG 소스 통합:
1. MENDA direct (24개)
2. MiKG: bacteria → neurotransmitter → depression → precursor mapping
3. Bacteria inference: KEGG_Compound_Bacteria + Disease_Bacteria
4. Ontology: KEGG_Compound subClassOf 체인
5. Literature: nutritional psychiatry 문헌 기반

실행: python3 knowledge_inference.py
의존: reconstruct_v2.py가 먼저 실행되어 food.csv, foodname.csv 생성되어야 함
"""

import json, re
import pandas as pd
import numpy as np

BASE_DIR = '/home/yoosun/food_recom_w_paper'
MIKG_DIR = '/home/yoosun/food_recom_w_paper/MiKG-JAIMS'

# ============================================================
# Source 1: MENDA direct
# ============================================================
print("[1/5] MENDA direct...")

with open(f'{BASE_DIR}/foodkg_triply/MENDA_Depression.jsonld') as f:
    menda = json.load(f)

menda_pos, menda_neg = set(), set()
for entry in menda:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            for v in (vals if isinstance(vals, list) else [vals]):
                if isinstance(v, dict) and '@id' in v:
                    cid = v['@id'].split('/')[-1]
                    if cid.startswith('C'):
                        if 'Positive' in key: menda_pos.add(cid)
                        elif 'Negative' in key: menda_neg.add(cid)

print(f"  pos={len(menda_pos)}, neg={len(menda_neg)}")

# ============================================================
# Source 2: MiKG neurotransmitter → precursor chain
# ============================================================
print("[2/5] MiKG neurotransmitter-precursor inference...")

with open(f'{MIKG_DIR}/MiKG_Schema_Data_20201007.ttl') as f:
    mikg_content = f.read()

# Depression과 연결된 neurotransmitter
dep_ntm = re.findall(
    r'hasNeurotransmitter\s+mikg:(\S+)\s*;\s*\n\s*mikg:hasMentalDisorder\s+mikg:Depressive-disorder',
    mikg_content
)
print(f"  Depression neurotransmitters: {dep_ntm}")

# Neurotransmitter → bacteria
ntm_bacteria = {}
blocks = mikg_content.split('\nmikg:')
for block in blocks:
    if 'hasGutMicrobiota' in block and 'hasNeurotransmitter' in block:
        bacts = re.findall(r'hasGutMicrobiota\s+mikg:(\S+)', block)
        ntms = re.findall(r'hasNeurotransmitter\s+mikg:(\S+)', block)
        for n in ntms:
            for b in bacts:
                ntm_bacteria.setdefault(n, set()).add(b.replace('-', ' '))

dep_bacteria_mikg = set()
for ntm in dep_ntm:
    dep_bacteria_mikg.update(ntm_bacteria.get(ntm, set()))
print(f"  Depression bacteria (via NTM): {len(dep_bacteria_mikg)}")

# Neurotransmitter → KEGG + precursor mapping
# 핵심: 음식에 있는 건 neurotransmitter 자체가 아니라 그 precursor
ntm_precursor_map = {
    # neurotransmitter: [(precursor_kegg, precursor_name, direction), ...]
    'Serotonin': [
        ('C00806', 'Tryptophan', +1),       # TRP → 5-HTP → Serotonin
        ('C00643', 'Vitamin B-6', +1),       # cofactor (not in our 88, skip)
    ],
    'Dopamine': [
        ('C01536', 'Tyrosine', +1),          # Tyr → L-DOPA → Dopamine
        ('C02057', 'Phenylalanine', +1),     # Phe → Tyr → Dopamine
    ],
    'Norepinephrine': [
        ('C01536', 'Tyrosine', +1),          # Tyr → Dopamine → NE
        ('C00072', 'Vitamin C', +1),         # cofactor for DBH enzyme
    ],
    'GABA': [
        ('C00025', 'Glutamic acid', +1),     # Glu → GABA (via GAD)
        ('C05776', 'Vitamin B-12', +1),      # cofactor
    ],
    'Histamine': [
        ('C00768', 'Histidine', +1),         # His → Histamine (via HDC)
    ],
    'Acetylcholine': [
        ('C00114', 'Choline', +1),           # Choline → ACh (via ChAT)
        ('C00588', 'Phosphocholine', +1),    # phospholipid source
        ('C00670', 'Glycerophosphocholine', +1),
    ],
}

mikg_precursor_incidence = {}
for ntm in dep_ntm:
    if ntm in ntm_precursor_map:
        for kegg_id, name, direction in ntm_precursor_map[ntm]:
            if kegg_id not in mikg_precursor_incidence:
                mikg_precursor_incidence[kegg_id] = direction
                print(f"  {ntm} → precursor {kegg_id} ({name}) = {'+' if direction > 0 else '-'}")

# ============================================================
# Source 3: Bacteria inference (CB + DB + MiKG)
# ============================================================
print("\n[3/5] Bacteria compound inference...")

# CB: bacteria → compounds
with open(f'{BASE_DIR}/foodkg_triply/KEGG_Compound_Bacteria.jsonld') as f:
    cb = json.load(f)
cb_bact_compounds = {}
for entry in cb:
    for node in entry.get('@graph', []):
        bid = node.get('@id', '')
        for key, vals in node.items():
            if 'hasMetabolites' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        cb_bact_compounds.setdefault(bid, set()).add(v['@id'].split('/')[-1])

# Bacteria_Ontology: entity ID → name
bact_name_to_id = {}
with open(f'{BASE_DIR}/foodkg_triply/Bacteria_Ontology.trig') as f:
    for line in f:
        if 'label' in line:
            id_m = re.search(r'<(http://nlp_microbe[^>]+)>', line)
            label_m = re.search(r'"([^"]+)"', line)
            if id_m and label_m:
                bact_name_to_id[label_m.group(1).lower()] = id_m.group(1)

# MiKG depression bacteria → CB entity ID 매칭 (name + genus)
matched_cb_ids = set()
for bname in dep_bacteria_mikg:
    bname_l = bname.lower()
    if bname_l in bact_name_to_id:
        eid = bact_name_to_id[bname_l]
        if eid in cb_bact_compounds:
            matched_cb_ids.add(eid)
    else:
        genus = bname_l.split()[0]
        for name, eid in bact_name_to_id.items():
            if name.startswith(genus) and eid in cb_bact_compounds:
                matched_cb_ids.add(eid)
                break

bacteria_compounds = set()
for bid in matched_cb_ids:
    bacteria_compounds.update(cb_bact_compounds.get(bid, set()))

print(f"  MiKG bacteria matched to CB: {len(matched_cb_ids)}")
print(f"  Compounds via bacteria: {len(bacteria_compounds)}")

# ============================================================
# Source 4: Ontology inference (subClassOf)
# ============================================================
print("\n[4/5] Ontology inference...")

ontology_rules = {
    # child → parent (parent의 incidence 상속)
    # Vitamin E family
    'C02483': ('C02477', 'Vitamin E'),
    'C14151': ('C02477', 'Vitamin E'),
    'C14152': ('C02477', 'Vitamin E'),
    'C14153': ('C02477', 'Vitamin E'),
    'C14154': ('C02477', 'Vitamin E'),
    'C14155': ('C02477', 'Vitamin E'),
    'C14156': ('C02477', 'Vitamin E'),
    # Folate family
    'C00440': ('C00504', 'Folate'),
    'C03479': ('C00504', 'Folate'),
    # Sugar family
    'C01496': ('C00089', 'Sucrose/Sugar'),
    'C00208': ('C00089', 'Sucrose/Sugar'),
    'C00243': ('C00089', 'Sucrose/Sugar'),
    'C01582': ('C00089', 'Sucrose/Sugar'),
    # Vitamin B-12 (cobalamin family)
    'C05776': ('C00253', 'B-vitamin'),
    # Carotenoid → Vitamin A
    'C02094': ('C00473', 'Vitamin A/Carotenoid'),
    'C05433': ('C00473', 'Vitamin A/Carotenoid'),
    'C08591': ('C00473', 'Vitamin A/Carotenoid'),
    'C06098': ('C00473', 'Vitamin A/Carotenoid'),
    'C08601': ('C00473', 'Vitamin A/Carotenoid'),
    'C05432': ('C00473', 'Vitamin A/Carotenoid'),
    'C20484': ('C00473', 'Vitamin A/Carotenoid'),
    'C15858': ('C00473', 'Vitamin A/Carotenoid'),
    'C15981': ('C00473', 'Vitamin A/Carotenoid'),
    'C05414': ('C00473', 'Vitamin A/Carotenoid'),
    'C05421': ('C00473', 'Vitamin A/Carotenoid'),
    # Vitamin D family
    'C05441': ('C05443', 'Vitamin D'),
    'C05443': ('C05443', 'Vitamin D'),
}

# ============================================================
# Source 5: Literature inference
# ============================================================
print("[5/5] Literature inference...")

literature_rules = {
    # Minerals — 우울증 연관 확립된 것
    'C00023': (+1, 'Iron — anemia-depression [PMID:22578925]'),
    'C00038': (+1, 'Zinc [PMID:23567517]'),
    'C00305': (+1, 'Magnesium [PMID:28654669]'),
    'C01529': (+1, 'Selenium [PMID:22265347]'),
    'C00076': (+1, 'Calcium [PMID:29099763]'),
    'C00238': (+1, 'Potassium [PMID:28915368]'),
    'C01330': (-1, 'Sodium — high Na diet negative [paper ref 9]'),
    'C00473': (+1, 'Vitamin A [PMID:24179891]'),
    'C05443': (+1, 'Vitamin D3 [PMID:25713056]'),
    'C02385': (+1, 'Arginine — NO pathway [PMID:31189391]'),
    'C07481': (-1, 'Caffeine — anxiety/sleep [PMID:26339067]'),
    # Amino acids (MiKG precursor에서 이미 커버된 것 제외)
    'C01733': (+1, 'Methionine — SAMe pathway [PMID:25077519]'),
    'C00716': (+1, 'Serine — phosphatidylserine [PMID:25609263]'),
    # Neutral — 확실한 근거 없음
    'C00034': (0, 'Manganese — unclear'),
    'C00070': (0, 'Copper — unclear'),
    'C00087': (0, 'Sulfur — neutral'),
    'C00150': (0, 'Molybdenum — neutral'),
    'C00175': (0, 'Cobalt — neutral'),
    'C00291': (0, 'Nickel — neutral'),
    'C06262': (0, 'Phosphorus — neutral'),
    'C06266': (0, 'Boron — neutral'),
    'C00742': (0, 'Fluoride — neutral'),
    'C01382': (0, 'Iodine — indirect via thyroid'),
    'C07480': (0, 'Theobromine — neutral'),
    'C00369': (0, 'Starch — neutral'),
    'C00828': (0, 'Vitamin K MK-4 — neutral'),
    'C01628': (0, 'Vitamin K dihydro — neutral'),
    'C02059': (0, 'Vitamin K phyllo — neutral'),
    'C01753': (0, 'Beta-sitosterol — neutral'),
    'C01789': (0, 'Campesterol — neutral'),
    'C05442': (0, 'Stigmasterol — neutral'),
    # Amino acids — BCAA 등 중립
    'C16433': (0, 'Aspartic acid — neutral'),
    'C16434': (0, 'Isoleucine — BCAA neutral'),
    'C16435': (0, 'Proline — neutral'),
    'C16436': (0, 'Valine — BCAA neutral'),
    'C01401': (0, 'Alanine — neutral'),
    'C00736': (0, 'Cysteine — neutral'),
}

# ============================================================
# 통합: 우선순위에 따라 incidence 결정
# ============================================================
print("\n" + "=" * 70)
print("Incidence 통합")
print("=" * 70)

df = pd.read_csv(f'{BASE_DIR}/food_nutrient.csv', low_memory=False)
food_kegg = sorted(df[df['nutrient_kegg'].astype(str).str.startswith('C')]['nutrient_kegg'].unique())
kegg_names = df[df['nutrient_kegg'].astype(str).str.startswith('C')][
    ['nutrient_name', 'nutrient_kegg']
].drop_duplicates().groupby('nutrient_kegg')['nutrient_name'].apply(lambda x: x.iloc[0]).to_dict()

incidence = {}
source_info = {}

for c in food_kegg:
    # Priority 1: MENDA direct
    in_pos = c in menda_pos
    in_neg = c in menda_neg
    if in_pos or in_neg:
        if in_pos and not in_neg:
            incidence[c] = +1
            source_info[c] = 'MENDA_pos'
        elif in_neg and not in_pos:
            incidence[c] = -1
            source_info[c] = 'MENDA_neg'
        else:
            # Both → MiKG precursor로 tie-break
            if c in mikg_precursor_incidence:
                incidence[c] = mikg_precursor_incidence[c]
                source_info[c] = 'MENDA_both+MiKG_precursor'
            elif c in bacteria_compounds:
                incidence[c] = +1
                source_info[c] = 'MENDA_both+bacteria'
            else:
                incidence[c] = +1  # default positive (논문 Table 3: (+)가 다수)
                source_info[c] = 'MENDA_both→pos'
        continue

    # Priority 2: MiKG neurotransmitter precursor
    if c in mikg_precursor_incidence:
        incidence[c] = mikg_precursor_incidence[c]
        source_info[c] = 'MiKG_precursor'
        continue

    # Priority 3: Bacteria compound inference
    if c in bacteria_compounds:
        incidence[c] = +1
        source_info[c] = 'bacteria_compound'
        continue

    # Priority 4: Ontology (parent incidence 상속)
    if c in ontology_rules:
        parent_id, parent_name = ontology_rules[c]
        # parent의 incidence 계산
        p_pos = parent_id in menda_pos
        p_neg = parent_id in menda_neg
        p_mikg = mikg_precursor_incidence.get(parent_id, None)
        p_lit = literature_rules.get(parent_id, (None,))[0]

        if p_pos and not p_neg:
            incidence[c] = +1
        elif p_neg and not p_pos:
            incidence[c] = -1
        elif p_mikg is not None:
            incidence[c] = p_mikg
        elif p_lit is not None:
            incidence[c] = p_lit
        else:
            incidence[c] = +1  # default for ontology inheritance
        source_info[c] = f'ontology({parent_name})'
        continue

    # Priority 5: Literature
    if c in literature_rules:
        val, desc = literature_rules[c]
        incidence[c] = val
        source_info[c] = f'literature'
        continue

    # Default
    incidence[c] = 0
    source_info[c] = 'unknown'

# ============================================================
# 결과 출력
# ============================================================
assigned = sum(1 for v in incidence.values() if v != 0)
pos_count = sum(1 for v in incidence.values() if v > 0)
neg_count = sum(1 for v in incidence.values() if v < 0)
zero_count = sum(1 for v in incidence.values() if v == 0)

print(f"\n  Total assigned (≠0): {assigned}/88 (논문: ~85)")
print(f"  Positive: {pos_count}")
print(f"  Negative: {neg_count}")
print(f"  Neutral:  {zero_count}")

# Source 분포
src_counts = {}
for s in source_info.values():
    key = s.split('(')[0]
    src_counts[key] = src_counts.get(key, 0) + 1
print(f"\n  Source별:")
for s, cnt in sorted(src_counts.items(), key=lambda x: -x[1]):
    print(f"    {s:30s}: {cnt}")

print(f"\n{'KEGG':>8} | {'Inc':>4} | {'Source':>30} | Nutrient")
print("-" * 95)
for c in food_kegg:
    marker = '★' if incidence[c] != 0 else ' '
    print(f"{c:>8} | {incidence[c]:>+4d} | {source_info[c]:>30} | {kegg_names.get(c, '?')} {marker}")

# ============================================================
# weight.csv 재생성
# ============================================================
print(f"\n{'='*70}")
print("weight.csv 생성")
print("=" * 70)

n = len(food_kegg)
W = np.zeros((8, n))

for j, c in enumerate(food_kegg):
    inc = incidence[c]
    pos_val = max(inc, 0)
    neg_val = max(-inc, 0)

    # Source별 차등 가중치
    src = source_info[c]
    if 'MENDA' in src:
        w_infer, w_fecal, w_t1, w_t2 = 1.0, 0.8, 0.9, 1.1
    elif 'MiKG' in src:
        w_infer, w_fecal, w_t1, w_t2 = 0.9, 1.2, 0.7, 1.0
    elif 'bacteria' in src:
        w_infer, w_fecal, w_t1, w_t2 = 0.7, 1.3, 0.8, 0.9
    elif 'ontology' in src:
        w_infer, w_fecal, w_t1, w_t2 = 0.8, 0.8, 0.9, 1.0
    elif 'literature' in src:
        w_infer, w_fecal, w_t1, w_t2 = 1.0, 0.6, 1.0, 1.0
    else:
        w_infer, w_fecal, w_t1, w_t2 = 0, 0, 0, 0

    W[0, j] = pos_val * w_infer
    W[1, j] = neg_val * w_infer
    W[2, j] = pos_val * w_fecal
    W[3, j] = neg_val * w_fecal
    W[4, j] = pos_val * w_t1
    W[5, j] = neg_val * w_t1
    W[6, j] = pos_val * w_t2
    W[7, j] = neg_val * w_t2

df_weight = pd.DataFrame(W, columns=food_kegg)
out_path = f'{BASE_DIR}/analyse/weight.csv'
df_weight.to_csv(out_path, index=False)
print(f"  저장: {out_path}")
print(f"  shape: {df_weight.shape}")
print(f"  non-zero per row: {[(W[i] != 0).sum() for i in range(8)]}")

print(f"\n✅ Knowledge inference v3 완료")
print(f"   다음: python3 run_recommendation.py")
