"""ourkg 구축 — 논문 §3 (데이터 통합 · 엔티티 링킹 · 지식 표현).

네 단계를 한 파일에 둔다. 각 단계는 앞 단계의 CSV 만 읽으므로 따로 돌려도 된다.

    python3 ourkg/build.py            # 네 단계 전부
    python3 ourkg/build.py kg         # 한 단계만
    python3 ourkg/build.py promenda microbe

  food      최신 FDC → food x KEGG compound 중량 행렬 F (g/100 g)   [논문 §3.1·3.2]
  promenda  ProMENDA → compound x depression 관계 행렬 E            [논문 §3.1]
  microbe   NCBI taxonomy · KEGG · MeSH 로 미생물 축 최신화          [논문 §3.1]
  kg        위 셋을 논문 §3.3 표현 규약대로 RDF 로 출력              [논문 §3.3]

산출물은 모두 ourkg/out/ 아래. 네트워크로 받은 것은 ourkg/cache/ 에 캐시한다.
"""

import os
import pandas as pd
import re
import json
import time
import collections
import urllib.parse
import requests
import csv
import hashlib

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BASE, OUT, FDC_RAW, UNIT_TO_G, FDC_CATEGORY,
                    normalize_label, normalize_category, kegg_map)


def food():
    """01 — 최신 FDC 원본 → food x KEGG compound 중량 행렬 F (g / 100 g).

    논문 §3.1(FDC 통합) · §3.2(라벨 정규화·exact matching 병합)를 따르되,
    논문이 고정한 135 food / 85 compound 목록을 쓰지 않고 FDC 전체에서 만든다.

    출력
      out/food_compound_long.csv  food_key, kegg, amount_g
      out/foods.csv               food_key, fdc_id, food_name, data_type, category, n_compound
    """
    MIN_COV = int(os.environ.get('MIN_COV', '20'))   # 음식당 최소 측정 compound 수
    CHUNK = 2_000_000

    print('[1/5] nutrient -> KEGG 매핑표')
    mp = kegg_map()
    nid2kegg = dict(zip(mp['nutrient_id'], mp['nutrient_kegg']))
    nid2unit = dict(zip(mp['nutrient_id'], mp['nutrient_unit']))
    nid2name = dict(zip(mp['nutrient_id'], mp['nutrient_name']))
    print(f'  nutrient {len(nid2kegg)} -> KEGG compound {mp["nutrient_kegg"].nunique()}')

    print('[2/5] food.csv')
    food = pd.read_csv(os.path.join(FDC_RAW, 'food.csv'), low_memory=False,
                       usecols=['fdc_id', 'data_type', 'description', 'food_category_id'])
    print(f'  {len(food):,} 행')
    cat_num = pd.to_numeric(food['food_category_id'], errors='coerce')
    food['category'] = cat_num.map(FDC_CATEGORY)
    food.loc[food['category'].isna(), 'category'] = food['food_category_id'].where(
        cat_num.isna(), None)
    food['category'] = food['category'].fillna('Unknown')

    # FNDDS(survey_fndds_food)는 food.csv 에 food_category_id 가 없다. 카테고리는
    # survey_fndds_food.csv 의 wweia_category_number 에 있다 (FDC survey 배포본).
    # 이것을 붙이지 않으면 FNDDS 음식 545종이 전부 Unclassified 가 되고, 그 안에
    # 칵테일류가 몰려 있어 추천 카테고리 분포가 왜곡된다.
    _sf = os.path.join(FDC_RAW, 'survey_fndds_food.csv')
    _wc = os.path.join(FDC_RAW, 'wweia_food_category.csv')
    if os.path.exists(_sf) and os.path.exists(_wc):
        sf = pd.read_csv(_sf, usecols=['fdc_id', 'wweia_category_number'])
        wc = pd.read_csv(_wc)
        wmap = dict(zip(wc['wweia_food_category'], wc['wweia_food_category_description']))
        sf['wweia'] = sf['wweia_category_number'].map(wmap)
        food = food.merge(sf[['fdc_id', 'wweia']], on='fdc_id', how='left')
        hit = food['wweia'].notna() & (food['category'] == 'Unknown')
        food.loc[hit, 'category'] = food.loc[hit, 'wweia']
        print(f'  FNDDS WWEIA 카테고리 적용: {int(hit.sum()):,} 항목')
    else:
        print('  ⚠ survey_fndds_food.csv / wweia_food_category.csv 없음 — '
              'FNDDS 음식은 이름 규칙으로만 분류된다')

    food = food.rename(columns={'description': 'food_name'})

    print(f'[3/5] food_nutrient.csv 스트리밍 (KEGG 매핑 행만, 단위 g 환산)')
    keep = set(nid2kegg)
    parts = []
    rows = 0
    for ch in pd.read_csv(os.path.join(FDC_RAW, 'food_nutrient.csv'), chunksize=CHUNK,
                          usecols=['fdc_id', 'nutrient_id', 'amount'], low_memory=False):
        rows += len(ch)
        ch = ch[ch['nutrient_id'].isin(keep)]
        if len(ch):
            parts.append(ch)
        print(f'\r  읽음 {rows:,} / 보관 {sum(len(p) for p in parts):,}', end='', flush=True)
    print()
    fn = pd.concat(parts, ignore_index=True)
    del parts
    fn['kegg'] = fn['nutrient_id'].map(nid2kegg)
    fn['unit'] = fn['nutrient_id'].map(nid2unit)
    fn['amount_g'] = pd.to_numeric(fn['amount'], errors='coerce') * fn['unit'].map(UNIT_TO_G).fillna(1.0)
    fn = fn.dropna(subset=['amount_g'])
    print(f'  KEGG 측정값 {len(fn):,} 행, compound {fn["kegg"].nunique()}')

    print('[4/5] 라벨 병합 (논문 §3.2 exact matching)')
    fn = fn.merge(food[['fdc_id', 'food_name', 'data_type', 'category']], on='fdc_id', how='inner')
    fn['food_key'] = normalize_label(fn['food_name'])
    fn = fn[fn['food_key'].str.len() > 0]
    print(f'  FDC 항목 {fn["fdc_id"].nunique():,} -> 병합 음식 {fn["food_key"].nunique():,}')

    print(f'[5/5] 음식당 compound >= {MIN_COV} 필터')
    long = (fn.groupby(['food_key', 'kegg'], as_index=False)['amount_g'].mean())
    cov = long.groupby('food_key')['kegg'].nunique()
    keep_food = set(cov[cov >= MIN_COV].index)
    long = long[long['food_key'].isin(keep_food)]

    # 대표 항목은 큐레이션 수준이 높은 데이터셋 순으로 고른다.
    _PRIORITY = {'foundation_food': 0, 'sr_legacy_food': 1, 'survey_fndds_food': 2,
                 'sample_food': 3, 'sub_sample_food': 4, 'market_acquistion': 5,
                 'agricultural_acquisition': 6, 'experimental_food': 7, 'branded_food': 8}
    _sel = fn[fn['food_key'].isin(keep_food)].copy()
    _sel['_prio'] = _sel['data_type'].map(_PRIORITY).fillna(9)
    meta = (_sel.sort_values('_prio')
            .groupby('food_key')
            .agg(fdc_id=('fdc_id', 'first'), food_name=('food_name', 'first'),
                 data_type=('data_type', 'first'), category=('category', 'first')))
    meta['n_compound'] = cov.reindex(meta.index).astype(int)
    meta = meta.reset_index()
    meta['food_group'] = [normalize_category(c, n)
                          for c, n in zip(meta['category'], meta['food_name'])]

    long.to_csv(os.path.join(OUT, 'food_compound_long.csv'), index=False)
    meta.to_csv(os.path.join(OUT, 'foods.csv'), index=False)
    print(f'  음식 {len(meta):,} / compound {long["kegg"].nunique()} / 값 {len(long):,}')
    print(f'  음식당 compound 중앙값 {meta["n_compound"].median():.1f} '
          f'(논문 heatmap 원본 33.0)')
    print('  카테고리 상위:')
    print(meta['food_group'].value_counts().head(12).to_string())
    print(f"  Unclassified {int((meta['food_group'] == 'Unclassified').sum()):,}")


