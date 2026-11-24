"""ourkg 공통 유틸 — 재현 파이프라인(reconstruct.py 등)과 분리된 확장판."""
import io
import os
import re
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OURKG = os.path.join(BASE, 'ourkg')
OUT = os.path.join(OURKG, 'out')
FDC_RAW = os.path.join(BASE, 'fdc_raw')
os.makedirs(OUT, exist_ok=True)

# 논문 §3.1 "The nutrients of the food are quantified in weight" — 전부 g 으로.
UNIT_TO_G = {'G': 1.0, 'MG': 1e-3, 'UG': 1e-6, 'IU': 1e-6}

# 논문 §3.2 라벨 정규화: 콤마 앞 영양소군 접두사 / 샘플코드 / 괄호 지역표기 제거.
NUTRIENT_PREFIX = (r'^(fatty acids|niacin|tocopherols|sugars|amino acids|'
                   r'cholesterol|pantothenic acid|starch|carotenoids|choline|'
                   r'folate|proximates|minerals|fa|vitamin [a-z0-9\- ]+)\s*[,\-]\s*')


# 논문 §3.2 가 명시한 음식 라벨 규칙 (2026-11-09 에 전부 구현).
#   (1) "splitting the food labels by commas and removing unnecessary words that
#        may follow the first comma, such as 'ready to drink' appearing after 'milk'"
#   (2) "exact matching is employed to merge foods with identical labels"
#   (3) "transform plural words into singular form"
#   (4) "convert uppercase letters to lowercase"
# LABEL_MODE=legacy 로 두면 2026-11-08 이전 동작(쉼표 유지·복수 유지)을 쓴다.
# 민감도 비교용이고 기본값은 paper 다.
LABEL_MODE = os.environ.get('LABEL_MODE', 'paper')

# (1) 은 **일괄 절단이 아니다.** 논문이 든 예는 "'ready to drink' appearing after
# 'milk'" 처럼 **불필요한 말**을 지우는 것이고, 논문 자신의 Table 2·3·4 음식명은
# 쉼표 뒤를 그대로 유지한다 — "Lettuce, Romaine" · "Broccoli, raw" ·
# "Goose egg, cooked" · "Milk, skim". 첫 쉼표에서 통째로 자르면 그 이름들이
# 나올 수 없다. 그래서 불필요어 목록을 지우는 방식으로 구현한다.
# (일괄 절단판은 §13 에 민감도로 기록했다 — A층 지표가 크게 퇴행한다.)
UNNECESSARY = (r',\s*(ready[ -]to[ -](?:drink|eat|serve|cook)|as purchased|'
               r'as consumed|includes? [^,]*|not further specified|nfs|'
               r'unprepared|prepared|from (?:concentrate|dry)|reconstituted|'
               r'undiluted|diluted[^,]*|commercially prepared|home ?made|'
               r'all types?|various|unspecified|regular|original)\b')

# 복수 -> 단수. 영어 규칙 최소판이며, 'ss/us/is/os' 로 끝나는 말은 건드리지 않는다
# (glass, citrus, analysis, potatos 아님). FDC 라벨은 명사구라 이 정도로 충분하다.
_PLURAL = [
    (r'\b([a-z]+?)ies\b', r'\1y'),                       # berries -> berry
    (r'\b([a-z]+?(?:ch|sh|ss|x|z))es\b', r'\1'),          # peaches -> peach
    (r'\b([a-z]+?o)es\b', r'\1'),                         # tomatoes -> tomato
    (r"\b([a-z]+?[^siu'])s\b", r'\1'),                    # carrots -> carrot
                                                           # 소유격 제외: McDONALD'S
]                                                          # ss/us/is 는 건드리지 않는다
                                                           # (glass, citrus, analysis)


def singularize(series):
    out = series
    for pat, rep in _PLURAL:
        out = out.str.replace(pat, rep, regex=True)
    return out


CACHE = os.path.join(OURKG, 'cache')


def cached_get(name, fetch, ttl_days=30):
    """네트워크로 받은 것을 ourkg/cache/ 에 둔다.

    TTL 안이면 캐시를 쓰므로 **같은 창 안에서는 재현 가능**하고, 지나면 자동으로
    다시 받아 **최신성**을 얻는다. build.microbe() 와 build.kg() 가 공유한다.
    """
    os.makedirs(CACHE, exist_ok=True)
    import time
    p = os.path.join(CACHE, name)
    if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < ttl_days * 86400:
        return open(p, encoding='utf-8').read()
    txt = fetch()
    open(p, 'w', encoding='utf-8').write(txt)
    return txt


