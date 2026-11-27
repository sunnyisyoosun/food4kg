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
from common import outp, OUT, BASE, taxid_alias, canon          # noqa: E402

RESULT = []            # (상태, 이름, 메시지)


def _say(state, name, msg):
    RESULT.append((state, name, msg))
    mark = {'PASS': 'ok  ', 'FAIL': 'FAIL', 'SKIP': '--  '}[state]
    print(f'  {mark} {name:34s} {msg}')


def _need(*names):
    """산출물이 다 있으면 DataFrame 들을, 하나라도 없으면 None 을 돌려준다."""
    out = []
    for n in names:
        p = outp(n)
        if not os.path.exists(p):
            return None, n
        out.append(p)
    return out, None


# ---------------------------------------------------------------- 1. 스키마
# 단계를 따로 돌리다가 열 이름을 바꾸면 **읽는 쪽이 조용히 빈 값을 본다.**
# 아래 열은 다른 모듈이 이름으로 집어 쓰는 것들이다.
SCHEMA = {
    'foods.csv': ['food_key', 'food_name', 'data_type', 'n_compound',
                  'n_source', 'source_types', 'label_share'],
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


def check_units():
    """KEGG 매핑된 영양소의 단위가 **전부 질량 환산 가능한지.**

    `build.py` 는 모르는 단위를 조용히 그램으로 뒀다(`.fillna(1.0)`). 그래서
    매핑표만 보던 때 citric acid 가 1,740 g/100g 으로 나왔다. 지금은 build 가
    멈추게 고쳤지만 **build 는 몇 분 걸린다** — 매핑표에 비질량 단위를 넣는
    순간 커밋에서 걸려야 한다. 그게 이 검사다 (§53).

    FDC 에는 `KCAL`·`kJ`·`PH`·`SP_GR`·`UMOL_TE`·`MCG_RE`·`MG_ATE`·`MG_GAE` 가
    있고 전부 질량이 아니다. 지금 걸린 것은 0 개다(`Energy`·`Specific Gravity`
    는 `nutrient_kegg_map.csv` 에서 `kegg=0` 이고 `kegg_map()` 이 걸러낸다).
    """
    import common
    nut = os.path.join(common.FDC_RAW, 'nutrient.csv')
    if not os.path.exists(nut):
        return _say('SKIP', '영양소 단위 매핑', 'FDC nutrient.csv 가 없다')
    u = dict(zip(*pd.read_csv(nut, usecols=['id', 'unit_name']).values.T))
    nm = dict(pd.read_csv(nut, usecols=['id', 'name']).values)
    ids = set()
    for fn in ('nutrient_kegg_map.csv', 'nutrient_kegg_candidates.csv'):
        p = os.path.join(common.BASE, 'setup', fn)
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        col = 'nutrient_kegg' if 'nutrient_kegg' in d else 'kegg'
        # `kegg_map()` 과 **같은 규칙**으로 좁힌다 — kegg 가 'C…' 가 아닌 행은
        # 매핑이 아니다(Energy 는 0 으로 적혀 있다).
        d = d[d[col].astype(str).str.startswith('C')]
        ids |= set(d['nutrient_id'].dropna().astype(int))
    bad = {i: u.get(i) for i in ids if u.get(i) not in common.UNIT_TO_G}
    _say('FAIL' if bad else 'PASS', '영양소 단위 매핑',
         '질량이 아닌 단위: ' + ', '.join(
             f'{i} {nm.get(i)!r} {v!r}' for i, v in sorted(bad.items())[:6])
         if bad else
         f'KEGG 매핑된 영양소 {len(ids)} 전부 UNIT_TO_G 로 환산된다 '
         f'({sorted(common.UNIT_TO_G)})')


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


def _csv_literals(node, nested_calls=()):
    """노드 안의 `.csv` 문자열 리터럴과 f-string 을 모은다. **한 자리다.**

    `declared_outputs` 와 `io_graph` 가 같은 스캔을 각자 들고 있었다 — 둘 다
    f-string 치환부를 `*` 로 접고 중첩 호출의 안쪽을 빼야 하는데, 그 두 규칙을
    두 군데 적으면 갈라진다(실제로 둘 다 한 번씩 그 자리에서 틀렸다).

    `nested_calls` 에 함수 이름을 주면 그 이름의 **중첩 호출 안쪽을 뺀다** —
    `pd.read_csv(p).to_csv(q)` 에서 `to_csv` 노드를 통째로 훑으면 `p` 까지
    "쓰는 것" 으로 세기 때문이다.
    """
    import ast
    # **f-string 자식은 **항상** 뺀다.** `f'a_{k}.csv'` 의 자식 Constant
    # `.csv` 까지 세면 아무것도 안 가리키는 패턴이 생긴다. 두 함수를 합칠 때
    # 이 규칙을 조건부로 만들었다가 시험이 회귀를 잡았다.
    inner = {id(c) for n in ast.walk(node) if isinstance(n, ast.JoinedStr)
             for c in ast.walk(n) if c is not n}
    if nested_calls:
        inner |= {id(c) for n in ast.walk(node)
                  if isinstance(n, ast.Call) and n is not node
                  and getattr(n.func, 'attr', getattr(n.func, 'id', ''))
                  in nested_calls
                  for c in ast.walk(n)}
    out = set()
    for n in ast.walk(node):
        if id(n) in inner:
            continue
        lit = None
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            lit = n.value
        elif isinstance(n, ast.JoinedStr):
            lit = ''.join(v.value if isinstance(v, ast.Constant) else '*'
                          for v in n.values)
        if lit and '.csv' in lit:
            out.add(os.path.basename(lit))
    return out


def declared_outputs(here=None):
    """코드가 **쓸 수 있다고 말한** 산출물 이름의 패턴 목록.

    모든 `.py` 를 AST 로 읽어 `.csv` 가 든 문자열 상수와 f-string 을 모은다.
    f-string 의 치환부는 `*` 로 두어 `learned_{FEATURES}.csv` 가
    `learned_form.csv` 를 덮게 한다. **문자열을 조립해서 쓰는 경로는 놓친다**
    — 그래서 이 검사는 "코드에 흔적이 없다" 까지만 말하고, 그게 곧 고아라고
    단정하지 않는다(아래 메시지가 생산자 후보를 같이 보여 준다).
    """
    import ast
    here = here or HERE
    pats = {}
    for fn in sorted(f for f in os.listdir(here) if f.endswith('.py')):
        tree = ast.parse(open(os.path.join(here, fn), encoding='utf-8').read())
        for lit in _csv_literals(tree):
            pats.setdefault(lit, set()).add(fn)
    return pats


def check_outputs():
    """`out/` 의 산출물마다 **만드는 코드가 레포에 있는지.**

    문서가 가리키는 산출물의 생산자를 지우고 문서는 안 고친 적이 있다
    (`3508e48` 가 `ensemble.py` 를 지워 `ensemble_comparison.csv` 가 고아가
    됐다). 더 나쁜 것은 **커밋된 적조차 없는** 일회성 스크립트의 산물이다
    (`pca_comparison.csv`·`threshold_comparison.csv` 는 `git log -S` 가 0 건).
    둘 다 "재현 가능한 산출물" 이라고 표에 올라가 있었다.

    `provenance.json` 기록의 **부재는 실패로 삼지 않는다.** 기본값 아닌 환경에서만
    만들어지는 산출물(`consensus_*`)은 기본 실행에 기록이 안 남는 것이 정상이고,
    기록은 장치를 넣은 뒤의 실행만 담는다. 그래서 여기서 FAIL 은 **코드 부재**
    하나이고, 기록 부재는 세어서 보여 주기만 한다 — 안 재는 것을 재는 척하지
    않으려고 적어 둔다.
    """
    import json
    if not os.path.isdir(OUT):
        return _say('SKIP', '산출물 생산자', 'out/ 이 없다')
    pats = declared_outputs()
    rx = [(re.compile('^' + re.escape(k).replace('\\*', '.*') + '$'), k)
          for k in pats]
    # **하위 폴더까지 본다.** 파생물을 `out/sweep/` 등으로 내린 뒤 이 검사가
    # csv 89 -> 49 만 보고 **조용히 통과했다** — 옮긴 40 개가 생산자·문서 언급
    # 보장 밖으로 나간 것이다. `legacy/` 는 생산 코드가 없는 기록이라 뺀다.
    have = []
    for root, dirs, files in os.walk(OUT):
        dirs[:] = [d for d in dirs if d != 'legacy']
        have += [f for f in files if f.endswith('.csv')]
    have = sorted(have)
    if not have:
        return _say('SKIP', '산출물 생산자', 'out/ 에 csv 가 없다')
    orphan = [f for f in have if not any(r.match(f) for r, _ in rx)]

    # **파일명은 ASCII 만.** `consensus_<설정>.csv` 의 설정 키가 `현행` 이라
    # `consensus_현행.csv` 가 생겼다 — 다른 OS·도구에서 깨져 읽히고 URL 로도
    # 못 쓴다. 키가 파일명이 되는 구조라 이름만 바꾸면 다시 생긴다 (§54).
    nonascii = [f for f in have if not f.isascii()]
    _say('FAIL' if nonascii else 'PASS', '산출물 이름 ASCII',
         f'ASCII 가 아닌 파일명 {nonascii[:5]}' if nonascii else
         f'csv {len(have)} 전부 ASCII')

    # **열 이름도 ASCII 만.** 한국어 열이 82 종 있었다 — 다른 도구로 읽을 때
    # 인코딩에 걸리고, `df.열이름` 속성 접근이 되지 않아 코드가 두 표기를
    # 오가게 된다(§55). 값은 한국어를 허용한다 — 그건 내용이다.
    import csv as _csv
    badcol = []
    for root, dirs, files in os.walk(OUT):
        dirs[:] = [d for d in dirs if d != 'legacy']
        for f in sorted(files):
            if not f.endswith('.csv'):
                continue
            try:
                with open(os.path.join(root, f), encoding='utf-8') as fh:
                    hdr = next(_csv.reader(fh))
            except Exception:
                continue
            badcol += [f'{f}:{c}' for c in hdr if not c.isascii()]
    _say('FAIL' if badcol else 'PASS', '산출물 열 이름 ASCII',
         f'ASCII 가 아닌 열 {badcol[:5]}' if badcol else
         f'csv {len(have)} 의 열 이름 전부 ASCII')

    # **파생물이 하위 폴더에 있는지.** `common.OUT_SUB` 가 규칙이고 쓰는 쪽은
    # `outp()` 를 쓴다. 누가 `os.path.join(OUT, …)` 로 되돌리면 평평한 자리에
    # 떨어지는데, 그걸 사람이 눈으로 볼 수는 없다.
    # **git 이 추적하는 파일 크기.** `.gitignore` 가 경로를 못 박고 있어서
    # §56 에서 파일을 옮기자 118 MB 가 추적으로 들어왔고 GitHub 가 푸시를
    # 거부했다(100 MB 제한). 커밋 시점에 알아야 한다 — 푸시는 그 뒤다.
    import subprocess
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        ls = subprocess.run(['git', 'ls-files', '-z'], cwd=BASE, env=env,
                            capture_output=True, text=True, timeout=30)
        big = []
        for rel in ls.stdout.split('\0'):
            if not rel:
                continue
            fp = os.path.join(BASE, rel)
            if os.path.isfile(fp) and os.path.getsize(fp) > 90 * 1024 ** 2:
                big.append(f'{rel} {os.path.getsize(fp) / 1024 ** 2:.0f}MB')
        _say('FAIL' if big else 'PASS', 'git 추적 파일 크기',
             f'GitHub 100MB 제한을 넘는다: {big[:3]}' if big else
             'git 이 추적하는 파일 전부 90MB 이하')
    except Exception as e:
        _say('SKIP', 'git 추적 파일 크기', f'git 을 못 불렀다: {e}')

    import common as _c
    misplaced = [f for f in os.listdir(OUT)
                 if f.endswith('.csv') and _c.out_sub(f)]
    _say('FAIL' if misplaced else 'PASS', '파생물 폴더 배치',
         f'하위 폴더로 가야 하는데 out/ 에 있다 {misplaced[:5]}' if misplaced else
         f'하위 폴더 {len(_c.OUT_SUB)} 개 규칙대로 놓여 있다')
    pv = outp('provenance.json')
    rec = json.load(open(pv)) if os.path.exists(pv) else {}
    # 고아의 **마지막 생산자**를 출처 기록에서 찾아 준다. 지워진 모듈 이름이
    # 남아 있으면 git 이력을 뒤질 자리를 바로 가리킨다.
    who = {f: rec[f].get('argv', '?') for f in orphan if f in rec}
    unrec = [f for f in have if f not in rec]
    # --- 둘째: 문서가 그 산출물을 **언급하는지** -------------------------
    # 처음엔 basename 을 literal 로 grep 해서 "미언급 20 개" 라고 셌다.
    # **그 검사가 틀렸다** — `out/consensus_*.csv` 처럼 패턴 행으로 적힌 것을
    # 못 봤다. 문서 쪽 토큰도 `*` 를 와일드카드로 받아야 한다.
    doc_pats = set()
    for fn in DOCS + DOCS_EXCLUDED:          # §43 산출물 표는 RESULTS.md 에 있다
        dp = os.path.join(HERE, fn)
        if os.path.exists(dp):
            doc_pats |= set(re.findall(r'[^\s`|/]*\.csv',
                                       open(dp, encoding='utf-8').read()))
    # **선두가 와일드카드인 토큰은 버린다.** 문서에 `out/*.csv` 라는 말이
    # 한 번 나오는데, 그걸 패턴으로 받으면 `^.*$` 가 되어 **88 개 전부가
    # 언급된 것으로 통과한다.** 처음 판이 그래서 조용히 PASS 했다.
    # 리터럴 머리가 4 자 이상인 것만 패턴으로 인정한다.
    drx = []
    for d in doc_pats:
        # `{소스}` 같은 자리표시자는 **중괄호 안쪽까지 통째로** 지워야 한다.
        # 괄호만 `.*` 로 바꾸면 `..*소스.csv` 가 되어 아무것도 안 맞는다.
        b = re.sub(r'\{[^}]*\}', '*', os.path.basename(d))
        head = b.split('*')[0]
        if len(head) < 4:
            continue
        drx.append(re.compile('^' + re.escape(b).replace('\\*', '.*') + '$'))
    undoc = [f for f in have if not any(r.match(f) for r in drx)]

    msg = (f'만드는 코드가 없는 산출물 {len(orphan)}: '
           + ', '.join(f'{f}({who.get(f, "출처기록도 없다")})' for f in orphan[:6])
           + (f' 외 {len(orphan) - 6}' if len(orphan) > 6 else '')) if orphan else (
           f'csv {len(have)} 전부 코드에 생산자가 있다 '
           f'(이름 패턴 {len(pats)} · 출처기록 없는 것 {len(unrec)} — 실패 아님)')
    _say('FAIL' if orphan else 'PASS', '산출물 생산자', msg)
    _say('FAIL' if undoc else 'PASS', '산출물 문서 언급',
         f'어느 문서에도 안 나오는 산출물 {len(undoc)}: ' + ', '.join(undoc[:8])
         + (f' 외 {len(undoc) - 8}' if len(undoc) > 8 else '') if undoc else
         f'csv {len(have)} 전부 문서에 나온다 (문서 쪽 이름·패턴 {len(drx)})')


def check_deadcode():
    """`if __name__` **뒤에** 정의된 함수와 아무도 쓰지 않는 모듈을 찾는다.

    같은 함정을 두 번 당했다 — `SWEEPS['ezero']` 를 `if __name__` 뒤에 등록해
    쓸기가 한 번도 안 돌았고, `ensemble.py` 의 `boot()` 도 거기 있었다.
    모듈로 import 하면 정의되지만 **스크립트로 돌리면 그 줄에 닿지 않는다.**
    """
    import ast
    late, orphan = [], []
    files = sorted(f for f in os.listdir(HERE) if f.endswith('.py'))
    for fn in files:
        src = open(os.path.join(HERE, fn), encoding='utf-8').read()
        tree = ast.parse(src)
        guard = None
        for node in tree.body:
            if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                    and getattr(node.test.left, 'id', '') == '__name__'):
                guard = node.lineno
        if guard:
            for node in tree.body:
                if (isinstance(node, (ast.FunctionDef, ast.Assign))
                        and node.lineno > guard):
                    nm = (node.name if isinstance(node, ast.FunctionDef)
                          else getattr(node.targets[0], 'id', '?'))
                    late.append(f'{fn}:{nm}')
        # 아무 모듈도 import 하지 않고 run_all 단계도 아니면 고아다.
        stem = fn[:-3]
        # common 은 전부가 import 하고, run_all·check 는 입구다.
        # build·analyze 는 run_all 이 단계 이름이 아니라 **스크립트로** 부른다.
        if stem in ('check', 'run_all', 'common', 'build', 'analyze'):
            continue
        used = any(re.search(rf'\b(import {stem}\b|from {stem} import)',
                             open(os.path.join(HERE, g), encoding='utf-8').read())
                   for g in files if g != fn)
        import run_all
        if not used and stem not in run_all.STEPS and not any(
                v[0] == fn for v in {**run_all.VERIFY, **run_all.SWEEP}.values()):
            orphan.append(fn)
    _say('FAIL' if late else 'PASS', '__main__ 뒤 정의',
         f'스크립트로 돌면 안 닿는다: {late}' if late else
         f'{len(files)} 파일 전부 정의가 가드 앞에 있다')
    _say('FAIL' if orphan else 'PASS', '고아 모듈',
         f'아무도 안 쓰고 단계에도 없다: {orphan}' if orphan else
         '모든 모듈이 import 되거나 run_all 단계다')


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

    # **같은 스위치의 기본값이 두 군데서 갈라지면 한쪽만 되돌아간다.** §27 에서
    # 앙상블을 기본값에서 뺐는데 `recommend()` 만 'none' 으로 바꾸고
    # `ensemble_modes()` 는 'shrunk,nhanes_all' 로 남아, 점수는 shrunk 로 내고
    # 근거는 앙상블로 설명하는 불일치가 되살아났다 (§51). 리터럴 기본값이
    # 서로 다르게 적힌 변수를 잡는다 — 상수로 모으면 통과한다.
    defaults = {}
    for fn in sorted(f for f in os.listdir(HERE) if f.endswith('.py')):
        # **시험 파일은 일부러 반례를 담는다.** 넣자마자 `tests.py` 안의
        # `E_MODE', 'union_all'`(회귀 시험의 assertNotIn 문자열)과 오류 주입용
        # `X_SW` 를 잡아 FAIL 이 떴다 — 검사가 자기 시험을 결함으로 본 것이다.
        if fn == 'tests.py':
            continue
        src = open(os.path.join(HERE, fn), encoding='utf-8').read()
        for name, dflt in re.findall(
                r"os\.environ\.get\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*,"
                r"\s*(['\"][^'\"]*['\"])\s*\)", src):
            defaults.setdefault(name, {}).setdefault(dflt.strip('\'"'), []).append(fn)
    split = {k: {d: sorted(set(v)) for d, v in m.items()}
             for k, m in defaults.items() if len(m) > 1}
    _say('FAIL' if split else 'PASS', '환경변수 기본값 단일성',
         f'기본값이 갈린 변수 {split}' if split else
         f'리터럴 기본값을 가진 {len(defaults)} 개 모두 한 값이다')


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

    nt = outp('ourkg.nt')
    if not os.path.exists(nt):
        return _say('SKIP', 'KG 파일', 'ourkg.nt 없다 (gitignore)')
    # IRI 에 들어가면 안 되는 문자 — 공백·꺾쇠·따옴표·파이프·역따옴표 등.
    # `kegg.jp/entry/C00094|C11481` 같은 값이 2,323 건 있었다(§37). rdflib 는
    # 경고만 하고 넘어가므로 **사람이 로그를 봐야** 알았다. 여기서 막는다.
    ILLEGAL = re.compile(r'[\s<>"{}|\\^`]')
    n, dup, bad_iri = 0, 0, {}
    seen = set()
    with open(nt, encoding='utf-8') as f:
        for line in f:
            n += 1
            h = hash(line)
            if h in seen:
                dup += 1
            else:
                seen.add(h)
            # **N-Triples 구조대로 읽는다.** 그냥 `<...>` 를 긁으면 리터럴
            # 안의 꺾쇠를 잡는다 — FoodOn 라벨 "fat content < 50%, > 35% pufa"
            # 가 그렇게 오탐으로 걸렸다. 리터럴 안의 꺾쇠는 N-Triples 에서
            # 정상이다(`"`·`\`·개행만 escape 가 필요하다).
            # 줄 모양은 `<주어> <술어> <목적어> .` 또는 `… "리터럴" .` 이고
            # IRI 에는 `>` 가 들어갈 수 없으므로 `[^>]*` 로 끊어 읽으면 된다.
            m = re.match(r'<([^>]*)> <([^>]*)> (?:<([^>]*)>)?', line)
            if not m:
                bad_iri.setdefault('(파싱 실패)', 0)
                bad_iri['(파싱 실패)'] += 1
                continue
            for iri in m.groups():
                if iri and ILLEGAL.search(iri):
                    bad_iri.setdefault(iri, 0)
                    bad_iri[iri] += 1
    bad = []
    if n != uniq:
        bad.append(f'줄 수 {n:,} != kg_stats Total {uniq:,}')
    if dup:
        bad.append(f'중복 statement {dup:,}')
    _say('FAIL' if bad else 'PASS', 'KG 파일 중복',
         '; '.join(bad) if bad else f'{n:,} 줄 · 중복 0')
    _say('FAIL' if bad_iri else 'PASS', 'KG IRI 유효성',
         f'허용 안 되는 문자가 든 IRI {len(bad_iri)} 종 '
         f'{sum(bad_iri.values()):,} 건: {list(bad_iri)[:3]}' if bad_iri else
         'IRI 에 공백·파이프 등이 없다')


