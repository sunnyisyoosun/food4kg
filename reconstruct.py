"""
Food4healthKG 재현: 누락된 입력 파일 역설계 (개선)
=====================================================
변경사항:
1. food_nutrient.csv의 88 KEGG compound 전부 사용 (논문 85와 근사)
2. 음식 매칭 개선 (fuzzy + 수동 매핑)
3. 같은 KEGG ID에 여러 nutrient가 매핑될 때 합산
"""

import difflib
import re
import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = '/home/yoosun/food_recom_w_paper'
OUT_DIR = os.path.join(BASE_DIR, 'analyse')

# ============================================================
# 1. MENDA: compound → depression 관계
# ============================================================
print("[1/6] MENDA 파싱...")

with open(os.path.join(BASE_DIR, 'foodkg_triply/MENDA_Depression.jsonld')) as f:
    menda = json.load(f)

pos_kegg, neg_kegg = set(), set()
for entry in menda:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            compounds = [v['@id'].split('/')[-1] for v in vals if isinstance(v, dict) and '@id' in v]
            if 'PositiveAssociation' in key:
                pos_kegg.update(c for c in compounds if c.startswith('C'))
            elif 'NegativeAssociation' in key:
                neg_kegg.update(c for c in compounds if c.startswith('C'))

print(f"  pos={len(pos_kegg)}, neg={len(neg_kegg)}")

# ============================================================
# 2. food_nutrient.csv → food × KEGG pivot
# ============================================================
print("[2/6] food_nutrient.csv 로드 + 라벨 정규화...")

df = pd.read_csv(os.path.join(BASE_DIR, 'food_nutrient.csv'), low_memory=False)
df_kegg = df[df['nutrient_kegg'].astype(str).str.startswith('C')].copy()

# ------------------------------------------------------------------
# 단위 환산 — 논문 §3.1 "The nutrients of the food are quantified in weight,
# enabling effective calculation and comparison."
#
# FDC 원값은 compound 마다 G / MG / UG / IU 로 다르다. 논문 heatmap.xlsx 를
# 역산하면 저자는 전부 g 으로 환산했다: 계수 MG 10^-3.00, UG 10^-6.00,
# IU 10^-6.05 (IU 를 µg 처럼 취급) — tools/paper.py units.
# 환산하지 않으면 논문 heatmap 과의 행 코사인이 0.295, 환산하면 0.981 이다.
#
# 피벗 전에 행 단위로 환산한다. Retinol(C00473)·Vitamin E(C02477)는 한
# compound 에 IU 와 µg/mg 행이 함께 있어, 피벗 후 환산하면 서로 다른 단위가
# 평균된다.
#
# UNIT_MODE=raw 이면 이전 동작(원단위 혼용).
# ------------------------------------------------------------------
UNIT_MODE = os.environ.get('UNIT_MODE', 'grams')
UNIT_TO_G = {'G': 1.0, 'MG': 1e-3, 'UG': 1e-6, 'IU': 1e-6}
_raw_amount = df_kegg['amount'].copy()
if UNIT_MODE == 'grams':
    _f = df_kegg['nutrient_unit'].map(UNIT_TO_G)
    _bad = _f.isna()
    if _bad.any():
        print(f"  ⚠ 환산 불가 단위 {df_kegg.loc[_bad, 'nutrient_unit'].unique()} "
              f"— {int(_bad.sum())}행 원값 유지")
    df_kegg['amount'] = df_kegg['amount'] * _f.fillna(1.0)
    print("  단위: g 환산 (MG 1e-3, UG 1e-6, IU 1e-6)")
else:
    print("  단위: 원단위 혼용 (UNIT_MODE=raw)")

# ------------------------------------------------------------------
# 논문 §3.2 (entity linking):
#   "The preprocessing steps involve splitting the food labels by commas and
#    removing unnecessary words that may follow the first comma... Next,
#    exact matching is employed to merge foods with identical labels."
#
# FDC Foundation Foods는 같은 음식을 영양소군별로 따로 등재한다:
#   "Niacin, American cheese, pasteurized process, KRAFT - NFY090HJK"   (1종)
#   "Fatty Acids, American cheese, pasteurized process, KRAFT - NFY090HKC" (25종)
#   "Choline, American cheese, ... - NFY090HJS"  ...
# 접두사 / 샘플코드 / 지역표기를 떼면 라벨이 같아지고, 병합하면 한 음식의
# 전체 성분 프로파일이 복원된다. (American cheese: 1 -> 59, Tamale: 1 -> 79)
# 병합하지 않으면 85 커버리지 중앙값이 15 수준에 머문다(논문 원본 33).
# ------------------------------------------------------------------
NUTRIENT_PREFIX = (r'^(fatty acids|niacin|tocopherols|sugars|amino acids|'
                   r'cholesterol|pantothenic acid|starch|carotenoids|choline|'
                   r'folate|proximates|minerals|fa|vitamin [a-z0-9\- ]+)\s*[,\-]\s*')

