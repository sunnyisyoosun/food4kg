"""
진단 모음
===========
(구 diag_kg_relations / diag_menda_structure / diag_table3_signs / diag_q2_path /
 diag_compound_sign / diag_lipids / diag_unassigned / diag_gold_subsets /
 analyse_sausage / diag_density_gap / diag_nutrient_mapping 통합)

실행
    python3 tools/diag.py kg         KG 관계명·MENDA 구조·Table3 부호·Q2 경로
    python3 tools/diag.py signs      compound 부호가 논문 순위와 어긋나는 곳
    python3 tools/diag.py lipids     지질 39종의 부호 근거 추적
    python3 tools/diag.py unassigned 방향 미확보 compound 에 쓰지 않은 근거가 있는가
    python3 tools/diag.py data       측정 밀도 격차 · KEGG 매핑 커버리지
    python3 tools/diag.py food <이름> 특정 food 점수를 compound 단위로 분해
    python3 tools/diag.py menda_jsonld    MENDA_Depression.jsonld 구조 전수 조사
    python3 tools/diag.py menda_orig      MENDA 원본으로 KG pos/neg 목록 역산
    python3 tools/diag.py menda_rule      MENDA 원본 집계 규칙 16종 vs 논문 부호
    python3 tools/diag.py promenda_types  ProMENDA Type1~5 의미 역추론
    python3 tools/diag.py supplements [검색어]  Supplements.docx 본문 추출 (기본 SPARQL)
    python3 tools/diag.py all             kg·signs·lipids·unassigned·data
"""
import collections
import json
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment

import core

K = core.K


# ------------------------------------------------------------------
def kg():
    """KG 관계명과 MENDA 구조, Table 3 부호 재현, Q2 경로 병목."""
    print('[관계명]')
    for fname in ('Disease_Bacteria.jsonld', 'MENDA_Depression.jsonld',
                  'KEGG_Compound_Bacteria.jsonld', 'Mental_health.jsonld'):
        path = os.path.join(core.FKG, fname)
        if not os.path.exists(path):
            continue
        c = collections.Counter()
        for entry in json.load(open(path)):
            for node in entry.get('@graph', []):
                for key in node:
                    if not key.startswith('@'):
                        c[key.rsplit('#', 1)[-1].rsplit('/', 1)[-1]] += 1
        top = ', '.join(f'{k}={v}' for k, v in c.most_common(4))
        print(f'  {fname:32s} {top}')
    print('  ※ Disease_Bacteria 에는 hasAssociation 만 있다. 논문 Query 2 의')
    print('     hasPositiveAssociation(세균) 구분이 공개본에 없어 재현 불가.')

    pos, neg = core.menda_sets()
    print()
    print(f'[MENDA 구조] 주어 = mesh/D003865 (Depressive Disorder)')
    print(f'  hasPositiveAssociation {len(pos)}종 / '
          f'hasNegativeAssociation {len(neg)}종 / 양쪽 {len(pos & neg)}종')

    PAPER = [
        ('C00025', '+', 'Glutamic acid', 'Table 3'),
        ('C00037', '+', 'Glycine', 'Table 3'),
        ('C00158', '+', 'Citric acid', 'Table 3'),
        ('C00072', '+', 'Ascorbic acid', 'Table 3'),
        ('C00188', '-', 'L-Threonine', 'Table 3'),
        ('C00114', '-', 'Choline', 'Table 3'),
        ('C00864', '+', 'Pantothenic acid', 'Table 4'),
        ('C00047', '+', 'Lysine', 'Table 4'),
        ('C00031', '+', 'D-Glucose', 'Fig 5'),
        ('C00089', '+', 'Sucrose', 'Fig 5'),
        ('C01496', '+', 'Fructose', 'Fig 5'),
        ('C06424', '-', 'Tetradecanoic acid', 'Fig 5'),
        ('C06429', '-', 'Docosahexaenoic acid', 'Fig 5'),
    ]
    print()
    print('[논문이 부호를 명시한 compound 의 MENDA 소속]')
    dec = ok = 0
    for kegg, sign, name, ref in PAPER:
        inp, inn = kegg in pos, kegg in neg
        where = ('both' if inp and inn else 'pos' if inp
                 else 'neg' if inn else '없음')
        mark = ''
        if where in ('pos', 'neg'):
            dec += 1
            ours = '+' if where == 'pos' else '-'
            ok += (ours == sign)
            mark = 'O' if ours == sign else 'X'
        print(f'  {kegg:8s} {name:22s} 논문={sign}  MENDA={where:>5s}  '
              f'{ref:8s} {mark}')
    print(f'  -> 한쪽에만 속해 판정 가능한 것 {dec}/{len(PAPER)}, 그중 일치 {ok}')
    print('  ★ 공개 MENDA 에는 방향 정보가 사실상 없다. 이것이 재현 실패의 근원.')

    print()
    print('[Q2 세균 경로 병목]')
    bac2dis, bac2cmp = {}, {}
    for entry in json.load(open(os.path.join(core.FKG,
                                             'Disease_Bacteria.jsonld'))):
        for node in entry.get('@graph', []):
            nid = node.get('@id', '')
            if not nid.startswith('http://nlp_microbe'):
                continue
            for key, vals in node.items():
                if 'hasAssociation' in key:
                    for v in (vals if isinstance(vals, list) else [vals]):
                        if isinstance(v, dict) and '@id' in v:
                            bac2dis.setdefault(nid, set()).add(v['@id'])
    for entry in json.load(open(os.path.join(
            core.FKG, 'KEGG_Compound_Bacteria.jsonld'))):
        for node in entry.get('@graph', []):
            nid = node.get('@id', '')
            for key, vals in node.items():
                if 'hasMetabolites' in key:
                    for v in (vals if isinstance(vals, list) else [vals]):
                        if isinstance(v, dict) and '@id' in v:
                            cid = v['@id'].rsplit('/', 1)[-1]
                            if cid.startswith('C'):
                                bac2cmp.setdefault(nid, set()).add(cid)
    p85 = core.paper85()
    alias_of = {}
    for c in p85.kegg:
        for k in core.kegg_alias.incidence_keys(c):
            alias_of[k] = c
    reach = {alias_of[c] for cs in bac2cmp.values() for c in cs
             if c in alias_of}
    print(f'  Disease_Bacteria 세균 {len(bac2dis)} / '
          f'KEGG_Compound_Bacteria 세균 {len(bac2cmp)} / '
          f'교집합 {len(set(bac2dis) & set(bac2cmp))}')
    print(f'  85종 중 KEGG_Compound_Bacteria 에 등장: {len(reach)}종 '
          f'(상한). 지질 대부분이 없다.')


