"""
Food4healthKG 재현: 누락된 입력 파일 역설계 (개선)
=====================================================
변경사항:
1. food_nutrient.csv의 88 KEGG compound 전부 사용 (논문 85와 근사)
2. 음식 매칭 개선 (fuzzy + 수동 매핑)
3. 같은 KEGG ID에 여러 nutrient가 매핑될 때 합산
"""

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
print("[2/6] food_nutrient.csv 로드 + pivot...")

df = pd.read_csv(os.path.join(BASE_DIR, 'food_nutrient.csv'), low_memory=False)
df_kegg = df[df['nutrient_kegg'].astype(str).str.startswith('C')].copy()

# 같은 food+KEGG 쌍이 여러 nutrient로 존재 (e.g. Vitamin A, IU + RAE)
# → 합산
pivot_all = df_kegg.pivot_table(
    index=['fdc_id', 'food_name'],
    columns='nutrient_kegg',
    values='amount',
    aggfunc='sum',
    fill_value=0
)
pivot_all = pivot_all.reset_index()
print(f"  전체 pivot: {pivot_all.shape[0]} foods × {pivot_all.shape[1]-2} compounds")

all_kegg_cols = [c for c in pivot_all.columns if str(c).startswith('C')]
print(f"  KEGG compound: {len(all_kegg_cols)}")

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

food_lookup = {}
for _, row in pivot_all.iterrows():
    food_lookup[row['food_name'].strip().lower()] = row

matched_rows = []
unmatched = []

for idx, name in enumerate(p5_names):
    name_l = name.strip().lower()
    
    # 1) exact
    if name_l in food_lookup:
        row = food_lookup[name_l]
        matched_rows.append((idx, name, row))
        continue
    
    # 2) manual map
    if name in manual_map:
        alt = manual_map[name].lower()
        found = False
        for k, row in food_lookup.items():
            if alt in k:
                matched_rows.append((idx, name, row))
                found = True
                break
        if found:
            continue
    
    # 3) prefix match (첫 15자)
    prefix = name_l[:15]
    found = False
    for k, row in food_lookup.items():
        if prefix in k or k.startswith(prefix):
            matched_rows.append((idx, name, row))
            found = True
            break
    
    if not found:
        # 4) shorter prefix (첫 10자)
        prefix2 = name_l[:10]
        for k, row in food_lookup.items():
            if prefix2 in k:
                matched_rows.append((idx, name, row))
                found = True
                break
    
    if not found:
        unmatched.append(name)

print(f"  매칭: {len(matched_rows)}/135, 실패: {len(unmatched)}")
if unmatched:
    print(f"  미매칭: {unmatched}")

# ============================================================
# 4. foodname.csv 생성
# ============================================================
print("[4/6] foodname.csv 생성...")

# food type 추정
def guess_type(name):
    n = name.lower()
    rules = [
        (['milk','cheese','yogurt','butter','egg','cream','ricotta','parmesan',
          'mozzarella','cheddar','swiss','cottage'], 1.0),
        (['beef','steak','round','loin','tenderloin','porterhouse','t-bone'], 13.0),
        (['chicken','turkey','poultry','ground turkey'], 5.0),
        (['pork','bacon','ham','chorizo'], 10.0),
        (['sausage','frankfurter','hot dog','lunchmeat','breakfast sausage'], 7.0),
        (['tuna','pollock','haddock','fish','salmon','shellfish'], 15.0),
        (['apple','peach','kiwi','orange','banana','grape','melon','cantaloupe',
          'nectarine','pear','strawberr','fig','grapefruit','fruit'], 9.0),
        (['onion','kale','carrot','broccoli','lettuce','tomato','bean','garlic',
          'olive','pickle','vegetable'], 11.0),
        (['flour','oatmeal','bread','starch','corn','rice','wheat','pasta'], 20.0),
        (['cookie','sugar','sweet','chocolate'], 19.0),
        (['oil','canola','soybean oil','fat'], 4.0),
        (['sauce','salsa','ketchup','mustard','soup','gravy'], 6.0),
        (['hummus','soy','peanut','almond','sunflower','nut','seed','legume'], 16.0),
        (['restaurant','pupusa','fried rice','chinese'], 25.0),
    ]
    for keywords, t in rules:
        if any(w in n for w in keywords):
            return t
    return 11.0

rows = []
for idx, name, data in matched_rows:
    row = {'fdc_id': int(data['fdc_id']), 'foodname': name}
    for c in all_kegg_cols:
        row[c] = data[c]
    row['type'] = guess_type(name)
    rows.append(row)

df_foodname = pd.DataFrame(rows)
df_foodname.to_csv(os.path.join(OUT_DIR, 'foodname.csv'), index=False)
print(f"  shape: {df_foodname.shape}")
print(f"  foods: {len(df_foodname)}, compounds: {len(all_kegg_cols)}")

# ============================================================
# 5. food.csv 생성
# ============================================================
print("[5/6] food.csv 생성...")

df_food = df_foodname[all_kegg_cols + ['type']].copy()
df_food.to_csv(os.path.join(OUT_DIR, 'food.csv'), index=False)
print(f"  shape: {df_food.shape}")

# ============================================================
# 6. weight.csv 생성
# ============================================================
print("[6/6] weight.csv 생성...")

n = len(all_kegg_cols)
W = np.zeros((8, n))

for j, c in enumerate(all_kegg_cols):
    ip = 1.0 if c in pos_kegg else 0.0
    ing = 1.0 if c in neg_kegg else 0.0
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

overlap = set(all_kegg_cols) & (pos_kegg | neg_kegg)
only_pos = set(all_kegg_cols) & pos_kegg - neg_kegg
only_neg = set(all_kegg_cols) & neg_kegg - pos_kegg
both = set(all_kegg_cols) & pos_kegg & neg_kegg

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
