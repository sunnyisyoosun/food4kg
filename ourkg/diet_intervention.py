"""식이 중재 → 미생물 (gutMDisorder) 로 **E 를 외부에서 검정한다**.

왜 이게 필요한가
----------------
`E x F^T` 에 미생물이 들어갈 자리가 없다는 구조 문제(RESULTS §A)와, 미생물
축에 방향 신호가 없다는 결과(§31·§32)는 모두 **관측 데이터**로 얻은 것이다 —
"질환에서 늘어난 균" 이다. 그건 인과가 아니다. 환자가 아파서 그 균이 늘었을
수도 있다.

중재 데이터는 다르다. **음식을 주고 균이 변하는 것을 본 것**이라 방향이
음식 → 미생물 이다. gutMDisorder 의 식이 중재 행(`common.
gutmdisorder_intervention`)이 그 자료다. 우리 `E` 와 compound-미생물 축이
gut-brain 가정을 담고 있다면, **이 자료로 검정할 수 있다.**

미리 고정한 예측 (계산 전에 적는다)
-----------------------------------
`score(중재) = 늘어난 균이 대사하는 compound 의 평균 E
             - 줄어든 균이 대사하는 compound 의 평균 E`

- **지중해식 > 0** — ModiMedDiet(SMILES RCT)가 우울증에 처방한 바로 그 식단이고
  우리 외부 기준이다. 우리 축이 맞으면 양수여야 한다.
- **고지방식 < 0** — 같은 축에서 반대로 가야 한다.

이 두 줄을 먼저 적어 두는 이유는, 48 개 중재 점수를 다 본 뒤 양수인 것을
골라 "맞았다" 고 말하는 것을 막기 위해서다.

읽을 때의 한계
--------------
`compound_microbe` 는 "이 균의 유전체에 이 compound 를 다루는 효소가 있다" 이고
**분해인지 생산인지 모른다**(§15b 와 같은 한계). 그래서 이 검정이 음수로
나와도 "가정이 틀렸다" 가 아니라 "이 자료로는 못 본다" 일 수 있다. 양수로
나왔을 때만 한 방향으로 강한 주장이 된다.

쓰는 법
-------
    python3 ourkg/diet_intervention.py            # 검정
    python3 ourkg/diet_intervention.py map        # 음식 매칭 커버리지
환경변수
    IV_RANK=species   종 수준 compound 링크만 (기본 all)
    IV_PERM=2000      순열 횟수
"""
import os
import re
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (OUT, BASE, gutmdisorder_intervention, compound_microbe,
                    depression_e)

# 미리 고정한 대조. 키는 intervention 표기에 대한 정규식이다.
PRESPECIFIED = (
    ('지중해식 (ModiMedDiet 처방)', r'^Diet, Mediterranean', '> 0'),
    ('고지방식', r'^(Diet, High-Fat|Higher-fat diet)$', '< 0'),
)


def _microbe_e(rank=None):
    """균 taxid → 그 균이 대사하는 compound 의 평균 E."""
    e = depression_e('e_shrunk')
    cm = compound_microbe(rank=rank)
    cm = cm[cm.kegg.isin(e.index)].copy()
    cm['e'] = cm.kegg.map(e)
    g = cm.groupby('taxid')['e'].agg(['mean', 'size'])
    return g['mean'], g['size']


def _score(df, me):
    """늘어난 균의 평균 E − 줄어든 균의 평균 E."""
    up = df.loc[df.alteration == 'increase', 'taxid'].map(me).dropna()
    dn = df.loc[df.alteration == 'decrease', 'taxid'].map(me).dropna()
    if not len(up) or not len(dn):
        return np.nan, len(up), len(dn)
    return float(up.mean() - dn.mean()), len(up), len(dn)


