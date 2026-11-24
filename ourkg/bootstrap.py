"""Top-K 지표의 **표집 변동**을 잰다 -> out/bootstrap_ci.csv

    python3 ourkg/bootstrap.py                 # 기본 설정
    BOOT_R=200 python3 ourkg/bootstrap.py shrunk nhanes_all

왜 필요한가 — RESULTS 의 채택·기각이 대부분 "추천군 21 vs 19" 같은 **차이 2~5**
위에 서 있는데, 그 차이가 잡음인지 잰 적이 없다. Top 30 은 칸이 30 개뿐이라
음식 몇 개만 바뀌어도 쉽게 흔들린다.

**비복원 부분표집**(기본 80%)을 R 번 반복해 지표의 분포를 본다. 복원추출은
같은 음식이 여러 번 뽑혀 Top-K 칸을 중복 점유하므로 순위 문제에서 지표가
부풀려진다.

구간이 겹치면 "차이 없음" 으로 읽어야 한다 — 기존 기각 기록이 그 자로 다시
읽혀야 하는 것이 이 작업의 요점이다.
"""
import importlib
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


def one(env, seed, frac):
    os.environ.update(env)
    os.environ['BOOT_FRAC'], os.environ['BOOT_SEED'] = str(frac), str(seed)
    import analyze
    importlib.reload(analyze)
    import contextlib, io as _io
    with contextlib.redirect_stdout(_io.StringIO()):       # 반복이 많아 조용히
        res = analyze.recommend(save=False)
    t, b = res.head(30), res.tail(30)
    return {'추천군': int(t.food_group.isin(REC).sum()),
            '비추천군': int(b.food_group.isin(NOT).sum()),
            '위반': int(t.food_group.isin(NOT).sum())}


def run(configs, R=None, frac=None):
    R = R or int(os.environ.get('BOOT_R', '200'))
    frac = frac or float(os.environ.get('BOOT_FRAC_SIZE', '0.8'))
    rows = []
    for lab, env in configs:
        vals = [one(env, s, frac) for s in range(R)]
        d = pd.DataFrame(vals)
        full = one(env, 0, 0)          # 전체 코호트 (부분표집 없음)
        r = {'설정': lab, 'R': R, 'frac': frac}
        for k in ('추천군', '비추천군', '위반'):
            lo, hi = np.percentile(d[k], [2.5, 97.5])
            r[k] = f'{full[k]} [{lo:.0f}, {hi:.0f}]'
            r[k + '_sd'] = round(float(d[k].std()), 2)
        rows.append(r)
        print(f'  {lab:18s} ' + '  '.join(f'{k} {r[k]}' for k in
                                          ('추천군', '비추천군', '위반')), flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, 'bootstrap_ci.csv'), index=False)
    print(f'\n  -> out/bootstrap_ci.csv  (값 = 전체 코호트 [95% 구간])')
    return t


# 이름 붙인 후보 — 기본값을 바꿀지 판단할 때 쓴다 (RESULTS §17f)
BASE = {'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0', 'E_ZERO': '',
        'F_SCALE': 'per100g', 'F_COLUMNS': 'linked', 'PCA_COMPONENTS': '0',
        'NO_SIM': '0', 'SIM_SIGN': 'none', 'DEDUP': 'none'}
CANDIDATES = {
    '현행': {'E_MODE': 'shrunk', 'SIM_SPACE': 'composition'},
    'effect+nhanes': {'E_MODE': 'nhanes_all', 'SIM_SPACE': 'effect'},
    'effect+shrunk': {'E_MODE': 'shrunk', 'SIM_SPACE': 'effect'},
    'comp+nhanes': {'E_MODE': 'nhanes_all', 'SIM_SPACE': 'composition'},
    'dedup-comp': {'E_MODE': 'shrunk', 'SIM_SPACE': 'composition',
                   'DEDUP': 'composition'},
    'dedup-name2': {'E_MODE': 'shrunk', 'SIM_SPACE': 'composition',
                    'DEDUP': 'name2'},
    'learned-name2': {'E_MODE': 'learned', 'SIM_SPACE': 'composition',
                      'DEDUP': 'name2'},
    'union': {'E_MODE': 'union', 'SIM_SPACE': 'composition'},
    'union_all': {'E_MODE': 'union_all', 'SIM_SPACE': 'composition'},
}


if __name__ == '__main__':
    want = sys.argv[1:] or list(CANDIDATES)
    bad = [w for w in want if w not in CANDIDATES]
    if bad:
        sys.exit(f'알 수 없는 후보 {bad}. 가능: {list(CANDIDATES)}')
    run([(w, {**BASE, **CANDIDATES[w]}) for w in want])
