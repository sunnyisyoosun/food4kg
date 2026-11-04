"""
재현율 집계
============
논문의 주장을 층위별로 나눠 무엇이 얼마나 재현되었는지 센다.
단일 퍼센트는 오해를 부르므로 층위를 분리한다.
(구 eval/paper_ranking.py 통합 — NDCG@30, 교차 겹침)

실행: python3 tools/scorecard.py
"""

import json
import os
import re
import sys

import numpy as np
import pandas as pd

import core
import paper

sys.path.insert(0, os.path.join(core.BASE, 'eval'))
import m1 as M1
import paper_kg_stats as KGS
import paper_data as PN

_SQ_PATH = f'{core.OUT}/paper_sparql_summary.json'
SQ = json.load(open(_SQ_PATH)) if os.path.exists(_SQ_PATH) else None
_RP_PATH = f'{core.OUT}/paper_sparql_replaceable.json'
RP = json.load(open(_RP_PATH)) if os.path.exists(_RP_PATH) else None

d = core.Data.load()
m = core.metrics(d, d.score())
food = pd.read_csv(f'{core.OUT}/food.csv')
fn = pd.read_csv(f'{core.OUT}/foodname.csv')
nz = (d.X != 0).sum(1)
n_dir = int((d.E != 0).sum())

# 논문 순위 대조 부가 지표
idx, rank, p5, ptop, pbot = core.paper_ranking(d.names)
p = d.score()
order = [idx[j] for j in np.argsort(-p[idx])]
top = {d.names[i] for i in order[:core.K]}
bot = {d.names[i] for i in order[-core.K:]}
n = len(idx)
rank_of = dict(zip([d.names[i] for i in idx], rank))
rel = np.array([max(0.0, (n - rank_of[d.names[i]]) / n) for i in order])
disc = 1.0 / np.log2(np.arange(2, core.K + 2))
ndcg = float((rel[:core.K] * disc).sum() /
             (np.sort(rel)[::-1][:core.K] * disc).sum())

# 논문 주장 (무작위 기준선 없이 통과 여부만; 전체는 tools/paper.py claims)
cl = paper.evaluate_claims(p, d, paper._groups(d.cols))
n_claims = sum(v[1] for v in cl.values())
pca = paper.c4_pca(d.Xn, d.E)['Xn*E']

# ------------------------------------------------------------------
# --check-docs : 문서에 손으로 적은 수치가 현재 값과 맞는가 (§17.19)
#   "논문 수식은 꼴찌(−0.543)" 가 극성 교정 뒤에도 세 문서에 5주간 남아
#   거짓 주장이 되어 있었다. 재실행 한 번이면 드러나는 것이었다.
#   아래 등록표의 정규식으로 문서를 긁어 현재 값과 대조한다.
# ------------------------------------------------------------------
def canonical():
    """문서가 인용해도 되는 정본 수치."""
    c = {
        'spearman': f'{m["spearman"]:+.3f}',
        'top30': str(m['top_overlap']),
        'a_rec': f'{m["top30_rec"]}/30',
        'a_not': f'{m["bot30_not"]}/30',
        'bot30': str(m['bot_overlap']),
        'gold': m['gold'].strip(),
        'edir': str(n_dir),
        'density': str(int(np.median(nz))),
        'pca': str(pca),
        'claims': str(n_claims),
    }
    _m1 = M1.load_cached()
    if _m1 is not None:
        _s1 = M1.summary(_m1)
        c.update(m1_rep=str(_s1['reproduced']), m1_both=str(_s1['both']))
    _i = KGS.load_cached_inference()
    if _i:
        c['infer_total'] = f'{_i["inferred_total"]:,d}'
    _c = KGS.load_cached_complication()
    if _c:
        c['compl_pair'] = f'{_c["cond1_2"]}/{_c["n_pair_mental"]}'
        c['compl_tri'] = str(_c['triples'])
        c['compl_all'] = f'{_c["triples_all"]:,d}'
        c['compl_t5'] = f'{_c["t5_cond1"]}/{_c["t5_total"]}'
        c['compl_ev'] = f'{_c["t5_evidence"]}/{_c["t5_total"]}'
    _a = PN.audit()
    c['au_cons'] = f'{_a["consensus"]} / {_a["n_question"]}'
    c['au_majw'] = str(_a['majority_wrong'])
    c['au_noninf'] = str(_a['not_inferred_items'])
    c['au_rate'] = str(_a['confirmed_rate'])
    _cv = KGS.load_cached_coverage()
    if _cv:
        c['cov_ratio'] = str(_cv['ratio'])
        c['cov_both'] = str(_cv['n_both'])
    if RP:
        c['rp_usable'] = str(RP['mikg_usable'])
    if SQ:
        c.update(t3=str(SQ['table3']), t3v=str(SQ.get('table3_verbatim', '')), t4=str(SQ['table4_raw']),
                 t2=str(SQ['table2']), t5c=str(SQ['t5_complication']),
                 t5d=str(SQ['t5_diet']), kg_total=f'{SQ["kg_total"]:,d}',
                 t4bad=str(SQ.get('table4_badname', '')))
    return c