# ------------------------------------------------------------------
def _ref_table(d):
    """compound 별 '논문 순위 기준 방향' (진단용. E 로 쓰면 순환)."""
    idx, rank, _, _, _ = core.paper_ranking(d.names)
    ref = {}
    for j, c in enumerate(d.cols):
        v = d.Xn[idx, j]
        ref[c] = (np.nan if np.count_nonzero(v) < 8
                  else -stats.spearmanr(v, rank).statistic)
    return ref


def signs():
    """어떤 compound 부호가 논문 순위와 어긋나는가."""
    d = core.Data.load()
    p85 = core.paper85()
    grp = dict(zip(p85.kegg, p85.group))
    nm = dict(zip(p85.kegg, p85['name']))
    ref = _ref_table(d)
    E = d.signs()

    rows = [(c, grp.get(c, '?'), E[c], ref[c]) for c in d.cols]
    ok = [r for r in rows if not np.isnan(r[3])]
    signed = [r for r in ok if r[2] != 0]
    agree = sum(1 for r in signed if np.sign(r[2]) == np.sign(r[3]))
    print(f'  부호 부여 {len(signed)}종 중 논문 순위와 방향 일치 {agree} '
          f'({agree / max(len(signed), 1) * 100:.0f}%)')
    print()
    print(f'  {"group":24s} {"ref평균":>8s} {"+":>4s} {"-":>4s} {"0":>4s}')
    for g in sorted(set(grp.values())):
        sub = [r for r in rows if r[1] == g]
        rr = np.nanmean([r[3] for r in sub])
        print(f'  {g:24s} {rr:+8.3f} '
              f'{sum(1 for r in sub if r[2] > 0):4d} '
              f'{sum(1 for r in sub if r[2] < 0):4d} '
              f'{sum(1 for r in sub if r[2] == 0):4d}')
    print()
    print('  부호가 어긋난 compound (|ref| 큰 순 12)')
    bad = sorted((r for r in signed if np.sign(r[2]) != np.sign(r[3])),
                 key=lambda r: -abs(r[3]))[:12]
    for c, g, e, rr in bad:
        print(f'    {c}  {str(nm.get(c))[:24]:25s} {g[:20]:21s} '
              f'우리={e:+d}  ref={rr:+.3f}')


