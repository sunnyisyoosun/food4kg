"""
논문 Table 1 — 전문가 대조용 20문항 (Supplementary Materials)
==============================================================
`Food4healthKG/Supplements.docx`의 Table 1을 그대로 옮긴 것.

컬럼
  no          문항 번호 (0~19)
  question    질문
  attribute   6개 범주 중 하나
  expected    논문이 Food4healthKG로 얻었다고 보고한 답
  v0, v1, v2  전문가 3인이 원본 데이터에서 직접 찾은 답과 일치하는가 (1/0)

논문 §5.1: "The accuracy of our results against the gold standard answers of the
three experts are found to be 0.95, 0.9, and 0.95, respectively."
-> V0/V1/V2 평균이 각각 0.95 / 0.90 / 0.95 여야 한다(검증용).
"""

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
