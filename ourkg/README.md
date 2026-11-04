# ourkg — 최신 FDC + ProMENDA 로 다시 만든 Food4healthKG

논문 Fu et al. (2023) *Food4healthKG* 의 **구축 방식과 평가 방식**을 그대로 쓰되,
데이터를 최신 공개본으로 바꿔 우리 KG 를 만든다. 원 논문 **재현**은 레포 루트의
`reconstruct.py` → `run_recommendation.py` 경로이고, 이 디렉토리와 섞지 않는다.
(재현 수치는 `REPRODUCTION.md`, 미해결 문제는 `PROBLEMS.md`)

## 바뀐 것

| 축 | 논문 (2023) | ourkg |
|---|---|---|
| 음식·성분 | FDC 34,250 샘플 (2022 배포본) | FDC 전체 2,101,279 항목 (2026-09 배포본) |
| 우울증-대사물 | MENDA 5,675 관계 | **ProMENDA** (Pu et al. 2024) 22,519 레코드 / 995 연구 |
| compound | KEGG 230 metabolite | KEGG, FDC 영양소에 매핑되는 130종 |
| 미생물 | NCBI taxonomy 322,917 | NCBI efetch 로 학명·rank·계통 **현재 값**으로 갱신 |
| compound-미생물 | KEGG (2022) | KEGG REST 로 **재계산** (compound → EC → KO → organism) |
| 미생물-정신질환 | MiKG 1,234 | MiKG 원본 TTL 의 미생물→신경전달물질→정신질환 경로 406쌍 |
| 질환 분류 | MeSH + SNOMED CT | MeSH SPARQL 로 tree number 조회 (F03 판정). SNOMED 미통합 |
| 식품 온톨로지 | FoodOn + Chinese Food Ontology | **미통합** (아래 한계) |

## 실행

```bash
python3 ourkg/run_all.py          # 01 → 06
python3 ourkg/run_all.py 05 06    # 일부만
```

필요 입력:

| 경로 | 내용 |
|---|---|
| `fdc_raw/food.csv`, `food_nutrient.csv`, `nutrient.csv` | FDC Full Download (CSV) |
| `fdc_raw/survey_fndds_food.csv`, `wweia_food_category.csv` | FDC survey 배포본. FNDDS 음식의 카테고리에 필요하다 — 없으면 FNDDS 545종이 Unclassified 가 된다 ([survey zip](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_csv_2024-10-31.zip)) |
| `41398_2024_2948_MOESM3_ESM.xlsx` | ProMENDA (Pu et al. 2024 supplementary) |
| `foodkg_triply/`, `MiKG-JAIMS/` | 논문 배포본·MiKG — 루트 `README.md` §2 |
KEGG / NCBI / MeSH 는 실행 중 네트워크로 받고 `ourkg/cache/` 에 캐시한다.

## 단계

| | 파일 | 하는 일 | 주요 산출물 |
|---|---|---|---|
| 01 | `01_food.py` | FDC 원본 2,700만 행 스트리밍 → 단위 g 환산 → 논문 §3.2 라벨 병합 → 카테고리 정규화 | `food_compound_long.csv`, `foods.csv` |
| 02 | `02_promenda.py` | ProMENDA → compound별 우울증 극성 E | `compound_depression.csv` |
| 03 | `03_microbe.py` | MeSH tree / NCBI taxonomy / KEGG 로 미생물 축 | `microbes.csv`, `compound_microbe.csv`, `microbe_disease*.csv` |
| 04 | `04_kg.py` | 논문 §3.3 표현 규약대로 RDF 출력 | `ourkg.nt`, `kg_stats.csv` |
| 05 | `05_recommend.py` | 논문 Algorithm 1 (식 1·2) | `recommendation.csv`, `recommendation.png` |
| 06 | `06_eval.py` | §4.1 SPARQL Q1~Q3, §5.1 방법 1·2 | `eval_*.csv/json` |

## 결과

### KG 규모 (논문 Table 1 대응)

| source | relation | entity | triples |
|---|---|---|---|
| FoodData Central | 9 | 783,035 | 3,146,277 |
| MiKG | 6 | 1,060 | 6,802 |
| MeSH | 2 | 245 | 5,400 |
| ProMENDA | 6 | 1,289 | 5,150 |
| KEGG | 3 | 213 | 2,384 |
| NCBI taxonomy | 5 | 210 | 590 |
| **Total** | **20** | **785,393** | **3,166,603** |