def check_pathcheck():
    """CSV 경로와 KG 경로가 같은 gut-brain compound 집합을 내는가.

    `analyze.py pathcheck` 가 KG 적재에 80 초라 매번 돌릴 수 없다. 대신 그
    판정이 `out/gutbrain_compounds.json` 에 적히므로 **결론과 신선도**를 본다.
    전에는 경고를 화면에만 찍어서 어긋난 상태가 20 일간 안 보였다 (§38).
    """
    import json
    p = outp('gutbrain_compounds.json')
    nt = outp('ourkg.nt')
    if not os.path.exists(p):
        return _say('SKIP', 'gut-brain 경로 일관', 'json 없다 (analyze.py pathcheck)')
    d = json.load(open(p))
    if 'agree' not in d:
        return _say('SKIP', 'gut-brain 경로 일관',
                    '판정이 안 적혀 있다 — analyze.py pathcheck 를 다시 돌려라')
    bad = []
    if not d['agree']:
        bad.append(f"어긋난다: CSV 에만 {d.get('only_csv')} · KG 에만 {d.get('only_kg')}")
    if os.path.exists(nt) and os.path.getmtime(p) < os.path.getmtime(nt):
        bad.append('판정이 ourkg.nt 보다 오래됐다 — pathcheck 를 다시 돌려라')
    _say('FAIL' if bad else 'PASS', 'gut-brain 경로 일관',
         '; '.join(bad) if bad else
         f"CSV {d.get('n_csv')}종 = KG {d.get('n_kg')}종")


