"""ourkg 분석 — 논문 §4 (추천) · §5.1 (평가).

    python3 ourkg/analyze.py            # 둘 다
    python3 ourkg/analyze.py recommend
    python3 ourkg/analyze.py evaluate

  recommend  논문 Algorithm 1 (식 1·2) 을 우리 KG 에 적용 (depression)
  evaluate   §4.1 SPARQL Q1~Q3, §5.1 방법 1·2
             PART 환경변수로 일부만 실행 가능 (기본 ABC)

ourkg/build.py 의 산출물을 읽는다.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
import re
import json
import time
import random
import itertools
import collections
import requests

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'eval'))
from common import OUT, BASE


def recommend(e_mode=None, path=None, save=True):
    """05 — 논문 Algorithm 1 을 우리 KG 에 적용 (depression).

    §4.2.1  D = E x F^T
    §4.2.2  S = adjusted cosine similarity (식 1), P = D x S (식 2), Threshold·Top K
    공식 구현(final.py) 경로를 따른다: PCA 없음, 행별 min-max, S 의 대각 0,
    p 를 S 열합으로 나눔. 다만 음식이 14,000 규모라 식 (1) 을 벡터화했다
    (공식 이중 루프와 같은 값, tools 로 소규모 대조 가능).

    출력
      out/recommendation.csv   rank, food_key, food_name, food_group, score, n_compound
      out/recommendation.png   Fig.4(b) 대응 t-SNE

    e_mode / path 를 주면 환경변수 E_MODE / PATH 대신 그 값을 쓴다 (compare 가 쓴다).
    save=False 면 파일을 쓰지 않고 결과 DataFrame 만 돌려준다.
    """
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import OUT

    K = int(os.environ.get('TOP_K', '30'))
    # 논문 §4.2.1 — "we employ principal component analysis (PCA) on the obtained
    # incidence matrix to reduce its dimensionality ... To ensure that we preserve
    # more than 80% of the variance present in the original sample, we select five
    # principal components as the final dimension of the matrix."
    #
    # Fig.4(a) 의 x 축이 principal components 1~85 이므로 PCA 는 compound 축에
    # 걸리고, 그 축소 공간에서 유사도 S 를 계산하라는 뜻이다. D = E x F^T 는
    # 원래 F 로 계산한다(E 가 compound 축에 정의돼 있으므로).
    #
    # 2026-11-05 이전에는 공식 final.py 를 따라 PCA 를 끄고 돌렸다. 그 결과
    # S 가 신호를 깎는 것으로 보였는데(§8·§10), 논문의 PCA 를 켜면 반대로 돕는다.
    # 논문이 쓴 것은 '5' 라는 숫자가 아니라 '분산 80% 보존' 이라는 규칙이다.
    # 우리 F 에서 80% 를 넘는 최소 성분 수는 10 이다(논문 데이터에서는 5).
    # 논문은 숫자(5)와 규칙(분산 80%)을 함께 적는데, 논문 데이터에서는 둘이 같고
    # 우리 F 에서는 다르다 — 5 성분은 74.1%, 80% 를 넘으려면 10 성분이다.
    # 기본값은 논문이 명시한 숫자 5 로 둔다. 규칙 적용판은 auto 로 돌린다.
    #   PCA_COMPONENTS=0     PCA 없음 (기본, 아래 이유)
    #   PCA_COMPONENTS=5     논문 §4.2.1 의 숫자
    #   PCA_COMPONENTS=auto  논문 규칙(분산 PCA_VARIANCE, 기본 0.80) 적용
    #   PCA_COMPONENTS=<n>   직접 지정
    #
    # 기본값이 0 인 이유 (§13): F 를 논문대로 우울증 연결 compound 로 제한하면
    # PCA 를 켜는 쪽이 Top 30 을 망가뜨린다. 논문 §4.2.3 이 보고한 결과
    # ("recommended foods are mainly fish and shellfish products, as well as
    # fruits and vegetables")를 재현하는 것은 PCA 를 끈 쪽이다.
    # 논문 본문(PCA 를 쓰라)과 논문 결과(§4.2.3)가 어긋나고, 결과 쪽을 따랐다.
    _pca_opt = os.environ.get('PCA_COMPONENTS', '0')
    PCA_VAR = float(os.environ.get('PCA_VARIANCE', '0.80'))
    PCA_N = -1 if _pca_opt == 'auto' else int(_pca_opt)

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
    #   E_MODE=sig       BH q<0.05 인 compound 만 ±1
    #   E_MODE=weighted  네 근거의 가중 합의 (build.py evidence)
    #   E_MODE=priority  우선순위 첫 비영 값 (build.py evidence)
    E_MODE = e_mode or os.environ.get('E_MODE', 'shrunk')
    if E_MODE.startswith('stype:'):
        sp = os.path.join(OUT, 'compound_depression_stype.csv')
        if not os.path.exists(sp):
            sys.exit('compound_depression_stype.csv 가 없다. '
                     'python3 ourkg/analyze.py stype')
        col = pd.read_csv(sp).set_index('kegg')[E_MODE.split(':', 1)[1]]
    elif E_MODE == 'learned':
        # 주의: 이 E 는 ModiMedDiet 라벨로 학습한 것이다(analyze.py invert).
        # ModiMedDiet 기준으로 잴 때는 held-out 음식만 써야 한다.
        lp = os.path.join(OUT, 'compound_learned.csv')
        if not os.path.exists(lp):
            sys.exit('compound_learned.csv 가 없다. python3 ourkg/analyze.py invert')
        col = pd.read_csv(lp).set_index('kegg')['e_learned']
    elif E_MODE.split('_')[0] in ('weighted', 'priority', 'vote'):
        ev_path = os.path.join(OUT, 'compound_evidence.csv')
        if not os.path.exists(ev_path):
            sys.exit('compound_evidence.csv 가 없다. python3 ourkg/build.py evidence')
        ev = pd.read_csv(ev_path).set_index('kegg')
        col = ev['e_' + E_MODE]
    elif E_MODE == 'binary':
        col = E_df['e_binary']
    elif E_MODE == 'sig':
        col = E_df['e_binary'].where(E_df['q'] < 0.05, 0.0)
    else:
        col = E_df['e_shrunk']
    e = np.array([col.get(c, 0.0) for c in compounds], dtype=float)
    print(f'  E_MODE={E_MODE}')

    # 논문 §4.2.1 — "135 food samples and their associated 85 component compounds,
    # **with these compounds being linked to depression**".
    # 논문의 F 는 우울증에 연결된 compound 만 열로 갖는다. 우리 F 는 FDC 에서
    # KEGG 로 매핑되는 130종 전부였고, 그중 E 가 비영인 것은 66종뿐이다.
    # D = E x F^T 에는 영향이 없지만(E=0 열은 기여가 0) **유사도 S 가 쓸모없는
    # 64개 축을 포함해 계산**되고 있었다. 논문대로 제한한다.
    #   F_COLUMNS=linked  E 가 비영인 compound 만 (기본, 논문 §4.2.1)
    #   F_COLUMNS=all     FDC 에서 매핑된 compound 전부 (2026-11-05 이전 동작)
    F_COLUMNS = os.environ.get('F_COLUMNS', 'linked')
    if F_COLUMNS == 'linked':
        sel = np.flatnonzero(e)
        if len(sel) == 0:
            sys.exit(f'E_MODE={E_MODE} 에서 비영 compound 가 없다.')
        F = F.iloc[:, sel]
        compounds = [compounds[i] for i in sel]
        e = e[sel]
        print(f'  F_COLUMNS=linked — 우울증 연결 compound {len(sel)}열만 사용')
    elif F_COLUMNS != 'all':
        sys.exit(f'F_COLUMNS 는 linked 또는 all. 받은 값: {F_COLUMNS}')

    # 경로 제한 — 논문 Fig.2 의 두 갈래 중 어느 쪽을 쓸 것인가.
    #
    #   direct    Food → Compound → Mental disorder
    #             지금까지의 기본값이자 논문 Algorithm 1 이 실제로 쓰는 경로다.
    #             E 가 compound-우울증 직접 연관(ProMENDA)에서 오고 미생물은
    #             점수에 들어가지 않는다. 미생물 축은 KG 와 §4.1 쿼리에만 쓰인다.
    #
    #   gutbrain  Food → Compound → Gut microbiota → Mental disorder
    #             논문이 §1·§3.1 에서 내세우는 gut-brain axis 경로. 미생물을
    #             거치는 compound 만 남기고 나머지 E 를 0 으로 둔다.
    #             (KEGG compound-미생물 링크 + 그 미생물의 MeSH F03 연관)
    #             REPRODUCTION §16 의 V2 ablation 과 같은 취지인데, 그쪽은
    #             공개 KG 에서 85 중 8종만 남았고 여기서는 35종이 남는다.
    PATH = path or os.environ.get('PATH_MODE', 'direct')
    # PATH_SOURCE=csv(기본, 빠름) | kg(ourkg.nt 에 SPARQL). 두 집합이 같은지는
    # `analyze.py pathcheck` 가 검사한다.
    if PATH == 'gutbrain':
        gut = (gutbrain_from_kg() if os.environ.get('PATH_SOURCE') == 'kg'
               else gutbrain_from_csv())
        keep_e = np.array([c in gut for c in compounds])
        e = e * keep_e
    elif PATH != 'direct':
        sys.exit(f'PATH_MODE 는 direct 또는 gutbrain. 받은 값: {PATH}')
    print(f'  PATH={PATH}  (E 비영 {int((e != 0).sum())})')
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
        if PCA_N < 0:
            _p = PCA().fit(X)
            cum = np.cumsum(_p.explained_variance_ratio_)
            PCA_N = int(np.argmax(cum >= PCA_VAR)) + 1
            print(f'  PCA 성분 자동 선택: 분산 {PCA_VAR:.0%} 를 넘는 최소 {PCA_N} 성분')
        p = PCA(n_components=PCA_N)
        Xs = p.fit_transform(X)
        print(f'  PCA {PCA_N} 성분, 설명분산 {p.explained_variance_ratio_.sum():.3f} '
              f'(논문 §4.2.1)')
    else:
        Xs = X
        print('  PCA 없음 (공식 final.py 경로)')

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

    # 논문 §4.2.2 Algorithm 1 line 8 — "P = D x S : **Threshold** and Top K"
    #
    # 논문은 Threshold 가 무엇에 걸리는지 밝히지 않는다. 유사도로 인용한
    # Sarwar et al. (2001) item-based CF 에서 Threshold 는 **이웃 선택**을
    # 뜻한다 — 약한 유사도를 예측에서 빼는 것이다. 그 읽기를 따른다.
    # Top K 는 출력(P)에 걸리고 Threshold 는 S 에 걸린다.
    #
    #   positive  S < 0 을 0 으로 (기본). 매개변수가 없어 사전 지정이 가능하다.
    #             adjusted cosine 의 음수는 '성분 구성이 반대' 라는 뜻인데,
    #             그대로 두면 닮지 않은 음식의 점수가 부호를 뒤집어 전파된다.
    #   none      자르지 않는다 (2026-11-05 이전 동작)
    #   topn:<N>  음식마다 가장 닮은 N 개만 남긴다 (Sarwar 의 model size)
    #   q<p>      |S| 의 p 분위수 미만을 0 으로
    SIM_THRESHOLD = os.environ.get('SIM_THRESHOLD', 'none')
    _n_before = int((S != 0).sum())
    if SIM_THRESHOLD == 'positive':
        S[S < 0] = 0.0
    elif SIM_THRESHOLD == 'negative':      # 진단용 — 음수 절반만 남긴다
        S[S > 0] = 0.0
    elif SIM_THRESHOLD.startswith('topn:'):
        N = int(SIM_THRESHOLD.split(':', 1)[1])
        if N < S.shape[1]:
            cut = np.partition(S, -N, axis=1)[:, -N][:, None]
            S = np.where(S >= cut, S, 0.0)
    elif SIM_THRESHOLD.startswith('q'):
        q = float(SIM_THRESHOLD[1:]) / 100.0
        t = np.quantile(np.abs(S[S != 0]), q) if (S != 0).any() else 0.0
        S = np.where(np.abs(S) >= t, S, 0.0)
    elif SIM_THRESHOLD != 'none':
        sys.exit(f'SIM_THRESHOLD 는 positive|none|topn:<N>|q<p>. 받은 값: {SIM_THRESHOLD}')
    _n_after = int((S != 0).sum())
    print(f'  Threshold={SIM_THRESHOLD}  S 비영 {_n_before:,} -> {_n_after:,} '
          f'({_n_after / max(_n_before, 1) * 100:.0f}%)')
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
    if not save:
        return res
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
    return res


def evaluate():
    """06 — 논문 §4.1 쿼리와 §5.1 두 평가법을 우리 KG 에 적용.

    A. §4.1 Query 1·2·3 을 ourkg.nt 위에서 SPARQL 로 실행 (Table 2·3·4 대응)
    B. §5.1 방법 1 — Supplement Table 1 의 20문항을 우리 KG 에 **직접 질의**해
       논문 답과 대조한다. eval/m1.py 의 질의 20개를 그대로 재사용하고(m1.KG 상속),
       적재만 우리 산출물로 바꾼다. 전문가 3인이 없으므로 정확도 0.95/0.90/0.95
       자체는 재현 대상이 아니다(eval/m1.py 서두와 같은 이유).
    C. §5.1 방법 2 — 우리 KG 가 만든 추론 15건을 PubMed 로 검증.
       논문은 수작업 검색이었다. 여기서는 E-utilities 로 같은 판정(1/-1/0)을 자동화한다.
       1 = 두 엔티티가 함께 나오는 논문이 있음, 0 = 없음.
       (논문의 -1 '반대 증거' 는 초록 읽기가 필요해 자동 판정하지 않는다.)

    출력  out/eval_*.json / out/eval_*.csv
    """
    PART = os.environ.get('PART', 'ABC')
    S = requests.Session()
    S.headers['User-Agent'] = 'ourkg/1.0'

    # ======================================================================
    if 'A' in PART:
        from rdflib import Graph, URIRef, Literal

        print('[A] ourkg.nt 적재 (3M triple, 수 분 소요)', flush=True)
        t0 = time.time()
        g = Graph()
        g.parse(os.path.join(OUT, 'ourkg.nt'), format='nt')
        print(f'  triple {len(g):,}  {time.time()-t0:.0f}s', flush=True)

        PREFIX = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX npq:  <http://nutrition.vu.nl/pop/qualifier#>
    PREFIX mpq:  <http://nlp_microbe.ccnu.edu.cn/pop/qualifier#>
    PREFIX our:  <http://nutrition.vu.nl/ourkg/>
    PREFIX ent:  <http://nutrition.vu.nl/entity#>
    """

        # 논문 Supplementary Query 1 을 그대로 쓰면 음식 라벨 regex 가 중량 노드 76만 개와
        # 조인되어 끝나지 않는다(논문 자신도 Q1 이 폭발한다 — eval/paper_sparql.py 참조).
        # 먼저 라벨로 음식 URI 를 싸게 찾고, 그 결과를 VALUES 로 주입해 본 쿼리를 돌린다.
        # 질문의 의미는 같고, 바뀐 것은 조인 순서뿐이다.
        def find_foods(pattern, limit=6):
            q = PREFIX + f"""select ?f ?l where {{
              ?f rdf:type ent:Food ; rdfs:label ?l .
              filter regex(?l, "{pattern}", "i")
            }} limit {limit}"""
            return [(r[0], str(r[1])) for r in g.query(q)]

        res = {}

        # --- Q1 (§4.1.1) 혼합 식단의 영양소 흡수량 (Table 2 대응)
        # rdflib 는 VALUES 를 BGP 아래로 밀어 넣지 않아, 음식을 묶지 않으면 중량 노드
        # 76만 개와 조인한다. 음식 URI 를 쿼리 문자열에 직접 넣어 subject 를 묶는다.
        eggs = find_foods('^Egg, whole')
        milks = find_foods('^Milk, whole|^Milk, reduced fat')
        print(f'\n  --- Q1 (Table 2 대응)  음식 {len(eggs)} x {len(milks)}', flush=True)
        t0 = time.time()
        rows = []
        for eu, el in eggs:
            for mu, ml in milks:
                q = PREFIX + f"""select ?cname ?ew ?mw where {{
                  <{eu}> npq:hasNutrientWeights ?e . ?e npq:ofCompound ?c ; rdf:value ?ew .
                  <{mu}> npq:hasNutrientWeights ?m . ?m npq:ofCompound ?c ; rdf:value ?mw .
                  ?c rdfs:label ?cname .
                  filter regex(?cname, "Riboflavin|Thiamin|Niacin", "i")
                }}"""
                for r in g.query(q):
                    rows.append([el, ml, str(r[0]), float(r[1]), float(r[2]),
                                 float(r[1]) + float(r[2])])
        rows.sort(key=lambda r: -r[-1])
        res['Q1'] = rows[:8]
        print(f'      {len(rows)}행  {time.time()-t0:.1f}s', flush=True)
        for r in rows[:8]:
            print(f'      {r[0][:28]:28s} {r[1][:30]:30s} {r[2][:14]:14s} {r[5]:10.6f}',
                  flush=True)

        # --- Q2 (§4.1.1) 성분 → 장내세균 → 우울증 (Table 3 대응)
        t0 = time.time()
        q2 = PREFIX + """select ?cname ?microbe ?rel where {
          ?c ?rel <http://id.nlm.nih.gov/mesh/D003865> ; rdfs:label ?cname .
          filter(?rel in (npq:hasPositiveAssociation, npq:hasNegativeAssociation))
          ?m mpq:hasMetabolites ?c ; rdfs:label ?microbe .
        } limit 200"""
        rows = sorted({(str(a), str(b), str(c).split('#')[-1]) for a, b, c in g.query(q2)})
        res['Q2'] = [list(r) for r in rows]
        print(f'\n  --- Q2 (Table 3 대응)  {len(rows)}행  {time.time()-t0:.1f}s', flush=True)
        for r in rows[:10]:
            print(f'      {r[0][:26]:26s} {r[1][:34]:34s} {r[2]}', flush=True)

        # --- Q3 (§4.1.1) 우울증 + 합병증에 동시에 작용하는 성분 (Table 4 대응)
        t0 = time.time()
        q3 = PREFIX + """select distinct ?cname ?microbe ?disease where {
          ?c ?rel <http://id.nlm.nih.gov/mesh/D003865> ; rdfs:label ?cname .
          filter(?rel in (npq:hasPositiveAssociation, npq:hasNegativeAssociation))
          ?m mpq:hasMetabolites ?c ; rdfs:label ?microbe ; mpq:hasAssociation ?d .
          ?d rdfs:subClassOf ent:MentalDisorder ; rdfs:label ?disease .
          filter(?d != <http://id.nlm.nih.gov/mesh/D003865>)
        } limit 100"""
        rows = sorted({(str(a), str(b), str(c)) for a, b, c in g.query(q3)})
        res['Q3'] = [list(r) for r in rows]
        print(f'\n  --- Q3 (Table 4 대응)  {len(rows)}행  {time.time()-t0:.1f}s', flush=True)
        for r in rows[:12]:
            print(f'      {r[0][:26]:26s} {r[1][:34]:34s} {r[2]}', flush=True)

        json.dump(res, open(os.path.join(OUT, 'eval_sparql.json'), 'w'),
                  ensure_ascii=False, indent=1)

    # ======================================================================
    if 'B' in PART:
        import paper_data
        sys.path.insert(0, os.path.join(BASE, 'eval'))
        import m1

        print('\n[B] §5.1 방법 1 — 20문항을 우리 KG 에 직접 질의')
        # 예전 판은 측면(aspect)마다 '축이 있는가' 를 손으로 O/△ 로 적고 20문항이
        # 그것을 상속했다. 그건 답변 **가능성**이지 답이 아니다. 이제 eval/m1.py 의
        # 20개 질의 함수를 그대로 재사용해 **답을 뽑아 논문 답과 대조**한다.
        # m1.KG 를 상속하고 적재만 우리 산출물로 바꾼다 — 질의 20개는 손대지 않는다.

        # m1.NUT 는 FDC nutrient_id 로 되어 있고 우리 long 표는 KEGG 로 되어 있다.
        NUT2KEGG = {1214: 'C00047', 1190: 'C00504', 1105: 'C00473',
                    1032: 'C00158', 1162: 'C00072', 1092: 'C00238',
                    1178: 'C05776', 1175: None}      # 1175 B-6 는 KEGG 대응이 없다
        # 우리 long 표는 g, 공개 KG 는 FDC 원 단위(mg/µg)다. 공통 음식에서 잰
        # 배율은 공통 음식에서 재어 모두 10^3 이었다 (ourkg/RESULTS.md 방법 1).
        G_TO_FDC = 1000.0

        class OurKG(m1.KG):
            def __init__(self):
                dd = collections.defaultdict
                foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
                long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
                mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str})
                md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'),
                                 dtype={'taxid': str})
                cm = pd.read_csv(os.path.join(OUT, 'compound_microbe.csv'),
                                 dtype={'taxid': str})
                cd = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))

                self.food = dict(zip(foods.fdc_id, foods.food_name))
                key2fdc = dict(zip(foods.food_key, foods.fdc_id))
                long = long.assign(fdc=long.food_key.map(key2fdc))

                # nut2kegg 는 '음식 성분으로 측정된 compound' 집합이다 (q15 가
                # .values() 로 쓴다). 공개 KG 는 Food_Nutrient 의 sameAs 전부를 담으므로
                # 우리도 음식 행렬의 compound 전부를 넣는다 — 8종만 넣으면 안 된다.
                self.w = dd(dict)
                self.nut2kegg = {i: k for i, k in enumerate(sorted(set(long.kegg.dropna())))}
                for nid, kegg in NUT2KEGG.items():
                    if kegg is None:
                        continue
                    sub = long[long.kegg == kegg]
                    self.w[nid] = {int(f): v * G_TO_FDC
                                   for f, v in zip(sub.fdc, sub.amount_g)
                                   if pd.notna(f)}

                # 카테고리: FDC 세분류 → SR 27군 두 층 + 온톨로지 라벨.
                self.f2c, self.clab, self.csub = dd(set), {}, dd(set)
                fine_uri_lbl = {}
                _nrm = lambda x: re.sub(r'[^a-z]', '', str(x).lower())
                food_by_first = {}
                for fdc, nm in zip(foods.fdc_id, foods.food_name):
                    food_by_first.setdefault(_nrm(str(nm).split(',')[0]), int(fdc))
                for fdc, cat, grp in zip(foods.fdc_id, foods.category, foods.food_group):
                    for lv, val in (('cat', cat), ('grp', grp)):
                        if pd.isna(val):
                            continue
                        u = f'ourkg:{lv}/{val}'
                        self.clab[u] = str(val)
                        if lv == 'cat':
                            fine_uri_lbl[str(val)] = u
                        if lv == 'cat':
                            self.f2c[int(fdc)].add(u)
                            if pd.notna(grp):
                                self.csub[u].add(f'ourkg:grp/{grp}')
                        else:
                            self.f2c[int(fdc)].add(u)

                # 온톨로지(FoodOn·중국)가 붙은 카테고리·음식에는 그쪽 라벨도
                # 카테고리로 달아 준다. 안 그러면 통합해 놓고 질의가 못 본다.
                ol = os.path.join(OUT, 'category_ontology.csv')
                if os.path.exists(ol):
                    o = pd.read_csv(ol)
                    label2fine = {k: v for k, v in fine_uri_lbl.items()}
                    for our, kind, onto_lab, src in zip(o['our'], o['kind'],
                                                        o['onto_label'], o['source']):
                        if not isinstance(onto_lab, str):
                            continue
                        u = f'onto:{src}/{onto_lab}'
                        self.clab[u] = onto_lab
                        if kind == 'category' and our in label2fine:
                            self.csub[label2fine[our]].add(u)
                        elif kind == 'food':
                            fu = food_by_first.get(_nrm(our))
                            if fu is not None:
                                self.f2c[fu].add(u)

                # KEGG brite 분류축. m1.KG 와 같은 형태로 맞춘다 —
                #   klab   전체 URI -> 라벨 (compound 는 kegg entry URI)
                #   ksub   클래스 URI -> 상위 클래스 URI
                #   ktype  bare compound id -> 클래스 URI
                KEGG_URI = 'https://www.kegg.jp/entry/'
                self.klab = {}
                self.ksub, self.ktype = dd(set), dd(set)
                kc = os.path.join(OUT, 'kegg_class.csv')
                cc = os.path.join(OUT, 'compound_class.csv')
                if os.path.exists(kc):
                    k1 = pd.read_csv(kc)
                    # KEGG 원 라벨이 먼저다. 우리 ProMENDA 이름("Thiamine")은 KEGG 라벨
                    # ("Thiamine (Vitamin B1)")의 괄호 표기를 잃어서, 질의가 'Vitamin'
                    # 으로 거르면 전부 떨어진다.
                    for u, lab, par in zip(k1.class_uri, k1.label, k1.parent_uri):
                        if pd.notna(lab):
                            self.klab[u] = lab
                        if isinstance(par, str) and par:
                            self.ksub[u].add(par)
                for k, n in zip(cd.kegg, cd.name):       # KEGG 라벨이 없을 때만 보충
                    if pd.notna(n):
                        self.klab.setdefault(KEGG_URI + k, n)
                if os.path.exists(cc):
                    k2 = pd.read_csv(cc)
                    for kid, cu in zip(k2.kegg, k2.class_uri):
                        self.ktype[kid].add(cu)

                self.bname = dict(zip(mic.taxid, mic.name))
                self.b2c = dd(set)
                for t, k in zip(cm.taxid, cm.kegg):
                    self.b2c[t].add(k)
                self.b2d, self.dlab = dd(set), {}
                for t, mid, dis in zip(md.taxid, md.mesh_id, md.disease):
                    self.b2d[t].add(mid)
                    self.dlab[mid] = dis
                self.menda = set(cd.kegg)

                # MiKG 유래 정신질환 목록 — 우리 산출물에서 직접 준다.
                # 이게 없으면 q13 이 MiKG 원본 TTL 을 읽어 공개 KG 의 답을 낸다.
                mikg = pd.read_csv(os.path.join(OUT, 'microbe_disease_mikg.csv'))
                self._mental = sorted(set(mikg.disease.dropna()))

                # 계통: microbes.csv 의 lineage 로 부모 사슬을 만든다.
                # 공개 KG 의 bpar 는 taxid -> taxid 다. 우리 lineage 는 이름뿐이라
                # 상위 분류군은 이름을 그대로 노드 id 로 쓰고 bname 에 등록한다.
                self.bpar = {}
                for t, lin in zip(mic.taxid, mic.lineage):
                    if pd.isna(lin):
                        continue
                    chain = [x.strip() for x in str(lin).split(';') if x.strip()]
                    if not chain:
                        continue
                    self.bpar[t] = chain[-1]          # taxid -> 최근접 상위 (이름 노드)
                    for i in range(len(chain) - 1, 0, -1):
                        self.bpar[chain[i]] = chain[i - 1]
                        self.bname.setdefault(chain[i], chain[i])
                    self.bname.setdefault(chain[0], chain[0])

            def mental_disorders(self):
                return self._mental

        kg = OurKG()
        print(f'  적재: 음식 {len(kg.food):,}  영양소축 {len(kg.w)}/8  '
              f'세균 {len(kg.bname)}  질환 {len(kg.dlab)}')

        rows = []
        for t in m1.M1:
            try:
                rep, val, why = m1.QUERY[t['no']](kg)
            except Exception as e:                      # 축이 없으면 그대로 기록한다
                rep, val, why = 'X', 'X', f'{type(e).__name__}: {e}'
            rows.append({'no': t['no'], 'aspect': t['attribute'],
                         'question': t['question'], 'paper_answer': t['paper_answer'],
                         'ourkg_reproduced': rep, 'ourkg_valid': val, 'note': why,
                         'expert_consensus': int(t['consensus'])})
        b = pd.DataFrame(rows)
        b.to_csv(os.path.join(OUT, 'eval_method1.csv'), index=False)
        n = int((b.ourkg_reproduced != '-').sum())
        rep = int((b.ourkg_reproduced == 'O').sum())
        both = int(((b.ourkg_reproduced == 'O') & (b.ourkg_valid == 'O')).sum())
        con = b[(b.expert_consensus == 1) & (b.ourkg_reproduced != '-')]
        print(f'  논문 답 재현 {rep}/{n}   재현+타당 {both}/{n}   '
              f'전문가 전원동의 {len(con)}문항 중 '
              f'{int((con.ourkg_reproduced == "O").sum())}')
        print(f'  (공개 KG 를 같은 질의로 돌리면 18/20 — eval/m1.py)')
        print(b.groupby(['aspect', 'ourkg_reproduced']).size().to_string())

    # ======================================================================
    if 'C' in PART:
        print('\n[C] §5.1 방법 2 — 추론 15건 PubMed 검증')
        md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})
        mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str}
                          ).set_index('taxid')['name'].to_dict()
        mdis = pd.read_csv(os.path.join(OUT, 'microbe_disease_mikg.csv'))
        rec = pd.read_csv(os.path.join(OUT, 'recommendation.csv'))
        E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
        long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
        foods = pd.read_csv(os.path.join(OUT, 'foods.csv')).set_index('food_key')

        random.seed(0)
        infs = []

        def _species(name):
            """균주 이름 -> 종 수준(속 + 종). 논문 Table 5 의 근거 세균은
            `Bifidobacterium longum`·`Escherichia coli` 처럼 종 수준이다.
            `Lactococcus lactis subsp. lactis` 같은 균주명은 문헌에 거의 안 붙는다."""
            w = re.split(r'\s+', re.sub(r'\b(subsp|str|var|serovar)\.?\b.*', '',
                                        str(name)).strip())
            return ' '.join(w[:2]) if len(w) >= 2 else (w[0] if w else str(name))

        def _food_terms(name):
            """구체 음식명 -> 일반명 사다리.

            논문 Table 5 의 Diet 행은 `Garlic`·`Milk`·`Coffee`·`Lettuce`·`Onion` 처럼
            **일반명 수준**이다. 우리는 FDC 개별 항목에서 뽑으므로 그대로 쓰면 문헌이
            붙지 않는다 — "Mustard greens" AND "depression" 은 0 건인데
            "mustard" AND "depression" 은 194 건이다. 같은 수준으로 맞춘다.
            """
            def clean(seg):
                # 브랜드 토큰 제거 — 대문자가 2 자 이상인 토큰(FUZE, BOLTHOUSE,
                # McDONALD'S)은 문헌 검색어가 못 된다.
                w = [x for x in seg.split() if sum(c.isupper() for c in x) < 2]
                return re.sub(r'\s+', ' ', ' '.join(w)).strip(" '\"-")

            t = ''
            for seg in re.split(r'[,(]', str(name)):      # 첫 구간이 브랜드뿐이면 다음
                t = clean(seg)
                if t:
                    break
            if not t:
                return ['food']
            out = [t]
            head = t.split()[0]
            if head.lower() != t.lower():
                out.append(head)
            return out

        # 추론 (a) Complication — 같은 미생물을 공유하는 두 정신질환 (논문 §3.3)
        by_mic = collections.defaultdict(set)
        for _, r in mdis.iterrows():
            by_mic[r['microbe']].add(r['disease'])
        pairs = collections.Counter()
        for m, ds in by_mic.items():
            for a, b in itertools.combinations(sorted(ds), 2):
                pairs[(a, b)] += 1
        for (a, b), n in pairs.most_common(40):
            shared = sorted(m for m, ds in by_mic.items() if a in ds and b in ds)
            # 공유 미생물이 여럿이면 시드 고정 난수로 하나를 고른다. 문헌이 가장 잘
            # 붙는 것을 고르면 검증이 아니라 확증 편향이 된다.
            infs.append({'type': 'Complication', 'q': f'{a} and {b}',
                         'evidence': _species(random.choice(shared)),
                         'n_shared_microbe': n,
                         'terms': [a, b]})

        # 추론 (b) Diet recommendation — 상·하위 음식과 그 근거 compound
        def basis(fk):
            sub = long[long.food_key == fk].copy()
            sub['e'] = sub['kegg'].map(E['e_shrunk']).fillna(0)
            sub['w'] = sub['amount_g'] * sub['e']
            if sub.empty or sub['w'].abs().max() == 0:
                return None
            row = sub.loc[sub['w'].abs().idxmax()]
            return str(E['name'].get(row['kegg'], row['kegg']))

        for fk in list(rec.head(20)['food_key']) + list(rec.tail(20)['food_key']):
            c = basis(fk)
            if not c:
                continue
            nm = foods.loc[fk, 'food_name']
            infs.append({'type': 'Diet recommendation',
                         'q': f'{nm} and depression', 'evidence': c,
                         'terms': [_food_terms(str(nm))[0], 'depression'],
                         'ladder': _food_terms(str(nm))})

        # 표본 — 같은 근거 물질이 반복되면 15 건이 사실상 4~5 건이 된다.
        # (2026-11-09 이전 판은 Palmitic acid + 소고기가 15 건 중 4 건이었다.)
        random.shuffle(infs)
        seen, sample = collections.Counter(), []
        for inf in infs:
            if seen[inf['evidence']] >= 2:
                continue
            seen[inf['evidence']] += 1
            sample.append(inf)
            if len(sample) == 15:
                break

        def pubmed(terms, extra=None):
            q = ' AND '.join(f'"{t}"' for t in terms if t)
            if extra:
                q += f' AND "{extra}"'
            r = S.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
                      params={'db': 'pubmed', 'term': q, 'retmax': 3, 'retmode': 'json'},
                      timeout=60)
            time.sleep(0.4)
            try:
                d = r.json()['esearchresult']
                return int(d['count']), d.get('idlist', [])
            except Exception:
                return 0, []

        rows = []
        for i, inf in enumerate(sample, 1):
            # 판정은 '두 엔티티 + KG 가 댄 근거' 세 항이 모두 함께 나오는 논문이
            # 있는가로 한다. 질환 이름 두 개만으로 검색하면 anxiety+depression 처럼
            # 1만 건이 나와 아무것도 검증하지 못한다(그 수치는 참고용으로만 남긴다).
            ladder = inf.get('ladder') or [inf['terms'][0]]
            n = n_pair = 0
            ids, used, level = [], inf['terms'][0], 0
            for lv, term in enumerate(ladder):
                terms = [term] + inf['terms'][1:]
                n, ids = pubmed(terms, inf['evidence'])
                n_pair, _ = pubmed(terms)
                used, level = term, lv
                if n:
                    break
            rows.append({'no': i - 1, 'question': inf['q'], 'attributes': inf['type'],
                         'ourkg': inf['evidence'], 'pubmed': ';'.join(ids[:2]),
                         'term_used': used, 'term_level': level,
                         'n_hits_with_evidence': n, 'n_hits_pair_only': n_pair,
                         'result': 1 if n else 0})
            print(f"  {i:2d}. {inf['q'][:44]:46s} {inf['evidence'][:20]:22s} "
                  f"[{used[:14]:16s}] 근거포함={n:5d}  두항만={n_pair:6d}"
                  f"  -> {'1' if n else '0'}")
        t5 = pd.DataFrame(rows)
        t5.to_csv(os.path.join(OUT, 'eval_method2.csv'), index=False)
        # --- 같은 자로 재기. 우리 기준(3항 공출현)을 **논문 자신의 15건**에 적용해
        # 보정값을 얻는다. 이것 없이 "우리 x/15 vs 논문 11/15" 를 비교하면 자가 다르다.
        from paper_data import TABLE5 as _PT5
        cal = []
        for _no, _q, _attr, _ev, _pmid, _res in _PT5:
            _a, _b = [x.strip() for x in _q.split(' and ')]
            _n3, _ = pubmed([_a, _b], _ev)
            _n2, _ = pubmed([_a, _b])
            cal.append({'no': _no, 'attributes': _attr, 'question': _q,
                        'evidence': _ev, 'paper_result': _res,
                        'n_hits_with_evidence': _n3, 'n_hits_pair_only': _n2})
        cdf = pd.DataFrame(cal)
        cdf.to_csv(os.path.join(OUT, 'eval_method2_calibration.csv'), index=False)

        up = int((t5.term_level > 0).sum())
        print(f"\n  확인됨(1) {int((t5.result == 1).sum())}/15, "
              f"미확인(0) {int((t5.result == 0).sum())}/15   "
              f"(논문 Table 5: 11 / 3 / 반대 1)")
        print(f"  일반명으로 올려서 맞은 것 {up}건, 근거 물질 고유 "
              f"{t5.ourkg.nunique()}종 (전판 15건 중 4건이 같은 물질이었다)")
        o3 = int((t5.n_hits_with_evidence > 0).sum())
        o2 = int((t5.n_hits_pair_only > 0).sum())
        c3 = int((cdf.n_hits_with_evidence > 0).sum())
        c2 = int((cdf.n_hits_pair_only > 0).sum())
        print()
        print('  같은 자로 — 기준별 비교')
        print(f'    {"기준":22s}{"우리 15건":>10s}{"논문 15건":>12s}')
        print(f'    {"3항 공출현(엄격)":22s}{o3:>8d}/15{c3:>10d}/15')
        print(f'    {"2항 공출현(논문에 가까움)":22s}{o2:>8d}/15{c2:>10d}/15')
        print(f'    논문이 보고한 값: 11/15 (confirmed) — 2항 기준과 비슷하다')
        print('    → 엄격 기준으로는 논문 자신도 거의 통과하지 못한다.')


