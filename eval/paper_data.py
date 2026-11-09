"""
논문 전사 자료 — 표·수치를 논문에서 그대로 옮긴 것
====================================================
세 가지를 한 파일에 모은다. 전부 "논문이 무엇을 적었는가" 이고 측정 코드가 아니다.

  TABLE1          Supplement Table 1 — 전문가 대조용 20문항
  TABLE5          Table 5 — 문헌 검증 15건
  PAPER_NUMBERS   논문이 제시한 수치 29개 체크리스트 (+ 강제 규칙)

실행: python3 eval/paper_data.py
"""
import sys

# ==========================================================================
# Supplement Table 1 — 전문가 대조용 20문항
# ==========================================================================
# 논문 Table 1 — 전문가 대조용 20문항 (Supplementary Materials)
# ==============================================================
# `Food4healthKG/Supplements.docx`의 Table 1을 그대로 옮긴 것.
# 
# 컬럼
#   no          문항 번호 (0~19)
#   question    질문
#   attribute   6개 범주 중 하나
#   expected    논문이 Food4healthKG로 얻었다고 보고한 답
#   v0, v1, v2  전문가 3인이 원본 데이터에서 직접 찾은 답과 일치하는가 (1/0)
# 
# 논문 §5.1: "The accuracy of our results against the gold standard answers of the
# three experts are found to be 0.95, 0.9, and 0.95, respectively."
# -> V0/V1/V2 평균이 각각 0.95 / 0.90 / 0.95 여야 한다(검증용).

TABLE1 = [
    (0,  'Lists of fruits which contains Lysine', 'food categories',
     'Melons, oranges, strawberries, etc', 1, 1, 1),
    (1,  'The food categories of the cola', 'food categories',
     'Soft drinks, beverages', 1, 1, 1),
    (2,  'The food categories of the soy milk', 'food categories',
     'Milk substitutes, beverages', 1, 1, 1),
    (3,  'The lists of baby food', 'food categories',
     'Carrots(baby food), plums(baby food), etc', 1, 1, 1),
    (4,  'The weight of folate that peach pie can provides in gut', 'compounds in food and gut',
     '0.046mg/100g', 1, 1, 1),
    (5,  'The difference of retinol between milk and yogurt', 'compounds in food and gut',
     '0.127mg/100g milk, 0.702mg/100g yogurt', 1, 1, 1),
    (6,  'The weight of citric acid can Adlercreutzia equolifaciens taken from grape juice',
     'compounds in food and gut', '309mg/100g', 1, 1, 1),
    (7,  'The weight of ascorbic acid can Bifidobacterium longum taken from lettuce',
     'compounds in food and gut', '15mg/100g', 1, 1, 1),
    (8,  'The rank of Potassium weight in food', 'weight calculation',
     'Beans, Egg whites, Almonds, etc', 1, 1, 1),
    (9,  'The weight of Vitamin B12 in mixed diet orange and sausage', 'weight calculation',
     '0.072mg/200g', 1, 1, 1),
    (10, 'The weight of Vitamin B6 in egg and whole milk', 'weight calculation',
     '6.591mg/200g', 1, 1, 1),
    (11, 'The microbial related mental disorders', 'disease classification',
     'Autistic disorder, developmental disorder, etc', 1, 1, 1),
    (12, 'The difference between depression and autistic disorder', 'disease classification',
     'Depression(Mood disorder) / Autistic disorder(developmental disorder)', 1, 1, 0),
    (13, 'The list of diseases in mental disorders', 'disease classification',
     'Eating disorder, bipolar disorder, etc', 1, 1, 1),
    (14, 'The vitamins may have effects on depression', 'compounds categories',
     'Vitamin B1-B5, VC, VE, etc', 0, 1, 1),
    (15, 'The alkaloids involved from food', 'compounds categories',
     'Caffeine, theobromine, etc', 1, 0, 1),
    (16, 'The categories of biological compounds', 'compounds categories',
     'Peptides, alkaloids, etc', 1, 1, 1),
    (17, 'The Bacteroides may have effects on depression', 'bacteria taxonomy',
     'Bacteroides ovatus, vulgatus, fragilis', 1, 1, 1),
    (18, 'The taxonomy tree of Escherichia coli', 'bacteria taxonomy',
     'Escherichia, Enterobacteriaceae, etc', 1, 1, 1),
    (19, 'The top 3 genus of bacteria related to disease', 'bacteria taxonomy',
     'Streptococcus, Bacteroides, Prevotella', 1, 0, 1),
]