논문은 140 relation / 1,637,915 entity / 13,346,991 triple 이다. 차이의 대부분은
온톨로지 축(SNOMED CT 429만, NCBI taxonomy 전체 131만, FoodOn·중국 온톨로지 30만)을
통합하지 않은 데서 온다. 음식-성분 축만 보면 우리 쪽이 더 크다 (314만 vs 233만).

음식 14,719종 (음식당 측정 compound 중앙값 **47**, 논문 heatmap 원본은 33),
compound 130종, 우울증 극성이 확정된 compound 66종 (논문 E 는 85종 중 공개 소스로 69종).

### 추천 (depression, Top/Bottom 30)

비추천 쪽은 논문 §4.2.3·Fig.5 서술과 그대로 맞는다.

| | ourkg Bottom 30 | 논문 §4.2.3 |
|---|---|---|
| | Beef Products 20, Lamb/Veal 5, Sausages and Luncheon Meats 4, Poultry 1 | "sausage products, baked products, and sweets" / 피라미드 상단 "barbecue products, beef products, sausages, and luncheon meats" |

추천 쪽은 부분적으로만 맞는다.

| | ourkg Top 30 | 논문 §4.2.3 |
|---|---|---|
| | Alcoholic Beverages 12, Beverages 6, Fruits and Fruit Juices 4, Sweets 3, Vegetables 2, Finfish and Shellfish 1 | "mainly fish and shellfish products, as well as fruits and vegetables" |

Top 10: Sugar substitute (sucralose) / Honey / Cream of tartar / Lettuce, romaine /
Pears (canned) / Energy drink (sugar free) / Applesauce / Pears (light syrup) /
Energy drink (HFCS) / Butternut squash.

상위를 칵테일·당류가 차지하는 것은 논문의 기전이 큐레이션된 목록에 의존한다는 뜻이다.
당류가 위로 오는 것 자체는 논문 기전 그대로다. 논문 Fig.4(c) 의
추천 음식군도 탄수화물(D-glucose, maltose, sucrose, fructose, starch)이 가장 진하고,
§4.2.3 은 양파의 D-glucose 를 추천 근거로 든다. 음식 모집단이 135종으로 큐레이션되지
않으면 같은 기전이 설탕·주스·에너지드링크를 끌어올린다.

### §5.1 방법 1 — Supplement Table 1 의 20문항

전문가 3인이 없으므로 논문의 정확도 0.95 / 0.90 / 0.95 자체는 재현 대상이 아니다
(`eval/m1.py` 서두와 같은 이유). 우리 KG 가 각 측면을 답할 축을 갖췄는지만 집계한다.

| 측면 | 문항 | 판정 | 근거 |
|---|---|---|---|
| weight calculation | 3 | O | 성분 중량 768,157건 (g/100g) |
| compounds categories | 3 | O | KEGG compound 130 |
| compounds in food and gut | 4 | O | FDC 성분 + KEGG compound-미생물 |
| bacteria taxonomy | 3 | O | NCBI taxonomy 127종, 학명·rank·계통 갱신 |
| food categories | 4 | △ | FDC SR 27군만. FoodOn·중국 온톨로지 미통합 |
| disease classification | 3 | △ | MeSH tree number 만. SNOMED CT 미통합 |

완전 답변 13 / 부분 7 / 불가 0.

### §5.1 방법 2 — 추론 15건 문헌 검증

논문은 수작업 PubMed 검색이었다. 여기서는 E-utilities 로 자동화하되, 판정을
**두 엔티티 + KG 가 댄 근거 물질이 모두 함께 나오는 논문이 있는가**로 둔다.
질환 이름 두 개만 검색하면 anxiety + depression 이 16,578건이라 아무것도 검증하지
못하기 때문이다(그 수치는 `n_hits_pair_only` 로 함께 남긴다).

| | 확인(1) | 미확인(0) | 반대(-1) |
|---|---|---|---|
| ourkg | **4 / 15** | 11 / 15 | 자동 판정하지 않음 |
| 논문 Table 5 | 11 / 15 | 3 / 15 | 1 / 15 |

