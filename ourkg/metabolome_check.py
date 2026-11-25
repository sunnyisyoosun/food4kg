"""측정된 분변 대사체로 우리 compound-미생물 링크를 검정한다.

    python3 ourkg/metabolome_check.py            # 두 코호트 모두
    python3 ourkg/metabolome_check.py KANG_AUTISM_2017

왜 필요한가 — RESULTS.md §15b 에서 gut-brain 가중을 기각한 뒤 해석이 둘 남았다.
(1) 미생물 매개 경로가 실제로 기여하지 않거나, (2) **우리 링크가 너무 거칠거나.**
KEGG 는 "유전체에 효소가 있다" 는 추론이고 VMH 는 예측이다. 실제 장내 대사량이
아니다. 그 둘을 가르려면 **측정값**이 필요하다.

데이터 — Gut Microbiome-Metabolome Dataset Collection (Muller et al., npj
Biofilms Microbiomes 2022). 짝지어진 분변 마이크로바이옴 + 대사체 14 코호트를
통일된 형식으로 큐레이션했다. `mtb.map.tsv` 가 대사물을 **KEGG id 로 직접
매핑**하므로 우리 축에 변환 없이 붙는다.

우울증 코호트는 이 모음에 없다. 대신 둘을 쓴다 — **자폐**(우리 KG 의 F03
질환이고 Disbiome 에서 균 203 종으로 가장 두껍다)와 **IBS**(gut-brain disorder,
샘플 444). 우울증 전용은 MTBLS12050 이 있으나 EBI API 가 401 을 돌려준다.

검정 — 우리가 예측한 (속, compound) 쌍이 측정에서도 더 강하게 연관되는가.
상관의 **부호는 보지 않는다**: 대사는 소비(음)일 수도 생산(양)일 수도 있다.
"""
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, OUT, compound_microbe, enable_provenance

BASE_URL = ('https://raw.githubusercontent.com/borenstein-lab/'
            'microbiome-metabolome-curated-data/main/data/processed_data')

enable_provenance()   # 산출물 출처 기록 (common.PROV)
COHORTS = ('KANG_AUTISM_2017', 'MARS_IBS_2020')
# 모음의 14 코호트 전부. 링크를 **만들 때**는 전부 쓴다 — 한 코호트의 상관은
# 다중검정으로 쉽게 나오므로 **여러 코호트에서 반복되는 쌍만** 받아야 한다.
ALL_COHORTS = (
    'ERAWIJANTARI_GASTRIC_CANCER_2020', 'FRANZOSA_IBD_2019', 'HE_INFANTS_MFGM_2019',
    'JACOBS_IBD_FAMILIES_2016', 'KANG_AUTISM_2017', 'KIM_ADENOMAS_2020',
    'KOSTIC_INFANTS_DIABETES_2015', 'MARS_IBS_2020', 'POYET_BIO_ML_2019',
    'SINHA_CRC_2016', 'WANDRO_PRETERMS_2018', 'WANG_ESRD_2020', 'YACHIDA_CRC_2019',
    'iHMP_IBDMDB_2019')
FILES = ('mtb.tsv', 'genera.tsv', 'mtb.map.tsv', 'metadata.tsv')


def _load(cohort):
    d = os.path.join(CACHE, 'gmm', cohort)
    os.makedirs(d, exist_ok=True)
    out = {}
    for f in FILES:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            urllib.request.urlretrieve(f'{BASE_URL}/{cohort}/{f}', p)
        out[f] = pd.read_csv(p, sep='\t')
    return out


def _our_links():
    """우리가 예측한 (속, KEGG) 쌍. 코호트가 속 수준이라 속으로 올린다."""
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str}).fillna('')
    genus = {r.taxid: str(r['name']).split()[0] for _, r in mic.iterrows() if r['name']}
    cm = compound_microbe()
    cm['genus'] = cm.taxid.map(genus)
    return set(map(tuple, cm.dropna(subset=['genus'])[['genus', 'kegg']].values))


