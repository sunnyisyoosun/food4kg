# ourkg 결과 정리

논문 Fu et al. (2023) *Food4healthKG* 의 **구축 방식과 평가 방식**을 그대로 쓰고,
데이터만 최신 공개본(FDC 2026-09 전체 + ProMENDA 2024 + KEGG/NCBI/MeSH 현재 조회)으로
바꿔 만든 지식그래프의 결과다.

원 논문 **재현**(`reconstruct.py` → `run_recommendation.py`)과는 분리된 별도 산출물이다.
재현 수치는 [`../REPRODUCTION.md`](../REPRODUCTION.md), 미해결 문제는
[`../PROBLEMS.md`](../PROBLEMS.md), 파이프라인 사용법·설계 결정은
[`README.md`](README.md) 에 있다.

재현 방법: `python3 ourkg/run_all.py`

---

## 1. 한눈에

| | 논문 (2023) | ourkg |
|---|---|---|
| triple | 13,346,991 | **3,166,603** |
| entity | 1,637,915 | 785,393 |
| relation | 140 | 20 |
| 음식 | 34,250 샘플 → 135 사용 | 14,719 (추천 코호트 12,574) |
| compound | 85 | 130 |
| 음식당 측정 compound 중앙값 | 33 | **47** |
| 우울증 극성이 확정된 compound | 85 (공개 소스로는 69) | 66 |
| §5.1 방법 2 문헌 검증 | 11 / 15 | **4 / 15** |

triple 수가 논문의 1/4 인 것은 온톨로지 축(SNOMED CT 429만, NCBI taxonomy 전체 131만,
FoodOn·중국 식품 온톨로지 30만)을 통합하지 않았기 때문이다.
**음식-성분 축만 보면 우리 쪽이 더 크다 (314만 vs 233만).**

---

## 2. KG 규모 (논문 Table 1 대응)

`ourkg/out/kg_stats.csv`

| source | relation | entity | triples |
|---|---:|---:|---:|
| FoodData Central | 9 | 783,035 | 3,146,277 |
| MiKG | 6 | 1,060 | 6,802 |
| MeSH | 2 | 245 | 5,400 |
| ProMENDA | 6 | 1,289 | 5,150 |
| KEGG | 3 | 213 | 2,384 |
| NCBI taxonomy | 5 | 210 | 590 |
| **Total** | **20** | **785,393** | **3,166,603** |

논문 Table 1 과 대조:

| source | 논문 triples | ourkg triples | 비고 |
|---|---:|---:|---|
| FoodData Center | 2,332,603 | 3,146,277 | FDC 전체 배포본 사용 |
| FoodOn | 79,769 | — | 미통합 |
| Chinese Food Ontology | 215,863 | — | 미통합 |
| KEGG | 74,286 | 2,384 | compound-미생물 경로만 재계산 |
| NCBI taxonomy | 1,306,152 | 590 | 정신질환 연관 127종만 |
| MENDA | 5,675 | 5,150 (ProMENDA) | 후속판으로 교체 |
| MiKG | 1,234 | 6,802 | 신경전달물질 경로 포함 |
| SNOMED CT | 4,291,226 | — | 미통합 |
| MESH | 261,556 | 5,400 | tree number 만 |

### 데이터 처리 경로

```
FDC food_nutrient.csv  27,195,013 행
  → KEGG 매핑 영양소만              10,961,631 행 (compound 134)
  → 단위 g 환산 (MG 1e-3, UG 1e-6, IU 1e-6)
  → 논문 §3.2 라벨 병합      1,949,651 항목 → 482,937 음식
  → 음식당 compound ≥ 20            14,719 음식 / compound 130 / 값 768,157

ProMENDA  22,519 레코드 / 995 연구
  → KEGG ID 보유                    17,653 행 / compound 1,412
  → Type1 극성 반전(논문 규약)      10,927 행
  → compound별 다수결               +623 / −664 / tie 125
  → FDC compound 130 과 교집합      66종

KEGG REST (재계산)
  compound → EC                     86 compound / 745 링크
  → KO → organism                   compound-미생물 2,124 링크 (compound 59 / 미생물 82)

MeSH SPARQL / NCBI efetch
  미생물-질환 2,076 관계 중 F03 정신질환 115건 (미생물 89 / 질환 6)
  NCBI 로 학명·rank·계통 갱신       127종
  MiKG 원본: 미생물→신경전달물질 82, 신경전달물질→정신질환 41
             → 이어 붙인 미생물-정신질환 406쌍 (정신질환 11종)
```

