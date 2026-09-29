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
import kegg_alias
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

# ------------------------------------------------------------------
# Study type 별 up/down 의미 보정
# ------------------------------------------------------------------
# ProMENDA 의 M_Study_type_Metabolite_level 은 비교 설계를 구분한다
# (tools/diag.py promenda_types 로 M_Groups 에서 역추론).
#
#   Type1  "depression vs control", "CUMS vs control"   14,370행
#          -> up = 우울증에서 증가 = 악화 연관 (-1). 위 해석이 맞다.
#   Type2  "CUMS + fluoxetine vs CUMS", "post-ketamine vs baseline"  6,169행
#          -> up = 치료로 증가 = 회복 연관 (+1). 의미가 반대다.
#   Type3  "rTMS vs control" (대상이 Healthy individuals 100%)  1,717행
#          -> 건강인 대상 개입. 우울증 방향과 직접 대응하지 않아 제외.
#   Type4  "responder vs non-responder"  239행
#          -> up = 반응자에서 증가 = 유익 (+1). 반대다.
#   Type5  24행. 표본이 작아 제외.
#
# 기존 코드는 모든 Type 에 같은 해석을 적용해 Type1 과 Type2 를 부호가
# 뒤섞인 채로 합산했다. 여기서 보정한다.
STYPE_COL = 'M_Study_type_Metabolite_level'
STYPE_SIGN = {'Type1': +1, 'Type2': -1, 'Type3': 0, 'Type4': -1, 'Type5': 0}
# 기본값 0. 보정이 의미론적으로는 옳지만 실측이 엇갈린다.
#   보정 OFF  Spearman -0.303  Top30 6/30  gold 7/9
#   보정 ON   Spearman -0.190  Top30 3/30  gold 6/9
# gold 와 Top30 이 OFF 를 지지한다. 특히 C06424 tetradecanoic acid 가
# 보정 시 - -> + 로 뒤집히는데, 논문 §4.2.3 이 PMID 20524151 과 함께
# 소시지의 악화 성분으로 명시한 것이다.
# 즉 논문의 근거 데이터는 보정하지 않은 혼합 집계처럼 거동한다.
# 진단·비교용으로 FIX_STUDY_TYPE=1 로 켤 수 있다 (tools/ab.py study_type).
FIX_STUDY_TYPE = os.environ.get('FIX_STUDY_TYPE', '0') == '1'

if reg_col:
    df_kegg['incidence'] = df_kegg[reg_col].apply(parse_regulation)
    if FIX_STUDY_TYPE and STYPE_COL in df_kegg.columns:
        mult = df_kegg[STYPE_COL].astype(str).map(STYPE_SIGN).fillna(0)
        before = int((df_kegg['incidence'] != 0).sum())
        df_kegg['incidence'] = df_kegg['incidence'] * mult.astype(int)
        after = int((df_kegg['incidence'] != 0).sum())
        flipped = int((mult == -1).sum())
        dropped = int((mult == 0).sum())
        print(f"  study type 보정: 방향 반전 {flipped:,}행(Type2/4), "
              f"제외 {dropped:,}행(Type3/5), 유효 {before:,} -> {after:,}")
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

# 기존 knowledge_query.py 결과 로드
weight_path = os.path.join(BASE_DIR, 'analyse/weight.csv')
df_weight = pd.read_csv(weight_path)
compounds = df_weight.columns.tolist()

