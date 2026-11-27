"""Top-K 의 **명백한 오류**를 센다 -> out/toperr_comparison.csv

    python3 ourkg/toperr.py            # 후보 전부
    python3 ourkg/toperr.py current

왜 — §24·§25 에서 기본값을 두 번 바꿨는데 **둘 다 수치가 아니라 목록을 보고**
정했다("캐러멜 딥이 상위에 있는 건 오류"). 이 프로젝트의 다른 결정은 전부
수치가 갈랐는데 기본값만 다른 기준이었다(§27).

그 판단을 **규칙으로 적는다.** 그러면 재현 가능하고, 내가 틀렸는지도 검증된다.

**규칙은 외부 기준에서 가져온다 — 내가 고른 음식 목록이 아니다.**

  1  ModiMedDiet extras        임상 기준이 "주 3 회 이하로 제한" 하는 군
                               (튀김·패스트푸드·가공육·과자·가당음료·주류·정제곡물)
  2  1 회 섭취량 < 5 g          FDC food_portion. 말린 향신료가 여기 걸린다 —
                               100 g 당 농도로 추천되지만 실제로 그만큼 안 먹는다
  3  보충제·분말                음식이 아니다. powder/mix/isolate/shake/supplement
  4  시럽 가공                  heavy/light syrup — 첨가당이 들어간 통조림

**이 규칙은 실패를 본 뒤에 쓴 것이다.** 현재 기본값에 유리하게 고르지 않으려고
① 은 외부 임상 기준 그대로, ② 는 FDC 측정값, ③④ 는 이름 규칙으로 두고,
**이미 기각한 설정까지 전부** 같은 자로 잰다.
"""
import os
import re
import sys
import warnings

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd  # noqa: E402
from common import (outp, BASE, CACHE, OUT, recommend_under,  # noqa: E402
                    enable_provenance)

enable_provenance()   # 산출물 출처 기록 (common.PROV)

POWDER = r'powder|\bmix\b|isolate|shake|supplement|instant breakfast|formula'
SYRUP = r'heavy syrup|light syrup|in syrup|syrup pack'
SERVING_MIN = 5.0          # g


def _serving():
    d = os.path.join(CACHE, 'fdc_portion')
    files = [os.path.join(d, f) for f in ('survey.csv', 'sr_legacy.csv')
             if os.path.exists(os.path.join(d, f))]
    if not files:
        return {}
    fp = pd.concat([pd.read_csv(f, dtype=str) for f in files])
    fp['g'] = pd.to_numeric(fp.gram_weight, errors='coerce')
    return fp[fp.g > 0].groupby('fdc_id').g.median().to_dict()


def flag(res, K=30):
    """Top-K 각 행에 어떤 규칙이 걸리는지. 반환: (표, 규칙별 개수)"""
    import analyze
    t = res.head(K).copy()
    lab, _ = analyze.modimed_labels(t)
    serv = _serving()
    t['extras'] = (lab.values == -1)
    t['small_serving'] = [
        (serv.get(str(f)) is not None and serv[str(f)] < SERVING_MIN)
        for f in (t['fdc_id'] if 'fdc_id' in t else [None] * len(t))]
    name = t['food_name'].astype(str)
    t['powder'] = name.str.contains(POWDER, case=False, regex=True)
    t['syrup'] = name.str.contains(SYRUP, case=False, regex=True)
    cols = ['extras', 'small_serving', 'powder', 'syrup']
    t['오류'] = t[cols].any(axis=1)
    return t, {c: int(t[c].sum()) for c in cols} | {'total_dedup': int(t['오류'].sum())}


if __name__ == '__main__':
    import importlib
    from bootstrap import BASE as B, CANDIDATES
    want = sys.argv[1:] or ['current', 'union_all', 'ensemble', 'learned-name2',
                            'effect+nhanes']
    rows = []
    for name in want:
        env = dict(B)
        if name == 'ensemble':
            env['ENSEMBLE'] = 'shrunk,nhanes_all'
        else:
            env['ENSEMBLE'] = 'none'
            env.update(CANDIDATES.get(name, {'E_MODE': name}))
        res, _ = recommend_under(env)
        if 'fdc_id' not in res:
            foods = pd.read_csv(outp('foods.csv'))
            res = res.merge(foods[['food_key', 'fdc_id']], on='food_key', how='left')
        _, n = flag(res)
        n['config'] = name
        n['Top1'] = str(res.iloc[0].food_name)[:34]
        rows.append(n)
        print(f"  {name:14s} 오류 {n['total_dedup']:2d}/30  "
              f"(extras {n['extras']} · 섭취량 {n['small_serving']} · "
              f"분말 {n['powder']} · 시럽 {n['syrup']})  {n['Top1']}", flush=True)
    pd.DataFrame(rows).to_csv(outp('toperr_comparison.csv'), index=False)
    print('\n  -> out/toperr_comparison.csv')
