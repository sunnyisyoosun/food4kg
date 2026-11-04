"""
논문 §5.1 평가 재현
====================
논문은 두 가지 평가를 쓴다. NDCG나 순위 지표는 쓰지 않는다(확인: 논문·공식
final.py 모두 'ndcg'/'dcg' 문자열 0건. 공식 코드의 AP/hit/precision/recall은
정의만 있고 cal_results()에서 전부 주석 처리되어 있다).

  방법 1  전문가 20문항 수작업 대조 (Supplementary Table 1)
          논문 결과: 전문가 3인 대비 정확도 0.95 / 0.90 / 0.95
  방법 2  문헌 검증 15건 (Table 5)
          논문 결과: 11 confirmed / 1 contradicted / 3 unknown

재현 범위
---------
방법 1의 원형(전문가가 원본 데이터에서 손으로 답을 찾아 대조)은 재현 불가능하다.
대신 공개 KG(foodkg_triply/)에 20문항을 직접 질의해 **논문이 보고한 답이 나오는가**
(재현)와 **그 답이 질문에 맞는가**(타당)를 판정한다. 전문가 대조가 아니라 KG 답의
재현이다. 결과는 analyse/paper_eval_table1.csv.

방법 2는 문헌 검증 결과(1/-1/0)를 논문에서 그대로 받고, **우리 KG가 같은 추론을
만들어내는가**를 확인한다. PubMed 재검색은 하지 않는다.

실행: python3 eval/run_paper_eval.py
"""
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BASE)

import m1
from m1 import FKG, OUT, load_bacteria_names, load_disease_bacteria, load_disease_labels
from paper_data import TABLE5, PAPER_COUNTS
import kegg_alias


# ------------------------------------------------------------------
# 방법 2 — Table 5 추론 재현
# ------------------------------------------------------------------
def eval_table5():
    print('=' * 74)
    print('방법 2 — 문헌 검증 대상 추론 15건 (논문 Table 5)')
    print('=' * 74)
    print('  논문 보고: confirmed 11 / contradicted 1 / unknown 3')
    print('  여기서 보는 것: 우리 KG가 같은 추론을 만들어내는가')
    print()

    bac_names = load_bacteria_names()
    name2bac = {}
    for bid, nm in bac_names.items():
        name2bac.setdefault(nm.strip().lower(), set()).add(bid)
    bac2dis = load_disease_bacteria()
    dis_labels = load_disease_labels()

    weight = pd.read_csv(os.path.join(OUT, 'weight.csv'))
    E = {c: (1 if weight[c].iloc[0] > 0 else (-1 if weight[c].iloc[1] > 0 else 0))
         for c in weight.columns}
    p85 = pd.read_csv(os.path.join(OUT, 'paper85_compounds.csv'))
    name2kegg = {str(n).strip().lower(): k for k, n in zip(p85.kegg, p85['name'])}
    # Table 5의 표기 흔들림 보정
    name2kegg.setdefault('threonine', 'C00188')
    name2kegg.setdefault('l-threonine', 'C00188')
    name2kegg.setdefault('ascorbate', 'C00072')
    name2kegg.setdefault('nicotinic acid', 'C00253')
    name2kegg.setdefault('alpha-tocopherol', 'C02477')

    rows = []
    for no, q, attr, ev, pmid, result in TABLE5:
        evl = ev.strip().lower()
        if attr == 'Complication':
            bids = name2bac.get(evl, set())
            n_dis = sum(len(bac2dis.get(b, ())) for b in bids)
            ok = bool(bids) and n_dis > 0
            detail = (f'KG에 세균 {"있음" if bids else "없음"}, '
                      f'연결된 질병 {n_dis}건')
        else:
            kegg = name2kegg.get(evl)
            if kegg is None or kegg not in E:
                # 논문 Table 3/5의 compound가 Fig.4(c)의 85 목록에 없는 경우.
                # 논문 내부 불일치이지 우리 KG의 실패가 아니다(§4 참조).
                ok = False
                detail = f'{kegg or "?"} — 85 목록 밖 (논문 내부 불일치)'
            else:
                d = E[kegg]
                ok = d != 0
                detail = (f'{kegg} incidence='
                          f'{"+" if d > 0 else ("-" if d < 0 else "0")}')
        rows.append(dict(no=no, attribute=attr, question=q, evidence=ev,
                         paper=result, reproduced=ok, detail=detail))

    df = pd.DataFrame(rows)
    for _, r in df.iterrows():
        mark = 'O' if r.reproduced else 'X'
        lab = {1: 'confirmed', -1: 'contradicted', 0: 'unknown'}[r.paper]
        print(f'  {mark} #{r.no:<2d} [{r.attribute[:12]:12s}] {r.question[:38]:39s} '
              f'{lab:12s} {r.detail}')

    n = len(df)
    rep = int(df.reproduced.sum())
    print()
    outside = int((df.detail.str.contains('85 목록 밖')).sum())
    print(f'  KG 추론 재현: {rep}/{n}'
          + (f'   (실패 {n-rep}건 중 {outside}건은 compound가 85 목록 밖)'
             if outside else ''))
    for lab, val in ((1, 'confirmed'), (-1, 'contradicted'), (0, 'unknown')):
        sub = df[df.paper == lab]
        print(f'    {val:12s} 논문 {PAPER_COUNTS[lab]}건 중 재현 '
              f'{int(sub.reproduced.sum())}건')
    return df


# ------------------------------------------------------------------
# 방법 1 — Table 1 20문항
# ------------------------------------------------------------------
# (질문, 논문 정답, 검증쿼리) 삼중항과 질의 구현은 eval/m1.py 에 고정돼 있다.
def eval_table1():
    return m1.report()


if __name__ == '__main__':
    df = eval_table5()
    eval_table1()          # analyse/paper_eval_table1.csv 는 m1.report() 가 저장한다
    print()
    out = os.path.join(OUT, 'paper_eval_table5.csv')
    df.to_csv(out, index=False)
    print(f'저장: {out}')