---

## 3. 추천 결과 (depression)

`ourkg/out/recommendation.csv` — 12,569 음식 전체 순위

### Top 10

| 순위 | 음식 | 카테고리 | 점수 |
|---:|---|---|---:|
| 1 | Sugar substitute, sucralose, powder | Sweets | 24.42 |
| 2 | Honey | Sweets | 21.17 |
| 3 | Leavening agents, cream of tartar | Baked Products | 17.91 |
| 4 | Lettuce, cos or romaine, raw | Vegetables | 13.73 |
| 5 | Pears, canned, heavy syrup pack | Fruits and Fruit Juices | 13.63 |
| 6 | Beverages, Energy Drink, sugar free | Beverages | 13.41 |
| 7 | Applesauce, canned, sweetened | Fruits and Fruit Juices | 13.33 |
| 8 | Pears, canned, light syrup pack | Fruits and Fruit Juices | 12.72 |
| 9 | Beverages, Energy Drink with HFCS | Beverages | 12.24 |
| 10 | Squash, winter, butternut, raw | Vegetables | 11.97 |

### Bottom 10

| 순위 | 음식 | 카테고리 | 점수 |
|---:|---|---|---:|
| 12560 | Lamb, loin, trimmed to 1/4" fat, raw | Lamb, Veal, and Game | −411.43 |
| 12561 | Beef, rib large end, prime, roasted | Beef Products | −411.43 |
| 12562 | Beef, rib whole, prime, broiled | Beef Products | −411.46 |
| 12563 | Beef, rib whole, prime, roasted | Beef Products | −411.53 |
| 12564 | Dutch brand loaf, chicken, pork and beef | Sausages and Luncheon Meats | −411.59 |
| 12565 | Beef, rib small end, prime, roasted | Beef Products | −411.66 |
| 12566 | Beef, rib large end, all grades, roasted | Beef Products | −411.72 |
| 12567 | Bologna, beef and pork | Sausages and Luncheon Meats | −411.74 |
| 12568 | Beef, rib whole, choice, roasted | Beef Products | −412.21 |
| 12569 | Beerwurst, pork and beef | Sausages and Luncheon Meats | −413.05 |

### 카테고리 분포 — 논문 §4.2.3 과의 대조

| 카테고리 | Top 30 | Bottom 30 |
|---|---:|---:|
| **Alcoholic Beverages** | **12** | 0 |
| Beverages | 6 | 0 |
| Fruits and Fruit Juices | 4 | 0 |
| Sweets | 3 | 0 |
| Vegetables and Vegetable Products | 2 | 0 |
| Finfish and Shellfish Products | 1 | 0 |
| Baby Foods | 1 | 0 |
| Baked Products | 1 | 0 |
| **Beef Products** | 0 | **20** |
| **Lamb, Veal, and Game Products** | 0 | **5** |
| **Sausages and Luncheon Meats** | 0 | **4** |
| Poultry Products | 0 | 1 |

**비추천 쪽은 논문과 그대로 일치한다.** 논문 §4.2.3 은 비추천을 "sausage products,
baked products, and sweets", Fig.5 피라미드 상단을 "barbecue products, beef products,
sausages, and luncheon meats, pork products" 로 적는다. 우리 Bottom 30 은 소고기 20 /
양고기 5 / 소시지·런천미트 4 로 같은 구성이다.

**추천 쪽은 일치하지 않는다.** 논문은 "mainly fish and shellfish products, as well as
fruits and vegetables" 라고 했고, 우리 Top 30 은 **칵테일류 12 / 음료 6** 이 절반 이상을
차지한다. 과일 4 / 채소 2 / 어패류 1 은 들어오지만 소수다.

원인은 둘이고, 둘 다 데이터를 바꾼 데서 온다.

