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
import numpy as np
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
from common import (BASE, OUT, FDC_RAW, UNIT_TO_G, FDC_CATEGORY, cached_get, kegg_rest,
                    normalize_label, normalize_category, kegg_map, normkey,
                    mesh_lookup, cached_covering)


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
    food['wweia_code'] = pd.NA


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
        food.loc[hit, 'wweia_code'] = sf.set_index('fdc_id')['wweia_category_number'] \
            .reindex(food.loc[hit, 'fdc_id']).astype('Int64').values
        print(f'  FNDDS WWEIA 카테고리 적용: {int(hit.sum()):,} 항목')
    else:
        print('  ⚠ survey_fndds_food.csv / wweia_food_category.csv 없음 — '
              'FNDDS 음식은 이름 규칙으로만 분류된다')

    # 브랜드 자유문자열 카테고리는 FDC 안에서 **구분자가 세 가지**다 — 공백 둘,
    # 하이픈, en dash. 같은 카테고리가 셋으로 쪼개진다:
    #   'Fruit  Prepared/Processed' 1,532 · 'Fruit - …' 695 · 'Fruit – …' 44
    # 16 개 카테고리 51,108 항목이 이렇게 갈려 있었다. **WWEIA 적용 뒤에** 돌려야
    # 한다 — 먼저 돌리면 나중에 붙는 WWEIA 철자가 통합을 비켜 간다. 구두점·대소문자를 지운
    # 키로 묶고, 그 안에서 **가장 많이 쓰인 철자**를 대표로 삼는다(표시용 라벨을
    # 지어내지 않는다). WWEIA 의 'Plant-based milk' 와 브랜드의 'Plant Based Milk'
    # 처럼 어휘가 달라도 같은 키면 묶인다 — §5.1 방법 1 #2 의 soy milk 가 이 경우다.
    _vc = food['category'].value_counts()
    _canon, _seen = {}, {}
    for _name, _n in _vc.items():
        _k = normkey(_name, 'a-z0-9/&')
        if _k not in _seen:                      # value_counts 는 빈도 내림차순
            _seen[_k] = _name
        _canon[_name] = _seen[_k]
    _merged = sum(1 for a, b in _canon.items() if a != b)
    food['category'] = food['category'].map(_canon).fillna(food['category'])
    print(f'  카테고리 철자 통합: {_merged} 개 철자 -> 대표 철자로 병합')

    food = food.rename(columns={'description': 'food_name'})

    # 논문은 KG 의 compound(§3.2 23,212)와 추천 행렬 F 의 compound(§4.2.1 85)를
    # **분리**한다. 우리는 둘을 한 표로 쓰고 있었고, 그래서 "F 에 넣으면 추천이
    # 무너지는 성분"이 KG 에서도 통째로 빠졌다 — §5.1 방법 1 #4·#6·#10 이 그래서
    # 막혔다. 스트리밍은 **확장 매핑**(후보 94 종 포함)으로 넓게 받고, F 는 뒤에서
    # `setup/nutrient_kegg_map.csv` 로 좁힌다. F 는 정의상 바뀌지 않는다.
    _cand = os.path.join(BASE, 'setup', 'nutrient_kegg_candidates.csv')
    kg_nid2kegg, kg_nid2name = dict(nid2kegg), dict(nid2name)
    # 단위는 FDC nutrient.csv 가 정본이다. 매핑표(F 층)만 보면 후보 성분의 단위가
    # NaN -> fillna(1.0) 이 되어 **mg 를 g 로 취급**한다 (citric acid 가 1,740 g/100g
    # 으로 나왔다). KG 층을 넓히면서 같이 넓혀야 하는 표다.
    _nut = pd.read_csv(os.path.join(FDC_RAW, 'nutrient.csv'))
    kg_nid2unit = dict(zip(_nut['id'], _nut['unit_name']))
    kg_nid2unit.update(nid2unit)
    if os.path.exists(_cand):
        _c = pd.read_csv(_cand)
        kg_nid2kegg.update(dict(zip(_c['nutrient_id'], _c['kegg'])))
        kg_nid2name.update(dict(zip(_c['nutrient_id'], _c['nutrient_name'])))
    # F 에서 일부러 뺀 성분도 KG 에는 둔다 — Vitamin B-6 는 넣으면 추천이 무너져
    # 기각했지만(§4.3) 질의는 답할 수 있어야 한다. KEGG 대응이 없는 것이 아니다.
    kg_nid2kegg.setdefault(1175, 'C00314')
    kg_nid2name.setdefault(1175, 'Vitamin B-6')
    print(f'  KG 층 매핑 {len(kg_nid2kegg)} (F 층 {len(nid2kegg)})')

    print(f'[3/5] food_nutrient.csv 스트리밍 (KEGG 매핑 행만, 단위 g 환산)')
    keep = set(kg_nid2kegg)
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
    fn['kegg'] = fn['nutrient_id'].map(kg_nid2kegg)
    fn['unit'] = fn['nutrient_id'].map(kg_nid2unit)
    fn['amount_g'] = pd.to_numeric(fn['amount'], errors='coerce') * fn['unit'].map(UNIT_TO_G).fillna(1.0)
    fn = fn.dropna(subset=['amount_g'])
    print(f'  KEGG 측정값 {len(fn):,} 행, compound {fn["kegg"].nunique()}')

    print('[4/5] 라벨 병합 (논문 §3.2 exact matching)')
    fn = fn.merge(food[['fdc_id', 'food_name', 'data_type', 'category', 'wweia_code']],
                  on='fdc_id', how='inner')
    fn['food_key'] = normalize_label(fn['food_name'])
    fn = fn[fn['food_key'].str.len() > 0]
    n_before, n_after = fn['fdc_id'].nunique(), fn['food_key'].nunique()
    print(f'  FDC 항목 {n_before:,} -> 병합 음식 {n_after:,} '
          f'(병합으로 {n_before - n_after:,} 감소)')
    _link = {'fdc_rows': int(len(food)),
             'nutrient_mapped': int(len(nid2kegg)),
             'nutrient_kegg': int(mp['nutrient_kegg'].nunique()),
             'kegg_rows': int(len(fn)),
             'kegg_compound': int(fn['kegg'].nunique()),
             'food_before_merge': int(n_before),
             'food_after_merge': int(n_after),
             'min_cov': MIN_COV}

    # --- KG 층: 성분별 측정치를 **그대로** 둔다 (대표 선택·F 제한 없음).
    # 질의는 FDC nutrient 를 이름으로 묻는다("Folate, DFE", "Vitamin B-6").
    _kg_fn = fn.assign(nutrient_name=fn['nutrient_id'].map(kg_nid2name)).copy()

    # 한 KEGG 에 FDC nutrient 가 여럿 붙는다 (Folate 는 DFE·total·food·folic acid
    # 넷). 전에는 **평균**을 냈는데 서로 다른 것을 재는 값이라 어느 쪽도 아닌
    # 수가 된다 — Pie, peach 의 엽산이 DFE 46 / total 29 / food 4 의 평균 26.3 이
    # 됐다. 대표 측정치 하나를 규칙으로 고른다.
    #   · IU 는 질량이 아니다 (비타민 D 1 IU = 0.025 µg). 질량 측정치가 있으면 그쪽
    #   · DFE·RAE 는 **등가 환산값**이라 뒤로 — DFE = food folate + 1.7 x folic
    #     acid, RAE 는 카로티노이드를 접은 값이다. F 는 '그 KEGG 화합물의 중량'
    #     이므로 기본 측정치(Folate, total · Retinol)를 쓴다. 논문은 Table 2 에서
    #     DFE 를 화합물 중량처럼 썼지만(§5.1 방법 1 #4) 그 혼동을 따라가지 않는다.
    #   · 'added' · 'label entry' · ', food' · 이성질체 분해값은 뒤로
    def _nut_rank(nid):
        n = str(nid2name.get(nid, '')).lower()
        r = 5 if nid2unit.get(nid) == 'IU' else 0
        if re.search(r'\badded\b|label entry|\bfrom \b', n):
            r += 4
        if n.startswith(('cis-', 'trans-')):
            r += 3
        if re.search(r'\bdfe\b|\brae\b', n):
            r += 2
        elif re.search(r'\btotal\b', n):
            r -= 1
        if re.search(r', food\b', n):
            r += 2
        return r

    fn = fn[fn['nutrient_id'].isin(nid2kegg)]          # 여기서부터 F 층
    fn['rank'] = fn['nutrient_id'].map(_nut_rank)
    fn = fn[fn['rank'] == fn.groupby(['food_key', 'kegg'])['rank'].transform('min')]

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
    # 세분 카테고리 -> 상위 식품군. WWEIA 4 자리 코드에는 **큐레이션된 SR 군 링크**가
    # 있다(`setup/wweia_srgroup.csv`, 배포 KG Food_Category.jsonld 에서 추출한 118 개).
    # 앞 2 자리가 상위인 접두 규칙이 아니다 — 재 보니 일치 1 / 불일치 117 이다.
    # 링크가 있으면 그것을 쓰고, 없으면 기존 이름 규칙으로 떨어뜨린다.
    _sr = {}
    _srp = os.path.join(BASE, 'setup', 'wweia_srgroup.csv')
    if os.path.exists(_srp):
        _srdf = pd.read_csv(_srp, dtype={'wweia_code': str})
        _sr = dict(zip(_srdf['wweia_code'], _srdf['sr_group']))
    _wcode = (_sel.sort_values('_prio').groupby('food_key')['wweia_code'].first()
              if 'wweia_code' in _sel.columns else pd.Series(dtype=object))
    _wc = _wcode.reindex(meta['food_key']).values
    meta['food_group'] = [
        _sr.get(str(int(w)), normalize_category(c, n)) if pd.notna(w)
        else normalize_category(c, n)
        for w, c, n in zip(_wc, meta['category'], meta['food_name'])]
    _linked = int(sum(1 for w in _wc if pd.notna(w) and str(int(w)) in _sr))
    print(f'  WWEIA -> SR 군 큐레이션 링크 적용: {_linked:,} 음식')

    # FoodOn 축 — 매칭·조상 로직은 foodon_match.py 한 곳에 있다.
    import foodon_match as _fm
    _fo = _fm.link_table(meta)
    if _fo is None:
        print('  ⚠ FoodOn 캐시 없음 — ourkg/cache/foodon_*.json')
    else:
        _fo.to_csv(os.path.join(OUT, 'food_foodon.csv'), index=False)
        _cls = _fo[_fo.rel == 'class']
        _link['foodon_food'] = int(_cls.food_key.nunique())
        _link['foodon_class'] = int(_cls.foodon.nunique())
        print(f'  FoodOn 축: 음식 {_link["foodon_food"]:,} / {len(meta):,} '
              f'({_link["foodon_food"] / len(meta):.1%}) · 클래스 '
              f'{_link["foodon_class"]:,} · 조상 포함 링크 {len(_fo):,}')

    _link['food_after_mincov'] = int(long['food_key'].nunique())
    _link['compound_after_mincov'] = int(long['kegg'].nunique())
    with open(os.path.join(OUT, 'food_link.json'), 'w') as _fh:
        json.dump(_link, _fh, indent=1)
    long.to_csv(os.path.join(OUT, 'food_compound_long.csv'), index=False)
    # KG 층은 **대표 항목의 값**을 쓴다. foods.csv 는 큐레이션 순위(_PRIORITY)로
    # 대표 fdc_id 를 고르는데 값만 라벨 전체 평균이면 둘이 어긋난다 — 'Pie, peach'
    # 는 대표가 SR legacy(DFE 46 µg)인데 FNDDS(42)와 평균 내 44 가 됐다(방법 1 #4).
    # 음식 쪽 문턱. 개념만 보면 KG 에는 MIN_COV 가 필요 없고(그것은 유사도를
    # 계산하는 F 층의 요구다) 논문 KG 는 FDC 항목 122 만 개를 담는다. 그래서
    # KG_MIN_COV=1 로 풀어 **재 봤고 퇴행이었다** — 음식 14,886 -> 475,769,
    # 파일 463 MB, 점수는 그대로인데 브랜드·시료가 상위를 차지해 답의 질이
    # 떨어졌다(#7 arugula -> GREENS JUICE, #8 베이킹파우더 -> ALMOND BUTTER,
    # #0 과일 94 -> 80). 노린 #6 도 열리지 않았다. RESULTS.md §4.3.
    KG_MIN_COV = int(os.environ.get('KG_MIN_COV', str(MIN_COV)))
    _kcov = _kg_fn.groupby('food_key')['kegg'].nunique()
    _kg_keep = set(_kcov[_kcov >= KG_MIN_COV].index)
    # 대표 항목은 F 코호트 밖 음식에도 같은 규칙(_PRIORITY)으로 고른다.
    _kg_prio = _kg_fn.assign(_p=_kg_fn['data_type'].map(_PRIORITY).fillna(9))
    _krep = (_kg_prio.sort_values('_p').groupby('food_key')['fdc_id'].first().to_dict())
    _rep = {**_krep, **dict(zip(meta['food_key'], meta['fdc_id']))}
    _kg_fn = _kg_fn[_kg_fn['food_key'].isin(_kg_keep)]
    _kg_fn = _kg_fn[_kg_fn['fdc_id'] == _kg_fn['food_key'].map(_rep)]
    _kgc = (_kg_fn.groupby(['food_key', 'fdc_id', 'food_name', 'nutrient_id',
                            'nutrient_name', 'kegg'], as_index=False)['amount_g'].mean())
    _kgc.to_csv(os.path.join(OUT, 'food_compound_kg.csv'), index=False)
    _link['kg_food'] = int(_kgc['food_key'].nunique())
    _link['kg_compound'] = int(_kgc['kegg'].nunique())
    _link['kg_nutrient'] = int(_kgc['nutrient_id'].nunique())
    print(f'  KG 층: 음식 {_link["kg_food"]:,} · compound {_link["kg_compound"]} '
          f'· nutrient {_link["kg_nutrient"]} · 값 {len(_kgc):,}  '
          f'(F 층 음식 {len(meta):,} · compound {long["kegg"].nunique()})')
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
    S = requests.Session()
    S.headers['User-Agent'] = 'ourkg/1.0 (food4health reproduction+extension)'
    cached = cached_get                       # common.py 로 올렸다
    def kegg(path):
        return kegg_rest(path, session=S)


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
    # 배포 Disease_Bacteria 에 없는 균을 보탠다. MiKG 가 말하는 균 36 종과 평가가
    # 요구하는 균(논문 Table 3·5, 방법 1 #6 의 Adlercreutzia 등)이 빠져 있었다 —
    # compound 링크를 아무리 늘려도 **균이 없으면 소용없다**는 것이 #6 으로 드러났다.
    # 이름 -> taxid 해소는 NCBI esearch 로 했고, 학명이 바뀐 5 종(Bacteroides
    # vulgatus -> Phocaeicola vulgatus 등)은 NCBI 동의어 목록으로 확인했다.
    _add = os.path.join(BASE, 'setup', 'microbes_added.csv')
    if os.path.exists(_add):
        _ad = pd.read_csv(_add, dtype=str).fillna('')
        _new = sorted(set(_ad[_ad.taxid != ''].taxid) - set(taxids))
        taxids = sorted(set(taxids) | set(_new))
        print(f'  보탠 미생물 {len(_new)} (setup/microbes_added.csv)')
    print(f'  관계 {len(pairs):,} / 미생물 {len(taxids):,} / 질환 {len(sorted({d for _, d in pairs})):,}')

    # ------------------------------------------------------------------
    # Disbiome (ugent.be) — 외부 큐레이션 미생물-질환 목록.
    #
    # 그 전까지 미생물 축을 넓히는 길은 setup/microbes_added.csv 하나였고 기준이
    # '평가가 요구하는 균' 이었다. 그러면 **이미 아는 균만 늘어난다** — 평가가
    # 묻지 않는 균은 영원히 안 들어온다. 자기참조다.
    # Disbiome 은 우리 평가와 무관하게 큐레이션된 목록이라 그 고리가 끊긴다.
    # (논문 §2 가 든 gutMDisorder 는 호스트가 죽어 Disbiome 으로 리다이렉트된다.)
    #
    # 질환명이 자유 표기(MedDRA 계열)라 MeSH descriptor 로 해소해야 F03 판정을
    # 같은 자리에서 할 수 있다 — common.mesh_lookup 참조.
    print('[1b/5] Disbiome → 미생물-질환 (외부 큐레이션)')
    _db = json.loads(cached('disbiome_experiment.json', lambda: S.get(
        'https://disbiome.ugent.be:8080/experiment', timeout=300).text))
    _dnames = sorted({r['disease_name'] for r in _db})
    _d2m = json.loads(cached('disbiome_mesh.json',
                             lambda: json.dumps(mesh_lookup(_dnames, S), ensure_ascii=False)))
    _alias = os.path.join(BASE, 'setup', 'disease_alias.csv')
    if os.path.exists(_alias):
        _al = pd.read_csv(_alias, dtype=str).fillna('')
        for _, _r in _al.iterrows():
            _d2m[_r['source_name']] = {'mesh_id': _r['mesh_id'], 'mesh_label': _r['mesh_label'],
                                       'term_used': _r['mesh_label'], 'match': 'alias'}
        print(f'  별칭표로 보탠 질환 {len(_al)} (setup/disease_alias.csv)')
    print(f'  질환 표기 {len(_dnames)} → MeSH 해소 {len(_d2m)}')

    disb = pd.DataFrame([
        {'taxid': str(r['organism_ncbi_id']), 'organism': r['organism_name'],
         'disease_name': r['disease_name'], 'outcome': r['qualitative_outcome'],
         'mesh_id': _d2m[r['disease_name']]['mesh_id'],
         'disease': _d2m[r['disease_name']]['mesh_label'],
         'term_used': _d2m[r['disease_name']]['term_used'],
         'match': _d2m[r['disease_name']]['match']}
        for r in _db if r.get('organism_ncbi_id') and r['disease_name'] in _d2m])
    print(f'  실험 {len(disb):,} / 균 {disb.taxid.nunique():,} / 질환 {disb.mesh_id.nunique()}')

    meshids = sorted({d for _, d in pairs} | set(disb.mesh_id))

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


    tree = cached_covering('mesh_tree.json', fetch_tree, meshids)
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
    disb['is_mental'] = disb['mesh_id'].isin(mental)
    disb['is_neuro'] = disb['mesh_id'].isin(neuro)
    disb.to_csv(os.path.join(OUT, 'microbe_disease_disbiome.csv'), index=False)
    _dsel = disb[disb.is_mental | disb.is_neuro]
    print(f'  Disbiome 정신·신경 관계 {len(_dsel):,} '
          f'(미생물 {_dsel.taxid.nunique()} 종, 질환 {_dsel.mesh_id.nunique()} 종)')

    print(f'  정신질환 관계 {int(md.is_mental.sum()):,} '
          f'(미생물 {md[md.is_mental].taxid.nunique()} 종, 질환 {md[md.is_mental].mesh_id.nunique()} 종)')
    for d, n in md[md.is_mental].disease.value_counts().head(12).items():
        print(f'     {n:4d}  {d}')

    # ------------------------------------------------------------------
    print('[3/5] NCBI taxonomy 로 학명·계통 갱신')
    # 질환 링크가 있는 균 + **보탠 균**. 보탠 쪽은 Disease_Bacteria 에 쌍이 없어
    # 이 필터에서 탈락한다 — MiKG(미생물→신경전달물질→정신질환)와 평가가 근거다.
    _added = set()
    if os.path.exists(_add):
        _added = set(pd.read_csv(_add, dtype=str).fillna('').taxid) - {''}
    _base = set(md[md.is_mental | md.is_neuro]['taxid'])
    _disb = set(_dsel['taxid'])
    focus = sorted(_base | _disb | _added)
    print(f'  대상 {len(focus)} 종 = 배포 KG {len(_base)}'
          f' + Disbiome {len(_disb - _base)} + 보탠 {len(_added - _base - _disb)}')


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


    # 캐시가 요청을 덮는지 common.cached_covering 이 확인한다 — 안 그러면 focus 가
    # 늘어도 옛 캐시가 돌아와 보탠 균이 조용히 빠진다(실제로 127 종에 머물렀다).
    tax = cached_covering('ncbi_taxonomy.json', fetch_tax, focus)
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
    # 종 이름 2 단어로만 맞추다가 485 종 중 167 종밖에 못 이었다. 못 이은 318 중
    # **255 가 종이 아니다** — 속 200 · 과 47 · 목 6 · 문 5 · 강 2. Disbiome 이
    # 속·과 수준으로 보고하기 때문이고, 2 단어 매칭으로는 구조적으로 못 잡는다.
    #
    # KEGG genome 이름의 첫 단어가 속이므로 **종 -> 속** 사다리를 둔다. 어느
    # 수준에서 걸렸는지 `match_rank` 에 적는다 — 속 수준 링크는 "이 속의 어떤
    # 유전체가 이 compound 를 대사한다"는 더 약한 주장이라 구분할 수 있어야 한다.
    by_species, by_genus = collections.defaultdict(list), collections.defaultdict(list)
    for o in orgs:
        w = re.sub(r'\(.*?\)', '', o['name']).split()
        if not w:
            continue
        by_species[' '.join(w[:2]).lower()].append(o['org'])
        by_genus[re.sub(r'[^a-z]', '', w[0].lower())].append(o['org'])

    tax_org, tax_lv = {}, {}
    for t, rec in tax.items():
        w = rec['name'].split()
        for lv, key, table in (('species', ' '.join(w[:2]).lower(), by_species),
                               ('genus', re.sub(r'[^a-z]', '', w[0].lower()), by_genus)):
            if key in table:
                tax_org[t], tax_lv[t] = table[key][0], lv
                break
    _n = collections.Counter(tax_lv.values())
    print(f'  KEGG organism 코드 연결 {len(tax_org)}/{len(tax)} '
          f'(종 {_n["species"]} · 속 {_n["genus"]})')

    micro = pd.DataFrame([{'taxid': t, **rec, 'kegg_org': tax_org.get(t, ''),
                           'match_rank': tax_lv.get(t, '')}
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
                    rows.append({'kegg': c, 'taxid': t, 'kegg_org': org, 'n_ko': n,
                                 'match_rank': tax_lv.get(t, '')})
        print(f'\r  organism {i}/{len(orgcodes)}  링크 {len(rows):,}', end='', flush=True)
    print()
    cm = pd.DataFrame(rows)
    cm.to_csv(os.path.join(OUT, 'compound_microbe.csv'), index=False)
    print(f'  그중 속 수준 매칭 {int((cm["match_rank"] == "genus").sum()):,} 링크 '
          f'— "이 속의 어떤 유전체가" 라는 더 약한 주장이다')
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
    from rdflib import Graph, URIRef, RDFS

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

    # MiKG 가 statement 마다 달아 둔 것 — 전에는 버리고 있었다.
    #   hasEvidenceLevel  A 4 / B 23 / C 55   근거 등급
    #   hasRegulation     Promote 13 / Inhibit 1  방향
    #   hasMapID          KEGG pathway id (map00380 등) 56
    # statement 단위로 모아 microbe_neurotransmitter 에 붙인다.
    _st = []
    for _s in set(g.subjects(_p('hasGutMicrobiota'), None)):
        _mic = [_local(o) for o in g.objects(_s, _p('hasGutMicrobiota'))]
        _nt = [_local(o) for o in g.objects(_s, _p('hasNeurotransmitter'))]
        _ev = [str(o) for o in g.objects(_s, _p('hasEvidenceLevel'))]
        _rg = [str(o) for o in g.objects(_s, _p('hasRegulation'))]
        for _m in _mic:
            for _n in _nt:
                _st.append({'microbe': _m, 'neurotransmitter': _n,
                            'evidence_level': _ev[0] if _ev else '',
                            'regulation': _rg[0] if _rg else ''})
    if _st:
        _stdf = pd.DataFrame(_st).drop_duplicates(['microbe', 'neurotransmitter'])
        mn = mn.merge(_stdf, on=['microbe', 'neurotransmitter'], how='left')
        print(f'  MiKG statement 속성: 근거등급 '
              f'{dict(_stdf.evidence_level.value_counts())} · 방향 '
              f'{dict(_stdf.regulation.value_counts())}')

    # KEGG pathway 는 statement 가 아니라 별도 노드에 달려 신경전달물질과 이어진다.
    # 미생물 -> 신경전달물질 -> **대사 경로** 라는 한 층이 더 생긴다.
    _pw = [{'neurotransmitter': _local(_n), 'kegg_pathway': str(_mid),
            'pathway_label': str(_lb)}
           for _s in set(g.subjects(_p('hasMapID'), None))
           for _mid in g.objects(_s, _p('hasMapID'))
           for _n in g.objects(_s, _p('hasNeurotransmitter'))
           for _lb in list(g.objects(_s, RDFS.label)) or ['']]
    if _pw:
        _pwdf = pd.DataFrame(_pw).drop_duplicates()
        _pwdf.to_csv(os.path.join(OUT, 'neurotransmitter_pathway.csv'), index=False)
        print(f'  MiKG KEGG pathway 축: {len(_pwdf)} 링크 · '
              f'경로 {_pwdf.kegg_pathway.nunique()} · '
              f'신경전달물질 {_pwdf.neurotransmitter.nunique()}')

    # MiKG 가 자기 엔티티에 달아 둔 외부 식별자 (MeSH 51 · SNOMED 63).
    # 우리는 이름 문자열로 잇고 있었다 — ID 로 이으면 모호성이 사라진다.
    _SAME = URIRef('http://www.w3.org/2002/07/owl#sameAs')
    _xref = []
    for _s, _, _o in g.triples((None, _SAME, None)):
        _u = str(_o)
        _src = 'MeSH' if 'nlm.nih.gov' in _u else ('SNOMED CT' if 'ihtsdo' in _u else '')
        if _src:
            _xref.append({'entity': _local(_s), 'source': _src,
                          'id': _u.rsplit('/', 1)[-1], 'uri': _u})
    _xdf = pd.DataFrame(_xref).drop_duplicates()
    _xdf.to_csv(os.path.join(OUT, 'mikg_xref.csv'), index=False)
    print(f'  MiKG 외부 식별자: 엔티티 {_xdf.entity.nunique()} · '
          f'{dict(_xdf.source.value_counts())}')

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

    print('[1/6] Food · Category (FDC)')
    foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
    long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
    food_uri = {k: NS['our'] + 'food/' + slug(k) for k in foods['food_key']}
    cat_uri, fine_uri, fine_parent = {}, {}, {}
    for _, r in foods.iterrows():
        u = food_uri[r['food_key']]
        W.t(u, A, NS['ent'] + 'Food', 'FoodData Central')
        W.t(u, LABEL, r['food_name'], 'FoodData Central', literal=True)
        W.t(u, NS['our'] + 'fdcId', str(r['fdc_id']), 'FoodData Central', literal=True)
        W.t(u, NS['our'] + 'dataType', r['data_type'], 'FoodData Central', literal=True)
        c = cat_uri.setdefault(r['food_group'], NS['our'] + 'category/' + slug(r['food_group']))
        W.t(u, SUBCLASS, c, 'FoodData Central')
        # 세분 카테고리(FDC category) 를 한 층 더 둔다 — §3.2 의 2단 매핑 구조이고,
        # FoodOn·중국 온톨로지가 붙는 지점도 이 층이다 ([6/6]).
        if isinstance(r['category'], str) and r['category']:
            fu = fine_uri.setdefault(r['category'],
                                     NS['our'] + 'category/' + slug('fine:' + r['category']))
            W.t(u, SUBCLASS, fu, 'FoodData Central')
            fine_parent[r['category']] = c
    for name, u in cat_uri.items():
        W.t(u, A, NS['ent'] + 'FoodCategory', 'FoodData Central')
        W.t(u, LABEL, name, 'FoodData Central', literal=True)
    for name, u in fine_uri.items():
        W.t(u, A, NS['ent'] + 'FoodCategory', 'FoodData Central')
        W.t(u, LABEL, name, 'FoodData Central', literal=True)
        W.t(u, SUBCLASS, fine_parent[name], 'FoodData Central')
    print(f'  음식 {len(foods):,} / 상위 카테고리 {len(cat_uri)} / 세분 {len(fine_uri)}')

    print('[2/6] Food → Nutrient 중량 (npq:hasNutrients / hasNutrientWeights)')
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

    print('[3/6] Compound (KEGG) · depression 관계 (ProMENDA)')
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

    # --- 근거별 극성과 결합값 (build.py evidence 의 산출물)
    #
    # 위의 hasPositive/NegativeAssociation 은 ProMENDA 단독 극성이다 —
    # 논문 §3.1 이 MENDA 한 소스로 E 를 만든 것과 같은 구조다.
    # 근거가 여럿일 때 그것을 KG 안에서 추적할 수 있어야 하므로,
    # 소스마다 근거 노드를 하나 두고(논문이 중량에 쓰는 reification 과 같은 꼴:
    # npq:hasNutrientWeights -> 노드 -> rdf:value) 점수와 출처를 단다.
    # 결합값 여섯 가지는 compound 에 직접 리터럴로 붙인다.
    ev_path = os.path.join(OUT, 'compound_evidence.csv')
    if os.path.exists(ev_path):
        ev = pd.read_csv(ev_path)
        SOURCES = ['promenda', 'menda', 'rules', 'afs']
        SOURCE_META = {
            'promenda': ('ProMENDA (Pu et al. 2024)', 1.0),
            'menda': ('MENDA (Pu et al. 2020)', 0.6),
            'rules': ('재현 파이프라인 85 compound 극성', 0.4),
            'afs': ('Antidepressant Food Score (LaChance & Ramsey 2018)', 0.5),
        }
        COMBINED = ['e_weighted', 'e_priority', 'e_vote',
                    'e_weighted_norules', 'e_priority_norules', 'e_vote_norules']
        for name, (label, weight) in SOURCE_META.items():
            su = NS['our'] + 'source/' + name
            W.t(su, A, NS['ent'] + 'EvidenceSource', 'evidence')
            W.t(su, LABEL, label, 'evidence', literal=True)
            W.t(su, NS['our'] + 'sourceWeight', f'{weight:g}', 'evidence',
                literal=True, dtype='double')

        n_ev, n_comb = 0, 0
        for _, r in ev.iterrows():
            cu = NS['kegg'] + r['kegg']
            for name in SOURCES:
                score = float(r.get(f'{name}_score', 0) or 0)
                if score == 0:
                    continue
                nu = f'{NS["our"]}evidence/{r["kegg"]}_{name}'
                W.t(cu, NS['our'] + 'hasEvidence', nu, 'evidence')
                W.t(nu, A, NS['ent'] + 'Evidence', 'evidence')
                W.t(nu, NS['our'] + 'fromSource', NS['our'] + 'source/' + name,
                    'evidence')
                W.t(nu, NS['our'] + 'aboutDisease', DEPRESSION, 'evidence')
                W.t(nu, VALUE, f'{score:.6g}', 'evidence',
                    literal=True, dtype='double')
                rel = ('hasPositiveAssociation' if score > 0
                       else 'hasNegativeAssociation')
                W.t(nu, NS['npq'] + rel, DEPRESSION, 'evidence')
                n_ev += 1
            for col in COMBINED:
                val = float(r.get(col, 0) or 0)
                if val == 0:
                    continue
                # 주의: col.replace('e_', ...) 는 'e_vote' 의 'vot|e_' 까지 바꾼다.
                prop = NS['our'] + 'combinedE_' + col[len('e_'):]
                W.t(cu, prop, f'{val:.6g}', 'evidence',
                    literal=True, dtype='double')
                n_comb += 1
        print(f'  근거 노드 {n_ev:,} (소스 {len(SOURCES)}) / 결합값 {n_comb:,} '
              f'(방식 {len(COMBINED)})')
    else:
        print('  ⚠ compound_evidence.csv 없음 — 근거별 극성은 싣지 않는다 '
              '(python3 ourkg/build.py evidence)')

    print('[4/6] Microbe (NCBI) · compound-microbe (KEGG) · microbe-disease')
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
    # 속 수준 매칭은 **출처를 갈라서** 담는다. 버리지 않는다 — 실재하는 정보다.
    # 다만 "이 종이 대사한다" 가 아니라 "이 속의 어떤 유전체가" 이므로 KEGG 종
    # 수준 추론과 같은 태그를 달면 SPARQL 로 거를 수 없다 (DATA.md §6·§7).
    _n_genus = 0
    for _, r in cm.iterrows():
        _g = str(r.get('match_rank', '')) == 'genus'
        W.t(NS['mic'] + r['taxid'], NS['mpq'] + 'hasMetabolites',
            NS['kegg'] + r['kegg'], 'KEGG(속 수준)' if _g else 'KEGG')
        _n_genus += _g
    print(f'  compound-미생물 {len(cm):,} (종 수준 {len(cm) - _n_genus:,} · '
          f'속 수준 {_n_genus:,} — 출처 태그로 구분)')
    # VMH/AGORA2 — 유전체 규모 대사 재구성에서 온 compound-미생물.
    # **예측이지 실측이 아니다.** 같은 술어를 쓰되 출처를 따로 달아 KEGG 추론
    # 경로나 MiKG 의 A/B/C 근거와 섞이지 않게 한다 (DATA.md §8).
    # 두 경로로 받았다 — 벌크 zip(AGORA2 SBML)과 REST API. 같은 VMH 데이터이고
    # 커버리지가 서로 다르므로(벌크 30,397 / API 34,992 KEGG 링크) 합쳐 쓴다.
    _vmp = os.path.join(BASE, 'ourkg', 'cache', 'vmh_metabolites.csv')
    _srcs = [os.path.join(BASE, 'ourkg', 'cache', f) for f in
             ('agora_microbe_metabolite.csv', 'vmh_microbe_metabolite.csv')]
    _srcs = [f for f in _srcs if os.path.exists(f)]
    n_vmh = 0
    if _srcs and os.path.exists(_vmp):
        _a2k = pd.read_csv(_vmp, dtype=str).fillna('')
        _a2k = dict(zip(_a2k.abbr, _a2k.kegg))
        _ag = pd.concat([pd.read_csv(f, dtype=str)[['taxid', 'met_abbr']]
                         for f in _srcs]).drop_duplicates()
        _ag['kegg'] = _ag.met_abbr.map(_a2k).fillna('')
        _vl = _ag[_ag.kegg != ''][['taxid', 'kegg']].drop_duplicates()
        _vl.to_csv(os.path.join(OUT, 'compound_microbe_vmh.csv'), index=False)
        _known = set(cm[['taxid', 'kegg']].itertuples(index=False, name=None))
        for _t, _k in _vl.itertuples(index=False, name=None):
            W.t(NS['mic'] + _t, NS['mpq'] + 'hasMetabolites',
                NS['kegg'] + _k, 'VMH/AGORA2')
            n_vmh += 1
        _both = len(_known & set(_vl.itertuples(index=False, name=None)))
        print(f'  VMH/AGORA2 compound-미생물 {n_vmh:,} '
              f'(compound {_vl.kegg.nunique()} · 균 {_vl.taxid.nunique()} · '
              f'KEGG 경로와 겹침 {_both:,})')

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

    # Disbiome — 외부 큐레이션 미생물-질환. 출처를 MiKG 와 **분리해서** 올린다.
    # Elevated/Reduced 는 그 질환에서 그 균의 **존재비 변화**이지 이로움/해로움이
    # 아니다. hasPositive/NegativeAssociation 으로 바꾸면 뜻이 달라지므로
    # 중립 hasAssociation 에 abundance 속성으로 붙인다.
    _dbp = os.path.join(OUT, 'microbe_disease_disbiome.csv')
    n_disb = 0
    if os.path.exists(_dbp):
        _db = pd.read_csv(_dbp, dtype={'taxid': str})
        _db = _db[_db.is_mental | _db.is_neuro]
        _seen = set()
        for _, r in _db.iterrows():
            du = NS['mesh'] + r['mesh_id']
            W.t(NS['mic'] + r['taxid'], NS['mpq'] + 'hasAssociation', du, 'Disbiome')
            W.t(du, A, NS['ent'] + 'Disease', 'Disbiome')
            key = (r['taxid'], r['mesh_id'], r['outcome'])
            if key not in _seen:
                _seen.add(key)
                W.t(NS['mic'] + r['taxid'], NS['our'] + 'abundanceIn',
                    f"{r['disease']}|{r['outcome']}", 'Disbiome', literal=True)
            n_disb += 1
        print(f'  Disbiome 미생물-질환 {n_disb:,} (균 {_db.taxid.nunique()} · 질환 {_db.mesh_id.nunique()})')

    print('[5/6] 신경전달물질 경로 (MiKG)')
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
        # MiKG 가 statement 마다 달아 둔 근거 등급(A/B/C)과 방향(Promote/Inhibit).
        # 전에는 버리고 있었다 — KG 에서 관계의 **질**을 구분할 수 있게 한다.
        for _k, _pred in (('evidence_level', 'evidenceLevel'),
                          ('regulation', 'regulation')):
            _v = r.get(_k)
            if isinstance(_v, str) and _v:
                W.t(mu + '/' + str(r['neurotransmitter']).replace(' ', '-'),
                    NS['our'] + _pred, _v, 'MiKG', literal=True)
    for _, r in nd.iterrows():
        nu = NS['mikg'] + str(r['neurotransmitter']).replace(' ', '-')
        du = NS['mikg'] + str(r['disease']).replace(' ', '-')
        W.t(nu, A, NS['ent'] + 'Neurotransmitter', 'MiKG')
        W.t(nu, LABEL, r['neurotransmitter'], 'MiKG', literal=True)
        W.t(du, A, NS['ent'] + 'Disease', 'MiKG')
        W.t(du, SUBCLASS, NS['ent'] + 'MentalDisorder', 'MiKG')
        W.t(du, LABEL, r['disease'], 'MiKG', literal=True)
        W.t(nu, NS['mpq'] + 'hasAssociation', du, 'MiKG')

    # MiKG 가 자기 엔티티에 달아 둔 MeSH·SNOMED CT 식별자. 우리는 이름 문자열로
    # 잇고 있었다 — 배포본에 라벨·계층이 없어 포기했던 SNOMED 축이 여기서 열린다.
    _xp = os.path.join(OUT, 'mikg_xref.csv')
    n_mikg_x = 0
    if os.path.exists(_xp):
        for _, r in pd.read_csv(_xp).iterrows():
            W.t(NS['mikg'] + str(r['entity']).replace(' ', '-'), SAMEAS,
                str(r['uri']), 'MiKG')
            n_mikg_x += 1
    # 미생물 -> 신경전달물질 -> KEGG 대사 경로 (별도 노드에 hasMapID 로 달려 있다)
    _pp = os.path.join(OUT, 'neurotransmitter_pathway.csv')
    n_mikg_pw = 0
    if os.path.exists(_pp):
        for _, r in pd.read_csv(_pp).iterrows():
            _pu = 'https://www.kegg.jp/pathway/' + str(r['kegg_pathway'])
            W.t(NS['mikg'] + str(r['neurotransmitter']).replace(' ', '-'),
                NS['our'] + 'hasPathway', _pu, 'MiKG')
            if isinstance(r.get('pathway_label'), str) and r['pathway_label']:
                W.t(_pu, LABEL, r['pathway_label'], 'MiKG', literal=True)
            n_mikg_pw += 1
    print(f'  MiKG 외부 식별자 {n_mikg_x} · KEGG pathway {n_mikg_pw} triple 추가')

    # ------------------------------------------------------------------
    print('[6/6] 온톨로지 축 (KEGG brite · FoodOn · 중국 식품 온톨로지 · SNOMED CT)')
    # 논문 §3.1 이 든 세 축이다. 원본은 레포의 공개 KG 에서 가져온다 — 외부 재수집은
    # 하지 않는다. 다리(우리 엔티티와의 연결)가 몇 개나 생기는지 함께 센다.
    FKG = os.path.join(BASE, 'foodkg_triply')
    cdep = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))

    def _ld(fn):
        with open(os.path.join(FKG, fn)) as fh:
            return [n for e in json.load(fh) for n in e.get('@graph', [])]

    def _lit(n, key):
        v = n.get(key)
        if not v:
            return None
        v = v if isinstance(v, list) else [v]
        x = v[0].get('@value') if isinstance(v[0], dict) else v[0]
        return x if isinstance(x, str) else None

    onto_link = []
    FOODON_SA = 'http://www.w3.org/2002/07/owl#sameAs'
    CN_EN = 'http://wasp.cs.vu.nl/KG#hasEnglishLabel'

    def _norm(x):
        return re.sub(r'[^a-z]', '', str(x).lower())

    def _variants(x):
        """온톨로지 라벨 하나에서 매칭용 변형을 만든다.
        'Soy milk (milk) beverage' -> {soymilkbeverage, soymilk, soymilkmilkbeverage}"""
        x = str(x)
        out = {x, re.sub(r'\s*\(.*?\)\s*', ' ', x), x.split(',')[0]}
        base = re.sub(r'\s*\(.*?\)\s*', ' ', x).strip()
        for tail in (' beverage', ' drink', ' products', ' product'):
            if base.lower().endswith(tail):
                out.add(base[: -len(tail)])
        return {_norm(v) for v in out if _norm(v)}

    # 우리 쪽 연결 대상: 세분 카테고리(위에서 만든 fine_uri)와 음식 라벨
    fine_by_label = {k: v for k, v in fine_uri.items()}
    fine_by_norm, fine_label_by_norm = {}, {}
    for k, v in fine_uri.items():
        for var in _variants(k):
            fine_by_norm.setdefault(var, v)
            fine_label_by_norm.setdefault(var, k)
    food_by_norm, food_label_by_norm = {}, {}
    for _, r in foods.iterrows():
        first = str(r['food_name']).split(',')[0]
        for var in _variants(first):
            food_by_norm.setdefault(var, food_uri[r['food_key']])
            food_label_by_norm.setdefault(var, first)

    # --- KEGG brite 화합물 분류축
    # 논문 §3.1 "leveraged the compound ontology from KEGG compounds".
    # 우리 KEGG 단계는 compound-미생물 경로만 만들었고 분류축이 없었다 —
    # §5.1 방법 1 의 #14·#15·#16 이 이것 때문에 답하지 못했다.
    # BRITE=live (기본) 면 KEGG REST 에서 분류축을 **다시 받는다**. 논문 배포본의
    # KEGG 서브셋은 6,685 노드뿐이라 85 중 27 개에 분류가 붙지 않는다(§17.29).
    # 실패하면 정적 스냅샷으로 폴백한다. 캐시 TTL 30일 — 같은 창 안에서는 재현된다.
    BRITE_MODE = os.environ.get('BRITE', 'live')

    def _brite_live():
        """br08001·br08002·br08005 를 받아 (클래스라벨, 상위, compound->클래스)."""
        lab, par, c2c = {}, collections.defaultdict(set), collections.defaultdict(set)
        for br in ('br08001', 'br08002', 'br08005'):
            txt = kegg_rest(f'get/br:{br}')
            path = {}
            for line in txt.split('\n'):
                m = re.match(r'^([A-F])\s*(.*)$', line)
                if not m or not m[2].strip():
                    continue
                lv, rest = m[1], m[2].strip()
                cm = re.match(r'^(C\d{5})\s+(.+)$', rest)
                if cm:                                   # compound 행
                    parent = path.get(chr(ord(lv) - 1))
                    if parent:
                        c2c[cm[1]].add(parent)
                    continue
                uri = f'{NS["our"]}brite/{br}/{lv}/{re.sub(r"[^A-Za-z0-9]+", "_", rest)[:60]}'
                lab[uri] = re.sub(r'\s*\[Fig\]\s*$', '', rest)
                up = path.get(chr(ord(lv) - 1))
                if up:
                    par[uri].add(up)
                path[lv] = uri
                for d in 'BCDEF':                        # 더 깊은 경로는 무효화
                    if d > lv:
                        path.pop(d, None)
        return lab, par, c2c

    KT = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
    # 우리 compound 에 KEGG_ALIAS 를 **조회용으로만** 적용한다 — 논문 ID 27 개는
    # 자기 KEGG 파일에 노드가 없어 라벨도 brite 분류도 붙지 않는다 (§17.29).
    sys.path.insert(0, BASE)
    from kegg_alias import KEGG_ALIAS
    _raw = set(long['kegg'].dropna()) | set(cdep['kegg'].dropna())
    ours_kegg = {KEGG_ALIAS.get(k, k) for k in _raw}
    alias_hit = sum(1 for k in _raw if k in KEGG_ALIAS)
    cls_label, cls_parent, cmp_cls = {}, collections.defaultdict(set), collections.defaultdict(set)
    for n in _ld('KEGG_Compound.jsonld'):
        u = n['@id']
        lab = _lit(n, LABEL)
        if 'Class' in u:
            if lab:
                cls_label[u] = lab
            for v in n.get(SUBCLASS, []):
                if isinstance(v, dict) and v.get('@id'):
                    cls_parent[u].add(v['@id'])
        elif '/entry/C' in u:
            kid = u.rsplit('/', 1)[-1]
            if kid not in ours_kegg:
                continue
            if lab:
                cls_label[u] = lab
            for v in n.get(KT, []):
                if isinstance(v, dict) and 'Class' in v.get('@id', ''):
                    cmp_cls[kid].add(v['@id'])
    if BRITE_MODE == 'live':
        try:
            l2, p2, c2 = _brite_live()
            cls_label.update(l2)
            for k, v in p2.items():
                cls_parent[k] |= v
            n_live = 0
            for kid, cs in c2.items():
                if kid in ours_kegg:
                    cmp_cls[kid] |= cs
                    n_live += 1
            print(f'  KEGG brite live — 분류 {len(l2):,}, 우리 compound 에 붙은 것 {n_live}')
        except Exception as e:
            print(f'  ⚠ brite live 실패({type(e).__name__}) — 정적 스냅샷만 쓴다')

    n_br = 0
    for u, lab in cls_label.items():
        W.t(u, LABEL, lab, 'KEGG', literal=True)
        n_br += 1
    for u, ps in cls_parent.items():
        for pu in ps:
            W.t(u, SUBCLASS, pu, 'KEGG')
            n_br += 1
    for kid, cs in cmp_cls.items():
        for cu in cs:
            W.t(NS['kegg'] + kid, A, cu, 'KEGG')
            n_br += 1
    pd.DataFrame([{'class_uri': u, 'label': cls_label.get(u, ''), 'parent_uri': pu}
                  for u, ps in cls_parent.items() for pu in ps]
                 + [{'class_uri': u, 'label': l, 'parent_uri': ''}
                    for u, l in cls_label.items() if u not in cls_parent]
                 ).to_csv(os.path.join(OUT, 'kegg_class.csv'), index=False)
    pd.DataFrame([{'kegg': k, 'class_uri': c} for k, cs in cmp_cls.items() for c in cs]
                 ).to_csv(os.path.join(OUT, 'compound_class.csv'), index=False)
    print(f'  KEGG brite {n_br:,} triple — 분류 {len(cls_label):,}, '
          f'분류된 compound {len(cmp_cls)}/{len(ours_kegg)} '
          f'(KEGG_ALIAS 로 해소 {alias_hit})')

    # --- FoodOn
    n_fo = n_fo_link = 0
    cat_sameas = {}
    for n in _ld('Food_Category.jsonld'):
        tgt = [v['@id'] for v in n.get(FOODON_SA, []) if 'FOODON' in v.get('@id', '')]
        lab = _lit(n, LABEL)
        if tgt and lab:
            cat_sameas[lab] = tgt[0]
    OBO = 'http://www.geneontology.org/formats/oboInOwl#'
    SYN = NS['our'] + 'synonym'
    fo_alias = collections.defaultdict(set)     # 정규화 이름 -> FoodOn URI
    fo_label = {}                               # FoodOn URI -> 그쪽 원 라벨
    for n in _ld('Food_Ontology.jsonld'):
        u = n['@id']
        lab = _lit(n, LABEL)
        if lab:
            W.t(u, LABEL, lab, 'FoodOn', literal=True)
            n_fo += 1
            fo_label[u] = lab
            for v in _variants(lab):
                fo_alias[v].add(u)
        # 동의어도 가져온다 — 라벨만으로는 우리 카테고리와 거의 안 붙는다.
        for pk in (OBO + 'hasSynonym', OBO + 'hasNarrowSynonym'):
            for x in (n.get(pk) or []):
                sv = x.get('@value') if isinstance(x, dict) else x
                if isinstance(sv, str) and sv:
                    W.t(u, SYN, sv, 'FoodOn', literal=True)
                    n_fo += 1
                    for v in _variants(sv):
                        fo_alias[v].add(u)
        for v in n.get(SUBCLASS, []):
            if isinstance(v, dict) and v.get('@id', '').startswith('http'):
                W.t(u, SUBCLASS, v['@id'], 'FoodOn')
                n_fo += 1
    for lab, fo in cat_sameas.items():
        tu = fine_by_label.get(lab)
        if tu:
            W.t(tu, SAMEAS, fo, 'FoodOn')
            n_fo += 1
            n_fo_link += 1
            onto_link.append({'our': lab, 'kind': 'category',
                              'onto_label': fo_label.get(fo, lab), 'source': 'FoodOn'})
    # 공개 KG 의 sameAs 8 건 말고, 라벨·동의어 정규화 일치로도 잇는다.
    for lab, tu in fine_by_label.items():
        cand = set().union(*[fo_alias.get(v, set()) for v in _variants(lab)]) or set()
        for fo in sorted(cand)[:1]:
            W.t(tu, SAMEAS, fo, 'FoodOn')
            n_fo += 1
            n_fo_link += 1
            onto_link.append({'our': lab, 'kind': 'category',
                              'onto_label': lab, 'source': 'FoodOn'})
    # 질환 상위 분류 — MeSH 트리. 논문은 SNOMED CT 로 이 축을 세웠다고 하지만
    # 배포본에는 id 284 개뿐이고 라벨·계층이 없다(§5.1 방법 1 #12). 우리는 이미
    # 트리 번호를 갖고 있었고, 번호는 접두를 자르면 조상이 된다
    # (F03.600.300.375 < F03.600.300 < F03.600 Mood Disorders < F03 Mental Disorders).
    # 번호 -> 기술어 이름은 MeSH SPARQL 로 받아 둔다. 파일명은 build.microbe 의
    # `mesh_tree.json`({mesh_id: [트리번호]})과 **달라야 한다** — 같은 이름을 쓰면
    # 서로 덮어써서 F03 판정이 전부 실패한다(실제로 그렇게 깨졌다).
    _mtp = os.path.join(BASE, 'ourkg', 'cache', 'mesh_tree_ancestors.json')
    n_tree = 0
    if os.path.exists(_mtp):
        _MT = json.load(open(_mtp))
        _rows = []
        for _mid, _dis, _tns in md[['mesh_id', 'disease', 'tree_numbers']].dropna(
                subset=['tree_numbers']).drop_duplicates().values:
            _du = NS['mesh'] + str(_mid)
            for _t in str(_tns).split(';'):
                _p = _t.strip().split('.')
                for _i in range(1, len(_p)):          # 자기 자신은 뺀다
                    _a = _MT.get('.'.join(_p[:_i]))
                    if not _a or _a['mesh_id'] == _mid:
                        continue
                    W.t(_du, SUBCLASS, NS['mesh'] + _a['mesh_id'], 'MeSH tree')
                    W.t(NS['mesh'] + _a['mesh_id'], LABEL, _a['label'], 'MeSH tree',
                        literal=True)
                    n_tree += 2
                    _rows.append({'mesh_id': _mid, 'disease': _dis,
                                  'tree_number': _t.strip(), 'ancestor_tree': '.'.join(_p[:_i]),
                                  'ancestor_mesh': _a['mesh_id'], 'ancestor': _a['label']})
        pd.DataFrame(_rows).drop_duplicates().to_csv(
            os.path.join(OUT, 'disease_tree.csv'), index=False)
        print(f'  MeSH 트리 상위 분류: {n_tree:,} triple '
              f'(질환 {len({r["mesh_id"] for r in _rows})}종)')

    # OLS 로 받은 FoodOn 축(out/food_foodon.csv)도 KG 에 쓴다. CSV 에만 두면
    # §4.1 SPARQL 평가가 못 본다 — 배포 subset 은 soy milk 가 없고 계층도 끊겨 있다.
    _fop = os.path.join(OUT, 'food_foodon.csv')
    n_fo_ols = 0
    if os.path.exists(_fop):
        _d = pd.read_csv(_fop)
        _obo = 'http://purl.obolibrary.org/obo/'
        _uri = lambda oid: _obo + str(oid).replace(':', '_')
        for _oid, _lab in _d[['foodon', 'foodon_label']].drop_duplicates().values:
            if isinstance(_lab, str):
                W.t(_uri(_oid), LABEL, _lab, 'FoodOn/OLS', literal=True)
                n_fo_ols += 1
        _cls = _d[_d.rel == 'class'].set_index('food_key')['foodon'].to_dict()
        for _fk, _oid in _cls.items():
            _fu = food_uri.get(_fk)
            if _fu:
                W.t(_fu, SAMEAS, _uri(_oid), 'FoodOn/OLS')
                n_fo_ols += 1
        for _fk, _g in _d[_d.rel == 'ancestor'].groupby('food_key'):
            _c = _cls.get(_fk)
            if _c:
                for _a in _g['foodon'].unique():
                    W.t(_uri(_c), SUBCLASS, _uri(_a), 'FoodOn/OLS')
                    n_fo_ols += 1
    print(f'  FoodOn {n_fo:,} triple, 우리 카테고리와 연결 {n_fo_link}'
          f' · OLS 축 {n_fo_ols:,} triple')

    # --- 중국 식품 온톨로지
    n_cn = n_cn_cat = n_cn_food = 0
    for n in _ld('Food_Chinese.jsonld'):
        u = n['@id']
        en = _lit(n, CN_EN)
        if en:
            W.t(u, LABEL, en, 'Chinese Food Ontology', literal=True)
            n_cn += 1
            vs = _variants(en)
            ck = next((v for v in vs if v in fine_by_norm), None)
            fk = next((v for v in vs if v in food_by_norm), None)
            if ck:
                W.t(fine_by_norm[ck], SAMEAS, u, 'Chinese Food Ontology')
                n_cn += 1
                n_cn_cat += 1
                onto_link.append({'our': fine_label_by_norm[ck], 'kind': 'category',
                                  'onto_label': en, 'source': 'Chinese'})
            elif fk:
                W.t(food_by_norm[fk], SAMEAS, u, 'Chinese Food Ontology')
                n_cn += 1
                n_cn_food += 1
                onto_link.append({'our': food_label_by_norm[fk], 'kind': 'food',
                                  'onto_label': en, 'source': 'Chinese'})
        for v in n.get(SUBCLASS, []):
            if isinstance(v, dict) and v.get('@id', '').startswith('http'):
                W.t(u, SUBCLASS, v['@id'], 'Chinese Food Ontology')
                n_cn += 1
    print(f'  중국 식품 온톨로지 {n_cn:,} triple, '
          f'카테고리 연결 {n_cn_cat} / 음식 연결 {n_cn_food}')

    pd.DataFrame(onto_link).to_csv(os.path.join(OUT, 'category_ontology.csv'), index=False)
    print(f'  온톨로지 ↔ 카테고리/음식 매핑 {len(onto_link)} 건 → category_ontology.csv')

    # --- SNOMED CT
    # 공개 KG 의 SNOMED 은 Mental_health.jsonld 의 284 노드뿐이고 rdf:value(id 문자열)
    # 와 MeSH 로의 sameAs 10 건만 있다. **라벨도 상위 클래스도 없다** — 논문 Table 1 이
    # 적은 4,291,226 triple 은 배포되지 않았다. 넣을 수 있는 것은 이것이 전부다.
    n_sct = n_sct_link = 0
    our_dis = {NS['mesh'] + str(x) for x in md['mesh_id'].dropna().unique()}
    for n in _ld('Mental_health.jsonld'):
        u = n['@id']
        if 'ihtsdo' not in u:
            continue
        v = _lit(n, VALUE)
        if v:
            W.t(u, VALUE, v, 'SNOMED CT', literal=True)
            n_sct += 1
        for o in n.get(FOODON_SA, []):
            if isinstance(o, dict) and o.get('@id', '').startswith('http'):
                W.t(u, SAMEAS, o['@id'], 'SNOMED CT')
                n_sct += 1
                if o['@id'] in our_dis:
                    n_sct_link += 1
    print(f'  SNOMED CT {n_sct} triple (id·sameAs 뿐, 라벨·계층 없음), '
          f'우리 질병과 연결 {n_sct_link}')

    # ------------------------------------------------------------------
    # 논문 §3.2 Entity linking 대응표. 재현 트랙의 eval/paper_kg_stats.linking()
    # 이 논문 수치를 **검증**한다면, 여기서는 우리가 **수행한** 링킹을 집계한다.
    _xp2 = os.path.join(OUT, 'mikg_xref.csv')
    _n_sct_mikg = _n_mesh_mikg = 0
    if os.path.exists(_xp2):
        _xd = pd.read_csv(_xp2)
        _n_sct_mikg = int((_xd.source == 'SNOMED CT').sum())
        _n_mesh_mikg = int((_xd.source == 'MeSH').sum())
    _mnp = os.path.join(OUT, 'microbe_neurotransmitter.csv')
    _n_mikg_ev = 0
    if os.path.exists(_mnp):
        _mnd = pd.read_csv(_mnp)
        if 'evidence_level' in _mnd.columns:
            _n_mikg_ev = int(_mnd.evidence_level.notna().sum())

    fl = {}
    _flp = os.path.join(OUT, 'food_link.json')
    if os.path.exists(_flp):
        with open(_flp) as _fh:
            fl = json.load(_fh)
    rows = [
        ('food', 'FDC 원본 항목', fl.get('fdc_rows'), '§3.1 34,250 food samples'),
        ('food', '라벨 병합 전 (KEGG 측정 보유)', fl.get('food_before_merge'), ''),
        ('food', '라벨 병합 후 (§3.2 exact matching)', fl.get('food_after_merge'),
         '§3.2 "merge foods with identical labels"'),
        ('food', f'음식당 compound >= {fl.get("min_cov")} 필터 후', fl.get('food_after_mincov'),
         '§4.2.1 135 food'),
        ('food', '세분 카테고리 (FDC category)', len(fine_uri), '§3.2 128 distinct categories'),
        ('food', '상위 카테고리 (SR food group)', len(cat_uri), ''),
        ('compound', 'nutrient -> KEGG 매핑', fl.get('nutrient_mapped'), ''),
        ('compound', '음식 행렬의 KEGG compound', fl.get('compound_after_mincov'),
         '§3.2 23,212 compounds / §4.2.1 85'),
        ('compound', 'ProMENDA E 의 KEGG compound', int(cdep['kegg'].nunique()), ''),
        ('compound', 'KEGG brite 로 분류된 compound', len(cmp_cls), '§3.1 compound ontology'),
        ('microbe', 'NCBI taxonomy 링크 (taxid)', int(mic['taxid'].nunique()),
         '§3.2 984,031 gut microbiota'),
        ('microbe', 'KEGG organism 매칭', int(mic['kegg_org'].notna().sum()), ''),
        ('disease', 'MeSH 링크', int(md['mesh_id'].nunique()), '§3.2 3,505 mental disorders'),
        ('disease', 'SNOMED CT 링크 (배포본)', n_sct_link, '배포본에 라벨·계층 없음'),
        ('disease', 'SNOMED CT 링크 (MiKG xref)', _n_sct_mikg, 'MiKG 가 엔티티에 단 SCT id'),
        ('disease', 'MeSH 링크 (MiKG xref)', _n_mesh_mikg, ''),
        ('microbe', 'MiKG 근거 등급 보유 관계', _n_mikg_ev, 'A/B/C'),
        ('microbe', 'MiKG KEGG pathway 링크', n_mikg_pw, '미생물→신경전달물질→경로'),
        ('microbe', 'compound-미생물 (KEGG 추론, 종 수준)',
         int((cm.get('match_rank', pd.Series(dtype=str)) != 'genus').sum()),
         'compound→EC→KO→organism'),
        ('microbe', 'compound-미생물 (KEGG 추론, 속 수준)',
         int((cm.get('match_rank', pd.Series(dtype=str)) == 'genus').sum()),
         '"이 속의 어떤 유전체가" — 더 약한 주장'),
        ('microbe', 'compound-미생물 (VMH/AGORA2)', n_vmh, '유전체 재구성 — 예측'),
        ('microbe', '미생물-질환 (Disbiome)', n_disb,
         '외부 큐레이션 — 축 확장의 자기참조를 끊는다'),
        ('ontology', 'FoodOn ↔ 카테고리 (배포 KG 부분집합)', n_fo_link, '§3.1 FoodOn'),
        ('ontology', 'FoodOn 클래스 링크 (음식, OLS)', fl.get('foodon_food'),
         '배포 subset 에 없는 계층 — foodon_match.py'),
        ('ontology', 'FoodOn 고유 클래스 (OLS)', fl.get('foodon_class'), ''),
        ('ontology', '중국 온톨로지 ↔ 카테고리', n_cn_cat, '§3.1 Chinese Food Ontology'),
        ('ontology', '중국 온톨로지 ↔ 음식', n_cn_food, ''),
    ]
    ls = pd.DataFrame(rows, columns=['axis', 'item', 'value', 'paper'])
    ls.to_csv(os.path.join(OUT, 'linking_stats.csv'), index=False)
    print('\n[링킹] 논문 §3.2 대응 — out/linking_stats.csv')
    for _, r in ls.iterrows():
        v = '-' if pd.isna(r['value']) else f'{int(r["value"]):,}'
        print(f'  {r["axis"]:9s} {r["item"][:36]:38s} {v:>10s}  {r["paper"]}')

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


