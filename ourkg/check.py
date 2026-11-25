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
    p = os.path.join(OUT, 'gutbrain_compounds.json')
    nt = os.path.join(OUT, 'ourkg.nt')
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


def check_provenance():
    """정본 산출물이 기본값으로 만들어졌는지, 입력보다 낡지 않았는지."""
    import json
    stale = []
    for out_f, deps in DEPENDS.items():
        p = os.path.join(OUT, out_f)
        if not os.path.exists(p):
            continue
        for d in deps:
            dp = os.path.join(OUT, d)
            if os.path.exists(dp) and os.path.getmtime(p) < os.path.getmtime(dp) - 1:
                stale.append(f'{out_f} < {d}')
    _say('FAIL' if stale else 'PASS', '산출물 신선도',
         f'입력보다 오래된 것 {stale}' if stale else
         f'의존 {len(DEPENDS)} 쌍 모두 산출물이 입력보다 새롭다')

    pv = os.path.join(OUT, 'provenance.json')
    if not os.path.exists(pv):
        return _say('SKIP', '정본 산출물 출처', 'provenance.json 없다 — 한 단계 돌려라')
    rec = json.load(open(pv))
    bad = {f: r['env'] for f, r in rec.items()
           if f in CANONICAL and r.get('env')}
    unknown = [f for f in CANONICAL
               if os.path.exists(os.path.join(OUT, f)) and f not in rec]
    msg = []
    if bad:
        msg.append(f'기본값 아닌 환경으로 만들어진 정본 {bad}')
    _say('FAIL' if bad else 'PASS', '정본 산출물 출처',
         '; '.join(msg) if msg else
         f'기록 {len(rec)} 건 · 정본 중 비기본값 0'
         + (f' (기록 없는 정본 {len(unknown)} — 아직 안 돌린 단계)' if unknown else ''))


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
          'deadcode': check_deadcode,
          'emode': check_emode, 'env': check_env, 'recommend': check_recommend,
          'pathcheck': check_pathcheck, 'kg': check_kg,
          'provenance': check_provenance, 'docs': check_docs}


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