def lipids():
    """지질 39종의 부호 근거 추적."""
    d = core.Data.load()
    p85 = core.paper85()
    nm = dict(zip(p85.kegg, p85['name']))
    src = core.sources()
    mpos, mneg = core.menda_sets()
    PM = core.promenda()
    ref = _ref_table(d)
    E = d.signs()

    out = []
    for c in p85[p85.group == 'Lipids'].kegg:
        ks = set(core.kegg_alias.incidence_keys(c))
        menda = ('both' if (ks & mpos and ks & mneg) else
                 'pos' if ks & mpos else 'neg' if ks & mneg else '-')
        hit = core.lookup(PM, c)
        if hit:
            a, b = hit
            t = a + b
            pmtxt, mar = f'{a}:{b}', (abs(a - b) / t if t else 0.0)
        else:
            pmtxt, mar = '-', np.nan
        out.append((ref.get(c, np.nan), c, E[c], menda, pmtxt, mar,
                    src.get(c, '?').split('(')[0][:22]))
    out.sort(key=lambda r: (np.isnan(r[0]), r[0]))

    print(f'  {"KEGG":7s} {"compound":23s} {"우리":>4s} {"ref":>7s} '
          f'{"MENDA":>6s} {"ProMENDA":>9s} {"margin":>7s}  source')
    bad = 0
    for rr, c, e, menda, pmtxt, mar, s in out:
        flag = ' '
        if not np.isnan(rr) and e != 0 and np.sign(e) != np.sign(rr):
            flag, bad = '!', bad + 1
        print(f'  {c:7s} {str(nm.get(c))[:22]:23s} {e:+4d} '
              f'{(f"{rr:+.3f}" if not np.isnan(rr) else "   -  "):>7s} '
              f'{menda:>6s} {pmtxt:>9s} '
              f'{(f"{mar:.3f}" if not np.isnan(mar) else "  -  "):>7s} {flag} {s}')
    print(f'  -> 논문 순위와 어긋남 {bad}종')
    print('  ※ 아미노산과 달리 ProMENDA 가 강한 마진으로 + 를 지지한다.')
    print('     기본값 문제가 아니라 근거와 논문의 실질적 충돌이다.')


def unassigned():
    """E=0 인 compound 에 아직 쓰지 않은 근거가 있는가."""
    d = core.Data.load()
    p85 = core.paper85()
    nm = dict(zip(p85.kegg, p85['name']))
    grp = dict(zip(p85.kegg, p85.group))
    SUBSETS = {
        '전체': None,
        'Faece': ('M_Tissue_Metabolite_level_1', 'Faece'),
        'Gut': ('M_Tissue_Metabolite_level_2', 'Gut'),
        'Human': ('M_Organism_Metabolite_level_2', 'Human'),
    }
    TAB = {k: core.promenda(v) for k, v in SUBSETS.items()}
    E = d.signs()
    zeros = [c for c in d.cols if E[c] == 0]
    print(f'  E=0 인 compound {len(zeros)}종 / {len(d.cols)}')
    print()
    hdr = f'  {"KEGG":8s} {"compound":22s} {"group":14s}'
    for s in SUBSETS:
        hdr += f' {s:>11s}'
    print(hdr)
    nodata = []
    gain = {s: 0 for s in SUBSETS}
    for c in zeros:
        line = f'  {c:8s} {str(nm.get(c))[:21]:22s} {str(grp.get(c))[:13]:14s}'
        any_data = False
        for s in SUBSETS:
            dd, cnt = core.direction(TAB[s], c)
            if cnt != '-':
                any_data = True
            if dd:
                gain[s] += 1
            sym = '+' if dd > 0 else ('-' if dd < 0 else '.')
            line += f' {sym}{cnt:>10s}'
        if not any_data:
            nodata.append(c)
        print(line)
    print()
    print(f'  어떤 소스에도 데이터가 없는 것: {len(nodata)}종 -> {nodata}')
    print(f'  부분집합이 방향을 줄 수 있는 수: '
          + ', '.join(f'{s}={gain[s]}' for s in SUBSETS))
    print('  ※ Faece 는 gold 9종에서 1:2 수준 표본으로 대부분 틀린다. 쓰지 않는다.')
    print('     (검증: 이 파일의 gold_subsets 출력 참고)')

    print()
    print('  [gold 9종의 부분집합별 값]')
    print(f'  {"KEGG":8s} {"compound":22s} {"논문":>4s} {"현재":>4s}'
          + ''.join(f' {s:>10s}' for s in SUBSETS))
    for kg_, (sign, name, ref) in core.gold.GOLD.items():
        cur = core.gold.direction(d.w, kg_) or '-'
        line = f'  {kg_:8s} {name[:21]:22s} {sign:>4s} {cur:>4s}'
        for s in SUBSETS:
            hit = core.lookup(TAB[s], kg_)
            line += f' {(f"{hit[0]}:{hit[1]}" if hit else "-"):>10s}'
        print(line)


