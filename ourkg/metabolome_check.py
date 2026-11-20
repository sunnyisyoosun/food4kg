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
from common import CACHE, OUT, compound_microbe

BASE_URL = ('https://raw.githubusercontent.com/borenstein-lab/'
            'microbiome-metabolome-curated-data/main/data/processed_data')
COHORTS = ('KANG_AUTISM_2017', 'MARS_IBS_2020')
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


if __name__ == '__main__':
    for c in (sys.argv[1:] or COHORTS):
        check(c)
        print()