def cached_covering(name, fetch, keys):
    """`cached_get` 인데 **캐시가 요청을 덮는지** 확인한다.

    `cached_get` 은 파일만 보고 입력 변화를 모른다. 요청 목록이 늘어도 옛 캐시를
    돌려주므로 새로 늘어난 것이 조용히 빠진다. 같은 함정을 두 번 당했다 —
    taxid 가 127 -> 162 로 늘었을 때, MeSH descriptor 가 244 -> 313 으로 늘었을 때
    (F03 판정이 15 -> 6 으로 줄었다). 그래서 검사를 코드 한 곳으로 모은다.

    `keys` 가 캐시의 키에 다 들어 있지 않으면 캐시를 버리고 다시 받는다.
    """
    import json
    data = json.loads(cached_get(name, fetch))
    missing = set(keys) - set(data)
    if missing:
        print(f'  캐시에 없는 {len(missing)} 건 — 다시 받는다')
        os.remove(os.path.join(CACHE, name))
        data = json.loads(cached_get(name, fetch))
    return data


def cached_bytes(name, fetch, ttl_days=30):
    """`cached_get` 의 바이너리판 — xlsx 같은 것을 받는다.

    텍스트판과 달리 디코딩하지 않는다. 받다가 끊긴 파일을 캐시로 굳히면 다음
    실행이 조용히 깨지므로, **임시 파일에 받아서 다 받은 뒤에 옮긴다.**
    """
    os.makedirs(CACHE, exist_ok=True)
    import time
    p = os.path.join(CACHE, name)
    if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < ttl_days * 86400:
        return open(p, 'rb').read()
    blob = fetch()
    tmp = p + '.part'
    open(tmp, 'wb').write(blob)
    os.replace(tmp, p)
    return blob


# gutMDisorder v3 (bio-computing.hrbmu.edu.cn) — 논문 §2 가 든 미생물-질환 DB.
# 이전 호스트(bio-annotation.cn)가 죽어 Disbiome 으로 대체했는데, 하얼빈의대
# 새 호스트에서 v3 가 살아 있다. SPA 라 페이지에는 표가 없고 번들의
# /gutMDisorder_api/api/resource/download?fileName=... 가 xlsx 를 준다.
GMD_URL = ('https://bio-computing.hrbmu.edu.cn/gutMDisorder_api/api'
           '/resource/download?fileName=')
# (파일, 메타시트, 연관시트, taxid 열, 근거 열)
GMD_FILES = (
    ('gutMDisorder_v3_Literature-based_All.xlsx', 'Literature', 'Association',
     'GutMicrobiataNCBIID', 'PMID'),
    ('gutMDisorder_v3_Rawdata-based_All.xlsx', 'projectr', 'associationr',
     'GutMicrobeNCBIID', 'Projectnumber'),
)
GMD_HEALTH = 'D006262'          # MeSH "Health" — 대조군
GMD_PHENOTYPE = 'Gut microbiota associated with phenotype'
GMD_INTERVENTION = 'Interventions change the composition of gut microbiota'