def promenda():
    """02 — ProMENDA → compound x depression 관계 행렬 E.

    논문 §3.1 은 MENDA(2020) 의 depression-metabolite 5,675 관계를 썼다.
    여기서는 그 후속판 ProMENDA(Pu et al. 2024) 전체를 쓴다.

    극성 규약 — 논문 §4.2.1 "a value of 1 indicates a positive relationship between
    a compound and depression (relieving the disease)". 재현 파이프라인
    (map_promenda.py, PROBLEMS.md §7)에서 확정한 규약을 그대로 가져온다.
      Type1 (우울증 vs 대조군): up in depression = +1
      Type2/4 (치료·반응 비교)  : up = 치료로 증가  = -1 로 이미 대응
      Type3/5                   : 설계가 대응되지 않아 집계에서 제외하지 않고
                                  다수결에만 참여 (재현판과 동일)

    출력
      out/compound_depression.csv  kegg, direction, pos, neg, n_study, n_record
      out/promenda_records.csv     kegg, study_id, incidence, study_type, tissue, organism
    """
    SRC = os.path.join(BASE, '41398_2024_2948_MOESM3_ESM.xlsx')
    STYPE_COL = 'M_Study_type_Metabolite_level'
    REG_COL = 'M_Up/Down_regulated '

    UP = {'up', 'upregulated', 'up-regulated', 'increased', 'increase', 'higher'}
    DOWN = {'down', 'downregulated', 'down-regulated', 'decreased', 'decrease', 'lower'}

    print('[1/3] ProMENDA 로드')
    df = pd.read_excel(SRC, sheet_name='M_Metabolite')
    print(f'  {len(df):,} 행 / metabolite {df["M_Metabolite_ID"].nunique():,} '
          f'/ study {df["M_Study_ID"].nunique():,}')

    print('[2/3] KEGG 추출 + 극성')
    df = df[df['M_KEGG'].astype(str).str.contains(r'C\d{5}', na=False)].copy()
    df['kegg'] = df['M_KEGG'].astype(str).str.extract(r'(C\d{5})')[0]


    def incidence(v):
        v = str(v).lower().strip()
        if v in UP:
            return -1          # 기본 해석: 우울증에서 증가 = 악화
        if v in DOWN:
            return +1
        return 0


    df['incidence'] = df[REG_COL].apply(incidence)
    is_t1 = df[STYPE_COL].astype(str) == 'Type1'
    df.loc[is_t1, 'incidence'] *= -1      # 논문 규약: Type1 은 up = +1
    print(f'  KEGG 보유 {len(df):,} 행 / compound {df["kegg"].nunique():,}')
    print(f'  Type1 반전 {int(is_t1.sum()):,} 행')
    print(f'  +1 {int((df.incidence == 1).sum()):,} / -1 {int((df.incidence == -1).sum()):,} '
          f'/ 0 {int((df.incidence == 0).sum()):,}')

    print('[3/3] compound 별 다수결')
    g = df.groupby('kegg')
    rows = []
    for kegg, sub in g:
        pos = int((sub['incidence'] == 1).sum())
        neg = int((sub['incidence'] == -1).sum())
        direction = 1 if pos > neg else (-1 if neg > pos else 0)
        rows.append({'kegg': kegg, 'name': sub['M_Metabolite_name'].iloc[0],
                     'direction': direction, 'pos': pos, 'neg': neg,
                     'n_study': sub['M_Study_ID'].nunique(), 'n_record': len(sub)})
    E = pd.DataFrame(rows).sort_values('n_record', ascending=False).reset_index(drop=True)

    # 근거 강도 — ProMENDA 는 논문이 쓴 MENDA 보다 훨씬 크고(compound 1,412),
    # 연구 2~3건짜리 compound 까지 들어온다. 논문의 85 compound 는 큐레이션된
    # 목록이라 이 문제가 없었지만, 전체를 쓰면 근거가 얕은 compound 가 다수결에서
    # ±1 을 똑같이 받는다(예: Ethanol 4:1, 연구 3건).
    #
    #  e_binary  : 논문 §4.2.1 그대로의 +1 / -1 / 0
    #  e_shrunk  : (pos-neg)/(pos+neg+K) — 사전 설정한 유사계수 K 로 0 쪽으로 축소.
    #              근거가 쌓이면 ±1 에 가까워지고 얕으면 0 에 가깝다.
    #  q         : pos:neg 에 대한 이항검정 양측 p 의 BH 보정값(근거 유의성)
    from scipy.stats import binomtest

    SHRINK_K = int(os.environ.get('SHRINK_K', '10'))
    E['e_binary'] = E['direction']
    E['e_shrunk'] = (E['pos'] - E['neg']) / (E['pos'] + E['neg'] + SHRINK_K)
    pv = [binomtest(int(r.pos), int(r.pos + r.neg)).pvalue if (r.pos + r.neg) > 0 else 1.0
          for r in E.itertuples()]
    E['p'] = pv
    _o = pd.Series(pv).rank(method='first').astype(int).values
    _srt = sorted(range(len(pv)), key=lambda i: pv[i])
    _q = [0.0] * len(pv)
    _prev = 1.0
    for rank, i in enumerate(reversed(_srt), 1):
        _prev = min(_prev, pv[i] * len(pv) / (len(pv) - rank + 1))
        _q[i] = _prev
    E['q'] = _q
    E.to_csv(os.path.join(OUT, 'compound_depression.csv'), index=False)
    print(f'  근거 축소 K={SHRINK_K}: |e_shrunk| 중앙값 {E.e_shrunk.abs().median():.3f}, '
          f'BH q<0.05 {int((E.q < 0.05).sum())} compound')

    cols = ['kegg', 'M_Study_ID', 'incidence', STYPE_COL,
            'M_Tissue_Metabolite_level_1', 'M_Organism_Metabolite_level_1']
    df[cols].rename(columns={'M_Study_ID': 'study_id', STYPE_COL: 'study_type',
                             'M_Tissue_Metabolite_level_1': 'tissue',
                             'M_Organism_Metabolite_level_1': 'organism'}
                    ).to_csv(os.path.join(OUT, 'promenda_records.csv'), index=False)

    print(f'  compound {len(E):,}  (+ {int((E.direction == 1).sum())} / '
          f'- {int((E.direction == -1).sum())} / tie {int((E.direction == 0).sum())})')

    food = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    fk = set(food['kegg'].unique())
    ov = fk & set(E[E.direction != 0]['kegg'])
    print(f'  FDC compound {len(fk)} 중 depression 방향 확정 {len(ov)} '
          f'(논문 E: 85 중 공개 소스로 69)')