# ------------------------------------------------------------------
def data():
    """측정 밀도 격차와 KEGG 매핑 커버리지."""
    d = core.Data.load()
    B, kegg, cname, cgrp = core.heatmap()
    assert d.cols == kegg, '열 순서 불일치'

    def nrm(A):
        n = np.linalg.norm(A, axis=1, keepdims=True)
        n[n == 0] = 1
        return A / n

    C = nrm(B) @ nrm(d.Xn).T
    r, c = linear_sum_assignment(-C)
    conf = [(int(a), int(b)) for a, b, s in zip(r, c, C[r, c]) if s > 0.9]
    pb = np.array([(B[a] != 0).sum() for a, _ in conf])
    ob = np.array([(d.Xn[b] != 0).sum() for _, b in conf])
    nz = (d.X != 0).sum(1)
    nzp = (B != 0).sum(1)

    print('[측정 밀도]  85종 중 값이 있는 compound 수')
    print(f'  {"":10s} {"논문":>8s} {"우리":>8s}')
    for lab, a, b in (('중앙값', np.median(nzp), np.median(nz)),
                      ('평균', nzp.mean(), nz.mean()),
                      ('최대', nzp.max(), nz.max())):
        print(f'  {lab:10s} {a:8.1f} {b:8.1f}')
    print(f'  5개 이하   {int((nzp <= 5).sum()):8d} {int((nz <= 5).sum()):8d}')
    print()
    print(f'[같은 음식끼리]  신뢰 매칭(cos>0.9) {len(conf)}쌍')
    print(f'  논문 중앙값 {np.median(pb):.0f} vs 우리 {np.median(ob):.0f}  '
          f'(차이 중앙값 {np.median(ob - pb):+.0f})')

    miss = np.zeros(len(d.cols), dtype=int)
    have = np.zeros(len(d.cols), dtype=int)
    for a, b in conf:
        pm_ = B[a] != 0
        om = d.Xn[b] != 0
        miss += (pm_ & ~om).astype(int)
        have += pm_.astype(int)
    gm = {}
    for j, cc in enumerate(d.cols):
        g = cgrp.get(cc, '?')
        gm.setdefault(g, [0, 0])
        gm[g][0] += miss[j]
        gm[g][1] += have[j]
    print()
    print('  그룹별 결손률 (논문엔 있고 우리엔 없음)')
    for g, (m, h) in sorted(gm.items(), key=lambda x: -x[1][0] / max(x[1][1], 1)):
        print(f'    {g:24s} {m:5d}/{h:<5d}  {m / max(h, 1) * 100:5.1f}%')

    print()
    print('[KEGG 매핑 커버리지]')
    nutr = pd.read_csv(os.path.join(core.BASE, 'fdc_raw/nutrient.csv'),
                       low_memory=False)
    mp = pd.read_csv(os.path.join(core.BASE, 'setup/nutrient_kegg_map.csv'))
    fn = pd.read_csv(os.path.join(core.BASE, 'food_nutrient.csv'),
                     low_memory=False, usecols=['nutrient_id', 'nutrient_kegg'])
    print(f'  fdc_raw/nutrient.csv {len(nutr)}종 정의 / '
          f'매핑표 {len(mp)}행 / 데이터 등장 {fn.nutrient_id.nunique()}종')
    unknown = sorted(set(fn.nutrient_id) - set(mp['nutrient_id']))
    print(f'  매핑표가 모르는 영양소 {len(unknown)}종')
    kk = fn['nutrient_kegg'].astype(str).str.startswith('C')
    present = set(fn.loc[kk, 'nutrient_kegg'].unique())
    absent = [c for c in d.cols
              if c not in present
              and not (set(core.kegg_alias.incidence_keys(c)) & present)]
    print(f'  85종 중 food_nutrient.csv 에 한 번도 없는 것: {absent}')
    print('  ※ 매핑 커버리지는 병목이 아니다. 밀도 격차는 FDC 에 그 음식의')
    print('     해당 영양소 측정 항목이 없어서 생긴다.')


# ------------------------------------------------------------------
def food(pattern=None):
    """특정 food 의 점수를 compound 단위로 분해."""
    d = core.Data.load()
    p85 = core.paper85()
    nm = dict(zip(p85.kegg, p85['name']))
    grp = dict(zip(p85.kegg, p85.group))
    p = d.score()
    order = np.argsort(-p)
    rank = {i: r + 1 for r, i in enumerate(order)}

    if pattern:
        sel = [i for i in range(len(d.names))
               if pattern.lower() in d.names[i].lower()]
    else:  # 기본: 카테고리별 평균 기여
        sel = []
    if pattern and not sel:
        print(f'  "{pattern}" 에 맞는 food 없음')
        return

    if sel:
        for i in sel[:5]:
            u = float(d.Xn[i] @ d.E)
            print(f'  [{d.names[i][:60]}]  순위 {rank[i]}/{len(d.names)}  '
                  f'p={p[i]:.3f}  u={u:.3f}')
            contrib = d.Xn[i] * d.E
            for j in np.argsort(-np.abs(contrib))[:8]:
                if contrib[j] == 0:
                    break
                print(f'      {contrib[j]:+7.3f}  {d.cols[j]} '
                      f'{str(nm.get(d.cols[j]))[:24]:25s} {grp.get(d.cols[j])}')
            print()
    else:
        print('  카테고리별 u 기여 (그룹 단위)')
        cats = sorted(set(d.Y))
        print(f'  {"category":14s} ' + ''.join(
            f'{g[:11]:>12s}' for g in sorted(set(grp.values()))))
        for t in cats:
            rows = [i for i in range(len(d.Xn)) if d.Y[i] == t]
            line = f'  {core.CAT.get(t, str(t))[:13]:14s} '
            for g in sorted(set(grp.values())):
                jj = [j for j, c in enumerate(d.cols) if grp.get(c) == g]
                line += f'{(d.Xn[rows][:, jj] * d.E[jj]).sum(1).mean():12.3f}'
            print(line)


