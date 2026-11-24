"""NHANES 로 **섭취-결과** 기반 E 를 만든다.

    python3 ourkg/nhanes.py            # 받기 -> E 산출 -> ProMENDA 와 대조
    NHANES_CYCLE=2015 python3 ourkg/nhanes.py

왜 필요한가 — 현재 `E` 는 ProMENDA 에서 온다. 그것은 "우울증 환자에서 이
대사물의 **농도**가 높다/낮다" 이지 "그것을 **먹으면** 좋다/나쁘다" 가 아니다
(RESULTS §9). 그 불일치가 Top-K 에 실제로 드러난다 — 에탄올(+0.200)·설탕
(+0.259)이 이로운 쪽으로 표시되고, 그 둘을 빼면 추천군이 21 -> 17 로 떨어진다
(§15b 검정 ⑧). 즉 **현재 점수가 틀린 양수에 일부 기대고 있다.**

NHANES 는 같은 사람에게서 **24 시간 식이회상**과 **PHQ-9 우울 척도**를 잰다.
섭취와 결과를 직접 잇는 소스이므로 `E` 의 뜻과 맞는다.

  식이   DR1TOT  (하루치 영양소 총량 67 열)
  우울   DPQ     (PHQ-9 9 문항, 0~27)
  인구   DEMO    (나이·성별·소득)

**이것은 관찰 연구다.** 인과가 아니고 역인과(우울해서 덜 먹는다)와 교란이
남는다. 나이·성별·총열량·소득을 보정하지만 그걸로 충분하지 않다. 그래서
`E_MODE` 의 **선택지**로 두고 기본값으로 삼지 않는다 — 채택 여부는 §4.2.3 과
ModiMedDiet 로 재서 정한다.
"""
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, CACHE, OUT

CYCLES = {'2017': ('2017', 'J'), '2015': ('2015', 'I'), '2013': ('2013', 'H')}
URL = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{yr}/DataFiles/{f}.xpt'

# NHANES 영양소 변수 -> 우리 KEGG. 이름은 setup/nutrient_kegg_map.csv 와 맞춘다.
# 엽산은 NHANES 가 셋으로 나누는데(총량·강화·식품) 우리 F 는 C00504 하나라
# 총량(DR1TFOLA)만 쓴다. 비타민 B-6 와 알파-토코페롤은 우리 매핑표에 KEGG 가
# 없어(각각 '0' 으로 기각, 'Vitamin E, added' 만 있음) 뺀다.
NUT2KEGG = {
    'DR1TRET': 'C00473', 'DR1TACAR': 'C05433', 'DR1TBCAR': 'C02094',
    'DR1TCRYP': 'C08591', 'DR1TLYCO': 'C05432', 'DR1TLZ': 'C06098',
    'DR1TVB1': 'C00378', 'DR1TVB2': 'C00255', 'DR1TNIAC': 'C00253',
    'DR1TFOLA': 'C00504', 'DR1TCHL': 'C00114', 'DR1TVB12': 'C05776',
    'DR1TVC': 'C00072', 'DR1TVD': 'C05443', 'DR1TVK': 'C02059',
    'DR1TCALC': 'C00076', 'DR1TPHOS': 'C06262', 'DR1TMAGN': 'C00305',
    'DR1TIRON': 'C00023', 'DR1TZINC': 'C00038', 'DR1TCOPP': 'C00070',
    'DR1TSODI': 'C01330', 'DR1TPOTA': 'C00238', 'DR1TSELE': 'C01529',
    'DR1TCAFF': 'C07481', 'DR1TTHEO': 'C07480', 'DR1TALCO': 'C00469',
    'DR1TCHOL': 'C00187',
    # 지방산 — FDC 의 SFA/MUFA/PUFA 표기와 같은 사슬 길이로 잇는다
    'DR1TS040': 'C00246', 'DR1TS060': 'C01585', 'DR1TS080': 'C06423',
    'DR1TS100': 'C01571', 'DR1TS120': 'C02679', 'DR1TS140': 'C06424',
    'DR1TS160': 'C00249', 'DR1TS180': 'C01530', 'DR1TM161': 'C08362',
    'DR1TM181': 'C00712', 'DR1TM201': 'C16526', 'DR1TM221': 'C08316',
    'DR1TP182': 'C01595', 'DR1TP183': 'C06427', 'DR1TP184': 'C16300',
    'DR1TP204': 'C00219', 'DR1TP205': 'C06428', 'DR1TP225': 'C16513',
    'DR1TP226': 'C06429',
}