def normalize_label(series):
    return (series.astype(str).str.strip().str.lower()
            .str.replace(NUTRIENT_PREFIX, '', regex=True)          # 영양소군 접두사
            .str.replace(r'\s*-\s*[a-z0-9]{6,12}\s*$', '', regex=True)  # 샘플코드
            .str.replace(r'\s*\([^)]*\)\s*', ' ', regex=True)      # 지역표기
            .str.replace(r'[\s,]+$', '', regex=True)
            .str.replace(r'\s+', ' ', regex=True).str.strip())

# 라벨 병합 on/off (A/B용). off면 항목 이름을 그대로 쓴다.
MERGE_LABELS = os.environ.get('MERGE_LABELS', '1') == '1'
if MERGE_LABELS:
    df_kegg['base'] = normalize_label(df_kegg['food_name'])
else:
    df_kegg['base'] = df_kegg['food_name'].astype(str).str.strip().str.lower()
n_before = df_kegg['food_name'].nunique()
n_after = df_kegg['base'].nunique()
print(f"  라벨 병합: {n_before:,}개 항목 -> {n_after:,}개 음식")

# 병합 전 미리 커버리지를 구해 둔다(피벗 없이 계산 — 전체 피벗은 너무 크다)
_cov_series = df_kegg.groupby('base')['nutrient_kegg'].nunique()
_fdc_of_base = df_kegg.groupby('base')['fdc_id'].first()
_name_of_base = df_kegg.groupby('base')['food_name'].first()
available_kegg = sorted(df_kegg['nutrient_kegg'].unique())
print(f"  KEGG compound (사용 가능): {len(available_kegg)}")

# ============================================================
# 2b. 논문 85 compound로 필터 (heatmap.xlsx에서 추출)
# ============================================================
print("[2b/6] 논문 85 compound 필터...")

paper85 = pd.read_csv(os.path.join(OUT_DIR, 'paper85_compounds.csv'))

# 논문과 우리 데이터가 같은 물질에 다른 KEGG ID를 쓰는 경우.
# 논문 KEGG ID -> food_nutrient.csv의 KEGG ID
KEGG_ALIAS = {
    'C02823': 'C05776',  # Vitamin B12        <- 'Vitamin B-12'
    'C16522': 'C03242',  # Eicosatrienoic acid <- 'PUFA 20:3'
    # 'C08319' (alpha-Licanic acid): FDC nutrient 대응 미확인 → 0으로 채움
}

available = set(available_kegg)
all_kegg_cols = []   # 논문 순서(orig_idx)를 따르는 85개 열 이름
col_source = {}      # 논문 KEGG -> 실제로 값을 가져올 열 (없으면 None)

for _, r in paper85.iterrows():
    pk = r['kegg']
    src = pk if pk in available else KEGG_ALIAS.get(pk)
    if src is not None and src not in available:
        src = None
    all_kegg_cols.append(pk)
    col_source[pk] = src

resolved = [k for k, v in col_source.items() if v is not None]
aliased  = [k for k, v in col_source.items() if v is not None and v != k]
missing  = [k for k, v in col_source.items() if v is None]

print(f"  논문 85 중 매칭: {len(resolved)}/85")
print(f"  alias 적용: {len(aliased)} -> " +
      ", ".join(f"{k}->{col_source[k]}" for k in aliased))
if missing:
    names = dict(zip(paper85['kegg'], paper85['name']))
    print(f"  미해결 (0으로 채움): {[(k, names[k]) for k in missing]}")
print(f"  제외된 우리 쪽 compound: {len(available - set(col_source.values()))}")

# ============================================================
# 3. 135개 음식 매칭 (개선)
# ============================================================
print("[3/6] 135 foods 매칭...")

with open(os.path.join(BASE_DIR, 'analyse/p5_foodname.txt')) as f:
    p5_names = [l.strip() for l in f if l.strip()]

