"""ourkg 파이프라인 일괄 실행.

    python3 ourkg/run_all.py                  # 구축 -> 분석 -> 검정
    python3 ourkg/run_all.py kg recommend     # 지정 단계만
    python3 ourkg/run_all.py --env            # 환경변수 전수 (소스에서 긁는다)

단계가 코드에 흩어져 있었다 — `groups`(Fig 4(c))가 여기 안 들어 있었고,
외부 검정 둘과 쓸기 셋은 아예 밖에 있어 따로 돌려야 했다. 전부 등록한다.
각 파일을 직접 돌려도 같다.

**`.venv` 를 켜야 한다** (루트 README 의 설치 절 참조):

    source .venv/bin/activate
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

BUILD = ['food', 'form', 'promenda', 'evidence', 'microbe', 'kg']
ANALYZE = ['recommend', 'compare', 'external', 'invert', 'stype',
           'pathcheck', 'groups', 'evaluate']
# 외부 자로 재는 단계. 네트워크를 쓰고 캐시가 비면 오래 걸린다.
VERIFY = {'probiotic': ('probiotic_rct.py', ['test']),     # RESULTS §15b 검정 ①②
          'metabolome': ('metabolome_check.py', []),        # RESULTS §15b 검정 ④
          'nhanes': ('nhanes.py', []),                      # RESULTS §15d
          'diet_iv': ('diet_intervention.py', []),          # RESULTS §33 (중재로 E 검정)
          'e_autism': ('e_autism.py', []),                  # RESULTS §34 (검정력 반론)
          'bootstrap': ('bootstrap.py', []),                # RESULTS §17 (주지표 근거)
          'consensus': ('consensus.py', [])}                # RESULTS §23 (합의 Top-K)
# 설정 쓸기. 하나하나가 recommend 를 여러 번 돌린다.
SWEEP = {'sweep': ('sweep.py', [])}
STEPS = BUILD + ANALYZE + list(VERIFY) + list(SWEEP)


def envs():
    """환경변수를 **소스에서 긁어** 보여준다. 손으로 적은 목록은 낡는다."""
    found = {}
    for fn in sorted(f for f in os.listdir(HERE) if f.endswith('.py')):
        src = open(os.path.join(HERE, fn), encoding='utf-8').read()
        for m in re.finditer(r"environ\.get\('([A-Z_]+)'(?:,\s*'([^']*)')?", src):
            found.setdefault(m.group(1), (fn, m.group(2)))
    print(f'환경변수 {len(found)} — 기본값은 해당 함수의 docstring·주석 참조\n')
    for k, (fn, d) in sorted(found.items()):
        print(f'  {k:22s} {("= " + d) if d is not None else "":16s} {fn}')


def main(argv):
    if '--env' in argv:
        return envs()
    want = argv or STEPS
    unknown = [w for w in want if w not in STEPS]
    if unknown:
        sys.exit(f'알 수 없는 단계 {unknown}. 가능: {STEPS}')

    plan = [('build.py', [s for s in BUILD if not argv or s in want]),
            ('analyze.py', [s for s in ANALYZE if not argv or s in want])]
    plan += [(f, a) for k, (f, a) in {**VERIFY, **SWEEP}.items()
             if not argv or k in want]

    for script, steps in plan:
        if not steps and script in ('build.py', 'analyze.py'):
            continue
        r = subprocess.run([sys.executable, os.path.join(HERE, script), *steps])
        if r.returncode:
            sys.exit(f'{script} {steps} 실패 (exit {r.returncode})')
    print('\n완료. 산출물: ourkg/out/')


if __name__ == '__main__':
    main(sys.argv[1:])