def check_hooks():
    """커밋 훅이 **켜져 있는지**.

    `hooks/pre-commit` 은 레포에 있지만 `git config core.hooksPath hooks` 를
    한 번 쳐야 돈다. 그 설정은 `.git/config` 에 있어 **버전 관리되지 않으므로
    새로 클론한 사람은 훅 없이 커밋한다.** git 은 클론 시 훅 자동 활성화를
    보안상 막으니(임의 코드 실행이 된다) 할 수 있는 것은 **알려 주는 것**이다.

    훅을 쓰지 않기로 했으면 `OURKG_NO_HOOK_CHECK=1` 로 끈다.
    """
    import subprocess
    if os.environ.get('OURKG_NO_HOOK_CHECK') == '1':
        return _say('SKIP', '커밋 훅', 'OURKG_NO_HOOK_CHECK=1')
    hook = os.path.join(BASE, 'hooks', 'pre-commit')
    if not os.path.exists(hook):
        return _say('SKIP', '커밋 훅', 'hooks/pre-commit 이 없다')
    bad = []
    # **`cwd` 만으로는 부족하다.** `git commit` 은 GIT_DIR·GIT_WORK_TREE 를
    # 환경에 내보내고 그게 cwd 를 이긴다 — 훅 안에서 이 검사를 돌리면 BASE 가
    # 아니라 *훅을 띄운* 레포의 설정을 읽는다. 실제 레포에서는 우연히 같은 답이
    # 나와 안 보였고, 임시 레포로 보는 메타 시험이 커밋 때만 깨져서 드러났다.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    try:
        got = subprocess.run(['git', 'config', '--get', 'core.hooksPath'],
                             cwd=BASE, env=env,
                             capture_output=True, text=True).stdout.strip()
    except Exception as e:                       # git 이 없는 환경
        return _say('SKIP', '커밋 훅', f'git 을 못 불렀다: {e}')
    if got != 'hooks':
        bad.append(f'core.hooksPath 가 {got!r} 다 — `git config core.hooksPath hooks`')
    if not os.access(hook, os.X_OK):
        bad.append('hooks/pre-commit 에 실행 권한이 없다 — `chmod +x hooks/pre-commit`')
    _say('FAIL' if bad else 'PASS', '커밋 훅',
         '; '.join(bad) if bad else 'core.hooksPath=hooks · 실행 가능')