1. **당류** — 논문 Fig.4(c) 의 추천 음식군 히트맵에서 가장 진한 축이 탄수화물
   (D-glucose, maltose, sucrose, starch, fructose)이고, §4.2.3 은 양파의 D-glucose 를
   추천 근거로 든다. 즉 당류가 위로 오는 것은 **논문의 기전 그대로**다. 음식 모집단이
   135종으로 큐레이션되지 않으면 같은 기전이 설탕·시럽절임 과일·에너지드링크를 끌어올린다.
2. **에탄올** — ProMENDA 에서 Ethanol 은 연구 3건(pos 4 : neg 1)으로 "우울증에서 감소"
   쪽이라 E 가 +가 된다. 논문의 85 compound 목록에는 에탄올이 없었다. 근거량 축소
   (`E_MODE=shrunk`)로도 칵테일류는 Top 30 에 남는다 — 칵테일은 측정 성분이 적어
   에탄올이 프로파일을 지배하기 때문이다.

**이것은 우리 KG 가 "칵테일을 우울증에 권한다"는 뜻이 아니라, 논문의 알고리즘이
큐레이션된 음식 목록과 큐레이션된 compound 목록에 의존한다는 뜻이다.** 논문 §4.2.1 의
"135 food samples and their associated 85 component compounds" 가 어떻게 선정됐는지
본문에 없고(REPRODUCTION §4), 그 선정이 결과의 상당 부분을 만든다.

시각화: `ourkg/out/recommendation.png` (논문 Fig.4(b) 대응 t-SNE)

---

## 4. 평가 — 논문 §5.1

### 방법 1 (human annotation) — Supplement Table 1 의 20문항

논문은 전문가 3인과 대조해 정확도 0.95 / 0.90 / 0.95 를 보고한다. 전문가 답변 자체가
공개되지 않았으므로(`eval/m1.py` 서두 참조) 이 수치는 재현 대상이 아니다. 대신 우리 KG 가
각 측면을 답할 축을 갖췄는지를 집계한다. `ourkg/out/eval_method1.csv`

| 측면 | 문항 수 | 판정 | 근거 |
|---|---:|:---:|---|
| weight calculation | 3 | O | 성분 중량 768,157건 (g/100g) |
| compounds categories | 3 | O | KEGG compound 130 |
| compounds in food and gut | 4 | O | FDC 성분 + KEGG compound-미생물 |
| bacteria taxonomy | 3 | O | NCBI taxonomy 127종, 학명·rank·계통 갱신 |
| food categories | 4 | △ | FDC SR 27군만. FoodOn·중국 식품 온톨로지 미통합 |
| disease classification | 3 | △ | MeSH tree number 만. SNOMED CT 미통합 |

완전 답변 **13** / 부분 **7** / 불가 **0**

### 방법 2 (문헌 논증) — 추론 15건 PubMed 검증

논문은 수작업 검색이었다. 여기서는 E-utilities 로 자동화하되, 판정을 **두 엔티티 +
KG 가 댄 근거 물질이 모두 함께 나오는 논문이 있는가**로 둔다. 질환 이름 두 개만
검색하면 anxiety + depression 이 16,578건이라 아무것도 검증하지 못하기 때문이다.
(그 수치는 `n_hits_pair_only` 로 함께 남긴다.) `ourkg/out/eval_method2.csv`

| | 확인 (1) | 미확인 (0) | 반대 (−1) |
|---|---:|---:|---:|
| **ourkg** | **4 / 15** | 11 / 15 | 자동 판정하지 않음 |
| 논문 Table 5 | 11 / 15 | 3 / 15 | 1 / 15 |

유형별로 보면 결과가 갈린다.

| 유형 | 건수 | 확인 | 내용 |
|---|---:|---:|---|
| Diet recommendation | 7 | **4** | Beef·Lamb × depression × palmitic acid (PMID 23463571, 165282) |
| Complication | 8 | **0** | 공유 미생물까지 포함하면 뒷받침 문헌이 없다 |

**Complication 추론 0건은 보고할 만한 결과다.** 논문 Table 5 의 Complication 8건은
모두 확인(1)이다. 우리가 MiKG 공개본에서 복원한 406쌍은 "미생물 → 신경전달물질 →
정신질환" 경로를 이어 붙여 만든 것인데, 논문이 쓴 MiKG 1,234 관계(비공개)와 다른
것으로 보인다. 공유 미생물을 고를 때는 시드 고정 난수를 쓴다 — 문헌이 가장 잘 붙는
것을 고르면 검증이 아니라 확증 편향이 된다.

