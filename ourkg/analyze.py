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
from common import OUT, BASE, CACHE, compound_microbe


def mental_taxids():
    """정신질환·신경퇴행에 연관된 미생물 taxid 집합.

    두 출처를 합친다 — 배포 `Disease_Bacteria`(MeSH F03 판정)와 Disbiome.
    Disbiome 쪽이 질환 23 종·균 457 종으로 훨씬 두껍다.
    """
    out = set()
    for fn, cols in (('microbe_disease.csv', ('is_mental',)),
                     ('microbe_disease_disbiome.csv', ('is_mental', 'is_neuro'))):
        path = os.path.join(OUT, fn)
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, dtype={'taxid': str})
        m = False
        for c in cols:
            if c in df:
                m = m | df[c].fillna(False).astype(bool)
        out |= set(df[m]['taxid'])
    return out


def gutbrain_weight(compounds):
    """compound 별 **미생물 매개 경로 지지도** w (길이 = len(compounds)).

    논문 §4.2.2 의 식 (1)(2) 에는 미생물이 없다. 그래서 KG 최대 소스인
    VMH 44,094 쌍이 추천 점수에 **0 기여**한다 — §1·§3.1 이 내세우는 gut-brain
    axis 가 알고리즘에 연결되지 않는다. 이것은 논문 알고리즘의 정의 때문이지
    우리 구현의 한계가 아니다 ([`METHODS.md`](METHODS.md) 한계).

    `PATH_MODE=gutbrain` 은 미생물을 거치지 않는 compound 의 E 를 **0 으로
    죽이는** 이분법이라 compound 가 절반으로 줄고 Top-K 가 흔들렸다. 여기서는
    죽이지 않고 **가중**한다 — 우울증 연관 균이 대사하는 compound 를 더 세게
    본다.

        w[c] = 1 + ALPHA * s[c]        s[c] in [0, 1]

    `s[c]` 는 그 compound 를 대사하는 **정신질환 연관 균의 수**를 0~1 로 민 것.
    `ALPHA=0` 이면 w 가 전부 1 이라 **논문 경로와 완전히 같다** (기본값).

    환경변수
      GUTBRAIN_ALPHA   가중 세기. 0 = 끔(기본)
      GUTBRAIN_SOURCE  kegg | vmh | both (기본 both)
      GUTBRAIN_RANK    species(기본) | all — 속 수준 매칭을 넣을지
                       (KEGG 링크의 55% 가 속 수준이다. DATA.md §6)
      GUTBRAIN_SCALE   count(기본, 균 수를 최대값으로 나눔) | binary(있으면 1)
                       | log(log1p 후 최대값으로 나눔)
    """
    alpha = float(os.environ.get('GUTBRAIN_ALPHA', '0'))
    if not alpha:
        return np.ones(len(compounds)), 0

    src = os.environ.get('GUTBRAIN_SOURCE', 'both')
    rank = os.environ.get('GUTBRAIN_RANK', 'species')
    if src == 'measured':
        # 측정 상관으로 만든 링크 (metabolome_check.py build). 속 수준이라
        # 우리 taxid 로 펼친다 — 같은 속의 종이 여럿이면 전부 받는다.
        mp = os.path.join(OUT, 'compound_microbe_measured.csv')
        if not os.path.exists(mp):
            sys.exit('compound_microbe_measured.csv 가 없다. '
                     'python3 ourkg/metabolome_check.py build')
        meas = pd.read_csv(mp)
        mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'),
                          dtype={'taxid': str}).fillna('')
        mic['genus'] = mic['name'].astype(str).str.split().str[0]
        cm = meas.merge(mic[['taxid', 'genus']], on='genus')[['taxid', 'kegg']]
        cm = cm.drop_duplicates()
    else:
        sources = ('kegg', 'vmh') if src == 'both' else (src,)
        cm = compound_microbe(sources=sources, rank=None if rank == 'all' else rank)
    # 어느 균 집합으로 가중할 것인가.
    #   mental  우리 KG 가 정신질환에 연결한 균 (기본) — Disbiome + 배포 F03
    #   rct     **외부** 기준: 우울/불안 RCT 에서 시험된 균
    #           (setup/probiotic_rct.csv, PubMed RCT 203 편에서 뽑은 25 종)
    who = os.environ.get('GUTBRAIN_MICROBES', 'mental')
    if who == 'rct':
        taxa = set(pd.read_csv(os.path.join(BASE, 'setup', 'probiotic_rct.csv'),
                               dtype={'taxid': str}).taxid)
    else:
        taxa = mental_taxids()
    cm = cm[cm['taxid'].isin(taxa)]
    n = cm.groupby('kegg')['taxid'].nunique()

    scale = os.environ.get('GUTBRAIN_SCALE', 'count')
    v = np.array([float(n.get(c, 0)) for c in compounds])
    if scale == 'binary':
        s = (v > 0).astype(float)
    elif scale == 'log':
        s = np.log1p(v)
        s = s / s.max() if s.max() else s
    else:
        s = v / v.max() if v.max() else v
    print(f'  GUTBRAIN_ALPHA={alpha} MICROBES={who} SOURCE={src} RANK={rank} SCALE={scale} '
          f'— 경로 있는 compound {int((v > 0).sum())}/{len(compounds)} '
          f'(균 중앙값 {np.median(v[v > 0]) if (v > 0).any() else 0:.0f})')
    return 1.0 + alpha * s, int((v > 0).sum())