def check(cohort, n_perm=2000):
    from scipy.stats import spearmanr, mannwhitneyu
    d = _load(cohort)
    mtb, gen, mp = d['mtb.tsv'], d['genera.tsv'], d['mtb.map.tsv']
    k = mp.dropna(subset=['KEGG']).set_index('Compound')['KEGG'].to_dict()
    sid = mtb.columns[0]
    mtb = mtb.set_index(sid)
    gen = gen.set_index(gen.columns[0]).reindex(mtb.index)
    # 속 이름은 'k__Bacteria;p__...;g__Bacteroides' 꼴일 수 있다 — 마지막 g__ 만
    gen.columns = [str(c).split('g__')[-1].split(';')[0].strip() for c in gen.columns]
    gen = gen.loc[:, [bool(c) and c != 'NA' for c in gen.columns]]
    # 희소한 축은 상관이 의미 없다 — 절반 이상의 샘플에서 0 인 속은 뺀다
    gen = gen.loc[:, (gen > 0).mean() > 0.5]
    print(f'== {cohort}: 샘플 {len(mtb)} / 대사물 {mtb.shape[1]} (KEGG {len(k)}) '
          f'/ 속 {gen.shape[1]} (희소 제거 후)')

    ours = _our_links()
    rows = []
    for cname, kegg in k.items():
        if cname not in mtb.columns:
            continue
        y = pd.to_numeric(mtb[cname], errors='coerce')
        for g in gen.columns:
            rho, p = spearmanr(gen[g], y, nan_policy='omit')
            if np.isnan(rho):
                continue
            rows.append({'genus': g, 'kegg': kegg, 'compound': cname,
                         'rho': rho, 'p': p, 'ours': (g, kegg) in ours})
    t = pd.DataFrame(rows)
    if t.empty:
        print('  쌍이 없다.')
        return t
    a, b = t[t.ours], t[~t.ours]
    print(f'  (속, compound) 쌍 {len(t):,} — 우리가 예측한 것 {len(a):,} / 나머지 {len(b):,}')
    if len(a) < 10:
        print('  예측 쌍이 너무 적어 검정하지 않는다.')
        return t
    obs = a.rho.abs().mean()
    u = mannwhitneyu(a.rho.abs(), b.rho.abs(), alternative='greater')
    rng = np.random.default_rng(0)
    null = np.array([rng.choice(t.rho.abs().values, len(a), replace=False).mean()
                     for _ in range(n_perm)])
    print(f'  |rho| 평균 — 예측 {obs:.4f} / 나머지 {b.rho.abs().mean():.4f}')
    print(f'    Mann-Whitney p = {u.pvalue:.4f}   순열 p = {float((null >= obs).mean()):.4f}')
    print(f'  p<0.05 쌍 비율 — 예측 {(a.p < .05).mean():.3f} / 나머지 {(b.p < .05).mean():.3f}')
    t.to_csv(os.path.join(OUT, f'metabolome_check_{cohort}.csv'), index=False)
    return t


def _pairs(cohort, min_prev=0.5):
    """한 코호트의 (속, KEGG) Spearman 전부. BH 보정 q 까지."""
    from scipy.stats import spearmanr, false_discovery_control
    d = _load(cohort)
    mtb, gen, mp = d['mtb.tsv'], d['genera.tsv'], d['mtb.map.tsv']
    if 'KEGG' not in mp:
        return pd.DataFrame()
    k = mp.dropna(subset=['KEGG']).set_index('Compound')['KEGG'].to_dict()
    mtb = mtb.set_index(mtb.columns[0])
    gen = gen.set_index(gen.columns[0]).reindex(mtb.index)
    gen.columns = [str(c).split('g__')[-1].split(';')[0].strip() for c in gen.columns]
    gen = gen.loc[:, [bool(c) and c != 'NA' for c in gen.columns]]
    gen = gen.loc[:, (gen > 0).mean() > min_prev]
    cols = [c for c in k if c in mtb.columns]
    if not (len(gen.columns) and cols):
        return pd.DataFrame()
    rows = []
    for c in cols:
        y = pd.to_numeric(mtb[c], errors='coerce')
        for g in gen.columns:
            rho, p = spearmanr(gen[g], y, nan_policy='omit')
            if not np.isnan(rho):
                rows.append((g, k[c], rho, p))
    t = pd.DataFrame(rows, columns=['genus', 'kegg', 'rho', 'p'])
    if not t.empty:
        t['q'] = false_discovery_control(t.p.values)
        t['cohort'] = cohort
        t['n'] = len(mtb)
    return t


def build_links(q_max=0.05, min_cohorts=2):
    """측정 상관으로 compound-미생물 링크를 만든다 -> out/compound_microbe_measured.csv

    §15c 검정 ④ 에서 우리 예측 링크(KEGG 추론 · VMH 예측)가 측정된 분변
    대사체와 **무관함**이 드러났다. 측정에서 직접 만든다.

    **재현성을 요구한다.** 한 코호트 안에서는 다중검정으로 상관이 쉽게 나온다
    (IBS 에서 BH 전 p<0.05 쌍이 41% 였다). BH q 를 걸고, 그 위에 **서로 다른
    코호트 min_cohorts 개 이상에서 같은 부호로** 유의할 것을 요구한다.
    부호를 맞추는 것은 소비/생산 방향이 코호트마다 뒤집히면 잡음이기 때문이다.
    """
    parts = []
    for i, c in enumerate(ALL_COHORTS, 1):
        try:
            t = _pairs(c)
        except Exception as e:
            print(f'  ! {c}: {type(e).__name__}')
            continue
        print(f'  [{i}/{len(ALL_COHORTS)}] {c:34s} 쌍 {len(t):7,} '
              f'(q<{q_max} {int((t.q < q_max).sum()) if len(t) else 0:,})', flush=True)
        if len(t):
            parts.append(t)
    allt = pd.concat(parts, ignore_index=True)
    sig = allt[allt.q < q_max].copy()
    sig['sign'] = np.sign(sig.rho)
    g = sig.groupby(['genus', 'kegg', 'sign']).agg(
        n_cohorts=('cohort', 'nunique'), median_rho=('rho', 'median'),
        cohorts=('cohort', lambda x: ';'.join(sorted(set(x))))).reset_index()
    out = g[g.n_cohorts >= min_cohorts].sort_values(
        ['n_cohorts', 'median_rho'], ascending=[False, False])
    path = os.path.join(OUT, 'compound_microbe_measured.csv')
    out.to_csv(path, index=False)
    print(f'\n  전체 쌍 {len(allt):,} / q<{q_max} {len(sig):,} / '
          f'{min_cohorts}+ 코호트 재현 **{len(out):,}**')
    print(f'  속 {out.genus.nunique()} · compound {out.kegg.nunique()}  ->  {path}')
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'build':
        build_links()
    else:
        for c in (a or COHORTS):
            check(c)
            print()