# ------------------------------------------------- 5b. 산출물 출처 (provenance)
#
# **정본 산출물**은 기본값으로 만들어야 한다. 쓸기 산출물(`*_comparison.csv` 등)은
# 환경을 바꿔 돌리는 것이 목적이므로 예외다 — 그 구분이 없으면 검사가 늘 실패한다.
CANONICAL = (
    'recommendation.csv', 'recommendation.png', 'foods.csv', 'microbes.csv',
    'compound_microbe.csv', 'compound_depression.csv', 'kg_stats.csv',
    'eval_method1.csv', 'eval_method2.csv', 'eval_method2_calibration.csv',
    'eval_sparql.json', 'microbe_disease_agreement.csv', 'modimed_labels.csv',
)
# 산출물 -> 그것이 읽는 입력. 입력보다 오래되면 낡은 것이다.
# (11-05 산출물 9 개가 입력 재구축 뒤 20 일 방치된 일이 있었다.)
DEPENDS = {
    'recommendation.csv': ('foods.csv', 'compound_depression.csv', 'food_form.csv'),
    'modimed_labels.csv': ('foods.csv',),
    'eval_method1.csv': ('compound_microbe.csv', 'microbes.csv'),
    'microbe_disease_agreement.csv': ('microbe_disease_disbiome.csv',
                                      'microbe_disease_gutmdisorder.csv'),
    'compound_microbe.csv': ('microbes.csv',),
    'kg_stats.csv': ('microbes.csv', 'compound_microbe.csv', 'foods.csv'),
    'diet_intervention_score.csv': ('compound_microbe.csv', 'compound_depression.csv'),
    'e_autism_microbe.csv': ('compound_microbe.csv', 'microbe_disease_agreement.csv'),
}