def serving_grams(foods):
    """음식당 **1 회 섭취량(g)**. FDC food_portion 의 중앙값, 결측은 음식군 중앙값.

    `F` 가 g/100 g 이라 "100 g 먹었을 때" 를 가정한다. 그런데 향신료는 1 회
    4.2 g, 음료는 193 g 이다 — **46 배** 차이다. 이 왜곡이 기각된 설정 둘에서
    같은 꼴로 드러났다 (RESULTS §15d):

      `all+auto`      상위가 말린 향신료 (파프리카·오레가노)
      `E_MODE=nhanes` 상위가 영양 강화 분말

    둘 다 1 회 섭취량이 작은데 100 g 당 농도가 높은 식품이다.

    **논문을 벗어난다** — §4.1.2 는 "each food instance's unit weight is
    standardized to 100 g" 라고 명시한다. 그래서 `F_SCALE` 의 선택지로 두고
    기본값은 `per100g` 다.

    커버리지가 56% 뿐이라(12,513 중 6,970) 결측을 어떻게 다루느냐가 결과를
    가른다. 음식군 중앙값으로 메우고, 아예 없으면 전체 중앙값을 쓴다.
    """
    d = os.path.join(CACHE, 'fdc_portion')
    files = [os.path.join(d, f) for f in ('survey.csv', 'sr_legacy.csv')
             if os.path.exists(os.path.join(d, f))]
    if not files:
        sys.exit('ourkg/cache/fdc_portion/ 가 비었다 — FDC food_portion.csv 가 필요하다 '
                 '(DATA.md §1 참조)')
    fp = pd.concat([pd.read_csv(f, dtype=str) for f in files])
    fp['g'] = pd.to_numeric(fp.gram_weight, errors='coerce')
    med = fp[fp.g > 0].groupby('fdc_id').g.median()
    s = foods['fdc_id'].astype(str).map(med)
    n_have = int(s.notna().sum())
    by_group = s.groupby(foods['food_group']).transform('median')
    s = s.fillna(by_group).fillna(s.median())
    print(f'  F_SCALE=serving — 서빙 보유 {n_have:,}/{len(foods):,} '
          f'({n_have / max(len(foods), 1) * 100:.0f}%), 나머지는 음식군 중앙값. '
          f'중앙값 {s.median():.0f} g')
    return s


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
    elif E_MODE.startswith('nhanes'):
        # 섭취-결과 기반 E (ourkg/nhanes.py). ProMENDA 의 "환자에서 농도가
        # 높다" 와 달리 "먹으면 어떻게 되나" 를 잰다 — RESULTS §9·§15b.
        np_ = os.path.join(OUT, 'compound_depression_nhanes.csv')
        if not os.path.exists(np_):
            sys.exit('compound_depression_nhanes.csv 가 없다. python3 ourkg/nhanes.py')
        _nh = pd.read_csv(np_).set_index('kegg')
        # nhanes = q<0.05 만(보수적) · nhanes_all = 전부
        col = _nh['e_nhanes' if E_MODE == 'nhanes_all' else 'e_sig']
    elif E_MODE == 'binary':
        col = E_df['e_binary']
    elif E_MODE == 'sig':
        col = E_df['e_binary'].where(E_df['q'] < 0.05, 0.0)
    else:
        col = E_df['e_shrunk']
    e = np.array([col.get(c, 0.0) for c in compounds], dtype=float)
    # 특정 compound 의 E 를 0 으로 둔다 (진단용).
    # §15b 검정 ⑦ 에서 에탄올(C00469 e=+0.200)·설탕(C00089 e=+0.259)이 양수인
    # 것이 드러났다. ProMENDA 의 up/down 은 "우울증 환자에서 이 대사물이 높다"
    # 이지 "먹으면 좋다" 가 아니다(§9) — 그 불일치가 F 열에 남은 자리다.
    # 유사도 평활화가 덮고 있을 뿐이라, 영향 크기를 재려고 둔다.
    E_ZERO = [c for c in os.environ.get('E_ZERO', '').split(',') if c]
    if E_ZERO:
        _hit = [i for i, c in enumerate(compounds) if c in E_ZERO]
        for i in _hit:
            e[i] = 0.0
        print(f'  E_ZERO={",".join(E_ZERO)} — {len(_hit)}개 열의 E 를 0 으로')
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

    # gut-brain 가중. ALPHA=0 이면 w 가 전부 1 이라 논문 경로와 동일하다.
    w, _n_gb = gutbrain_weight(compounds)
    e = e * w
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
    # 1 회 섭취량 기준으로 바꾸기 — 논문은 100 g 고정이다(§4.1.2).
    F_SCALE = os.environ.get('F_SCALE', 'per100g')
    if F_SCALE == 'serving':
        _sv = serving_grams(foods.loc[F.index].reset_index()).values
        F = F.mul(_sv / 100.0, axis=0)
    elif F_SCALE != 'per100g':
        sys.exit(f'F_SCALE 은 per100g 또는 serving. 받은 값: {F_SCALE}')

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
    gnames = sub['food_group'].unique()     # 모듈 함수 groups() 를 가리지 않게
    cmap = plt.get_cmap('tab20')
    for i, gname in enumerate(gnames):
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

        # 질의는 FDC nutrient 를 id 로 묻는다. 전에는 그것을 KEGG 로 접어 F 층
        # (food_compound_long)에서 찾았는데, F 는 KEGG 당 **대표 측정치 하나**만
        # 남긴 표라 "Folate, DFE"(1190)·"Vitamin B-6"(1175) 같은 질문이 요구하는
        # 값을 잃었다. 이제 KG 층(food_compound_kg)에서 nutrient_id 로 바로 찾는다.
        # 우리 표는 g, 공개 KG 는 FDC 원 단위(mg/µg)다. 공통 음식에서 잰
        # 배율은 모두 10^3 이었다 (ourkg/RESULTS.md 방법 1).
        G_TO_FDC = 1000.0

        class OurKG(m1.KG):
            def __init__(self):
                dd = collections.defaultdict
                foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
                mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str})
                md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'),
                                 dtype={'taxid': str})
                # compound-미생물은 **두 출처를 합쳐** 본다. KEGG 추론 경로만 보면
                # metabolizes() 가 VMH/AGORA2 의 경로를 놓친다 (#6 의 Adlercreutzia
                # x citric acid 가 그 경우다). 출처 구분은 KG 가 들고 있다.
                #
                # **종 수준만 쓴다.** 방법 1 의 #6·#7 은 Adlercreutzia
                # equolifaciens, Bifidobacterium longum 을 이름으로 콕 집는다.
                # 속 수준 매칭으로 답하면 "이 속의 어떤 유전체가" 를 "이 종이" 로
                # 바꿔 읽는 것이다 (KEGG 링크의 55% 가 속 수준이다).
                cm = compound_microbe(rank='species')
                cd = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))

                self.food = dict(zip(foods.fdc_id, foods.food_name))
                key2fdc = dict(zip(foods.food_key, foods.fdc_id))

                # 성분 중량과 nutrient -> KEGG 는 **KG 층**에서 온다. 공개 KG 의
                # nut2kegg 와 같은 뜻(FDC nutrient id -> KEGG)이 되도록 nutrient_id
                # 를 키로 쓴다 — 전에는 인덱스를 키로 둬 이름만 같고 뜻이 달랐다.
                self.w = dd(dict)
                _kg = pd.read_csv(os.path.join(OUT, 'food_compound_kg.csv'))
                # KG 층은 F 코호트(MIN_COV>=20) 밖 음식도 담는다. 그 음식들도
                # 질의 대상이므로 self.food 에 등록한다 — 안 하면 KG 에 넣어 놓고
                # 질의가 못 본다 (방법 1 #6 의 grape juice 가 그 경우였다).
                self.food.update(dict(zip(_kg.fdc_id, _kg.food_name)))
                self.nut2kegg = dict(zip(_kg.nutrient_id, _kg.kegg))
                for _nid, _g in _kg.groupby('nutrient_id'):
                    self.w[int(_nid)] = {int(f): v * G_TO_FDC
                                         for f, v in zip(_g.fdc_id, _g.amount_g)}

                # 카테고리: FDC 세분류 → SR 27군 두 층 + 온톨로지 라벨.
                self.f2c, self.clab, self.csub = dd(set), {}, dd(set)
                fine_uri_lbl = {}
                from common import normkey as _nk
                _nrm = lambda x: _nk(x, 'a-z').replace(' ', '')
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

                # 질환 상위 분류 (out/disease_tree.csv) — #12 가 쓰는 축.
                self.dtree = {}
                _dt = os.path.join(OUT, 'disease_tree.csv')
                if os.path.exists(_dt):
                    for _d, _a in pd.read_csv(_dt)[['disease', 'ancestor']].dropna().values:
                        self.dtree.setdefault(str(_d), set()).add(str(_a))

                # FoodOn 축 — 음식의 클래스와 조상을 모두 카테고리로 단다.
                import foodon_match as _fm
                _k2f = dict(zip(foods.food_key, foods.fdc_id))
                _n = 0
                for _fk, _labs in _fm.labels_by_food().items():
                    _fdc = _k2f.get(_fk)
                    for _lab in (_labs if _fdc is not None else ()):
                        self.clab[f'onto:FoodOn/{_lab}'] = _lab
                        self.f2c[int(_fdc)].add(f'onto:FoodOn/{_lab}')
                        _n += 1
                print(f'  FoodOn 카테고리 링크 {_n:,}')

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
        _art = int(((b.ourkg_reproduced == 'O') & b.no.isin(m1.PAPER_DEFECT)).sum())
        if _art:
            print(f'  ※ 재현 {rep} 중 {_art} 건은 논문 Query 1 결함을 재연한 것이다'
                  f' — 주지표는 재현+타당 쪽이다 (eval/m1.PAPER_DEFECT)')
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

        # 꼬리의 일반 명사를 떨구는 사다리. 음식 쪽만 사다리를 주고 있었는데,
        # 논문 Table 5 의 **질환 쪽 표기**도 그대로는 안 걸린다 —
        # "parkinson disorder" 는 0 건이고 MeSH 표기는 "Parkinson Disease" 다.
        # "Egg products" 도 1 건뿐이다. 양쪽에 같은 사다리를 준다.
        _TAIL = r'\s+(products?|disorders?|disease)$'

        def _generic(t):
            out, t = [], str(t).strip()
            if t:
                out.append(t)
            g = re.sub(_TAIL, '', t, flags=re.I).strip()
            if g and g.lower() != t.lower():
                out.append(g)
            return out or ['']

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

        # 판정은 **초록 판독**이다 — 논문이 수작업으로 한 것을 efetch 로 자동화한다.
        # 두 엔티티가 한 문장에 함께 나오고 연관 표현이 있으면 +1, 부정이면 -1.
        # 논문 Table 5 15 건으로 세 자를 재어 고른 것이다 (confirmed 11 / non-conf 4):
        #   3항(두 엔티티+근거 물질) 1/11 vs 0/4 · 2항 10/11 vs 3/4 · 초록 10/11 vs 1/4
        # 색인 공출현 두 자는 버렸다. 상세는 RESULTS §4.3.
        ASSOC = (r'associat|correlat|linked|relationship|risk|comorbid|predict|'
                 r'effect|influenc|contribut|increas|decreas|reduc|improv|'
                 r'protect|prevalen')
        # 음성 결론 표현. 처음에는 "no significant association" 계열만 담았는데
        # 30 건에서 한 번밖에 안 걸렸다. 초록이 실제로 쓰는 꼴을 더 담는다 —
        # 특히 **보정 후 사라지는 경우**(논문 #10 의 근거가 이것이다: "BMI 를
        # 넣으면 유의하지 않다")와 귀무 결과 서술.
        NEG = (r'\bno\s+(significant\s+|clear\s+|consistent\s+)?(association|'
               r'correlation|relationship|difference|effect|evidence|link)|'
               r'not\s+(significantly\s+|statistically\s+)?(associat|correlat|'
               r'relat|differ|link)|failed to|'
               r'did not (differ|associat|reach|show|find)|unrelated|'
               r'\bnull\s+(association|finding|result)|'
               r'no longer (significant|associat)|'
               r'(attenuated|disappeared|lost significance|non-?significant)')
        ABS_K = int(os.environ.get('ABS_K', '20'))      # 읽을 초록 수

        # 음식 행에는 **식이 맥락**을 함께 요구한다. 이게 없으면 "mustard oil 로
        # 내장통증을 유발했다"(자극제)나 우울증 병력이 적힌 증례 보고가 +1 로 잡힌다.
        DIET = (r'diet|dietary|intake|consum|ingest|eating|nutrition|food|meal|'
                r'supplement|feeding|serving|beverage|drink')
        # 동형이의어 — 'inbreeding depression'(근친교배 약세)·'ST-segment
        # depression' 은 우울증이 아니다. 이런 수식어가 붙은 문장은 버린다.
        HOMOGRAPH = (r'(inbreeding|outbreeding|st[- ]segment|spreading|respiratory|'
                     r'economic|freezing[- ]point|bone marrow|immunosuppress)\s+'
                     r'depress')

        def _stem(t):
            """엔티티 이름 -> 문장에서 찾을 패턴.

            어간을 몇 글자로 자르지 않는다(Mustard -> musta 가 무관한 단어까지
            걸렸다). 여러 단어 이름은 **구(句)로** 맞춘다 — 사이에 한 단어까지만
            허용한다. 가장 긴 단어 하나만 쓰면 `Sex behavior disorder` 가
            "REM sleep **behavior** disorder" 를 잡는다. 논문 15 건으로 재어
            판별력 0.83 이 유지되는 것을 확인하고 넣었다 (RESULTS §4.3).
            """
            t = re.sub(r'\b(disorder|disorders|disease|diseases|products|total)\b',
                       '', t, flags=re.I)
            w = [x.lower() for x in re.split(r'\W+', t.strip()) if len(x) > 2]
            if not w:
                return None
            if len(w) > 1:
                return r'\b' + r'(?:\W+\w+){0,1}\W+'.join(
                    re.escape(x) + r'\w*' for x in w) + r'\b'
            b = re.escape(w[0])
            # autistic/autism 처럼 어미가 갈리는 질환명은 공통 어간까지만 쓴다.
            for a in ('autis', 'depress', 'anxi', 'schizo'):
                if b.startswith(a):
                    return a + r'\w*'
            return rf'\b{b}(s|es|\'s)?\b'

        def search_read(terms):
            """색인 검색 + 상위 ABS_K 편의 제목·초록. (적중 수, PMID, 본문)
            증례 보고는 한 사람의 병력 나열이라 연관의 근거가 못 되므로 뺀다."""
            def eu(cgi, **kw):
                r = S.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/' + cgi,
                          params=dict(db='pubmed', **kw), timeout=120)
                time.sleep(0.4)
                return r
            q = ' AND '.join(f'"{t}"' for t in terms if t)
            try:
                d = eu('esearch.fcgi', term=q, retmax=ABS_K, retmode='json',
                       sort='relevance').json()['esearchresult']
                n, ids = int(d['count']), d.get('idlist', [])
            except Exception:
                return 0, [], {}
            if not ids:
                return n, [], {}
            txt = eu('efetch.fcgi', id=','.join(ids), retmode='xml',
                     rettype='abstract').text
            docs = {}
            for m in re.finditer(r'<PubmedArticle>.*?</PubmedArticle>', txt, re.S):
                a, pid = m.group(0), re.search(r'<PMID[^>]*>(\d+)</PMID>', m.group(0))
                if pid and 'Case Reports' not in a:
                    docs[pid.group(1)] = re.sub(r'<[^>]+>', ' ', ' '.join(
                        re.findall(r'<(?:ArticleTitle|AbstractText)[^>]*>(.*?)'
                                   r'</(?:ArticleTitle|AbstractText)>', a, re.S)))
            return n, ids, docs

        # 개수 비교(`pos > neg`)는 음성 증거를 구조적으로 묻는다. 연관 문장은
        # 19·25·45 까지 올라가는데 음성은 0~1 이라, **한 건의 음성 증거로는 절대
        # 못 뒤집는다.** 비율로 바꾼다 — 음성이 전체 판정 문장의 NEG_RATIO 이상일
        # 때 -1.
        #
        # 정답이 -1 인 사례가 논문 #10 하나뿐이라 이 문턱은 **약하게만 식별된다.**
        # 한 건에 맞춰 고르면 과적합이므로, 논문 15 건 전체 일치율로 고르고
        # 그 민감도를 RESULTS.md 에 남긴다.
        NEG_RATIO = float(os.environ.get('NEG_RATIO', '0.5'))
        # 연관 어휘가 **두 개체를 걸치는 구간**에 있을 때만 세는 제약. 재 보고
        # **기각했다** — 논문 15 건 일치가 12 -> 11 로 내려간다. #6 의 나열 문장을
        # 6 -> 1 로 줄이지만 #8(Garlic x Alzheimer)을 깬다. 마늘 연구는
        # `garlic extract`·`allicin` 으로 쓰지 `dietary` 를 안 써서, 식이 맥락
        # 게이트와 **곱해지면** 통과 문장이 전부 떨어진다. 되돌릴 수 있게 남긴다.
        ASSOC_SPAN = os.environ.get('ASSOC_SPAN', '0') != '0'

        def _verdict(pos, neg):
            if not (pos or neg):
                return 0
            return -1 if neg / (pos + neg) >= NEG_RATIO else 1

        def _standalone(low, pat):
            """개체 매치가 **독립 토큰**인가. 복합어 조각이면 아니다.

            논문 #10 에서 'egg' 가 `vegetable-egg-beans-milk dietary pattern` 의
            조각으로 걸렸다. 그 문장은 달걀이 아니라 **식이 패턴**을 말한다.
            하이픈으로 앞뒤에 붙어 있으면 그 개체를 가리킨 것이 아니다.
            """
            for m in re.finditer(pat, low):
                before = low[m.start() - 1] if m.start() else ' '
                after = low[m.end()] if m.end() < len(low) else ' '
                if not (before == '-' and after in '-abcdefghijklmnopqrstuvwxyz'):
                    return m
            return None

        def _assoc_between(low, pa, pb):
            """연관 어휘가 **두 개체를 걸치는 구간**에 있는가.

            문장 어디든 ASSOC 가 있으면 세던 것이 1 차 문제였다. 논문 #6 의
            `Alzheimer's disease (AD), Parkinson's disease (PD), and autism
            spectrum disorder (ASD)` 는 **나열**이지 둘을 서로 말한 게 아닌데
            문장 끝의 다른 동사로 양성이 됐다.

            구간은 첫 매치 **앞 60 자**부터 둘째 매치 뒤 40 자까지다. 앞을 포함하는
            것은 `association between X and Y` 처럼 어휘가 둘보다 앞에 오기
            때문이다. 나열은 사이에 연관 동사가 없어 떨어진다.
            """
            if not (pa and pb):
                return False
            ma, mb = _standalone(low, pa), _standalone(low, pb)
            if not (ma and mb):
                return False
            if not ASSOC_SPAN:
                return bool(re.search(ASSOC, low))
            lo, hi = sorted([ma.start(), mb.start()])
            return bool(re.search(ASSOC, low[max(0, lo - 60):hi + 40]))

        def judge(terms, evidence, ladder=None, diet=False):
            """한 건을 초록 판독으로 판정한다 (1 / 0 / -1).

            음식명은 일반명 사다리를 올리며 재시도한다. 우리 15 건과 논문 자신의
            15 건을 **같은 함수로** 잰다 — 보정값이 자의 차이가 아니라 대상의
            차이가 되도록.
            """
            # 두 항 **모두** 사다리를 탄다. 한쪽만 내리면 상대 항 표기가 안 맞는
            # 경우(논문 #11 "parkinson disorder" 0 건)를 못 넘는다. 첫 항을 먼저
            # 내리고, 그래도 초록이 없으면 둘째 항을 내린다.
            second = terms[1] if len(terms) > 1 else ''
            rungs = [(a, b) for a in (ladder or _generic(terms[0]))
                     for b in _generic(second)]
            n = pos = neg = 0
            ids, docs, term, lv = [], {}, terms[0], 0
            best = (10 ** 9, '')
            for lv, (term, second_t) in enumerate(rungs):
                n, ids, docs = search_read([term, second_t] + terms[2:])
                pa, pb = _stem(term), _stem(second_t)
                pos, neg = 0, 0
                best = (10 ** 9, '')
                for pid, body in docs.items():
                    sents = re.split(r'(?<=[.!?])\s+', body)
                    for si, sent in enumerate(sents):
                        low = sent.lower()
                        # **문장 쌍 창.** 초록은 앞 문장에서 개체를 말하고 다음
                        # 문장에서 "No significant association was observed." 처럼
                        # 개체 이름 없이 끊어 쓴다. 한 문장만 보면 그 음성 결론이
                        # 통째로 안 세어진다 — 30 건에서 sent_negative 가 1 인 것이
                        # 단 한 건이었던 이유다. 판정 단서는 이 문장에서 찾고,
                        # 개체는 **앞 문장까지** 포함한 창에서 찾는다.
                        ctx = (sents[si - 1] + ' ' + sent).lower() if si else low
                        if not (pa and pb and _standalone(ctx, pa)
                                and _standalone(ctx, pb)):
                            continue
                        # 동음이의·식이 맥락 게이트는 **이 문장**에서 본다.
                        # 창으로 넓혔더니 앞 문장의 식이 단어로 통과해 우리 15 건의
                        # 판정이 9/6 -> 13/2 로 확 느슨해졌다. 창은 끊어 쓴 음성
                        # 결론을 잡으려고 둔 것이지 게이트를 풀려고 둔 게 아니다.
                        if re.search(HOMOGRAPH, low):
                            continue        # 우울증이 아닌 'depression'
                        if diet and not re.search(DIET, low):
                            continue        # 음식 행은 식이 맥락이 있어야 센다
                        if re.search(NEG, low):
                            neg += 1
                        elif _assoc_between(low, pa, pb):
                            pos += 1
                            # 인용문은 **첫 매치가 아니라** 두 엔티티가 가장 가까이
                            # 붙은 문장으로 고른다. 첫 매치를 쓰면 "psychedelics 가
                            # 담배·섭식… 을 개선" 처럼 두 질환이 나열에만 같이 든
                            # 문장이 걸린다. 가까울수록 둘을 **서로** 말한 문장이다.
                            m1, m2 = _standalone(low, pa), _standalone(low, pb)
                            lo, hi = sorted([m1.start(), m2.start()])
                            if hi - lo < best[0]:
                                # 문장 앞 90 자가 아니라 **매치 주변**을 보여준다.
                                # 앞을 자르면 정작 두 엔티티가 나온 대목이 잘린다.
                                w = sent.strip()[max(0, lo - 30):hi + 60]
                                best = (hi - lo, f'{pid}: …{w}…' if lo > 30
                                        else f'{pid}: {w}…')
                if pos or neg:
                    break
            return {'evidence': evidence, 'pubmed': ';'.join(ids[:2]),
                    'term_used': term, 'term_level': lv,
                    'n_hits_pair_only': n, 'n_abstracts': len(docs),
                    'sent_assoc': pos, 'sent_negative': neg, 'quote': best[1],
                    'result': _verdict(pos, neg)}

        from paper_data import TABLE5 as _PT5
        cases = [('ourkg', i['q'], i['type'], i['evidence'], i['terms'],
                  i.get('ladder'), None) for i in sample]
        cases += [('paper', q, at, ev, [x.strip() for x in q.split(' and ')], None, rs)
                  for _n, q, at, ev, _p, rs in _PT5]
        rows = []
        for who, q, attr, ev, terms, ladder, pres in cases:
            r = judge(terms, ev, ladder, diet=str(attr).startswith('Diet'))
            r.update(who=who, question=q, attributes=attr, paper_result=pres)
            rows.append(r)
            print(f"  [{who:5s}] {q[:40]:42s} [{r['term_used'][:14]:16s}] "
                  f"색인={r['n_hits_pair_only']:6d} 초록={r['n_abstracts']:3d} "
                  f"연관문장={r['sent_assoc']:3d} 부정={r['sent_negative']:2d}"
                  f"  -> {r['result']:+d}")
        all_rows = pd.DataFrame(rows)

        # 두 파일은 **같은 스키마**다. 열을 따로 고르지 않는다 — 보정값은 우리 자를
        # 논문 15 건에 그대로 댄 것이라, 같은 열로 나란히 읽히는 게 맞다.
        def dump(who, name):
            d = all_rows[all_rows.who == who].reset_index(drop=True)
            d.insert(0, 'no', d.index)
            d.to_csv(os.path.join(OUT, name), index=False)
            return d

        t5 = dump('ourkg', 'eval_method2.csv')
        cdf = dump('paper', 'eval_method2_calibration.csv')

        # 같은 자를 논문 자신의 15 건에 대어 판별력을 본다 (confirmed 11 /
        # non-confirmed 4). 색인 공출현 두 자는 여기서 떨어졌다 — RESULTS §4.3.
        conf = cdf.paper_result == 1
        hit = cdf.result == 1
        tp, fn = int((hit & conf).sum()), int((~hit & conf).sum())
        fp, tn = int((hit & ~conf).sum()), int((~hit & ~conf).sum())
        bal = (tp / max(tp + fn, 1) + tn / max(tn + fp, 1)) / 2
        print(f"\n  확인(+1) {int((t5.result == 1).sum())}/15, "
              f"미확인(0) {int((t5.result == 0).sum())}/15, "
              f"반대(-1) {int((t5.result == -1).sum())}/15"
              f"   (논문 Table 5: 11 / 3 / 1)")
        print(f"  일반명으로 올려서 맞은 것 {int((t5.term_level > 0).sum())}건, "
              f"근거 물질 고유 {t5.evidence.nunique()}종")
        print('\n  같은 자로 — 논문 15 건에 대었을 때의 판별력')
        print(f'    confirmed {tp}/{tp + fn} 통과 · non-confirmed {fp}/{fp + tn} 통과'
              f'   균형정확도 {bal:.2f}')
        print('    (색인 공출현: 3항 1/11 vs 0/4 = 0.55, 2항 10/11 vs 3/4 = 0.58)')

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
            cm = compound_microbe(sources=('kegg',))
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
    cm = compound_microbe(sources=('kegg',))
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


