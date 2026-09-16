"""
ProMENDA → Food Compound 매핑
==============================
1. ProMENDA metabolite dataset (xlsx) 다운로드:
   https://menda.cqmu.edu.cn/data/MENDA_metabolite_dataset_20230910.xlsx

2. 이 스크립트를 Food4healthKG 디렉토리에서 실행:
   python3 map_promenda.py

3. 결과: weight.csv 업데이트 (incidence 확장)

의존: add_fatty_acid_kegg.py → reconstruct_v2.py 가 먼저 실행되어
       food_nutrient.csv (134 compounds), food.csv, foodname.csv 생성되어야 함
"""

import pandas as pd
import numpy as np
import json
import re
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMENDA_FILE = os.path.join(BASE_DIR, '41398_2024_2948_MOESM3_ESM.xlsx')

if not os.path.exists(PROMENDA_FILE):
    print(f"❌ ProMENDA 파일이 없습니다.")
    print(f"   다운로드: https://menda.cqmu.edu.cn/data/MENDA_metabolite_dataset_20230910.xlsx")
    print(f"   저장 위치: {PROMENDA_FILE}")
    sys.exit(1)

# ============================================================
# 1. ProMENDA 로드
# ============================================================
print("[1/5] ProMENDA 로드...")

# 시트 구조 확인
xl = pd.ExcelFile(PROMENDA_FILE)
print(f"  시트: {xl.sheet_names}")

# metabolite 데이터 로드 (시트 이름이 다를 수 있음)
# 일반적으로 첫 번째 시트 또는 'metabolite' 포함 시트
sheet = None
for s in xl.sheet_names:
    if 'metabolite' in s.lower() or 'meta' in s.lower():
        sheet = s
        break
if sheet is None:
    sheet = xl.sheet_names[0]

df_pm = pd.read_excel(PROMENDA_FILE, sheet_name=sheet)
print(f"  시트: {sheet}")
print(f"  행: {len(df_pm):,}, 열: {len(df_pm.columns)}")
print(f"  컬럼: {df_pm.columns.tolist()}")

# ============================================================
# 2. 컬럼 자동 감지
# ============================================================
print("\n[2/5] 컬럼 감지...")

# ProMENDA 컬럼 이름 패턴 매칭
col_map = {}
for col in df_pm.columns:
    cl = str(col).lower()
    if 'kegg' in cl and 'id' in cl:
        col_map['kegg_id'] = col
    elif 'kegg' in cl and 'id' not in cl:
        col_map.setdefault('kegg_id', col)
    elif 'hmdb' in cl:
        col_map['hmdb'] = col
    elif 'molecule' in cl and 'name' in cl:
        col_map['name'] = col
    elif 'metabolite' in cl and 'name' in cl:
        col_map['name'] = col
    elif 'name' in cl and 'name' not in col_map:
        col_map['name'] = col
    elif 'up/down' in cl or 'regulation' in cl or 'direction' in cl or 'change' in cl:
        col_map['regulation'] = col
    elif 'organism' in cl or 'species' in cl:
        col_map['organism'] = col
    elif 'tissue' in cl or 'sample' in cl or 'specimen' in cl:
        col_map['tissue'] = col

print(f"  감지된 컬럼 매핑:")
for k, v in col_map.items():
    print(f"    {k}: {v}")

# 필수 컬럼 확인
if 'name' not in col_map:
    # 첫 번째 string 컬럼을 name으로
    for col in df_pm.columns:
        if df_pm[col].dtype == 'object':
            col_map['name'] = col
            break

# regulation 컬럼이 없으면 모든 컬럼에서 up/down 패턴 찾기
if 'regulation' not in col_map:
    for col in df_pm.columns:
        vals = df_pm[col].dropna().astype(str).str.lower().unique()
        if any('up' in v or 'down' in v or 'increase' in v or 'decrease' in v for v in vals[:20]):
            col_map['regulation'] = col
            break

print(f"\n  최종 매핑: {col_map}")

# 샘플 데이터
print(f"\n  샘플 (처음 5행):")
display_cols = [v for v in col_map.values() if v in df_pm.columns]
print(df_pm[display_cols].head().to_string())

# ============================================================
# 3. KEGG ID 추출 + regulation 방향 결정
# ============================================================
print("\n[3/5] KEGG compound 추출...")

# KEGG ID가 있는 행만 필터
kegg_col = col_map.get('kegg_id', None)
name_col = col_map.get('name')
reg_col = col_map.get('regulation', None)