def io_graph(here=None):
    """모듈마다 **읽는 CSV 와 쓰는 CSV** 를 코드에서 뽑는다.

    `DEPENDS` 는 손으로 쓴 9 쌍이었다. 그래서 `compound_microbe_measured.csv`
    처럼 아무도 적어 주지 않은 산출물은 **신선도 검사를 한 번도 받지 않았다.**
    손 목록은 낡는다 — `scan_env` 를 소스에서 긁게 만든 것과 같은 이유다.

    `read_csv(...)` · `to_csv(...)` 호출의 인수에 든 `.csv` 문자열만 본다.
    경로를 변수에 담아 넘기는 자리는 **놓친다**(그건 손 목록이 메운다).
    놓치는 것은 괜찮지만 **없는 의존을 만들면 안 된다** — 한 모듈이 읽고 쓰는
    것끼리만 잇고, 자기 자신으로 가는 변은 버린다.
    """
    import ast
    here = here or HERE
    _csvs = lambda node: _csv_literals(node, ('read_csv', 'to_csv'))
    io = {}
    for fn in sorted(f for f in os.listdir(here) if f.endswith('.py')):
        if fn in ('check.py', 'tests.py'):       # 검사 자신은 소비자가 아니다
            continue
        tree = ast.parse(open(os.path.join(here, fn), encoding='utf-8').read())
        r, w = set(), set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                name = getattr(n.func, 'attr', getattr(n.func, 'id', ''))
                if name == 'read_csv':
                    r |= _csvs(n)
                elif name == 'to_csv':
                    w |= _csvs(n)
        io[fn] = (r, w)

    # **모듈 안에서 읽고 쓰는 것끼리는 잇지 않는다.** 처음엔 전부 이었더니
    # 없는 의존 84 개가 생겼다 — `analyze.py` 는 한 번 돌며 11 개를 읽고 12 개를
    # 쓰는데, 그 안의 기록 순서는 내부 사정이라 mtime 선후에 뜻이 없다.
    # 뜻이 있는 것은 **모듈을 넘는 변**이다: 다른 모듈이 만든 입력보다 내 산출물이
    # 오래됐으면 그 모듈을 다시 돌려야 한다.
    producer = {f: fn for fn, (_, w) in io.items() for f in w}
    g = {}
    for fn, (r, w) in io.items():
        for out_f in w:
            for dep in r:
                if (dep != out_f and '*' not in out_f and '*' not in dep
                        and producer.get(dep) not in (None, fn)):
                    g.setdefault(out_f, set()).add(dep)
    return g