def gutmdisorder(session=None):
    """gutMDisorder v3 → (taxid, mesh_id, 증감) 표.

    **방향을 신뢰할 수 있는 행만 남긴다.** 메타 시트의 Condition1 vs Condition2
    가 비교쌍이고 `Alteration` 은 1 기준 2 대비 증감인데, Condition2 가 Health
    인 행만 "질환에서 증가/감소" 로 읽을 수 있다. 나머지는
      - 중재 vs 대조 (Yogurt vs No yogurt),
      - 질환 vs 질환 (궤양성대장염 vs 크론병),
      - 중증도 (악화 vs 자연완화), 인구집단 (African American vs Non-Hispanic white)
    라서 질환 방향이 아니다. ResearchType 도 phenotype 으로 제한한다.
    Human 만 쓴다 — 마우스 행은 식품 추천의 근거가 될 수 없다.

    Condition1ID 는 동반질환이 `;` 로 붙고 MeSH 가 없으면 `*` 다. `D\d{6,}` 만
    뽑아 한 질환씩 행으로 펼친다.
    """
    import requests
    S = session or requests.Session()
    rows = []
    for fn, msheet, asheet, txcol, evcol in GMD_FILES:
        blob = cached_bytes(fn, lambda fn=fn: S.get(
            GMD_URL + fn, timeout=300).content)
        meta = pd.read_excel(io.BytesIO(blob), sheet_name=msheet)
        assoc = pd.read_excel(io.BytesIO(blob), sheet_name=asheet)
        keep = meta[(meta.HumanOrMouse.astype(str).str.strip() == 'Human')
                    & (meta.Condition2ID.astype(str).str.strip() == GMD_HEALTH)
                    & (meta.ResearchType == GMD_PHENOTYPE)]
        a = assoc.rename(columns={assoc.columns[0]: 'Index'}).merge(
            keep[['Index', 'Condition1', 'Condition1ID', evcol]], on='Index')
        for _, r in a.iterrows():
            if pd.isna(r[txcol]):
                continue
            alt = str(r['Alteration']).strip().lower()
            # increased/decreased 표기 혼용을 합치고, present/absent 는 증감이
            # 아니라 검출 여부라 방향으로 쓰지 않는다.
            alt = {'increased': 'increase', 'decreased': 'decrease'}.get(alt, alt)
            for mid in re.findall(r'D\d{6,}', str(r['Condition1ID'])):
                rows.append({
                    'taxid': str(int(r[txcol])), 'organism': r['GutMicrobe'],
                    'gmd_rank': str(r['Classification']).strip().lower(),
                    'mesh_id': mid, 'disease_name': str(r['Condition1']),
                    'alteration': alt, 'pvalue': r.get('PValue'),
                    'evidence': str(r[evcol]), 'gmd_source': msheet})
    g = pd.DataFrame(rows)
    # 같은 (균, 질환, 방향) 이 여러 논문/프로젝트에서 나오면 근거 수로 접는다.
    g['n_evidence'] = g.groupby(['taxid', 'mesh_id', 'alteration'])['evidence'
                                                                   ].transform('nunique')
    return g


def kegg_rest(path, session=None, timeout=180):
    """KEGG REST. rate limit(0.34s)을 지키고 캐시한다."""
    import time
    import requests

    def f():
        sess = session or requests.Session()
        sess.headers.setdefault('User-Agent', 'ourkg/1.0')
        r = sess.get(f'https://rest.kegg.jp/{path}', timeout=timeout)
        r.raise_for_status()
        time.sleep(0.34)
        return r.text

    return cached_get('kegg_' + path.replace('/', '_') + '.txt', f)


def normalize_label(series):
    """논문 §3.2 의 음식 라벨 정규화."""
    s = (series.astype(str).str.strip().str.lower()
         .str.replace(NUTRIENT_PREFIX, '', regex=True)
         .str.replace(r'\s*-\s*[a-z0-9]{6,12}\s*$', '', regex=True)   # 브랜드 샘플코드
         .str.replace(r'\s*\([^)]*\)\s*', ' ', regex=True)           # 괄호 지역표기
         # 괄호를 지우면 ", , raw" 처럼 빈 쉼표 구간이 남는다. 합쳐 준다.
         .str.replace(r'\s*,(\s*,)+', ',', regex=True)
         .str.replace(r'^\s*,\s*', '', regex=True))
    if LABEL_MODE == 'paper':
        s = s.str.replace(UNNECESSARY, '', regex=True)                # (1) 불필요어 제거
    s = (s.str.replace(r'[\s,]+$', '', regex=True)
         .str.replace(r'\s+', ' ', regex=True).str.strip())
    if LABEL_MODE == 'paper':
        s = singularize(s)                                            # (3) 복수 -> 단수
    return s


# FDC food_category (SR Legacy food group) id -> 이름. FDC 배포본 food_category.csv 와 동일.
FDC_CATEGORY = {
    1: 'Dairy and Egg Products', 2: 'Spices and Herbs', 3: 'Baby Foods',
    4: 'Fats and Oils', 5: 'Poultry Products', 6: 'Soups, Sauces, and Gravies',
    7: 'Sausages and Luncheon Meats', 8: 'Breakfast Cereals',
    9: 'Fruits and Fruit Juices', 10: 'Pork Products',
    11: 'Vegetables and Vegetable Products', 12: 'Nut and Seed Products',
    13: 'Beef Products', 14: 'Beverages', 15: 'Finfish and Shellfish Products',
    16: 'Legumes and Legume Products', 17: 'Lamb, Veal, and Game Products',
    18: 'Baked Products', 19: 'Sweets', 20: 'Cereal Grains and Pasta',
    21: 'Fast Foods', 22: 'Meals, Entrees, and Side Dishes', 23: 'Snacks',
    24: 'American Indian/Alaska Native Foods', 25: 'Restaurant Foods',
    26: 'Branded Food Products Database', 27: 'Quality Control Materials',
    28: 'Alcoholic Beverages',
}


