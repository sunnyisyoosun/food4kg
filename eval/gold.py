"""
독립 정답셋 (single source of truth)
=====================================
논문에서 compound의 depression 방향이 **명시적으로** 확정된 것만 모은다.
카테고리 결과와 무관하므로 파라미터 튜닝의 비순환적 기준이 된다.

채택 기준: 논문이 부호 또는 PMID로 방향을 직접 못박은 것.
  - Fig. 5   : Positive/Negative Association으로 그려지고 PMID 동반
  - Table 3  : Compound 열에 (+)/(-) 표기
  - Table 4  : Compound 열에 (+)/(-) 표기
  - Table 5  : Result=1(문헌 확인)인 diet recommendation 행

제외: 85 compound 목록(Fig.4(c))에 없는 것은 추천 알고리즘 입력이 아니므로 뺀다.
  C00025 Glutamic acid, C00188 L-Threonine, C00114 Choline,
  C00158 Citric acid, C00097 Cystine, C00047 Lysine — 전부 85에 없음.
  (Table 3/4와 Fig. 4가 서로 다른 compound 집합을 쓰는 논문 내부 불일치)
제외: Table 5 #9 alpha-Tocopherol(C02477)은 Result=0(unknown)이라 방향 없음.
"""

GOLD = {
    # --- Fig. 5 (PMID 동반) ---
    'C06429': ('-', 'Docosahexaenoic acid', 'Fig5 PMID 28439746'),
    'C06424': ('-', 'Tetradecanoic acid',   'Fig5 PMID 20524151'),
    'C00031': ('+', 'D-Glucose',            'Fig5 PMID 30388595'),
    'C00089': ('+', 'Sucrose',              'Fig5 PMID 33948112'),
    'C01496': ('+', 'Fructose',             'Fig5 PMID 33984318'),
    # --- Table 3 ---
    'C00037': ('+', 'Glycine',              'Table 3 #1 Broccoli'),
    'C00072': ('+', 'Ascorbic acid',        'Table 3 #3/#4, Table 5 #14 PMID 34293597'),
    # --- Table 4 ---
    'C00864': ('+', 'Pantothenic acid',     'Table 4 #0/#1 Peaches'),
    # --- Table 5 (Result=1) ---
    'C00253': ('+', 'Nicotinic acid',       'Table 5 #12 Lettuce-anxiety PMID 30709646'),
}


def direction(weight_df, kegg):
    """weight.csv에서 compound의 현재 방향을 읽는다."""
    if kegg not in weight_df.columns:
        return None
    pos, neg = weight_df[kegg].iloc[0], weight_df[kegg].iloc[1]
    return '+' if pos > 0 else ('-' if neg > 0 else '0')


def score(weight_df):
    """(맞은 개수, 비교한 개수, 실패 목록)"""
    ok, n, misses = 0, 0, []
    for k, (d, nm, ref) in GOLD.items():
        ours = direction(weight_df, k)
        if ours is None:
            continue
        n += 1
        if ours == d:
            ok += 1
        else:
            misses.append(f'{k} {nm}({d}->{ours})')
    return ok, n, misses