# (파일, 키, 정규식)  — 정규식의 첫 그룹이 문서에 적힌 값
DOC_CLAIMS = [
    ('REPRODUCTION.md', 'a_rec', r"`metrics\(\)\['top30_rec'\]` — 현재 \*\*(\d+/30)\*\*"),
    ('REPRODUCTION.md', 'a_not', r"`metrics\(\)\['bot30_not'\]` — 현재 \*\*(\d+/30)\*\*"),
    ('README.md',       'spearman', r'순위 Spearman ※ \| \*\*([+-][\d.]+)\*\*'),
    ('README.md',       'top30',    r'Top30 겹침\*\* \(우연 6\.7\) ※ \| \*\*(\d+) / 30'),
    ('README.md',       'bot30',    r'Bottom30 겹침\*\* \(우연 6\.7\) ※ \| \*\*(\d+) / 30'),
    ('README.md',       'edir',     r'E 방향 확보 \| (\d+) / 85'),
    ('README.md',       'density',  r'측정 밀도 \(compound 수 중앙값\) \| (\d+)'),
    ('README.md',       'gold',     r'명시한 compound \(gold\) \| (\d+ / \d+)'),
    ('README.md',       'kg_total', r'공개 KG 는 ([\d,]+) 트리플이다'),
    ('PROBLEMS.md',     'spearman', r'Spearman ([+-][\d.]+)'),
    ('REPRODUCTION.md', 't3v', r'#### \(1\) 원문 쿼리만으로는 \*\*(\d+)/8\*\*'),
    ('REPRODUCTION.md', 'rp_usable', r'하위 10종 중 조건 만족: \*\*(\d+)종\*\*'),
    ('REPRODUCTION.md', 'infer_total', r'합계\s+([\d,]+)\s+논문 4,741,023'),
    ('REPRODUCTION.md', 'compl_pair', r'조건 \(1\) 세균 공유\s+(\d+/\d+) 쌍   → 트리플'),
    ('REPRODUCTION.md', 'compl_tri',  r'조건 \(1\) 세균 공유\s+\d+/\d+ 쌍   → 트리플 (\d+)개'),
    ('REPRODUCTION.md', 'compl_all',  r'→ 트리플 ([\d,]+)개\n```'),
    ('REPRODUCTION.md', 'compl_t5',   r'\| Table 5 Complication 8행 \| \*\*(\d+/\d+)\*\*'),
    ('README.md',       'compl_t5',   r'Table 5 Complication \*\*(\d+/\d+)\*\*'),
    ('REPRODUCTION.md', 'compl_ev',   r'논문이 Table 5 에 적은 \*\*그 세균\*\*이 두 질병에 붙는가 \| \*\*(\d+/\d+)\*\*'),
    ('REPRODUCTION.md', 'cov_ratio',  r'아미노산 최대 261 vs 비타민 최소 5,085 — \*\*([\d.]+)배\*\*'),
    ('REPRODUCTION.md', 'au_cons',   r'3인 만장일치\s+(\d+ / \d+)'),
    ('REPRODUCTION.md', 'au_majw',   r'2인 이상이 오답으로 본 문항\s+(\d+) / 20'),
    ('REPRODUCTION.md', 'au_noninf', r'Diet recommendation  (\d+)건'),
    ('REPRODUCTION.md', 'au_rate',   r'확인율 ([\d.]+)      unknown'),
    ('REPRODUCTION.md', 'cov_both',   r'둘 다 가진 세균\s+(\d+)\s+← 4단 경로'),
    ('REPRODUCTION.md', 't4bad', r'`질병명 불일치 (\d+)/5` 를 매 실행 출력한다'),
    ('REPRODUCTION.md', 't5c',      r'방법 2 \(Table 5\)  Complication (\d+)/8'),
    ('REPRODUCTION.md', 't5d',      r'Complication \d+/8,  Diet recommendation (\d+)/7'),
]