# 수동 매핑 (fuzzy match 실패하는 항목)
manual_map = {
    'Onions, red': 'Onions, raw',
    'Onions, white': 'Onions, raw',
    'bananas, overripe': 'Bananas, raw',
    'Apples, red delicious': 'Apples, raw',
    'Flour, corn, enriched': 'Flour, corn',
    'FLOUR, PASTRY, white (UNENRICHED) (UNBLEACHED)': 'Flour, wheat',
    'FLOUR, RICE, GLUTENOUS': 'Flour, rice',
    'Flour, all-purpose, enriched': 'Flour, wheat',
    'Flour, bread, white, enriched': 'Flour, wheat',
    'FLOUR, RICE, BROWN (ORGANIC)': 'Flour, rice',
    'Flour, Rice, white, unenriched': 'Flour, rice',
    'Flour, whole wheat, unenriched': 'Flour, whole-wheat',
    'Nectarines': 'Nectarines, raw',
    'Kale, Fresh': 'Kale, raw',
    'Broccoli': 'Broccoli, raw',
    'GARLIC': 'Garlic, raw',
    'Hummus': 'Hummus, commercial',
    'TOMATOES, GRAPE': 'Tomatoes, grape',
    'FLOUR, PASTRY, white (UNENRICHED) (UNBLEACHED)': 'flour, pastry',
    'Flour, all-purpose, enriched': 'flour, all-purpose',
    'Flour, bread, white, enriched': 'flour, bread',
    'FLOUR, SOY (DEFATTED)': 'soy flour',
    'Fatty Acids, Pollock, raw (CT) - NFY060DMU': 'Pollock, raw',
    'Fatty Acids, Haddock, raw (CT) - NFY060CMM': 'Haddock, raw',
    'Fatty Acids, Cottage cheese, 2% milkfat, BREAKSTONE (CT,NC) - NFY120BN5': 'Cottage cheese',
    'Fatty Acids, Oil, coconut, LOU ANA (NC) - NFY120PDM': 'Oil, coconut',
    'Fatty Acids, Tuna, canned, in water, drained solids,  BUMBLEBEE CHUNK LIGHT, IN WATER  (CO,CT) - NFY090S1B': 'Tuna, canned',
    'Fatty Acids, Peanut butter, creamy, SKIPPY (MI) - NFY120C7X': 'Peanut butter',
    'Lunchmeat, ham - NFY1210O9': 'Ham, sliced',
    'Fatty Acids, Mozzarella cheese, low-moisture, part-skim, SARGENTO': 'Mozzarella',
    'EGG, GRADE A, LARGE, WHOLE, RAW, FRESH': 'Egg, whole, raw',
    'BUTTER, STICK, UNSALTED': 'butter, without salt',
    'Fatty Acids, Cheddar cheese, sliced, CRACKER BARREL': 'Cheddar cheese',
    'Whole eggs': 'Egg, whole, raw',
    'Egg whites': 'Egg, white, raw',
    'Egg yolk': 'Egg, yolk, raw',
    'Ham': 'Ham, sliced',
    'Bacon, cooked': 'Bacon, cooked',
    'Canola oil': 'Oil, canola',
}

# 같은 이름에 FDC 항목이 여러 개 있고, 영양소 측정치 개수가 천차만별이다.
# 첫 번째 후보를 집으면 측정치가 1~2개뿐인 항목이 걸리는 일이 잦다.
# (수정 전: 85개 중 측정 compound 중앙값 9.5, 5개 이하가 132개 중 58개.
#  논문 heatmap.xlsx 원본은 중앙값 33, 5개 이하가 135개 중 2개)
# -> 후보를 모두 모은 뒤 논문 85개 기준 측정치가 가장 많은 항목을 고른다.

_src_cols = set(col_source[c] for c in all_kegg_cols if col_source[c] is not None)

# 논문 85 기준 커버리지 (병합된 라벨 단위)
_cov85 = (df_kegg[df_kegg['nutrient_kegg'].isin(_src_cols)]
          .groupby('base')['nutrient_kegg'].nunique())

def coverage(base):
    return int(_cov85.get(base, 0))

SIM_TOLERANCE = 0.08   # 최고 유사도에서 이만큼 안쪽인 후보끼리만 커버리지로 경쟁


def best_of(candidates, target):
    """이름 유사도를 먼저 보고, 동급 후보 중에서 커버리지가 큰 것을 고른다.

    커버리지만으로 고르면 'Ham' -> 'Fast foods, hamburger',
    'Chicken, dark meat' -> 'Energy drink, RED BULL' 같은 오매칭이 생긴다.
    """
    if not candidates:
        return None
    t = target
    scored = [(difflib.SequenceMatcher(None, t, b).ratio(), b) for b in candidates]
    best_sim = max(sc for sc, _ in scored)
    near = [b for sc, b in scored if sc >= best_sim - SIM_TOLERANCE]
    return max(near, key=coverage)