# step3 결과를 권위 있는 기준으로 삼아 weight.csv 를 새로 만든다(멱등성).
_res_path = os.path.join(BASE_DIR, 'analyse/knowledge_query_results.csv')
if os.path.exists(_res_path):
    _res = pd.read_csv(_res_path)
    _step3_inc = dict(zip(_res['compound'], _res['incidence']))
    _step3_src = dict(zip(_res['compound'], _res['source'].astype(str)))
    # infer 행만 step3 결과로 채운다. faecal / type1 / type2 행은 0 으로 두고
    # 아래 5b 에서 각 ProMENDA 부분집합으로 독립 집계한다.
    W0 = np.zeros((8, len(compounds)))
    for _j, _c in enumerate(compounds):
        _inc = _step3_inc.get(_c, 0)
        _w = kegg_alias.infer_scale(_step3_src.get(_c, ''))
        W0[0, _j] = max(_inc, 0) * _w
        W0[1, _j] = max(-_inc, 0) * _w
    df_weight = pd.DataFrame(W0, columns=compounds)
    print(f"  step3 기준으로 초기화 (멱등). "
          f"방향 부여 {int(sum(1 for c in compounds if _step3_inc.get(c, 0) != 0))}종")
else:
    print("  ⚠ knowledge_query_results.csv 없음 — weight.csv 현재 값을 그대로 씁니다")

# step3(knowledge_query.py)가 각 compound의 incidence를 어떤 근거로 정했는지.
# MENDA에 pos/neg가 동시에 등장하는 compound는 방향을 정할 근거가 없어
# step3가 임의로 +1을 부여한다('MENDA_both...'). 이런 자리는 ProMENDA의
# study 카운트(정량 근거)로 덮어쓴다.
#
# 실제 사례: C06424 tetradecanoic acid. 논문 4.2.3/Fig.5는 소시지의 대표
# 성분으로 depression을 악화시킨다(negative)고 명시하는데, step3의
# 'MENDA_both→pos' 기본값이 +1을 주고 있었다. ProMENDA는 pos 13 / neg 19로
# negative를 지지한다.
WEAK_SOURCES = ('MENDA_both',)   # 방향이 근거 없이 정해진 source 접두어

step3_source = _step3_src if os.path.exists(_res_path) else {}

def is_weak(c):
    """step3가 근거 없이 방향을 정한 자리인가."""
    return step3_source.get(c, '').startswith(WEAK_SOURCES)

# ------------------------------------------------------------------
# 멱등성
# 이전에는 weight.csv 의 '현재 값'을 보고 빈 자리만 채웠다. 그래서 설정을
# 바꿔 이 스크립트만 다시 돌리면 앞선 실행이 채운 값이 남아 새 설정이
# 반영되지 않았다(진단 중 실제로 두 번 혼선을 일으켰다).
# 이제는 step3 의 knowledge_query_results.csv 를 기준으로 weight.csv 를
# 매번 새로 만든다. 같은 설정이면 몇 번을 돌려도 결과가 같다.
# ------------------------------------------------------------------

# ============================================================
# 5b. 4개 소스를 ProMENDA 부분집합에서 실제로 구성
# ============================================================
# weight.csv 8행 = 4개 소스 × (pos, neg). 공식 final.py의 이름은
#   infer / faecal / type1 / type2.
# ProMENDA에 이 구분이 실제로 존재한다:
#   M_Tissue_Metabolite_level_1 == 'Faece'          -> faecal
#   M_Study_type_Metabolite_level == 'Type1'/'Type2' -> type1 / type2
# 이전 구현은 소스 2~4를 소스 1에 0.8/0.9/1.1을 곱해 만들었다(근거 없음).
# 여기서는 각 소스를 해당 부분집합에서 독립적으로 집계한다.

# 다수결을 뒤집는 데 요구하는 최소 마진: |pos-neg| / total
# 0.0이면 1표 차이로도 방향이 바뀐다. 실제로 Glycine(59:61, 마진 0.016)이
# 논문 Table 3의 '+'와 반대로 뒤집혔다.
# 값 0.10은 tools/ab.py margin 스윕으로 정했다. 논문 Fig.5/Table 3의
# 방향 확정 compound(독립 정답셋) 정확도가 0.0에서 5/7, 0.05~0.15에서 6/7,
# 0.20 이상에서 다시 5/7. 안정 구간의 중앙값을 취한다.
MARGIN = float(os.environ.get('PROMENDA_MARGIN', '0.10'))

