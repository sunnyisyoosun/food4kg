"""
repo 배포본만으로 재현되는가
==============================
공식 Food4healthKG repo 가 배포한 것만 쓴다. 외부 다운로드(FDC 전체,
ProMENDA, MENDA 원본, MiKG)와 우리가 만든 매핑표를 전부 배제한다.

입력 4개
  1. analyse/heatmap.xlsx                  85 compound 목록 + 6개 group
  2. analyse/p5_foodname.txt               135 food 이름 (+ 줄 순서 = 논문 순위)
  3. food_nutrient.csv                     (food_nutrient.csv.zip 에서 추출)
  4. foodkg_triply/MENDA_Depression.jsonld (foodkg_triply.zip 에서 추출)

알고리즘은 공식 final.py 를 그대로 쓴다
  정규화  행별 min-max
  유사도  modified cosine (common = 둘 다 >0, 분모는 전체)
  점수    p = (Xn·E)·S / colsum(S),  S[i,i]=0

E 는 MENDA_Depression.jsonld 의 두 목록만으로 만든다.
논문 §4.2.1 을 따라 hasPositiveAssociation -> +1.
양쪽에 속하면(both) 방향을 정할 수 없다 — 그 처리를 3가지로 비교한다.

실행: python3 tools/repo_only.py [food_nutrient.csv 경로]
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(BASE, 'Food4healthKG')
K = 30

FN = (sys.argv[1] if len(sys.argv) > 1 else
      os.path.join(BASE, 'food_nutrient.csv'))
if not os.path.exists(FN):
    sys.exit(f'food_nutrient.csv 없음: {FN}')

print('입력')
print(f'  heatmap.xlsx              {os.path.join(REPO, "analyse/heatmap.xlsx")}')
print(f'  p5_foodname.txt           {os.path.join(REPO, "analyse/p5_foodname.txt")}')
print(f'  food_nutrient.csv         {FN}')
print(f'  MENDA_Depression.jsonld   foodkg_triply/')
print()

# ---------------------------------------------------------------- 1. 85 compound
hm = pd.read_excel(os.path.join(REPO, 'analyse/heatmap.xlsx'), header=None)
order = np.argsort([int(v) for v in hm.iloc[0]])
COLS = [list(hm.iloc[1])[j] for j in order]
CNAME = dict(zip(list(hm.iloc[1]), list(hm.iloc[2])))
print(f'[1] heatmap.xlsx -> compound {len(COLS)}종')

# ---------------------------------------------------------------- 2. 135 food
p5 = [l.strip() for l in
      open(os.path.join(REPO, 'analyse/p5_foodname.txt')) if l.strip()]
print(f'[2] p5_foodname.txt -> food {len(p5)}개')

# ---------------------------------------------------------------- 3. F 행렬
print('[3] food_nutrient.csv 로드...')
df = pd.read_csv(FN, low_memory=False)
dk = df[df['nutrient_kegg'].astype(str).str.startswith('C')].copy()
have = sorted(dk['nutrient_kegg'].unique())
print(f'    KEGG 매핑된 compound {len(have)}종')
print(f'    논문 85종과 교집합    {len(set(have) & set(COLS))}종'
      f'  ({len(set(COLS) - set(have))}종 결손)')

dk['nl'] = dk['food_name'].astype(str).str.strip().str.lower()
piv = dk.pivot_table(index='nl', columns='nutrient_kegg', values='amount',
                     aggfunc='mean', fill_value=0)

# p5 이름 -> pivot 행. 정확 일치 우선, 없으면 앞부분 일치
idx_names = list(piv.index)
prefix_map = {}
for n in idx_names:
    prefix_map.setdefault(n[:15], n)

rows, kept_names, miss = [], [], []
for name in p5:
    nl = name.strip().lower()
    hit = nl if nl in piv.index else prefix_map.get(nl[:15])
    if hit is None:
        cand = [n for n in idx_names if nl[:10] and nl[:10] in n]
        hit = cand[0] if cand else None
    if hit is None:
        miss.append(name)
        continue
    rows.append(piv.loc[hit].reindex(COLS).fillna(0).values.astype(float))
    kept_names.append(name)

X = np.array(rows)
print(f'    food 매칭 {len(kept_names)}/{len(p5)}  (실패 {len(miss)})')
nz = (X != 0).sum(1)
print(f'    측정 compound 중앙값 {np.median(nz):.0f} / 85   (논문 원본 33)')

# ---------------------------------------------------------------- 4. E
with open(os.path.join(BASE, 'foodkg_triply/MENDA_Depression.jsonld')) as f:
    mj = json.load(f)
pos, neg = set(), set()
for entry in mj:
    for node in entry.get('@graph', []):
        for key, vals in node.items():
            short = key.rsplit('#', 1)[-1]
            if short not in ('hasPositiveAssociation', 'hasNegativeAssociation'):
                continue
            tgt = pos if short == 'hasPositiveAssociation' else neg
            for v in (vals if isinstance(vals, list) else [vals]):
                if isinstance(v, dict) and '@id' in v:
                    cid = v['@id'].rsplit('/', 1)[-1]
                    if cid.startswith('C'):
                        tgt.add(cid)
print(f'[4] MENDA jsonld -> pos {len(pos)} / neg {len(neg)} / both {len(pos & neg)}')

def build_E(both):
    """both: 'pos' | 'neg' | 'zero'"""
    e = []
    for c in COLS:
        p_, n_ = c in pos, c in neg
        if p_ and n_:
            e.append({'pos': 1, 'neg': -1, 'zero': 0}[both])
        elif p_:
            e.append(1)
        elif n_:
            e.append(-1)
        else:
            e.append(0)
    return np.array(e, dtype=float)

# ---------------------------------------------------------------- 5. 점수
def normalize(A):
    out, keep = [], []
    for i in range(A.shape[0]):
        r = A[i].astype(float).copy()
        if r.max() - r.min() == 0:
            continue
        out.append((r - r.min()) / (r.max() - r.min()))
        keep.append(i)
    return np.array(out), keep


Xn, keep = normalize(X)
nm = [kept_names[i] for i in keep]
Z = Xn - Xn.mean(1, keepdims=True)
M = (Xn > 0).astype(float)
ZM = Z * M
ss = (Z ** 2).sum(1)
den = np.sqrt(np.outer(ss, ss))
S = np.divide(ZM @ ZM.T, den, out=np.zeros((len(Xn),) * 2),
              where=(den != 0) & ((M @ M.T) > 0))
np.fill_diagonal(S, 0.0)
cs = S.sum(0)

rank_of = {}
for i, n in enumerate(p5):
    rank_of.setdefault(n, i)
sel = [i for i, n in enumerate(nm) if n in rank_of]
prank = np.array([rank_of[nm[i]] for i in sel], dtype=float)
ptop, pbot = set(p5[:K]), set(p5[-K:])

print(f'[5] 유사도·점수  유효 food {len(Xn)}')
print()
print('=' * 72)
print('결과 — 논문 순위(p5)와 대조')
print('=' * 72)
print(f"  {'both 처리':14s} {'E 부호':>16s} {'Spearman':>9s} {'Top30':>8s} {'Bot30':>8s}")
for both in ('pos', 'neg', 'zero'):
    E = build_E(both)
    u = Xn @ E
    p = np.divide(u @ S, cs, out=np.zeros_like(cs), where=cs != 0)
    rho = stats.spearmanr(-p[sel], prank).statistic
    o = np.argsort(-p)
    top = {nm[i] for i in o[:K]}
    bot = {nm[i] for i in o[-K:]}
    sig = f'+{int((E>0).sum())}/-{int((E<0).sum())}/0={int((E==0).sum())}'
    print(f'  {both:14s} {sig:>16s} {rho:+9.3f} {len(top & ptop):6d}/{K} '
          f'{len(bot & pbot):6d}/{K}')
print(f'\n  우연 기대값: Top30/Bot30 모두 약 {K*K/max(len(sel),1):.1f}')

print()
print('결손 요약')
print(f'  85종 중 F 에 데이터 있는 것   {int((X != 0).any(0).sum())}')
print(f'  85종 중 E 방향이 정해진 것    '
      f'{int((build_E("zero") != 0).sum())} (both=zero 기준)')
if miss:
    print(f'  매칭 실패 food {len(miss)}개: {miss[:5]}')