def microbe():
    """03 — 미생물 축 최신화: NCBI taxonomy + KEGG.

    논문 §3.1 은 (a) NCBI taxonomy 322,917 미생물, (b) KEGG 230 metabolite,
    (c) MiKG 1,234 미생물-정신질환 관계를 썼다.

    여기서는
      미생물 - 정신질환 : Food4healthKG 배포본 Disease_Bacteria (MiKG 유래) 에서
                          taxid - MeSH 쌍을 뽑고, MeSH SPARQL 로 tree number 를
                          지금 받아 F03(Mental Disorders) 여부를 판정한다.
      미생물 이름/계통   : NCBI efetch 로 현재 학명·rank·lineage 로 갱신.
      compound - 미생물  : KEGG REST 로 지금 다시 계산한다.
                          compound -> enzyme(EC) -> KO -> organism.

    출력 (모두 out/)
      microbe_disease.csv       taxid, name, mesh_id, disease, tree_numbers, is_mental
      microbes.csv              taxid, name(NCBI 현재), rank, lineage, kegg_org
      compound_microbe.csv      kegg, taxid, kegg_org, n_ko   (hasMetabolites)
    캐시: ourkg/cache/
    """
    CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
    os.makedirs(CACHE, exist_ok=True)
    S = requests.Session()
    S.headers['User-Agent'] = 'ourkg/1.0 (food4health reproduction+extension)'


    def cached(name, fetch, ttl_days=30):
        p = os.path.join(CACHE, name)
        if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < ttl_days * 86400:
            return open(p, encoding='utf-8').read()
        txt = fetch()
        open(p, 'w', encoding='utf-8').write(txt)
        return txt


    def kegg(path):
        def f():
            r = S.get(f'https://rest.kegg.jp/{path}', timeout=180)
            r.raise_for_status()
            time.sleep(0.34)
            return r.text
        return cached('kegg_' + path.replace('/', '_') + '.txt', f)


    # ------------------------------------------------------------------
    print('[1/5] Disease_Bacteria → taxid - MeSH 쌍')
    HA = 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#hasAssociation'
    LAB = 'http://www.w3.org/2000/01/rdf-schema#label'
    graph = json.load(open(os.path.join(BASE, 'foodkg_triply', 'Disease_Bacteria.jsonld'),
                           encoding='utf-8'))[0]['@graph']
    labels = {n['@id']: n[LAB][0]['@value'] for n in graph if LAB in n}
    pairs = []
    for n in graph:
        if HA not in n:
            continue
        m = re.search(r'/entity/(\d+)$', n['@id'])
        if not m:
            continue
        for o in n[HA]:
            d = o['@id'].rsplit('/', 1)[-1]
            if d.startswith('D'):
                pairs.append((m.group(1), d))
    pairs = sorted(set(pairs))
    taxids = sorted({t for t, _ in pairs})
    meshids = sorted({d for _, d in pairs})
    print(f'  관계 {len(pairs):,} / 미생물 {len(taxids):,} / 질환 {len(meshids):,}')

    # ------------------------------------------------------------------
    print('[2/5] MeSH tree number (id.nlm.nih.gov SPARQL) → F03 판정')


    def fetch_tree():
        out = {}
        for i in range(0, len(meshids), 60):
            chunk = meshids[i:i + 60]
            values = ' '.join(f'mesh:{d}' for d in chunk)
            q = ('PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#> '
                 'PREFIX mesh: <http://id.nlm.nih.gov/mesh/> '
                 f'SELECT ?d ?tn WHERE {{ VALUES ?d {{ {values} }} '
                 '?d meshv:treeNumber ?tn }')
            r = S.get('https://id.nlm.nih.gov/mesh/sparql',
                      params={'query': q, 'format': 'JSON', 'limit': 5000}, timeout=120)
            r.raise_for_status()
            for b in r.json()['results']['bindings']:
                d = b['d']['value'].rsplit('/', 1)[-1]
                out.setdefault(d, []).append(b['tn']['value'].rsplit('/', 1)[-1])
            time.sleep(0.5)
            print(f'\r  {min(i+60, len(meshids))}/{len(meshids)}', end='', flush=True)
        print()
        return json.dumps(out)


    tree = json.loads(cached('mesh_tree.json', fetch_tree))
    mental = {d for d, tns in tree.items() if any(t.startswith('F03') for t in tns)}
    neuro = {d for d, tns in tree.items()
             if any(t.startswith('C10.574') or t.startswith('C10.228.140') for t in tns)}
    print(f'  tree number 확보 {len(tree)}/{len(meshids)} / F03 정신질환 {len(mental)} '
          f'/ 신경퇴행 등 {len(neuro)}')

    md = pd.DataFrame(pairs, columns=['taxid', 'mesh_id'])
    md['disease'] = md['mesh_id'].map(lambda d: labels.get(f'http://id.nlm.nih.gov/mesh/{d}', ''))
    md['tree_numbers'] = md['mesh_id'].map(lambda d: ';'.join(tree.get(d, [])))
    md['is_mental'] = md['mesh_id'].isin(mental)
    md['is_neuro'] = md['mesh_id'].isin(neuro)
    print(f'  정신질환 관계 {int(md.is_mental.sum()):,} '
          f'(미생물 {md[md.is_mental].taxid.nunique()} 종, 질환 {md[md.is_mental].mesh_id.nunique()} 종)')
    for d, n in md[md.is_mental].disease.value_counts().head(12).items():
        print(f'     {n:4d}  {d}')

    # ------------------------------------------------------------------
    print('[3/5] NCBI taxonomy 로 학명·계통 갱신')
    focus = sorted(set(md[md.is_mental | md.is_neuro]['taxid']))
    print(f'  대상 {len(focus)} 종 (정신질환·신경퇴행 연관 미생물)')


    def fetch_tax():
        recs = {}
        for i in range(0, len(focus), 200):
            chunk = focus[i:i + 200]
            r = S.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
                      params={'db': 'taxonomy', 'id': ','.join(chunk), 'retmode': 'xml'},
                      timeout=120)
            r.raise_for_status()
            import xml.etree.ElementTree as ET
            for tx in ET.fromstring(r.text).findall('Taxon'):
                recs[tx.findtext('TaxId')] = {
                    'name': tx.findtext('ScientificName'),
                    'rank': tx.findtext('Rank'),
                    'lineage': tx.findtext('Lineage') or '',
                }
            time.sleep(0.4)
            print(f'\r  {min(i+200, len(focus))}/{len(focus)}', end='', flush=True)
        print()
        return json.dumps(recs)


    tax = json.loads(cached('ncbi_taxonomy.json', fetch_tax))
    print(f'  갱신된 taxon {len(tax)}')

    # ------------------------------------------------------------------
    print('[4/5] KEGG organism 매칭')
    # KEGG 는 list/organism 을 내렸다(400). list/genome 형식: "T00202\tbfr; Bacteroides fragilis YCH46"
    org_txt = kegg('list/genome')
    orgs = []
    for line in org_txt.strip().split('\n'):
        f = line.split('\t')
        if len(f) < 2 or '; ' not in f[1]:
            continue
        code, name = f[1].split('; ', 1)
        orgs.append({'tnum': f[0], 'org': code.strip(), 'name': name.strip()})
    print(f'  KEGG organism {len(orgs):,}')
    by_species = collections.defaultdict(list)
    for o in orgs:
        sp = ' '.join(re.sub(r'\(.*?\)', '', o['name']).split()[:2]).lower()
        by_species[sp].append(o['org'])

    tax_org = {}
    for t, rec in tax.items():
        sp = ' '.join(rec['name'].split()[:2]).lower()
        if sp in by_species:
            tax_org[t] = by_species[sp][0]
    print(f'  KEGG organism 코드 연결 {len(tax_org)}/{len(tax)}')

    micro = pd.DataFrame([{'taxid': t, **rec, 'kegg_org': tax_org.get(t, '')}
                          for t, rec in tax.items()])
    micro.to_csv(os.path.join(OUT, 'microbes.csv'), index=False)
    md.to_csv(os.path.join(OUT, 'microbe_disease.csv'), index=False)

    # ------------------------------------------------------------------
    print('[5/5] KEGG compound → EC → KO → organism')
    cpds = set(pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))['kegg'].unique())

    c2ec = collections.defaultdict(set)
    for line in kegg('link/enzyme/compound').strip().split('\n'):
        a, b = line.split('\t')
        c = a.split(':')[-1]
        if c in cpds:
            c2ec[c].add(b.split(':')[-1])
    print(f'  compound -> EC: {len(c2ec)} compound, {sum(len(v) for v in c2ec.values()):,} 링크')

    ec2ko = collections.defaultdict(set)
    for line in kegg('link/ko/enzyme').strip().split('\n'):
        a, b = line.split('\t')
        ec2ko[a.split(':')[-1]].add(b.split(':')[-1])

    c2ko = {c: {k for e in ecs for k in ec2ko.get(e, ())} for c, ecs in c2ec.items()}
    print(f'  compound -> KO: 중앙값 {pd.Series([len(v) for v in c2ko.values()]).median():.0f}')

    rows = []
    orgcodes = sorted({v for v in tax_org.values() if v})
    for i, org in enumerate(orgcodes, 1):
        try:
            txt = kegg(f'link/ko/{org}')
        except Exception as e:
            print(f'\n  ! {org}: {e}')
            continue
        kos = {l.split('\t')[1].split(':')[-1] for l in txt.strip().split('\n') if '\t' in l}
        for t, o in tax_org.items():
            if o != org:
                continue
            for c, cko in c2ko.items():
                n = len(cko & kos)
                if n:
                    rows.append({'kegg': c, 'taxid': t, 'kegg_org': org, 'n_ko': n})
        print(f'\r  organism {i}/{len(orgcodes)}  링크 {len(rows):,}', end='', flush=True)
    print()
    cm = pd.DataFrame(rows)
    cm.to_csv(os.path.join(OUT, 'compound_microbe.csv'), index=False)
    print(f'  compound-미생물 {len(cm):,} 링크 / compound {cm["kegg"].nunique()} '
          f'/ 미생물 {cm["taxid"].nunique()}')


    # ------------------------------------------------------------------
    # 6. MiKG 원본 — 미생물 → 신경전달물질 → 정신질환 (gut-brain axis 경로)
    #
    # Disease_Bacteria 만으로는 정신질환 관계가 얇다(F03 6종, 우울증 1건).
    # MiKG(Liu et al. 2021) 원본은 미생물-신경전달물질 statement 와
    # 신경전달물질-정신질환 relationship 을 따로 두고, 둘을 이어야 논문이 말한
    # "미생물-정신질환" 관계가 나온다.
    # ------------------------------------------------------------------
    print('[6/6] MiKG 원본 — 미생물 → 신경전달물질 → 정신질환')
    from rdflib import Graph, URIRef

    MI = 'http://ztonebv.com/MiKG#'
    g = Graph()
    g.parse(os.path.join(BASE, 'MiKG-JAIMS', 'MiKG_Schema_Data_20201007.ttl'), format='turtle')


    def _p(n):
        return URIRef(MI + n)


    def _local(u):
        return str(u).split('#')[-1].replace('-', ' ')


    # 신경전달물질 → KEGG compound (KEGG 엔트리로 확인한 표준 ID)
    NT_KEGG = {'Dopamine': 'C03758', 'Serotonin': 'C00780', 'GABA': 'C00334',
               'Norepinephrine': 'C00547', 'Acetylcholine': 'C01996',
               'Glutamate': 'C00025', 'Histamine': 'C00388', 'Melatonin': 'C01598',
               'Epinephrine': 'C00788', 'Glycine': 'C00037'}

    mn = []
    for s, _, mic in g.triples((None, _p('hasGutMicrobiota'), None)):
        for nt in g.objects(s, _p('hasNeurotransmitter')):
            mods = [str(o) for o in g.objects(s, _p('hasModulation'))]
            pmids = [str(o).split('pmid')[-1] for o in g.objects(s, _p('hasReference'))]
            mn.append({'microbe': _local(mic), 'neurotransmitter': _local(nt),
                       'nt_kegg': NT_KEGG.get(_local(nt), ''),
                       'modulation': ';'.join(mods), 'pmids': ';'.join(pmids)})
    mn = pd.DataFrame(mn).drop_duplicates()

    nd = []
    for s, _, dis in g.triples((None, _p('hasMentalDisorder'), None)):
        for nt in g.objects(s, _p('hasNeurotransmitter')):
            pmids = [str(o).split('pmid')[-1] for o in g.objects(s, _p('hasReference'))]
            nd.append({'neurotransmitter': _local(nt), 'disease': _local(dis),
                       'nt_kegg': NT_KEGG.get(_local(nt), ''), 'pmids': ';'.join(pmids)})
    nd = pd.DataFrame(nd).drop_duplicates()

    mn.to_csv(os.path.join(OUT, 'microbe_neurotransmitter.csv'), index=False)
    nd.to_csv(os.path.join(OUT, 'neurotransmitter_disease.csv'), index=False)

    joined = mn.merge(nd[['neurotransmitter', 'disease']], on='neurotransmitter')
    joined[['microbe', 'neurotransmitter', 'disease']].drop_duplicates().to_csv(
        os.path.join(OUT, 'microbe_disease_mikg.csv'), index=False)
    print(f'  미생물-신경전달물질 {len(mn)} / 신경전달물질-정신질환 {len(nd)} '
          f'/ 이어 붙인 미생물-정신질환 {len(joined.drop_duplicates(["microbe", "disease"])):,}')
    print(f'  미생물 {mn.microbe.nunique()} 종 / 정신질환 {nd.disease.nunique()} 종 '
          f'/ KEGG 로 연결된 신경전달물질 {int((mn.nt_kegg != "").sum() > 0) and mn[mn.nt_kegg != ""].neurotransmitter.nunique()}')
    print('  정신질환:', ', '.join(sorted(nd.disease.unique())))