PAPER_ACCURACY = (0.95, 0.90, 0.95)   # 논문 §5.1이 보고한 V0/V1/V2 정확도


# ==========================================================================
# Table 5 — 문헌 검증 15건
# ==========================================================================
# 논문 Table 5 — 문헌 검증 대상 추론 15건
# ========================================
# 논문 §5.1 두 번째 평가:
# 
# > "We randomly select 15 inferred results from our knowledge graph... We searched
# >  the biomedical literature to determine if there was evidence to support or
# >  contradict the conclusion. If there is published literature confirming the
# >  conclusion, we label the result 'true' (1). If there is contradictory evidence,
# >  'false' (-1). If no relevant literature evidence could be found, 'unknown' (0)."
# 
# 보고된 결과: 11건 confirmed, 1건 contradicted, 3건 unknown.
# 
# 컬럼
#   no, question, attribute, kg_evidence(논문이 Food4healthKG에서 얻은 근거),
#   pmid, result(1 / -1 / 0)

TABLE5 = [
    (0,  'Autistic disorder and depression',     'Complication',
     'Bifidobacterium longum',  '31560663', 1),
    (1,  'Parkinson disorder and depression',    'Complication',
     'Streptococcus mutans',    '28802935', 1),
    (2,  'Learning disabilities and autism',     'Complication',
     'Escherichia coli',        '15165430', 1),
    (3,  'Anxiety and depression',               'Complication',
     'Escherichia coli',        '25370281', 1),
    (4,  'Bipolar disorder and depression',      'Complication',
     'Lactobacillus plantarum', '25533909', 1),
    (5,  'Learning disabilities and depression', 'Complication',
     'Bacillus cereus',         None,       0),
    (6,  'Parkinson disorder and autism',        'Complication',
     'Lactobacillus reuteri',   None,       0),
    (7,  'Alzheimer Disease and autism',         'Complication',
     'Bacteroides fragilis',    '34827633', 1),
    (8,  'Garlic and Alzheimer Disease',         'Diet recommendation',
     'Threonine',               '16395514', 1),
    (9,  'Milk and Learning disabilities',       'Diet recommendation',
     'alpha-Tocopherol',        None,       0),
    (10, 'Egg products and depression',          'Diet recommendation',
     'Cystine',                 '29948220', -1),
    (11, 'Coffee and parkinson disorder',        'Diet recommendation',
     'Threonine',               '31416163', 1),
    (12, 'Lettuce and anxiety',                  'Diet recommendation',
     'Nicotinic acid',          '30709646', 1),
    (13, 'Sweets and depression',                'Diet recommendation',
     'L-Threonine',             '25230537', 1),
    (14, 'Onion and depression',                 'Diet recommendation',
     'Ascorbate',               '34293597', 1),
]

PAPER_COUNTS = {1: 11, -1: 1, 0: 3}   # 논문이 보고한 판정 분포