# ModiMedDiet 의 **주당 처방 횟수**. 규칙의 src 문자열에 이미 적혀 있던 것을
# 수치로 옮긴다. 범위는 중앙값을 쓴다(5-8/day -> 6.5/day -> 45.5/week).
#
# `eggs <=6/week` 와 extras 의 `<=3/week` 는 **상한**이지 처방량이 아니다.
# 달걀은 처방 12군에 들어 있으므로 상한을 그대로 쓰고, extras 는 "적게 먹으라"
# 는 쪽이라 0 으로 둔다 — 상한 3 을 그대로 쓰면 생선(주 2회)보다 위에 놓인다.
MODIMED_FREQ = {
    'vegetables 6/day': 42.0,
    'whole grains 5-8/day': 45.5,
    'fruit 3/day': 21.0,
    'olive oil 3 tbsp/day': 21.0,
    'low-fat unsweetened dairy 2-3/day': 17.5,
    'raw unsalted nuts 1/day': 7.0,
    'eggs <=6/week': 6.0,
    'legumes 3-4/week': 3.5,
    'lean red meat 3-4/week': 3.5,
    'chicken 2-3/week': 2.5,
    'fish >=2/week': 2.0,
}


def modimed_freq(res):
    """음식마다 주당 처방 횟수. 처방 12군은 위 표, extras 는 0, 해당 없음은 NaN."""
    lab, why = modimed_labels(res)
    f = why.map(MODIMED_FREQ)
    f[lab == -1] = float(os.environ.get('MODIMED_EXTRAS_FREQ', '0'))
    f[lab == 0] = float('nan')
    return f