def check_docs():
    can = canonical()
    bad = miss = ok = 0
    print('=' * 70)
    print('문서 수치 검사 — 손으로 적은 값이 현재 값과 맞는가')
    print('=' * 70)
    for fn, key, pat in DOC_CLAIMS:
        path = os.path.join(core.BASE, fn)
        if key not in can:
            print(f'  ?  {fn:16s} {key:10s} 정본 없음 (캐시 미생성)')
            miss += 1
            continue
        txt = open(path).read()
        found = re.search(pat, txt)
        if not found:
            print(f'  ?  {fn:16s} {key:10s} 패턴 불일치 — 문서 표현이 바뀌었다')
            miss += 1
        elif found.group(1).replace(' ', '') == can[key].replace(' ', ''):
            ok += 1
        else:
            print(f'  ✘  {fn:16s} {key:10s} 문서 "{found.group(1)}" vs 현재 "{can[key]}"')
            bad += 1
    print()
    print(f'  일치 {ok} / 불일치 {bad} / 확인불가 {miss}   (등록 {len(DOC_CLAIMS)}건)')
    if bad:
        print('  ⚠ 문서를 고치거나, 값이 바뀐 이유를 기록할 것')
    return bad


if '--check-docs' in sys.argv:
    sys.exit(1 if check_docs() else 0)

print('=' * 70)
print('Food4healthKG 재현 집계')
print('=' * 70)
print()
print('[0] 논문 §3 KG 구축 — Table 1 통계 · Entity linking · 관계 표현')
_kgs = KGS.load_cached()
if _kgs is None:
    print('    캐시 없음 — python3 eval/paper_kg_stats.py 를 먼저 실행하면 여기에 나온다')
