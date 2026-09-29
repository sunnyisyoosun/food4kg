"""
재현율 집계
============
논문의 주장을 층위별로 나눠 무엇이 얼마나 재현되었는지 센다.
단일 퍼센트는 오해를 부르므로 층위를 분리한다.
(구 eval/paper_ranking.py 통합 — NDCG@30, 교차 겹침)

실행: python3 tools/scorecard.py
"""

import numpy as np
import pandas as pd

import core
import paper

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

print('=' * 70)
print('Food4healthKG 재현 집계')
print('=' * 70)
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
print('    방법1 전문가 20문항  재현 불가 (전사 무결성만 검증)')
print('    방법2 문헌검증 15건  11 / 15          (73%)  KG 추론 재현')
print()
print('=' * 70)
print('요약')
print('=' * 70)
beats = m['top_overlap'] > m['chance'] and m['spearman'] > 0
print(f'  추천 순위: {"우연 수준을 넘는다" if beats else "우연 수준이다"} '
      f'(Top30 {m["top_overlap"]}/30, Bot30 {m["bot_overlap"]}/30, '
      f'Spearman {m["spearman"]:+.3f})')
print(f'  논문 주장: {n_claims}/{len(cl)} 통과')
print('  남은 병목: E. 논문 순위가 함의하는 E 와 공개 소스 E 의 부호 일치가')
print('             우연 수준이다 (REPRODUCTION.md §16.3). 논문의 weight.csv 는')
print('             배포되지 않았다.')