def modimed_spearman(res):
    """추천 점수와 **주당 처방 횟수**의 순위 상관.

    지금까지 ModiMedDiet 은 처방군/extras **이분법**이었다. 그러면 채소(주 42회)
    와 lean red meat(주 3-4회)가 같은 +1 이 되어 정답셋이 처방 강도를 잃는다.
    SMILES 는 빈도 처방이므로 그 기울기를 그대로 쓰는 것이 맞다.

    AUC 가 Top-K 와 어긋난 것(§13)은 라벨이 **이분법**이라 순서의 가운데를 못
    봤기 때문이기도 하다. 순위 상관은 전 구간의 순서를 본다.

    되돌아보기 쉽게 둘을 같이 낸다 — 전체(extras 포함)와 처방군 안에서만.
    """
    from scipy.stats import spearmanr
    f = modimed_freq(res)
    # 상위 N 개 안에서만 재는 변형. 전역 ρ 는 AUC 와 마찬가지로 **맨 위에 무엇이
    # 오는지에 둔감**하다 — 추천군 0 개인 설정을 기본값보다 위에 놓는다(§13b).
    # Top-K 추천의 품질을 보려면 상위 구간을 봐야 한다.
    topn = int(os.environ.get('MODIMED_RHO_TOP', '0'))
    head = res.head(topn).index if topn else res.index
    out = {}
    for name, m in (('전체', f.notna()),
                    ('처방군만', f.notna() & (f > 0)),
                    (f'상위{topn}', f.notna() & f.index.isin(head)) if topn else
                    ('전체', f.notna())):
        if m.sum() < 10 or f[m].nunique() < 2:
            continue
        rho, pv = spearmanr(res.loc[m, 'score'], f[m])
        out[f'modimed_rho_{name}'] = round(float(rho), 3)
        out[f'modimed_rho_{name}_n'] = int(m.sum())
    return out


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
        **modimed_spearman(res),
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
    # 참고값을 하드코딩하면 데이터가 바뀔 때마다 낡는다 (0.665/0.491 로 박혀
    # 있었다). 비교표에서 읽어 오고, 표가 없으면 그 사실을 적는다.
    _cmp = os.path.join(OUT, 'e_mode_comparison.csv')
    if os.path.exists(_cmp):
        _c = pd.read_csv(_cmp)
        _col = next((c for c in ('modimed_AUC(참고)', 'modimed_AUC')
                     if c in _c.columns), None)
        if _col:
            _best = _c.loc[_c[_col].idxmax()]
            _base = _c[(_c.e_mode == 'shrunk') & (_c.path == 'direct')]
            _bv = f"{_base[_col].iloc[0]:.3f}" if len(_base) else '-'
            print(f'  (참고: 공개 소스 최고 {_best.e_mode} {_best.path} '
                  f'{_best[_col]:.3f} / 기본 shrunk direct {_bv} '
                  f'— out/e_mode_comparison.csv)')
    else:
        print('  (참고값 없음 — analyze.py compare 를 먼저 돌린다)')
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