# ==========================================================================
# 논문 수치 체크리스트
# ==========================================================================
# 논문이 제시한 수치 전수 목록 — 판정 신뢰도 장치
# =================================================
# §17.9·§17.10·§17.12·§17.14·§17.16 에서 "논문이 틀렸다" 는 판정이 다섯 번 뒤집혔다.
# 모두 같은 원인이었다 — **정의를 좁게 잡고 곧바로 결함으로 단정**.
# 
# 그래서 논문의 수치를 전부 목록으로 고정하고, 각 수치에 상태와 근거를 붙인다.
# 규칙은 하나다.
# 
#     MISMATCH 로 표시하려면 hunted=True 여야 한다.
#     즉 `python3 tools/paper.py hunt <값>` 을 돌려 후보가 없음을 보인 뒤에만
#     "배포본에서 나오지 않는다" 고 말할 수 있다.
# 
# 이 규칙은 아래 _check() 에서 강제된다. 어기면 import 가 실패한다.
# 
# 상태
#   MATCH      배포 자료에서 정확히 재현됨
#   MATCH_EST  재현되지만 유도가 우리 재구성이다 (확정으로 쓰지 말 것)
#   MISMATCH   탐색했으나 나오지 않음 (hunted 필수)
#   UNTESTED   아직 검증하지 않음
#   NA         재현 대상이 아님 (전문가 평가 등)
# 
# 실행: python3 eval/paper_data.py

# ============================================================
# 논문이 compound 의 depression 방향을 **명시한** 것만 (옛 eval/gold.py)
# 독립 정답셋 (single source of truth)
# =====================================
# 논문에서 compound의 depression 방향이 **명시적으로** 확정된 것만 모은다.
# 카테고리 결과와 무관하므로 파라미터 튜닝의 비순환적 기준이 된다.
# 
# 채택 기준: 논문이 부호 또는 PMID로 방향을 직접 못박은 것.
#   - Fig. 5   : Positive/Negative Association으로 그려지고 PMID 동반
#   - Table 3  : Compound 열에 (+)/(-) 표기
#   - Table 4  : Compound 열에 (+)/(-) 표기
#   - Table 5  : Result=1(문헌 확인)인 diet recommendation 행
# 
# 제외: 85 compound 목록(Fig.4(c))에 없는 것은 추천 알고리즘 입력이 아니므로 뺀다.
#   C00025 Glutamic acid, C00188 L-Threonine, C00114 Choline,
#   C00158 Citric acid, C00097 Cystine, C00047 Lysine — 전부 85에 없음.
#   (Table 3/4와 Fig. 4가 서로 다른 compound 집합을 쓰는 논문 내부 불일치)
# 제외: Table 5 #9 alpha-Tocopherol(C02477)은 Result=0(unknown)이라 방향 없음.
# ============================================================
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


MATCH, MATCH_EST, MISMATCH, UNTESTED, NA = (
    'MATCH', 'MATCH_EST', 'MISMATCH', 'UNTESTED', 'NA')