def compare():
    """E 를 만드는 방식들을 같은 기준으로 나란히 비교한다.

    판정 기준은 논문 §4.2.3 서술에서 실행 전에 가져왔다.
      추천   "the recommended foods are mainly fish and shellfish products,
              as well as fruits and vegetables"
      비추천 "the not recommended foods are mainly sausage products, baked
              products, and sweets" + Fig.5 피라미드 상단의 beef / sausages /
              luncheon meats / pork

    각 모드에서 Top K / Bottom K 가 이 카테고리에 몇 개나 들어가는지 세고,
    모드 사이의 순위 상관과 Top K 겹침을 함께 낸다.

    출력
      out/e_mode_comparison.csv
    """
    from scipy.stats import spearmanr

    K = int(os.environ.get('TOP_K', '30'))
    MODES = os.environ.get(
        'E_MODES',
        'shrunk,binary,weighted,priority,vote,'
        'weighted_norules,priority_norules,vote_norules').split(',')

    REC_OK = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
              'Vegetables and Vegetable Products'}
    NOT_OK = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
              'Beef Products', 'Pork Products', 'Lamb, Veal, and Game Products'}

    PATHS = os.environ.get('PATHS', 'direct').split(',')

    res, rows = {}, []
    for m in MODES:
      for pth in PATHS:
        key = m if pth == 'direct' else f'{m}|{pth}'
        print(f'\n--- E_MODE={m}  PATH={pth}')
        r = recommend(e_mode=m, path=pth, save=False)
        res[key] = r
        top, bot = r.head(K), r.tail(K)
        rows.append({
            'e_mode': m, 'path': pth,
            'n_compound_nonzero': None,          # 아래에서 채운다
            f'top{K}_논문추천군': int(top['food_group'].isin(REC_OK).sum()),
            f'bot{K}_논문비추천군': int(bot['food_group'].isin(NOT_OK).sum()),
            f'top{K}_주류': int((top['food_group'] == 'Alcoholic Beverages').sum()),
            # 교차 위반 — 논문이 비추천이라고 한 군이 Top 에, 추천이라고 한 군이
            # Bottom 에 들어간 수. 한쪽만 보면 좋아 보이는 모드를 걸러낸다.
            f'top{K}_위반': int(top['food_group'].isin(NOT_OK).sum()),
            f'bot{K}_위반': int(bot['food_group'].isin(REC_OK).sum()),
            **modimed_score(r, K),
            'top_food': top['food_name'].iloc[0][:40],
            'bot_food': bot['food_name'].iloc[-1][:40],
        })

    # 모드별로 실제로 몇 개 compound 가 0 이 아닌지
    ev_path = os.path.join(OUT, 'compound_evidence.csv')
    dep = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
    ev = pd.read_csv(ev_path).set_index('kegg') if os.path.exists(ev_path) else None
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    cpds = sorted(long['kegg'].unique())
    for row in rows:
        m = row['e_mode']
        if m.split('_')[0] in ('weighted', 'priority', 'vote') and ev is not None:
            col = ev['e_' + m]
        elif m == 'binary':
            col = dep['e_binary']
        elif m == 'sig':
            col = dep['e_binary'].where(dep['q'] < 0.05, 0.0)
        else:
            col = dep['e_shrunk']
        sel = cpds
        if row['path'] == 'gutbrain':
            cm = pd.read_csv(os.path.join(OUT, 'compound_microbe.csv'), dtype={'taxid': str})
            md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})
            gut = set(cm[cm['taxid'].isin(set(md[md['is_mental']]['taxid']))]['kegg'])
            sel = [c for c in cpds if c in gut]
        row['n_compound_nonzero'] = sum(1 for c in sel if col.get(c, 0))

    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(OUT, 'e_mode_comparison.csv'), index=False)

    print('\n' + '=' * 78)
    print('E 구성 방식 비교')
    print('  §4.2.3  논문이 자기 출력을 서술한 문장 (top/bot 열)')
    print('  ModiMedDiet  SMILES trial (Jacka 2017) 이 실제로 처방한 식단 — 외부 기준')
    print('=' * 78)
    print(tab.to_string(index=False))

    print(f'\n모드 사이의 순위 상관 (Spearman) / Top{K} 겹침')
    for a, b in itertools.combinations(res, 2):
        ra = res[a].set_index('food_key')['score']
        rb = res[b].set_index('food_key')['score'].reindex(ra.index)
        rho = spearmanr(ra.values, rb.values).statistic
        ov = len(set(res[a].head(K)['food_key']) & set(res[b].head(K)['food_key']))
        print(f'  {a:9s} vs {b:9s}   rho={rho:+.3f}   Top{K} 겹침 {ov}/{K}')