def normkey(x, keep='a-z0-9 '):
    """이름 비교용 키. 구두점을 공백으로 지우고 소문자·공백 정규화.

    카테고리 철자 통합(build), 음식 이름 대조(analyze), FoodOn 매칭
    (foodon_match)이 전부 같은 규칙을 쓴다.
    """
    return re.sub(r'\s+', ' ', re.sub(f'[^{keep}]+', ' ', str(x).lower())).strip()


def mesh_lookup(names, session=None, pause=0.12):
    """자유 표기 질환명 -> MeSH descriptor. id.nlm.nih.gov/mesh/lookup REST.

    SPARQL 로 라벨 역조회를 하려다 0 건을 받았다 — MeSH 의 라벨 술어는
    `meshv:prefLabel` 이 아니라 `rdfs:label` 이고, 용어 계층
    (descriptor -> concept -> term) 을 모두 타야 해서 쿼리가 무거웠다. 전용
    lookup REST 가 같은 일을 한 번에 한다.

    `match=exact` 는 **descriptor 라벨만** 본다. 그래서 표기 변형 사다리를 둔다 —
    원문 -> 괄호 제거·쉼표 분해 -> 소유격(Parkinson's -> Parkinson) -> 복수 제거
    -> 'disorders' -> 'Disorder'. exact 를 먼저 보고 없으면 contains 로 내린다.
    먼저 걸린 것을 쓰고 어느 표기·어느 모드로 걸렸는지 함께 돌려준다 —
    해소 근거를 추적할 수 있어야 한다.

    **contains 는 앞에 붙는 수식어를 거르지 못한다.** 'Cognitive impairment' 가
    'Chemotherapy-Related Cognitive Impairment' 로 붙었다 — 화학요법 후 인지장애는
    다른 질환이다. 처음에는 '찾은 라벨이 질의어로 시작할 때만 받는다'는 규칙을
    걸었는데, **쓸 수 없는 기준이었다** — 걸려 떨어진 9 건 중 6 건이
    `Caries -> Dental Caries`, `Cirrhosis -> Liver Cirrhosis` 처럼 앞 수식어가
    질환을 바꾸지 않는 올바른 매칭이었다. 앞에 붙는 말이 해부 위치인지 원인인지는
    문자열로 가를 수 없다.

    그래서 거르지 않고 **`match` 열에 'contains' 라고 적어 감사 가능하게 둔다.**
    틀린 해소는 `setup/disease_alias.csv` 가 덮어쓴다 — 근거를 적어 두고 들어간다.
    이 수작업은 질환 **이름**에만 걸리므로, 어떤 미생물이 들어오는지는 바꾸지
    않는다. 축을 넓히는 기준 자체는 Disbiome 쪽에 그대로 있다.
    """
    import json, time, urllib.parse, urllib.request
    U = 'https://id.nlm.nih.gov/mesh/lookup/descriptor'

    def forms(n):
        f = []
        for part in [n] + re.split(r'\s*,\s*', n):
            part = re.sub(r'\s*\(.*?\)', '', part).strip().replace("'s", '').replace("'", '')
            if len(part) < 3:
                continue
            f.append(part)
            if part.lower().endswith('s'):
                f.append(part[:-1])
            f.append(re.sub(r'\bdisorders?\b', 'Disorder', part, flags=re.I))
        seen = []
        for x in f:
            if x not in seen:
                seen.append(x)
        return seen

    out = {}
    for i, n in enumerate(names):
        for form in forms(n):
            for mode in ('exact', 'contains'):
                q = U + '?' + urllib.parse.urlencode({'label': form, 'match': mode, 'limit': 5})
                try:
                    r = urllib.request.urlopen(urllib.request.Request(
                        q, headers={'User-Agent': 'ourkg/1.0'}), timeout=40)
                    res = json.load(r)
                except Exception:
                    res = []
                time.sleep(pause)
                if res:
                    out[n] = {'mesh_id': res[0]['resource'].rsplit('/', 1)[-1],
                              'mesh_label': res[0]['label'], 'term_used': form,
                              'match': mode}
                    break
            if n in out:
                break
        print(f'\r  MeSH 해소 {i + 1}/{len(names)} — {len(out)}', end='', flush=True)
    print()
    return out