def form():
    """F 에 구조·가공 축을 더한다 — FDC **측정값**에서만.

    왜
    --
    §7 에서 ModiMedDiet 이 가르는 것은 상당 부분 성분이 아니라 **형태**였다
    (separable lean only vs lean and fat, whole vs refined, raw vs fried).
    지금 F 는 KEGG 에 매핑되는 영양소 130종만 담아 이걸 전혀 모른다.
    §8 에서 잰 성분 중량만의 상한은 AUC 0.816 이다. 그 상한 자체를 올리는 길이다.

    누수 방지
    ---------
    ModiMedDiet 라벨은 **음식 이름 문자열** 규칙으로 만들었다(§7). 그러므로
    형태 축을 이름에서 뽑으면 라벨을 특징으로 쓰는 것이 되어 평가가 무의미해진다.
    여기서는 **FDC 가 측정한 영양소 값만** 쓴다. 이름·카테고리는 보지 않는다.

    더하는 축 (전부 FDC 측정 영양소, KEGG 매핑이 없어 F 에서 빠져 있던 것들)
      절대량   Energy(1008) Protein(1003) Fat(1004) Carb(1005) Water(1051)
               Fiber(1079) AddedSugar(1235) TotalSugar(2000/1063)
               SFA(1258) MUFA(1292) PUFA(1293) TFA(1257) Ash(1007)
      비율     added_sugar_share(= 첨가당/탄수화물), sugar_share,
               sat_share(= 포화/지방), unsat_ratio(= (MUFA+PUFA)/SFA),
               carb_share·fat_energy_share(= 중량/열량)
               ※ 절대량이 이미 100 g 당 값이라 'x/100' 은 비율이 아니다. 뺐다.
    비율이 가공·형태의 대리 변수다 — 정제 곡물은 섬유 밀도가 낮고 첨가당 비중이
    높으며, 기름에 튀긴 것은 지방 비중과 에너지 밀도가 높다.

    논문 §3.1 은 "The nutrients of the food are quantified in weight" 라고만 하고
    KEGG 매핑을 요구하지 않는다. 다만 KG 의 compound 축은 KEGG 그대로 둔다 —
    여기서 더하는 것은 추천 입력 F 이지 KG 의 엔티티가 아니다.

    출력
      out/food_form.csv   food_key x (절대량 + 비율)
    """
    NUTRIENTS = {
        1008: 'energy_kcal', 1003: 'protein_g', 1004: 'fat_g',
        1005: 'carb_g', 1051: 'water_g', 1079: 'fiber_g',
        1235: 'added_sugar_g', 2000: 'total_sugar_g', 1063: 'total_sugar_g2',
        1258: 'sfa_g', 1292: 'mufa_g', 1293: 'pufa_g', 1257: 'tfa_g',
        1007: 'ash_g',
    }
    CHUNK = 2_000_000

    print('[1/3] food.csv (라벨 병합용)')
    food = pd.read_csv(os.path.join(FDC_RAW, 'food.csv'), low_memory=False,
                       usecols=['fdc_id', 'description'])
    food['food_key'] = normalize_label(food['description'])
    keep_keys = set(pd.read_csv(os.path.join(OUT, 'foods.csv'))['food_key'])
    food = food[food['food_key'].isin(keep_keys)]
    key_of = dict(zip(food['fdc_id'], food['food_key']))
    print(f'  대상 FDC 항목 {len(food):,} -> 음식 {food["food_key"].nunique():,}')

    print('[2/3] food_nutrient.csv 스트리밍 (구조 영양소만)')
    want = set(NUTRIENTS)
    parts, rows = [], 0
    for ch in pd.read_csv(os.path.join(FDC_RAW, 'food_nutrient.csv'), chunksize=CHUNK,
                          usecols=['fdc_id', 'nutrient_id', 'amount'], low_memory=False):
        rows += len(ch)
        ch = ch[ch['nutrient_id'].isin(want) & ch['fdc_id'].isin(key_of)]
        if len(ch):
            parts.append(ch)
        print(f'\r  읽음 {rows:,} / 보관 {sum(len(p) for p in parts):,}',
              end='', flush=True)
    print()
    fn = pd.concat(parts, ignore_index=True)
    fn['food_key'] = fn['fdc_id'].map(key_of)
    fn['feat'] = fn['nutrient_id'].map(NUTRIENTS)
    fn['amount'] = pd.to_numeric(fn['amount'], errors='coerce')
    tab = fn.pivot_table(index='food_key', columns='feat', values='amount',
                         aggfunc='mean')
    # total_sugar 는 두 nutrient_id 중 있는 쪽을 쓴다
    if 'total_sugar_g2' in tab.columns:
        tab['total_sugar_g'] = tab.get('total_sugar_g', np.nan).fillna(
            tab['total_sugar_g2'])
        tab = tab.drop(columns='total_sugar_g2')
    tab = tab.reindex(sorted(keep_keys)).fillna(0.0)
    print(f'  음식 {len(tab):,} x 절대량 {tab.shape[1]}')

    print('[3/3] 비율 (가공·형태 대리 변수)')
    def ratio(a, b):
        return np.divide(tab[a].values, tab[b].values,
                         out=np.zeros(len(tab)), where=tab[b].values > 0)

    # 절대량은 이미 100 g 당 값이므로 'x/100' 꼴은 비율이 아니라 같은 열의
    # 복사본이다(완전 공선). 진짜 비율만 더한다.
    tab['added_sugar_share'] = ratio('added_sugar_g', 'carb_g')
    tab['sugar_share'] = ratio('total_sugar_g', 'carb_g')
    tab['sat_share'] = ratio('sfa_g', 'fat_g')
    tab['unsat_ratio'] = np.divide((tab['mufa_g'] + tab['pufa_g']).values,
                                   tab['sfa_g'].values,
                                   out=np.zeros(len(tab)),
                                   where=tab['sfa_g'].values > 0)
    tab['carb_share'] = ratio('carb_g', 'energy_kcal')
    tab['fat_energy_share'] = ratio('fat_g', 'energy_kcal')
    tab = tab.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    tab.to_csv(os.path.join(OUT, 'food_form.csv'))
    print(f'  저장: food_form.csv  {tab.shape[0]:,} x {tab.shape[1]}')
    nz = (tab != 0).mean().sort_values(ascending=False)
    print('  비영 비율 상위:')
    for k, v in nz.head(8).items():
        print(f'    {k:20s} {v*100:5.1f}%')


STEPS = {'food': food, 'form': form, 'promenda': promenda,
         'evidence': evidence, 'microbe': microbe, 'kg': kg}


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