def gutbrain_from_csv():
    """중간 CSV 로 gut-brain 경로 compound 집합을 만든다 (빠른 경로)."""
    cm = pd.read_csv(os.path.join(OUT, 'compound_microbe.csv'), dtype={'taxid': str})
    md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})
    mental_tax = set(md[md['is_mental']]['taxid'])
    return set(cm[cm['taxid'].isin(mental_tax)]['kegg'])


def gutbrain_from_kg():
    """같은 집합을 ourkg.nt 에 SPARQL 을 던져 만든다 (권위 있는 경로).

    논문 §4.1.1 Query 3 과 같은 패턴이다 — compound 를 대사하는 세균이
    정신질환(MeSH F03)과 연관된 경우. 결과는 out/gutbrain_compounds.json 에
    캐시한다(3M triple 적재가 60초 걸린다).
    """
    cache = os.path.join(OUT, 'gutbrain_compounds.json')
    nt = os.path.join(OUT, 'ourkg.nt')
    if os.path.exists(cache) and os.path.exists(nt) and \
            os.path.getmtime(cache) >= os.path.getmtime(nt):
        return set(json.load(open(cache))['kegg'])

    from rdflib import Graph
    if not os.path.exists(nt):
        sys.exit('ourkg.nt 가 없다. python3 ourkg/build.py kg')
    print(f'  ourkg.nt 적재...', flush=True)
    t0 = time.time()
    g = Graph()
    g.parse(nt, format='nt')
    print(f'  triple {len(g):,}  {time.time()-t0:.0f}s', flush=True)

    q = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX mpq:  <http://nlp_microbe.ccnu.edu.cn/pop/qualifier#>