else:
    s0 = KGS.summary(_kgs)
    print(f'    Relation 열          {s0["relation_match"]}/{s0["n_present"]} 소스 일치 (합 정의)   '
          f'공개 KG 합 {s0["relation_total_sum"]} / 논문 열 합 {s0["paper_relation_colsum"]}'
          f' (Total 행은 {s0["paper"]["relation"]})')
    print(f'    Entity 열            {s0["entity_match"]}/{s0["n_present"]} 소스 일치   '
          f'공개 KG 합 {s0["entity_total"]:,d} / 논문 열 합 {s0["paper_entity_colsum"]:,d}'
          f' (Total 행은 {s0["paper"]["entity"]:,d})')
    if SQ:
        print(f'    Triples 열           {SQ["table1_match"]}/{SQ["table1_n"]} 소스 일치   '
              f'공개 KG 총 {SQ["kg_total"]:,d}')
    else:
        print('    Triples 열           → python3 eval/paper_sparql.py 를 돌리면 여기에 나온다')
    _lnk = KGS.load_cached_linking()
    if _lnk is not None:
        sl = KGS.linking_summary(_lnk)
        print(f'    §3.2 Entity linking  {sl["n_item_match"]}/{sl["n_item"]} 항목 일치   '
              f'(확정 {sl["n_item_confirmed"]}, 추정 '
              f'{sl["n_item_match"] - sl["n_item_confirmed"]} — 128 = 64×2 는 재구성)')
        print('                         합계 1,637,915 만 미해결 (SNOMED 부재) '
              '— REPRODUCTION §17.12')
    _inf = KGS.load_cached_inference()
    if _inf:
        print(f'    §3.3 추론 규칙(a)   전이 {_inf["inferred_hierarchy"]:,d} + '
              f'타입전파 {_inf["inferred_type"]:,d} = {_inf["inferred_total"]:,d}  '
              f'논문 {_inf["paper_inferred"]:,d} 의 '
              f'{_inf["inferred_total"]/_inf["paper_inferred"]*100:.1f}% (§17.20)')
        _top = next(iter(_inf['by_source'].items()))
        print(f'                         생성의 {_top[1]/_inf["inferred_hierarchy"]*100:.0f}%'
              f'가 {_top[0]} (NCBI 계통수). 논문 예시인 KEGG 는 '
              f'{_inf["by_source"].get("KEGG_Compound.jsonld", 0):,d}건')
    _cp = KGS.load_cached_complication()
    if _cp:
        print(f'    §3.3 추론 규칙(b)   합병증 {_cp["cond1_2"]}/{_cp["n_pair_mental"]} 쌍 '
              f'= 트리플 {_cp["triples"]}개   '
              f'Table 5 {_cp["t5_cond1"]}/{_cp["t5_total"]}'
              f'(조건2까지 {_cp["t5_cond1_2"]}, 근거세균 {_cp["t5_evidence"]}), '
              f'Table 4 {_cp["t4_cond1_2"]}/{_cp["t4_total"]} (§17.24)')
        print(f'                         정신질환 안에서는 완전그래프(변별력 0). '
              f'질병 {_cp["n_disease"]}종 전체로 넓히면 트리플 {_cp["triples_all"]:,d}개')
    _rel = KGS.load_cached_relations()
    if _rel is not None:
        sr = KGS.relations_summary(_rel)
        print(f'    §3.3 관계 어휘       {sr["present"]}/{sr["n"]} 존재   '
              f'(self-defined {sr["self_defined"]}/3, predefined {sr["predefined"]}/3)'
              f'   추론 0 / 논문 {sr["inferred_paper"]:,d}')
        print('    §3.3 관계 계층       선언 0건 · 일반↔하위 겹침 0건 (방향이 반대) '
              '— 명명 규약일 뿐 (§17.13)')
    print('    §3.1 본문 수치        2/3 일치 — FDC 34,250 · KEGG metabolites 230 / '
          'NCBI 322,917 만 1.2% 차이')
print()
_pn = PN.summary()
print(f'    논문 수치 체크리스트   {_pn["total"]}개 — '
      f'일치 {_pn.get("MATCH",0)} · 추정 {_pn.get("MATCH_EST",0)} · '
      f'불일치 {_pn.get("MISMATCH",0)} · 미검증 {_pn.get("UNTESTED",0)} · '
      f'대상외 {_pn.get("NA",0)}')
print('                         불일치는 tools/paper.py hunt 탐색 후에만 표시 가능 '
      '(eval/paper_data.py)')
_au = PN.audit()
print(f'    §5.1 평가 방식 점검    방법1 {_au["accuracy"]} = 전문가별 동의율 '
      f'(gold 아님). 만장일치 {_au["consensus"]}/{_au["n_question"]}, '
      f'다수가 오답으로 본 문항 {_au["majority_wrong"]}개 → 포화')