def compound_microbe(sources=('kegg', 'vmh'), rank=None):
    """compound-미생물 링크를 **근거 수준을 걸러서** 읽는다.

    네 곳이 각자 `read_csv` 하고 있었고 아무도 `match_rank` 를 보지 않았다.
    그대로 두면 속 수준 링크가 종 수준과 같은 무게로 집계된다 — KEGG 링크
    10,257 중 **5,686(55%)**이 속 수준이라 과대평가가 작지 않다. 읽는 자리를
    하나로 합치고 거르는 기준을 여기 둔다.

    `rank`:
      'species'  종 수준 매칭만. **이름이 지정된 종을 묻는 질문**(§5.1 방법 1
                 `#6`·`#7` 은 Adlercreutzia equolifaciens, Bifidobacterium
                 longum 을 콕 집는다)에는 이쪽을 써야 한다. 속 링크로 답하면
                 "이 속의 어떤 유전체가" 를 "이 종이" 로 바꿔 읽는 것이다.
      None/'all' 전부. 커버리지를 말할 때와 KG 에 담을 때 쓴다 — 속 수준 링크도
                 실재하는 정보다. 버리지 않고 **구분해서** 담는다.

    VMH/AGORA2 쪽에는 `match_rank` 가 없다. 그쪽은 VMH 의 `ncbiId` 로 taxid 에
    직접 붙으므로 수준 문제가 없다 — 걸러낼 것이 없어 그대로 쓴다.
    """
    import pandas as pd
    out = []
    files = {'kegg': 'compound_microbe.csv', 'vmh': 'compound_microbe_vmh.csv'}
    for src in sources:
        path = os.path.join(OUT, files[src])
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, dtype={'taxid': str})
        if src == 'kegg' and rank in ('species', 'genus'):
            df = df[df.get('match_rank', '') == rank]
        df = df[['taxid', 'kegg']].copy()
        df['source'] = src
        out.append(df)
    if not out:
        return pd.DataFrame(columns=['taxid', 'kegg', 'source'])
    return pd.concat(out).drop_duplicates(['taxid', 'kegg'])


# 중재 행에서 "무중재 대조" 를 가리는 패턴. 대조군이 다른 식단이면 증감이
# "그 식단 대비" 라서 "먹으면 늘어난다" 로 읽을 수 없다.
GMD_NULL_CONTROL = re.compile(
    r'^(no\s|non[\s-]|placebo|habitual diet|normal chow|sedentary)', re.I)


def _gmd_parts(x):
    return [p.strip() for p in re.split(r'[;，]', str(x)) if p.strip() and p.strip() != '*']