PREFIX ent:  <http://nutrition.vu.nl/entity#>
select distinct ?c where {
  ?m mpq:hasMetabolites ?c ; mpq:hasAssociation ?d .
  ?d rdfs:subClassOf ent:MentalDisorder .
}"""
    got = {str(r[0]).rsplit('/', 1)[-1] for r in g.query(q)}
    got = {c for c in got if c.startswith('C')}
    json.dump({'kegg': sorted(got), 'query': q}, open(cache, 'w'), indent=1)
    return got


def pathcheck():
    """gut-brain 경로 compound 집합을 CSV 와 KG 에서 각각 뽑아 대조한다.

    §6 의 PATH_MODE=gutbrain 은 속도 때문에 중간 CSV 로 경로를 계산한다.
    그 집합이 KG 에 실제로 실린 triple 과 같은지 여기서 검사한다. 어긋나면
    build.py kg 가 관계를 빠뜨렸거나 URI 가 맞지 않는다는 뜻이다.

    출력
      out/gutbrain_compounds.json   KG 에서 뽑은 집합과 쿼리 원문
    """
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    fdc = set(long['kegg'].unique())

    csv_set = gutbrain_from_csv() & fdc
    kg_set = gutbrain_from_kg() & fdc

    print(f'\n  CSV  (compound_microbe + microbe_disease.is_mental)  {len(csv_set)}종')
    print(f'  KG   (ourkg.nt SPARQL, Query 3 패턴)                  {len(kg_set)}종')
    only_csv = sorted(csv_set - kg_set)
    only_kg = sorted(kg_set - csv_set)
    print(f'  일치 {len(csv_set & kg_set)} / CSV 에만 {len(only_csv)} / KG 에만 {len(only_kg)}')
    if only_csv:
        print(f'    CSV 에만: {only_csv}')
    if only_kg:
        print(f'    KG 에만:  {only_kg}')
    if not only_csv and not only_kg:
        print('  두 경로가 같은 집합을 낸다 — KG 와 중간 CSV 가 일관된다.')
    else:
        print('  ⚠ 어긋난다. build.py kg 가 쓰는 관계와 CSV 필터의 정의를 맞춰야 한다.')


# ======================================================================
# 외부 정답셋 — SMILES trial 의 ModiMedDiet (Jacka et al. 2017)
#
# 지금까지의 판정 기준은 논문 §4.2.3 서술 하나뿐이었다. 그것은 논문이 자기
# 알고리즘의 출력을 서술한 문장이라, 같은 기준으로 설정을 고르면 성적이
# 과대평가된다(RESULTS.md §5 끝).
#
# ModiMedDiet 은 우울증 환자 67명 대상 12주 RCT 에서 **실제로 처방된** 식단이고,
# 1차 결과(MADRS)가 유의하게 개선됐다. 출력이 아니라 개입이므로 출처가 독립이다.
# 단, 내용은 완전히 독립이 아니다 — 지중해식 식단이라 "채소·생선 좋고 가공육·
# 과자 나쁨"이라는 방향 자체는 §4.2.3 과 겹친다. 겹치지 않는 것은 근거의 출처다.
#
# 처방 (Jacka et al. 2017, BMC Medicine 15:23, ModiMedDiet 12 food groups)
#   whole grains 5-8/day · vegetables 6/day · fruit 3/day · legumes 3-4/week
#   low-fat unsweetened dairy 2-3/day · raw unsalted nuts 1/day · fish >=2/week
#   lean red meat 3-4/week · chicken 2-3/week · eggs <=6/week · olive oil 3 tbsp/day
#   extras (sweets, refined cereals, fried food, fast food, processed meats,
#           sugary drinks, 그리고 spirits/beer) 합쳐 <=3/week
#
# 처방이 조건부인 것들(low-fat·unsweetened·raw·unsalted·lean·whole·olive)은
# 카테고리만으로 가를 수 없으므로 이름 규칙을 둔다. 규칙은 전부 위 처방 문구에서
# 그대로 가져왔고, 어느 쪽에도 걸리지 않는 음식은 unlabeled 로 두어 집계에서 뺀다.
# ======================================================================

# (정규식, 라벨, 근거) — 순서대로 평가하고 먼저 맞는 것이 이긴다.
# extras 가 먼저다: "refined cereals" 는 곡물이지만 extra 이고,
# "fried food" 는 채소여도 extra 다.
MODIMED_RULES = [
    # --- extras (<=3 servings/week 로 제한된 것) ---
    (r'fried|french fries|deep.?fried|tempura|batter',       -1, 'extras: fried food'),
    (r'fast food|mcdonald|burger king|kfc|taco bell|pizza hut|wendy',
                                                              -1, 'extras: fast food'),
    (r'sausage|frankfurter|hot dog|bologna|salami|bacon|ham,|luncheon|'
     r'pepperoni|bratwurst|chorizo|jerky|spam|loaf, ',        -1, 'extras: processed meat'),
    (r'candy|candies|chocolate|cookie|brownie|cake|pie,|doughnut|donut|'
     r'pastry|ice cream|pudding|syrup|sugars?(?!\s*snap)|honey|jam,|jelly|'
     r'sweet roll',                                           -1, 'extras: sweets'),
    (r'soft drink|soda|cola|energy drink|fruit drink|sports drink|'
     r'lemonade|punch|sweetened bever',                       -1, 'extras: sugary drinks'),
    # 'tomato juice cocktail' · 'fruit cocktail' 은 술이 아니다.
    (r'beer|liquor|whiskey|vodka|gin |rum |tequila|(?<!juice )(?<!fruit )cocktail|'
     r'martini|daiquiri|'
     r'margarita|liqueur|brandy|bourbon|schnapps',            -1, 'extras: spirits/beer'),
    # refined cereals — 통곡물 표기가 없는 빵·시리얼·흰쌀·흰밀가루
    (r'^(bread|bagel|roll|bun|cracker|muffin|pancake|waffle|tortilla|biscuit|'
     r'cereal|pasta|noodle|rice|flour)\b(?!.*(whole|bran|brown|multigrain|'
     r'multi.grain|whole.grain|rye|oat))',                    -1, 'extras: refined cereal'),

    # --- 처방된 12군 ---
    # 'oat' 를 그냥 쓰면 'coated'(튀김옷 입힌 닭) 가 통곡물로 잡힌다.
    (r'whole.?grain|whole.?wheat|multi.?grain|brown rice|\boats?\b|oatmeal|'
     r'barley|quinoa|bulgur|\brye\b|\bbran\b',               +1, 'whole grains 5-8/day'),
    (r'\bolive oil\b|oil, olive',                             +1, 'olive oil 3 tbsp/day'),
    # 처방은 low-fat **unsweetened** dairy 다. 가당·가향 제품은 위 sweets 규칙에
    # 걸리지 않는 것들(바닐라·과일 요구르트 등)을 여기서 뺀다.
    (r'^(?!.*(vanilla|flavored|fruit|sweetened|chocolate|strawberry|honey))'
     r'(.*(milk|yogurt|cheese).*(nonfat|low.?fat|skim|1% |2% |reduced fat|'
     r'part.?skim)|.*(nonfat|low.?fat|skim|reduced fat).*(milk|yogurt|cheese))',
                                                              +1, 'low-fat unsweetened dairy 2-3/day'),
    (r'^egg|egg, whole|egg white|egg yolk',                   +1, 'eggs <=6/week'),
    (r'chicken|turkey',                                       +1, 'chicken 2-3/week'),
    # 처방은 **lean** red meat 이다. FDC 의 'separable lean and fat' 은 지방을
    # 포함한 부위라 처방 대상이 아니다. 'separable lean only' 만 잡는다.
    (r'(beef|lamb|veal).*separable lean only',                +1, 'lean red meat 3-4/week'),
    # 'oyster mushroom' 이 어패류로 잡히지 않도록 버섯을 먼저 거른다.
    (r'mushroom',                                             +1, 'vegetables 6/day'),
    (r'fish|salmon|tuna|sardine|mackerel|cod|haddock|trout|herring|anchov|'
     r'shrimp|crab|oyster|mussel|clam|scallop|squid|lobster',  +1, 'fish >=2/week'),
    (r'bean|lentil|chickpea|\bpeas?\b|legume|soy|tofu|hummus',
                                                              +1, 'legumes 3-4/week'),
    # 콩보다 뒤에 둔다 — 'Pigeon peas, mature seeds, raw' 는 견과가 아니라 콩이다.
    (r'nuts?, .*(raw|unsalted|without salt)|seeds?, .*(raw|unsalted|without salt)',
                                                              +1, 'raw unsalted nuts 1/day'),
    # 'breadfruit' 가 과일로 잡히지 않게 앞 글자를 막는다.
    (r'(?<![a-z])fruit|apple|banana|orange|berr|grape|melon|peach|pear|plum|mango|'
     r'pineapple|kiwi|cherr|apricot|fig|date',                 +1, 'fruit 3/day'),
    (r'vegetable|lettuce|spinach|broccoli|carrot|tomato|onion|cabbage|kale|'
     r'pepper|cucumber|zucchini|squash|celery|asparagus|mushroom|potato|'
     r'cauliflower|eggplant|beet|turnip|radish',               +1, 'vegetables 6/day'),
]


def modimed_labels(foods):
    """음식 이름·카테고리에 ModiMedDiet 라벨을 붙인다.

    +1 처방군 / -1 extras / 0 해당 없음(집계에서 제외).
    """
    text = (foods['food_name'].astype(str) + ' | '
            + foods['food_group'].astype(str)).str.lower()
    label = pd.Series(0, index=foods.index)
    why = pd.Series('', index=foods.index)
    # SMILES 는 성인 우울증 환자 대상이다. 이유식은 처방 대상이 아니므로 뺀다.
    adult = foods['food_group'] != 'Baby Foods'
    for pat, lab, src in MODIMED_RULES:
        hit = adult & (label == 0) & text.str.contains(pat, regex=True, na=False)
        label[hit] = lab
        why[hit] = src
    return label, why


# ModiMedDiet 은 **빈도** 처방이다. 채소 6회/일(주 42회)과 lean red meat 주 3-4회를
# 같은 +1 로 두면 정답셋이 처방 강도를 잃는다(§11 D). MODIMED_POSITIVES 로 고른다.
#   all        처방 12군 전부를 양성으로 (기본, §7 표가 이것이다)
#   high_freq  매일 처방되는 군만 양성으로 — 채소·과일·통곡물·유제품·견과·올리브유
LOW_FREQ_RULES = {'lean red meat 3-4/week', 'chicken 2-3/week', 'eggs <=6/week',
                  'fish >=2/week', 'legumes 3-4/week'}


def modimed_positives(res):
    """양성 마스크를 MODIMED_POSITIVES 규약에 맞춰 돌려준다."""
    lab, why = modimed_labels(res)
    if os.environ.get('MODIMED_POSITIVES', 'all') == 'high_freq':
        lab = lab.copy()
        lab[(lab == 1) & why.isin(LOW_FREQ_RULES)] = 0
    return lab


def modimed_score(res, K):
    """추천 순위를 ModiMedDiet 정답셋으로 채점한다.

    AUC   처방군이 extras 보다 위에 오는 확률 (Mann-Whitney U / n1n2).
          0.5 가 무작위, 1.0 이 완전 분리. 해당 없음(0) 인 음식은 뺀다.
    Top K / Bottom K  각 끝에 처방군·extras 가 몇 개인지.
    """
    lab = modimed_positives(res)
    pos = res.loc[lab == 1, 'score'].values
    neg = res.loc[lab == -1, 'score'].values
    if len(pos) == 0 or len(neg) == 0:
        return {}
    from scipy.stats import mannwhitneyu
    u = mannwhitneyu(pos, neg, alternative='two-sided').statistic
    auc = u / (len(pos) * len(neg))
    top, bot = res.head(K), res.tail(K)
    ltop = modimed_positives(top)
    lbot = modimed_positives(bot)
    # 주지표는 Top K 다. AUC 는 음식 6,000여 개 전체의 순서를 재므로 맨 위에
    # 무엇이 오는지에 둔감하다 — 실제로 AUC 최고 설정의 Top 30 이 처방 0 /
    # extras 19(1위가 증류주)인 경우가 있었다(§13). Top-K 추천의 품질은
    # Top K 안의 구성으로 잰다. AUC 는 참고로 남긴다.
    return {
        f'top{K}_처방군': int((ltop == 1).sum()),
        f'top{K}_extras': int((ltop == -1).sum()),
        f'bot{K}_extras': int((lbot == -1).sum()),
        'modimed_AUC(참고)': round(float(auc), 3),
    }


def external():
    """ModiMedDiet 정답셋 자체를 찍어 본다 — 라벨이 타당한지 사람이 보라고.

    출력
      out/modimed_labels.csv
    """
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    CURATED = ('foundation_food', 'sr_legacy_food', 'survey_fndds_food')
    foods = foods[foods['data_type'].isin(CURATED)].reset_index(drop=True)
    lab, why = modimed_labels(foods)
    foods['modimed'] = lab
    foods['modimed_rule'] = why
    foods.to_csv(os.path.join(OUT, 'modimed_labels.csv'), index=False)

    print(f'  추천 코호트 {len(foods):,}')
    print(f'  처방군(+1) {int((lab == 1).sum()):,} / '
          f'extras(-1) {int((lab == -1).sum()):,} / '
          f'해당 없음 {int((lab == 0).sum()):,}')
    print('\n  규칙별 건수:')
    for rule, n in why[why != ''].value_counts().items():
        print(f'    {n:6,d}  {rule}')
    print('\n  표본 — 처방군:')
    for _, r in foods[lab == 1].sample(8, random_state=0).iterrows():
        print(f'    {r.food_name[:52]:54s} {r.modimed_rule}')
    print('  표본 — extras:')
    for _, r in foods[lab == -1].sample(8, random_state=0).iterrows():
        print(f'    {r.food_name[:52]:54s} {r.modimed_rule}')
    print('  표본 — 해당 없음:')
    for _, r in foods[lab == 0].sample(8, random_state=0).iterrows():
        print(f'    {r.food_name[:52]:54s} {r.food_group}')


def invert():
    """E 의 부호를 ModiMedDiet 라벨에서 역추정하고 공개 소스 E 와 대조한다.

    왜
    --
    성분 중량만으로 ModiMedDiet 처방군/extras 를 가르는 상한은 AUC 0.816 인데,
    ProMENDA 기반 E 는 D = X·e 로 0.520 밖에 내지 못한다. 커버리지는 병목이
    아니다 — E 가 있는 66종만 써도 지도학습은 0.782 다. 전부 **부호**에서 잃는다.

    가설: ProMENDA 는 "우울증 환자에서 이 대사물 농도가 높/낮다"를 재는
    case-control 메타볼로믹스지 "먹으면 좋/나쁘다"가 아니다. 논문 §4.2.1 의 E 는
    그 둘을 동일시한다. 역추정한 E 와 ProMENDA 의 부호를 compound 별로 대조하면
    어디서 갈리는지 목록이 나온다.

    누수 방지 (실행 전에 고정)
    --------------------------
    - 음식 단위로 50/50 분할(seed 0, 층화). E 는 train 음식만 보고 학습한다.
    - 보고하는 AUC 는 test 음식만으로 잰다.
    - 논문 §4.2.3 기준은 학습에 전혀 쓰지 않으므로 독립 체크로 남는다.
    - 유사도 S 는 라벨을 쓰지 않는 비지도 단계라 전체 음식으로 계산한다.

    출력
      out/compound_learned.csv    역추정 E (E_MODE=learned 로 쓸 수 있다)
      out/invert_comparison.csv   compound 별 역추정 부호 vs 공개 소스 부호
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
    from sklearn.metrics import roc_auc_score

    C_REG = float(os.environ.get('INVERT_C', '1.0'))
    SEED = int(os.environ.get('INVERT_SEED', '0'))
    # FEATURES=compound(기본, 논문 F 그대로) | form(구조·가공 축만) | both
    # form 은 build.py form 이 만든 FDC 측정값이다. 라벨이 이름 규칙이므로
    # 측정값만 쓰는 한 누수가 없다(§10).
    FEATURES = os.environ.get('FEATURES', 'compound')

    print('[1/5] 코호트와 라벨')
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    CURATED = ('foundation_food', 'sr_legacy_food', 'survey_fndds_food')
    foods = foods[foods['data_type'].isin(CURATED)].reset_index(drop=True)
    lab, _ = modimed_labels(foods)
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    F = (long.pivot_table(index='food_key', columns='kegg', values='amount_g',
                          fill_value=0.0)
         .reindex(foods['food_key']).fillna(0.0))
    compounds = list(F.columns)
    X = F.values.astype(float)
    colmax = X.max(axis=0)
    X = np.divide(X, colmax, out=np.zeros_like(X), where=colmax > 0)

    if FEATURES in ('form', 'both'):
        fp = os.path.join(OUT, 'food_form.csv')
        if not os.path.exists(fp):
            sys.exit('food_form.csv 가 없다. python3 ourkg/build.py form')
        Ff = (pd.read_csv(fp).set_index('food_key')
              .reindex(foods['food_key']).fillna(0.0))
        Xf = Ff.values.astype(float)
        fmax = np.abs(Xf).max(axis=0)
        Xf = np.divide(Xf, fmax, out=np.zeros_like(Xf), where=fmax > 0)
        if FEATURES == 'form':
            X, compounds = Xf, list(Ff.columns)
        else:
            X = np.hstack([X, Xf])
            compounds = compounds + list(Ff.columns)
        print(f'  FEATURES={FEATURES} -> 특징 {X.shape[1]}')

    m = (lab != 0).values
    y = (lab[m] == 1).astype(int).values
    Xs, keys = X[m], foods.loc[m, 'food_key'].values
    print(f'  라벨 있는 음식 {len(y):,} (처방군 {y.sum():,} / extras {(1-y).sum():,})'
          f' / compound {len(compounds)}')

    print('[2/5] 상한 — 성분 중량만으로 지도학습 (5-fold CV)')
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    oof = cross_val_predict(LogisticRegression(max_iter=2000, C=C_REG), Xs, y,
                            cv=cv, method='predict_proba')[:, 1]
    ceiling = roc_auc_score(y, oof)
    print(f'  AUC {ceiling:.3f}')

    print('[3/5] 50/50 분할로 E 역추정')
    i_tr, i_te = train_test_split(np.arange(len(y)), test_size=0.5,
                                  stratify=y, random_state=SEED)
    clf = LogisticRegression(max_iter=2000, C=C_REG).fit(Xs[i_tr], y[i_tr])
    coef = clf.coef_[0]
    e_learned = coef / (np.abs(coef).max() or 1.0)
    auc_te = roc_auc_score(y[i_te], Xs[i_te] @ coef)
    print(f'  train {len(i_tr):,} / test {len(i_te):,}')
    print(f'  held-out AUC (D = X·e 단독)  {auc_te:.3f}   '
          f'(ProMENDA e_shrunk 0.520 / 상한 {ceiling:.3f})')

    learned = pd.DataFrame({'kegg': compounds, 'e_learned': np.round(e_learned, 4),
                            'coef': np.round(coef, 4)})
    # E_MODE=learned 가 읽는 파일은 compound 축일 때만 덮어쓴다.
    # form/both 는 compound 가 아닌 특징이 섞여 있어 E 로 쓸 수 없다.
    lname = ('compound_learned.csv' if FEATURES == 'compound'
             else f'learned_{FEATURES}.csv')
    learned.to_csv(os.path.join(OUT, lname), index=False)
    print(f'  저장: {lname}')
    if FEATURES != 'compound':
        print('  상위 가중치:')
        for _, r in learned.reindex(learned['e_learned'].abs()
                                    .sort_values(ascending=False).index).head(12).iterrows():
            print(f'    {r.kegg:22s} {r.e_learned:+.3f}')

    if FEATURES != 'compound':
        print('\n  (FEATURES != compound 이므로 부호 대조·파이프라인 단계는 건너뛴다 '
              '— 논문 E 는 compound 축에만 정의된다)')
        return

    print('[4/5] 공개 소스 E 와 부호 대조')
    dep = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
    ev = pd.read_csv(os.path.join(OUT, 'compound_evidence.csv')).set_index('kegg')
    # 이름은 ProMENDA/evidence 에 없을 수 있다 — FDC 영양소 이름으로 보충한다.
    nmap = pd.read_csv(os.path.join(BASE, 'setup', 'nutrient_kegg_map.csv'))
    fdc_name = (nmap.drop_duplicates('nutrient_kegg')
                .set_index('nutrient_kegg')['nutrient_name'].to_dict())

    def cname(c):
        for v in (ev['name'].get(c), dep['name'].get(c), fdc_name.get(c)):
            if isinstance(v, str) and v and v != 'nan':
                return v
        return c

    rows = []
    for i, c in enumerate(compounds):
        pm = float(dep['e_shrunk'].get(c, 0.0))
        rows.append({
            'kegg': c,
            'name': cname(c),
            'e_learned': round(float(e_learned[i]), 4),
            'promenda': round(pm, 4),
            'menda': round(float(ev['menda_score'].get(c, 0.0)), 4),
            'rules': round(float(ev['rules_score'].get(c, 0.0)), 4),
            'afs': round(float(ev['afs_score'].get(c, 0.0)), 4),
            'sign_vs_promenda': ('' if pm == 0 else
                                 ('same' if np.sign(e_learned[i]) == np.sign(pm)
                                  else 'FLIP')),
        })
    cmp_tab = pd.DataFrame(rows)
    cmp_tab['abs'] = cmp_tab['e_learned'].abs()
    cmp_tab = cmp_tab.sort_values('abs', ascending=False).drop(columns='abs')
    cmp_tab.to_csv(os.path.join(OUT, 'invert_comparison.csv'), index=False)

    both = cmp_tab[cmp_tab['sign_vs_promenda'] != '']
    same = int((both['sign_vs_promenda'] == 'same').sum())
    print(f'  둘 다 비영인 compound {len(both)} / 부호 일치 {same} '
          f'({same/len(both)*100:.0f}%)')
    print('\n  역추정 |e| 가 큰 상위 15 — biomarker 방향과 식이 방향이 갈리는 곳')
    print(f'    {"kegg":8s} {"name":30s} {"learned":>8s} {"ProMENDA":>9s}  판정')
    for _, r in cmp_tab.head(15).iterrows():
        print(f'    {r.kegg:8s} {str(r["name"])[:30]:30s} '
              f'{r.e_learned:+8.3f} {r.promenda:+9.3f}  {r.sign_vs_promenda}')

    print('[5/5] 역추정 E 로 논문 Algorithm 1 을 돌린다')
    res = recommend(e_mode='learned', save=False)
    test_keys = set(keys[i_te])
    sub = res[res['food_key'].isin(test_keys)]
    lab_sub, _ = modimed_labels(sub)
    auc_pipe = roc_auc_score((lab_sub == 1).astype(int).values, sub['score'].values)
    K = int(os.environ.get('TOP_K', '30'))
    NOT_OK = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
              'Beef Products', 'Pork Products', 'Lamb, Veal, and Game Products'}
    REC_OK = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
              'Vegetables and Vegetable Products'}
    top, bot = res.head(K), res.tail(K)
    print(f'  held-out 음식 {len(sub):,} 에서 전체 파이프라인 AUC {auc_pipe:.3f}')
    print(f'  (참고: 현재 최고 vote direct 0.665 / 기본 shrunk 0.491)')
    print(f'  §4.2.3 (학습에 쓰지 않은 독립 체크) — '
          f'Top{K} 추천군 {int(top["food_group"].isin(REC_OK).sum())} / '
          f'Bottom{K} 비추천군 {int(bot["food_group"].isin(NOT_OK).sum())}')
    print(f'  Top{K} 첫 음식: {top["food_name"].iloc[0][:50]}')
    print(f'  Bottom{K} 끝 음식: {bot["food_name"].iloc[-1][:50]}')