def menda_jsonld():
    """MENDA_Depression.jsonld 전수 조사
    ===================================
    지금까지 이 파일에서 pos/neg 두 목록만 읽었다. 그 외에 E 를 보완할
    정보가 있는지 구조를 끝까지 훑는다.
    
      - 모든 키와 값 타입
      - 노드 종류와 개수
      - 85종 중 이 파일에 등장하는 것 / E=0 인 것과의 교집합
    """
    PATH = os.path.join(core.BASE, 'foodkg_triply/MENDA_Depression.jsonld')
    data = json.load(open(PATH))

    print(f'최상위 타입: {type(data).__name__}, 길이 {len(data)}')
    for i, entry in enumerate(data):
        print(f'  entry[{i}] 키: {list(entry.keys())}, @graph 노드 {len(entry.get("@graph", []))}')

    # 모든 키 수집
    keys = collections.Counter()
    valtypes = collections.Counter()
    nodes = []
    for entry in data:
        for node in entry.get('@graph', []):
            nodes.append(node)
            for k, v in node.items():
                short = k.rsplit('#', 1)[-1].rsplit('/', 1)[-1]
                keys[short] += 1
                vv = v if isinstance(v, list) else [v]
                for x in vv:
                    if isinstance(x, dict):
                        valtypes[f'{short}: ' + ('@id' if '@id' in x else
                                                 '@value' if '@value' in x
                                                 else str(list(x)))] += 1
                    else:
                        valtypes[f'{short}: {type(x).__name__}'] += 1

    print()
    print('모든 키:')
    for k, v in keys.most_common():
        print(f'  {k:26s} {v:6d}')
    print()
    print('키별 값 형태:')
    for k, v in valtypes.most_common(12):
        print(f'  {k:40s} {v:6d}')

    # 노드 종류
    print()
    subj = collections.Counter()
    for n in nodes:
        nid = str(n.get('@id', ''))
        if 'kegg' in nid.lower():
            subj['KEGG compound'] += 1
        elif 'mesh' in nid.lower():
            subj['MeSH disease'] += 1
        elif nid.startswith('_:'):
            subj['blank node'] += 1
        else:
            subj[nid.split('/')[2] if nid.count('/') > 2 else nid[:40]] += 1
    print('노드 주어 종류:')
    for k, v in subj.most_common():
        print(f'  {k:40s} {v:6d}')

    # 샘플 노드 (compound 쪽)
    print()
    print('compound 노드 샘플 2개:')
    shown = 0
    for n in nodes:
        if 'kegg' in str(n.get('@id', '')).lower():
            print(f'  {json.dumps(n, ensure_ascii=False)[:400]}')
            shown += 1
            if shown >= 2:
                break

    # 85종 커버리지
    pos, neg = core.menda_sets()
    in_file = set()
    for n in nodes:
        nid = str(n.get('@id', ''))
        cid = nid.rsplit('/', 1)[-1]
        if cid.startswith('C') and cid[1:].isdigit():
            in_file.add(cid)

    d = core.Data.load()
    E = d.signs()
    zeros = [c for c in d.cols if E[c] == 0]
    q = pd.read_csv(os.path.join(core.OUT, 'knowledge_query_results.csv'))
    src = dict(zip(q['compound'], q['source'].astype(str)))

    def keys_of(c):
        return set(core.kegg_alias.incidence_keys(c))

    cov = [c for c in d.cols if keys_of(c) & in_file]
    zc = [c for c in zeros if keys_of(c) & in_file]
    print()
    print('=' * 70)
    print(f'파일에 등장하는 KEGG compound: {len(in_file)}')
    print(f'  pos 목록 {len(pos)} / neg 목록 {len(neg)} / 양쪽 {len(pos & neg)}')
    print(f'논문 85종 중 파일에 있는 것: {len(cov)}')
    print(f'E=0 인 {len(zeros)}종 중 파일에 있는 것: {len(zc)}')
    print()
    if zc:
        p85 = core.paper85()
        nm = dict(zip(p85.kegg, p85['name']))
        print('E=0 인데 파일에 있는 compound — 왜 방향을 못 정했나')
        for c in zc:
            ks = keys_of(c)
            w = ('both' if (ks & pos and ks & neg) else
                 'pos' if ks & pos else 'neg' if ks & neg else '목록에 없음')
            print(f'  {c}  {str(nm.get(c))[:24]:25s} MENDA={w:12s} src={src.get(c, "?")[:24]}')
    print()
    print('E=0 인데 파일에 아예 없는 것:', [c for c in zeros if c not in zc])