def kg():
    """04 — 앞 단계 산출물을 논문 §3.3 표현 규약대로 RDF 로 쓴다.

    논문 Fig.1/Fig.2 의 prefix 와 관계를 그대로 쓰되 네임스페이스만 우리 것으로 분기한다.
      npq:  http://nutrition.vu.nl/pop/qualifier#        (food 쪽 qualifier)
      mpq:  http://nlp_microbe.ccnu.edu.cn/pop/qualifier# (microbe 쪽 qualifier)
      our:  http://nutrition.vu.nl/ourkg/                 (우리 KG 고유 엔티티)

    관계 (논문 §3.3)
      self-defined : npq:hasNutrients, npq:hasNutrientWeights, mpq:hasMetabolites,
                     mpq:hasAssociation + hasPositiveAssociation/hasNegativeAssociation
      predefined   : rdf:type, rdfs:subClassOf, rdfs:label, owl:sameAs

    출력
      out/ourkg.nt        N-Triples
      out/kg_stats.csv    논문 Table 1 대응 통계 (source, relation, entity, triples)
    """
    NS = {
        'our': 'http://nutrition.vu.nl/ourkg/',
        'npq': 'http://nutrition.vu.nl/pop/qualifier#',
        'mpq': 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#',
        'ent': 'http://nutrition.vu.nl/entity#',
        'mic': 'http://nlp_microbe.ccnu.edu.cn/entity/',
        'kegg': 'https://www.kegg.jp/entry/',
        'mesh': 'http://id.nlm.nih.gov/mesh/',
        'mikg': 'http://ztonebv.com/MiKG#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
    }

    OUT_NT = os.path.join(OUT, 'ourkg.nt')
    stats = collections.defaultdict(lambda: {'triples': 0, 'relations': set(), 'entities': set()})


    def slug(s):
        return hashlib.md5(str(s).encode('utf-8')).hexdigest()[:12]


    def esc(s):
        return (str(s).replace('\\', '\\\\').replace('"', '\\"')
                .replace('\n', '\\n').replace('\r', ''))


    class Writer:
        def __init__(self, path):
            self.f = open(path, 'w', encoding='utf-8')
            self.n = 0

        def t(self, s, p, o, source, literal=False, dtype=None):
            obj = o if not literal else (
                f'"{esc(o)}"^^<{NS["xsd"]}{dtype}>' if dtype else f'"{esc(o)}"')
            if not literal:
                obj = f'<{o}>'
            self.f.write(f'<{s}> <{p}> {obj} .\n')
            self.n += 1
            st = stats[source]
            st['triples'] += 1
            st['relations'].add(p)
            st['entities'].add(s)
            if not literal:
                st['entities'].add(o)

        def close(self):
            self.f.close()


    W = Writer(OUT_NT)
    A = NS['rdf'] + 'type'
    LABEL = NS['rdfs'] + 'label'
    SUBCLASS = NS['rdfs'] + 'subClassOf'
    SAMEAS = NS['owl'] + 'sameAs'
    VALUE = NS['rdf'] + 'value'

    print('[1/5] Food · Category (FDC)')
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    food_uri = {k: NS['our'] + 'food/' + slug(k) for k in foods['food_key']}
    cat_uri = {}
    for _, r in foods.iterrows():
        u = food_uri[r['food_key']]
        W.t(u, A, NS['ent'] + 'Food', 'FoodData Central')
        W.t(u, LABEL, r['food_name'], 'FoodData Central', literal=True)
        W.t(u, NS['our'] + 'fdcId', str(r['fdc_id']), 'FoodData Central', literal=True)
        W.t(u, NS['our'] + 'dataType', r['data_type'], 'FoodData Central', literal=True)
        c = cat_uri.setdefault(r['food_group'], NS['our'] + 'category/' + slug(r['food_group']))
        W.t(u, SUBCLASS, c, 'FoodData Central')
    for name, u in cat_uri.items():
        W.t(u, A, NS['ent'] + 'FoodCategory', 'FoodData Central')
        W.t(u, LABEL, name, 'FoodData Central', literal=True)
    print(f'  음식 {len(foods):,} / 카테고리 {len(cat_uri)}')

    print('[2/5] Food → Nutrient 중량 (npq:hasNutrients / hasNutrientWeights)')
    for i, (fk, kegg, amt) in enumerate(long.itertuples(index=False), 1):
        fu = food_uri.get(fk)
        if fu is None:
            continue
        nu = f'{NS["our"]}weight/{slug(fk)}_{kegg}'
        cu = NS['kegg'] + kegg
        W.t(fu, NS['npq'] + 'hasNutrients', cu, 'FoodData Central')
        W.t(fu, NS['npq'] + 'hasNutrientWeights', nu, 'FoodData Central')
        W.t(nu, NS['npq'] + 'ofCompound', cu, 'FoodData Central')
        W.t(nu, VALUE, f'{amt:.10g}', 'FoodData Central', literal=True, dtype='double')
        if i % 200000 == 0:
            print(f'\r  {i:,}/{len(long):,}', end='', flush=True)
    print(f'\r  중량 triple {len(long)*4:,}')

    print('[3/5] Compound (KEGG) · depression 관계 (ProMENDA)')
    E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))
    DEPRESSION = NS['mesh'] + 'D003865'
    W.t(DEPRESSION, A, NS['ent'] + 'Disease', 'ProMENDA')
    W.t(DEPRESSION, LABEL, 'Major depressive disorder', 'ProMENDA', literal=True)
    food_cpds = set(long['kegg'].unique())
    for kegg in sorted(food_cpds):
        cu = NS['kegg'] + kegg
        W.t(cu, A, NS['ent'] + 'Compound', 'KEGG')
        W.t(cu, NS['our'] + 'keggId', kegg, 'KEGG', literal=True)
    n_rel = 0
    for _, r in E.iterrows():
        if r['direction'] == 0:
            continue
        cu = NS['kegg'] + r['kegg']
        rel = 'hasPositiveAssociation' if r['direction'] > 0 else 'hasNegativeAssociation'
        W.t(cu, NS['npq'] + rel, DEPRESSION, 'ProMENDA')
        W.t(cu, NS['npq'] + 'hasAssociation', DEPRESSION, 'ProMENDA')
        W.t(cu, LABEL, r['name'], 'ProMENDA', literal=True)
        W.t(cu, NS['our'] + 'nStudy', str(int(r['n_study'])), 'ProMENDA', literal=True)
        n_rel += 1
    print(f'  compound {len(food_cpds)} / depression 극성 관계 {n_rel}')

    print('[4/5] Microbe (NCBI) · compound-microbe (KEGG) · microbe-disease')
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str})
    for _, r in mic.iterrows():
        u = NS['mic'] + r['taxid']
        W.t(u, A, NS['ent'] + 'Microbe', 'NCBI taxonomy')
        W.t(u, LABEL, r['name'], 'NCBI taxonomy', literal=True)
        W.t(u, NS['our'] + 'rank', str(r['rank']), 'NCBI taxonomy', literal=True)
        W.t(u, NS['our'] + 'lineage', str(r['lineage']), 'NCBI taxonomy', literal=True)
        if isinstance(r['kegg_org'], str) and r['kegg_org']:
            W.t(u, SAMEAS, f'https://www.kegg.jp/entry/gn:{r["kegg_org"]}', 'NCBI taxonomy')

    cm = pd.read_csv(os.path.join(OUT, 'compound_microbe.csv'), dtype={'taxid': str})
    for _, r in cm.iterrows():
        W.t(NS['mic'] + r['taxid'], NS['mpq'] + 'hasMetabolites',
            NS['kegg'] + r['kegg'], 'KEGG')
    print(f'  미생물 {len(mic)} / compound-미생물 {len(cm):,}')

    md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})
    for _, r in md.iterrows():
        du = NS['mesh'] + r['mesh_id']
        W.t(NS['mic'] + r['taxid'], NS['mpq'] + 'hasAssociation', du, 'MiKG')
        W.t(du, A, NS['ent'] + 'Disease', 'MiKG')
        if isinstance(r['disease'], str):
            W.t(du, LABEL, r['disease'], 'MiKG', literal=True)
        if r['is_mental']:
            W.t(du, SUBCLASS, NS['ent'] + 'MentalDisorder', 'MeSH')
        for tn in str(r['tree_numbers']).split(';'):
            if tn and tn != 'nan':
                W.t(du, NS['our'] + 'meshTree', tn, 'MeSH', literal=True)

    print('[5/5] 신경전달물질 경로 (MiKG)')
    mn = pd.read_csv(os.path.join(OUT, 'microbe_neurotransmitter.csv'))
    nd = pd.read_csv(os.path.join(OUT, 'neurotransmitter_disease.csv'))
    for _, r in mn.iterrows():
        mu = NS['mikg'] + str(r['microbe']).replace(' ', '-')
        nu = NS['mikg'] + str(r['neurotransmitter']).replace(' ', '-')
        W.t(mu, A, NS['ent'] + 'Microbe', 'MiKG')
        W.t(mu, LABEL, r['microbe'], 'MiKG', literal=True)
        W.t(mu, NS['mpq'] + 'hasMetabolites', nu, 'MiKG')
        if isinstance(r['nt_kegg'], str) and r['nt_kegg']:
            W.t(nu, SAMEAS, NS['kegg'] + r['nt_kegg'], 'MiKG')
    for _, r in nd.iterrows():
        nu = NS['mikg'] + str(r['neurotransmitter']).replace(' ', '-')
        du = NS['mikg'] + str(r['disease']).replace(' ', '-')
        W.t(nu, A, NS['ent'] + 'Neurotransmitter', 'MiKG')
        W.t(nu, LABEL, r['neurotransmitter'], 'MiKG', literal=True)
        W.t(du, A, NS['ent'] + 'Disease', 'MiKG')
        W.t(du, SUBCLASS, NS['ent'] + 'MentalDisorder', 'MiKG')
        W.t(du, LABEL, r['disease'], 'MiKG', literal=True)
        W.t(nu, NS['mpq'] + 'hasAssociation', du, 'MiKG')

    W.close()
    print(f'\n총 triple {W.n:,}  →  {OUT_NT}')

    rows = [{'source': s, 'relation': len(v['relations']),
             'entity': len(v['entities']), 'triples': v['triples']}
            for s, v in sorted(stats.items(), key=lambda kv: -kv[1]['triples'])]
    all_rel = set().union(*[v['relations'] for v in stats.values()])
    all_ent = set().union(*[v['entities'] for v in stats.values()])
    rows.append({'source': 'Total', 'relation': len(all_rel),
                 'entity': len(all_ent), 'triples': W.n})
    st = pd.DataFrame(rows)
    st.to_csv(os.path.join(OUT, 'kg_stats.csv'), index=False)
    print()
    print(st.to_string(index=False))


