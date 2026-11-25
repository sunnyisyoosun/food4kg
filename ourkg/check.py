"""산출물과 문서가 서로 맞는지 **네트워크 없이 빠르게** 검사한다.

왜 이게 필요한가
----------------
테스트가 하나도 없는 상태에서 환경변수 55 개와 800 줄 함수를 다루고 있었다.
그 조합에서 실제로 난 버그들의 공통점은 **실패해도 출력이 그럴듯하다**는 것이고,
그래서 전부 우연히 발견됐다.

  · `SWEEPS['ezero']` 를 `if __name__` **뒤**에 등록해 한 번도 안 돌았다
  · `union` 분기가 `nhanes` 안에 중첩돼 조용히 `shrunk` 로 떨어졌다
  · `basis()` 가 점수와 **다른 E** 를 근거로 보여줬다
  · 병합된 NCBI taxid 를 들고 있는 균 12 종이 축에서 조용히 빠졌다
  · 문서 수치가 산출물과 갈렸다 (`F 층 130` vs 135, `798` vs `791`)

그래서 **그 종류를 겨냥한** 불변식만 검사한다. 통계적 결론(신호 유무)은 검사
대상이 아니다 — 그건 실험이고 `RESULTS.md` 가 기록한다.

쓰는 법
-------
    python3 ourkg/check.py            # 전부
    python3 ourkg/check.py kg docs    # 일부만
    python3 ourkg/check.py --list
실패가 하나라도 있으면 **exit 1** 이다. `run_all.py` 의 `check` 단계.
`.nt` 가 없거나 일부 산출물이 없으면 그 검사는 SKIP 으로 남기고 실패로 세지
않는다 — 단계별로 돌릴 수 있어야 하기 때문이다.
"""
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import OUT, BASE, taxid_alias, canon          # noqa: E402

RESULT = []            # (상태, 이름, 메시지)


def _say(state, name, msg):
    RESULT.append((state, name, msg))
    mark = {'PASS': 'ok  ', 'FAIL': 'FAIL', 'SKIP': '--  '}[state]
    print(f'  {mark} {name:34s} {msg}')


def _need(*names):
    """산출물이 다 있으면 DataFrame 들을, 하나라도 없으면 None 을 돌려준다."""
    out = []
    for n in names:
        p = os.path.join(OUT, n)
        if not os.path.exists(p):
            return None, n
        out.append(p)
    return out, None


# ---------------------------------------------------------------- 1. 스키마
# 단계를 따로 돌리다가 열 이름을 바꾸면 **읽는 쪽이 조용히 빈 값을 본다.**
# 아래 열은 다른 모듈이 이름으로 집어 쓰는 것들이다.
SCHEMA = {
    'foods.csv': ['food_key', 'food_name', 'data_type', 'n_compound'],
    'compound_depression.csv': ['kegg', 'e_shrunk', 'e_binary', 'q'],
    'microbes.csv': ['taxid', 'name', 'rank', 'kegg_org', 'match_rank',
                     'taxid_current'],
    'compound_microbe.csv': ['kegg', 'taxid', 'taxid_current', 'match_rank'],
    'microbe_disease_disbiome.csv': ['taxid', 'mesh_id', 'outcome',
                                     'is_mental', 'is_neuro'],
    'microbe_disease_gutmdisorder.csv': ['taxid', 'mesh_id', 'outcome',
                                         'is_mental', 'is_neuro'],
    'microbe_disease_agreement.csv': ['taxid', 'mesh_id', 'status',
                                      'direction', 'n_sources'],
    'recommendation.csv': ['rank', 'food_key', 'score', 'food_group'],
    'kg_stats.csv': ['source', 'relation', 'entity', 'triples'],
}


def check_schema():
    for fn, cols in SCHEMA.items():
        p, missing_file = _need(fn)
        if missing_file:
            _say('SKIP', fn, '없다')
            continue
        have = pd.read_csv(p[0], nrows=1).columns
        lack = [c for c in cols if c not in have]
        _say('FAIL' if lack else 'PASS', fn,
             f'빠진 열 {lack}' if lack else f'열 {len(cols)} 확인')