# (위치, 값, 상태, 근거)   hunted 여부는 HUNTED 에 적는다
PAPER_NUMBERS = [
    # ---- §3.1 본문 ----
    ('§3.1 FDC food samples',        34250,      MATCH,     '§17.1 fdc_id 고유수'),
    ('§3.1 KEGG metabolites',          230,      MATCH,     '§17.14 pq:hasNutrients 목적어'),
    ('§3.1 NCBI gut microbes',      322917,      MISMATCH,  '§17.14 공개 KG 326,533 (1.2% 차)'),
    ('§3.1 MENDA associations',       5675,      MATCH_EST, '§17.4 원본 xlsx 행 수'),
    ('§3.1 MiKG associations',        1234,      MATCH,     '§17.1 Triples 열'),
    ('§3.1 총 triples',           13346991,      MATCH_EST, '§17.1 = 배포 4,314,742 + 추론 + SNOMED'),
    ('§3.1 총 relations',              140,      MISMATCH,  '§17.9 논문 열 합은 156'),
    # ---- Table 1 Relation 열 ----
    ('Table1 Relation 8소스',            8,      MATCH,     '§17.9 합 정의로 8/8'),
    # ---- Table 1 Entity 열 ----
    ('Table1 Entity 8소스',              8,      MATCH,     '§17.10 노드 수 정의로 8/8'),
    ('Table1 Entity Total',        1637915,      MISMATCH,  '§17.12 열 합 4,995,950 과 불일치'),
    ('Table1 Inferred',            4741023,      MISMATCH,  '§17.20 규칙(a) 재구현 2,436,403 (51.4%)'),
    # ---- Table 1 Triples 열 ----
    ('Table1 Triples 9소스',             7,      MATCH,     '§17.1 7/9 일치 (MENDA·SNOMED 제외)'),
    # ---- §3.2 ----
    ('§3.2 food entities',         1220480,      MATCH,     '§17.10'),
    ('§3.2 food categories',           128,      MISMATCH,  '§17.16 서술대로 병합하면 64'),
    ('§3.2 compounds',               23212,      MATCH,     '§17.10'),
    ('§3.2 gut microbiota',         984031,      MATCH,     '§17.10'),
    ('§3.2 mental disorders',         3505,      MATCH_EST, '§17.12 MENDA 2,367 + MiKG 1,138'),
    ('§3.2 normalized total',      1637915,      MISMATCH,  '§17.12 네 수치 합은 1,010,876'),
    # ---- §3.3 ----
    ('§3.3 관계 어휘 6종',               6,      MATCH,     '§17.8 6/6 존재'),
    # ---- §4.2 ----
    ('§4.2.1 food samples',            135,      MATCH,     'scorecard [1]'),
    ('§4.2.1 compounds',                85,      MATCH,     'scorecard [1] heatmap.xlsx'),
    ('§4.2.1 PCA 주성분',                5,      MATCH,     'scorecard [1] PCA(Xn⊙E) 80%'),
    ('§4.2.3 Top-K',                    30,      NA,        '설정값'),
    ('§4.2.3 compound 그룹',             6,      MATCH,     'heatmap.xlsx 4행'),
    # ---- §5.1 ----
    ('§5.1 문항 수',                    20,      MATCH,     'eval/m1.py'),
    ('§5.1 aspect 수',                   6,      MATCH,     'eval/m1.py assert'),
    ('§5.1 전문가 정확도 V0',          0.95,      NA,        '전문가 답 미공개 (§17.3)'),
    ('§5.1 추론 검증 건수',             15,      MATCH,     'TABLE5'),
    ('§5.1 confirmed',                  11,      NA,        'PubMed 재검색 미실시'),
]

# MISMATCH 로 표시하려면 tools/paper.py hunt 으로 탐색한 기록이 있어야 한다.
HUNTED = {
    322917: '§17.14 Bacteria_Ontology 술어별 전수 — 일치 없음',
    140: '§17.9 논문 자체 산술 (탐색 대상 아님, 열 합 156 로 확정)',
    1637915: '§17.12 9소스 Entity 부분집합 합 전수 — 조합 없음',
    4741023: '§17.20 규칙(a) 전이 추론을 직접 재구현해 2,436,403 생성 (51.4%). '
             '배포본 자체에는 0건',
    128: '§17.16 부분집합 6 × 정규화 12 = 72 조합 + tools/paper.py hunt — 일치 없음',
}


def _check():
    bad = [(w, v) for w, v, st, _ in PAPER_NUMBERS
           if st == MISMATCH and v not in HUNTED]
    if bad:
        raise AssertionError(
            'MISMATCH 인데 탐색 기록이 없다. tools/paper.py hunt 을 돌리고 HUNTED 에 적을 것: '
            + ', '.join(f'{w}({v})' for w, v in bad))


_check()


