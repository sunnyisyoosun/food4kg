"""
Food4healthKG 재현 Step 2: 추천 알고리즘 실행 + 시각화
======================================================
final.py의 score() + cal_results() + tsne() 재현

Pipeline:
  1. Normalization
  2. D = weight × food^T (incidence score)
  3. Adjusted cosine similarity between foods
  4. P = D^T × S (recommendation probability)
  5. Top-K ranking
  6. T-SNE visualization
  7. PCA variance plot
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import math
import os
import warnings
warnings.filterwarnings('ignore')

OUT_DIR = '/home/yoosun/food_recom_w_paper/analyse'

# ============================================================
# 데이터 로드
# ============================================================
print("[1/7] 데이터 로드...")

food = pd.read_csv(os.path.join(OUT_DIR, 'food.csv'))
weight = pd.read_csv(os.path.join(OUT_DIR, 'weight.csv'))
foodname = pd.read_csv(os.path.join(OUT_DIR, 'foodname.csv'))

X_raw = food.values[:, :-1].astype(float)  # (132, 88) compound amounts
Y = food['type'].values                     # food category
we = weight.values                          # (8, 88) source weights
fnames = foodname['foodname'].tolist()
fdc_ids = foodname['fdc_id'].tolist()

n_foods, n_compounds = X_raw.shape
print(f"  Foods: {n_foods}, Compounds: {n_compounds}")

# ============================================================
# Normalization (final.py의 normalization 함수)
# ============================================================
print("[2/7] Normalization...")

def normalization(X):
    """각 행(food)별 min-max normalization"""
    result = []
    for i in range(X.shape[0]):
        row = X[i].copy()
        mn, mx = row.min(), row.max()
        rng = mx - mn
        if rng == 0:
            continue
        row = (row - mn) / rng
        result.append(row)
    return np.array(result)

X = normalization(X_raw)
print(f"  Normalized shape: {X.shape}")
# normalization에서 range=0인 행이 제거될 수 있으므로 인덱스 매핑
valid_idx = []
for i in range(X_raw.shape[0]):
    rng = X_raw[i].max() - X_raw[i].min()
    if rng > 0:
        valid_idx.append(i)

Y_valid = Y[valid_idx]
fnames_valid = [fnames[i] for i in valid_idx]
n1 = X.shape[0]
print(f"  Valid foods after norm: {n1} (dropped {n_foods - n1})")

# ============================================================
# Score 계산 (final.py의 score 함수 재현)
# ============================================================
print("[3/7] Recommendation score 계산...")

# Weight decomposition: 4 sources × 2 (pos, neg)
infer = we[0:2, :]   # inference
feacal = we[2:4, :]   # fecal
type1 = we[4:6, :]    # MENDA type1
type2 = we[6:8, :]    # MENDA type2

weightpos = np.array([1, 0])
weightneg = np.array([0, 1])

# D = weight^T × weight_direction → compound별 score
# 논문: we1 = infer^T × weightneg → negative weight 사용
we1 = np.dot(infer.T, weightneg)   # (88,)
we2 = np.dot(feacal.T, weightneg)
we3 = np.dot(type1.T, weightneg)
we4 = np.dot(type2.T, weightpos)   # type2는 positive

# u = X × we → food별 score
u1 = np.dot(X, we1)  # (n1,)
u2 = np.dot(X, we2)
u3 = np.dot(X, we3)
u4 = np.dot(X, we4)

print(f"  Score ranges:")
print(f"    u1 (infer):  [{u1.min():.3f}, {u1.max():.3f}]")
print(f"    u2 (fecal):  [{u2.min():.3f}, {u2.max():.3f}]")
print(f"    u3 (type1):  [{u3.min():.3f}, {u3.max():.3f}]")
print(f"    u4 (type2):  [{u4.min():.3f}, {u4.max():.3f}]")

# ============================================================
# Adjusted Cosine Similarity (논문 Eq.1)
# ============================================================
print("[4/7] Adjusted cosine similarity 계산...")

def adjusted_cosine(x, y):
    """final.py의 user_similarity_on_modified_cosine 재현"""
    common = [i for i in range(len(x)) if x[i] > 0 and y[i] > 0]
    if len(common) == 0:
        return 0.0
    avg_x = float(sum(x)) / len(x)
    avg_y = float(sum(y)) / len(y)
    
    numer = sum((x[j] - avg_x) * (y[j] - avg_y) for j in common)
    denom1 = sum((x[m] - avg_x) ** 2 for m in range(len(x)))
    denom2 = sum((y[n] - avg_y) ** 2 for n in range(len(y)))
    
    denom = math.sqrt(denom1 * denom2)
    if denom == 0:
        return 0.0
    return float(numer) / denom

Xt = X.T  # (88, n1) — column = food
S = np.zeros((n1, n1))

for i in range(n1):
    for j in range(i + 1, n1):
        sim = adjusted_cosine(Xt[:, i], Xt[:, j])
        S[i, j] = sim
        S[j, i] = sim
    if i % 20 == 0:
        print(f"    similarity: {i}/{n1}...")

print(f"  Similarity matrix: {S.shape}")
print(f"  Non-zero: {(S != 0).sum()}, Mean: {S[S != 0].mean():.4f}")

# ============================================================
# Recommendation probability P (논문 Eq.2)
# ============================================================
print("[5/7] Recommendation probability 계산...")

# P = u^T × S, normalized by column sum
def calc_prob(u, S):
    p = np.dot(u.T, S)
    col_sums = np.sum(S, axis=0)
    col_sums[col_sums == 0] = 1  # div by zero 방지
    p = p / col_sums
    return p

p1 = calc_prob(u1, S)  # inference-based
p2 = calc_prob(u2, S)  # fecal-based
p3 = calc_prob(u3, S)  # type1-based
p4 = calc_prob(u4, S)  # type2-based

# 결과 저장
df_result = pd.DataFrame({
    'infer': p1, 'faecal': p2, 'type1': p3, 'type4': p4
})
df_result.to_csv(os.path.join(OUT_DIR, 'acs04.csv'), index=False)
print(f"  acs04.csv 저장 완료")

# Ranking (infer 기준)
rank_idx = np.argsort(-p1)  # 내림차순
K = 30

print(f"\n  === Top {K} 추천 음식 (inference 기준) ===")
for i, idx in enumerate(rank_idx[:K]):
    print(f"    {i+1:2d}. {fnames_valid[idx]:<55s} score={p1[idx]:.4f}  type={Y_valid[idx]}")

print(f"\n  === 비추천 음식 (하위 {K}개) ===")
for i, idx in enumerate(rank_idx[-K:]):
    print(f"    {n1-K+i+1:2d}. {fnames_valid[idx]:<55s} score={p1[idx]:.4f}  type={Y_valid[idx]}")

# ============================================================
# RMSE / MAE (sources 간 비교)
# ============================================================
print("\n[6/7] Evaluation metrics...")

def RMSE(a, b):
    return math.sqrt(np.mean((a - b) ** 2))

def MAE(a, b):
    return np.mean(np.abs(a - b))

print(f"  Inference vs Fecal:  RMSE={RMSE(p1,p2):.4f}, MAE={MAE(p1,p2):.4f}")
print(f"  Inference vs Type1:  RMSE={RMSE(p1,p3):.4f}, MAE={MAE(p1,p3):.4f}")
print(f"  Inference vs Type2:  RMSE={RMSE(p1,p4):.4f}, MAE={MAE(p1,p4):.4f}")

# ============================================================
# Visualization
# ============================================================
print("\n[7/7] 시각화...")

# --- (a) PCA variance plot (논문 Fig.4a) ---
pca = PCA()
pca.fit(X)
cum_var = np.cumsum(pca.explained_variance_ratio_)

fig, axes = plt.subplots(1, 3, figsize=(24, 7))

ax = axes[0]
ax.bar(range(1, len(cum_var)+1), pca.explained_variance_ratio_, 
       alpha=0.6, label='individual explained variance')
ax.plot(range(1, len(cum_var)+1), cum_var, 'r-o', label='cumulative explained variance')
ax.set_xlabel('Principal components', fontsize=14)
ax.set_ylabel('Explained variance ratio', fontsize=14)
ax.set_title('(a) PCA Result', fontsize=16, fontweight='bold')
ax.legend(fontsize=11)
ax.set_xlim(0, min(20, len(cum_var)+1))

# PCA 5차원으로 축소 (논문: 80% variance 기준)
n_pca = np.argmax(cum_var >= 0.8) + 1
print(f"  PCA: {n_pca} components for 80% variance (cum={cum_var[n_pca-1]:.3f})")

X_pca = PCA(n_components=max(n_pca, 5)).fit_transform(X)

# --- (b) T-SNE visualization (논문 Fig.4b) ---
# Top K를 recommended(circle), 나머지를 not-recommended(triangle)로 표시
top_set = set(rank_idx[:K])

tsne = TSNE(n_components=2, learning_rate=100, init='pca', random_state=42)
X_tsne = tsne.fit_transform(X_pca)

target_map = {
    1.0: 'Dairy and Egg Products',
    15.0: 'Finfish and Shellfish Products',
    9.0: 'Fruits and Fruit Juices',
    11.0: 'Vegetables and Vegetable Products',
    12.0: 'Nut and Seed Products',
    16.0: 'Legumes and Legume Products',
    20.0: 'Cereal Grains and Pasta',
    2.0: 'Spices and Herbs',
    4.0: 'Fats and Oils',
    5.0: 'Poultry Products',
    6.0: 'Soups, Sauces, and Gravies',
    7.0: 'Sausages and Luncheon Meats',
    10.0: 'Pork Products',
    13.0: 'Beef Products',
    18.0: 'Baked Products',
    19.0: 'Sweets',
    25.0: 'Restaurant Foods',
}

ax = axes[1]
unique_types = sorted(set(Y_valid))
colors = {t: cm.rainbow(int(255 / max(len(unique_types), 1)) * i) 
          for i, t in enumerate(unique_types)}

for t in unique_types:
    label = target_map.get(t, f'Type {t}')
    # recommended (circles)
    mask_rec = [(Y_valid[j] == t and j in top_set) for j in range(n1)]
    mask_not = [(Y_valid[j] == t and j not in top_set) for j in range(n1)]
    
    rec_pts = X_tsne[mask_rec]
    not_pts = X_tsne[mask_not]
    
    if len(rec_pts) > 0:
        ax.scatter(rec_pts[:, 0], rec_pts[:, 1], c=[colors[t]], 
                  marker='o', s=80, label=label)
    if len(not_pts) > 0:
        ax.scatter(not_pts[:, 0], not_pts[:, 1], c=[colors[t]], 
                  marker='^', s=50, alpha=0.5)
        if len(rec_pts) == 0:
            ax.scatter([], [], c=[colors[t]], marker='^', label=label)

ax.set_title('(b) T-SNE: Categories of food on nutrition recommendation', 
             fontsize=14, fontweight='bold')
ax.legend(bbox_to_anchor=(1.05, 0), loc='lower left', fontsize=8)

# --- (c) Depression Nutrition Pyramid ---
ax = axes[2]

# 3단계 피라미드
rec_foods = [fnames_valid[i] for i in rank_idx[:K]]
mid_foods = [fnames_valid[i] for i in rank_idx[K:K*2]]
not_foods = [fnames_valid[i] for i in rank_idx[-K:]]

rec_types = [Y_valid[i] for i in rank_idx[:K]]
mid_types = [Y_valid[i] for i in rank_idx[K:K*2]]
not_types = [Y_valid[i] for i in rank_idx[-K:]]

from collections import Counter
rec_cat = Counter(rec_types)
mid_cat = Counter(mid_types)
not_cat = Counter(not_types)

# 피라미드 시각화
pyramid_data = [
    ('Not Recommended\n(Top tier)', not_cat, '#ff6b6b'),
    ('General Foods\n(Middle tier)', mid_cat, '#ffd93d'),
    ('Recommended\n(Bottom tier)', rec_cat, '#6bcb77'),
]

y_pos = 0
for label, cat_counter, color in pyramid_data:
    cats = [target_map.get(t, f'Type {t}') for t in cat_counter.keys()]
    counts = list(cat_counter.values())
    total = sum(counts)
    
    width = total / K * 0.8
    ax.barh(y_pos, width, height=0.8, color=color, edgecolor='white')
    
    cat_str = ', '.join([f"{target_map.get(t, '?')}({c})" 
                         for t, c in sorted(cat_counter.items(), key=lambda x: -x[1])[:3]])
    ax.text(width + 0.02, y_pos, cat_str, va='center', fontsize=7)
    ax.text(-0.05, y_pos, label, va='center', ha='right', fontsize=9, fontweight='bold')
    y_pos += 1

ax.set_xlim(-0.1, 1.5)
ax.set_title('(c) Depression Nutrition Pyramid', fontsize=14, fontweight='bold')
ax.axis('off')

plt.tight_layout()
fig_path = os.path.join(OUT_DIR, 'recommendation_results.png')
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
print(f"  저장: {fig_path}")

# ============================================================
# 요약
# ============================================================
print("\n" + "=" * 60)
print("✅ Step 2 완료: 추천 결과")
print("=" * 60)

rec_type_names = [target_map.get(Y_valid[i], '?') for i in rank_idx[:K]]
not_type_names = [target_map.get(Y_valid[i], '?') for i in rank_idx[-K:]]

print(f"\n  추천 식품 카테고리 분포 (Top {K}):")
for cat, cnt in Counter(rec_type_names).most_common():
    print(f"    {cat}: {cnt}")

print(f"\n  비추천 식품 카테고리 분포 (Bottom {K}):")
for cat, cnt in Counter(not_type_names).most_common():
    print(f"    {cat}: {cnt}")

print(f"""
  논문 기대 결과 vs 재현:
  ─────────────────────────────────────────
  추천:  과일/채소/주스가 상위 → {'✅' if 'Fruit' in str(rec_type_names) or 'Vegetable' in str(rec_type_names) else '❌'}
  비추천: 소시지/베이커리/스위트 상위 → {'✅' if 'Sausage' in str(not_type_names) or 'Beef' in str(not_type_names) else '❌'}
""")