# ------------------------------------------------------- 2. 미생물 축 도달성
def check_microbe():
    """질환 관계가 가리키는 균이 **축에 실제로 있는가.**

    병합 taxid 버그가 여기서 났다 — 관계는 KG 에 올라가는데 그 균의 라벨·계통·
    compound 링크가 없었다. 정본으로 정규화한 뒤 비교한다.
    """
    paths, miss = _need('microbes.csv', 'microbe_disease_disbiome.csv',
                        'microbe_disease_gutmdisorder.csv')
    if miss:
        return _say('SKIP', '미생물 축 도달성', f'{miss} 없다')
    m = pd.read_csv(paths[0], dtype={'taxid': str, 'taxid_current': str})
    alias = taxid_alias()
    have = set(canon(m.taxid, alias))
    lost = {}
    for p in paths[1:]:
        d = pd.read_csv(p, dtype={'taxid': str})
        sel = d[d.is_mental | d.is_neuro]
        gone = set(canon(sel.taxid, alias)) - have
        if gone:
            lost[os.path.basename(p)] = sorted(gone)[:6]
    _say('FAIL' if lost else 'PASS', '미생물 축 도달성',
         f'축에 없는 균 {lost}' if lost else
         f'정신·신경 관계의 균 전부 축에 있다 (균 {len(have)})')

    # 정본 정규화가 실제로 걸려 있는지 — 안 걸리면 같은 균을 두 번 센다.
    dup = int(m.taxid_current.duplicated().sum())
    _say('PASS', '정본 taxid 열', f'행 {len(m)} = 고유 균 {m.taxid_current.nunique()}'
         + (f' + 병합 전/후 중복 {dup} 쌍' if dup else ''))


def check_links():
    """compound 링크가 같은 (균, compound) 를 두 번 세지 않는가."""
    paths, miss = _need('compound_microbe.csv')
    if miss:
        return _say('SKIP', 'compound 링크', '없다')
    cm = pd.read_csv(paths[0], dtype={'taxid': str, 'taxid_current': str})
    if cm.duplicated(['kegg', 'taxid']).any():
        return _say('FAIL', 'compound 링크',
                    f'(kegg, taxid) 중복 {int(cm.duplicated(["kegg","taxid"]).sum())}')
    uniq = len(cm.drop_duplicates(['kegg', 'taxid_current']))
    _say('PASS', 'compound 링크',
         f'행 {len(cm):,} = 고유 (균, compound) 쌍 {uniq:,}')

    # 읽는 자리(common)가 정본으로 모으는지 — 여기서 안 모이면 집계가 부푼다.
    from common import compound_microbe
    cmr = compound_microbe(sources=('kegg',))
    _say('FAIL' if len(cmr) != uniq else 'PASS', 'compound_microbe() 정규화',
         f'읽은 쌍 {len(cmr):,} vs 고유 {uniq:,}')


def check_agreement():
    """방향 합의 표의 상태와 방향이 서로 맞는가."""
    paths, miss = _need('microbe_disease_agreement.csv')
    if miss:
        return _say('SKIP', '방향 합의 표', '없다')
    a = pd.read_csv(paths[0], dtype={'taxid': str})
    bad = []
    if not set(a.status) <= {'agreed', 'conflict'}:
        bad.append(f'status 값 {set(a.status) - {"agreed", "conflict"}}')
    # 합의면 방향이 있어야 하고, 모순이면 없어야 한다.
    if a[a.status == 'agreed'].direction.isna().any():
        bad.append('agreed 인데 direction 이 빈 행')
    if (a[a.status == 'conflict'].direction.notna()
            & (a[a.status == 'conflict'].direction != '')).any():
        bad.append('conflict 인데 direction 이 있는 행')
    _say('FAIL' if bad else 'PASS', '방향 합의 표',
         '; '.join(bad) if bad else
         f'쌍 {len(a):,} (합의 {int((a.status == "agreed").sum()):,} · '
         f'모순 {int((a.status == "conflict").sum()):,})')


