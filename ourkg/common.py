"""ourkg 공통 유틸 — 재현 파이프라인(reconstruct.py 등)과 분리된 확장판."""
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