def test():
    rank = os.environ.get('IV_RANK') or None
    nperm = int(os.environ.get('IV_PERM', '2000'))
    rng = np.random.default_rng(0)

    me, nc = _microbe_e(rank)
    iv = gutmdisorder_intervention()
    iv = iv[iv.alteration.isin(('increase', 'decrease'))]
    iv = iv[iv.taxid.isin(me.index)]
    iv.to_csv(os.path.join(OUT, 'diet_intervention.csv'), index=False)
    print(f'[1/3] 쓸 수 있는 행 {len(iv)} / 중재 {iv.intervention.nunique()} '
          f'/ 균 {iv.taxid.nunique()} (compound 링크 있는 균만)')
    print(f'      균당 compound 수 중앙값 {int(nc.reindex(iv.taxid.unique()).median())}')

    rows = []
    for name, g in iv.groupby('intervention'):
        s, nu, nd = _score(g, me)
        if np.isnan(s):
            continue
        # 순열: 같은 균 집합에서 증가/감소 라벨만 섞는다. 균 구성이 아니라
        # **방향이** 신호를 내는지 본다.
        # pandas StringArray 를 그대로 섞으면 numpy 가 '올바름을 보장하지
        # 못한다' 고 경고한다 — object ndarray 로 바꿔 섞는다.
        lab = g.alteration.to_numpy(dtype=object).copy()
        null = np.empty(nperm)
        for i in range(nperm):
            rng.shuffle(lab)
            h = g.assign(alteration=lab)
            null[i] = _score(h, me)[0]
        null = null[~np.isnan(null)]
        p = float((null >= s).mean()) if len(null) else np.nan
        rows.append({'중재': name[:46], 'n증가': nu, 'n감소': nd,
                     'score': round(s, 4),
                     '귀무': round(float(null.mean()), 4) if len(null) else np.nan,
                     'p(>)': round(p, 3)})
    t = pd.DataFrame(rows).sort_values('score', ascending=False)
    # 29 개 중재를 다 재고 가장 작은 p 를 집으면 안 된다 — BH 로 보정한다.
    from scipy.stats import false_discovery_control
    if len(t):
        t['q(BH)'] = false_discovery_control(t['p(>)'].clip(1e-6, 1).values).round(3)
    t.to_csv(os.path.join(OUT, 'diet_intervention_score.csv'), index=False)

    print('\n[2/3] 미리 고정한 예측 — 이것이 주검정이다')
    hit = 0
    for label, pat, expect in PRESPECIFIED:
        sel = iv[iv.intervention.str.match(pat)]
        s, nu, nd = _score(sel, me)
        if np.isnan(s):
            print(f'  {label:26s} 자료 부족 (증가 {nu} · 감소 {nd})')
            continue
        ok = (s > 0) if expect == '> 0' else (s < 0)
        hit += ok
        print(f'  {label:26s} 예측 {expect:4s} / 실제 {s:+.4f} '
              f'(증가 {nu} · 감소 {nd})  {"맞음" if ok else "틀림"}')
    print(f'  → {hit}/{len(PRESPECIFIED)} 맞음')

    print('\n[3/3] 중재별 점수 (참고 — 여기서 골라 주장하지 않는다)')
    print(t.to_string(index=False))
    print(f'\n  저장: out/diet_intervention_score.csv (중재 {len(t)})')
    print('  주의: compound_microbe 는 분해/생산을 구분하지 않는다. 음수가')
    print('  나와도 "가정이 틀렸다" 가 아니라 "이 자료로는 못 본다" 일 수 있다.')
    return t


def map_foods():
    """중재 표기를 우리 음식·compound 에 붙여 **KG 간선으로 쓸 수 있는 양**을 센다.

    위 검정은 미생물만 쓰므로 이 매칭이 필요 없다. 이쪽은 다른 목적이다 —
    `food -> microbe` 간선을 KG 에 넣으려면 중재 표기가 FDC 음식이어야 한다.
    """
    from common import normkey
    iv = gutmdisorder_intervention()
    terms = sorted(set(iv.intervention))
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    fk = {}
    for _, r in foods.iterrows():
        fk.setdefault(normkey(str(r['food_name'])), r['food_key'])
    nm = pd.read_csv(os.path.join(BASE, 'setup', 'nutrient_kegg_map.csv'))
    ck = {normkey(str(r['nutrient_name'])): r['nutrient_kegg']
          for _, r in nm.iterrows()}
    rows = []
    for t in terms:
        k = normkey(t)
        rows.append({'intervention': t, 'food_key': fk.get(k, ''),
                     'kegg': ck.get(k, ''),
                     'n_row': int((iv.intervention == t).sum())})
    m = pd.DataFrame(rows)
    # 정확 일치가 0 인 이유를 가린다. FDC 라벨은 `Fish, salmon, Atlantic,
    # farmed, raw` 꼴의 복합 서술어라 `Salmon` 같은 한 단어와 안 맞는다.
    # **후보가 있는지**를 부분 일치로 세어 "없다" 와 "이름이 다르다" 를 구분한다.
    names = foods.food_name.astype(str).str.lower()
    for i, r in m.iterrows():
        w = str(r['intervention']).lower().strip()
        if len(w) < 4 or r['food_key']:
            continue
        hit = names[names.str.contains(re.escape(w), regex=True)]
        m.loc[i, 'substr_n'] = len(hit)
        m.loc[i, 'substr_example'] = hit.iloc[0] if len(hit) else ''
    m['substr_n'] = m['substr_n'].fillna(0).astype(int)
    m.to_csv(os.path.join(OUT, 'diet_intervention_map.csv'), index=False)
    print(f'중재 표기 {len(m)}')
    print(f'  FDC 음식 이름과 **정확** 일치 {int((m.food_key != "").sum())}')
    print(f'  F 층 compound 이름과 정확 일치 {int((m.kegg != "").sum())}')
    cand = m[m.substr_n > 0].sort_values('n_row', ascending=False)
    print(f'  부분 일치 후보가 있는 표기 {len(cand)} (큐레이션하면 붙을 수 있다)')
    for _, r in cand.iterrows():
        print(f"    {r['intervention'][:38]:40s} 행 {r['n_row']:3d}"
              f" / FDC 후보 {r['substr_n']:5d}  예: {r['substr_example'][:44]}")
    print('  저장: out/diet_intervention_map.csv')
    return m


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'map':
        map_foods()
    else:
        test()