# ----------------------------------------------------------- 3. 분기 등록
#  `SWEEPS['ezero']` 를 `if __name__` 뒤에 등록해 한 번도 안 돌았던 적이 있다.
def check_registry():
    import sweep
    missing = [k for k, (_, cfg) in sweep.SWEEPS.items()
               if cfg is None and k not in ('gutbrain', 'simthr', 'ezero')]
    _say('FAIL' if missing else 'PASS', 'sweep 등록',
         f'디스패치 없는 쓸기 {missing}' if missing else
         f'쓸기 {len(sweep.SWEEPS)} 전부 실행 가능')

    import run_all
    unknown = [s for s in run_all.STEPS
               if s not in run_all.BUILD + run_all.ANALYZE
               and s not in run_all.VERIFY and s not in run_all.SWEEP]
    _say('FAIL' if unknown else 'PASS', 'run_all 단계',
         f'정의 없는 단계 {unknown}' if unknown else
         f'단계 {len(run_all.STEPS)} 전부 정의됨')


def check_emode():
    """문서에 적힌 `E_MODE` 가 전부 해소되는가.

    `union` 이 `nhanes` 분기 안에 중첩돼 조용히 `shrunk` 로 떨어졌던 적이 있다.
    그래서 **같은 값을 돌려주는 모드가 있으면** 의심한다.
    """
    import analyze
    modes = ['shrunk', 'binary', 'sig']
    got, fail = {}, []
    for mo in modes:
        try:
            s = analyze.resolve_e(mo)
            got[mo] = (len(s), round(float(s.fillna(0).abs().sum()), 4))
        except SystemExit as e:
            fail.append(f'{mo}: {e}')
    same = [f'{a}=={b}' for i, a in enumerate(got) for b in list(got)[i + 1:]
            if got[a] == got[b]]
    _say('FAIL' if fail or same else 'PASS', 'E_MODE 해소',
         ('; '.join(fail + same)) if (fail or same) else
         f'{len(got)} 모드가 서로 다른 E 를 돌려준다')

    # 모르는 이름은 **소리 내고 멈춰야** 한다 (조용한 기본값 복귀 금지).
    try:
        analyze.resolve_e('이런모드는없다')
        _say('FAIL', 'E_MODE 미지값', '모르는 모드가 조용히 통과했다')
    except SystemExit:
        _say('PASS', 'E_MODE 미지값', '모르는 모드에서 멈춘다')


def check_env():
    """소스가 읽는 환경변수가 `run_all.py --env` 에 다 나오는가."""
    import run_all
    found = set()
    for fn in os.listdir(HERE):
        if not fn.endswith('.py'):
            continue
        src = open(os.path.join(HERE, fn), encoding='utf-8').read()
        found |= set(re.findall(r"os\.environ\.get\(\s*['\"]([A-Z][A-Z0-9_]*)", src))
        found |= set(re.findall(r"os\.environ\[\s*['\"]([A-Z][A-Z0-9_]*)", src))
    listed = set(run_all.scan_env()) if hasattr(run_all, 'scan_env') else None
    if listed is None:
        return _say('SKIP', '환경변수 문서화', 'run_all.scan_env 없다')
    lack = sorted(found - listed)
    _say('FAIL' if lack else 'PASS', '환경변수 문서화',
         f'--env 에 안 나오는 것 {lack}' if lack else f'{len(found)} 개 전부 나온다')


# --------------------------------------------------------------- 4. 추천
def check_recommend():
    paths, miss = _need('recommendation.csv')
    if miss:
        return _say('SKIP', '추천 산출물', '없다')
    r = pd.read_csv(paths[0])
    bad = []
    if not r['score'].notna().all():
        bad.append('score 에 NaN')
    if not (r['rank'].values == range(1, len(r) + 1)).all():
        bad.append('rank 가 1..N 이 아니다')
    if not r['score'].is_monotonic_decreasing:
        bad.append('score 가 rank 순으로 내려가지 않는다')
    if r['food_name'].isna().any():
        bad.append('food_name 에 NaN')
    _say('FAIL' if bad else 'PASS', '추천 산출물',
         '; '.join(bad) if bad else f'{len(r):,} 행 · rank/score 정합')