def check_provenance():
    """정본 산출물이 기본값으로 만들어졌는지, 입력보다 낡지 않았는지."""
    import json
    # 손 목록(DEPENDS)과 **코드에서 뽑은 그래프**를 합친다. 어느 쪽에서 온
    # 변인지 메시지에 남긴다 — 뽑은 쪽이 없는 의존을 만들면 그 자리를 봐야 한다.
    derived = io_graph()
    edges = {k: set(v) for k, v in DEPENDS.items()}
    for k, v in derived.items():
        edges.setdefault(k, set()).update(v)
    stale = []
    for out_f, deps in edges.items():
        p = outp(out_f)
        if not os.path.exists(p):
            continue
        for d in sorted(deps):
            dp = outp(d)
            if os.path.exists(dp) and os.path.getmtime(p) < os.path.getmtime(dp) - 1:
                src = '손' if d in DEPENDS.get(out_f, ()) else '코드'
                stale.append(f'{out_f} < {d}({src})')
    n_edge = sum(len(v) for v in edges.values())
    _say('FAIL' if stale else 'PASS', '산출물 신선도',
         f'입력보다 오래된 것 {stale[:6]}'
         + (f' 외 {len(stale) - 6}' if len(stale) > 6 else '') if stale else
         f'의존 {n_edge} 변(산출물 {len(edges)}) 모두 산출물이 입력보다 새롭다 '
         f'— 손 목록 {sum(len(v) for v in DEPENDS.values())} · 코드에서 뽑은 것 '
         f'{sum(len(v) for v in derived.values())}')

    pv = outp('provenance.json')
    if not os.path.exists(pv):
        return _say('SKIP', '정본 산출물 출처', 'provenance.json 없다 — 한 단계 돌려라')
    rec = json.load(open(pv))
    bad = {f: r['env'] for f, r in rec.items()
           if f in CANONICAL and r.get('env')}
    unknown = [f for f in CANONICAL
               if os.path.exists(outp(f)) and f not in rec]
    msg = []
    if bad:
        msg.append(f'기본값 아닌 환경으로 만들어진 정본 {bad}')
    _say('FAIL' if bad else 'PASS', '정본 산출물 출처',
         '; '.join(msg) if msg else
         f'기록 {len(rec)} 건 · 정본 중 비기본값 0'
         + (f' (기록 없는 정본 {len(unknown)} — 아직 안 돌린 단계)' if unknown else ''))


# ---------------------------------------------------------------- 6. 문서
#  문서 수치가 산출물과 갈리는 일이 반복됐다. 핵심 수치만 자동으로 맞춘다.
# 산출물에서 계산할 수 있는 "사실" — 문서는 이 값을 적어야 한다.
# 문서 안의 `<!--chk:이름-->` 앵커 바로 **앞**의 숫자와 비교한다.
#
# 왜 앵커인가 — 전에는 "값이 문서 어딘가에 있나" 만 봤고 수치 3 개뿐이었다.
# 그러면 다른 자리에 묵은 값이 남아도 통과한다. 실제로 그 셋 밖의 수치
# (`VMH 44,094` · `MiKG 7,193` · 겹침)는 검사가 아니라 **손으로** 찾아 고쳤다.
# 앵커를 달면 **그 자리**를 검사하므로 어디가 틀렸는지도 바로 나온다.
# 마크다운에서 HTML 주석은 렌더링되지 않아 읽는 사람에게는 안 보인다.
def facts():
    import pandas as pd
    g = lambda n: outp(n)
    out = {}
    if os.path.exists(g('kg_stats.csv')):
        k = pd.read_csv(g('kg_stats.csv'))
        tot = k[k.source.str.startswith('Total')]
        cl = k[k.source.str.startswith('Σ')]
        if len(tot):
            out['kg.triples'] = f'{int(tot.triples.iloc[0]):,}'
            out['kg.relations'] = str(int(tot.relation.iloc[0]))
            out['kg.entities'] = f'{int(tot.entity.iloc[0]):,}'
        if len(cl):
            out['kg.claims'] = f'{int(cl.triples.iloc[0]):,}'
            if len(tot):
                out['kg.overlap'] = f'{int(cl.triples.iloc[0]) - int(tot.triples.iloc[0]):,}'
    if os.path.exists(g('microbes.csv')):
        m = pd.read_csv(g('microbes.csv'), dtype={'taxid': str, 'taxid_current': str})
        out['microbe.ids'] = f'{len(m):,}'
        if 'taxid_current' in m:
            out['microbe.taxa'] = f'{m.taxid_current.nunique():,}'
        out['microbe.kegg_org'] = f'{int(m.kegg_org.notna().sum()):,}'
    if os.path.exists(g('compound_microbe.csv')):
        cm = pd.read_csv(g('compound_microbe.csv'),
                         dtype={'taxid': str, 'taxid_current': str})
        out['links.rows'] = f'{len(cm):,}'
        if 'taxid_current' in cm:
            out['links.unique'] = f'{len(cm.drop_duplicates(["kegg", "taxid_current"])):,}'
        out['links.species'] = f'{int((cm.match_rank == "species").sum()):,}'
        out['links.genus'] = f'{int((cm.match_rank == "genus").sum()):,}'
    if os.path.exists(g('compound_microbe_vmh.csv')):
        v = pd.read_csv(g('compound_microbe_vmh.csv'))
        out['links.vmh'] = f'{len(v):,}'
        out['links.vmh_compounds'] = f'{v.kegg.nunique():,}'
    if os.path.exists(g('compound_microbe_measured.csv')):
        out['links.measured'] = f'{len(pd.read_csv(g("compound_microbe_measured.csv"))):,}'
    # **검사 수를 문서가 손으로 적고 있었다** — "29 항목" 이 다섯 군데 남아
    # 있었다(지금 16). 세는 것은 코드가 한다.
    out['check.names'] = str(len(CHECKS))
    _fl = g('food_link.json')
    if os.path.exists(_fl):
        import json
        fj = json.load(open(_fl))
        for k, name in (('food_multi_source', 'food.multi_source'),
                        ('food_mixed_types', 'food.mixed_types'),
                        ('food_label_minority', 'food.label_minority'),
                        ('food_source_max', 'food.source_max')):
            if k in fj:
                out[name] = f'{int(fj[k]):,}'
    if os.path.exists(g('power_bound.csv')):
        pw = pd.read_csv(g('power_bound.csv'))
        bh = 'bound_adj'
        # **주장마다 따로 낸다.** 처음엔 표 전체에서 가장 조인 행을 뽑았는데,
        # 주장 셋이 한 표에 들어오면서 그 값이 어느 주장의 경계인지 모르게 됐다.
        for key, claim in (('', '미생물 축 부호일치'), ('agree.', '소스 간 방향 일치'),
                           ('auc.', '합병증 문헌 lift (AUC)')):
            c = pw[pw['claim'] == claim]
            if not len(c):
                continue
            # 귀무가 행마다 다르면 경계끼리 바로 비교할 수 없다 — **귀무 위
            # 초과분**이 가장 작은 행을 고른다 (§48).
            tight = c.loc[(c[bh] - c['null']).idxmin()]
            out[f'power.{key}rows'] = str(len(c))
            out[f'power.{key}n'] = f'{int(tight.n):,}'
            out[f'power.{key}mdes'] = f'{tight[bh]:.3f}'
            out[f'power.{key}obs'] = f'{tight["observed"]:.3f}'
            out[f'power.{key}null'] = f'{tight["null"]:.3f}'
            out[f'power.{key}over'] = str(int(c['above_bound'].sum()))
    if os.path.exists(g('foods.csv')):
        f = pd.read_csv(g('foods.csv'))
        out['foods.count'] = f'{len(f):,}'
        out['foods.median_compounds'] = str(int(f.n_compound.median()))
    if os.path.exists(g('compound_depression.csv')):
        E = pd.read_csv(g('compound_depression.csv'))
        out['E.compounds'] = f'{len(E):,}'
        out['E.nonzero'] = f'{int((E.e_shrunk != 0).sum()):,}'
    nmp = os.path.join(BASE, 'setup', 'nutrient_kegg_map.csv')
    if os.path.exists(nmp):
        out['F.compounds'] = str(pd.read_csv(nmp).nutrient_kegg.nunique())
    if os.path.exists(g('recommendation.csv')):
        out['rec.rows'] = f'{len(pd.read_csv(g("recommendation.csv"))):,}'
    if os.path.exists(g('microbe_disease_agreement.csv')):
        a = pd.read_csv(g('microbe_disease_agreement.csv'))
        out['agree.pairs'] = f'{len(a):,}'
        out['agree.agreed'] = f'{int((a.status == "agreed").sum()):,}'
        out['agree.conflict'] = f'{int((a.status == "conflict").sum()):,}'
    out.update(_facts_repro())
    return out


