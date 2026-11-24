"""설정 쓸기 — 한 자리에서 잰다.

    python3 ourkg/sweep.py                 # 전부
    python3 ourkg/sweep.py gutbrain        # 하나만
    WHO=mental,rct python3 ourkg/sweep.py gutbrain

쓸기가 셋으로 갈려 있었다(`sweep_fcolumns` · `sweep_gutbrain` ·
`sweep_modimed_rho`). 셋 다 **같은 골격**이었다 — 설정을 환경변수로 바꿔
`recommend` 를 돌리고, 두 기준으로 채점해 CSV 로 쓴다. 다른 것은 **무엇을
바꾸느냐** 뿐이라 그것만 표로 두고 골격을 합쳤다.

채점은 항상 둘을 같이 낸다. AUC 가 가장 높은 설정의 Top 30 이 처방 0 /
extras 19(1 위가 증류주)인 경우가 있었다(RESULTS §13). **Top-K 가 주지표다.**

**Top-K 안에서는 `비추천군`·`위반` 이 주지표다** (RESULTS §17). 음식을 5% 만
빼도 `추천군` 은 21 -> 6 까지 흔들리는데(폭 16) `비추천군` 은 [25, 27](폭 2)
이다. 추천군 차이가 **5 이하면 잡음 구간**이라 그것만으로 채택·기각하지 않는다.
그래서 표의 열 순서도 비추천군을 앞에 둔다.
"""
import importlib
import os
import sys
import warnings

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd  # noqa: E402
from common import OUT  # noqa: E402

REC = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
       'Vegetables and Vegetable Products'}
NOT = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
       'Beef Products', 'Pork Products'}

# 이름: (출력 파일, [(라벨, {환경변수}), ...]).  RESULTS 의 해당 절을 함께 적는다.
def _gutbrain():
    out = []
    for spec in os.environ.get('WHO', 'mental,mental/kegg,mental/measured,rct').split(','):
        who, _, src = spec.partition('/')
        for a in (0, 0.5, 1, 2, 4, 8):
            out.append((f'{spec} a={a}', {'GUTBRAIN_ALPHA': str(a),
                                          'GUTBRAIN_MICROBES': who,
                                          'GUTBRAIN_SOURCE': src or 'both'}))
    return out


def _simthr():
    """S 희소화. 두 가지를 같이 본다 — Top-K 가 나아지는가, 그리고 **미생물
    가중이 살아나는가**(ALPHA=0 vs 2 의 차이가 커지는가). RESULTS §15b 의
    "S 가 99.3% 꽉 차 있어 D 의 변조가 평균에 묻힌다" 를 검증하는 자리다."""
    out = []
    for thr in ('none', 'positive', 'q50', 'q90', 'topn:1000', 'topn:100', 'topn:30'):
        for a in (0, 2):
            out.append((f'{thr} a={a}', {'SIM_THRESHOLD': thr,
                                         'GUTBRAIN_ALPHA': str(a),
                                         'GUTBRAIN_MICROBES': 'mental'}))
    return out