def gutmdisorder_intervention(session=None):
    """gutMDisorder 의 **식이 중재** 행 → (중재, 미생물, 증감).

    `gutmdisorder()` 가 버리는 쪽이다. 저쪽은 "질환에서 늘어나는 균" 을 뽑으려고
    `Condition2 == Health` 만 남기는데, 중재 행은 Condition2 가 대조군이라 전부
    탈락한다. 그런데 **중재 행이야말로 `음식 → 미생물` 관측**이다 — 우리
    `E x F^T` 에 미생물이 들어갈 자리가 없는 구조 문제의 빠진 간선이다.

    **여기서도 방향을 믿을 수 있는 행만 남긴다.** 대조군이 무중재가 아니면
    증감이 "다른 식단 대비" 다. 실제로 식이 중재 메타행 147 중 **60 이
    다른 식단과의 대조**였다(저항전분 저 vs 고, 폴리덱스트로스 vs 옥수수섬유,
    저섬유/중지방 vs 저섬유/고지방 …). 그걸 섞으면 부호가 뒤집힌다.

    규칙: Condition1 에서 Condition2 에도 있는 항(동반질환·인구집단)을 뺀 것이
    **중재**다. 남은 Condition2 쪽 항이 없거나(동반질환만 적힌 대조군) 전부
    `No …`/`Placebo`/`Habitual diet` 류면 **무중재 대조**로 본다.
    Human · `InterventionType = Diet, Food, and Nutrition` 만 쓴다.

    열: intervention · taxid · organism · gmd_rank · alteration · pvalue
        · control · evidence · gmd_source
    """
    import requests
    S = session or requests.Session()
    rows = []
    for fn, msheet, asheet, txcol, evcol in GMD_FILES:
        blob = cached_bytes(fn, lambda fn=fn: S.get(GMD_URL + fn, timeout=300).content)
        meta = pd.read_excel(io.BytesIO(blob), sheet_name=msheet)
        assoc = pd.read_excel(io.BytesIO(blob), sheet_name=asheet)
        meta = meta[(meta.HumanOrMouse.astype(str).str.strip() == 'Human')
                    & (meta.ResearchType == GMD_INTERVENTION)
                    & (meta.InterventionType.astype(str)
                       .str.contains('Diet, Food', na=False))]
        keep = []
        for _, r in meta.iterrows():
            p1, p2 = _gmd_parts(r['Condition1']), _gmd_parts(r['Condition2'])
            iv = [x for x in p1 if x not in set(p2)]
            extra = [x for x in p2 if x not in set(p1)]
            if not iv:
                continue
            if extra and not all(GMD_NULL_CONTROL.match(x) for x in extra):
                continue                      # 다른 식단과의 대조 — 방향을 못 쓴다
            keep.append({'Index': r['Index'], 'intervention': ';'.join(iv),
                         'control': r['Condition2'], 'evidence': str(r[evcol])})
        if not keep:
            continue
        k = pd.DataFrame(keep)
        a = assoc.rename(columns={assoc.columns[0]: 'Index'}).merge(k, on='Index')
        for _, r in a.iterrows():
            if pd.isna(r[txcol]):
                continue
            alt = str(r['Alteration']).strip().lower()
            alt = {'increased': 'increase', 'decreased': 'decrease'}.get(alt, alt)
            rows.append({
                'intervention': r['intervention'], 'taxid': str(int(r[txcol])),
                'organism': r['GutMicrobe'],
                'gmd_rank': str(r['Classification']).strip().lower(),
                'alteration': alt, 'pvalue': r.get('PValue'),
                'control': r['control'], 'evidence': r['evidence'],
                'gmd_source': msheet})
    return pd.DataFrame(rows)


def measured_links():
    """측정 상관 링크(`metabolome_check.py build`)를 taxid 로 펼친다.

    원 표는 **속 수준**이다(분변 대사체 코호트가 속까지만 분해한다). 우리
    taxid 의 속명과 맞춰 펼친다. analyze.py 에만 있던 것을 두 모듈이 쓰게
    되면서 여기로 옮겼다 — compound_microbe 와 같은 자리에 둔다.
    """
    import pandas as pd
    p = os.path.join(OUT, 'compound_microbe_measured.csv')
    if not os.path.exists(p):
        return pd.DataFrame(columns=['taxid', 'kegg'])
    m = pd.read_csv(p)
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'),
                      dtype={'taxid': str}).fillna('')
    mic['genus'] = mic['name'].astype(str).str.split().str[0]
    return m.merge(mic[['taxid', 'genus']], on='genus')[['taxid', 'kegg']
                                                        ].drop_duplicates()


def microbe_disease_direction():
    """(균, 질환) 쌍마다 **방향을 믿을 수 있는지** 판정해서 돌려준다.

    전에는 Disbiome 과 gutMDisorder 가 각자 `our:abundanceIn` 을 올렸다. 출처
    태그로만 갈라 두니 KG 를 쓰는 쪽이 모순을 직접 밟는다 — 두 소스가 공유하는
    **613 쌍 중 216(35%)이 방향이 반대**다(우연 50% 보다는 낫지만 3 쌍 중 1 쌍).
    각 소스는 자기 안에서도 어긋난다(Disbiome 7.1% · gutMDisorder 4.4%) —
    같은 균·질환을 다른 연구가 반대로 보고한 것이다.

    그래서 방향은 **쌍 단위로 먼저 합의를 보고** 올린다. 불일치 쌍을 버리지는
    않는다 — "연관은 있고 방향은 모른다" 가 실제로 우리가 아는 것이고, 버리면
    그 사실이 KG 에서 사라진다. `status` 로 구분해 담아 감사 가능하게 둔다.

    status:
      'agreed'    방향이 하나로 모인다. `direction` 이 Elevated/Reduced.
      'conflict'  Elevated 와 Reduced 가 같이 있다. `direction` 은 ''.
    열: taxid · mesh_id · disease · status · direction · n_sources · sources
        · n_elevated · n_reduced
    """
    import pandas as pd
    DIRECTIONAL = ('Elevated', 'Reduced')
    parts = []
    for fn, src in (('microbe_disease_disbiome.csv', 'Disbiome'),
                    ('microbe_disease_gutmdisorder.csv', 'gutMDisorder')):
        path = os.path.join(OUT, fn)
        if not os.path.exists(path):
            continue
        d = pd.read_csv(path, dtype={'taxid': str})
        d = d[(d.get('is_mental', False) | d.get('is_neuro', False))
              & d.outcome.isin(DIRECTIONAL)]
        d = d[['taxid', 'mesh_id', 'disease', 'outcome']].copy()
        d['source'] = src
        parts.append(d)
    cols = ['taxid', 'mesh_id', 'disease', 'status', 'direction',
            'n_sources', 'sources', 'n_elevated', 'n_reduced']
    if not parts:
        return pd.DataFrame(columns=cols)
    a = pd.concat(parts).drop_duplicates(['taxid', 'mesh_id', 'outcome', 'source'])
    rows = []
    for (tx, mid), g in a.groupby(['taxid', 'mesh_id']):
        dirs = set(g.outcome)
        up = int((g.outcome == 'Elevated').sum())
        dn = int((g.outcome == 'Reduced').sum())
        rows.append({
            'taxid': tx, 'mesh_id': mid,
            # 라벨은 소스마다 표기가 달라 가장 긴 것을 쓴다(약어보다 정식 명칭).
            'disease': max(g.disease.astype(str), key=len),
            'status': 'agreed' if len(dirs) == 1 else 'conflict',
            'direction': dirs.pop() if len(dirs) == 1 else '',
            'n_sources': int(g.source.nunique()),
            'sources': '+'.join(sorted(set(g.source))),
            'n_elevated': up, 'n_reduced': dn})
    return pd.DataFrame(rows, columns=cols)