def stype():
    """ProMENDA 를 연구 설계(Study type)별로 나눠 E 를 만들고 외부 기준으로 잰다.

    왜
    --
    §8 에서 공개 소스 E 의 부호가 ModiMedDiet 과 48% 밖에 맞지 않았고, 그 이유를
    "case-control 메타볼로믹스(농도)와 식이 효과(먹으면 좋/나쁨)는 다른 것을
    잰다"로 봤다. 그렇다면 ProMENDA 안에서도 **개입 효과를 재는 설계**는
    식이 방향에 더 가까워야 한다. 그걸 직접 검정한다.

    ProMENDA 의 M_Study_type_Metabolite_level (M_Groups 로 역추론, map_promenda.py)
      Type1  14,370행  "depression vs control", "CUMS vs control"
                       -> 환자에서 올라간 것. 원인인지 결과인지 모른다.
      Type2   6,169행  "CUMS + fluoxetine vs CUMS", "post-ketamine vs baseline"
                       -> **치료로 올라간 것**. 개입 효과다.
      Type3   1,717행  "rTMS vs control" (대상이 건강인)
                       -> 우울증 방향과 대응하지 않는다. 뺀다.
      Type4     239행  "responder vs non-responder"
                       -> 반응자에서 올라간 것. 개입 효과 쪽이다.
      Type5      24행  표본이 작아 뺀다.

    비교하는 E (전부 공개 소스만, 학습 없음)
      paper      현재 기본값. Type1 만 up=+1 로 뒤집고 나머지는 그대로 (= e_shrunk)
      t1_paper   Type1 만, up=+1 (논문 규약)
      t1_harm    Type1 만, up=-1 (환자에서 오른 것 = 해롭다는 읽기)
      t2         Type2 만, up=+1 (치료로 오른 것 = 이롭다)
      t4         Type4 만, up=+1
      t24        Type2+4, up=+1  <- 개입 효과만 모은 것
      semantic   Type1 up=-1 + Type2/4 up=+1, Type3/5 제외

    학습이 없으므로 ModiMedDiet 라벨 전체로 잰다(누수 없음). 다만 변형 일곱 중
    하나를 이 기준으로 고르는 것은 선택이므로, 전부 보고하고 §4.2.3 도 함께 낸다.

    출력
      out/stype_comparison.csv
      out/compound_depression_stype.csv   변형별 E (E_MODE=stype:<이름> 로 쓸 수 있다)
    """
    from sklearn.metrics import roc_auc_score
    from common import polarity

    SHRINK_K = int(os.environ.get('SHRINK_K', '10'))
    SRC = os.path.join(BASE, '41398_2024_2948_MOESM3_ESM.xlsx')
    STYPE = 'M_Study_type_Metabolite_level'

    print('[1/4] ProMENDA 로드')
    df = pd.read_excel(SRC, sheet_name='M_Metabolite')
    df = df[df['M_KEGG'].astype(str).str.contains(r'C\d{5}', na=False)].copy()
    df['kegg'] = df['M_KEGG'].astype(str).str.extract(r'(C\d{5})')[0]
    df['base'] = df['M_Up/Down_regulated '].apply(polarity)   # up=-1, down=+1
    df['t'] = df[STYPE].astype(str)
    print('  ' + ' / '.join(f'{t} {int(n):,}' for t, n in
                            df['t'].value_counts().sort_index().items()))

    def build(spec):
        """spec: {Type 이름: up 의 부호}. 없는 Type 은 제외."""
        sub = df[df['t'].isin(spec)].copy()
        # base 는 up=-1 이다. spec[t] 가 +1 이면 뒤집는다.
        mult = sub['t'].map(lambda t: -1 if spec[t] > 0 else 1)
        sub['inc'] = sub['base'] * mult
        g = sub.groupby('kegg')['inc']
        pos = g.apply(lambda x: int((x == 1).sum()))
        neg = g.apply(lambda x: int((x == -1).sum()))
        return ((pos - neg) / (pos + neg + SHRINK_K)).to_dict()

    VARIANTS = {
        't1_paper': {'Type1': +1},
        't1_harm':  {'Type1': -1},
        't2':       {'Type2': +1},
        't4':       {'Type4': +1},
        't24':      {'Type2': +1, 'Type4': +1},
        'semantic': {'Type1': -1, 'Type2': +1, 'Type4': +1},
    }
    E = {name: build(spec) for name, spec in VARIANTS.items()}
    dep = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
    E['paper'] = dep['e_shrunk'].to_dict()

    print('[2/4] 음식 행렬과 ModiMedDiet 라벨')
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    foods = foods[foods['data_type'].isin(
        ('foundation_food', 'sr_legacy_food', 'survey_fndds_food'))].reset_index(drop=True)
    lab, _ = modimed_labels(foods)
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    F = (long.pivot_table(index='food_key', columns='kegg', values='amount_g',
                          fill_value=0.0).reindex(foods['food_key']).fillna(0.0))
    compounds = list(F.columns)
    X = F.values.astype(float)
    cmax = X.max(axis=0)
    X = np.divide(X, cmax, out=np.zeros_like(X), where=cmax > 0)
    m = (lab != 0).values
    y = (lab[m] == 1).astype(int).values
    Xs = X[m]
    print(f'  라벨 있는 음식 {len(y):,}')

    lp = os.path.join(OUT, 'compound_learned.csv')
    learned = (pd.read_csv(lp).set_index('kegg')['e_learned'].to_dict()
               if os.path.exists(lp) else {})

    print('[3/4] 변형별 채점')
    rows = []
    out_e = {'kegg': compounds}
    for name in ['paper', 't1_paper', 't1_harm', 't2', 't4', 't24', 'semantic']:
        e = np.array([float(E[name].get(c, 0.0)) for c in compounds])
        out_e[name] = np.round(e, 4)
        nz = int((e != 0).sum())
        auc = roc_auc_score(y, Xs @ e) if nz else float('nan')
        both = [(e[i], learned.get(c, 0.0)) for i, c in enumerate(compounds)
                if e[i] and learned.get(c, 0.0)]
        agree = (sum(1 for a, b in both if np.sign(a) == np.sign(b)) / len(both)
                 if both else float('nan'))
        rows.append({'variant': name, 'n_compound': nz,
                     'modimed_AUC': round(auc, 3),
                     'sign_vs_learned': f'{int(agree*len(both))}/{len(both)}'
                                        if both else '',
                     'agree_pct': round(agree * 100) if both else None})
    tab = pd.DataFrame(rows)
    pd.DataFrame(out_e).to_csv(
        os.path.join(OUT, 'compound_depression_stype.csv'), index=False)
    tab.to_csv(os.path.join(OUT, 'stype_comparison.csv'), index=False)

    print()
    print('=' * 70)
    print('ProMENDA 연구 설계별 E — ModiMedDiet 기준 (학습 없음)')
    print('=' * 70)
    print(tab.to_string(index=False))
    print(f'\n  참고: 역추정 E held-out 0.803 / 성분 중량 상한 0.816 / 무작위 0.500')

    print('\n[4/4] 가장 좋은 변형으로 논문 Algorithm 1 을 돌린다')
    best = tab.loc[tab['modimed_AUC'].idxmax(), 'variant']
    print(f'  (ModiMedDiet 기준 최고: {best})')
    res = recommend(e_mode=f'stype:{best}', save=False)
    K = int(os.environ.get('TOP_K', '30'))
    REC_OK = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
              'Vegetables and Vegetable Products'}
    NOT_OK = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
              'Beef Products', 'Pork Products', 'Lamb, Veal, and Game Products'}
    top, bot = res.head(K), res.tail(K)
    lab_r, _ = modimed_labels(res)
    print(f'  전체 파이프라인 ModiMedDiet AUC '
          f'{roc_auc_score((lab_r[lab_r != 0] == 1).astype(int).values, res.loc[lab_r != 0, "score"].values):.3f}')
    print(f'  §4.2.3 — Top{K} 추천군 {int(top["food_group"].isin(REC_OK).sum())} / '
          f'Bottom{K} 비추천군 {int(bot["food_group"].isin(NOT_OK).sum())}')
    print(f'  Top{K} 첫 음식: {top["food_name"].iloc[0][:50]}')
    print(f'  Bottom{K} 끝 음식: {bot["food_name"].iloc[-1][:50]}')