SWEEPS = {
    # §21 — 지도학습 점수를 직접 쓰면. E 를 거치는 경로와 비교.
    'learned': ('learned_comparison.csv',
                [(lab, {'E_MODE': em, 'NO_SIM': ns, 'SIM_SPACE': 'composition',
                        'SIM_SIGN': 'none', 'SIM_THRESHOLD': 'none',
                        'GUTBRAIN_ALPHA': '0', 'E_ZERO': '', 'DEDUP': 'none',
                        'F_SCALE': 'per100g'})
                 for lab, em, ns in (('현행 shrunk x S', 'shrunk', '0'),
                                     ('learned x S', 'learned', '0'),
                                     ('learned 단독(=지도학습 점수)', 'learned', '1'),
                                     ('shrunk 단독', 'shrunk', '1'))]),
    # §21b — learned x S 에서 중복 변종을 묶으면 위반이 줄어드나.
    'learned_dedup': ('learned_dedup_comparison.csv',
                      [(f'{em}/{dd}', {'E_MODE': em, 'DEDUP': dd, 'NO_SIM': '0',
                                       'SIM_SPACE': 'composition', 'SIM_SIGN': 'none',
                                       'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0',
                                       'E_ZERO': '', 'F_SCALE': 'per100g'})
                       for em in ('shrunk', 'learned')
                       for dd in ('none', 'composition', 'name2')]),
    # §19 — 중복 변종을 묶으면. 두 기준 x 두 E 모드.
    'dedup': ('dedup_comparison.csv',
              [(f'{dd}/{em}', {'DEDUP': dd, 'E_MODE': em, 'SIM_SPACE': 'composition',
                               'NO_SIM': '0', 'SIM_SIGN': 'none',
                               'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0',
                               'E_ZERO': '', 'F_SCALE': 'per100g'})
               for dd in ('none', 'composition', 'name2')
               for em in ('shrunk',)]),
    # §17e — 나쁜 음식의 기여를 0 이하로 묶으면. E 모드 x 유사도 공간과 교차.
    'simsign': ('simsign_comparison.csv',
                [(f'{sg}/{sp}/{em}', {'SIM_SIGN': sg, 'SIM_SPACE': sp, 'E_MODE': em,
                                      'NO_SIM': '0', 'SIM_THRESHOLD': 'none',
                                      'GUTBRAIN_ALPHA': '0', 'E_ZERO': '',
                                      'F_SCALE': 'per100g'})
                 for sg in ('none', 'clip')
                 for sp in ('composition', 'effect')
                 for em in ('shrunk', 'nhanes_all')]),
    # §17d — 유사도를 무엇으로 재나. 성분 구성 vs 우울증 프로파일.
    'simspace': ('simspace_comparison.csv',
                 [(f'{sp}/{em}', {'SIM_SPACE': sp, 'E_MODE': em, 'NO_SIM': '0',
                                  'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0',
                                  'E_ZERO': '', 'F_SCALE': 'per100g'})
                  for sp in ('composition', 'effect')
                  for em in ('shrunk', 'nhanes_all')]),
    # §17c — 유사도 단계를 빼면 어떤가. D 단독 vs D x S.
    'nosim': ('nosim_comparison.csv',
              [(f'{lab}/{em}', {'NO_SIM': ns, 'E_MODE': em, 'SIM_THRESHOLD': 'none',
                                'GUTBRAIN_ALPHA': '0', 'E_ZERO': '',
                                'F_SCALE': 'per100g'})
               for lab, ns in (('P=DxS', '0'), ('P=D', '1'))
               for em in ('shrunk', 'nhanes_all')]),
    # §17b — 음수 유사도 가중. "안 닮아서 좋다" 를 얼마나 인정할 것인가.
    'negw': ('negw_comparison.csv',
             [(f'neg:{w}', {'SIM_THRESHOLD': f'neg:{w}', 'E_MODE': 'shrunk',
                            'GUTBRAIN_ALPHA': '0', 'E_ZERO': '',
                            'F_SCALE': 'per100g'})
              for w in ('0', '0.25', '0.5', '0.75', '1')]),
    # §15b — 유사도 희소화. S 가 꽉 차 있어 D 의 변조가 묻히는지.
    'simthr': ('simthr_comparison.csv', None),
    # §13 — F 열 제한 x PCA. AUC 와 Top-K 가 어긋나는 것을 처음 본 자리다.
    'fcolumns': ('fcolumns_comparison.csv',
                 [(f'{c}+{p}', {'F_COLUMNS': c, 'PCA_COMPONENTS': p})
                  for c in ('linked', 'all') for p in ('0', '5', 'auto')]),
    # §13b — 빈도 가중 순위 상관이 Top-K 와 같은 방향인지.
    'modimed_rho': ('modimed_rho_comparison.csv',
                    [(lab, {'F_COLUMNS': c, 'PCA_COMPONENTS': p, 'GUTBRAIN_ALPHA': '0'})
                     for lab, c, p in (('기본', 'linked', '0'), ('all+0', 'all', '0'),
                                       ('linked+PCA', 'linked', 'auto'),
                                       ('all+auto(기각)', 'all', 'auto'))]),
    # §15b·§15c — 미생물 매개 가중. 균 집합 x 링크 출처 x 세기.
    'gutbrain': ('gutbrain_comparison.csv', None),
    # §15b 검정 ⑧ — 에탄올·설탕의 E 를 0 으로 두면 무엇이 바뀌나.
    'ezero': ('ezero_comparison.csv', None),
    # §15e — F 를 1 회 섭취량 기준으로. E 소스와 교차해서 본다.
    'fscale': ('fscale_comparison.csv',
               [(f'{sc}/{em}', {'F_SCALE': sc, 'E_MODE': em,
                                'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0'})
                for sc in ('per100g', 'serving')
                for em in ('shrunk', 'nhanes_all')]),
    # §16 — E 의 소스를 바꾼다. ProMENDA(농도) vs NHANES(섭취-결과).
    'emode': ('emode_comparison.csv',
              [(m, {'E_MODE': m, 'SIM_THRESHOLD': 'none', 'GUTBRAIN_ALPHA': '0',
                    'E_ZERO': ''})
               for m in ('shrunk', 'binary', 'nhanes', 'nhanes_all', 'learned')]),
}


