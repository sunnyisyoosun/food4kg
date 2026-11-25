"""논문 §3.3 합병증 추론 — **검정 전에 입력의 판별력을 먼저 잰다.**

논문 §3.3 은 "두 질환이 미생물을 공유하면 합병증 관계" 로 추론한다. 우리가 그
추론을 재현하고 초기하수 검정(hypergeometric)을 걸었더니 거의 모든 쌍이
통과했고, 그걸 "외부 −1 정답셋이 없어서 판정 못 한다" 로 적어 뒀다.

**그 진단이 틀렸다.** −1 정답셋은 두 가지 이유로 답이 아니다.

1. **Cochrane "no evidence" 류는 잘못된 도구다.** 그것은 *치료 효과*에 근거가
   없다는 뜻이고 *동반이환이 없다*는 뜻이 아니다. 증거의 부재를 부재의 증거로
   쓰는 셈이다.
2. **정신질환 안에는 자연적으로 −1 이 없다.** 덴마크 전국 레지스트리(590 만 명 ·
   8,390 만 인년 · 90 쌍 전부)가 "정신질환 사이의 동반이환 위험 증가는 예외가
   아니라 규칙" 이라고 결론한다(Plana-Ripoll et al., JAMA Psychiatry 2019).
   완벽한 정답셋을 구해도 거의 전부 +1 이라 **라벨이 변하지 않는다.**

대신 **라벨 없이** 답할 수 있다. 질환별 미생물 집합이 서로 **포개져** 있으면
겹침은 작은 쪽 크기와 같아지고 "기대보다 많다" 가 **구조적으로 보장**된다.
그러면 검정 결과는 생물학이 아니라 집합 모양의 산물이다.

그래서 이 모듈은 **순서를 바꾼다** — 특이성을 먼저 재고, 통과하지 못하면
초기하수 검정을 **돌리지 않는다**. 못 하는 것을 못 한다고 말하는 것이 그럴듯한
p 값을 내는 것보다 낫다.

쓰는 법
-------
    python3 ourkg/complication.py              # 기본 소스(mikg)
    COMP_SOURCE=disbiome python3 ourkg/complication.py
    COMP_SOURCE=gutmdisorder ...
    COMP_SOURCE=curated ...                    # Disbiome + gutMDisorder 합집합
환경변수
    COMP_SOURCE    mikg | disbiome | gutmdisorder | curated (기본 mikg)
    COMP_MIN_SET   질환당 최소 균 수 (기본 5)
    COMP_NEST_MAX  허용하는 포개짐 비율 (기본 0.30). 넘으면 검정을 안 돌린다
"""
import itertools
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, canon, enable_provenance, taxid_alias   # noqa: E402

enable_provenance()   # 산출물 출처 기록 (common.PROV)

SOURCES = ('mikg', 'disbiome', 'gutmdisorder', 'curated')


def disease_sets(source=None):
    """질환 → 미생물 집합. 소스에 따라 **집합의 모양이 달라진다**.

    `mikg` 는 미생물 → 신경전달물질 → 질환 경로다. 신경전달물질이 6 종뿐이라
    모든 질환이 거의 같은 집합을 받는다 — 그게 포개짐의 원인이다.
    `disbiome`·`gutmdisorder` 는 질환마다 다른 균을 준다.
    """
    source = source or os.environ.get('COMP_SOURCE', 'mikg')
    if source not in SOURCES:
        sys.exit(f'COMP_SOURCE 는 {SOURCES} 중 하나. 받은 값: {source}')
    sets = {}
    if source == 'mikg':
        mn = os.path.join(OUT, 'microbe_neurotransmitter.csv')
        nd = os.path.join(OUT, 'neurotransmitter_disease.csv')
        for p in (mn, nd):
            if not os.path.exists(p):
                sys.exit(f'{os.path.basename(p)} 가 없다. python3 ourkg/build.py microbe')
        j = pd.read_csv(mn).merge(pd.read_csv(nd), on='neurotransmitter')
        for d, g in j.groupby('disease'):
            sets[str(d)] = set(g.microbe.astype(str))
    else:
        files = {'disbiome': ['microbe_disease_disbiome.csv'],
                 'gutmdisorder': ['microbe_disease_gutmdisorder.csv'],
                 'curated': ['microbe_disease_disbiome.csv',
                             'microbe_disease_gutmdisorder.csv']}[source]
        alias = taxid_alias()
        parts = []
        for fn in files:
            p = os.path.join(OUT, fn)
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p, dtype={'taxid': str})
            d = d[d.is_mental.fillna(False).astype(bool)
                  | d.is_neuro.fillna(False).astype(bool)]
            d = d[['taxid', 'mesh_id', 'disease']].copy()
            d['taxid'] = canon(d['taxid'], alias)      # 병합 taxid 를 정본으로
            parts.append(d)
        if not parts:
            sys.exit(f'{files} 가 없다. python3 ourkg/build.py microbe')
        j = pd.concat(parts)
        # **이름이 아니라 MeSH id 로 묶는다.** 소스마다 표기가 달라
        # `Parkinson Disease`(gutMDisorder) 와 `Parkinson's Disease`(Disbiome)
        # 가 따로 들어왔고, 그 둘이 **서로의 쌍**으로 검정에 올라왔다
        # (q=1.0 — 같은 질환이니 당연하다). 이름으로 묶으면 같은 질환이 둘이 된다.
        for mid, g in j.groupby('mesh_id'):
            # 라벨은 가장 긴 표기를 쓴다(약어보다 정식 명칭).
            label = max(g.disease.astype(str), key=len)
            sets[f'{label} [{mid}]'] = set(g.taxid)
    lo = int(os.environ.get('COMP_MIN_SET', '5'))
    return {d: s for d, s in sets.items() if len(s) >= lo}, source


