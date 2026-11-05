"""ourkg 파이프라인 일괄 실행.

    python3 ourkg/run_all.py                  # 구축 4단계 → 분석 2단계
    python3 ourkg/run_all.py kg recommend     # 지정 단계만

단계 이름은 build.py 의 food/promenda/microbe/kg,
analyze.py 의 recommend/evaluate 다. 각 파일을 직접 돌려도 같다.

환경변수: MIN_COV, E_MODE, SHRINK_K, SOURCE_WEIGHTS, PRIORITY, NORM,
          SIM_NORM, DATA_TYPES, TOP_K, E_MODES, PART
          — 해당 함수의 docstring·주석 참조.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = ['food', 'promenda', 'evidence', 'microbe', 'kg']
ANALYZE = ['recommend', 'compare', 'evaluate']

want = sys.argv[1:]
plan = [('build.py', [s for s in BUILD if not want or s in want]),
        ('analyze.py', [s for s in ANALYZE if not want or s in want])]

unknown = [w for w in want if w not in BUILD + ANALYZE]
if unknown:
    sys.exit(f'알 수 없는 단계 {unknown}. 가능: {BUILD + ANALYZE}')

for script, steps in plan:
    if not steps:
        continue
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *steps])
    if r.returncode:
        sys.exit(f'{script} {steps} 실패 (exit {r.returncode})')
print('\n완료. 산출물: ourkg/out/')