### §4.1 SPARQL Query 1·2·3

`ourkg/out/eval_sparql.json` — rdflib 로 `ourkg.nt` 3,157,890 triple 을 적재(61초)해 실행.

논문 Supplementary Query 1 을 그대로 쓰면 음식 라벨 regex 가 중량 노드 768,157개와
조인되어 끝나지 않는다(논문 쪽 쿼리도 같은 문제를 갖는다 — `eval/paper_sparql.py`).
여기서는 음식 URI 를 먼저 싸게 찾아 subject 에 묶는다. 질문의 의미는 같고 조인 순서만 다르다.

| 쿼리 | 논문 대응 | 결과 | 시간 |
|---|---|---:|---:|
| Q1 혼합 식단의 영양소 흡수량 | Table 2 | 72행 (달걀 6 × 우유 6) | 3.0s |
| Q2 성분 → 장내세균 → 우울증 | Table 3 | 200행 | <0.1s |
| Q3 우울증 + 합병증에 동시 작용 | Table 4 | 100행 | <0.1s |

**Q1 (Table 2 대응)** — 달걀 + 우유 혼합 식단의 리보플라빈 (g / 200 g)

| 달걀 | 우유 | 영양소 | 합계 |
|---|---|---|---:|
| Egg, whole, cooked, hard-boiled | Milk, 2%, protein fortified | Riboflavin | 0.000707 |
| Egg, whole, cooked, hard-boiled | Milk, 2%, with nonfat milk solids | Riboflavin | 0.000707 |
| Egg, whole, cooked, hard-boiled | Milk, 2%, without added vitamin A/D | Riboflavin | 0.000698 |
| Egg, whole, cooked, fried | Milk, 2% | Riboflavin | 0.000689 |

논문 Table 2 처럼 조합마다 값이 조금씩 달라지는 구조가 그대로 재현된다.

**Q2 (Table 3 대응)** — 우울증 극성이 있는 성분을 대사하는 장내세균

| 성분 | 세균 | 관계 |
|---|---|---|
| Glycine | Agathobacter rectalis | hasPositiveAssociation |
| Glycine | Akkermansia muciniphila | hasPositiveAssociation |
| Glycine | Bacteroides fragilis | hasPositiveAssociation |
| Glycine | Bacteroides ovatus | hasPositiveAssociation |

논문 Table 3 은 같은 자리에 L-Threonine × *Bacteroides ovatus* / *vulgatus* (negative) 를 둔다.
우리 KG 에서도 *Bacteroides ovatus* 가 나오지만 성분과 극성이 다르다 —
compound-미생물 링크를 KEGG 에서 다시 계산했고 극성은 ProMENDA 에서 나오기 때문이다.

**Q3 (Table 4 대응)** — 우울증 성분 → 세균 → 다른 정신질환

| 성분 | 세균 | 질환 |
|---|---|---|
| 4-Hydroxyproline | Streptococcus salivarius | Autism |
| 5-Methyltetrahydrofolic acid | Clostridium butyricum | Autism |
| Alpha-Linolenic acid | Hominimerdicola alba | Autism |
| Arachidonic acid | Clostridium butyricum | Autism |

질환이 Autism 에 몰린다. 공개 `Disease_Bacteria` 에서 MeSH F03 으로 걸러지는 관계
115건 중 78건이 Autism 이기 때문이다(우울증은 1건). 논문 Table 4 는 Autistic disorder /
Bipolar disorder / Intellectual disability 가 고루 나온다.

---

## 5. 과정에서 드러난 것

세 가지 모두 **논문 규모(음식 135종)에서는 드러나지 않고 14,000종에서만 터지는**
문제다. 각각 환경변수로 되돌릴 수 있고, 근거는 [`README.md`](README.md) 설계 결정에 있다.

### (1) 공식 `final.py` 의 행별 min-max 정규화가 무너진다

음식마다 '그 음식의 최대 성분'이 1.0 이 되므로, 최대 성분이 우연히 E=+1 인 음식이
전부 상위에 온다. 적용 결과 Top 30 이 칵테일류(ethanol 이 최대 성분)로 채워졌다.