def _ols(X, y, j):
    """다중회귀의 계수 j 와 그 양측 p. statsmodels 를 새로 깔지 않으려고 둔다
    (README 의 설치 목록을 늘리면 재현이 그만큼 번거로워진다).

    b = (X'X)^-1 X'y,  var(b) = s^2 (X'X)^-1,  t = b/se ~ t(n-k)
    """
    from scipy.stats import t as tdist
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ (X.T @ y)
    resid = y - X @ b
    dof = len(y) - X.shape[1]
    s2 = float(resid @ resid) / dof
    se = np.sqrt(s2 * np.diag(XtX_inv))
    tv = b[j] / se[j]
    return float(b[j]), float(2 * tdist.sf(abs(tv), dof))


def _load(cycle):
    yr, suf = CYCLES[cycle]
    d = os.path.join(CACHE, 'nhanes', cycle)
    os.makedirs(d, exist_ok=True)
    out = {}
    for stem in ('DEMO', 'DPQ', 'DR1TOT'):
        f = f'{stem}_{suf}'
        p = os.path.join(d, f + '.xpt')
        if not os.path.exists(p):
            urllib.request.urlretrieve(URL.format(yr=yr, f=f), p)
        out[stem] = pd.read_sas(p, format='xport')
    return out


def _joined(cycle):
    """한 주기의 식이 x PHQ-9 x 인구 조인."""
    d = _load(cycle)
    q = [c for c in d['DPQ'].columns if c.startswith('DPQ') and c != 'DPQ100']
    x = d['DPQ'][q].replace({7: np.nan, 9: np.nan})
    dpq = d['DPQ'].assign(phq9=x.sum(axis=1).where(x.notna().all(axis=1)))
    j = (d['DR1TOT'].merge(dpq[['SEQN', 'phq9']], on='SEQN')
         .merge(d['DEMO'][['SEQN', 'RIAGENDR', 'RIDAGEYR', 'INDFMPIR']], on='SEQN'))
    j = j[(j.DR1DRSTZ == 1) & j.phq9.notna() & (j.RIDAGEYR >= 18) & (j.DR1TKCAL > 0)]
    return j.assign(cycle=cycle)


