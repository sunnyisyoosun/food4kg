"""
논문 Table 5 — 문헌 검증 대상 추론 15건
========================================
논문 §5.1 두 번째 평가:

> "We randomly select 15 inferred results from our knowledge graph... We searched
>  the biomedical literature to determine if there was evidence to support or
>  contradict the conclusion. If there is published literature confirming the
>  conclusion, we label the result 'true' (1). If there is contradictory evidence,
>  'false' (-1). If no relevant literature evidence could be found, 'unknown' (0)."

보고된 결과: 11건 confirmed, 1건 contradicted, 3건 unknown.

컬럼
  no, question, attribute, kg_evidence(논문이 Food4healthKG에서 얻은 근거),
  pmid, result(1 / -1 / 0)
"""

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