def kegg_map():
    """nutrient_id -> KEGG (논문/매핑표 ID 그대로).

    KEGG_ALIAS 는 **여기에 적용하지 않는다.** F 행렬의 ID 를 정식 ID 로 바꾸면
    ProMENDA 의 E 와 아미노산 13 개가 추가로 만나는데, 재 보니 A층이 엇갈린다 —
    비추천군 Bottom30 은 27 -> 30 으로 완벽해지지만 추천군 Top30 이 22 -> 15 로
    퇴행하고 상위가 마요네즈·버터로 바뀐다(아미노산이 E 에서 대부분 음(-)이라
    단백질이 많은 음식이 내려가고 지방·당이 올라간다). §18.9 적용 규칙 2 에 따라
    기각이다. 자세한 수치는 RESULTS.md 의 §3.2 절.

    KEGG_ALIAS 는 라벨·brite 분류·대사 경로를 **조회할 때만** 쓴다(build.kg()).
    """
    mp = pd.read_csv(os.path.join(BASE, 'setup', 'nutrient_kegg_map.csv'))
    mp = mp[mp['nutrient_kegg'].astype(str).str.startswith('C')]
    return mp


# 논문 §3.2 "we address overlaps in descriptions of food categories across
# different data resources through our self-defined mapping rules"
# branded_food 의 자유문자열 카테고리와 미분류 항목을 SR 28군으로 정규화한다.
# 순서대로 평가하고 먼저 맞는 규칙이 이긴다(구체 카테고리가 재료보다 앞).
CATEGORY_RULES = [
    (r'sausage|frankfurter|hot dog|luncheon|bologna|salami|bacon|ham\b|jerky',
     'Sausages and Luncheon Meats'),
    (r'restaurant|pizza|burger|sandwich|taco|burrito|fast food', 'Fast Foods'),
    (r'cheese|milk|yogurt|cream|dairy|butter|egg', 'Dairy and Egg Products'),
    (r'fish|salmon|tuna|shrimp|crab|shellfish|cod|tilapia|seafood|oyster',
     'Finfish and Shellfish Products'),
    (r'chicken|turkey|poultry|duck', 'Poultry Products'),
    (r'\bpork\b|sausage|pig', 'Pork Products'),
    (r'\bbeef\b|steak|veal|brisket', 'Beef Products'),
    (r'lamb|game|bison|venison', 'Lamb, Veal, and Game Products'),
    (r'bread|bakery|baked|cake|pie|cookie|muffin|roll|bun|cracker|pastry|tortilla',
     'Baked Products'),
    (r'candy|chocolate|sweet|dessert|syrup|sugar|ice cream|frozen novelt', 'Sweets'),
    (r'cereal|granola|oatmeal', 'Breakfast Cereals'),
    (r'grain|pasta|rice|noodle|flour|quinoa', 'Cereal Grains and Pasta'),
    (r'bean|lentil|legume|soy|tofu|chickpea|hummus|peanut butter',
     'Legumes and Legume Products'),
    (r'nut|seed|almond|cashew|walnut|pistachio', 'Nut and Seed Products'),
    (r'fruit|juice|berry|apple|banana|orange|grape', 'Fruits and Fruit Juices'),
    (r'vegetab|salad|potato|tomato|onion|carrot|broccoli|lettuce|mushroom',
     'Vegetables and Vegetable Products'),
    (r'\boil\b|\bfat\b|margarine|shortening|mayonnaise|dressing', 'Fats and Oils'),
    (r'soup|sauce|gravy|broth|salsa|condiment', 'Soups, Sauces, and Gravies'),
    (r'spice|herb|seasoning|pepper\b|\bsalt\b', 'Spices and Herbs'),
    (r'beer|wine|liquor|vodka|whisk|alcohol|rum\b', 'Alcoholic Beverages'),
    (r'drink|beverage|water|coffee|tea\b|soda|cola|smoothie|shake', 'Beverages'),
    (r'snack|chip|popcorn|pretzel|bar\b', 'Snacks'),
    (r'baby|infant|toddler', 'Baby Foods'),
    (r'meal|entree|side dish|dinner|bowl', 'Meals, Entrees, and Side Dishes'),
]
_CATEGORY_RE = [(re.compile(p), g) for p, g in CATEGORY_RULES]