확인된 4건은 전부 Diet recommendation (Beef·Lamb × depression × palmitic acid).
Complication 추론은 0건이다. MiKG 의 미생물→신경전달물질→정신질환 경로로 만든
합병증 추론은, 공유 미생물까지 포함해 검색하면 뒷받침하는 문헌이 없다. 논문의
Complication 8건이 모두 확인된 것과 대비된다 — 논문이 쓴 MiKG 1,234 관계(비공개)와
우리가 공개본에서 복원한 406쌍이 다른 것으로 보인다.

## 설계 결정 (실행 전에 고정, 결과를 보고 고르지 않았다)

각 항목은 환경변수로 되돌릴 수 있다.

1. **단위 g 환산** (`UNIT_MODE`) — 논문 §3.1 "quantified in weight".
2. **라벨 병합** — 논문 §3.2 "splitting the food labels by commas ... exact matching".
   FDC 항목 1,949,651 → 음식 482,937.
3. **음식당 최소 compound 20** (`MIN_COV=20`) — 성분이 1~2개만 측정된 항목은
   유사도 계산이 성립하지 않는다.
4. **E 의 근거 축소** (`E_MODE=shrunk`, `SHRINK_K=10`) — ProMENDA 는 논문이 쓴
   MENDA 보다 커서 연구 2~3건짜리 compound 도 다수결로 ±1 을 받는다. 예: Ethanol 은
   연구 3건(4:1)으로 +1 이 되어 칵테일류를 Top 30 에 몰아넣었다. `(pos-neg)/(pos+neg+K)`
   로 0 쪽으로 축소한다. `E_MODE=binary` 가 논문 §4.2.1 그대로, `E_MODE=sig` 는
   이항검정 BH q<0.05 인 compound 만 (FDC compound 73종 중 5종만 남는다).
5. **성분(열)별 정규화** (`NORM=compound`) — 공식 `final.py` 의 행별 min-max 는
   음식 135종에서는 되지만 14,000종에서는 무너진다. 음식마다 '그 음식의 최대 성분'이
   1.0 이 되므로 최대 성분이 우연히 E=+1 인 음식이 전부 상위에 온다. 열별 정규화는
   논문 Fig.4(c) "we normalize the compounds in the two groups of foods separately"
   를 근거로 한다. `NORM=row_minmax` 로 공식 경로 실행 가능.
6. **식 (2) 에 정규화 없음** (`SIM_NORM=none`) — 공식 `final.py` 는 `p[i] /= sum(S[:,i])`
   를 덧붙이는데, 식 (2) 에는 없다. adjusted cosine 은 음수를 가지므로 이 열합이
   0 근처가 될 수 있고, 성분이 적은 음식의 열합이 ~15 (중앙값 3,894)까지 떨어져
   점수를 폭발시켰다. `SIM_NORM=colsum` 으로 공식 경로 실행 가능.
7. **추천 코호트를 분석 측정 데이터로 제한** (`DATA_TYPES=curated`) — 논문 §4.2 의
   135개 음식은 전부 Foundation / SR Legacy / FNDDS 다. branded_food 는 라벨 신고값이라
   대부분 성분이 결측이고, 성분이 거의 없는 탄산수·단백질파우더가 상위를 차지한다.
   KG 자체(04)는 FDC 전체를 담는다. `DATA_TYPES=all` 로 포함 가능.

## 한계

- **식품 온톨로지 미통합.** FoodOn·중국 식품 온톨로지가 없어 음식 분류가 FDC
  SR 27군에 머문다. 논문의 128 카테고리 체계와 대응되지 않는다.
- **SNOMED CT 미통합.** 질환 분류는 MeSH tree number 만 쓴다.
- **미생물-정신질환이 얇다.** 공개 Disease_Bacteria 에서 MeSH F03 으로 걸러지는
  관계는 115건(질환 6종)뿐이고 우울증은 1건이다. MiKG 원본 경로로 406쌍을 보태도
  논문이 말한 1,234 에 못 미친다.
- **논문 §3.3 의 474만 추론을 재구현하지 않았다.** 전이 추론과 공통 세균 추론만 쓴다.
- **방법 2 의 자동 판정은 논문의 수작업 검색과 같지 않다.** 초록을 읽지 않으므로
  논문의 -1(반대 증거)을 만들지 못하고, 공출현만으로 1 을 준다.
