"""01 — 최신 FDC 원본 → food x KEGG compound 중량 행렬 F (g / 100 g).

논문 §3.1(FDC 통합) · §3.2(라벨 정규화·exact matching 병합)를 따르되,
논문이 고정한 135 food / 85 compound 목록을 쓰지 않고 FDC 전체에서 만든다.

출력
  out/food_compound_long.csv  food_key, kegg, amount_g
  out/foods.csv               food_key, fdc_id, food_name, data_type, category, n_compound
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BASE, OUT, FDC_RAW, UNIT_TO_G, FDC_CATEGORY,
                    normalize_label, normalize_category, kegg_map)

MIN_COV = int(os.environ.get('MIN_COV', '20'))   # 음식당 최소 측정 compound 수
CHUNK = 2_000_000

print('[1/5] nutrient -> KEGG 매핑표')
mp = kegg_map()
nid2kegg = dict(zip(mp['nutrient_id'], mp['nutrient_kegg']))
nid2unit = dict(zip(mp['nutrient_id'], mp['nutrient_unit']))
nid2name = dict(zip(mp['nutrient_id'], mp['nutrient_name']))
print(f'  nutrient {len(nid2kegg)} -> KEGG compound {mp["nutrient_kegg"].nunique()}')

print('[2/5] food.csv')
food = pd.read_csv(os.path.join(FDC_RAW, 'food.csv'), low_memory=False,
                   usecols=['fdc_id', 'data_type', 'description', 'food_category_id'])
print(f'  {len(food):,} 행')
cat_num = pd.to_numeric(food['food_category_id'], errors='coerce')
food['category'] = cat_num.map(FDC_CATEGORY)
food.loc[food['category'].isna(), 'category'] = food['food_category_id'].where(
    cat_num.isna(), None)
food['category'] = food['category'].fillna('Unknown')
food = food.rename(columns={'description': 'food_name'})

print(f'[3/5] food_nutrient.csv 스트리밍 (KEGG 매핑 행만, 단위 g 환산)')
keep = set(nid2kegg)
parts = []
rows = 0
for ch in pd.read_csv(os.path.join(FDC_RAW, 'food_nutrient.csv'), chunksize=CHUNK,
                      usecols=['fdc_id', 'nutrient_id', 'amount'], low_memory=False):
    rows += len(ch)
    ch = ch[ch['nutrient_id'].isin(keep)]
    if len(ch):
        parts.append(ch)
    print(f'\r  읽음 {rows:,} / 보관 {sum(len(p) for p in parts):,}', end='', flush=True)
print()
fn = pd.concat(parts, ignore_index=True)
del parts
fn['kegg'] = fn['nutrient_id'].map(nid2kegg)
fn['unit'] = fn['nutrient_id'].map(nid2unit)
fn['amount_g'] = pd.to_numeric(fn['amount'], errors='coerce') * fn['unit'].map(UNIT_TO_G).fillna(1.0)
fn = fn.dropna(subset=['amount_g'])
print(f'  KEGG 측정값 {len(fn):,} 행, compound {fn["kegg"].nunique()}')

print('[4/5] 라벨 병합 (논문 §3.2 exact matching)')
fn = fn.merge(food[['fdc_id', 'food_name', 'data_type', 'category']], on='fdc_id', how='inner')
fn['food_key'] = normalize_label(fn['food_name'])
fn = fn[fn['food_key'].str.len() > 0]
print(f'  FDC 항목 {fn["fdc_id"].nunique():,} -> 병합 음식 {fn["food_key"].nunique():,}')

print(f'[5/5] 음식당 compound >= {MIN_COV} 필터')
long = (fn.groupby(['food_key', 'kegg'], as_index=False)['amount_g'].mean())
cov = long.groupby('food_key')['kegg'].nunique()
keep_food = set(cov[cov >= MIN_COV].index)
long = long[long['food_key'].isin(keep_food)]

# 대표 항목은 큐레이션 수준이 높은 데이터셋 순으로 고른다.
_PRIORITY = {'foundation_food': 0, 'sr_legacy_food': 1, 'survey_fndds_food': 2,
             'sample_food': 3, 'sub_sample_food': 4, 'market_acquistion': 5,
             'agricultural_acquisition': 6, 'experimental_food': 7, 'branded_food': 8}
_sel = fn[fn['food_key'].isin(keep_food)].copy()
_sel['_prio'] = _sel['data_type'].map(_PRIORITY).fillna(9)
meta = (_sel.sort_values('_prio')
        .groupby('food_key')
        .agg(fdc_id=('fdc_id', 'first'), food_name=('food_name', 'first'),
             data_type=('data_type', 'first'), category=('category', 'first')))
meta['n_compound'] = cov.reindex(meta.index).astype(int)
meta = meta.reset_index()
meta['food_group'] = [normalize_category(c, n)
                      for c, n in zip(meta['category'], meta['food_name'])]

long.to_csv(os.path.join(OUT, 'food_compound_long.csv'), index=False)
meta.to_csv(os.path.join(OUT, 'foods.csv'), index=False)
print(f'  음식 {len(meta):,} / compound {long["kegg"].nunique()} / 값 {len(long):,}')
print(f'  음식당 compound 중앙값 {meta["n_compound"].median():.1f} '
      f'(논문 heatmap 원본 33.0)')
print('  카테고리 상위:')
print(meta['food_group'].value_counts().head(12).to_string())
print(f"  Unclassified {int((meta['food_group'] == 'Unclassified').sum()):,}")