def evidence():
    """근거 여러 개로 E 를 만든다 — 논문 §4.2.1 의 E 를 한 소스에 의존하지 않게.

    논문은 MENDA 한 소스로 E 를 만들었다(§3.1·§4.2.1). ProMENDA 하나만 쓰면
    130 compound 중 66 개만 방향이 정해지고, 근거가 얕은 compound 가 다수결로
    ±1 을 받는 문제가 있다(RESULTS.md §5-(3)). 여기서는 네 근거를 각각 부호 있는
    점수로 환산해 함께 둔다.

      promenda  ProMENDA (Pu et al. 2024) 995 연구. 가장 크고 최신      가중 1.00
      menda     MENDA (Pu et al. 2020) 5,675 관계. 논문이 실제 쓴 소스.
                ProMENDA 의 전판이라 상당 부분 겹친다                   가중 0.60
      rules     논문의 85 compound 목록에 대해 재현 파이프라인이 정한 극성
                (analyse/knowledge_query_results.csv). MENDA + 온톨로지·
                MiKG 규칙이 섞여 휴리스틱이 포함된다                     가중 0.40
      afs       Antidepressant Food Score (LaChance & Ramsey 2018) 의
                12 영양소. 우울증 근거가 정리된 외부 기준이지만 양성만
                있고 음성이 없어 부호가 한쪽으로 치우친다                가중 0.50

    가중치는 근거의 규모·최신성·휴리스틱 포함 여부로 실행 전에 정했고
    SOURCE_WEIGHTS 환경변수로 바꿀 수 있다. 결과를 보고 고르지 않았다.

    결합은 두 가지를 모두 만들어 둔다 (analyze.py 가 E_MODE 로 고른다).
      e_weighted  소스 점수의 가중 평균. 근거가 엇갈리면 0 에 가까워진다.
      e_priority  우선순위 첫 비영 값. 기본 rules > promenda > menda > afs
                  (논문이 쓴 목록에 가장 가까운 것부터).

    출력
      out/compound_evidence.csv
    """
    import ast

    from common import menda_consensus

    W = {'promenda': 1.0, 'menda': 0.6, 'rules': 0.4, 'afs': 0.5}
    if os.environ.get('SOURCE_WEIGHTS'):
        W.update(ast.literal_eval(os.environ['SOURCE_WEIGHTS']))
    PRIORITY = os.environ.get('PRIORITY', 'rules,promenda,menda,afs').split(',')

    food = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    cpds = sorted(food['kegg'].unique())
    print(f'  대상 compound {len(cpds)} (FDC 영양소에 매핑된 KEGG)')

    src = {}        # source -> {kegg: signed score}
    meta = {}       # kegg -> name

    # --- 1. ProMENDA
    pm = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))
    src['promenda'] = dict(zip(pm['kegg'], pm['e_shrunk']))
    meta.update(dict(zip(pm['kegg'], pm['name'])))
    print(f'  promenda  {sum(1 for c in cpds if src["promenda"].get(c, 0)):3d} compound')

    # --- 2. MENDA 2020 원본
    menda_path = os.path.join(BASE, 'menda.xlsx')
    if os.path.exists(menda_path):
        md = pd.read_excel(menda_path, sheet_name='Metabolite')
        tab, _ = menda_consensus(md, 'KEGG', 'Up/Down_regulated ',
                                 'Study_type_Metabolite_level',
                                 name_col='Metabolite_name', study_col='Study_ID')
        src['menda'] = dict(zip(tab['kegg'], tab['e_shrunk']))
        for k, n in zip(tab['kegg'], tab['name']):
            meta.setdefault(k, n)
        tab.to_csv(os.path.join(OUT, 'compound_depression_menda.csv'), index=False)
    else:
        src['menda'] = {}
        print('  ⚠ menda.xlsx 없음 — menda 근거 생략')
    print(f'  menda     {sum(1 for c in cpds if src["menda"].get(c, 0)):3d} compound')

    # --- 3. 논문 85 목록에 대한 재현 파이프라인의 극성
    q_path = os.path.join(BASE, 'analyse', 'knowledge_query_results.csv')
    if os.path.exists(q_path):
        q = pd.read_csv(q_path)
        q = q[q['incidence'] != 0]
        src['rules'] = dict(zip(q['compound'], q['incidence'].astype(float)))
        for k, n in zip(q['compound'], q['name']):
            meta.setdefault(k, n)
        rules_src = dict(zip(q['compound'], q['source']))
    else:
        src['rules'], rules_src = {}, {}
        print('  ⚠ analyse/knowledge_query_results.csv 없음 — rules 근거 생략')
    print(f'  rules     {sum(1 for c in cpds if src["rules"].get(c, 0)):3d} compound')

    # --- 4. AFS (LaChance & Ramsey 2018) 의 12 영양소 — 전부 양성
    # tools/paper.py 의 AFS 근사와 같은 KEGG 목록.
    AFS = {'C00504': 'Folate', 'C00023': 'Iron', 'C06429': 'DHA',
           'C00305': 'Magnesium', 'C00238': 'Potassium', 'C01529': 'Selenium',
           'C00378': 'Thiamine', 'C00473': 'Vitamin A', 'C02823': 'Vitamin B12',
           'C00072': 'Vitamin C', 'C00038': 'Zinc'}
    src['afs'] = {k: 1.0 for k in AFS}
    for k, n in AFS.items():
        meta.setdefault(k, n)
    print(f'  afs       {sum(1 for c in cpds if src["afs"].get(c, 0)):3d} compound')

    # --- 소스별 스케일 맞추기
    #
    # 소스마다 점수의 크기 규모가 다르다. MENDA 계열은 근거량으로 축소한 연속값이라
    # |score| 중앙값이 0.16 인 반면, rules·afs 는 범주형 판정이라 전부 ±1 이다.
    # 그대로 가중 평균하면 가중치와 무관하게 범주형 소스가 혼합을 지배한다
    # (실측: rules 가 ProMENDA 와 부호 일치 48% 인데도 순위를 뒤집었다).
    # 각 소스를 그 소스 안의 최대 |score| 로 나눠 [-1, 1] 로 맞춘다.
    # 소스 안의 상대적 강약은 보존되고, 소스 사이의 비중은 W 가 정한다.
    for s_name, d in src.items():
        mx = max((abs(v) for v in d.values()), default=0.0)
        if mx:
            src[s_name] = {k: v / mx for k, v in d.items()}

    # --- 결합
    #
    # 세 가지 결합을 모두 만들어 둔다 (analyze.py 가 E_MODE 로 고른다).
    #   e_weighted  스케일 맞춘 점수의 가중 평균
    #   e_priority  우선순위 첫 비영 소스의 부호
    #   e_vote      모든 소스를 부호로만 보는 가중 투표
    # 각각 rules 를 뺀 판(_norules)도 함께 낸다. rules 는 재현 파이프라인의
    # 휴리스틱이 섞인 범주형 판정이라, 넣고 뺀 차이를 비교할 수 있어야 한다.
    def combine(vals, weights, priority):
        active = {s: v for s, v in vals.items() if v != 0 and weights.get(s, 0) > 0}
        wsum = sum(weights[s] for s in active)
        if not wsum:
            return 0.0, 0.0, 0.0, set()
        e_w = sum(weights[s] * v for s, v in active.items()) / wsum
        e_v = sum(weights[s] * (1 if v > 0 else -1) for s, v in active.items()) / wsum
        e_p = 0.0
        for s in priority:
            if s in active:
                e_p = 1.0 if active[s] > 0 else -1.0
                break
        return e_w, e_p, e_v, {1 if v > 0 else -1 for v in active.values()}

    W_NR = {**W, 'rules': 0.0}
    PRIORITY_NR = [s for s in PRIORITY if s != 'rules']

    rows = []
    for c in cpds:
        vals = {s: float(src[s].get(c, 0.0)) for s in W}
        e_w, e_p, e_v, signs = combine(vals, W, PRIORITY)
        e_w2, e_p2, e_v2, _ = combine(vals, W_NR, PRIORITY_NR)
        active = {s: v for s, v in vals.items() if v != 0}
        rows.append({
            'kegg': c, 'name': meta.get(c, ''),
            **{f'{s}_score': round(vals[s], 4) for s in W},
            'n_source': len(active),
            'agree': '' if len(active) < 2 else ('same' if len(signs) == 1 else 'conflict'),
            'rules_src': rules_src.get(c, ''),
            'e_weighted': round(e_w, 4), 'e_priority': round(e_p, 4),
            'e_vote': round(e_v, 4),
            'e_weighted_norules': round(e_w2, 4),
            'e_priority_norules': round(e_p2, 4),
            'e_vote_norules': round(e_v2, 4),
        })
    ev = pd.DataFrame(rows).sort_values('n_source', ascending=False)
    ev.to_csv(os.path.join(OUT, 'compound_evidence.csv'), index=False)

    nz_w = int((ev['e_weighted'] != 0).sum())
    nz_p = int((ev['e_priority'] != 0).sum())
    only_pm = int((ev['promenda_score'] != 0).sum())
    print()
    print(f'  방향이 정해진 compound   ProMENDA 단독 {only_pm}  ->  '
          f'가중합의 {nz_w} / 우선순위 {nz_p}  (전체 {len(ev)})')
    print(f'  근거 2개 이상 {int((ev.n_source >= 2).sum())} '
          f'(일치 {int((ev.agree == "same").sum())} / '
          f'충돌 {int((ev.agree == "conflict").sum())})')
    print()
    print('  근거가 충돌하는 compound:')
    for _, r in ev[ev.agree == 'conflict'].head(12).iterrows():
        parts = ' '.join(f'{s}={r[f"{s}_score"]:+.2f}' for s in W if r[f'{s}_score'])
        print(f'    {r.kegg} {str(r["name"])[:26]:28s} {parts}  '
              f'-> w={r.e_weighted:+.2f} p={r.e_priority:+.0f}')
    print()
    print('  두 결합이 부호까지 다른 compound:')
    diff = ev[(ev.e_weighted * ev.e_priority) < 0]
    for _, r in diff.head(10).iterrows():
        print(f'    {r.kegg} {str(r["name"])[:26]:28s} '
              f'weighted {r.e_weighted:+.2f} / priority {r.e_priority:+.0f}')
    print(f'    총 {len(diff)}개')


STEPS = {'food': food, 'promenda': promenda, 'evidence': evidence,
         'microbe': microbe, 'kg': kg}


def main(argv):
    want = argv or list(STEPS)
    unknown = [w for w in want if w not in STEPS]
    if unknown:
        sys.exit(f'알 수 없는 단계 {unknown}. 가능: {list(STEPS)}')
    for name in want:
        print(f'\n{"=" * 70}\n== {name}\n{"=" * 70}', flush=True)
        STEPS[name]()


if __name__ == '__main__':
    main(sys.argv[1:])
