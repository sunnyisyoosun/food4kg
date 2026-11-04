"""ourkg 파이프라인 일괄 실행.

    python3 ourkg/run_all.py            # 01 → 06
    python3 ourkg/run_all.py 05 06      # 지정 단계만

환경변수는 각 단계 파일 주석 참조 (MIN_COV, E_MODE, NORM, SIM_NORM, DATA_TYPES, PART).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ['01_food.py', '02_promenda.py', '03_microbe.py',
         '04_kg.py', '05_recommend.py', '06_eval.py']

want = sys.argv[1:]
for s in STEPS:
    if want and not any(s.startswith(w) for w in want):
        continue
    print(f'\n{"=" * 70}\n== {s}\n{"=" * 70}')
    r = subprocess.run([sys.executable, os.path.join(HERE, s)])
    if r.returncode:
        sys.exit(f'{s} 실패 (exit {r.returncode})')
print('\n완료. 산출물: ourkg/out/')