if kegg_col:
    df_kegg = df_pm[df_pm[kegg_col].astype(str).str.contains(r'C\d{5}', na=False)].copy()
    df_kegg['kegg_clean'] = df_kegg[kegg_col].astype(str).str.extract(r'(C\d{5})')[0]
else:
    # KEGG ID가 없으면 name으로 매핑해야 함
    print("  ⚠️ KEGG ID 컬럼 없음 — 이름 기반 매핑으로 전환")
    df_kegg = df_pm.copy()
    df_kegg['kegg_clean'] = None

print(f"  KEGG ID 있는 행: {len(df_kegg):,}")
print(f"  Unique KEGG compounds: {df_kegg['kegg_clean'].nunique()}")

# Regulation 방향
# up-regulation in depression = compound가 depression에서 증가 = negative (질병 연관)
# down-regulation in depression = compound가 depression에서 감소 = positive (부족 → 보충 필요)
# 논문 MENDA 규칙:
#   hasPositiveAssociation = compound가 depression 완화 (+1)
#   hasNegativeAssociation = compound가 depression 악화 (-1)
# ProMENDA에서:
#   up in depression → 질병 상태에서 증가 → 악화 관련 → negative (-1)
#   down in depression → 질병 상태에서 감소 → 부족 → 보충 시 완화 → positive (+1)

def parse_regulation(val):
    """ProMENDA regulation → incidence"""
    if pd.isna(val):
        return 0
    val = str(val).lower().strip()
    if val in ['up', 'upregulated', 'up-regulated', 'increased', 'increase', 'higher']:
        return -1  # up in depression = 악화 연관
    elif val in ['down', 'downregulated', 'down-regulated', 'decreased', 'decrease', 'lower']:
        return +1  # down in depression = 보충 시 완화
    else:
        return 0

if reg_col:
    df_kegg['incidence'] = df_kegg[reg_col].apply(parse_regulation)
else:
    df_kegg['incidence'] = 0

print(f"\n  Regulation 분포:")
print(f"    Positive (+1, down in dep): {(df_kegg['incidence'] == 1).sum()}")
print(f"    Negative (-1, up in dep):   {(df_kegg['incidence'] == -1).sum()}")
print(f"    Unknown (0):                {(df_kegg['incidence'] == 0).sum()}")

# ============================================================
# 4. Food compound와 매핑
# ============================================================
print("\n[4/5] Food compound 매핑...")

# 현재 food_nutrient.csv의 134 KEGG compounds
df_fn = pd.read_csv(os.path.join(BASE_DIR, 'food_nutrient.csv'), low_memory=False)
food_kegg = sorted(df_fn[df_fn['nutrient_kegg'].astype(str).str.startswith('C')]['nutrient_kegg'].unique())
kegg_names = df_fn[df_fn['nutrient_kegg'].astype(str).str.startswith('C')][
    ['nutrient_name', 'nutrient_kegg']
].drop_duplicates().groupby('nutrient_kegg')['nutrient_name'].apply(lambda x: x.iloc[0]).to_dict()

print(f"  Food compounds: {len(food_kegg)}")

# ProMENDA에서 compound별 consensus direction 계산
# 여러 study에서 같은 compound가 나올 수 있음 → majority vote
promenda_consensus = {}
if kegg_col:
    for kegg_id, grp in df_kegg.groupby('kegg_clean'):
        if pd.isna(kegg_id):
            continue
        votes = grp['incidence'].value_counts()
        pos = votes.get(1, 0)
        neg = votes.get(-1, 0)
        total = len(grp)
        
        if pos > neg:
            direction = +1
        elif neg > pos:
            direction = -1
        elif pos == neg and pos > 0:
            direction = 0  # tie
        else:
            direction = 0
        
        promenda_consensus[kegg_id] = {
            'direction': direction,
            'pos_count': pos,
            'neg_count': neg,
            'total': total
        }

# Name 기반 매핑 (KEGG ID 없는 compound용)
if name_col:
    name_to_kegg = {}
    for c in food_kegg:
        names = df_fn[df_fn['nutrient_kegg'] == c]['nutrient_name'].unique()
        for n in names:
            name_to_kegg[n.lower().strip()] = c
    
    # ProMENDA name과 food nutrient name 매칭
    for _, row in df_kegg.iterrows():
        if pd.notna(row.get('kegg_clean')) and row['kegg_clean'] in promenda_consensus:
            continue  # 이미 KEGG로 매핑됨
        pm_name = str(row.get(name_col, '')).lower().strip()
        if pm_name in name_to_kegg:
            kid = name_to_kegg[pm_name]
            if kid not in promenda_consensus:
                promenda_consensus[kid] = {
                    'direction': row['incidence'],
                    'pos_count': 1 if row['incidence'] == 1 else 0,
                    'neg_count': 1 if row['incidence'] == -1 else 0,
                    'total': 1
                }