def menda_orig():
    """MENDA 원본으로 논문의 pos/neg 목록을 역산할 수 있는가
    ========================================================
    `menda.xlsx` 는 MENDA 원본(5,675 entries / 464 studies).
    논문 §3.1 이 인용한 바로 그 데이터다.
    
    공개된 `foodkg_triply/MENDA_Depression.jsonld` 는 Depression -> compound 목록
    두 개(pos 378 / neg 399)로만 남아 있어 방향을 유도할 수 없었다(§12).
    MENDA 원본에서 그 두 목록을 재현하는 집계 규칙을 찾으면 E 를 복원할 수 있다.
    """
    XLSX = os.path.join(core.BASE, 'menda.xlsx')

    m = pd.read_excel(XLSX, sheet_name='Metabolite')
    REG = [c for c in m.columns if 'regulat' in c.lower()]
    print(f'Metabolite 시트 {m.shape}')
    print(f'방향 컬럼: {REG}')
    if not REG:
        print('열 전체:', list(m.columns))
        sys.exit('방향 컬럼을 찾지 못했다')
    reg_col = REG[0]
    print()
    print('방향 값 분포:')
    print(m[reg_col].value_counts(dropna=False).to_string())

    m['k'] = m['KEGG'].astype(str).str.extract(r'(C\d{5})')[0]
    print()
    print(f'KEGG ID 있는 행: {m["k"].notna().sum():,} / {len(m):,}')
    print(f'고유 KEGG compound: {m["k"].nunique():,}')

    r = m[reg_col].astype(str).str.strip().str.lower()
    m['up'] = r.str.startswith(('up', 'increas', 'higher'))
    m['down'] = r.str.startswith(('down', 'decreas', 'lower'))

    sub = m.dropna(subset=['k'])
    pos_any = set(sub.loc[sub['down'], 'k'])   # down = 결핍 = 논문의 positive(완화) 가정
    neg_any = set(sub.loc[sub['up'], 'k'])
    up_any = set(sub.loc[sub['up'], 'k'])
    down_any = set(sub.loc[sub['down'], 'k'])

    print()
    print('=' * 70)
    print('논문 KG 의 목록과 대조')
    print('=' * 70)
    kg_pos, kg_neg = core.menda_sets()
    print(f'  KG(jsonld)   pos {len(kg_pos)}  neg {len(kg_neg)}  양쪽 {len(kg_pos & kg_neg)}')
    print(f'  MENDA 원본   down {len(down_any)}  up {len(up_any)}  양쪽 {len(down_any & up_any)}')
    print()

    cands = {
        'down->pos / up->neg': (down_any, up_any),
        'up->pos / down->neg': (up_any, down_any),
    }
    for name, (p_, n_) in cands.items():
        jp = len(p_ & kg_pos) / max(len(p_ | kg_pos), 1)
        jn = len(n_ & kg_neg) / max(len(n_ | kg_neg), 1)
        print(f'  {name:24s} pos 일치 {len(p_ & kg_pos):3d}/{len(kg_pos)} (Jaccard {jp:.3f})'
              f'   neg 일치 {len(n_ & kg_neg):3d}/{len(kg_neg)} (Jaccard {jn:.3f})')

    print()
    print('=' * 70)
    print('논문이 부호를 명시한 compound — MENDA 원본은 무엇을 말하는가')
    print('=' * 70)
    GOLD_EXT = [
        ('C00025', '+', 'Glutamic acid', 'Table 3'),
        ('C00037', '+', 'Glycine', 'Table 3'),
        ('C00072', '+', 'Ascorbic acid', 'Table 3'),
        ('C00188', '-', 'L-Threonine', 'Table 3'),
        ('C00114', '-', 'Choline', 'Table 3'),
        ('C00864', '+', 'Pantothenic acid', 'Table 4'),
        ('C00031', '+', 'D-Glucose', 'Fig 5'),
        ('C00089', '+', 'Sucrose', 'Fig 5'),
        ('C01496', '+', 'Fructose', 'Fig 5'),
        ('C06424', '-', 'Tetradecanoic acid', 'Fig 5'),
        ('C06429', '-', 'Docosahexaenoic acid', 'Fig 5'),
        ('C00253', '+', 'Nicotinic acid', 'Table 5'),
    ]
    cnt = sub.groupby('k').agg(up=('up', 'sum'), down=('down', 'sum'))
    print(f"  {'KEGG':8s} {'compound':22s} {'논문':>4s} {'MENDA down:up':>14s} {'다수결':>6s} {'출처':10s} 판정")
    ok = tot = 0
    for kegg, sign, nm, ref in GOLD_EXT:
        hit = None
        for k in core.kegg_alias.incidence_keys(kegg):
            if k in cnt.index:
                hit = cnt.loc[k]
                break
        if hit is None:
            print(f'  {kegg:8s} {nm:22s} {sign:>4s} {"없음":>14s} {"-":>6s} {ref:10s} -')
            continue
        d, u = int(hit['down']), int(hit['up'])
        maj = '+' if d > u else ('-' if u > d else '0')
        tot += 1
        good = maj == sign
        ok += good
        print(f'  {kegg:8s} {nm:22s} {sign:>4s} {f"{d}:{u}":>14s} {maj:>6s} {ref:10s} '
              f'{"O" if good else "X"}')
    print(f'  -> down=+ 다수결 기준 일치 {ok}/{tot}')


