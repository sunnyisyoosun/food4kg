"""
Food4healthKG 추천 알고리즘 — 공식 final.py 충실 이식
======================================================
공식 repo(Food4healthKG/analyse/final.py)의 실행 경로를 그대로 재현한다.

공식 경로 (final.py __main__ 439-447행, 주석 처리되어 있던 부분):
    data = pd.read_csv('food.csv')
    X    = data.values[:, :-1]        # 마지막 열(type) 제외
    data = normalization(X)           # 행별 min-max, range==0인 행은 버림
    score(data)

공식 score() (final.py 43-110행):
    we1 = infer.T  @ [0,1]   -> weight.csv 1행
    we2 = feacal.T @ [0,1]   -> weight.csv 3행
    we3 = type1.T  @ [0,1]   -> weight.csv 5행
    we4 = type2.T  @ [1,0]   -> weight.csv 6행   (유일하게 pos)
    u   = X @ we
    S[i,j] = user_similarity_on_modified_cosine(X.T[:,i], X.T[:,j]),  S[i,i]=0
    p   = u.T @ S
    p[i] = p[i] / sum(S[:,i])

v2와의 차이 (v2는 논문 본문 해석, 이쪽은 공식 구현):
  - PCA 없음. similarity를 compound 원공간에서 계산.
  - E = pos - neg 가 아니라 weight.csv의 단일 행을 그대로 사용.
  - similarity의 common 조건이 != 0 이 아니라 > 0.

실행: python3 run_recommendation.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from collections import Counter
import math
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, 'analyse')

# E 정의. 논문 §4.2.1:
#   "We create an incidence matrix, denoted as E, in which a value of 1
#    indicates a positive relationship between a compound and depression
#    (relieving the disease), and a value of -1 indicates a negative
#    relationship (causing the disease)."
# 즉 E는 하나의 행렬에 +1과 -1이 함께 들어간다 -> E = pos - neg.
#
# 공식 final.py는 weight.csv의 '한 행'만 고르므로(weightpos/weightneg),
# 어느 행이 pos인지 알아야 하는데 공식 weight.csv가 배포되지 않아 확정 불가였다
# (구 FLIP_SIGN 모호성). 논문 정의를 쓰면 pos/neg를 둘 다 쓰므로 모호성이 없다.
# 우리 weight.csv의 행 규약은 reconstruct.py:334-336에서 우리가 직접 정한다
# (짝수 행 = pos, 홀수 행 = neg).
#
# 부수 효과: 한 행만 쓰면 negative 연관이 점수에 전혀 반영되지 않아
# '나쁜 성분이 많은' 음식이 감점되지 않는다.
#
#   'paper'    : E = pos - neg          (논문 §4.2.1, 기본값)
#   'official' : E = 단일 행            (공식 final.py 재현용)
E_MODE = os.environ.get('E_MODE', 'paper')

K = 30

# ============================================================
# 공식 final.py 378-406행 이식
# ============================================================
def normalization(X):
    """행별 min-max. range==0인 행은 결과에서 제외."""
    n1, n2 = X.shape
    out, kept = [], []
    for x in range(n1):
        rows = X[x].astype(float).copy()
        minVals, maxVals = rows.min(), rows.max()
        ranges = maxVals - minVals
        if ranges == 0:
            continue
        out.append((rows - minVals) / ranges)
        kept.append(x)
    return np.array(out), kept


# ============================================================
# 공식 final.py 112-128행 이식
# ============================================================
def user_similarity_on_modified_cosine(x, y):
    common = [i for i in range(len(x)) if x[i] > 0 and y[i] > 0]
    if len(common) == 0:
        return 0
    average1 = float(sum(x)) / len(x)
    average2 = float(sum(y)) / len(y)
    multiply_sum = sum((x[j] - average1) * (y[j] - average2) for j in common)
    pow_sum_1 = sum(math.pow(x[m] - average1, 2) for m in range(len(x)))
    pow_sum_2 = sum(math.pow(y[n] - average2, 2) for n in range(len(y)))
    denom = math.sqrt(pow_sum_1 * pow_sum_2)
    if denom == 0:
        return 0
    return float(multiply_sum) / denom


# ============================================================
# 데이터 로드 — 공식 __main__ 경로
# ============================================================
print("[1/6] 데이터 로드 (공식 경로)...")

food = pd.read_csv(os.path.join(OUT_DIR, 'food.csv'))
weight = pd.read_csv(os.path.join(OUT_DIR, 'weight.csv'))
foodname = pd.read_csv(os.path.join(OUT_DIR, 'foodname.csv'))

# 공식: array = data.values; X = array[:, :-1]  (마지막 열 type 제외)
array = food.values
X_raw = array[:, :-1].astype(float)
Y_all = food['type'].values
we = weight.values
fnames_all = foodname['foodname'].tolist()

n_foods, n_compounds = X_raw.shape
print(f"  food.csv: {n_foods} foods × {n_compounds} compounds")
print(f"  weight.csv: {we.shape}")
assert n_compounds == we.shape[1], \
    f"food.csv 열({n_compounds})과 weight.csv 열({we.shape[1]}) 불일치"

# ============================================================
# 정규화 — 공식과 동일
# ============================================================
print("\n[2/6] normalization (행별 min-max)...")

Xn, kept = normalization(X_raw)
Y = Y_all[kept]
fnames = [fnames_all[i] for i in kept]
n1 = Xn.shape[0]
print(f"  유효 food: {n1} (range==0으로 제외: {n_foods - n1})")

# ============================================================
# 가중치 벡터 — 공식 score() 57-66행
# ============================================================
print("\n[3/6] 가중치 벡터 (공식 score() 이식)...")

if E_MODE == 'paper':
    # 논문 §4.2.1: 각 소스의 (pos, neg) 쌍에서 E = pos - neg
    we1, we2, we3, we4 = (we[k] - we[k + 1] for k in (0, 2, 4, 6))
else:
    # 공식 final.py score(): 각 소스에서 단일 행만 사용
    weightpos, weightneg = np.array([1, 0]), np.array([0, 1])
    we1 = np.dot(we[0:2, ].T, weightneg)
    we2 = np.dot(we[2:4, ].T, weightneg)
    we3 = np.dot(we[4:6, ].T, weightneg)
    we4 = np.dot(we[6:8, ].T, weightpos)

for nm, w in [('we1(infer)', we1), ('we2(faecal)', we2),
              ('we3(type1)', we3), ('we4(type2)', we4)]:
    print(f"  {nm:14s} +{int((w > 0).sum()):3d} / -{int((w < 0).sum()):3d} / "
          f"0={int((w == 0).sum()):3d}")

u1 = np.dot(Xn, we1)
u2 = np.dot(Xn, we2)
u3 = np.dot(Xn, we3)
u4 = np.dot(Xn, we4)

# ============================================================
# similarity — compound 원공간, 공식과 동일
# ============================================================
print("\n[4/6] modified cosine similarity (compound 원공간)...")

Xt = np.transpose(Xn)
S = np.zeros((n1, n1))
for i in range(n1):
    S[i, i] = 0
    for j in range(i + 1, n1):
        s = user_similarity_on_modified_cosine(Xt[:, i], Xt[:, j])
        S[i, j] = s
        S[j, i] = s
    if i % 20 == 0:
        print(f"    i = {i}/{n1}")

nz = S[S != 0]
print(f"  S: {S.shape}, non-zero={len(nz)}, mean={nz.mean():.4f}")

# ============================================================
# 추천 점수 — 공식 score() 95-101행
# ============================================================
print("\n[5/6] 추천 점수...")

col_sums = np.sum(S, axis=0)

def to_prob(u):
    p = np.dot(u.T, S).astype(float)
    for i in range(len(p)):
        cs = col_sums[i]
        p[i] = p[i] / cs if cs != 0 else 0.0
    return p

p1, p2, p3, p4 = to_prob(u1), to_prob(u2), to_prob(u3), to_prob(u4)

pd.DataFrame({'infer': p1, 'faecal': p2,
              'type1': p3, 'type4': p4}
             ).to_csv(os.path.join(OUT_DIR, 'acs04.csv'), index=False)

rank_idx = np.argsort(-p1)

target_map = {
    1.0: 'Dairy and Egg', 15.0: 'Fish/Shellfish', 9.0: 'Fruits/Juices',
    11.0: 'Vegetables', 12.0: 'Nuts/Seeds', 16.0: 'Legumes',
    20.0: 'Cereal/Pasta', 4.0: 'Fats/Oils', 5.0: 'Poultry',
    6.0: 'Soups/Sauces', 7.0: 'Sausages', 10.0: 'Pork',
    13.0: 'Beef', 18.0: 'Baked', 19.0: 'Sweets', 25.0: 'Restaurant',
}

print(f"\n  === Top {K} 추천 음식 ===")
for i, idx in enumerate(rank_idx[:K]):
    print(f"    {i+1:2d}. {fnames[idx]:<55s} score={p1[idx]:.4f}  "
          f"{target_map.get(Y[idx], Y[idx])}")

print(f"\n  === 비추천 음식 (하위 {K}개) ===")
for i, idx in enumerate(rank_idx[-K:]):
    print(f"    {n1-K+i+1:2d}. {fnames[idx]:<55s} score={p1[idx]:.4f}  "
          f"{target_map.get(Y[idx], Y[idx])}")

def RMSE(a, b): return math.sqrt(np.mean((a - b) ** 2))
def MAE(a, b):  return np.mean(np.abs(a - b))

print(f"\n  Evaluation (논문에 없는 부가 지표):")
print(f"    Inference vs Fecal:  RMSE={RMSE(p1,p2):.4f}, MAE={MAE(p1,p2):.4f}")
print(f"    Inference vs Type1:  RMSE={RMSE(p1,p3):.4f}, MAE={MAE(p1,p3):.4f}")
print(f"    Inference vs Type2:  RMSE={RMSE(p1,p4):.4f}, MAE={MAE(p1,p4):.4f}")

# ============================================================
# 시각화
# ============================================================
print("\n[6/6] 시각화...")

fig, axes = plt.subplots(1, 3, figsize=(24, 7))

# (a) PCA — 논문 Fig.4(a). 점수 계산 경로에는 쓰이지 않고 진단용.
pca = PCA()
pca.fit(Xn)
cum_var = np.cumsum(pca.explained_variance_ratio_)
n80 = int(np.argmax(cum_var >= 0.8) + 1)
m = min(20, len(cum_var))
ax = axes[0]
ax.bar(range(1, m+1), pca.explained_variance_ratio_[:m], alpha=0.6, label='individual')
ax.plot(range(1, m+1), cum_var[:m], 'r-o', label='cumulative')
ax.axhline(0.8, color='k', ls='--', alpha=0.5)
ax.axvline(n80, color='g', ls='--', alpha=0.5, label=f'80% @ {n80} comp')
ax.set_xlabel('Principal components'); ax.set_ylabel('Explained variance ratio')
ax.set_title('(a) PCA (diagnostic only, not used in scoring)', fontweight='bold')
ax.legend()
print(f"  PCA 80% 도달: {n80} components (논문: 5)")

# (b) T-SNE — 공식 tsne(): init='pca', learning_rate=100
ax = axes[1]
X_tsne = TSNE(n_components=2, learning_rate=100, init='pca',
              random_state=42).fit_transform(Xn)
top_set = set(rank_idx[:K].tolist())
uniq = sorted(set(Y))
for t in uniq:
    color = cm.rainbow(int(255 / max(len(uniq), 1)) * uniq.index(t))
    label = target_map.get(t, f'Type {t}')
    rec = [j for j in range(n1) if Y[j] == t and j in top_set]
    nrec = [j for j in range(n1) if Y[j] == t and j not in top_set]
    if rec:
        ax.scatter(X_tsne[rec, 0], X_tsne[rec, 1], c=[color], marker='o', s=80, label=label)
    if nrec:
        ax.scatter(X_tsne[nrec, 0], X_tsne[nrec, 1], c=[color], marker='^', s=50, alpha=0.4)
        if not rec:
            ax.scatter([], [], c=[color], marker='^', label=label)
ax.set_title('(b) T-SNE (raw compound space)', fontweight='bold')
ax.legend(bbox_to_anchor=(1.05, 0), loc='lower left', fontsize=7)

# (c) 카테고리 분포
ax = axes[2]
rec_c = Counter(Y[i] for i in rank_idx[:K])
not_c = Counter(Y[i] for i in rank_idx[-K:])
cats = sorted(set(rec_c) | set(not_c))
xp = np.arange(len(cats))
ax.barh(xp + 0.2, [rec_c.get(c, 0) for c in cats], 0.4, color='#6bcb77', label='Recommended')
ax.barh(xp - 0.2, [not_c.get(c, 0) for c in cats], 0.4, color='#ff6b6b', label='Not recommended')
ax.set_yticks(xp)
ax.set_yticklabels([target_map.get(c, '?')[:12] for c in cats], fontsize=8)
ax.set_title('(c) Category Distribution', fontweight='bold')
ax.legend()

plt.tight_layout()
fig_path = os.path.join(OUT_DIR, 'recommendation_results_official.png')
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
print(f"  저장: {fig_path}")

# ============================================================
# 요약
# ============================================================
print(f"\n{'='*60}")
print(f"✅ 완료 (E_MODE={E_MODE})")
print(f"{'='*60}")

rec_names = Counter(target_map.get(Y[i], '?') for i in rank_idx[:K])
not_names = Counter(target_map.get(Y[i], '?') for i in rank_idx[-K:])

print(f"\n  추천 식품 카테고리 분포 (Top {K}):")
for c, n in rec_names.most_common():
    print(f"    {c}: {n}")
print(f"\n  비추천 식품 카테고리 분포 (Bottom {K}):")
for c, n in not_names.most_common():
    print(f"    {c}: {n}")

paper_rec = {'Vegetables', 'Fruits/Juices', 'Fish/Shellfish'}
paper_not = {'Sausages', 'Baked', 'Sweets', 'Beef'}
print(f"\n  논문 대비:")
print(f"    추천 일치:   {paper_rec & set(rec_names)}")
print(f"    추천 누락:   {paper_rec - set(rec_names)}")
print(f"    비추천 일치: {paper_not & set(not_names)}")
print(f"    비추천 누락: {paper_not - set(not_names)}")
