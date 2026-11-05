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


def normalize_label(series):
    return (series.astype(str).str.strip().str.lower()
            .str.replace(NUTRIENT_PREFIX, '', regex=True)
            .str.replace(r'\s*-\s*[a-z0-9]{6,12}\s*$', '', regex=True)
            .str.replace(r'\s*\([^)]*\)\s*', ' ', regex=True)
            .str.replace(r'[\s,]+$', '', regex=True)
            .str.replace(r'\s+', ' ', regex=True).str.strip())


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