def normalize_category(raw_category, food_name):
    """SR 28군 중 하나로. 숫자 id 로 이미 SR 군이면 그대로 둔다."""
    if raw_category in FDC_CATEGORY.values() and raw_category != 'Branded Food Products Database':
        return raw_category
    text = f'{raw_category} {food_name}'.lower()
    for rx, group in _CATEGORY_RE:
        if rx.search(text):
            return group
    return 'Unclassified'


# ------------------------------------------------------------------
# MENDA / ProMENDA 공통 극성 집계
#
# 두 데이터셋은 열 이름만 다르고 구조가 같다 (Up/Down + Study_type).
# 논문 §4.2.1 의 극성 규약과 Type1 반전은 PROBLEMS.md §7 에서 확정한 것을 쓴다.
# ------------------------------------------------------------------
UP_WORDS = {'up', 'upregulated', 'up-regulated', 'increased', 'increase', 'higher'}
DOWN_WORDS = {'down', 'downregulated', 'down-regulated', 'decreased', 'decrease', 'lower'}


def polarity(value):
    """원 표기 → 기본 해석. 우울증에서 증가 = 악화(-1), 감소 = +1."""
    v = str(value).lower().strip()
    if v in UP_WORDS:
        return -1
    if v in DOWN_WORDS:
        return 1
    return 0


def menda_consensus(df, kegg_col, reg_col, stype_col, name_col=None, study_col=None,
                    shrink_k=10):
    """MENDA 계열 테이블 → compound 별 극성 합의.

    논문 규약: Type1(우울증 vs 대조군)만 up = +1 로 뒤집는다.
    Type2~5 는 치료·반응 비교라 현재 해석(-1)이 이미 논문 규약과 같다.

    반환 열: kegg, name, pos, neg, n_study, n_record, direction, e_shrunk
      direction  다수결 +1 / -1 / 0
      e_shrunk   (pos-neg)/(pos+neg+K) — 근거가 얕으면 0 쪽으로 축소
    """
    d = df[df[kegg_col].astype(str).str.contains(r'C\d{5}', na=False)].copy()
    d['kegg'] = d[kegg_col].astype(str).str.extract(r'(C\d{5})')[0]
    d['incidence'] = d[reg_col].apply(polarity)
    if stype_col in d.columns:
        is_t1 = d[stype_col].astype(str) == 'Type1'
        d.loc[is_t1, 'incidence'] *= -1
    rows = []
    for kegg, sub in d.groupby('kegg'):
        pos = int((sub['incidence'] == 1).sum())
        neg = int((sub['incidence'] == -1).sum())
        rows.append({
            'kegg': kegg,
            'name': sub[name_col].iloc[0] if name_col else '',
            'pos': pos, 'neg': neg,
            'n_study': sub[study_col].nunique() if study_col else len(sub),
            'n_record': len(sub),
            'direction': 1 if pos > neg else (-1 if neg > pos else 0),
            'e_shrunk': (pos - neg) / (pos + neg + shrink_k),
        })
    return pd.DataFrame(rows), d