def menda_rule():
    """논문이 MENDA 의 'both' compound 를 어떻게 처리했는가 — 규칙 역산
    =================================================================
    KG 목록은 pos 378 / neg 399 / 양쪽 267 이라 'both' 가 70% 다.
    논문은 Table 3 / Table 4 / Fig. 5 에서 부호를 명시했으니, MENDA 원본의
    study 단위 데이터에 어떤 집계 규칙을 적용해야 그 부호가 나오는지 찾는다.
    
    기준: 논문이 부호를 명시한 compound 12종.
    """
    XLSX = os.path.join(core.BASE, 'menda.xlsx')
    m = pd.read_excel(XLSX, sheet_name='Metabolite')
    st = pd.read_excel(XLSX, sheet_name='Study')

    m['k'] = m['KEGG'].astype(str).str.extract(r'(C\d{5})')[0]
    r = m['Up/Down_regulated '].astype(str).str.strip().str.lower()
    # 논문 극성: hasPositiveAssociation = Up -> E = +1 (논문 §4.2.1 을 따름)
    m['inc'] = np.where(r.str.startswith(('up', 'increas', 'higher')), 1,
                        np.where(r.str.startswith(('down', 'decreas', 'lower')),
                                 -1, 0))
    m = m.dropna(subset=['k'])
    m = m[m['inc'] != 0]

    # study 메타 붙이기
    st_small = st[['Study_ID', 'Sample_size', 'PMID', 'Citation']].copy()


    def year_of(c):
        s = str(c)
        y = re.findall(r'(19|20)\d{2}', s)
        return int(s[s.find(y[0][:2]):][:4]) if y else np.nan


    st_small['year'] = st_small['Citation'].map(year_of)


    def size_of(v):
        n = re.findall(r'\d+', str(v))
        return sum(int(x) for x in n[:2]) if n else np.nan


    st_small['n'] = st_small['Sample_size'].map(size_of)
    m = m.merge(st_small, on='Study_ID', how='left')

    GOLD = [
        ('C00025', 1, 'Glutamic acid', 'Table 3'),
        ('C00037', 1, 'Glycine', 'Table 3'),
        ('C00072', 1, 'Ascorbic acid', 'Table 3'),
        ('C00188', -1, 'L-Threonine', 'Table 3'),
        ('C00114', -1, 'Choline', 'Table 3'),
        ('C00864', 1, 'Pantothenic acid', 'Table 4'),
        ('C00047', 1, 'Lysine', 'Table 4'),
        ('C00031', 1, 'D-Glucose', 'Fig 5'),
        ('C00089', 1, 'Sucrose', 'Fig 5'),
        ('C01496', 1, 'Fructose', 'Fig 5'),
        ('C06424', -1, 'Tetradecanoic acid', 'Fig 5'),
        ('C06429', -1, 'Docosahexaenoic acid', 'Fig 5'),
        ('C00253', 1, 'Nicotinic acid', 'Table 5'),
    ]

    T1 = 'Study_type_Metabolite_level'
    TIS1 = 'Tissue_Metabolite_level_1'
    TIS2 = 'Tissue_Metabolite_level_2'
    TIS3 = 'Tissue_Metabolite_level_3'
    ORG = 'Organism_Metabolite_level_2'


    def subset(name):
        if name == '전체':
            return m
        if name.startswith('Type'):
            return m[m[T1].astype(str) == name]
        if name == 'Human':
            return m[m[ORG].astype(str) == 'Human']
        if name == 'Animal':
            return m[m[ORG].astype(str) != 'Human']
        if name in ('Central', 'Peripheral'):
            return m[m[TIS3].astype(str) == name]
        if name in ('Blood', 'Brain', 'Faece', 'Urine'):
            return m[m[TIS2].astype(str) == name]
        return m


    RULES = {}
    for sub in ('전체', 'Type1', 'Type2', 'Human', 'Animal',
                'Central', 'Peripheral', 'Blood', 'Brain', 'Faece', 'Urine'):
        RULES[f'다수결 [{sub}]'] = ('majority', sub)
    RULES['any-up -> +1 [전체]'] = ('any_up', '전체')
    RULES['any-down -> -1 [전체]'] = ('any_down', '전체')
    RULES['표본수 가중 [전체]'] = ('weighted', '전체')
    RULES['최신 연구 [전체]'] = ('latest', '전체')
    RULES['최대 표본 연구 [전체]'] = ('biggest', '전체')


    def decide(kind, sub, kegg):
        d = subset(sub)
        keys = core.kegg_alias.incidence_keys(kegg)
        g = d[d['k'].isin(keys)]
        if g.empty:
            return 0
        if kind == 'majority':
            return int(np.sign(g['inc'].sum()))
        if kind == 'any_up':
            return 1 if (g['inc'] == 1).any() else -1
        if kind == 'any_down':
            return -1 if (g['inc'] == -1).any() else 1
        if kind == 'weighted':
            w = g['n'].fillna(1.0)
            return int(np.sign((g['inc'] * w).sum()))
        if kind == 'latest':
            gg = g.dropna(subset=['year'])
            if gg.empty:
                return 0
            return int(np.sign(gg.loc[gg['year'] == gg['year'].max(), 'inc'].sum()))
        if kind == 'biggest':
            gg = g.dropna(subset=['n'])
            if gg.empty:
                return 0
            return int(np.sign(gg.loc[gg['n'] == gg['n'].max(), 'inc'].sum()))
        return 0


    rows = []
    for name, (kind, sub) in RULES.items():
        ok = cov = 0
        detail = []
        for kegg, sign, nm, ref in GOLD:
            got = decide(kind, sub, kegg)
            if got != 0:
                cov += 1
                ok += (got == sign)
            detail.append('O' if got == sign else ('.' if got == 0 else 'X'))
        rows.append((ok, cov, name, ''.join(detail)))

    rows.sort(reverse=True)
    print(f'논문이 부호를 명시한 {len(GOLD)}종 기준')
    print(f"{'규칙':26s} {'일치':>6s} {'판정가능':>8s}  패턴 (O맞음 X틀림 .데이터없음)")
    print('-' * 78)
    for ok, cov, name, det in rows:
        print(f'{name:26s} {ok:3d}/{cov:<3d} {cov:8d}  {det}')

    print()
    print('compound 순서:', ' '.join(k for k, _, _, _ in GOLD))
    print()
    best = rows[0]
    print(f'최고: {best[2]}  {best[0]}/{best[1]}')
    print()
    print('※ 어떤 규칙도 12종을 다 맞히지 못하면, 논문의 E 는 MENDA 집계가 아니다.')