def build(cycle=None):
    """섭취 -> PHQ-9 연관으로 E 를 만든다 -> out/compound_depression_nhanes.csv

    보정: 나이·성별·**총열량**·소득(PIR). 총열량 보정이 핵심이다 — 안 하면
    "많이 먹는 사람" 효과가 모든 영양소에 공통으로 실린다(영양역학의 표준).

    부호 규약은 우리 `E` 와 맞춘다 — **+ 가 이로움(우울 감소)**. 회귀계수가
    음수(섭취가 늘수록 PHQ-9 가 낮다)면 E 는 +다.
    """
    # 여러 주기를 합친다. 한 주기(4,774)로는 compound 47 중 24 만 유의해
    # **E 의 음수 쪽 커버리지가 얇다** — effect 공간에서 바닥이 약한 원인이다
    # (RESULTS §17d·§20). 주기를 합치면 표본이 늘어 유의 compound 가 는다.
    # 주기는 **고정효과로 보정한다** — 조사 연도마다 식이 보고 방식과 PHQ-9
    # 분포가 달라 합치기만 하면 주기 간 차이가 영양소 계수에 실린다.
    # **기본값은 단주기다.** 3 주기(14,792)로 합치면 유의 compound 가 24 -> 38 로
    # 늘지만 **추천이 더 나빠진다** — 늘어난 것의 상당수가 인·아연·티아민·
    # 나이아신처럼 "고기를 많이 먹는 사람" 을 가리키는 영양소라 Top 1 이 소고기
    # 타코가 된다(RESULTS §20). 통계적 강도와 추천 품질이 반대로 간 사례다.
    cycles = (cycle or os.environ.get('NHANES_CYCLE', '2017')).split(',')
    parts = [_joined(c.strip()) for c in cycles]
    j = pd.concat(parts, ignore_index=True)
    print(f'[1/3] 주기 {",".join(cycles)} — 표본 {len(j):,} '
          f'({" + ".join(f"{len(p):,}" for p in parts)}) / PHQ-9>=10 '
          f'{int((j.phq9 >= 10).sum()):,} ({(j.phq9 >= 10).mean() * 100:.1f}%)')

    # 섭취는 오른쪽으로 길게 늘어진다 — log1p 로 펴고 표준화해 계수를 비교 가능하게
    cov = pd.DataFrame({
        'age': j.RIDAGEYR, 'female': (j.RIAGENDR == 2).astype(float),
        'kcal': np.log1p(j.DR1TKCAL), 'pir': j.INDFMPIR.fillna(j.INDFMPIR.median())},
        index=j.index)
    for c in cycles[1:]:                      # 주기 고정효과 (첫 주기가 기준)
        cov[f'cyc{c.strip()}'] = (j.cycle == c.strip()).astype(float).values
    rows = []
    for var, kegg in NUT2KEGG.items():
        if var not in j:
            continue
        v = pd.to_numeric(j[var], errors='coerce')
        if v.notna().sum() < 500 or v.std(skipna=True) == 0:
            continue
        z = np.log1p(v.clip(lower=0))
        z = (z - z.mean()) / z.std()
        X = pd.concat([z.rename('intake'), cov], axis=1)
        X.insert(0, 'const', 1.0)
        m = pd.concat([X, j.phq9], axis=1).dropna()
        if len(m) < 500:
            continue
        b, p = _ols(m[X.columns].values, m['phq9'].values, 1)   # 1 = intake 열
        rows.append({'kegg': kegg, 'nhanes_var': var, 'n': int(len(m)),
                     'beta': b, 'p': p})
    t = pd.DataFrame(rows)
    # 한 KEGG 에 여러 변수가 붙으면 표본이 큰 쪽
    t = t.sort_values('n', ascending=False).drop_duplicates('kegg')
    from scipy.stats import false_discovery_control
    t['q'] = false_discovery_control(t.p.values)
    # 부호 뒤집기 — beta<0(섭취가 늘수록 덜 우울)이 우리 규약의 +
    t['e_raw'] = -t.beta
    s = t.e_raw.abs().max()
    t['e_nhanes'] = (t.e_raw / s).round(4) if s else 0.0
    t['e_sig'] = np.where(t.q < 0.05, t.e_nhanes, 0.0)
    t.to_csv(os.path.join(OUT, 'compound_depression_nhanes.csv'), index=False)
    print(f'[2/3] compound {len(t)} — q<0.05 {int((t.q < 0.05).sum())}')
    for _, r in t.nsmallest(8, 'q').iterrows():
        print(f'    {r.kegg}  {r.nhanes_var:10s} beta={r.beta:+.4f}  q={r.q:.4f}'
              f'  E={r.e_nhanes:+.3f}')

    print('[3/3] ProMENDA E 와 대조')
    E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv')).set_index('kegg')
    j2 = t.set_index('kegg').join(E['e_shrunk'], how='inner')
    nz = j2[(j2.e_shrunk != 0) & (j2.e_nhanes != 0)]
    if len(nz) >= 10:
        from scipy.stats import spearmanr, binomtest
        agree = float((np.sign(nz.e_shrunk) == np.sign(nz.e_nhanes)).mean())
        bt = binomtest(int(round(agree * len(nz))), len(nz), 0.5)
        print(f'    겹치는 compound {len(nz)} / 부호일치 {agree:.3f} (p={bt.pvalue:.4f})'
              f' / rho {spearmanr(nz.e_shrunk, nz.e_nhanes).statistic:+.3f}')
    return t


if __name__ == '__main__':
    build()
