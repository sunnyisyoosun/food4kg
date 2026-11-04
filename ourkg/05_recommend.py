"""05 — 논문 Algorithm 1 을 우리 KG 에 적용 (depression).

§4.2.1  D = E x F^T
§4.2.2  S = adjusted cosine similarity (식 1), P = D x S (식 2), Threshold·Top K
공식 구현(final.py) 경로를 따른다: PCA 없음, 행별 min-max, S 의 대각 0,
p 를 S 열합으로 나눔. 다만 음식이 14,000 규모라 식 (1) 을 벡터화했다
(공식 이중 루프와 같은 값, tools 로 소규모 대조 가능).

출력
  out/recommendation.csv   rank, food_key, food_name, food_group, score, n_compound
  out/recommendation.png   Fig.4(b) 대응 t-SNE
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT

K = int(os.environ.get('TOP_K', '30'))
PCA_N = int(os.environ.get('PCA_COMPONENTS', '0'))   # 0 = 공식 경로(PCA 없음)

print('[1/5] 행렬 구성')
long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
foods = pd.read_csv(os.path.join(OUT, 'foods.csv')).set_index('food_key')
E_df = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')

# 추천 대상 음식 범위.
# 논문 §4.2 의 135개 음식은 전부 분석 측정 기반(Foundation / SR Legacy / FNDDS)이다.
# branded_food 는 라벨 신고값이라 대부분의 성분이 결측(0)이고, 성분이 거의 없는
# 탄산수·단백질파우더 같은 항목이 유사도 단계에서 상위를 차지한다.
# KG 자체(04)는 FDC 전체를 담고, 추천 코호트만 여기서 제한한다.
# DATA_TYPES=all 로 branded 포함 실행 가능.
CURATED = ('foundation_food', 'sr_legacy_food', 'survey_fndds_food')
if os.environ.get('DATA_TYPES', 'curated') != 'all':
    foods = foods[foods['data_type'].isin(CURATED)]
    long = long[long['food_key'].isin(set(foods.index))]
    print(f'  분석 측정 기반 음식만: {len(foods):,}')

F = long.pivot_table(index='food_key', columns='kegg', values='amount_g', fill_value=0.0)
F = F.reindex(foods.index).fillna(0.0)
compounds = list(F.columns)
# §4.2.1 E: +1 완화 / -1 악화. 방향이 확정되지 않은 compound 는 0.
#   E_MODE=binary  논문 그대로의 +1/-1/0
#   E_MODE=shrunk  근거량으로 축소한 연속값 (기본, 02 단계 참조)
#   E_MODE=sig     BH q<0.05 인 compound 만 ±1
E_MODE = os.environ.get('E_MODE', 'shrunk')
if E_MODE == 'binary':
    col = E_df['e_binary']
elif E_MODE == 'sig':
    col = E_df['e_binary'].where(E_df['q'] < 0.05, 0.0)
else:
    col = E_df['e_shrunk']
e = np.array([col.get(c, 0.0) for c in compounds], dtype=float)
print(f'  E_MODE={E_MODE}')
print(f'  F {F.shape[0]:,} x {F.shape[1]}  /  E 비영 {int((e != 0).sum())} '
      f'(+{int((e > 0).sum())} / -{int((e < 0).sum())})')

# 정규화 — NORM=compound(기본) | row_minmax(공식 final.py)
#
# 공식 final.py 는 행별 min-max 를 쓴다. 음식 135개·성분 85개에서는 동작하지만
# 음식이 14,000 규모가 되면 무너진다: 음식마다 '그 음식의 최대 성분'이 1.0 이
# 되므로, 최대 성분이 우연히 E=+1 인 음식(칵테일의 ethanol, 음료의 sucrose)이
# 전부 상위로 올라온다. 음식 간 비교가 불가능해진다.
#
# 기본값은 compound(열)별 max 스케일링이다. 논문 §4.2.1 "Each element in this
# matrix represents the weight of a compound in the corresponding food sample"
# 와 Fig.4(c) "we normalize the compounds in the two groups of foods separately"
# 가 성분 축 정규화를 가리킨다. 공식 경로는 NORM=row_minmax 로 그대로 돌릴 수 있다.
NORM = os.environ.get('NORM', 'compound')
print(f'[2/5] 정규화 (NORM={NORM})')
X = F.values.astype(float)
if NORM == 'row_minmax':
    rng = X.max(axis=1) - X.min(axis=1)
    keep = rng > 0
    X = (X[keep] - X[keep].min(axis=1, keepdims=True)) / rng[keep][:, None]
else:
    colmax = X.max(axis=0)
    X = np.divide(X, colmax, out=np.zeros_like(X), where=colmax > 0)
    keep = X.sum(axis=1) > 0
    X = X[keep]
names = F.index[keep]
print(f'  유지된 음식 {X.shape[0]:,} (전부 0 인 행 제외 {int((~keep).sum())})')

if PCA_N:
    from sklearn.decomposition import PCA
    p = PCA(n_components=PCA_N)
    Xs = p.fit_transform(X)
    print(f'  PCA {PCA_N} 성분, 설명분산 {p.explained_variance_ratio_.sum():.3f}')
else:
    Xs = X

print('[3/5] D = E x F^T')
D = X @ e

print('[4/5] S = adjusted cosine (식 1) — 벡터화')
Xc = Xs - Xs.mean(axis=1, keepdims=True)
M = (Xs > 0).astype(float)                 # 공식 구현의 common 조건 (>0)
num = (Xc * M) @ (Xc * M).T                # 공통 성분만 더한 분자
nrm = np.sqrt((Xc ** 2).sum(axis=1))       # 분모는 전체 성분 (식 1 그대로)
den = np.outer(nrm, nrm)
S = np.divide(num, den, out=np.zeros_like(num), where=den > 0)
np.fill_diagonal(S, 0.0)
print(f'  S {S.shape}  비영 비율 {float((S != 0).mean()):.3f}')

print('[5/5] P = D x S, Top K')
# 식 (2) P_{i,j} = sum(D_i x S_j) 에는 정규화가 없다.
# 공식 final.py 는 여기에 p[i] /= sum(S[:,i]) 를 덧붙인다. adjusted cosine 은
# 음수를 가지므로 이 열합은 0 근처나 음수가 될 수 있다. 음식 135개에서는 드물었지만
# 14,000개에서는 성분이 적은 음식(칵테일류)의 열합이 ~15 까지 떨어져(중앙값 3,894)
# 나눗셈이 점수를 폭발시킨다. 기본값은 논문 식 (2) 그대로다.
SIM_NORM = os.environ.get('SIM_NORM', 'none')   # none(논문 식2) | colsum(공식 코드)
P = D @ S
if SIM_NORM == 'colsum':
    colsum = S.sum(axis=0)
    P = np.divide(P, colsum, out=np.zeros_like(P), where=colsum != 0)
print(f'  SIM_NORM={SIM_NORM}')

res = pd.DataFrame({'food_key': names, 'score': P})
res = res.join(foods[['food_name', 'food_group', 'n_compound', 'data_type']],
               on='food_key')
res = res.sort_values('score', ascending=False).reset_index(drop=True)
res.insert(0, 'rank', res.index + 1)
res.to_csv(os.path.join(OUT, 'recommendation.csv'), index=False)

print(f'\n=== Top {K} (추천) ===')
print(res.head(K)[['rank', 'food_name', 'food_group', 'score']].to_string(index=False))
print(f'\n=== Bottom {K} (비추천) ===')
print(res.tail(K)[['rank', 'food_name', 'food_group', 'score']].to_string(index=False))

print('\n=== 카테고리 분포 (논문 §4.2.3) ===')
top = res.head(K)['food_group'].value_counts()
bot = res.tail(K)['food_group'].value_counts()
cmp = pd.DataFrame({'Top': top, 'Bottom': bot}).fillna(0).astype(int)
print(cmp.sort_values('Top', ascending=False).to_string())

# Fig.4(b) 대응
idx = np.r_[res.index[:K], res.index[-K:]]
sub = res.loc[idx]
pos = {k: i for i, k in enumerate(names)}
emb = TSNE(n_components=2, random_state=0,
           perplexity=min(30, len(idx) - 1)).fit_transform(
    X[[pos[k] for k in sub['food_key']]])
plt.figure(figsize=(9, 7))
groups = sub['food_group'].unique()
cmap = plt.get_cmap('tab20')
for i, gname in enumerate(groups):
    m = (sub['food_group'] == gname).values
    rec = (sub['rank'] <= K).values
    plt.scatter(emb[m & rec, 0], emb[m & rec, 1], marker='o', s=70,
                color=cmap(i % 20), label=gname)
    plt.scatter(emb[m & ~rec, 0], emb[m & ~rec, 1], marker='^', s=70,
                color=cmap(i % 20))
plt.title(f'ourkg food recommendation for depression (o=Top{K}, ^=Bottom{K})')
plt.legend(fontsize=7, loc='best', ncol=2)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'recommendation.png'), dpi=140)
print(f'\n저장: {os.path.join(OUT, "recommendation.csv")}, recommendation.png')
