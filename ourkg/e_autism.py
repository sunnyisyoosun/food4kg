"""자폐로 `E` 를 **측정에서** 만들어 검정력 반론에 답한다.

왜 이게 필요한가
----------------
§31·§32·§33 이 "미생물 축에 방향 신호가 없다" 로 끝났는데, 거기엔 반론이
하나 남는다 — **우울증 자료가 너무 얇다.** 배포 KG 의 우울증 미생물 관계는
1 건이었고 gutMDisorder 를 넣어 23 건이 됐을 뿐이다. 그 23 건으로 방향을
유도하고 "신호가 없다" 고 말하는 것은 검정력 문제와 구별되지 않는다.

gutMDisorder 가 늘려 준 방향은 우울증이 아니었다 — 1,239 관계 중 파킨슨이
672(54%) · 자폐 117 · 알츠하이머 116 · **우울증 23(1.9%)** 이다. 그래서
**미생물 자료가 두터운 질환에서 같은 검정을 한다.**

왜 파킨슨이 아니라 자폐인가
---------------------------
파킨슨이 가장 두텁지만 `E` 를 만들 소스가 없다. MENDA/ProMENDA 는 우울증
전용이고, 파킨슨 쪽에는 그에 상당하는 **큐레이션된 대사물 DB 가 없다**
(개별 연구 표만 있다). 한 연구의 표로 `E` 를 지어내면 995 연구 합의인
ProMENDA 와 비교할 때 비교 자체가 불공정해진다.

자폐는 다르다. 우리가 이미 쓰는 분변 대사체 모음
([`DATA.md` §13](DATA.md))에 **`KANG_AUTISM_2017` 코호트**가 있다 —
자폐 23 명 vs 신경전형 21 명, KEGG 로 붙는 대사물 57. 문헌 투표가 아니라
**측정된 환자-대조 차이**라서 ProMENDA 보다 오히려 근거 성격이 낫다.

부호 규약
---------
`common.polarity` 와 같게 맞춘다 — **환자에서 감소 = 양수(이로움)**.
그래서 `e_autism = -(자폐군 - 대조군)` 방향의 효과크기다.

쓰는 법
-------
    python3 ourkg/e_autism.py
환경변수
    AUTISM_COHORT=KANG_AUTISM_2017
    AUTISM_PERM=2000
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (OUT, CACHE, compound_microbe, microbe_disease_direction,
                    measured_links, depression_e, enable_provenance,
                    mdes, mdes_auc, direction_votes, sign_agree)

enable_provenance()   # 산출물 출처 기록 (common.PROV)

AUTISM_MESH = 'D000067877'          # MeSH Autism Spectrum Disorder
CASE_HINT = 'autis'                 # Study.Group 의 'Autistic ' (뒤 공백 주의)


def build_e(cohort=None):
    """KANG 코호트 → compound 별 `e_autism` (환자에서 감소 = 양수).

    효과크기는 **rank-biserial 상관**을 쓴다. 표본이 44 명이고 대사물 농도가
    정규분포가 아니라 평균차를 쓰면 이상치에 끌린다. Mann-Whitney U 에서
    `r = 2U/(n1*n2) - 1` 로 바로 얻는다 — 부호가 그대로 방향이다.
    """
    from scipy.stats import mannwhitneyu, false_discovery_control
    cohort = cohort or os.environ.get('AUTISM_COHORT', 'KANG_AUTISM_2017')
    d = os.path.join(CACHE, 'gmm', cohort)
    if not os.path.exists(d):
        sys.exit(f'코호트 캐시가 없다: {d}\n'
                 f'  python3 ourkg/metabolome_check.py 로 먼저 받는다.')
    md = pd.read_csv(os.path.join(d, 'metadata.tsv'), sep='\t')
    mtb = pd.read_csv(os.path.join(d, 'mtb.tsv'), sep='\t')
    mp = pd.read_csv(os.path.join(d, 'mtb.map.tsv'), sep='\t')

    sid = mtb.columns[0]
    mtb = mtb.set_index(sid)
    grp = md.set_index('Sample')['Study.Group'].reindex(mtb.index)
    case = grp.astype(str).str.lower().str.strip().str.startswith(CASE_HINT)
    print(f'[1/4] {cohort}: 환자 {int(case.sum())} / 대조 {int((~case).sum())} '
          f'/ 대사물 {mtb.shape[1]}')

    k = mp.dropna(subset=['KEGG']).set_index('Compound')['KEGG'].to_dict()
    rows = []
    for cname, kegg in k.items():
        if cname not in mtb.columns:
            continue
        y = pd.to_numeric(mtb[cname], errors='coerce')
        a, b = y[case.values].dropna(), y[~case.values].dropna()
        if len(a) < 5 or len(b) < 5:
            continue
        u = mannwhitneyu(a, b, alternative='two-sided')
        r = 2 * u.statistic / (len(a) * len(b)) - 1     # +면 환자에서 높다
        rows.append({'kegg': str(kegg), 'compound': cname,
                     # 규약: 환자에서 감소 = 양수. 그래서 부호를 뒤집는다.
                     'e_autism': round(-r, 4), 'p': u.pvalue,
                     'n_case': len(a), 'n_ctrl': len(b)})
    t = pd.DataFrame(rows)
    # 같은 KEGG 에 여러 대사물 이름이 붙으면 평균으로 접는다.
    if t.kegg.duplicated().any():
        t = (t.groupby('kegg')
             .agg(compound=('compound', lambda x: ';'.join(x)),
                  e_autism=('e_autism', 'mean'), p=('p', 'min'),
                  n_case=('n_case', 'max'), n_ctrl=('n_ctrl', 'max'))
             .reset_index())
    t['q'] = false_discovery_control(t['p'].values).round(4)
    t = t.sort_values('e_autism', ascending=False)
    t.to_csv(os.path.join(OUT, 'compound_autism.csv'), index=False)
    print(f'      compound {len(t)} / q<0.05 {int((t.q < 0.05).sum())}'
          f' / |e|>0.3 {int((t.e_autism.abs() > 0.3).sum())}'
          f'  -> out/compound_autism.csv')
    return t.set_index('kegg')


def compare_depression(ea):
    """`e_autism` 과 ProMENDA `e_shrunk` 가 같은 쪽을 보는가.

    둘이 상관이 있으면 ProMENDA 의 우울증 `E` 가 질환 특이적이 아니라
    **"장이 아픈 상태" 일반**을 잡고 있다는 뜻이 된다 — 그건 우울증 식품
    추천의 근거로서 약점이다. 없으면 질환 특이적이라는 쪽이다.
    """
    from scipy.stats import spearmanr, binomtest
    ed = depression_e()
    both = ea.index.intersection(ed.index)
    x, y = ea.loc[both, 'e_autism'], ed.loc[both, 'e_shrunk']
    nz = (x != 0) & (y != 0)
    print(f'\n[2/4] e_autism(측정) vs e_shrunk(ProMENDA 문헌) — 공통 compound '
          f'{len(both)} (둘 다 0 아닌 것 {int(nz.sum())})')
    if nz.sum() < 10:
        print('      너무 적어 검정하지 않는다.')
        return
    rho = spearmanr(x[nz], y[nz])
    agree, null, pp, _ = sign_agree(x[nz], y[nz])
    print(f'      Spearman rho = {rho.statistic:+.3f} (p={rho.pvalue:.3f}) '
          f'/ 부호일치 {agree:.3f} (귀무 {null:.3f} · 순열 p={pp:.3f})')
    print('      0 에 가까우면 ProMENDA 의 E 는 질환 특이적이다 — 자폐의')
    print('      측정 방향과 따로 움직인다는 뜻이다.')


def test_microbe(ea, n_perm=None):
    """자폐 미생물 방향 → `E_microbe` 를 만들어 `e_autism` 과 맞춰 본다.

    `analyze.emicrobe` 와 같은 검정인데 **질환이 자폐**다. 우울증은 미생물
    관계가 23 건이고 자폐는 117(gutMDisorder)·290(Disbiome) 이라, 신호가
    없는 것이 검정력 때문인지 여기서 갈린다.
    """
    from scipy.stats import spearmanr, binomtest, false_discovery_control
    K = float(os.environ.get('SHRINK_K', '10'))
    srcs = {}
    for fn, nm in (('microbe_disease_disbiome.csv', 'Disbiome'),
                   ('microbe_disease_gutmdisorder.csv', 'gutMDisorder')):
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, dtype={'taxid': str})
        d = d[(d.mesh_id == AUTISM_MESH) & d.outcome.isin(('Elevated', 'Reduced'))]
        if len(d):
            srcs[nm] = d[['taxid', 'outcome']]
    ag = microbe_disease_direction()
    ag = ag[(ag.mesh_id == AUTISM_MESH) & (ag.status == 'agreed')]
    if len(ag):
        srcs['합의 쌍만'] = ag.rename(columns={'direction': 'outcome'})[['taxid', 'outcome']]
    if len(srcs) >= 2 and 'Disbiome' in srcs and 'gutMDisorder' in srcs:
        srcs['두 소스 합'] = pd.concat([srcs['Disbiome'], srcs['gutMDisorder']])

    print(f'\n[3/4] 자폐 미생물 방향 → E_microbe (질환 = Autism Spectrum Disorder)')
    rows = []
    for sname, dsel in srcs.items():
        # 'measured' 를 꼭 넣는다 — emicrobe 의 우울증 검정에서 유일하게 0.5 를
        # 넘겼던 것이 이 링크였다. 빼면 비교가 불공정해진다(compound n 이
        # 37 vs 164 로 벌어진다).
        for lname in ('both', 'species', 'measured'):
            cm = (measured_links() if lname == 'measured'
                  else compound_microbe(rank=None if lname == 'both' else 'species'))
            if cm.empty:
                continue
            j = cm.merge(direction_votes(dsel), on='taxid')
            if j.empty:
                continue
            n = j.pivot_table(index='kegg', columns='outcome', aggfunc='size',
                              fill_value=0)
            up = n.get('Elevated', pd.Series(0, index=n.index))
            dn = n.get('Reduced', pd.Series(0, index=n.index))
            for assume, pos, neg in (('감소=이로움', dn, up), ('증가=이로움', up, dn)):
                em = (pos - neg) / (pos + neg + K)
                base = ea['e_autism'].reindex(em.index).dropna()
                e2 = em.reindex(base.index)
                nzm = (base != 0) & (e2 != 0)
                if nzm.sum() < 8:
                    continue
                # 귀무는 0.5 가 아니다 — §48. 순열로 만든다.
                agree, null, pp, _ = sign_agree(base[nzm], e2[nzm])
                rho = spearmanr(base[nzm], e2[nzm]).statistic
                rows.append({'미생물 소스': sname, '링크': lname, '방향가정': assume,
                             '균': dsel.taxid.nunique(), 'compound': int(nzm.sum()),
                             '부호일치': round(agree, 3),
                             '귀무(순열)': round(null, 3),
                             'p': round(float(pp), 4),
                             'rho': round(float(rho), 3)})
    t = pd.DataFrame(rows)
    if len(t):
        t['q(BH)'] = false_discovery_control(t['p'].values).round(3)
    t.to_csv(os.path.join(OUT, 'e_autism_microbe.csv'), index=False)
    print(t.to_string(index=False) if len(t) else '  쌍이 부족하다.')
    if len(t):
        print(f'\n  BH 보정 후 q<0.05 {int((t["q(BH)"] < 0.05).sum())}/{len(t)}')
    return t


def power_report(n_tests=28, alpha=0.05, power=0.80):
    """관측값이 **검출 가능한 구간 안**이었는지 표로 낸다 — 주장 셋 전부.

    §34 에서 미생물 축에만 했다. **같은 논법이 필요한 자리가 더 있었다** —
    "약하다"·"우연 수준이다" 로만 적고 *얼마나 작은 효과까지 배제되는지*는
    안 쟀다. 세 주장을 한 표에 둔다 (`out/power_bound.csv`).

    부호일치와 AUC 는 **둘 다 0.5 가 우연**이라 같은 열에서 읽을 수 있다.
    분산이 달라 경계 식은 각각 `mdes` · `mdes_auc` 를 쓴다.

    **다중검정 보정은 주장마다 다르다.** 처음엔 세 주장 전부에 `alpha/28` 을
    걸었는데, 28 은 미생물 축에서 잰 칸 수다 — 방향 일치와 문헌 lift 는 각각
    **단일 검정**이라 보정할 것이 없다. 일괄 적용하면 경계를 실제보다 느슨하게
    적어 "더 많이 배제된다" 고 말하게 된다.
    """
    from scipy.stats import binomtest, mannwhitneyu
    rows = []
    for fn, col_q in (('e_microbe_compare.csv', 'q'),
                      ('e_autism_microbe.csv', 'q(BH)')):
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            continue
        # **귀무 중심을 행마다 가져온다.** 0.5 를 박아 두고 경계를 내서
        # 0.596·0.629 같은 수를 적고 있었다 — 올바른 중심(≈0.585)에서는
        # 경계가 훨씬 높다(§48). 한글 열이라 itertuples 속성으로는 못 집는다.
        for r in pd.read_csv(p).to_dict('records'):
            n = int(r['compound'])
            p0 = float(r.get('귀무(순열)', 0.5))
            rows.append({'주장': '미생물 축 부호일치', '출처': fn, 'n': n,
                         '관측': float(r['부호일치']), '귀무': p0,
                         'p': float(r['p']), '보정검정수': n_tests,
                         f'경계(a={alpha})': mdes(n, alpha, power, p0),
                         '경계(보정후)': mdes(n, alpha / n_tests, power, p0)})

    # ② 두 큐레이션 소스의 방향 일치 (§32). "우연 수준" 으로만 적어 뒀다.
    ap = os.path.join(OUT, 'microbe_disease_agreement.csv')
    if os.path.exists(ap):
        a = pd.read_csv(ap)
        sh = a[a.n_sources == 2]
        if len(sh):
            n = len(sh)
            rows.append({'주장': '소스 간 방향 일치', '출처': os.path.basename(ap),
                         'n': n,
                         '관측': float((sh.status == 'agreed').mean()),
                         '귀무': 0.5,
                         'p': float(binomtest(int((sh.status == 'agreed').sum()),
                                              n, 0.5, 'greater').pvalue),
                         '보정검정수': 1,
                         f'경계(a={alpha})': mdes(n, alpha, power),
                         '경계(보정후)': mdes(n, alpha, power)})

    # ③ 합병증 비통과 쌍의 문헌 lift (§41). "AUC 0.574 는 약하다" 로만 적었다.
    lp = os.path.join(OUT, 'complication_literature_curated.csv')
    if os.path.exists(lp):
        d = pd.read_csv(lp).dropna(subset=['lift'])
        g1 = d[d['통과'] == True]['lift']
        g2 = d[d['통과'] != True]['lift']
        if len(g1) and len(g2):
            u = mannwhitneyu(g1, g2, alternative='greater')
            rows.append({'주장': '합병증 문헌 lift (AUC)', '출처': os.path.basename(lp),
                         'n': len(g1) + len(g2),
                         '관측': float(u.statistic) / (len(g1) * len(g2)),
                         '귀무': 0.5,
                         'p': float(u.pvalue),
                         '보정검정수': 1,
                         f'경계(a={alpha})': mdes_auc(len(g1), len(g2), alpha,
                                                    power),
                         '경계(보정후)': mdes_auc(len(g1), len(g2), alpha, power)})

    t = pd.DataFrame(rows)
    if not len(t):
        print('  관측 표가 없다. analyze.py emicrobe · e_autism.py 를 먼저 돌려라.')
        return t
    bh = '경계(보정후)'
    t['≥경계라면 잡혔다'] = t['관측'] >= t[bh]
    # **경계끼리 바로 비교할 수 없다.** 행마다 귀무 중심이 다르다 — 귀무
    # 0.415 짜리 행의 경계 0.544 를 "가장 조인 경계" 로 집어 0.585 중심의
    # 행과 나란히 적고 있었다. 비교 가능한 양은 **귀무 위 초과분**이다.
    t['경계-귀무'] = (t[bh] - t['귀무']).round(3)
    t = t.sort_values(['주장', 'n'], ascending=[True, False])
    t.to_csv(os.path.join(OUT, 'power_bound.csv'), index=False)

    for claim, g in t.groupby('주장', sort=False):
        # **경계는 n 이 가장 큰 검정에서 가장 조여진다.** 관측이 가장 큰 행을
        # 고르면 안 된다 — 그 행은 n 이 작아 경계가 느슨하다(처음에 그렇게 적어
        # 0.77 이라는 과한 수를 냈다).
        tight = g.loc[g['경계-귀무'].idxmin()]
        print(f'  [{claim}] 검정 {len(g)} · 귀무 위 초과분이 가장 작은 경계: '
              f'n={int(tight.n)} · 귀무 {tight["귀무"]:.3f} '
              f'-> a={alpha} {tight[f"경계(a={alpha})"]} · '
              f'보정({int(tight.보정검정수)}검정) {tight[bh]} '
              f'(초과 +{tight["경계-귀무"]:.3f})')
        print(f'      그 검정의 관측 {tight["관측"]:.3f} '
              f'(p={tight.p:.4f}) · 경계를 넘은 관측 '
              f'{int(g["≥경계라면 잡혔다"].sum())}/{len(g)}')
        # **유의한 관측에 "배제된다" 를 붙이면 안 된다.** 배제 논법은 귀무
        # 결과에만 쓴다 — 검출된 효과에는 경계가 "얼마나 간신히 잡았나" 를
        # 말한다. 처음엔 세 주장에 같은 문장을 찍어 lift(p=0.0068)에도
        # "배제된다" 고 적고 있었다.
        alpha_c = alpha / float(tight.보정검정수)
        if float(tight.p) < alpha_c:
            print(f'      => 효과가 **검출됐다** (p<{alpha_c:g}). 관측 '
                  f'{tight["관측"]:.3f} 이 경계 {tight[bh]} 와 거의 같다 '
                  f'— 이보다 작은 효과는 놓쳤을 수 있다')
        else:
            print(f'      => {tight[bh]} 이상인 효과는 배제된다 (귀무 '
                  f'{tight["귀무"]:.3f} 기준, 있었으면 잡혔다)')
    print('  귀무 ~ 경계 구간은 열려 있다 — 그건 "모른다" 가 아니라')
    print('  **경계가 있는 모름**이다.  -> out/power_bound.csv')
    return t


def main():
    ea = build_e()
    compare_depression(ea)
    t = test_microbe(ea)
    print('\n[4/4] 검정력 비교 — 이게 이 스크립트의 요점이다')
    g = pd.read_csv(os.path.join(OUT, 'microbe_disease_gutmdisorder.csv'),
                    dtype={'taxid': str})
    g = g[g.outcome.isin(('Elevated', 'Reduced'))]
    for nm, pat in (('우울증', r'[Dd]epressive'), ('자폐', r'Autism')):
        s = g[g.disease.astype(str).str.contains(pat, na=False)]
        print(f'  {nm}: gutMDisorder 관계 {len(s)} / 균 {s.taxid.nunique()}')
    ed = depression_e()
    print(f'  E 의 폭: ProMENDA(우울증) compound {len(ed)} '
          f'/ KANG(자폐 측정) compound {len(ea)}')
    if len(t):
        print(f'  검정에 쓰인 compound: 자폐 최대 {int(t.compound.max())} '
              f'(q<0.05 {int((t["q(BH)"] < 0.05).sum())}/{len(t)})')
    print('\n  ** 둘을 동시에 가진 적이 없다 **')
    print('   우울증 — E 는 넓고(1,412) 미생물이 얇다(관계 23)')
    print('   자폐   — 미생물은 두텁고(117~290) E 가 좁다(57, 그중 BH 유의 0)')
    print('  막히는 자리가 질환마다 다른데 결과는 같다 — 검정력 하나로 설명하려면')
    print('  두 번의 실패를 같은 이유로 묶어야 한다.')
    print('\n[5/5] 검정력의 경계를 계산한다 — "못 닫는다" 가 아니라 "여기까지 닫힌다"')
    power_report()
    return t


if __name__ == '__main__':
    main()
