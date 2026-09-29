"""
논문 기준 검증·개선 (REPRODUCTION.md §16)
==========================================
모든 판정 기준은 논문에서 가져왔고 실행 전에 고정했다.

실행
    python3 tools/paper.py units     §16.1 논문 F 의 단위 규약 역산
    python3 tools/paper.py claims    §16.2 논문 주장 C1~C6 검정 (+ 논문 내부 C3, C4 PCA)
    python3 tools/paper.py invert    §16.3 논문 순위 → E 역추정, held-out
    python3 tools/paper.py improve   §16.4 논문 기반 개선판 V1~V4 (재현과 분리)
    python3 tools/paper.py all

------------------------------------------------------------------------
units — 논문 F 의 단위 규약
  FDC 원값은 compound 마다 단위가 다르다 (G 52 / MG 24 / UG 8 / IU 1).
  논문 §3.1 "nutrients ... quantified in weight, enabling effective calculation
  and comparison" 은 공통 무게 단위를 시사하나 환산을 명시하지 않는다.
  1. 논문 heatmap.xlsx 행과 우리 food 를 **G 열만으로** 매칭한다
     (G 열끼리의 비율은 어떤 규약에서도 같다).
  2. 매칭 쌍에서 (B_j/B_k)/(X_j/X_k), j∈MG|UG|IU, k∈G 를 구하면 행 min-max
     (min=0) 가 스케일만 바꾸므로 그 값이 논문의 환산 계수다.
  3. 규약별 F 를 논문 heatmap 과 행 코사인으로 비교한다.
  원단위 사본은 reconstruct.py 가 analyse/food_rawunit.csv 로 남긴다.

claims — 논문 주장 단위 검증
  C1a §4.2.3  추천 = fish and shellfish, fruits, vegetables
  C1b §4.2.3  비추천 = sausage products, baked products, sweets
  C2  Fig. 5  피라미드 3층 (Veg·Fruit < Dairy/Egg·Fish·Soups·Fats < Baked·Beef·Sausages·Pork)
  C3  §4.2.3  추천30 vs 비추천30: 탄수화물·비타민 추천↑, 미량원소·다량영양소 비추천↑,
              아미노산·지질 비유의
  C4  §4.2.1  PCA(Xn ⊙ E) 80% 도달 5성분
  C5  Fig. 4(b)  추천/비추천이 성분 공간에서 분리 (5-fold 로지스틱 acc >= 0.80)
  C6  §4.2.3  양파(D-glucose 예시)가 상위 30
  판정: 단측 p<0.05 (비유의 항목은 양측 p>=0.05). 무작위 순위 2,000회 통과율을 함께 본다.

invert — 논문 순위 → E 역추정 (held-out)
  p = (Xn E) S / colsum(S) = A E 는 E 에 선형이다. 논문 순위를 [-1,1] 로 옮겨
  bounded ridge 로 E 를 푼다. gold 9종은 부호 제약. λ 는 학습 반쪽 5-fold 로만 고른다.
  음식 50/50 분할 200회, 보지 않은 반쪽에서 Spearman. 판정: 1비트 기준선 초과 여부.
  데이터 조합: ours(재구성 F + p5), paper(heatmap F + 행 순서).
  부가: gold 제약 없이 부트스트랩 200회 → 논문 순위가 논문 부호를 함의하는가.

improve — 논문 기반 개선판 (재현 결과에 넣지 않는다)
  R   재현 기준    현재 E, 공식 점수식
  V1  근거 가중 E  §3.1 의 MENDA 5,675 entries study 수로 |E| = |pos−neg|/(pos+neg+2).
                   방향은 R 그대로. 카운트 없는 compound 는 conf 중앙값.
  V2  장내미생물 경로  제목·§1 의 전제, Fig. 2 hasMetabolites→hasAssociation.
                   Query 2 경로(in_Q2)가 없는 compound 는 E=0.
  V3  유사도 제거   p = Xn E (Algorithm 1 의 S 단계 기여 확인)
  V4  V1 + V2
  (보조) AFS  LaChance & Ramsey (2018) Antidepressant Food Score 의 12 영양소 중
              85 compound 에 있는 11종(B6 없음), %DV/100g(상한 100%) 평균. 논문 밖 기준.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment, lsq_linear

import core
import gold

K = core.K
ALPHA = 0.05


def _groups(cols):
    grp = dict(zip(core.paper85().kegg, core.paper85().group))
    return [grp.get(c, '?') for c in cols]


def _mwu_greater(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.nan
    return stats.mannwhitneyu(a, b, alternative='greater').pvalue


def _paper_score(d):
    """p5 순위를 점수로 (높을수록 추천). p5 에 없는 food 는 NaN."""
    idx, rank, *_ = core.paper_ranking(d.names)
    s = np.full(len(d.names), np.nan)
    s[idx] = -rank
    return s


# ======================================================================
# units
# ======================================================================
TO_G = {'G': 1.0, 'MG': 1e-3, 'UG': 1e-6, 'IU': 1e-6}   # IU: 논문 역산값
MATCH_COS = 0.95
UNITS_CSV = os.path.join(core.OUT, 'compound_units.csv')


def compound_units(cols):
    """compound -> 주 단위 (행 수가 가장 많은 단위). analyse/compound_units.csv 캐시."""
    if os.path.exists(UNITS_CSV):
        u = pd.read_csv(UNITS_CSV)
        return dict(zip(u.kegg, u.unit))
    acc = []
    for ch in pd.read_csv(os.path.join(core.BASE, 'food_nutrient.csv'),
                          usecols=['nutrient_kegg', 'nutrient_unit'],
                          chunksize=2_000_000):
        acc.append(ch[ch.nutrient_kegg.isin(cols)]
                   .groupby(['nutrient_kegg', 'nutrient_unit']).size())
    cnt = pd.concat(acc).groupby(level=[0, 1]).sum().reset_index(name='n')
    top = (cnt.sort_values('n', ascending=False).drop_duplicates('nutrient_kegg')
           .rename(columns={'nutrient_kegg': 'kegg', 'nutrient_unit': 'unit'}))
    top[['kegg', 'unit']].to_csv(UNITS_CSV, index=False)
    return dict(zip(top.kegg, top.unit))


def units():
    food = pd.read_csv(os.path.join(core.OUT, 'food_rawunit.csv'))
    cols = [c for c in food.columns if c.startswith('C')]
    X = food[cols].values.astype(float)
    B, keggs, *_ = core.heatmap()
    assert keggs == cols, 'heatmap 열 순서가 food.csv 와 다르다'
    um = compound_units(cols)
    U = np.array([um.get(c) or um.get(next(
        (a for a in core.kegg_alias.incidence_keys(c) if a in um), c), 'G')
        for c in cols])
    print('단위 분포 (85 compound):',
          {str(k): int(v) for k, v in zip(*np.unique(U, return_counts=True))})

    jG = np.where(U == 'G')[0]
    C = core.cos_matrix(B[:, jG], X[:, jG])
    r, c = linear_sum_assignment(-C)
    nz = ((B[r][:, jG] > 0).sum(1) >= 3) & ((X[c][:, jG] > 0).sum(1) >= 3)
    keep = (C[r, c] > MATCH_COS) & nz
    r, c = r[keep], c[keep]
    print(f'\n[1] G 열만으로 매칭: cos>{MATCH_COS} 인 쌍 {len(r)}개')

    print('\n[2] 논문 환산 계수  (B_j/B_k)/(X_j/X_k), k∈G   '
          '1=원단위 혼용, 1e-3(MG)/1e-6(UG)=g 환산')
    for u in ('MG', 'UG', 'IU'):
        ratios = [np.log10((B[bi, j] / B[bi, k]) / (X[xi, j] / X[xi, k]))
                  for bi, xi in zip(r, c) for j in np.where(U == u)[0]
                  if B[bi, j] > 0 and X[xi, j] > 0
                  for k in jG if B[bi, k] > 0 and X[xi, k] > 0]
        if ratios:
            q = np.percentile(ratios, [25, 50, 75])
            print(f'    {u:3s} log10 중앙 {q[1]:+.2f}  IQR [{q[0]:+.2f}, {q[2]:+.2f}]'
                  f'  n={len(ratios)}')

    print('\n[3] 규약별 F vs 논문 heatmap (85열 행 코사인)')
    Xg = X * np.array([TO_G[u] for u in U])
    for lbl, V in (('원단위 (UNIT_MODE=raw)', X), ('g 환산 (기본값)', Xg)):
        Vn = core.rowminmax(V)
        cc = np.array([core.cos_matrix(B[[bi]], Vn[[xi]])[0, 0]
                       for bi, xi in zip(r, c)])
        full = core.cos_matrix(B, Vn)
        rr, ccol = linear_sum_assignment(-full)
        print(f'    {lbl:24s} 매칭쌍 평균 {cc.mean():.3f}  >0.9 '
              f'{int((cc > 0.9).sum())}/{len(cc)}  | 전체 헝가리안 {full[rr, ccol].mean():.3f}')

    print('\n[4] 행 최댓값을 차지하는 compound 그룹')
    grp = _groups(cols)
    for lbl, M in (('논문 heatmap', B), ('우리 원단위', core.rowminmax(X)),
                   ('우리 g 환산', core.rowminmax(Xg))):
        print(f'    {lbl:12s}', pd.Series([grp[j] for j in M.argmax(1)])
              .value_counts().to_dict())


# ======================================================================
# claims
# ======================================================================
REC_TEXT = {15.0, 9.0, 11.0}           # C1a: Fish, Fruits, Vegetables
NOT_TEXT = {7.0, 18.0, 19.0}           # C1b: Sausages, Baked, Sweets
TIER = {9.0: 2, 11.0: 2, 1.0: 1, 15.0: 1, 6.0: 1, 4.0: 1,
        18.0: 0, 13.0: 0, 7.0: 0, 10.0: 0}
C3_DIR = {'Carbohydrates': 'rec', 'Vitamins and cofactors': 'rec',
          'Trace Elements': 'not', 'Macronutrient': 'not',
          'Amino acid': 'ns', 'Lipids': 'ns'}
CLAIMS = ['C1a', 'C1b', 'C2', 'C3', 'C5', 'C6']


def _top_bot(s):
    ok = np.where(~np.isnan(s))[0]
    order = ok[np.argsort(-s[ok])]
    return order[:K], order[-K:]


def _c1(s, Y, cats, want):
    ok = ~np.isnan(s)
    ins = np.array([y in cats for y in Y]) & ok
    out = ~ins & ok
    p = (_mwu_greater(s[ins], s[out]) if want == 'high'
         else _mwu_greater(s[out], s[ins]))
    return p, p < ALPHA


def _c2(s, Y):
    t = np.array([TIER.get(y, np.nan) for y in Y])
    m = ~np.isnan(s) & ~np.isnan(t)
    r = stats.spearmanr(t[m], s[m])
    p = r.pvalue / 2 if r.statistic > 0 else 1 - r.pvalue / 2
    return (r.statistic, p), p < ALPHA


def _c3_rows(top_rows, bot_rows, groups):
    res = {}
    for g, want in C3_DIR.items():
        j = [i for i, c in enumerate(groups) if c == g]
        a, b = top_rows[:, j].mean(1), bot_rows[:, j].mean(1)
        if want == 'rec':
            p = _mwu_greater(a, b); ok = p < ALPHA
        elif want == 'not':
            p = _mwu_greater(b, a); ok = p < ALPHA
        else:
            p = stats.mannwhitneyu(a, b).pvalue; ok = p >= ALPHA
        res[g] = (a.mean(), b.mean(), p, ok)
    return res


def _c3(s, Xn, groups):
    top, bot = _top_bot(s)
    res = _c3_rows(Xn[top], Xn[bot], groups)
    return res, all(v[3] for v in res.values())


def _c5(s, Xn):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    top, bot = _top_bot(s)
    acc = cross_val_score(LogisticRegression(max_iter=2000),
                          np.vstack([Xn[top], Xn[bot]]),
                          np.r_[np.ones(K), np.zeros(K)], cv=5).mean()
    return acc, acc >= 0.80


def _c6(s, names):
    top = set(_top_bot(s)[0])
    on = [i for i, n in enumerate(names)
          if 'onion' in n.lower() and not np.isnan(s[i])]
    inside = [i for i in on if i in top]
    return (len(inside), len(on)), len(on) > 0 and len(inside) == len(on)


def c4_pca(Xn, E):
    """§4.2.1: incidence 행렬(Xn ⊙ E)의 80% 분산 도달 성분 수."""
    from sklearn.decomposition import PCA
    out = {}
    for lbl, M in (('Xn*E', Xn * E), ('Xn', Xn)):
        cum = np.cumsum(PCA().fit(M).explained_variance_ratio_)
        out[lbl] = int(np.searchsorted(cum, 0.80) + 1)
    return out


def evaluate_claims(s, d, groups):
    return {'C1a': _c1(s, d.Y, REC_TEXT, 'high'),
            'C1b': _c1(s, d.Y, NOT_TEXT, 'low'),
            'C2': _c2(s, d.Y),
            'C3': _c3(s, d.Xn, groups),
            'C5': _c5(s, d.Xn),
            'C6': _c6(s, d.names)}


def _cell(k, v):
    val, ok = v
    mark = 'PASS' if ok else 'fail'
    if k == 'C2':
        return f'{mark} rho={val[0]:+.2f}'
    if k == 'C3':
        return f'{mark} {sum(x[3] for x in val.values())}/6'
    if k == 'C5':
        return f'{mark} acc={val:.2f}'
    if k == 'C6':
        return f'{mark} {val[0]}/{val[1]}'
    return f'{mark} p={val:.3g}'


def claims(n_random=2000, seed=0):
    d = core.Data.load()
    groups = _groups(d.cols)
    S = {'paper': _paper_score(d), 'ours': d.score(d.E),
         # 동률 깨기(고정)
         '1bit': core.one_bit(d.Y) + 1e-9 * np.arange(len(d.Y))[::-1]}
    res = {n: evaluate_claims(s, d, groups) for n, s in S.items()}

    rng = np.random.default_rng(seed)
    passes = dict.fromkeys(CLAIMS, 0)
    for _ in range(n_random):
        r = evaluate_claims(rng.permutation(len(d.names)).astype(float), d, groups)
        for k in CLAIMS:
            passes[k] += r[k][1]

    print('논문 주장 단위 검증  (단측 p<0.05 / C5 acc>=0.80)')
    print(f'{"":6s}' + ''.join(f'{n:>20s}' for n in S) + f'{"random 통과율":>16s}')
    for k in CLAIMS:
        print(f'{k:6s}' + ''.join(f'{_cell(k, res[n][k]):>20s}' for n in S)
              + f'{passes[k] / n_random:>15.1%}')
    print(f'{"통과":6s}' + ''.join(
        f'{f"{sum(res[n][k][1] for k in CLAIMS)}/{len(CLAIMS)}":>20s}' for n in S))

    def show(rows):
        for g, (a, b, p, ok) in rows.items():
            print(f'    {g:24s} {a:.3f} / {b:.3f}  논문={C3_DIR[g]:3s} '
                  f'p={p:.3g}  {"ok" if ok else "X"}')

    print('\n[C3 상세] 그룹 평균 (추천30 / 비추천30)')
    for n in S:
        print(f'  {n}')
        show(res[n]['C3'][0])
    B, keggs, *_ = core.heatmap()
    print('  논문 내부: heatmap.xlsx 상위30 / 하위30 행 (논문 자신의 데이터)')
    show(_c3_rows(B[:K], B[-K:], _groups(keggs)))

    pc = c4_pca(d.Xn, d.E)
    print(f'\n[C4] PCA 80% 도달 — Xn*E: {pc["Xn*E"]}, Xn: {pc["Xn"]}  (논문 5)  '
          f'{"PASS" if pc["Xn*E"] == 5 else "fail"}')


# ======================================================================
# invert
# ======================================================================
LAMBDAS = [1e-3, 1e-2, 1e-1, 1, 10]
N_SPLIT = 200
N_BOOT = 200


def _design(Xn, with_sim=True):
    if not with_sim:
        return Xn
    S, cs = core.similarity(Xn)
    return np.divide(S.T @ Xn, cs[:, None], out=np.zeros_like(Xn),
                     where=cs[:, None] != 0)


def _bounds(cols, use_gold):
    lo, hi = np.full(len(cols), -np.inf), np.full(len(cols), np.inf)
    if use_gold:
        for j, c in enumerate(cols):
            if c in gold.GOLD:
                if gold.GOLD[c][0] == '+':
                    lo[j] = 0
                else:
                    hi[j] = 0
    return lo, hi


def _fit(A, t, lam, lo, hi):
    """열 스케일을 맞춘 bounded ridge."""
    sc = A.std(0)
    sc[sc == 0] = 1
    As = A / sc
    n = As.shape[1]
    M = np.vstack([np.c_[As, np.ones(len(As))],
                   np.c_[np.sqrt(lam) * np.eye(n), np.zeros(n)]])
    r = lsq_linear(M, np.r_[t, np.zeros(n)],
                   bounds=(np.r_[lo * sc, -np.inf], np.r_[hi * sc, np.inf]))
    return r.x[:n] / sc


def _pick_lambda(A, t, lo, hi, rng):
    folds = np.array_split(rng.permutation(len(t)), 5)
    best, bl = -np.inf, LAMBDAS[0]
    for lam in LAMBDAS:
        rs = []
        for f in folds:
            tr = np.setdiff1d(np.arange(len(t)), f)
            rs.append(stats.spearmanr(A[f] @ _fit(A[tr], t[tr], lam, lo, hi),
                                      t[f]).statistic)
        if np.nanmean(rs) > best:
            best, bl = np.nanmean(rs), lam
    return bl


def _invert_one(label, Xn, rank, cols, Y=None, E_ref=None):
    r_ = stats.rankdata(rank)
    t = 1 - 2 * (r_ - 1) / (len(r_) - 1)          # 1 = 최상위
    base = core.one_bit(Y) if Y is not None else None
    print(f'\n### {label}  (food {len(t)}, compound {len(cols)})')
    for with_sim in (True, False):
        A = _design(Xn, with_sim)
        lo, hi = _bounds(cols, use_gold=True)
        rng = np.random.default_rng(0)
        out, outb = [], []
        for _ in range(N_SPLIT):
            perm = rng.permutation(len(t))
            tr, te = perm[:len(t) // 2], perm[len(t) // 2:]
            e = _fit(A[tr], t[tr], _pick_lambda(A[tr], t[tr], lo, hi, rng), lo, hi)
            out.append(stats.spearmanr(A[te] @ e, t[te]).statistic)
            if base is not None:
                outb.append(stats.spearmanr(base[te], t[te]).statistic)
        out = np.array(out)
        tag = 'p = A E (공식식)' if with_sim else 'u = Xn E (유사도 없음)'
        line = (f'  {tag:22s} held-out 중앙 {np.median(out):+.3f} '
                f'[{np.percentile(out, 5):+.3f}, {np.percentile(out, 95):+.3f}]')
        if outb:
            outb = np.array(outb)
            line += (f'   1비트 {np.median(outb):+.3f}, 초과 분할 {(out > outb).mean():.0%}'
                     f'  {"식별됨" if np.median(out) > np.median(outb) else "식별 안 됨"}')
        print(line)
        if E_ref is not None and with_sim:
            print(f'  {"(참고) 현재 E":22s} 전체 Spearman '
                  f'{stats.spearmanr(A @ E_ref, t).statistic:+.3f}')

    # 논문 순위가 논문 부호를 함의하는가 (gold 제약 없음, 부트스트랩)
    A = _design(Xn, True)
    lo, hi = _bounds(cols, use_gold=False)
    rng = np.random.default_rng(1)
    lam = _pick_lambda(A, t, lo, hi, rng)
    frac = np.array([_fit(A[b], t[b], lam, lo, hi)
                     for b in (rng.integers(0, len(t), len(t))
                               for _ in range(N_BOOT))]) > 0
    frac = frac.mean(0)
    ok = n = 0
    print(f'  [부호 역추정, gold 제약 없음, λ={lam}]')
    for j, c in enumerate(cols):
        if c in gold.GOLD:
            g, nm, _ = gold.GOLD[c]
            est = '+' if frac[j] >= 0.9 else ('-' if frac[j] <= 0.1 else '?')
            if est != '?':
                n += 1
                ok += est == g
            print(f'    {c} {nm:22s} 논문 {g}  P(+)={frac[j]:.2f} → {est}')
    print(f'    안정 추정 {n}개 중 논문 부호 일치 {ok}')
    if E_ref is not None:
        stable = (frac >= 0.9) | (frac <= 0.1)
        m = stable & (E_ref != 0)
        est = np.where(frac >= 0.5, 1, -1)
        print(f'  [현재 E 와 비교] 안정 추정 {stable.sum()}개 중 E≠0 {m.sum()}개: '
              f'부호 일치 {int((np.sign(E_ref[m]) == est[m]).sum())}/{m.sum()}')


def invert():
    d = core.Data.load()
    idx, rank, *_ = core.paper_ranking(d.names)
    _invert_one('ours: 재구성 F + p5 순위', d.Xn[idx], rank, d.cols,
                Y=d.Y[idx], E_ref=d.E)
    B, keggs, *_ = core.heatmap()
    keep = B.max(1) > B.min(1)
    _invert_one('paper: heatmap.xlsx F + 행 순서', B[keep],
                np.arange(len(B))[keep].astype(float), keggs)


# ======================================================================
# improve
# ======================================================================
# AFS 근사: KEGG -> 1일 기준량(g). FDA DV(2016), EPA+DHA 는 250 mg 권고량.
AFS_DV = {'C00504': 400e-6, 'C00023': 18e-3, 'C06429': 250e-3,
          'C00305': 420e-3, 'C00238': 4.7, 'C01529': 55e-6,
          'C00378': 1.2e-3, 'C00473': 900e-6, 'C02823': 2.4e-6,
          'C00072': 90e-3, 'C00038': 11e-3}
#          folate, iron, DHA, Mg, K, Se, thiamine, vit A, B12, vit C, zinc


def improve():
    d = core.Data.load()
    groups = _groups(d.cols)

    tab = core.menda_orig()
    conf = {}
    for c in d.cols:
        v = core.lookup(tab, c)
        if v is not None and sum(v) > 0:
            conf[c] = abs(v[0] - v[1]) / (v[0] + v[1] + 2)
    fill = float(np.median(list(conf.values())))
    E1 = np.array([np.sign(e) * conf.get(c, fill) for c, e in zip(d.cols, d.E)])

    q = pd.read_csv(os.path.join(core.OUT, 'knowledge_query_results.csv'))
    q2 = dict(zip(q.compound, q.in_Q2.astype(bool)))
    gate = np.array([q2.get(c, False) for c in d.cols], dtype=float)
    print(f'V1: MENDA 카운트 있는 compound {len(conf)}개, 없는 것은 conf 중앙값 {fill:.3f}')
    print(f'V2: 미생물 경로(in_Q2) 있는 compound {int(gate.sum())}/85')

    fn = pd.read_csv(os.path.join(core.OUT, 'foodname.csv'))
    X = pd.read_csv(os.path.join(core.OUT, 'food.csv'))[list(AFS_DV)].values
    afs_all = np.minimum(X / np.array(list(AFS_DV.values())), 1.0).mean(1)
    by = dict(zip(fn.foodname, afs_all))
    afs = np.array([by[n] for n in d.names])

    idx, rank, _, ptop, pbot = core.paper_ranking(d.names)
    print(f'\n{"":16s} {"Spearman":>9s} {"Top30":>6s} {"Bot30":>6s} {"gold":>5s} '
          f'{"claims":>7s} {"(보조)AFS":>10s}   E')
    for lbl, p, E in (('R  재현 기준', d.score(d.E), d.E),
                      ('V1 근거 가중 E', d.score(E1), E1),
                      ('V2 미생물 경로', d.score(d.E * gate), d.E * gate),
                      ('V3 유사도 제거', d.Xn @ d.E, d.E),
                      ('V4 V1+V2', d.score(E1 * gate), E1 * gate)):
        order = np.argsort(-p)
        top = {d.names[i] for i in order[:K]}
        bot = {d.names[i] for i in order[-K:]}
        nc = sum(v[1] for v in evaluate_claims(p, d, groups).values())
        print(f'{lbl:16s} {stats.spearmanr(-p[idx], rank).statistic:+9.3f} '
              f'{len(top & ptop):4d}/30 {len(bot & pbot):4d}/30 '
              f'{core.gold_of_E(d.cols, E):>5s} {nc:5d}/6 '
              f'{stats.spearmanr(p, afs).statistic:+10.3f}   '
              f'+{int((E > 0).sum())}/-{int((E < 0).sum())}/0={int((E == 0).sum())}')

    pr = _paper_score(d)
    ok = ~np.isnan(pr)
    print(f'\n참고: AFS Spearman — 논문 순위(p5) '
          f'{stats.spearmanr(pr[ok], afs[ok]).statistic:+.3f}, '
          f'1비트 {stats.spearmanr(core.one_bit(d.Y), afs).statistic:+.3f}')


FUNCS = {'units': units, 'claims': claims, 'invert': invert, 'improve': improve}

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for k in (list(FUNCS) if which == 'all' else [which]):
        if k not in FUNCS:
            sys.exit(f'알 수 없는 항목: {k}\n가능: {", ".join(FUNCS)}, all')
        print(f'=== {k} ===')
        FUNCS[k]()
        print()