print(f'                         방법2 {_au["n_item"]}건 중 '
      f'{_au["not_inferred_items"]}건은 추론이 아님(Diet). '
      f'확인율 {_au["confirmed_rate"]} (unknown 제외 '
      f'{_au["confirmed_rate_excl_unknown"]})')
print('                         추천 알고리즘(§4.2)은 두 평가 어디에도 없다 (§17.27)')
print()
print('[1] 데이터 재구성 — 형태·규모')
print(f'    compound            85 / 85          (100%)  ※ heatmap.xlsx 에서 받아옴')
print(f'    food               {len(food)} / 135         ({len(food)/135*100:.0f}%)')
print(f'    foodname.csv 형상  {fn.shape} vs (135, 88)')
print(f'    측정 밀도 중앙값    {np.median(nz):.0f} / 33        ({np.median(nz)/33*100:.0f}%)')
print(f'    PCA(Xn⊙E) 80%      {pca} 성분 / 논문 5    {"✅" if pca == 5 else "❌"}')
print('    F vs 논문 heatmap  → python3 tools/paper.py units')
print()
print('[2] 핵심 입력 E (compound-depression 방향)')
print(f'    방향 확보           {n_dir} / 85          ({n_dir/85*100:.0f}%)')
print(f'    논문 명시 부호 일치  {m["gold"]:>5s}           '
      f'※ Fig5 PMID + Table 3/4/5')
if m['gold_miss']:
    print(f'      실패: {", ".join(m["gold_miss"])}')
print()
print('[3] 추천 결과 — 논문 순위(p5) 대조   ★ 핵심')
print(f'    Spearman           {m["spearman"]:+.3f}         (1.0 일치, 0 무관, 음수 역행)')
print(f'    Top30 겹침          {m["top_overlap"]} / 30          우연 기대값 {m["chance"]:.1f}')
print(f'    Bottom30 겹침       {m["bot_overlap"]} / 30          우연 기대값 {m["chance"]:.1f}')
print(f'    NDCG@30            {ndcg:.3f}          (논문에 없는 참고 지표)')
print(f'    우리 Top30∩논문 Bot30 {len(top & pbot)}개,  우리 Bot30∩논문 Top30 {len(bot & ptop)}개')
print()
print('    참고 — 카테고리 지표 (약함. 상위30에 과일 1개만 있어도 만점)')
print(f'      top30_rec {m["top30_rec"]}  bot30_not {m["bot30_not"]}  '
      f'카테고리 추천 {m["cat_rec"]}, 비추천 {m["cat_not"]}')
print()
print('[4] 논문 주장 (§4.2.3 / Fig. 4·5) — tools/paper.py claims')
print('    ' + '  '.join(f'{k}={"O" if v[1] else "X"}' for k, v in cl.items())
      + f'   통과 {n_claims}/{len(cl)}  (논문 순위 자신은 4/6)')
print()
print('[5] 논문 §5.1 평가')
# 방법 1 — eval/m1.py 가 고정한 (질문, 논문 정답, 검증쿼리) 20삼중항의 집계.
# 캐시(analyse/paper_eval_table1.csv)를 읽고, 없으면 공개 KG 에 직접 질의한다.
_m1 = M1.load_cached()
if _m1 is None:
    print('    방법1 캐시 없음 — 공개 KG 질의 중 (python3 eval/m1.py)')
    _m1 = M1.run()
    _m1.to_csv(M1.CSV, index=False)
s1 = M1.summary(_m1)
print(f'    방법1 전문가 20문항  전사 확인 V0/V1/V2 '
      + '/'.join(f'{a:.2f}' for a in s1['transcript_accuracy'])
      + '  논문 ' + '/'.join(f'{a:.2f}' for a in s1['paper_accuracy'])
      + ('  OK' if all(abs(a - b) < 1e-9 for a, b in
                       zip(s1['transcript_accuracy'], s1['paper_accuracy'])) else '  MISMATCH'))