# 논문 Fig.4(c) 의 6 군. 논문은 "biological roles" 라고만 하고 목록을 주지 않아
# 그림의 x 축 라벨로부터 읽었다. FDC 영양소 이름이 규칙적이라 이름으로 가른다.
#
# 두 군데서 그림과 다르게 뒀고, 이유를 적는다.
#  - **토코페롤·카로티노이드를 지질이 아니라 비타민·조효소에 둔다.** 그림은 이들을
#    Lipids 칸에 넣었는데(alpha-Tocopherol 은 Vitamins 칸에도 있어 그림 자체가
#    일관되지 않다), 영양학에서 이들은 비타민 E·프로비타민 A 다.
#  - **콜린·베타인은 그림대로 아미노산 군에 둔다.** 엄밀히는 4 급 암모늄 화합물이지만
#    FDC 가 아미노산과 함께 보고하고 그림도 그 칸에 뒀다.
COMPOUND_GROUPS = [
    ('지질', r'^(SFA|MUFA|PUFA|TFA) |cholesterol|sitosterol|campesterol|stigmasterol'),
    ('탄수화물', r'^(starch|fructose|lactose|galactose|sucrose|glucose|maltose)\b'),
    ('비타민·조효소', r'vitamin|folate|folic|riboflavin|thiamin|niacin|pantothenic|'
                     r'tocopherol|tocotrienol|carotene|cryptoxanthin|lycopene|lutein|'
                     r'zeaxanthin|phytoene|phytofluene|menaquinone|phylloquinone|'
                     r'ergocalciferol|tetrahydrofolate|MTHF|HCOFA'),
    ('다량무기질', r'^(sodium|calcium|magnesium|phosphorus|potassium|sulfur)[, ]'),
    ('미량원소', r'^(iron|copper|manganese|zinc|selenium|fluoride|iodine|boron|'
                 r'cobalt|molybdenum|nickel|chromium)[, ]'),
    ('아미노산', r'^(tryptophan|threonine|methionine|phenylalanine|tyrosine|alanine|'
                 r'glutamic|glycine|proline|valine|arginine|histidine|aspartic|serine|'
                 r'isoleucine|leucine|lysine|cystine|cysteine|hydroxyproline|choline|'
                 r'betaine)\b'),
    ('기타', r'.'),
]