# ------------------------------------------------------------- 5. KG 통계
def check_kg():
    paths, miss = _need('kg_stats.csv')
    if miss:
        return _say('SKIP', 'KG 통계', '없다')
    k = pd.read_csv(paths[0])
    tot = k[k.source.str.startswith('Total')]
    claim = k[k.source.str.startswith('Σ')]
    src = k[~k.source.str.startswith(('Total', 'Σ'))]
    if tot.empty:
        return _say('FAIL', 'KG 통계', 'Total 행이 없다')
    uniq = int(tot.triples.iloc[0])
    bad = []
    if not claim.empty:
        c = int(claim.triples.iloc[0])
        if int(src.triples.sum()) != c:
            bad.append(f'출처 합 {int(src.triples.sum()):,} != Σ 주장 {c:,}')
        if uniq > c:
            bad.append(f'고유 {uniq:,} > Σ 주장 {c:,}')
    _say('FAIL' if bad else 'PASS', 'KG 통계 정합',
         '; '.join(bad) if bad else
         f'고유 {uniq:,} ≤ Σ 주장 {int(claim.triples.iloc[0]):,}'
         if not claim.empty else f'고유 {uniq:,}')

    nt = os.path.join(OUT, 'ourkg.nt')
    if not os.path.exists(nt):
        return _say('SKIP', 'KG 파일', 'ourkg.nt 없다 (gitignore)')
    n = seen = 0
    dup = 0
    s = set()
    with open(nt, encoding='utf-8') as f:
        for line in f:
            n += 1
            h = hash(line)
            if h in s:
                dup += 1
            else:
                s.add(h)
    seen = len(s)
    bad = []
    if n != uniq:
        bad.append(f'줄 수 {n:,} != kg_stats Total {uniq:,}')
    if dup:
        bad.append(f'중복 statement {dup:,}')
    _say('FAIL' if bad else 'PASS', 'KG 파일 중복',
         '; '.join(bad) if bad else f'{n:,} 줄 · 중복 0')


# ---------------------------------------------------------------- 6. 문서
#  문서 수치가 산출물과 갈리는 일이 반복됐다. 핵심 수치만 자동으로 맞춘다.
def check_docs():
    paths, miss = _need('kg_stats.csv', 'microbes.csv')
    if miss:
        return _say('SKIP', '문서 수치', f'{miss} 없다')
    k = pd.read_csv(paths[0])
    tot = k[k.source.str.startswith('Total')]
    m = pd.read_csv(paths[1], dtype={'taxid': str, 'taxid_current': str})
    want = {
        'KG 고유 triple': f'{int(tot.triples.iloc[0]):,}',
        'KG 관계 수': str(int(tot.relation.iloc[0])),
        '미생물 고유 균': f'{m.taxid_current.nunique():,}',
    }
    rd = os.path.join(HERE, 'README.md')
    if not os.path.exists(rd):
        return _say('SKIP', '문서 수치', 'README.md 없다')
    txt = open(rd, encoding='utf-8').read()
    lack = [f'{k2}={v}' for k2, v in want.items() if v not in txt]
    _say('FAIL' if lack else 'PASS', 'README 수치',
         f'README 에 없는 값 {lack}' if lack else
         f'핵심 수치 {len(want)} 개가 산출물과 맞는다')


CHECKS = {'schema': check_schema, 'microbe': check_microbe, 'links': check_links,
          'agreement': check_agreement, 'registry': check_registry,
          'emode': check_emode, 'env': check_env, 'recommend': check_recommend,
          'kg': check_kg, 'docs': check_docs}


def main(argv):
    if argv and argv[0] == '--list':
        print(' '.join(CHECKS))
        return 0
    names = argv or list(CHECKS)
    unknown = [n for n in names if n not in CHECKS]
    if unknown:
        sys.exit(f'알 수 없는 검사 {unknown}. 가능: {list(CHECKS)}')
    for n in names:
        print(f'[{n}]')
        try:
            CHECKS[n]()
        except Exception as e:
            # **검사가 죽으면 뒤 검사가 안 돈다.** 산출물이 어긋나면 열이
            # 없거나 타입이 달라 예외가 나는 게 정상이므로, 그걸 FAIL 로
            # 보고하고 계속 간다. (이 구멍도 일부러 깨뜨려 보다가 찾았다.)
            _say('FAIL', n, f'{type(e).__name__}: {e}')
    n_fail = sum(1 for st, *_ in RESULT if st == 'FAIL')
    n_skip = sum(1 for st, *_ in RESULT if st == 'SKIP')
    print(f'\n통과 {len(RESULT) - n_fail - n_skip} / 실패 {n_fail} / 건너뜀 {n_skip}')
    return 1 if n_fail else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