def promenda_types():
    """ProMENDA 의 Type1~Type5 가 무엇인가
    =====================================
    weight.csv 의 type1 / type2 소스는 ProMENDA 의
    M_Study_type_Metabolite_level 값에서 온다. 논문(Food4healthKG)은 이
    구분의 의미를 적지 않았다. 시트와 데이터 특성에서 역으로 알아낸다.
    """
    XLSX = core.PROMENDA_XLSX

    pd.set_option('display.width', 200)
    x = pd.ExcelFile(XLSX)
    print('시트:', x.sheet_names)
    print()

    for sheet in x.sheet_names:
        df = x.parse(sheet, nrows=3)
        print(f'--- {sheet}  열: {list(df.columns)}')
    print()

    m = x.parse('M_Metabolite')
    TC = 'M_Study_type_Metabolite_level'
    print('=' * 74)
    print('Type 별 특성 — 어떤 연구 설계인지 역추론')
    print('=' * 74)
    print(m[TC].value_counts().to_string())
    print()

    for col, label in (
            ('M_Groups', '비교 그룹'),
            ('M_Organism_Metabolite_level_2', '생물종'),
            ('M_Tissue_Metabolite_level_3', '조직(중추/말초)'),
            ('M_Tissue_Metabolite_level_2', '조직'),
            ('M_Categories_of_depression_Metabolite_level_1', '우울증 분류'),
            ('M_Platform_Metabolite_level', '측정 플랫폼')):
        if col not in m.columns:
            continue
        print(f'--- {label} ({col})')
        ct = pd.crosstab(m[TC], m[col])
        # 각 Type 에서 비중이 큰 상위 5개만
        for t in sorted(m[TC].dropna().unique()):
            if t not in ct.index:
                continue
            row = ct.loc[t].sort_values(ascending=False)
            tot = row.sum()
            top = ', '.join(f'{k}={v}({v/tot*100:.0f}%)' for k, v in row.head(4).items()
                            if v > 0)
            print(f'    {t}: {top}')
        print()


def supplements(arg=None):
    """Supplements.docx에서 SPARQL 쿼리 전문을 뽑는다.
    """
    import zipfile
    path = os.path.join(core.BASE, 'Food4healthKG/Supplements.docx')

    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf8')
    txt = re.sub(r'<[^>]+>', '\n', xml)
    lines = [l.strip() for l in txt.split('\n') if l.strip()]

    start = arg or 'SPARQL'
    n = 120

    hits = [i for i, l in enumerate(lines) if start.lower() in l.lower()]
    if not hits:
        print(f'"{start}" 없음')
        return
    i = hits[-1]
    for l in lines[i:i + n]:
        print(' ', l[:130])


FUNCS = {'kg': kg, 'signs': signs, 'lipids': lipids,
         'unassigned': unassigned, 'data': data, 'food': food,
         'menda_jsonld': menda_jsonld, 'menda_orig': menda_orig,
         'menda_rule': menda_rule, 'promenda_types': promenda_types,
         'supplements': supplements}
# 'all' 은 빠른 진단만. MENDA/ProMENDA 원본 조사와 보충자료 추출은 이름으로 부른다.
ALL = ['kg', 'signs', 'lipids', 'unassigned', 'data']

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    for k in (ALL if which == 'all' else [which]):
        if k not in FUNCS:
            sys.exit(f'알 수 없는 항목: {k}\n가능: {", ".join(FUNCS)}, all')
        print(f'=== {k} ===')
        FUNCS[k](arg) if k in ('food', 'supplements') else FUNCS[k]()
        print()
