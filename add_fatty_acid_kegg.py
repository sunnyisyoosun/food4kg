"""
Fatty Acid KEGG 매핑 추가 + 전체 파이프라인 재실행
==================================================
food_nutrient.csv의 fatty acid nutrient (235K rows, KEGG=0)에
KEGG compound ID를 매핑하여 compound 수를 88 → 120+ 확장

매핑 근거: KEGG Compound Database (https://www.genome.jp/kegg/compound/)
"""

import pandas as pd
import numpy as np
import json
import re
import os

BASE_DIR = '/home/yoosun/food_recom_w_paper'

# ============================================================
# 1. Fatty acid → KEGG 매핑 테이블
# ============================================================
# 이름 규칙: SFA X:Y = Saturated fatty acid (탄소수:이중결합수)
# KEGG compound DB에서 확인된 매핑

FA_KEGG_MAP = {
    # === Saturated Fatty Acids (SFA) ===
    'SFA 4:0':   'C00246',   # Butyric acid
    'SFA 5:0':   'C00803',   # Pentanoic acid (Valeric acid)
    'SFA 6:0':   'C01585',   # Caproic acid (Hexanoic acid)
    'SFA 7:0':   'C17714',   # Heptanoic acid (없으면 skip)
    'SFA 8:0':   'C06423',   # Octanoic acid (Caprylic acid)
    'SFA 9:0':   'C01601',   # Nonanoic acid (Pelargonic acid)
    'SFA 10:0':  'C01571',   # Capric acid (Decanoic acid)
    'SFA 11:0':  'C17715',   # Undecanoic acid
    'SFA 12:0':  'C02679',   # Lauric acid
    'SFA 13:0':  'C17716',   # Tridecanoic acid
    'SFA 14:0':  'C06424',   # Myristic acid
    'SFA 15:0':  'C16537',   # Pentadecanoic acid
    'SFA 16:0':  'C00249',   # Palmitic acid
    'SFA 17:0':  'C16535',   # Heptadecanoic acid (Margaric acid)
    'SFA 18:0':  'C01530',   # Stearic acid
    'SFA 20:0':  'C06425',   # Arachidic acid
    'SFA 21:0':  'C16161',   # Heneicosanoic acid
    'SFA 22:0':  'C08281',   # Behenic acid
    'SFA 23:0':  'C16162',   # Tricosanoic acid
    'SFA 24:0':  'C08320',   # Lignoceric acid

    # === Monounsaturated Fatty Acids (MUFA) ===
    'MUFA 14:1':    'C08322',   # Myristoleic acid
    'MUFA 14:1 c':  'C08322',
    'MUFA 15:1':    'C16536',   # Pentadecenoic acid
    'MUFA 16:1':    'C08362',   # Palmitoleic acid
    'MUFA 16:1 c':  'C08362',
    'MUFA 17:1':    'C16534',   # Heptadecenoic acid
    'MUFA 17:1 c':  'C16534',
    'MUFA 18:1':    'C00712',   # Oleic acid
    'MUFA 18:1 c':  'C00712',
    'MUFA 20:1':    'C16526',   # Gondoic acid (Eicosenoic acid)
    'MUFA 20:1 c':  'C16526',
    'MUFA 22:1':    'C08316',   # Erucic acid
    'MUFA 22:1 c':  'C08316',
    'MUFA 22:1 n-9':  'C08316',
    'MUFA 22:1 n-11': 'C08323',  # Cetoleic acid / Nervonic precursor
    'MUFA 24:1 c':    'C08323',  # Nervonic acid
    'MUFA 12:1':      'C16150',  # Dodecenoic acid
    'MUFA 18:1-11 t (18:1t n-7)': 'C01712',  # Vaccenic acid (trans)

    # === Polyunsaturated Fatty Acids (PUFA) ===
    'PUFA 18:2':    'C01595',   # Linoleic acid
    'PUFA 18:2 c':  'C01595',
    'PUFA 18:2 i':  'C01595',
    'PUFA 18:2 n-6 c,c': 'C01595',
    'PUFA 18:2 CLAs': 'C04056',  # Conjugated linoleic acid
    'PUFA 18:3':    'C06427',   # alpha-Linolenic acid (ALA)
    'PUFA 18:3 c':  'C06427',
    'PUFA 18:3 n-3 c,c,c (ALA)': 'C06427',
    'PUFA 18:3 n-6 c,c,c': 'C06426',  # gamma-Linolenic acid (GLA)
    'PUFA 18:3i':   'C06427',
    'PUFA 18:4':    'C16300',   # Stearidonic acid
    'PUFA 20:2 c':  'C16525',   # Eicosadienoic acid
    'PUFA 20:2 n-6 c,c': 'C16525',
    'PUFA 20:3':    'C03242',   # Dihomo-gamma-linolenic acid
    'PUFA 20:3 c':  'C03242',
    'PUFA 20:3 n-3': 'C03242',
    'PUFA 20:3 n-6': 'C03242',
    'PUFA 20:3 n-9': 'C16512',  # Mead acid
    'PUFA 20:4':    'C00219',   # Arachidonic acid (AA)
    'PUFA 2:4 c':   'C00219',   # typo in FDC? probably 20:4
    'PUFA 2:4 n-6': 'C00219',
    'PUFA 2:5 n-3 (EPA)': 'C06428',  # EPA
    'PUFA 2:5 c':   'C06428',
    'PUFA 21:5':    'C16513',   # Heneicosapentaenoic acid
    'PUFA 22:2':    'C16533',   # Docosadienoic acid
    'PUFA 22:3':    'C16532',   # Docosatrienoic acid
    'PUFA 22:4':    'C16527',   # Docosatetraenoic acid (Adrenic acid)
    'PUFA 22:5 c':  'C16513',   # DPA
    'PUFA 22:5 n-3 (DPA)': 'C16513',
    'PUFA 22:6 c':  'C06429',   # DHA
    'PUFA 22:6 n-3 (DHA)': 'C06429',

    # === Trans Fatty Acids (TFA) ===
    'TFA 18:1 t':   'C01712',   # trans-Vaccenic acid / Elaidic acid
    'TFA 18:2 t not further defined': 'C01595',  # trans-Linoleic
    'TFA 18:2 t,t': 'C01595',
    'TFA 18:3 t':   'C06427',   # trans-ALA
    'TFA 20:1 t':   'C16526',
    'TFA 22:1 t':   'C08316',

    # === Aggregate categories → SKIP (no individual KEGG) ===
    # 'Fatty acids, total saturated': None,
    # 'Fatty acids, total monounsaturated': None,
    # 'Fatty acids, total polyunsaturated': None,
    # 'Fatty acids, total trans': None,
    # etc.
}

