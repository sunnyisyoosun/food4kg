"""
논문 85 compound 목록 추출
==========================
Food4healthKG/analyse/heatmap.xlsx (논문 Fig. 4(c) 원본 데이터)의
상단 4개 메타 행에서 논문이 실제로 사용한 85개 compound를 추출한다.

  행 0: 원본 compound 인덱스 (0~84)
  행 1: KEGG ID
  행 2: compound 이름
  행 3: 6개 biological group (논문 4.2.3)

출력: analyse/paper85_compounds.csv
실행: python3 build_paper85.py
"""

import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, 'Food4healthKG/analyse/heatmap.xlsx')
OUT = os.path.join(BASE_DIR, 'analyse/paper85_compounds.csv')

d = pd.read_excel(SRC, header=None)

df = pd.DataFrame({
    'orig_idx': d.iloc[0].tolist(),
    'kegg':     d.iloc[1].tolist(),
    'name':     d.iloc[2].tolist(),
    'group':    d.iloc[3].tolist(),
})

assert len(df) == 85, f"85개여야 하는데 {len(df)}개"
assert df['kegg'].nunique() == 85, "KEGG ID 중복"
assert sorted(df['orig_idx']) == list(range(85)), "orig_idx가 0~84가 아님"

# 논문의 원본 compound 순서(orig_idx)로 정렬 — final.py의 열 순서와 맞추기 위함
df = df.sort_values('orig_idx').reset_index(drop=True)
df.to_csv(OUT, index=False)

print(f"저장: {OUT}")
print(f"  compounds: {len(df)}")
print(f"\n  group 분포:")
print(df['group'].value_counts().to_string())