def _ezero():
    """에탄올·설탕의 E 를 0 으로 두면 무엇이 바뀌나 (RESULTS §15b 검정 ⑧).

    유사도 평활화가 이 오류를 덮고 있다는 진단을 검증한다 — 덮고 있다면
    기본(`none`)에서는 거의 안 바뀌고 희소화(`topn:100`)에서는 크게 바뀐다.
    """
    Z = 'C00469,C00089'          # 에탄올 · 설탕
    out = []
    for thr in ('none', 'topn:100'):
        for z in ('', Z):
            out.append((f'{thr} {"E_ZERO" if z else "원본"}',
                        {'SIM_THRESHOLD': thr, 'E_ZERO': z, 'GUTBRAIN_ALPHA': '0'}))
    return out


def run(name):
    path, cfgs = SWEEPS[name]
    if cfgs is None:
        cfgs = {'gutbrain': _gutbrain, 'simthr': _simthr,
                'ezero': _ezero}[name]()
    rows = []
    for lab, env in cfgs:
        os.environ.update(env)
        import analyze
        importlib.reload(analyze)
        res = analyze.recommend(save=False)
        sc = analyze.modimed_score(res, 30)
        top, bot = res.head(30), res.tail(30)
        rows.append({
            '설정': lab,
            # 주지표 — 표집에 안정적이다 (§17).
            # `비추천군` 은 **논문 §4.2.3 의 군 목록**으로만 센다(소시지·제과·
            # 과자·소고기·돼지). 유지류·양고기는 논문 목록에 없어 안 세어지는데,
            # 그것이 바닥에 오는 설정에서는 과소평가된다 — 그래서 외부 기준인
            # `bot30_extras`(ModiMedDiet 가 제한하는 군)를 **나란히** 둔다.
            # 어느 쪽을 셀지 우리가 정하지 않기 위해서다.
            'bot30_비추천군': int(bot.food_group.isin(NOT).sum()),
            'bot30_extras(외부)': sc.get('bot30_extras'),
            'top30_위반': int(top.food_group.isin(NOT).sum()),
            # 참고 — 폭 16 으로 흔들린다. 차이 5 이하는 읽지 않는다
            'top30_추천군(참고)': int(top.food_group.isin(REC).sum()),
            'MMD_처방군': sc.get('top30_처방군'),
            'MMD_extras': sc.get('top30_extras'),
            'AUC(참고)': sc.get('modimed_AUC(참고)'),
            'rho_처방군': sc.get('modimed_rho_처방군만'),
            'rho_상위': sc.get(f"modimed_rho_상위{os.environ.get('MODIMED_RHO_TOP', '0')}"),
            'top1': str(top.iloc[0].food_name)[:38]})
    t = pd.DataFrame(rows).dropna(axis=1, how='all')
    t.to_csv(os.path.join(OUT, path), index=False)
    print(f'\n== {name}  ->  out/{path}')
    print(t.to_string(index=False))
    return t


if __name__ == '__main__':
    want = sys.argv[1:] or list(SWEEPS)
    bad = [w for w in want if w not in SWEEPS]
    if bad:
        sys.exit(f'알 수 없는 쓸기 {bad}. 가능: {list(SWEEPS)}')
    for n in want:
        run(n)