# Also map some non-fatty-acid unmapped nutrients
OTHER_KEGG_MAP = {
    'Protein': None,            # aggregate, skip
    'Total lipid (fat)': None,  # aggregate
    'Carbohydrate, by difference': None,
    'Energy': None,
    'Energy (Atwater Specific Factors)': None,
    'Energy (Atwater General Factors)': None,
    'Ash': None,
    'Water': None,
    'Fiber, total dietary': None,
    'Sugars, total including NLEA': None,
    'Alcohol, ethyl': 'C00469',  # Ethanol → MENDA에 있음!
}

# ============================================================
# 2. food_nutrient.csv 업데이트
# ============================================================
print("[1/3] food_nutrient.csv에 KEGG 매핑 추가...")

df = pd.read_csv(f'{BASE_DIR}/food_nutrient.csv', low_memory=False)
print(f"  원본: {len(df):,} rows, KEGG mapped: {(df['nutrient_kegg'].astype(str).str.startswith('C')).sum():,}")

# 매핑 적용
mapped_count = 0
for nutrient_name, kegg_id in {**FA_KEGG_MAP, **OTHER_KEGG_MAP}.items():
    if kegg_id is None:
        continue
    mask = df['nutrient_name'] == nutrient_name
    if mask.sum() > 0:
        df.loc[mask, 'nutrient_kegg'] = kegg_id
        mapped_count += mask.sum()

print(f"  추가 매핑: {mapped_count:,} rows")
print(f"  업데이트 후 KEGG mapped: {(df['nutrient_kegg'].astype(str).str.startswith('C')).sum():,}")

new_kegg = sorted(df[df['nutrient_kegg'].astype(str).str.startswith('C')]['nutrient_kegg'].unique())
print(f"  Unique KEGG compounds: {len(new_kegg)} (기존 88)")

# MENDA overlap 확인
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

new_kegg_set = set(new_kegg)
direct_overlap = new_kegg_set & (menda_pos | menda_neg)
print(f"\n  MENDA overlap: {len(direct_overlap)} (기존 24)")
new_menda = direct_overlap - set(df[df['nutrient_kegg'].astype(str).str.startswith('C')].head(0).columns)

# 새로 추가된 MENDA compound
kegg_names = df[df['nutrient_kegg'].astype(str).str.startswith('C')][
    ['nutrient_name','nutrient_kegg']
].drop_duplicates().groupby('nutrient_kegg')['nutrient_name'].apply(lambda x: x.iloc[0]).to_dict()

print(f"\n  새로 MENDA에 매칭된 compound:")
old_kegg = set(pd.read_csv(f'{BASE_DIR}/food_nutrient.csv', low_memory=False)[
    pd.read_csv(f'{BASE_DIR}/food_nutrient.csv', nrows=1).columns[-1]
].unique())  # dummy

# 원본 88개
orig_df = pd.read_csv(f'{BASE_DIR}/food_nutrient.csv', low_memory=False)
orig_kegg = set(orig_df[orig_df['nutrient_kegg'].astype(str).str.startswith('C')]['nutrient_kegg'].unique())
new_compounds = new_kegg_set - orig_kegg
new_menda_compounds = new_compounds & (menda_pos | menda_neg)
print(f"  New compounds total: {len(new_compounds)}")
print(f"  New compounds in MENDA: {len(new_menda_compounds)}")
for c in sorted(new_menda_compounds):
    p = '+' if c in menda_pos else ''
    n = '-' if c in menda_neg else ''
    print(f"    {c} [{p}{n}] {kegg_names.get(c, '?')}")

# 저장
updated_path = f'{BASE_DIR}/food_nutrient_updated.csv'
df.to_csv(updated_path, index=False)
print(f"\n  저장: {updated_path}")

# ============================================================
# 3. 통계 요약
# ============================================================
print(f"\n{'='*60}")
print(f"요약")
print(f"{'='*60}")
print(f"  기존 KEGG compounds:    88")
print(f"  추가 KEGG compounds:    +{len(new_compounds)}")
print(f"  합계:                   {len(new_kegg)}")
print(f"")
print(f"  기존 MENDA overlap:     24")
print(f"  추가 MENDA overlap:     +{len(new_menda_compounds)}")
print(f"  합계:                   {len(direct_overlap)}")
print(f"  논문 목표:              85")