def compound_group(name):
    """영양소 이름 -> 논문 Fig.4(c) 의 6 군. 순서가 중요하다 — 지질을 먼저 본다."""
    for g, pat in COMPOUND_GROUPS:
        if re.search(pat, str(name), re.I):
            return g
    return '기타'


def groups():
    """논문 Fig.4(c) — 추천군과 비추천군의 성분군별 조성을 비교한다.

    §4.2.3 이 추천 결과의 **근거로 쓰는 그림**인데 우리는 Fig.4(a) PCA 와
    Fig.4(b) t-SNE 만 하고 이것을 빼놓고 있었다. 논문의 결론은 "추천군은
    탄수화물·비타민이 높고 비추천군은 미량원소·다량영양소가 높다" 이다.

    정규화 기준이 둘로 읽힌다. 논문 §4.2.3 은 "we normalize the compounds in the
    two groups of foods separately" 라고만 쓴다.

      `GROUP_NORM=compound` (기본) — compound 마다 두 군의 값을 그 compound 의
        최대값으로 나눈다. **그림이 보여주는 쪽이다** — Fig.4(c) 는 미량원소·
        비타민 칸에도 진한 칸이 있는데, 아래 방식으로는 그 칸들이 전부 0 이 된다.
      `GROUP_NORM=group` — 군 안에서 전체 최대값으로 나눈다. 문장의 문자 그대로지만
        전분·포도당(g)이 최대라 mg·µg 단위 성분이 전부 0 에 깔린다.

    둘 다 재서 §18 에 적었다.

    출력
      out/group_composition.csv   compound 별 두 군의 정규화 중량
      out/group_comparison.csv    6 군 요약 + Mann-Whitney U
      out/group_comparison.png    Fig.4(c) 대응 히트맵
    """
    from scipy.stats import mannwhitneyu

    K = int(os.environ.get('TOP_K', '30'))
    rec = pd.read_csv(os.path.join(OUT, 'recommendation.csv'))
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    nmap = pd.read_csv(os.path.join(BASE, 'setup', 'nutrient_kegg_map.csv'), dtype=str)
    nmap = nmap[nmap.nutrient_kegg.str.startswith('C', na=False)]
    kname = dict(zip(nmap.nutrient_kegg, nmap.nutrient_name))

    top = rec.head(K)['food_key'].tolist()
    bot = rec.tail(K)['food_key'].tolist()
    print(f'[1/3] 추천군 {len(top)} · 비추천군 {len(bot)} (K={K})')

    w = long[long.food_key.isin(top + bot)].copy()
    w['set'] = np.where(w.food_key.isin(top), 'rec', 'not')
    piv = w.pivot_table(index='kegg', columns='set', values='amount_g', aggfunc='mean').fillna(0)
    for c in ('rec', 'not'):
        if c not in piv:
            piv[c] = 0.0
    NORM = os.environ.get('GROUP_NORM', 'compound')
    print(f'  GROUP_NORM={NORM}')
    if NORM == 'compound':
        mx = piv[['rec', 'not']].max(axis=1).replace(0, np.nan)
        piv[['rec', 'not']] = piv[['rec', 'not']].div(mx, axis=0).fillna(0)
    else:
        for c in ('rec', 'not'):
            m = piv[c].max()
            piv[c] = piv[c] / m if m else 0.0
    piv['name'] = [kname.get(k, k) for k in piv.index]
    piv['group'] = piv['name'].map(compound_group)
    piv = piv.sort_values(['group', 'rec'], ascending=[True, False])
    piv.to_csv(os.path.join(OUT, 'group_composition.csv'))

    print('[2/3] 성분군별 조성 — 논문 Fig.4(c)')
    rows = []
    print(f'  {"성분군":14s} {"n":>4s} {"추천군":>8s} {"비추천군":>9s} {"차":>8s} {"p":>8s}')
    for g, sub in piv.groupby('group'):
        try:
            p = mannwhitneyu(sub['rec'], sub['not']).pvalue
        except ValueError:
            p = float('nan')
        rows.append({'group': g, 'n_compound': len(sub), 'rec_mean': sub['rec'].mean(),
                     'not_mean': sub['not'].mean(),
                     'diff': sub['rec'].mean() - sub['not'].mean(), 'p': p})
        print(f'  {g:14s} {len(sub):4d} {sub["rec"].mean():8.3f} '
              f'{sub["not"].mean():9.3f} {rows[-1]["diff"]:+8.3f} {p:8.3g}')
    tab = pd.DataFrame(rows).sort_values('diff', ascending=False)
    tab.to_csv(os.path.join(OUT, 'group_comparison.csv'), index=False)

    print('[3/3] 히트맵')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in ('NanumGothic', 'Noto Sans CJK KR', 'DejaVu Sans'):
        if any(f in x.name for x in font_manager.fontManager.ttflist):
            plt.rcParams['font.family'] = f
            break
    plt.rcParams['axes.unicode_minus'] = False
    order = [g for g, _ in COMPOUND_GROUPS if g in set(piv['group'])]
    piv = piv.loc[sorted(piv.index, key=lambda k: (order.index(piv.at[k, 'group']),
                                                   -piv.at[k, 'rec']))]
    fig, ax = plt.subplots(2, 1, figsize=(max(10, len(piv) * 0.16), 5), sharex=True)
    for a, c, t in zip(ax, ('rec', 'not'), ('추천군 Top 30', '비추천군 Bottom 30')):
        a.imshow(piv[[c]].T.values, aspect='auto', cmap='OrRd', vmin=0, vmax=1)
        a.set_yticks([0]); a.set_yticklabels([t], fontsize=9)
    bound, prev = [], None
    for i, g in enumerate(piv['group']):
        if g != prev:
            bound.append((i, g)); prev = g
    for a in ax:
        for i, _ in bound[1:]:
            a.axvline(i - .5, color='k', lw=.8)
    # sharex 라 ax[0] 에 눈금을 걸면 ax[1] 의 compound 이름에 덮인다. 성분군 이름은
    # 눈금이 아니라 주석으로 얹는다.
    for i, g in bound:
        ax[0].annotate(g, (i + .3, -.75), ha='left', va='bottom', fontsize=9,
                       annotation_clip=False)
    ax[1].set_xticks(range(len(piv)))
    ax[1].set_xticklabels([n[:22] for n in piv['name']], rotation=90, fontsize=5)
    fig.suptitle(f'Fig.4(c) 대응 — 추천/비추천군의 성분 조성 ({NORM} 정규화)',
                 fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'group_comparison.png'), dpi=150, bbox_inches='tight')
    print(f'  저장: {os.path.join(OUT, "group_comparison.png")}')