# p5 이름도 같은 규칙으로 정규화해야 병합된 라벨과 맞는다
p5_base = normalize_label(pd.Series(p5_names)).tolist()

all_bases = list(_cov_series.index)
base_set = set(all_bases)

matched_rows = []      # (idx, 원래 p5 이름, base 라벨)
unmatched = []

for idx, (name, nb) in enumerate(zip(p5_names, p5_base)):
    cands = []

    if nb in base_set:                                 # 1) exact
        cands.append(nb)

    if name in manual_map:                             # 2) manual map
        alt = normalize_label(pd.Series([manual_map[name]])).iloc[0]
        # 부분 문자열은 단어 경계를 넘는다("rice flour, rice starch" ⊃ "flour, rice")
        pre = [b for b in all_bases if b.startswith(alt)]
        cands.extend(pre if pre else [b for b in all_bases if alt in b])

    prefix = nb[:15]                                   # 3) prefix 15
    if prefix:
        cands.extend(b for b in all_bases if prefix in b)

    if not cands:                                      # 4) prefix 10
        prefix2 = nb[:10]
        if prefix2:
            cands.extend(b for b in all_bases if prefix2 in b)

    b = best_of(list(dict.fromkeys(cands)), nb)
    if b is None:
        unmatched.append(name)
    else:
        matched_rows.append((idx, name, b))

if matched_rows:
    import statistics
    covs = [coverage(b) for _, _, b in matched_rows]
    # 주의: 이 수치는 '측정 시도된' compound 수다(값이 0.0인 것도 포함).
    # 실제 비교 대상인 '값이 0이 아닌' 개수는 food.csv 생성 후에 찍는다.
    print(f"  병합 후 측정 시도된 compound: 중앙값={statistics.median(covs):.1f}")

# 선택된 음식만 피벗한다(전체 피벗은 메모리·시간 낭비)
_sel = set(b for _, _, b in matched_rows)
pivot_sel = (df_kegg[df_kegg['base'].isin(_sel)]
             .pivot_table(index='base', columns='nutrient_kegg',
                          values='amount', aggfunc='mean', fill_value=0))
# 진단용(tools/paper.py units): 환산 전 원단위 피벗
pivot_raw = (df_kegg[df_kegg['base'].isin(_sel)].assign(amount=_raw_amount)
             .pivot_table(index='base', columns='nutrient_kegg',
                          values='amount', aggfunc='mean', fill_value=0))

print(f"  매칭: {len(matched_rows)}/135, 실패: {len(unmatched)}")
if unmatched:
    print(f"  미매칭: {unmatched}")

# ============================================================
# 4. foodname.csv 생성
# ============================================================
print("[4/6] foodname.csv 생성...")