def specificity(sets):
    """**검정을 돌려도 되는지**를 먼저 판정한다.

    보는 것 둘
      ① **포개짐** — `공유 == min(|A|, |B|)` 인 쌍의 비율. 1 에 가까우면 한쪽이
         다른 쪽을 품고 있어 "기대보다 많다" 가 보장된다.
      ② **universe 를 다 가진 질환** — 그 질환은 모든 쌍에서 자동 통과한다.
    """
    uni = set().union(*sets.values()) if sets else set()
    rows, nested = [], 0
    for a, b in itertools.combinations(sorted(sets), 2):
        A, B = sets[a], sets[b]
        inter = len(A & B)
        rows.append({'a': a, 'b': b, '|A|': len(A), '|B|': len(B),
                     '공유': inter, 'min(A,B)': min(len(A), len(B)),
                     '포개짐': inter == min(len(A), len(B)),
                     'Jaccard': round(inter / len(A | B), 3)})
        nested += inter == min(len(A), len(B))
    t = pd.DataFrame(rows)
    full = [d for d, s in sets.items() if uni and s == uni]
    return t, {
        '질환': len(sets), 'universe': len(uni), '쌍': len(t),
        '포개진 쌍': nested,
        '포개짐 비율': round(nested / len(t), 3) if len(t) else 0.0,
        'universe 를 다 가진 질환': len(full),
        'Jaccard 중앙값': round(float(t.Jaccard.median()), 3) if len(t) else 0.0,
        'Jaccard 최소': round(float(t.Jaccard.min()), 3) if len(t) else 0.0,
    }


def hypergeom(sets):
    """초기하수 검정 — **특이성을 통과한 뒤에만** 부른다."""
    from scipy.stats import hypergeom as hg
    from scipy.stats import false_discovery_control
    uni = len(set().union(*sets.values()))
    rows = []
    for a, b in itertools.combinations(sorted(sets), 2):
        A, B = sets[a], sets[b]
        k = len(A & B)
        # P(겹침 >= k) — 모집단 uni, 성공 |A|, 추출 |B|
        p = hg.sf(k - 1, uni, len(A), len(B))
        rows.append({'a': a, 'b': b, '공유': k, 'A': len(A), 'B': len(B),
                     '기대': round(len(A) * len(B) / uni, 1), 'p': p})
    t = pd.DataFrame(rows)
    if len(t):
        t['q'] = false_discovery_control(t['p'].values)
    return t.sort_values('p')


def one(source):
    """소스 하나에 대해 특이성 → (통과하면) 검정. 한 줄 요약을 돌려준다."""
    sets, source = disease_sets(source)
    t, s = specificity(sets)
    t.to_csv(os.path.join(OUT, f'complication_specificity_{source}.csv'), index=False)
    print(f'\n== {source}')
    for k, v in s.items():
        print(f'  {k:24s} {v}')
    nest_max = float(os.environ.get('COMP_NEST_MAX', '0.30'))
    row = {'소스': source, '질환': s['질환'], 'universe': s['universe'],
           '쌍': s['쌍'], '포개짐 비율': s['포개짐 비율'],
           'Jaccard 중앙값': s['Jaccard 중앙값'],
           'universe 전체 보유': s['universe 를 다 가진 질환']}
    if s['포개짐 비율'] > nest_max:
        print(f'  판정: **검정을 돌리지 않는다** (포개짐 {s["포개짐 비율"]} > {nest_max})')
        print('    겹침이 작은 쪽 크기와 같아 "기대보다 많다" 가 구조적으로')
        print('    보장된다 — p 값은 생물학이 아니라 집합 모양의 산물이다.')
        print('    외부 -1 정답셋을 구해도 이건 해결되지 않는다 (모듈 docstring).')
        row.update({'검정': '거부', 'q<0.05': '', '통과율': ''})
        return row
    h = hypergeom(sets)
    h.to_csv(os.path.join(OUT, f'complication_hypergeom_{source}.csv'), index=False)
    n = int((h.q < 0.05).sum())
    print(f'  판정: 검정 통과 — q<0.05 {n}/{len(h)} ({n / len(h):.1%})')
    print(h.head(5)[['a', 'b', '공유', '기대', 'q']].to_string(index=False))
    row.update({'검정': '수행', 'q<0.05': f'{n}/{len(h)}',
                '통과율': f'{n / len(h):.1%}'})
    return row


def main():
    """**네 소스를 모두 본다.** 거부는 정상 결과이므로 exit 0 이다.

    `mikg` 가 거부되는 것이 이 모듈의 결론이고, 그것이 파이프라인 실패는 아니다
    — `run_all.py` 가 거기서 멈추면 안 된다.
    """
    only = os.environ.get('COMP_SOURCE')
    rows = [one(s) for s in ([only] if only else SOURCES)]
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, 'complication_summary.csv'), index=False)
    print('\n== 요약  -> out/complication_summary.csv')
    print(t.to_string(index=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