TISSUE_COL = 'M_Tissue_Metabolite_level_1'
STYPE_COL  = 'M_Study_type_Metabolite_level'

def consensus_over(sub):
    """부분집합에서 compound별 방향과 study 수를 집계."""
    out = {}
    if 'kegg_clean' not in sub.columns:
        return out
    for kid, grp in sub.groupby('kegg_clean'):
        if pd.isna(kid):
            continue
        v = grp['incidence'].value_counts()
        pos, neg = int(v.get(1, 0)), int(v.get(-1, 0))
        tot = len(grp)
        # 마진이 부족하면 방향을 정하지 않는다(0) -> 기존 값을 건드리지 않음
        if tot == 0 or abs(pos - neg) / tot < MARGIN:
            d = 0
        else:
            d = 1 if pos > neg else (-1 if neg > pos else 0)
        out[kid] = {'direction': d,
                    'pos_count': pos, 'neg_count': neg, 'total': tot}
    return out

subsets = [('infer',  df_kegg)]
if TISSUE_COL in df_kegg.columns:
    subsets.append(('faecal', df_kegg[df_kegg[TISSUE_COL].astype(str) == 'Faece']))
else:
    subsets.append(('faecal', df_kegg))
    print(f"  ⚠ {TISSUE_COL} 없음 — faecal을 전체로 대체")
for tname in ('Type1', 'Type2'):
    if STYPE_COL in df_kegg.columns:
        subsets.append((tname.lower(), df_kegg[df_kegg[STYPE_COL].astype(str) == tname]))
    else:
        subsets.append((tname.lower(), df_kegg))
        print(f"  ⚠ {STYPE_COL} 없음 — {tname}을 전체로 대체")

source_consensus = {}
print("  소스별 ProMENDA 부분집합:")
for name, sub in subsets:
    cons = consensus_over(sub)
    source_consensus[name] = cons
    hit = len(set(cons) & set(compounds))
    print(f"    {name:7s} rows={len(sub):6,d}  compounds={len(cons):5d}  "
          f"food 85와 겹침={hit}")

# ProMENDA consensus로 weight.csv 갱신
updated = 0
overridden = []
for j, c in enumerate(compounds):
    for s_i, (name, _) in enumerate(subsets):
        cons = source_consensus[name]
        info = next((cons[k] for k in kegg_alias.incidence_keys(c) if k in cons), None)
        if info is None or info['direction'] == 0 or info['total'] < 2:
            continue
        inc = info['direction']
        confidence = min(info['total'] / 10, 1.0)

        row_pos, row_neg = s_i * 2, s_i * 2 + 1
        was_empty = (df_weight.iloc[row_pos, j] == 0 and
                     df_weight.iloc[row_neg, j] == 0)
        weak = is_weak(c)
        if not (was_empty or weak):
            continue

        if s_i == 0 and weak and not was_empty:
            old_dir = '+' if df_weight.iloc[row_pos, j] > 0 else '-'
            new_dir = '+' if inc > 0 else '-'
            if old_dir != new_dir:
                overridden.append((c, kegg_names.get(c, '?'), old_dir, new_dir,
                                   info['pos_count'], info['neg_count']))

        df_weight.iloc[row_pos, j] = max(inc, 0) * confidence
        df_weight.iloc[row_neg, j] = max(-inc, 0) * confidence
        if s_i == 0:
            updated += 1

df_weight.to_csv(weight_path, index=False)
print(f"  업데이트된 compound: {updated}")
if overridden:
    print(f"\n  ★ step3의 근거 없는 기본값을 ProMENDA로 뒤집음 ({len(overridden)}개):")
    for c, nm, od, nd, pc, nc in overridden:
        print(f"      {c} {nm[:34]:34s} {od} -> {nd}  (ProMENDA pos:{pc} neg:{nc})")
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