# food type 추정
def guess_type(name):
    """FDC food category 추정.

    규칙은 순서대로 평가되며 먼저 맞는 것이 이긴다.
    구체적인 카테고리(소시지, 외식)를 재료 카테고리(소고기, 돼지고기)보다
    앞에 두어야 한다. 예: "Frankfurter, beef"는 Beef가 아니라 Sausages다.
    """
    n = name.lower()

    # 브랜드명이 카테고리 키워드와 충돌하는 경우 먼저 제거한다.
    # 예: "Cheddar cheese, sliced, CRACKER BARREL"의 'cracker'가 Baked로 오인됨.
    for brand in ['cracker barrel']:
        n = n.replace(brand, '')

    rules = [
        # --- 가공/조리 형태가 카테고리를 결정하는 것부터 ---
        (7.0,  'Sausages and Luncheon Meats',
         ['sausage', 'frankfurter', 'hot dog', 'lunchmeat', 'luncheon',
          'chorizo', 'bologna', 'salami', 'pepperoni']),
        (25.0, 'Restaurant Foods',
         ['chinese restaurant', 'restaurant, latino', 'pupusa', 'tamale',
          'fast food', 'fried rice']),
        (18.0, 'Baked Products',
         ['bread', 'roll,', 'bun', 'cake', 'pie', 'biscuit', 'cracker',
          'waffle', 'muffin', 'tortilla', 'bagel', 'cookie']),
        (19.0, 'Sweets',
         ['sugar', 'candy', 'chocolate', 'syrup', 'jam', 'jelly', 'sweets']),
        (4.0,  'Fats and Oils',
         ['oil', 'shortening', 'lard']),

        # --- 재료 카테고리 ---
        (12.0, 'Nut and Seed Products',
         ['almond', 'sunflower seed', 'walnut', 'pecan', 'cashew',
          'pistachio', 'sesame seed']),
        (16.0, 'Legumes and Legume Products',
         ['hummus', 'peanut', 'soybean', 'flour, soy', 'beans, dry',
          'kidney', 'lentil', 'chickpea', 'tofu']),
        (1.0,  'Dairy and Egg Products',
         ['milk', 'cheese', 'yogurt', 'butter', 'egg', 'cream', 'ricotta',
          'parmesan', 'mozzarella', 'cheddar', 'swiss', 'cottage']),
        (15.0, 'Finfish and Shellfish Products',
         ['tuna', 'pollock', 'haddock', 'fish', 'salmon', 'shrimp',
          'shellfish', 'cod,', 'crab', 'clam']),
        (5.0,  'Poultry Products',
         ['chicken', 'turkey', 'poultry', 'duck']),
        (10.0, 'Pork Products',
         ['pork', 'bacon', 'ham']),
        (13.0, 'Beef Products',
         ['beef', 'steak', 't-bone', 'porterhouse', 'tenderloin',
          'eye of round', 'top round', 'short loin']),
        (6.0,  'Soups, Sauces, and Gravies',
         ['sauce', 'salsa', 'ketchup', 'mustard', 'soup', 'gravy',
          'dressing']),

        # --- 식물성: 채소를 과일보다 먼저 (예: "TOMATOES, GRAPE") ---
        (11.0, 'Vegetables and Vegetable Products',
         ['onion', 'kale', 'carrot', 'broccoli', 'lettuce', 'tomato',
          'garlic', 'olive', 'pickle', 'vegetable', 'beans, snap',
          'potato', 'spinach', 'cabbage']),
        (9.0,  'Fruits and Fruit Juices',
         ['apple', 'peach', 'kiwi', 'orange', 'banana', 'melon',
          'cantaloupe', 'nectarine', 'pear', 'strawberr', 'fig',
          'grapefruit', 'grape', 'fruit', 'berry', 'berries']),
        (20.0, 'Cereal Grains and Pasta',
         ['flour', 'rice', 'pasta', 'starch', 'oat', 'wheat', 'corn',
          'cereal', 'grain']),
    ]
    # 부분 문자열이 아니라 단어 시작 위치로 매칭한다.
    # 예: 'broiled'에 'oil'이 들어 있어 Ground turkey가 Fats/Oils로 가는 것을 막는다.
    # 끝에는 경계를 두지 않아 'strawberr' -> 'strawberries' 같은 접두 매칭은 유지된다.
    for t, _label, keywords in rules:
        if any(re.search(r'\b' + re.escape(w), n) for w in keywords):
            return t
    return None   # 미분류 — 호출부에서 보고


# FDC 원본 카테고리 (숫자 ID 인 것만)
FDC_CATEGORY = {}
_fdc_food = os.path.join(BASE_DIR, 'fdc_raw/food.csv')
if os.path.exists(_fdc_food):
    _ff = pd.read_csv(_fdc_food, low_memory=False,
                      usecols=['fdc_id', 'food_category_id'])
    for _i, _c in zip(_ff['fdc_id'], _ff['food_category_id']):
        try:
            FDC_CATEGORY[int(_i)] = float(_c)
        except (TypeError, ValueError):
            pass
    print(f"  FDC 카테고리 로드: {len(FDC_CATEGORY):,}종")
else:
    print("  ⚠ fdc_raw/food.csv 없음 — guess_type() 추정만 사용")

rows = []
untyped = []
guessed = []
for idx, name, base_lbl in matched_rows:
    prof = pivot_sel.loc[base_lbl]
    row = {'fdc_id': int(_fdc_of_base[base_lbl]), 'foodname': name}
    for c in all_kegg_cols:
        src = col_source[c]
        row[c] = float(prof[src]) if (src is not None and src in prof.index) else 0.0
    # FDC 원본의 food_category_id 를 우선 쓴다 (fdc_raw/food.csv).
    # guess_type() 키워드 추정은 숫자 ID 구간에서 113/119(95%) 정확하지만,
    # 실제 값이 있으면 그것을 쓰는 게 맞다. Branded 항목은 카테고리가
    # 문자열("Pre-Packaged Fruit & Vegetables")이라 숫자로 못 쓰므로
    # 그때만 guess_type() 으로 떨어진다.
    t = FDC_CATEGORY.get(int(_fdc_of_base[base_lbl]))
    if t is None:
        t = guess_type(name)
        if t is None:
            untyped.append(name)
            t = 11.0   # fallback
        guessed.append(name)
    row['type'] = float(t)
    rows.append(row)