def _facts_repro():
    """**역설계 트랙**(룬트 `analyse/`)에서 읽는 사실.

    그족에는 자동 게이트가 0 개였다. `tools/scorecard.py` 가 상황을 보고하지만
    불변식 검사가 없어서 `PROBLEMS.md` 의 수치를 사람이 손으로 대조해야
    했다. 무거운 재계산 없이 **코미트된 산출물에서 읽을 수 있는 것**만
    사실로 둔다. Spearman 처럼 `tools/paper.py` 를 돌려야 나오는 것은
    여기 없다 — 그것까지 넣으면 검사가 몇 분짜리가 되어 코미트 훅에 못
    들어간다.
    """
    import json
    import pandas as pd
    A = os.path.join(BASE, 'analyse')
    out = {}
    if not os.path.isdir(A):
        return out
    g = lambda n: os.path.join(A, n)
    if os.path.exists(g('food.csv')):
        out['repro.foods'] = str(len(pd.read_csv(g('food.csv'))))
    if os.path.exists(g('foodname.csv')):
        fn = pd.read_csv(g('foodname.csv'))
        out['repro.foodname_rows'] = str(len(fn))
        out['repro.foodname_cols'] = str(fn.shape[1])
    if os.path.exists(g('paper85_compounds.csv')):
        out['repro.compounds'] = str(len(pd.read_csv(g('paper85_compounds.csv'))))
    if os.path.exists(g('paper_eval_table5.csv')):
        t5 = pd.read_csv(g('paper_eval_table5.csv'))
        out['repro.table5_n'] = str(len(t5))
        out['repro.table5_reproduced'] = str(int(t5.reproduced.fillna(False).sum()))
    sq = g('paper_sparql_summary.json')
    if os.path.exists(sq):
        d = json.load(open(sq))
        for k, name in (('table2', 'repro.table2'), ('table3', 'repro.table3'),
                        ('table4_raw', 'repro.table4'),
                        ('t5_complication', 'repro.t5_complication'),
                        ('t5_diet', 'repro.t5_diet')):
            if k in d:
                out[name] = str(d[k])
    return out


# 앵커를 검사할 문서. **루트 문서도 넣는다** — ourkg 수치를 인용하는데 범위에서
# 빠져 있었고, 실제로 `3,443,484`(현재 3,443,485)가 남아 있었다. 앵커를 39 자리에
# 달아 두고도 **범위를 정할 때 루트를 빼먹어** 같은 유형을 또 놓쳤다.
# 경로는 `HERE`(ourkg) 기준이다.
DOCS = ('README.md', 'DATA.md', 'METHODS.md', 'PROCESS.md',
        '../README.md', '../PROBLEMS.md', '../REPRODUCTION.md')