def audit():
    """논문 §5.1 평가 방식 자체를 점검한다 (§17.27).
    방법 1 은 Supplement Table 1 의 V0/V1/V2 열에서, 방법 2 는 Table 5 에서
    전부 계산된다 — 우리가 손으로 옮겨 적는 수치가 없다."""
    n = len(TABLE1)
    per = [sum(t[i] for t in TABLE1) for i in (4, 5, 6)]
    acc = tuple(round(v / n, 2) for v in per)
    vsum = [t[4] + t[5] + t[6] for t in TABLE1]
    dist = {k: vsum.count(k) for k in (0, 1, 2, 3)}
    # 전문가 쌍별 일치 (두 사람이 같은 판정을 내린 문항 수)
    pair = {}
    for i, j, nm in ((4, 5, 'V0-V1'), (4, 6, 'V0-V2'), (5, 6, 'V1-V2')):
        pair[nm] = sum(1 for t in TABLE1 if t[i] == t[j])

    attrs = {}
    res = {}
    for r in TABLE5:
        attrs[r[2]] = attrs.get(r[2], 0) + 1
        res[r[5]] = res.get(r[5], 0) + 1
    m = len(TABLE5)
    return dict(
        # 방법 1
        n_question=n, per_expert=per, accuracy=acc,
        accuracy_matches_paper=(acc == PAPER_ACCURACY),
        vsum_dist=dist, consensus=dist[3],
        majority_wrong=dist[0] + dist[1],   # 2인 이상이 "KG 가 틀렸다" 로 본 문항
        pair_agreement=pair,
        # 방법 2
        n_item=m, attributes=attrs,
        inferred_items=attrs.get('Complication', 0),
        not_inferred_items=attrs.get('Diet recommendation', 0),
        confirmed=res.get(1, 0), unknown=res.get(0, 0), contradicted=res.get(-1, 0),
        confirmed_rate=round(res.get(1, 0) / m, 2),
        confirmed_rate_excl_unknown=round(
            res.get(1, 0) / max(m - res.get(0, 0), 1), 2),
    )


def audit_report():
    a = audit()
    print('=' * 78)
    print('논문 §5.1 평가 방식 점검')
    print('=' * 78)
    print('  [방법 1] 전문가 20문항')
    print(f'    전문가별 "KG 가 맞다" 판정  {a["per_expert"]} / {a["n_question"]}'
          f'  → {a["accuracy"]}')
    print(f'    논문이 보고한 0.95/0.9/0.95 와 일치: {a["accuracy_matches_paper"]}'
          '  → 이 수치는 gold 대비 정확도가 아니라 **전문가별 동의율**이다')
    print(f'    vsum 분포 {a["vsum_dist"]}   3인 만장일치 {a["consensus"]}, '
          f'2인 이상이 오답으로 본 문항 {a["majority_wrong"]}')
    print(f'    전문가 쌍별 일치 문항 {a["pair_agreement"]} / {a["n_question"]}'
          '  (IAA 는 논문에 보고되지 않는다)')
    print('  [방법 2] 문헌 15건')
    print(f'    Attributes 구성 {a["attributes"]}'
          f'  → "inferred results" 라면서 {a["not_inferred_items"]}건은 추론이 아니다')
    print(f'    결과 confirmed {a["confirmed"]} / unknown {a["unknown"]} / '
          f'contradicted {a["contradicted"]}')
    print(f'    확인율 {a["confirmed_rate"]} (unknown 을 분모에서 빼면 '
          f'{a["confirmed_rate_excl_unknown"]})')
    return a


def summary():
    c = {}
    for _, _, st, _ in PAPER_NUMBERS:
        c[st] = c.get(st, 0) + 1
    return dict(total=len(PAPER_NUMBERS), **c)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'audit':
        audit_report()
        raise SystemExit
    s = summary()
    print('=' * 78)
    print('논문 수치 체크리스트')
    print('=' * 78)
    for w, v, st, why in PAPER_NUMBERS:
        mark = {'MATCH': '✔', 'MATCH_EST': '~', 'MISMATCH': '✘',
                'UNTESTED': '?', 'NA': '-'}[st]
        val = f'{v:,}' if isinstance(v, int) else str(v)
        print(f'  {mark} {w:26s} {val:>12s}  {st:10s} {why}')
    print()
    print('  ' + '  '.join(f'{k} {v}' for k, v in s.items()))
    print()
    print('  규칙: MISMATCH 는 tools/paper.py hunt 탐색 후에만 표시할 수 있다 (HUNTED).')
    if s.get('UNTESTED'):
        print(f'  ⚠ 미검증 {s["UNTESTED"]}건 남음')