if guessed:
    print(f"  FDC 카테고리가 숫자가 아니라 guess_type() 으로 추정: {len(guessed)}개")
if untyped:
    print(f"  ⚠ 카테고리 미분류 {len(untyped)}개 (11.0으로 fallback):")
    for u in untyped:
        print(f"      {u}")

df_foodname = pd.DataFrame(rows)
df_foodname.to_csv(os.path.join(OUT_DIR, 'foodname.csv'), index=False)
print(f"  shape: {df_foodname.shape}")
print(f"  foods: {len(df_foodname)}, compounds: {len(all_kegg_cols)}")

# ============================================================
# 5. food.csv 생성
# ============================================================
print("[5/6] food.csv 생성...")

df_food = df_foodname[all_kegg_cols + ['type']].copy()
_nz = (df_food[all_kegg_cols].values != 0).sum(axis=1)
print(f"  85 중 값이 0이 아닌 compound: 중앙값={float(np.median(_nz)):.1f}, "
      f"평균={_nz.mean():.1f}, 최대={_nz.max()}, "
      f"5개 이하={int((_nz <= 5).sum())}개   (논문 원본: 33.0 / 34.1 / 73 / 2개)")
df_food.to_csv(os.path.join(OUT_DIR, 'food.csv'), index=False)
print(f"  shape: {df_food.shape}")

# 진단용 원단위 사본 (tools/paper.py units 가 논문 환산 계수를 역산할 때 쓴다)
_raw_rows = []
for idx, name, base_lbl in matched_rows:
    prof = pivot_raw.loc[base_lbl]
    _raw_rows.append({c: float(prof[col_source[c]])
                      if (col_source[c] is not None and col_source[c] in prof.index)
                      else 0.0 for c in all_kegg_cols})
pd.DataFrame(_raw_rows).assign(type=df_food['type'].values).to_csv(
    os.path.join(OUT_DIR, 'food_rawunit.csv'), index=False)

# ============================================================
# 6. weight.csv 생성
# ============================================================
print("[6/6] weight.csv 생성...")

n = len(all_kegg_cols)
W = np.zeros((8, n))

for j, c in enumerate(all_kegg_cols):
    keys = {c, col_source[c]} - {None}
    # 논문 §4.2.1 을 따른다: hasPositiveAssociation -> +1.
    # (그 목록은 실제로 MENDA 의 'Up'=우울증에서 증가이므로 논문 자신의
    #  반전 오류지만, 재현이 목적이므로 논문을 따른다. REPRODUCTION.md §13)
    ip = 1.0 if keys & pos_kegg else 0.0
    ing = 1.0 if keys & neg_kegg else 0.0
    # 4 sources × 2 rows (pos, neg)
    for s in range(4):
        W[s*2, j] = ip
        W[s*2+1, j] = ing

df_weight = pd.DataFrame(W, columns=all_kegg_cols)
df_weight.to_csv(os.path.join(OUT_DIR, 'weight.csv'), index=False)
print(f"  shape: {df_weight.shape}")

# ============================================================
# 요약
# ============================================================
print("\n" + "=" * 60)
print("✅ 재구성 완료")
print("=" * 60)

eff = {col_source[c] or c for c in all_kegg_cols} | set(all_kegg_cols)
overlap = eff & (pos_kegg | neg_kegg)
only_pos = eff & pos_kegg - neg_kegg
only_neg = eff & neg_kegg - pos_kegg
both = eff & pos_kegg & neg_kegg

print(f"""
  파일                내 결과          논문
  ─────────────────────────────────────────
  foodname.csv        {df_foodname.shape}    (135, 88)
  food.csv            {df_food.shape}    (135, 89)
  weight.csv          {df_weight.shape}     (8, 88)

  Compounds 총: {len(all_kegg_cols)} (논문: 85)
  MENDA overlap: {len(overlap)} — positive only: {len(only_pos)}, negative only: {len(only_neg)}, both: {len(both)}
  
  Food category 분포:
{df_foodname['type'].value_counts().sort_index().to_string()}

  미매칭 음식 ({len(unmatched)}개):
  {unmatched}
""")
