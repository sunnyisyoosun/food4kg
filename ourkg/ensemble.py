"""순위 앙상블 — E 를 벡터가 아니라 **순위**에서 합친다.

    python3 ourkg/ensemble.py                      # shrunk + nhanes_all
    ENS_MODES=shrunk,nhanes_all,learned python3 ourkg/ensemble.py

왜 — §22 에서 두 `E` 를 **한 벡터에** 합쳤더니(`union`) 커버리지는 늘었지만
비추천군 sd 가 1.96 -> 6.91 로 3.6 배가 됐다. 진단은 **이질성**이었다:
ProMENDA 는 "환자에서 이 대사물의 **농도**가 높/낮다", NHANES 는 "이것을
**먹으면** PHQ-9 가 높/낮다" 를 잰다. 의미가 다른 값을 한 벡터에 넣은 것이다.

여기서는 **섞지 않는다.** 각 `E` 로 끝까지 점수를 낸 뒤 **순위 평균**을 낸다.
스케일도 의미도 다른 두 값을 직접 더하지 않으므로 그 이질성이 사라진다.

    P_final(food) = mean( rank_shrunk(food), rank_nhanes(food), ... )

`union_all` 과 비교하는 것이 요점이다 — 같은 두 소스를 **벡터에서** 합친 것과
**순위에서** 합친 것 중 어느 쪽이 나은가.
"""
import contextlib
import importlib
import io as _io
import os
import sys
import warnings

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from common import OUT  # noqa: E402

REC = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
       'Vegetables and Vegetable Products'}
NOT = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
       'Beef Products', 'Pork Products'}


def score(e_mode, env=None):
    """한 E 로 끝까지 돌린 점수. index = food_key."""
    os.environ.update({'SIM_SPACE': 'composition', 'SIM_SIGN': 'none',
                       'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0',
                       'E_ZERO': '', 'DEDUP': 'none', 'F_SCALE': 'per100g',
                       'NO_SIM': '0', 'E_MODE': e_mode})
    if env:
        os.environ.update(env)
    import analyze
    importlib.reload(analyze)
    with contextlib.redirect_stdout(_io.StringIO()):
        r = analyze.recommend(save=False)
    return r.set_index('food_key')


def ensemble(modes, env=None, K=30, save=True):
    parts, meta = {}, None
    for m in modes:
        r = score(m, env)
        # 순위는 **백분위**로 둔다 — 코호트 크기가 달라도 비교 가능하다
        parts[m] = r['score'].rank(pct=True)
        meta = r[['food_name', 'food_group']] if meta is None else meta
    R = pd.DataFrame(parts).dropna()
    out = meta.loc[R.index].copy()
    out['score'] = R.mean(axis=1)
    for m in modes:
        out[f'pct_{m}'] = R[m]
    out = out.sort_values('score', ascending=False)
    out.insert(0, 'rank', range(1, len(out) + 1))
    if save:
        out.to_csv(os.path.join(OUT, 'ensemble_recommendation.csv'), index=True)
    t, b = out.head(K), out.tail(K)
    # 두 소스가 얼마나 다른 말을 하는지 — 순위 상관
    rho = R.corr(method='spearman').values[0, 1] if len(modes) == 2 else float('nan')
    return {'설정': '+'.join(modes), 'n': len(out),
            '추천군': int(t.food_group.isin(REC).sum()),
            '비추천군': int(b.food_group.isin(NOT).sum()),
            '위반': int(t.food_group.isin(NOT).sum()),
            '두 순위의 rho': round(float(rho), 3),
            '1위': str(t.iloc[0].food_name)[:44]}, out


if __name__ == '__main__':
    modes = os.environ.get('ENS_MODES', 'shrunk,nhanes_all').split(',')
    rows = []
    # 비교군: 단일 E 들과 벡터 합치기(union_all)
    for m in modes:
        r = score(m)
        t, b = r.head(30), r.tail(30)
        rows.append({'설정': m, 'n': len(r),
                     '추천군': int(t.food_group.isin(REC).sum()),
                     '비추천군': int(b.food_group.isin(NOT).sum()),
                     '위반': int(t.food_group.isin(NOT).sum()),
                     '두 순위의 rho': float('nan'),
                     '1위': str(t.iloc[0].food_name)[:44]})
    r = score('union_all')
    t, b = r.head(30), r.tail(30)
    rows.append({'설정': 'union_all (벡터 합치기)', 'n': len(r),
                 '추천군': int(t.food_group.isin(REC).sum()),
                 '비추천군': int(b.food_group.isin(NOT).sum()),
                 '위반': int(t.food_group.isin(NOT).sum()),
                 '두 순위의 rho': float('nan'),
                 '1위': str(t.iloc[0].food_name)[:44]})
    row, _ = ensemble(modes)
    row['설정'] = '앙상블 (순위 합치기)'
    rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(OUT, 'ensemble_comparison.csv'), index=False)
    print(tab.to_string(index=False))


def boot(modes, R=60, frac=0.8, K=30):
    """앙상블의 표집 변동. §22 가 기각한 `union_all` 의 sd 6.91 과 비교한다."""
    rows = []
    for seed in range(R):
        env = {'BOOT_FRAC': str(frac), 'BOOT_SEED': str(seed)}
        r, _ = ensemble(modes, env=env, K=K, save=False)
        rows.append(r)
    d = pd.DataFrame(rows)
    out = {'설정': '앙상블 ' + '+'.join(modes), 'R': R}
    for k in ('추천군', '비추천군', '위반'):
        lo, hi = np.percentile(d[k], [2.5, 97.5])
        out[k] = f'[{lo:.0f}, {hi:.0f}]'
        out[k + '_sd'] = round(float(d[k].std()), 2)
    return out
