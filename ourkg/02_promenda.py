"""02 — ProMENDA → compound x depression 관계 행렬 E.

논문 §3.1 은 MENDA(2020) 의 depression-metabolite 5,675 관계를 썼다.
여기서는 그 후속판 ProMENDA(Pu et al. 2024) 전체를 쓴다.

극성 규약 — 논문 §4.2.1 "a value of 1 indicates a positive relationship between
a compound and depression (relieving the disease)". 재현 파이프라인
(map_promenda.py, PROBLEMS.md §7)에서 확정한 규약을 그대로 가져온다.
  Type1 (우울증 vs 대조군): up in depression = +1
  Type2/4 (치료·반응 비교)  : up = 치료로 증가  = -1 로 이미 대응
  Type3/5                   : 설계가 대응되지 않아 집계에서 제외하지 않고
                              다수결에만 참여 (재현판과 동일)

출력
  out/compound_depression.csv  kegg, direction, pos, neg, n_study, n_record
  out/promenda_records.csv     kegg, study_id, incidence, study_type, tissue, organism
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, OUT

SRC = os.path.join(BASE, '41398_2024_2948_MOESM3_ESM.xlsx')
STYPE_COL = 'M_Study_type_Metabolite_level'
REG_COL = 'M_Up/Down_regulated '

UP = {'up', 'upregulated', 'up-regulated', 'increased', 'increase', 'higher'}
DOWN = {'down', 'downregulated', 'down-regulated', 'decreased', 'decrease', 'lower'}

print('[1/3] ProMENDA 로드')
df = pd.read_excel(SRC, sheet_name='M_Metabolite')
print(f'  {len(df):,} 행 / metabolite {df["M_Metabolite_ID"].nunique():,} '
      f'/ study {df["M_Study_ID"].nunique():,}')

print('[2/3] KEGG 추출 + 극성')
df = df[df['M_KEGG'].astype(str).str.contains(r'C\d{5}', na=False)].copy()
df['kegg'] = df['M_KEGG'].astype(str).str.extract(r'(C\d{5})')[0]


def incidence(v):
    v = str(v).lower().strip()
    if v in UP:
        return -1          # 기본 해석: 우울증에서 증가 = 악화
    if v in DOWN:
        return +1
    return 0


df['incidence'] = df[REG_COL].apply(incidence)
is_t1 = df[STYPE_COL].astype(str) == 'Type1'
df.loc[is_t1, 'incidence'] *= -1      # 논문 규약: Type1 은 up = +1
print(f'  KEGG 보유 {len(df):,} 행 / compound {df["kegg"].nunique():,}')
print(f'  Type1 반전 {int(is_t1.sum()):,} 행')
print(f'  +1 {int((df.incidence == 1).sum()):,} / -1 {int((df.incidence == -1).sum()):,} '
      f'/ 0 {int((df.incidence == 0).sum()):,}')

print('[3/3] compound 별 다수결')
g = df.groupby('kegg')
rows = []
for kegg, sub in g:
    pos = int((sub['incidence'] == 1).sum())
    neg = int((sub['incidence'] == -1).sum())
    direction = 1 if pos > neg else (-1 if neg > pos else 0)
    rows.append({'kegg': kegg, 'name': sub['M_Metabolite_name'].iloc[0],
                 'direction': direction, 'pos': pos, 'neg': neg,
                 'n_study': sub['M_Study_ID'].nunique(), 'n_record': len(sub)})
E = pd.DataFrame(rows).sort_values('n_record', ascending=False).reset_index(drop=True)

# 근거 강도 — ProMENDA 는 논문이 쓴 MENDA 보다 훨씬 크고(compound 1,412),
# 연구 2~3건짜리 compound 까지 들어온다. 논문의 85 compound 는 큐레이션된
# 목록이라 이 문제가 없었지만, 전체를 쓰면 근거가 얕은 compound 가 다수결에서
# ±1 을 똑같이 받는다(예: Ethanol 4:1, 연구 3건).
#
#  e_binary  : 논문 §4.2.1 그대로의 +1 / -1 / 0
#  e_shrunk  : (pos-neg)/(pos+neg+K) — 사전 설정한 유사계수 K 로 0 쪽으로 축소.
#              근거가 쌓이면 ±1 에 가까워지고 얕으면 0 에 가깝다.
#  q         : pos:neg 에 대한 이항검정 양측 p 의 BH 보정값(근거 유의성)
from scipy.stats import binomtest

SHRINK_K = int(os.environ.get('SHRINK_K', '10'))
E['e_binary'] = E['direction']
E['e_shrunk'] = (E['pos'] - E['neg']) / (E['pos'] + E['neg'] + SHRINK_K)
pv = [binomtest(int(r.pos), int(r.pos + r.neg)).pvalue if (r.pos + r.neg) > 0 else 1.0
      for r in E.itertuples()]
E['p'] = pv
_o = pd.Series(pv).rank(method='first').astype(int).values
_srt = sorted(range(len(pv)), key=lambda i: pv[i])
_q = [0.0] * len(pv)
_prev = 1.0
for rank, i in enumerate(reversed(_srt), 1):
    _prev = min(_prev, pv[i] * len(pv) / (len(pv) - rank + 1))
    _q[i] = _prev
E['q'] = _q
E.to_csv(os.path.join(OUT, 'compound_depression.csv'), index=False)
print(f'  근거 축소 K={SHRINK_K}: |e_shrunk| 중앙값 {E.e_shrunk.abs().median():.3f}, '
      f'BH q<0.05 {int((E.q < 0.05).sum())} compound')

cols = ['kegg', 'M_Study_ID', 'incidence', STYPE_COL,
        'M_Tissue_Metabolite_level_1', 'M_Organism_Metabolite_level_1']
df[cols].rename(columns={'M_Study_ID': 'study_id', STYPE_COL: 'study_type',
                         'M_Tissue_Metabolite_level_1': 'tissue',
                         'M_Organism_Metabolite_level_1': 'organism'}
                ).to_csv(os.path.join(OUT, 'promenda_records.csv'), index=False)

print(f'  compound {len(E):,}  (+ {int((E.direction == 1).sum())} / '
      f'- {int((E.direction == -1).sum())} / tie {int((E.direction == 0).sum())})')

food = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
fk = set(food['kegg'].unique())
ov = fk & set(E[E.direction != 0]['kegg'])
print(f'  FDC compound {len(fk)} 중 depression 방향 확정 {len(ov)} '
      f'(논문 E: 85 중 공개 소스로 69)')
