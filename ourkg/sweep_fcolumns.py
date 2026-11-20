"""F 열 제한 × PCA 조합 비교표 (out/fcolumns_comparison.csv).

RESULTS §13 의 표를 만든 스크립트가 저장소에 없어 수치가 낡은 채로 인용되고
있었다. 재현 가능하게 여기 둔다. 두 기준을 같이 재는 것이 요점이다 —
AUC 가 가장 높은 설정의 Top 30 이 처방 0 / extras 19(1 위가 증류주)인 경우가
있었다(§13). Top-K 가 주지표다.
"""
import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import OUT  # noqa: E402

REC = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
       'Vegetables and Vegetable Products'}
NOT = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
       'Beef Products', 'Pork Products'}


def main():
    os.environ.setdefault('MODIMED_POSITIVES', 'high_freq')
    rows = []
    for fcol in ('linked', 'all'):
        for pca in ('0', '5', 'auto'):
            env = dict(os.environ, F_COLUMNS=fcol, PCA_COMPONENTS=pca)
            subprocess.run([sys.executable, '-W', 'ignore', 'analyze.py', 'recommend'],
                           cwd=HERE, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            import importlib
            import analyze as A
            importlib.reload(A)
            r = pd.read_csv(os.path.join(OUT, 'recommendation.csv'))
            m = A.modimed_score(r, 30)
            t, b = r.head(30), r.tail(30)
            rows.append({
                'F열': fcol, 'PCA': pca, '음식': len(r),
                'AUC': m['modimed_AUC(참고)'],
                '추천군': int(t.food_group.isin(REC).sum()),
                '비추천군': int(b.food_group.isin(NOT).sum()),
                '위반': int(t.food_group.isin(NOT).sum()),
                'MMD_top30_처방': m['top30_처방군'],
                'MMD_top30_extras': m['top30_extras'],
                'top': str(r.iloc[0].food_name)[:30]})
            print(rows[-1], flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(OUT, 'fcolumns_comparison.csv'), index=False)
    print('\n' + d.to_string(index=False))


if __name__ == '__main__':
    main()