→ 열(compound)별 정규화를 기본으로 (`NORM=compound`).
   근거는 논문 Fig.4(c) "we normalize the compounds in the two groups of foods separately".
   공식 경로는 `NORM=row_minmax` 로 실행 가능.

### (2) `p[i] /= sum(S[:,i])` 는 논문 식 (2) 에 없다

공식 `final.py` 가 덧붙인 처리다. adjusted cosine 은 음수를 가지므로 이 열합이 0 근처가
될 수 있다. 성분이 적은 음식의 열합이 **~15** 까지 떨어져(전체 중앙값 3,894) 나눗셈이
점수를 폭발시켰다.

→ 식 (2) 그대로를 기본으로 (`SIM_NORM=none`). 공식 경로는 `SIM_NORM=colsum`.

### (3) ProMENDA 전체를 쓰면 근거가 얕은 compound 가 다수결을 지배한다

논문의 85 compound 는 큐레이션된 목록이라 이 문제가 없었다. ProMENDA 는 1,412 compound
이고, 예컨대 **Ethanol 은 연구 3건(4:1)으로 +1** 을 받아 칵테일을 Top 30 에 몰아넣었다.

→ 근거량 축소 `(pos−neg)/(pos+neg+10)` 를 기본으로 (`E_MODE=shrunk`).
   논문 §4.2.1 그대로는 `E_MODE=binary`, 이항검정 BH q<0.05 만 쓰려면 `E_MODE=sig`
   (FDC compound 73종 중 5종만 남는다).

### (추가) branded_food 는 추천 코호트에서 뺀다

논문 §4.2 의 135개 음식은 전부 분석 측정 기반(Foundation / SR Legacy / FNDDS)이다.
branded_food 는 라벨 신고값이라 대부분의 성분이 결측(0)이고, 성분이 거의 없는
탄산수·단백질파우더가 유사도 단계에서 상위를 차지했다.
KG 자체는 FDC 전체를 담고, 추천 코호트만 제한한다 (`DATA_TYPES=curated`).

---

## 6. 한계

- **식품 온톨로지 미통합** — FoodOn·중국 식품 온톨로지가 없어 음식 분류가 FDC SR 27군에
  머문다. 논문의 128 카테고리 체계와 대응되지 않는다.
- **SNOMED CT 미통합** — 질환 분류는 MeSH tree number 만 쓴다.
- **미생물-정신질환이 얇다** — 공개 `Disease_Bacteria` 에서 MeSH F03 으로 걸러지는 관계는
  115건(질환 6종)뿐이고 우울증은 1건이다. MiKG 원본 경로로 406쌍을 보태도 논문이 말한
  1,234 에 못 미친다.
- **논문 §3.3 의 474만 추론을 재구현하지 않았다** — 전이 추론과 공통 세균 추론만 쓴다.
- **방법 2 의 자동 판정은 수작업 검색과 같지 않다** — 초록을 읽지 않으므로 논문의
  −1(반대 증거)을 만들지 못하고, 공출현만으로 1 을 준다.

---

## 7. 산출물

| 파일 | 내용 |
|---|---|
| `out/ourkg.nt` | RDF N-Triples 3,166,603 |
| `out/kg_stats.csv` | 논문 Table 1 대응 통계 |
| `out/foods.csv` | 음식 14,719 (fdc_id, 카테고리, 측정 compound 수) |
| `out/food_compound_long.csv` | 음식 × compound 중량 768,157 (g/100g) |
| `out/compound_depression.csv` | ProMENDA 극성 E (binary / shrunk / BH q) |
| `out/compound_microbe.csv` | KEGG 재계산 compound-미생물 2,124 |
| `out/microbes.csv` | NCBI 갱신 미생물 127 |
| `out/microbe_disease.csv`, `out/microbe_disease_mikg.csv` | 미생물-질환 |
| `out/recommendation.csv`, `out/recommendation.png` | 추천 순위·시각화 |
| `out/eval_method1.csv`, `out/eval_method2.csv`, `out/eval_sparql.json` | §5.1·§4.1 평가 |

`out/` 과 `cache/` 는 용량 때문에 git 에 올리지 않는다. `python3 ourkg/run_all.py` 로 재생성한다.
