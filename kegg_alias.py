"""
KEGG ID alias 표 (single source of truth)
==========================================
논문의 85 compound 목록(heatmap.xlsx)과 다른 데이터가 같은 물질에 서로 다른
KEGG ID를 쓰는 경우를 모은다. 매핑 실패가 아니라 ID 선택 차이다.

두 방향이 있다.

FOOD_ALIAS      논문 ID -> food_nutrient.csv(FDC)의 ID
                영양소 '양'을 가져올 때 쓴다. reconstruct.py.

INCIDENCE_ALIAS 논문 ID -> MENDA / ProMENDA의 ID
                depression '방향'을 조회할 때 쓴다.
                knowledge_query.py, map_promenda.py.

INCIDENCE_ALIAS의 아미노산 9개는 논문이 입체 비특이적 ID를 쓰고
MENDA/ProMENDA는 L-form을 쓰기 때문에 생긴다. ProMENDA에서 이름을
정확 대조해 확인했다(부분 문자열 함정 주의: 'Alanine'은 'Phenylalanine'에도
걸리고, 'Aspart'는 'N-Acetylaspartate'에도 걸린다).
"""

FOOD_ALIAS = {
    'C02823': 'C05776',   # Vitamin B12        <- FDC 'Vitamin B-12'
    'C16522': 'C03242',   # Eicosatrienoic acid <- FDC 'PUFA 20:3'
    # C08319 alpha-Licanic acid: FDC 대응 없음
}

INCIDENCE_ALIAS = {
    'C01733': 'C00073',   # Methionine -> L-Methionine    (ProMENDA 87행)
    'C16436': 'C00183',   # Valine     -> L-Valine        (116행)
    'C16435': 'C00148',   # Proline    -> L-Proline       (115행)
    'C02385': 'C00062',   # Arginine   -> L-Arginine      (62행)
    'C16434': 'C00407',   # Isoleucine -> L-Isoleucine    (116행)
    'C00716': 'C00065',   # Serine     -> L-Serine        (89행)
    'C01401': 'C00041',   # Alanine    -> L-Alanine       (163행)
    'C00736': 'C00097',   # Cysteine   -> L-Cysteine      (20행)
    'C16433': 'C00049',   # Aspartate  -> L-Aspartic acid (96행)
}


def incidence_keys(kegg):
    """compound의 방향을 조회할 때 확인할 KEGG ID.

    **순서가 있는 tuple** 을 돌려준다. 호출부가 next(k for k in ...) 로 첫
    일치를 고르는데, set 을 돌려주면 파이썬 해시 랜덤화 때문에 프로세스마다
    순회 순서가 달라져 결과가 흔들린다(실제로 weight.csv 가 실행마다 두 값을
    오갔다). 논문 ID 를 먼저 보고, 그다음 incidence alias, food alias 순.
    """
    out = []
    for k in (kegg, INCIDENCE_ALIAS.get(kegg), FOOD_ALIAS.get(kegg)):
        if k is not None and k not in out:
            out.append(k)
    return tuple(out)


# ------------------------------------------------------------------
# weight.csv infer 행의 근거별 크기 (step2 knowledge_query.py, step3 map_promenda.py 공유)
#
# weight.csv 8행 = infer / faecal / type1 / type2 × (pos, neg)  (공식 final.py:54-57)
# KG 규칙은 연구 설계·조직을 구분하지 않으므로 infer 행에만 쓴다.
# faecal / type1 / type2 는 step3 가 ProMENDA 부분집합에서 독립 집계한다.
# 값은 논문 근거가 없는 상수다 (PROBLEMS.md §4). 보고 수치를 바꾸지 않으려고
# 이전 값을 유지한다. 키 순서가 판정 우선순위다 — 먼저 맞는 근거가 이긴다.
# ------------------------------------------------------------------
INFER_SCALE = {'MENDA': 1.0, 'Q2': 0.9, 'MiKG': 0.9, 'ontology': 0.8,
               'literature': 1.0, 'group_prior': 0.8}


def infer_scale(source):
    return next((v for k, v in INFER_SCALE.items() if k in source), 0.0)