# Food compound와의 overlap
food_kegg_set = set(food_kegg)
overlap = food_kegg_set & set(promenda_consensus.keys())

# 기존 MENDA overlap과 비교
with open(os.path.join(BASE_DIR, 'foodkg_triply/MENDA_Depression.jsonld')) as f:
    menda = json.load(f)
old_menda = set()
for entry in menda:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            if 'Association' in key:
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        cid = v['@id'].split('/')[-1]
                        if cid.startswith('C'):
                            old_menda.add(cid)
old_overlap = food_kegg_set & old_menda

new_from_promenda = overlap - old_overlap

print(f"\n  === 매핑 결과 ===")
print(f"  ProMENDA unique compounds:    {len(promenda_consensus)}")
print(f"  Food compound overlap:        {len(overlap)} (기존 MENDA: {len(old_overlap)})")
print(f"  NEW from ProMENDA:            {len(new_from_promenda)}")

print(f"\n  새로 매핑된 compound:")
for c in sorted(new_from_promenda):
    info = promenda_consensus[c]
    d = '+' if info['direction'] > 0 else ('-' if info['direction'] < 0 else '0')
    print(f"    {c} [{d}] (pos:{info['pos_count']}, neg:{info['neg_count']}, total:{info['total']}) → {kegg_names.get(c, '?')}")

print(f"\n  기존 MENDA compound의 ProMENDA 업데이트:")
for c in sorted(old_overlap & overlap):
    info = promenda_consensus[c]
    d = '+' if info['direction'] > 0 else ('-' if info['direction'] < 0 else '0')
    print(f"    {c} [{d}] (pos:{info['pos_count']}, neg:{info['neg_count']}, total:{info['total']}) → {kegg_names.get(c, '?')}")

# ============================================================
# 5. weight.csv 업데이트
# ============================================================
print("\n[5/5] weight.csv 업데이트...")

# 기존 knowledge_inference_v3.py 결과 로드
weight_path = os.path.join(BASE_DIR, 'analyse/weight.csv')
df_weight = pd.read_csv(weight_path)
compounds = df_weight.columns.tolist()

# ProMENDA consensus로 incidence 업데이트
updated = 0
for j, c in enumerate(compounds):
    if c in promenda_consensus:
        info = promenda_consensus[c]
        if info['direction'] != 0 and info['total'] >= 2:
            # 2개 이상 study에서 확인된 것만 반영
            inc = info['direction']
            pos_val = max(inc, 0)
            neg_val = max(-inc, 0)
            
            # ProMENDA 가중치 (study 수 기반)
            confidence = min(info['total'] / 10, 1.0)  # 10 studies면 max
            
            # 기존 weight가 0이면 ProMENDA로 채움
            if df_weight.iloc[0, j] == 0 and df_weight.iloc[1, j] == 0:
                df_weight.iloc[0, j] = pos_val * confidence       # infer pos
                df_weight.iloc[1, j] = neg_val * confidence       # infer neg
                df_weight.iloc[2, j] = pos_val * confidence * 0.8 # fecal pos
                df_weight.iloc[3, j] = neg_val * confidence * 0.8 # fecal neg
                df_weight.iloc[4, j] = pos_val * confidence * 0.9 # type1 pos
                df_weight.iloc[5, j] = neg_val * confidence * 0.9 # type1 neg
                df_weight.iloc[6, j] = pos_val * confidence * 1.1 # type2 pos
                df_weight.iloc[7, j] = neg_val * confidence * 1.1 # type2 neg
                updated += 1

df_weight.to_csv(weight_path, index=False)
print(f"  업데이트된 compound: {updated}")
print(f"  저장: {weight_path}")

# 최종 통계
assigned = sum(1 for j in range(len(compounds)) 
               if df_weight.iloc[0, j] != 0 or df_weight.iloc[1, j] != 0)
print(f"\n{'='*60}")
print(f"✅ ProMENDA 매핑 완료")
print(f"{'='*60}")
print(f"  Food compounds:           {len(compounds)}")
print(f"  Incidence assigned (≠0):  {assigned}/{len(compounds)}")
print(f"  기존 MENDA overlap:       {len(old_overlap)}")
print(f"  ProMENDA overlap:         {len(overlap)}")
print(f"  New compounds added:      {updated}")
print(f"\n  다음: python3 run_recommendation.py")
