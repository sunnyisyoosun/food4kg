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
    COMP_LIT_SOURCE  literature 하위명령이 쓸 소스 (기본 curated)
    COMP_MIN_SET   질환당 최소 균 수 (기본 5)
    COMP_NEST_MAX  허용하는 포개짐 비율 (기본 0.30). 넘으면 검정을 안 돌린다
"""
import itertools
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (outp, OUT, canon, disease_key, enable_provenance,   # noqa: E402
                    taxid_alias)

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
        # **조인을 다시 하지 않는다.** `build.py` 가 같은 조인을 해서
        # `microbe_disease_mikg.csv` 로 이미 저장한다 — 여기서 또 하면 갈라진다.
        p = outp('microbe_disease_mikg.csv')
        if not os.path.exists(p):
            sys.exit('microbe_disease_mikg.csv 가 없다. python3 ourkg/build.py microbe')
        j = pd.read_csv(p)
        # **이름 그대로 묶으면 안 된다.** `Learning disorder` 와
        # `Learning disorders` 가 둘 다 있어 같은 질환이 둘로 세어졌다
        # (쌍 55 vs 45). mesh_id 가 없는 경로라 이름을 정규화해서 묶는다 — §41
        # 에서 mesh_id 로 고친 것과 같은 문제, 같은 해법의 다른 형태다.
        j['_dk'] = j['disease'].map(disease_key)
        for dk, g in j[j._dk != ''].groupby('_dk'):
            # 라벨은 가장 긴 표기를 쓴다(mesh_id 쪽과 같은 규약).
            lab = max(g['disease'].astype(str).unique(), key=len)
            sets[lab] = set(g.microbe.astype(str))
    else:
        files = {'disbiome': ['microbe_disease_disbiome.csv'],
                 'gutmdisorder': ['microbe_disease_gutmdisorder.csv'],
                 'curated': ['microbe_disease_disbiome.csv',
                             'microbe_disease_gutmdisorder.csv']}[source]
        alias = taxid_alias()
        parts = []
        for fn in files:
            p = outp(fn)
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
                     'shared': inter, 'min(A,B)': min(len(A), len(B)),
                     'nested': inter == min(len(A), len(B)),
                     'Jaccard': round(inter / len(A | B), 3)})
        nested += inter == min(len(A), len(B))
    t = pd.DataFrame(rows)
    full = [d for d, s in sets.items() if uni and s == uni]
    return t, {
        'diseases': len(sets), 'universe': len(uni), 'pairs': len(t),
        '포개진 쌍': nested,
        'nested_rate': round(nested / len(t), 3) if len(t) else 0.0,
        'universe 를 다 가진 질환': len(full),
        'jaccard_median': round(float(t.Jaccard.median()), 3) if len(t) else 0.0,
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
        rows.append({'a': a, 'b': b, 'shared': k, 'A': len(A), 'B': len(B),
                     'expected': round(len(A) * len(B) / uni, 1), 'p': p})
    t = pd.DataFrame(rows)
    if len(t):
        t['q'] = false_discovery_control(t['p'].values)
    return t.sort_values('p')


def one(source):
    """소스 하나에 대해 특이성 → (통과하면) 검정. 한 줄 요약을 돌려준다."""
    sets, source = disease_sets(source)
    t, s = specificity(sets)
    t.to_csv(outp(f'complication_specificity_{source}.csv'), index=False)
    print(f'\n== {source}')
    for k, v in s.items():
        print(f'  {k:24s} {v}')
    nest_max = float(os.environ.get('COMP_NEST_MAX', '0.30'))
    row = {'source': source, 'diseases': s['diseases'], 'universe': s['universe'],
           'pairs': s['pairs'], 'nested_rate': s['nested_rate'],
           'jaccard_median': s['jaccard_median'],
           'holds_full_universe': s['universe 를 다 가진 질환']}
    if s['nested_rate'] > nest_max:
        print(f'  판정: **검정을 돌리지 않는다** (포개짐 {s["nested_rate"]} > {nest_max})')
        print('    겹침이 작은 쪽 크기와 같아 "기대보다 많다" 가 구조적으로')
        print('    보장된다 — p 값은 생물학이 아니라 집합 모양의 산물이다.')
        print('    외부 -1 정답셋을 구해도 이건 해결되지 않는다 (모듈 docstring).')
        row.update({'test': '거부', 'q<0.05': '', 'pass_rate': ''})
        return row
    h = hypergeom(sets)
    h.to_csv(outp(f'complication_hypergeom_{source}.csv'), index=False)
    n = int((h.q < 0.05).sum())
    print(f'  판정: 검정 통과 — q<0.05 {n}/{len(h)} ({n / len(h):.1%})')
    print(h.head(5)[['a', 'b', 'shared', 'expected', 'q']].to_string(index=False))
    row.update({'test': '수행', 'q<0.05': f'{n}/{len(h)}',
                'pass_rate': f'{n / len(h):.1%}'})
    return row


# 논문 Table 5 의 **합병증 8 문항**을 우리 MeSH id 로 옮긴 표.
# 논문 자신이 `paper` 열에 +1(confirmed) / 0(unknown) 을 준다 — **그게 -1 정답셋
# 이다.** 외부에서 구할 필요가 없었다(§41 ②). 8 문항 중 2 는 `Learning
# disabilities` 가 Disbiome·gutMDisorder 의 정신·신경 집합에 없어 못 잰다.
PAPER_PAIRS = (
    #  no, 문항,                        a MeSH,        b MeSH,        논문 판정
    (0, 'Autistic disorder and depression', 'D000067877', 'D003865', 1),
    (1, 'Parkinson disorder and depression', 'D010300', 'D003865', 1),
    (2, 'Learning disabilities and autism', None, 'D000067877', 1),
    (3, 'Anxiety and depression', 'D000098647', 'D003865', 1),
    (4, 'Bipolar disorder and depression', 'D001714', 'D003865', 1),
    (5, 'Learning disabilities and depression', None, 'D003865', 0),
    (6, 'Parkinson disorder and autism', 'D010300', 'D000067877', 0),
    (7, 'Alzheimer Disease and autism', 'D000544', 'D000067877', 1),
)


def paper_eval(source='curated'):
    """논문 Table 5 합병증 8 문항을 **그 소스로** 다시 잰다.

    `mikg` 는 포개짐 때문에 검정을 못 돌리므로(§41 ③) 기본은 `curated` 다.
    논문이 0 으로 둔 문항을 우리가 +1 로 통과시키면 **위양성**이다 — 전에
    MiKG 경로로는 8/8 을 통과시켜 그 둘이 다 위양성이었다.
    """
    sets, source = disease_sets(source)
    mesh = {k.rsplit('[', 1)[-1].rstrip(']'): k for k in sets}
    h = hypergeom(sets)
    idx = {}
    for r in h.itertuples(index=False):
        idx[frozenset((r.a, r.b))] = r
    rows = []
    for no, q, am, bm, paper in PAPER_PAIRS:
        ka, kb = mesh.get(am), mesh.get(bm)
        if not ka or not kb:
            rows.append({'no': no, 'item': q, 'paper': paper, 'ours': '',
                         'verdict': '못 잼', 'shared': '', 'expected': '', 'q': '',
                         'reason': f'{"a" if not ka else "b"} 질환이 {source} 에 없다'})
            continue
        r = idx.get(frozenset((ka, kb)))
        ours = 1 if (r is not None and r.q < 0.05) else 0
        rows.append({'no': no, 'item': q, 'paper': paper, 'ours': ours,
                     'verdict': '일치' if ours == paper else '불일치',
                     'shared': r.shared, 'expected': r.expected, 'q': f'{r.q:.2e}', 'reason': ''})
    return pd.DataFrame(rows), source


# ----------------------------------------------------------------------
# 문헌 점검 — **쌍마다 판정하지 않고 분포를 비교한다.**
#
# `curated` 에서 통과 못 한 336 쌍이 -1 후보다. 그 336 개를 PubMed 로 하나씩
# 판정하려 하면 안 된다. 두 가지 이유다.
#   ① 질환 쌍의 공출현은 **연구량에 좌우된다.** `Anxiety AND depression` 은
#      19 만 건인데 그건 "두 주제가 함께 연구된다" 는 뜻이고 동반이환의 크기가
#      아니다 (§4.3 에서 같은 이유로 색인 2 항 공출현을 버렸다).
#   ② 논문이 없는 것은 **관계가 없다는 뜻이 아니다** (§41 ①과 같은 오류).
#
# 그래서 **lift** 를 쓴다 — 우리 초기하수 검정과 같은 모양이다.
#     lift = 관측 공출현 / 기대 공출현,  기대 = n_A * n_B / N
# 그리고 336 개를 개별 판정하는 대신 **통과군 129 vs 비통과군 336 의 lift 분포**를
# 비교한다. 우리 q 가 신호를 담고 있으면 통과군의 lift 가 높아야 한다.
# 대조가 없으면 아무것도 말할 수 없으므로 **465 쌍 전부**를 본다.
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
PUBMED_N = 38_000_000      # PubMed 전체 규모(근사). lift 의 분모 상수다.


def _mesh_term(descriptor, session):
    """MeSH descriptor id -> 정식 용어 (PubMed `[MeSH Terms]` 에 쓴다).

    소스 라벨은 자유 표기라 그대로 질의하면 어긋난다 (`Parkinson's Disease` vs
    MeSH `Parkinson Disease`). id 에서 정식 용어를 받아 쓴다.
    """
    import json
    from common import cached_get
    txt = cached_get(f'mesh_term_{descriptor}.json', lambda: session.get(
        f'https://id.nlm.nih.gov/mesh/lookup/details?descriptor={descriptor}',
        timeout=60).text)
    d = json.loads(txt)
    for t in d.get('terms', []):
        if t.get('preferred'):
            return t['label']
    return None


def _pubmed_count(query, session):
    import json
    import time
    from common import cached_get
    key = 'pubmed_' + ''.join(c if c.isalnum() else '_' for c in query)[:120] + '.json'

    def fetch():
        time.sleep(0.35)                       # NCBI 레이트 리밋
        r = session.get(EUTILS, params={'db': 'pubmed', 'term': query,
                                        'rettype': 'count', 'retmode': 'json'},
                        timeout=60)
        r.raise_for_status()
        return r.text
    try:
        return int(json.loads(cached_get(key, fetch))['esearchresult']['count'])
    except Exception:
        return None


def literature(source='curated'):
    """통과군 vs 비통과군의 **PubMed lift 분포**를 비교한다."""
    import requests
    from scipy.stats import mannwhitneyu
    S = requests.Session()
    S.headers.update({'User-Agent': 'ourkg/1.0 (food4health reconstruction)'})
    p = outp(f'complication_hypergeom_{source}.csv')
    if not os.path.exists(p):
        sys.exit(f'{os.path.basename(p)} 가 없다. python3 ourkg/complication.py')
    h = pd.read_csv(p)
    mids = sorted({k.rsplit('[', 1)[-1].rstrip(']')
                   for k in set(h.a) | set(h.b)})
    term, n1 = {}, {}
    for i, m in enumerate(mids, 1):
        t = _mesh_term(m, S)
        if not t:
            continue
        term[m] = t
        n1[m] = _pubmed_count(f'"{t}"[MeSH Terms]', S)
        print(f'\r  질환 {i}/{len(mids)}  {t[:40]:42s}', end='', flush=True)
    print()
    rows = []
    for i, r in enumerate(h.itertuples(index=False), 1):
        am = r.a.rsplit('[', 1)[-1].rstrip(']')
        bm = r.b.rsplit('[', 1)[-1].rstrip(']')
        if am not in term or bm not in term or not n1.get(am) or not n1.get(bm):
            continue
        both = _pubmed_count(f'"{term[am]}"[MeSH Terms] AND "{term[bm]}"[MeSH Terms]', S)
        if both is None:
            continue
        exp = n1[am] * n1[bm] / PUBMED_N
        rows.append({'a': r.a, 'b': r.b, 'q': r.q, 'passed': bool(r.q < 0.05),
                     'n_a': n1[am], 'n_b': n1[bm], 'cooccur': both,
                     'expected': round(exp, 1),
                     'lift': round(both / exp, 2) if exp > 0 else None})
        print(f'\r  쌍 {i}/{len(h)}', end='', flush=True)
    print()
    t = pd.DataFrame(rows)
    t.to_csv(outp(f'complication_literature_{source}.csv'), index=False)
    ok = t[t['passed']].lift.dropna()
    no = t[~t['passed']].lift.dropna()
    print(f'\n  쌍 {len(t)} (통과 {len(ok)} · 비통과 {len(no)})'
          f'  -> out/complication_literature_{source}.csv')
    if len(ok) < 5 or len(no) < 5:
        print('  한쪽이 너무 적어 비교하지 않는다.')
        return t
    u = mannwhitneyu(ok, no, alternative='greater')
    auc = u.statistic / (len(ok) * len(no))
    print(f'  lift 중앙값 — 통과 {ok.median():.1f} / 비통과 {no.median():.1f}')
    print(f'  Mann-Whitney (통과 > 비통과)  AUC {auc:.3f}  p {u.pvalue:.4f}')
    print('  AUC 0.5 가 우연이다. lift 는 연구량을 보정한 값이지만 **동반이환의')
    print('  크기가 아니라 함께 연구된 정도**다 — 그 한계를 넘겨 읽지 않는다.')
    return t


def main():
    """**네 소스를 모두 본다.** 거부는 정상 결과이므로 exit 0 이다.

    `mikg` 가 거부되는 것이 이 모듈의 결론이고, 그것이 파이프라인 실패는 아니다
    — `run_all.py` 가 거기서 멈추면 안 된다.
    """
    only = os.environ.get('COMP_SOURCE')
    rows = [one(s) for s in ([only] if only else SOURCES)]
    t = pd.DataFrame(rows)
    t.to_csv(outp('complication_summary.csv'), index=False)
    print('\n== 요약  -> out/complication_summary.csv')
    print(t.to_string(index=False))

    # 논문 Table 5 합병증 8 문항을 검정이 가능한 소스로 다시 잰다.
    pe, src = paper_eval(os.environ.get('COMP_PAPER_SOURCE', 'curated'))
    pe.to_csv(outp('complication_paper_eval.csv'), index=False)
    ok = int((pe['verdict'] == '일치').sum())
    na = int((pe['verdict'] == '못 잼').sum())
    print(f'\n== 논문 Table 5 합병증 8 문항 ({src})'
          f'  -> out/complication_paper_eval.csv')
    print(pe.to_string(index=False))
    print(f'\n  일치 {ok} / 잴 수 있는 {len(pe) - na} (못 잼 {na})')
    print('  논문이 0 으로 둔 문항을 우리가 1 로 통과시키면 위양성이다 —')
    print('  MiKG 경로로는 8/8 을 통과시켜 그 둘이 다 위양성이었다.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'literature':
        # **`COMP_SOURCE` 를 재사용하면 안 된다.** 이 하위명령의 기본값은
        # `curated` 이고 `disease_sets` 의 기본값은 `mikg` 라, 같은 변수에 기본값이
        # 둘이 됐다(검사가 잡았다 — §51). `COMP_PAPER_SOURCE` 선례대로 떼어 둔다.
        literature(os.environ.get('COMP_LIT_SOURCE', 'curated'))
        sys.exit(0)
    sys.exit(main())
