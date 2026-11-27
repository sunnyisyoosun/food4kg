"""합의 Top-K — 코호트가 흔들려도 상위에 남는 음식만 고른다.

    python3 ourkg/consensus.py                 # 기본 설정
    CONS_R=200 python3 ourkg/consensus.py current learned-name2

§17 이 Top-K 지표의 **표집 변동**을 보였다 — 음식을 5% 만 빼도 추천군이
21 에서 6 까지 떨어진다. 지금까지는 그것을 **없애려** 했고(중복 병합 §19,
E 소스 교체 §15d·§20, 합치기 §22) 전부 실패했다.

여기서는 **이용한다.** 부분표집을 R 번 돌려 **매번 Top-K 에 드는 비율**로
음식을 세운다. 결과가 구성상 안정적이고, "이 음식은 코호트가 바뀌어도 상위"
라는 더 강한 주장이 된다.

    선택도(food) = Top-K 에 들어간 부분표집의 비율
    합의 Top-K   = 선택도 상위 K 개

논문 Algorithm 1 을 바꾸지 않는다 — 같은 점수를 **여러 번 재서 고르는** 층을
위에 얹을 뿐이다. 그래서 어떤 `E`·유사도 설정과도 같이 쓴다.
"""
import collections
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
from common import outp, OUT, recommend_under, enable_provenance  # noqa: E402

enable_provenance()   # 산출물 출처 기록 (common.PROV)
from bootstrap import BASE, CANDIDATES, REC, NOT  # noqa: E402


def consensus(env, R=100, frac=0.8, K=30):
    """선택도 표. 각 음식이 Top-K / Bottom-K 에 든 비율."""
    top, bot, seen = collections.Counter(), collections.Counter(), collections.Counter()
    meta = {}
    for seed in range(R):
        res, _ = recommend_under(env, boot=(frac, seed))
        seen.update(res['food_key'])
        top.update(res.head(K)['food_key'])
        bot.update(res.tail(K)['food_key'])
        for _, r in pd.concat([res.head(K), res.tail(K)]).iterrows():
            meta[r['food_key']] = (r['food_name'], r['food_group'])
    rows = [{'food_key': k, 'food_name': meta[k][0], 'food_group': meta[k][1],
             'top_rate': top[k] / max(seen[k], 1), 'bot_rate': bot[k] / max(seen[k], 1),
             'n_seen': seen[k]}
            for k in set(top) | set(bot)]
    return pd.DataFrame(rows)


def run(names, R=None, K=30):
    R = R or int(os.environ.get('CONS_R', '100'))
    out = []
    for name in names:
        t = consensus({**BASE, **CANDIDATES[name]}, R=R, K=K)
        t['설정'] = name
        # 합의 Top-K / Bottom-K — 선택도 순
        ctop = t.nlargest(K, 'top_rate')
        cbot = t.nlargest(K, 'bot_rate')
        row = {'설정': name, 'R': R,
               '합의_추천군': int(ctop.food_group.isin(REC).sum()),
               '합의_비추천군': int(cbot.food_group.isin(NOT).sum()),
               '합의_위반': int(ctop.food_group.isin(NOT).sum()),
               'top_rate 중앙값': round(float(ctop.top_rate.median()), 3),
               '1위': str(ctop.iloc[0].food_name)[:40]}
        out.append(row)
        print(f"  {name:14s} 추천군 {row['합의_추천군']:2d} · 비추천군 "
              f"{row['합의_비추천군']:2d} · 위반 {row['합의_위반']:2d} · "
              f"선택도중앙 {row['top_rate 중앙값']:.2f} · 1위 {row['1위']}", flush=True)
        t.sort_values('top_rate', ascending=False).to_csv(
            outp(f'consensus_{name}.csv'), index=False)
    r = pd.DataFrame(out)
    r.to_csv(outp('consensus_summary.csv'), index=False)
    print(f'\n  -> out/consensus_summary.csv · out/consensus_<설정>.csv')
    return r


if __name__ == '__main__':
    run(sys.argv[1:] or ['current'])