# `RESULTS.md` 는 **일부러 뺀다.** 시간순 기록이라 옛 절의 수치는 **그때 값이
# 맞다** — 앵커를 달면 현재 값으로 맞추라고 요구하게 되어 기록을 망친다.
# (잊어서 빠진 것과 구분하려고 적어 둔다. 현재 값을 말하는 자리는 README·DATA·
# METHODS 이고 그쪽에 앵커가 있다.)
DOCS_EXCLUDED = ('RESULTS.md',)
# 앵커 **바로 앞**의 숫자만 집는다. 사이에 허용하는 것은 `**` 와 공백뿐이다 —
# 넉넉하게 두면 표에서 앞 칸 숫자를 집는다(`| 1 | 1,192 | 46,495<!--...-->` 에서
# 1,192 를 집었다). 좁게 두고 못 집으면 앵커를 옮기는 쪽이 맞다.
# 이름은 **느슨하게** 받는다(`[^\s>]+`). 못 보는 이름이 생기는 사고를
# 세 번 당했다 — 처음 `[a-z_.]+` 는 대변자를(`chk:F.compounds`), 그 다은
# `[A-Za-z_.]+` 는 숫자를(`chk:repro.t5_diet`) 못 봤다. 틀린 이름은
# "모르는 앨커" 로 잡힐니 클래스를 정교하게 만드는 것이 아니다.
_ANCHOR = re.compile(r'([0-9][0-9,]*(?:\.[0-9]+)?)\**<!--\s*chk:([^\s>]+?)\s*-->')
# **형식이 안 맞는 앵커를 조용히 넘기지 않는다.** 처음 판은 이름을 `[a-z_.]+` 로
# 받아 `chk:F.compounds` · `chk:E.nonzero` 같은 대문자 앵커를 **아예 못 봤다**.
# 그런데도 "앵커 15 개 통과" 라고 보고했다 — 검사가 있는 척만 한 것이다.
# 그래서 `<!--chk:` 가 있는데 위 패턴에 안 걸리는 자리를 따로 세어 FAIL 한다.
_ANCHOR_ANY = re.compile(r'<!--\s*chk:[^>]*-->')


def check_docs():
    """문서의 `<!--chk:이름-->` 앵커 수치가 산출물과 맞는지.

    앵커가 하나도 없으면 아직 안 달았다는 뜻이므로 SKIP 이 아니라 **FAIL** 이다
    — 조용히 통과하면 검사가 있는 척만 한다.
    """
    fx = facts()
    if not fx:
        return _say('SKIP', '문서 수치', '산출물이 없다')
    seen, bad, unknown, malformed = 0, [], [], []
    for fn in DOCS:
        p = os.path.join(HERE, fn)
        if not os.path.exists(p):
            continue
        txt = open(p, encoding='utf-8').read()
        # **코드 표기 안의 앵커는 설명용이다.** 이 장치를 설명하는 문서가
        # `<!--chk:이름-->` 을 예시로 쓰는데, 그걸 실제 앵커로 세면 "형식이 안
        # 맞는다" 고 스스로를 잡는다. 펜스 블록과 인라인 코드를 먼저 지운다.
        txt = re.sub(r'```.*?```', '', txt, flags=re.S)
        txt = re.sub(r'`[^`\n]*`', '', txt)
        n_any = len(_ANCHOR_ANY.findall(txt))
        n_ok = len(_ANCHOR.findall(txt))
        if n_any != n_ok:
            malformed.append(f'{fn}: {n_any - n_ok} 개가 형식에 안 맞는다 '
                             f'(숫자가 앵커 바로 앞에 있어야 한다)')
        for num, name in _ANCHOR.findall(txt):
            seen += 1
            if name not in fx:
                unknown.append(f'{fn}:{name}')
            elif num != fx[name]:
                bad.append(f'{fn}:{name} 문서 {num} vs 산출물 {fx[name]}')
    msg = []
    if bad:
        msg.append('; '.join(bad[:4]) + (f' 외 {len(bad)-4}' if len(bad) > 4 else ''))
    if unknown:
        msg.append(f'모르는 앵커 {unknown[:3]}')
    if malformed:
        msg.append('; '.join(malformed))
    if not seen:
        msg.append('앵커가 하나도 없다 — 문서에 <!--chk:이름--> 를 달아야 한다')
    _say('FAIL' if msg else 'PASS', '문서 수치 앵커',
         '; '.join(msg) if msg else
         f'앵커 {seen} 개가 산출물과 맞는다 (계산 가능한 사실 {len(fx)} 개)')

    # **목차는 손으로 두면 낡는다.** `RESULTS.md` 가 63 개 절 6,100 줄인데
    # 목차가 없어 넣었다 — 그 목차가 절과 어긋나면 없는 것보다 나쁘다.
    rp = os.path.join(HERE, 'RESULTS.md')
    if os.path.exists(rp):
        txt = open(rp, encoding='utf-8').read()
        heads = [h.strip() for h in re.findall(r'^## (.+)$', txt, re.M)]
        toc = re.findall(r'^- \*\*§?([\w—]+)\*\*', txt, re.M)
        want = [(re.match(r'^(\d+[a-z]?)\.', h).group(1)
                 if re.match(r'^\d+[a-z]?\.', h) else '—') for h in heads]
        bad = ([] if toc == want else
               [f'목차 {len(toc)} vs 절 {len(want)}'] if len(toc) != len(want) else
               [f'{a} != {b}' for a, b in zip(toc, want) if a != b][:4])
        _say('FAIL' if bad else 'PASS', 'RESULTS 목차',
             '; '.join(bad) if bad else f'목차가 절 {len(want)} 개와 일치한다')


CHECKS = {'schema': check_schema, 'microbe': check_microbe, 'links': check_links,
          'agreement': check_agreement, 'registry': check_registry,
          'deadcode': check_deadcode, 'outputs': check_outputs,
          'units': check_units,
          'emode': check_emode, 'env': check_env, 'recommend': check_recommend,
          'pathcheck': check_pathcheck, 'kg': check_kg,
          'provenance': check_provenance, 'hooks': check_hooks,
          'docs': check_docs}


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