def disagree():
    """두 평가 기준이 어디서 갈리는지 음식군별로 분해한다.

    §7 에서 "§4.2.3 을 잘 맞추는 설정일수록 ModiMedDiet AUC 가 나쁘다"를 보고,
    그 이유를 "붉은 고기 때문"이라고 적었다. 서술이지 측정이 아니었다. 여기서 잰다.

    세 가지를 낸다.
      A  음식군별로 두 기준이 무엇이라 말하는가 (라벨 교차표)
      B  음식군을 하나씩 빼고 ModiMedDiet AUC 를 다시 재서 영향력을 본다
         (leave-one-group-out). 뺐을 때 AUC 가 오르면 그 군이 깎고 있던 것이다.
      C  §4.2.3 최적 설정(shrunk)과 ModiMedDiet 최적 설정(learned)에서
         음식군의 평균 순위 백분위가 얼마나 움직이는가

    출력
      out/disagreement_by_group.csv
    """
    from sklearn.metrics import roc_auc_score

    REC_OK = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
              'Vegetables and Vegetable Products'}
    NOT_OK = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
              'Beef Products', 'Pork Products', 'Lamb, Veal, and Game Products'}

    print('[1/3] 두 설정의 순위')
    r_shrunk = recommend(e_mode='shrunk', save=False)
    r_learned = recommend(e_mode='learned', save=False)
    for r in (r_shrunk, r_learned):
        r['pct'] = 100.0 * (1 - r['rank'] / len(r))     # 100 = 최상위

    base = r_shrunk[['food_key', 'food_name', 'food_group', 'score', 'pct']].copy()
    base = base.rename(columns={'score': 'score_shrunk', 'pct': 'pct_shrunk'})
    base = base.merge(
        r_learned[['food_key', 'score', 'pct']].rename(
            columns={'score': 'score_learned', 'pct': 'pct_learned'}),
        on='food_key')
    lab, _ = modimed_labels(base)
    base['modimed'] = lab.values

    print('[2/3] A — 음식군별 두 기준의 말')
    rows = []
    sub = base[base['modimed'] != 0]
    y_all = (sub['modimed'] == 1).astype(int).values
    auc_s = roc_auc_score(y_all, sub['score_shrunk'].values)
    auc_l = roc_auc_score(y_all, sub['score_learned'].values)
    print(f'  전체 ModiMedDiet AUC — shrunk {auc_s:.3f} / learned {auc_l:.3f}')

    for g, part in base.groupby('food_group'):
        p = int((part['modimed'] == 1).sum())
        e = int((part['modimed'] == -1).sum())
        n = int((part['modimed'] == 0).sum())
        paper = ('추천군' if g in REC_OK else
                 ('비추천군' if g in NOT_OK else '-'))
        # B — 이 군을 빼고 다시 잰 AUC
        keep = sub['food_group'] != g
        d_s = d_l = float('nan')
        yk = (sub.loc[keep, 'modimed'] == 1).astype(int).values
        if len(set(yk)) == 2:
            d_s = roc_auc_score(yk, sub.loc[keep, 'score_shrunk'].values) - auc_s
            d_l = roc_auc_score(yk, sub.loc[keep, 'score_learned'].values) - auc_l
        rows.append({
            'food_group': g, 'n': len(part),
            'paper_§4.2.3': paper,
            'modimed_처방': p, 'modimed_extras': e, 'modimed_미분류': n,
            'conflict': ('O' if (paper == '비추천군' and p > e)
                         or (paper == '추천군' and e > p) else ''),
            'pct_shrunk': round(part['pct_shrunk'].mean(), 1),
            'pct_learned': round(part['pct_learned'].mean(), 1),
            'pct_이동': round(part['pct_learned'].mean() - part['pct_shrunk'].mean(), 1),
            'drop_dAUC_shrunk': round(d_s, 4),
            'drop_dAUC_learned': round(d_l, 4),
        })
    tab = pd.DataFrame(rows).sort_values('n', ascending=False)
    tab.to_csv(os.path.join(OUT, 'disagreement_by_group.csv'), index=False)

    print('\n  두 기준이 충돌하는 음식군 (논문은 비추천인데 ModiMedDiet 은 처방 우세)')
    conf = tab[tab['conflict'] == 'O']
    cols = ['food_group', 'n', 'paper_§4.2.3', 'modimed_처방', 'modimed_extras',
            'modimed_미분류']
    print(conf[cols].to_string(index=False) if len(conf) else '  없음')

    print('\n[3/3] B — 음식군을 빼면 ModiMedDiet AUC 가 얼마나 움직이나')
    print('  (양수 = 그 군을 빼면 AUC 가 오른다 = 그 군이 깎고 있었다)')
    inf = tab.reindex(tab['drop_dAUC_shrunk'].abs().sort_values(
        ascending=False).index).head(8)
    print(f'    {"food_group":36s} {"n":>5s} {"shrunk":>9s} {"learned":>9s}')
    for _, r in inf.iterrows():
        print(f'    {r.food_group[:36]:36s} {r.n:5d} '
              f'{r.drop_dAUC_shrunk:+9.4f} {r.drop_dAUC_learned:+9.4f}')

    # ------------------------------------------------------------------
    # D — 정답셋 자체의 결함 점검: ModiMedDiet 은 **빈도** 처방이다.
    #     채소 6회/일(주 42회) 과 lean red meat 주 3-4회를 우리 라벨은 똑같이
    #     +1 로 둔다. 충돌이 전부 붉은 고기에서 나온다면, 저빈도 처방군을
    #     양성에서 빼도 결론이 유지되는지 봐야 한다.
    # ------------------------------------------------------------------
    LOW_FREQ = {'lean red meat 3-4/week', 'chicken 2-3/week', 'eggs <=6/week',
                'fish >=2/week', 'legumes 3-4/week'}
    print('\n  D — 저빈도 처방군을 양성에서 빼면 (ModiMedDiet 은 빈도 처방이다)')
    _, why_all = modimed_labels(base)
    hi = base['modimed'].values.copy()
    hi[(base['modimed'].values == 1) & why_all.isin(LOW_FREQ).values] = 0
    sub2 = base[hi != 0]
    y2 = (hi[hi != 0] == 1).astype(int)
    a_s2 = roc_auc_score(y2, sub2['score_shrunk'].values)
    a_l2 = roc_auc_score(y2, sub2['score_learned'].values)
    print(f'    고빈도 처방군(채소·과일·통곡물·유제품·견과·올리브유) {int(y2.sum()):,} '
          f'vs extras {int((1-y2).sum()):,}')
    print(f'    AUC — shrunk {a_s2:.3f} (전체 {auc_s:.3f}) / '
          f'learned {a_l2:.3f} (전체 {auc_l:.3f})')

    print('\n  C — 순위 백분위가 가장 많이 움직인 음식군 (shrunk -> learned)')
    mv = tab.reindex(tab['pct_이동'].abs().sort_values(ascending=False).index).head(8)
    print(f'    {"food_group":36s} {"n":>5s} {"shrunk":>7s} {"learned":>8s} {"이동":>7s}')
    for _, r in mv.iterrows():
        print(f'    {r.food_group[:36]:36s} {r.n:5d} '
              f'{r.pct_shrunk:7.1f} {r.pct_learned:8.1f} {r.pct_이동:+7.1f}')


STEPS = {'recommend': recommend, 'compare': compare, 'external': external,
         'invert': invert, 'stype': stype, 'disagree': disagree,
         'pathcheck': pathcheck, 'evaluate': evaluate}


def main(argv):
    want = argv or list(STEPS)
    unknown = [w for w in want if w not in STEPS]
    if unknown:
        sys.exit(f'알 수 없는 단계 {unknown}. 가능: {list(STEPS)}')
    for name in want:
        print(f'\n{"=" * 70}\n== {name}\n{"=" * 70}', flush=True)
        STEPS[name]()


if __name__ == '__main__':
    main(sys.argv[1:])