print(f'                        공개 KG 로 답 재현 {s1["reproduced"]}/{s1["n"]}'
      f' (△{s1["reproduced_partial"]} X{s1["reproduced_fail"]}),'
      f' 재현되고 타당 {s1["both"]}/{s1["n"]}')
_short = {'food categories': 'food-cat', 'compounds in food and gut': 'cmp-in-food',
          'weight calculation': 'weight', 'disease classification': 'disease',
          'compounds categories': 'cmp-cat', 'bacteria taxonomy': 'bacteria'}
_c, _d = s1['consensus'], s1['dissent']
print(f'                        전문가 전원동의 {_c["n"]}문항 한정  재현 '
      f'{_c["reproduced"]}/{_c["n"]}, 재현∧타당 {_c["both"]}/{_c["n"]}'
      f'   (이견 {_d["n"]}문항 #{", #".join(map(str, s1["dissent_no"]))} 은 전문가 답 불명)')
print('                        aspect별 재현  '
      + '  '.join(f'{_short.get(k, k)} {v[0]}/{v[1]}' for k, v in s1['by_aspect'].items()))
print('                        (전문가 답 자체는 논문·부록·공식 repo 어디에도 없다. eval/m1.py)')
if SQ:
    print(f'    방법2 문헌검증 15건  엄격 기준 Complication {SQ["t5_complication"]}/8, '
          f'Diet {SQ["t5_diet"]}/7 (묶지 않으면 {SQ["t5_diet_loose"]}/7)')
    print(f'                        논문 보고 11/15 는 PubMed 결과. 우리는 KG 근거만 본다')
    print(f'    쿼리 → 표           Table 3 {SQ["table3"]}/8 '
          f'(원문 쿼리만으로는 {SQ.get("table3_verbatim","?")}/8, '
          f'논문 (+)/(-) 부호는 {SQ.get("table3_both_sided","?")}/8 이 '
          f'KG pos·neg 양쪽이라 유도 불가 §17.22), '
          f'Table 4 원문 {SQ["table4_raw"]}/5·묶으면 {SQ["table4_joined"]}/5 '
          f'(MiKG 로 SNOMED 이름 복원),')
    print(f'                        Table 2 {SQ["table2"]}/8 — 단 쿼리 결함으로 값이 틀림')
if RP:
    print(f'    §4.1 엔티티 교체     Q2·Q3 는 MiKG 질환 {RP["mikg_total"]}종 중 '
          f'{RP["mikg_usable"]}종만 가능 '
          f'({", ".join(RP["disorders_with_relation"])}만 pos/neg 관계 보유)')
    print(f'                        Q1 은 영양소·음식 조합 '
          f'{sum(1 for v in RP["q1_variants"].values() if v)}/'
          f'{len(RP["q1_variants"])} 모두 결과 — 논문 주장대로 (§17.21)')
else:
    print('    방법2·쿼리→표        → python3 eval/paper_sparql.py (약 4분) 를 먼저 실행')
print()
print('=' * 70)
print('요약')
print('=' * 70)
beats = m['top_overlap'] > m['chance'] and m['spearman'] > 0
print(f'  추천 순위: {"우연 수준을 넘는다" if beats else "우연 수준이다"} '
      f'(Top30 {m["top_overlap"]}/30, Bot30 {m["bot_overlap"]}/30, '
      f'Spearman {m["spearman"]:+.3f})')
print(f'  논문 주장: {n_claims}/{len(cl)} 통과')
print('  남은 격차: 논문의 E 는 weight.csv 가 배포되지 않아 확정할 수 없다.')
print('             순위의 상당 부분은 식물/동물 1비트(+0.695)로도 설명된다')
print('             (REPRODUCTION.md §16.6).')
