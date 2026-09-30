"""
FDC 원본에서 food_nutrient.csv 재조립
======================================
현재 food_nutrient.csv는 정확히 1,048,575행 = Excel 행 한계다.
Excel에서 열렸다가 저장되며 그 뒤가 잘린 파일이다(id 결번 1,100만 개,
id 비단조, fdc_id 최대 1,105,897 vs 실제 FDC 270만대).
이 때문에 85 compound 커버리지 중앙값이 18.5에 머문다(논문 원본 33.0).

사용법
------
1. https://fdc.nal.usda.gov/download-datasets.html 에서
   "Full Download of All Data Types" (CSV) 를 받아 압축을 푼다.
   우리 음식은 Foundation 83 / SR Legacy 38 / Branded 11 로 세 데이터셋에
   걸쳐 있으므로 개별 다운로드로는 부족하다.
2. python3 rebuild_food_nutrient.py <압축 푼 디렉토리>
3. python3 run_pipeline.py

★ 받은 CSV를 Excel로 열지 말 것. 같은 방식으로 다시 잘린다.

필요한 원본 파일
---------------
  food.csv           fdc_id, data_type, description
  food_nutrient.csv  id, fdc_id, nutrient_id, amount
  nutrient.csv       id, name, unit_name

출력 컬럼 (기존과 동일)
  id, fdc_id, food_name, nutrient_id, nutrient_name, amount, nutrient_unit, nutrient_kegg
"""
import os
import sys
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(BASE, 'nutrient_kegg_map.csv')
OUT_PATH = os.path.join(BASE, 'food_nutrient.csv')
EXCEL_LIMIT = 1_048_575

if len(sys.argv) < 2:
    sys.exit(__doc__)
src = sys.argv[1]

need = ['food.csv', 'food_nutrient.csv', 'nutrient.csv']
missing = [f for f in need if not os.path.exists(os.path.join(src, f))]
if missing:
    sys.exit(f"필요한 파일이 없습니다: {missing}\n받은 디렉토리 경로를 확인하세요.")

print('[1/4] FDC 원본 로드...')
food = pd.read_csv(os.path.join(src, 'food.csv'), low_memory=False,
                   usecols=['fdc_id', 'description'])
nutr = pd.read_csv(os.path.join(src, 'nutrient.csv'), low_memory=False,
                   usecols=['id', 'name', 'unit_name'])
fn = pd.read_csv(os.path.join(src, 'food_nutrient.csv'), low_memory=False,
                 usecols=['id', 'fdc_id', 'nutrient_id', 'amount'])
print(f'  food {len(food):,} / nutrient {len(nutr):,} / food_nutrient {len(fn):,}')
if len(fn) <= EXCEL_LIMIT:
    print(f'  ⚠ food_nutrient.csv가 {len(fn):,}행입니다. '
          f'{EXCEL_LIMIT:,}행 이하이면 이 파일도 잘렸을 수 있습니다.')

print('[2/4] 조인...')
df = (fn.merge(food, on='fdc_id', how='inner')
        .merge(nutr.rename(columns={'id': 'nutrient_id',
                                    'name': 'nutrient_name',
                                    'unit_name': 'nutrient_unit'}),
               on='nutrient_id', how='left'))
df = df.rename(columns={'description': 'food_name'})
print(f'  조인 결과: {len(df):,}행')

print('[3/4] KEGG 매핑 적용...')
mp = pd.read_csv(MAP_PATH)
kegg = dict(zip(mp['nutrient_id'], mp['nutrient_kegg']))
df['nutrient_kegg'] = df['nutrient_id'].map(kegg).fillna(0)
hit = df['nutrient_kegg'].astype(str).str.startswith('C')
print(f'  KEGG 매핑된 행: {int(hit.sum()):,} ({hit.mean()*100:.1f}%)')
unmapped = sorted(set(df.loc[~hit, 'nutrient_id']) - set(mp['nutrient_id']))
if unmapped:
    print(f'  매핑표에 없는 nutrient_id {len(unmapped)}개 (0으로 둠): {unmapped[:10]}')

print('[4/4] 저장...')
cols = ['id', 'fdc_id', 'food_name', 'nutrient_id',
        'nutrient_name', 'amount', 'nutrient_unit', 'nutrient_kegg']
df[cols].to_csv(OUT_PATH, index=False)
print(f'  {OUT_PATH}  {len(df):,}행')
print()
print('다음: python3 run_pipeline.py')