def emicrobe():
    """미생물 경로에서 **독립된 E** 를 유도해 ProMENDA 의 E 와 대조한다.

    §15b 에서 미생물 매개 가중이 안 먹히는 이유를 **구조**로 진단했다 —
    `P = D x S` 에서 `S` 가 99.3% 꽉 차 있어 `D` 의 compound 별 변조가 평균에
    묻힌다(ALPHA 를 9 배로 걸어도 순위상관 0.99).

    구조를 고치기 전에 **미생물 축에 신호가 있는지부터** 본다. 알고리즘을 안
    바꾸고 답할 수 있는 질문이다:

        compound c 를 대사하는 균이 우울증에서 **감소**한다면 c 는 이로운 쪽인가?
        그렇게 만든 E_microbe 가 ProMENDA 의 E 와 일치하는가?

    **방향 가정은 검증 대상이지 전제가 아니다.** "감소한 균이 좋은 균" 과 그
    반대를 **둘 다** 재서 어느 쪽이 맞는지(혹은 둘 다 아닌지) 본다.

    출력
      out/e_microbe.csv            compound 별 E_microbe 와 근거 수
      out/e_microbe_compare.csv    ProMENDA E 와의 일치 (방향 가정 x 질환 범위)
    """
    from scipy.stats import spearmanr

    K = float(os.environ.get('SHRINK_K', '10'))
    E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
    db = pd.read_csv(os.path.join(OUT, 'microbe_disease_disbiome.csv'),
                     dtype={'taxid': str})
    rows = []
    for scope, dsel in (('정신질환 전체', db[db.is_mental]),
                        ('우울증만', db[db.disease == 'Major Depressive Disorder'])):
        # 균별로 그 질환에서 늘었는지(Elevated) 줄었는지(Reduced)
        for src in ('both', 'measured'):
            cm = (compound_microbe() if src == 'both'
                  else _measured_links())
            if cm.empty:
                continue
            j = cm.merge(dsel[['taxid', 'outcome']], on='taxid')
            if j.empty:
                continue
            n = j.pivot_table(index='kegg', columns='outcome', aggfunc='size',
                              fill_value=0)
            up = n.get('Elevated', pd.Series(0, index=n.index))
            dn = n.get('Reduced', pd.Series(0, index=n.index))
            for assume, pos, neg in (('감소=이로움', dn, up), ('증가=이로움', up, dn)):
                e = (pos - neg) / (pos + neg + K)
                both = E['e_shrunk'].reindex(e.index).dropna()
                e2 = e.reindex(both.index)
                nz = (both != 0) & (e2 != 0)
                if nz.sum() < 10:
                    continue
                rho = spearmanr(both[nz], e2[nz]).statistic
                agree = float((np.sign(both[nz]) == np.sign(e2[nz])).mean())
                # 부호일치가 우연(0.5)보다 큰가 — 눈대중 말고 이항검정으로
                from scipy.stats import binomtest
                bt = binomtest(int(round(agree * nz.sum())), int(nz.sum()), 0.5,
                               alternative='greater')
                rows.append({'질환범위': scope, '링크': src, '방향가정': assume,
                             'compound': int(nz.sum()),
                             '부호일치': round(agree, 3), 'p': round(bt.pvalue, 4),
                             'rho': round(float(rho), 3)})
                if scope == '정신질환 전체' and src == 'both' and assume == '감소=이로움':
                    pd.DataFrame({'kegg': e.index, 'e_microbe': e.values,
                                  'n_reduced': dn.reindex(e.index).values,
                                  'n_elevated': up.reindex(e.index).values}
                                 ).to_csv(os.path.join(OUT, 'e_microbe.csv'), index=False)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, 'e_microbe_compare.csv'), index=False)
    print(t.to_string(index=False))
    print('\n  부호일치 0.5 · rho 0 이 우연 수준이다. 두 방향 가정이 대칭이므로')
    print('  한쪽이 0.5 보다 높으면 다른 쪽은 그만큼 낮다 — **크기**를 봐야 한다.')
    return t


def _measured_links():
    """측정 상관 링크를 taxid 로 펼친 것 (metabolome_check.py build)."""
    p = os.path.join(OUT, 'compound_microbe_measured.csv')
    if not os.path.exists(p):
        return pd.DataFrame(columns=['taxid', 'kegg'])
    m = pd.read_csv(p)
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str}).fillna('')
    mic['genus'] = mic['name'].astype(str).str.split().str[0]
    return m.merge(mic[['taxid', 'genus']], on='genus')[['taxid', 'kegg']].drop_duplicates()


STEPS = {'recommend': recommend, 'compare': compare, 'external': external,
         'invert': invert, 'stype': stype, 'disagree': disagree, 'groups': groups,
         'pathcheck': pathcheck, 'evaluate': evaluate, 'emicrobe': emicrobe}


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
