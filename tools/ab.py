"""
설정 A/B 비교
===============
파이프라인 설정을 바꿔가며 논문 순위·gold 로 비교한다.
(구 ab_rules.py / ab_fallback.py / ab_menda_both.py / ab_merge.py 통합)

실행
    python3 tools/ab.py rules       ontology / literature 규칙 on-off
    python3 tools/ab.py fallback    미근거 compound 처리 전략
    python3 tools/ab.py menda_both  MENDA 양방향 기본값 +1 vs 0
    python3 tools/ab.py menda_tiebreak  MENDA_both 를 원본 카운트로 가를지
    python3 tools/ab.py study_type  ProMENDA Type2/4 방향 보정 on-off
    python3 tools/ab.py merge       라벨 병합 on-off  (reconstruct 부터 재실행)
    python3 tools/ab.py margin      ProMENDA 다수결 마진 (구 tune_margin.py)
    python3 tools/ab.py units       단위 환산 g vs 원단위 (reconstruct 부터 재실행)
    python3 tools/ab.py all

끝나면 기본 설정으로 파이프라인을 다시 돌려 analyse/ 를 원상태로 돌린다.

margin 은 gold(독립 기준)로 고른다. p5 순위나 카테고리로 고르면 순환 논증이다.

지표
    Spearman / Top30 / Bot30  논문 순위(p5) 대조. 정직한 지표.
    top30_rec / cat_rec       카테고리 지표. 상위30에 과일 1개만 있어도 만점이라
                              약하다. 과거 보고가 이 지표에 기대 과대평가되었다.
    gold                      논문이 부호를 명시한 9종 (독립 기준)
"""
import sys

import core

RECON = ('reconstruct.py', 'knowledge_query.py', 'map_promenda.py')

CASES = {
    'rules': [
        ('ontology O / literature O', dict(USE_ONTOLOGY=1, USE_LITERATURE=1)),
        ('ontology O / literature X', dict(USE_ONTOLOGY=1, USE_LITERATURE=0)),
        ('ontology X / literature O', dict(USE_ONTOLOGY=0, USE_LITERATURE=1)),
        ('ontology X / literature X', dict(USE_ONTOLOGY=0, USE_LITERATURE=0)),
    ],
    'fallback': [
        ('A literature',    dict(USE_LITERATURE=1, GROUP_PRIOR_MODE='none')),
        ('B group_full',    dict(USE_LITERATURE=0, GROUP_PRIOR_MODE='full')),
        ('C group_carbvit (현재)', dict(USE_LITERATURE=0, GROUP_PRIOR_MODE='carbvit')),
        ('D none',           dict(USE_LITERATURE=0, GROUP_PRIOR_MODE='none')),
    ],
    'menda_both': [
        ('+1 (구 동작)', dict(MENDA_BOTH_DEFAULT_POS=1)),
        ('0  (현재)',    dict(MENDA_BOTH_DEFAULT_POS=0)),
    ],
    'menda_tiebreak': [
        ('orig (현재)', dict(MENDA_BOTH_TIEBREAK='orig')),
        ('none (구 동작)', dict(MENDA_BOTH_TIEBREAK='none')),
    ],
    'study_type': [
        ('보정 OFF (현재)', dict(FIX_STUDY_TYPE=0)),
        ('보정 ON',          dict(FIX_STUDY_TYPE=1)),
    ],
    'merge': [
        ('병합 ON (현재)', dict(MERGE_LABELS=1)),
        ('병합 OFF',      dict(MERGE_LABELS=0)),
    ],
    'margin': [(f'margin={m:<4}' + (' (현재)' if m == 0.10 else ''),
                dict(PROMENDA_MARGIN=m))
               for m in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50)],
    'units': [
        ('g 환산 (현재)', dict(UNIT_MODE='grams')),
        ('원단위',        dict(UNIT_MODE='raw')),
    ],
}
RESTART_FROM_RECON = {'merge', 'units'}


def run(kind):
    steps = RECON if kind in RESTART_FROM_RECON else None
    print(f'=== {kind} ===')
    for label, env in CASES[kind]:
        core.run_steps(env, steps) if steps else core.run_steps(env)
        d = core.Data.load()
        m = core.metrics(d, d.score())
        extra = (f'top30_rec={m["top30_rec"]:2d}  '
                 f'cat={m["cat_rec"]},{m["cat_not"]}')
        print(f'  {core.fmt(m, label, 24)}  {extra}')
    print()


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    kinds = list(CASES) if which == 'all' else [which]
    for k in kinds:
        if k not in CASES:
            sys.exit(f'알 수 없는 항목: {k}\n가능: {", ".join(CASES)}, all')
        run(k)
    core.run_steps({}, RECON if RESTART_FROM_RECON & set(kinds) else
                   ('knowledge_query.py', 'map_promenda.py'))
    print('기본 설정으로 복원했다.')
    print(f'우연 기대값: Top30/Bot30 모두 약 '
          f'{core.metrics(core.Data.load(), core.Data.load().score())["chance"]:.1f}')
