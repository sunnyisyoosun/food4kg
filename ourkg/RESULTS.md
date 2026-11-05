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
| triple | 13,346,991 | **3,168,163** |
| entity | 1,637,915 | 785,572 |
| relation | 140 | 30 |
| 음식 | 34,250 샘플 → 135 사용 | 14,719 (추천 코호트 12,574) |
| compound | 85 | 130 |
| 음식당 측정 compound 중앙값 | 33 | **47** |
| 우울증 극성이 확정된 compound | 85 (공개 소스로는 69) | 66 |
| §5.1 방법 2 문헌 검증 | 11 / 15 | **4 / 15** |
| §4.2.3 Top30 추천군 / Bottom30 비추천군 | 서술 | **22 / 27** (교차 위반 2) |
| ModiMedDiet Top30 처방군 / extras (빈도 반영) | — | **22 / 1** |
| 같은 기준에서 ModiMedDiet 로 학습한 E | — | 0.678 — **공개 소스가 이긴다** (§12) |
| `D = X·e` 만 비교하면 (PCA 무관) | — | 공개 0.520 / 역추정 0.803 / 상한 0.816 (§8) |

추천 점수 `D = E × Fᵀ` 에는 미생물이 들어가지 않는다 — 논문 식 (1)(2) 의 정의가
그렇다. gut-brain 경로를 거치는 compound 만 남겨도 순위 상관이 +0.99 다 (§6).

triple 수가 논문의 1/4 인 것은 온톨로지 축(SNOMED CT 429만, NCBI taxonomy 전체 131만,
FoodOn·중국 식품 온톨로지 30만)을 통합하지 않았기 때문이다.
**음식-성분 축만 보면 우리 쪽이 더 크다 (314만 vs 233만).**

`evidence` 행은 논문에 대응이 없다 — E 의 근거를 KG 안에서 추적하려고 우리가
추가한 축이다 (§5 끝).

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
| evidence | 15 | 278 | 1,560 |
| NCBI taxonomy | 5 | 210 | 590 |
| **Total** | **30** | **785,572** | **3,168,163** |

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

`ourkg/out/recommendation.csv` — 12,569 음식 전체 순위.
기본 설정은 `E_MODE=shrunk`, `F_COLUMNS=linked`(논문 §4.2.1), PCA 없음(§13).

### Top 12

| 순위 | 음식 | 카테고리 | 점수 |
|---:|---|---|---:|
| 1 | Vegetable juice, BOLTHOUSE FARMS, DAILY GREENS | Vegetables | 26.88 |
| 2 | Mustard spinach (tendergreen), raw | Vegetables | 26.42 |
| 3 | Mustard greens, boiled, with salt | Vegetables | 24.44 |
| 4 | Mustard greens, boiled, without salt | Vegetables | 24.35 |
| 5 | Beverages, FUZE orange mango, vitamin-fortified | Beverages | 22.41 |
| 6 | Turnip greens, canned, no salt added | Vegetables | 21.07 |
| 7 | Carrot juice, canned | Vegetables | 20.87 |
| 8 | Mustard greens, frozen, cooked | Vegetables | 20.73 |
| 9 | Cress, garden, raw | Vegetables | 20.12 |
| 10 | Balsam-pear (bitter gourd), leafy tips, boiled | Vegetables | 19.97 |
| 11 | McDONALD'S, Bacon Ranch Salad without chicken | Fast Foods | 19.15 |
| 12 | Babyfood, juice, apple-sweet potato | Baby Foods | 19.12 |

### 카테고리 분포 — 논문 §4.2.3 과의 대조

| 카테고리 | Top 30 | Bottom 30 |
|---|---:|---:|
| **Vegetables and Vegetable Products** | **16** | 0 |
| **Fruits and Fruit Juices** | **6** | 0 |
| Baby Foods | 2 | 1 |
| Sweets | 2 | 0 |
| Fast Foods / Beverages / Dairy / AI-AN Foods | 각 1 | 0 |
| **Beef Products** | 0 | **18** |
| **Sausages and Luncheon Meats** | 0 | **6** |
| **Pork Products** | 0 | **3** |
| Poultry Products | 0 | 2 |

| 기준 | 값 |
|---|---|
| §4.2.3 Top30 추천군 (어패류·과일·채소) | **22 / 30** |
| §4.2.3 Bottom30 비추천군 (소시지·베이커리·과자·육류) | **27 / 30** |
| 교차 위반 (비추천군이 Top 에) | **2** |
| ModiMedDiet Top30 처방군 / extras | **22 / 1** |
| ModiMedDiet AUC (참고) | 0.592 |

**논문 §4.2.3 을 양쪽 모두 재현한다.**

> "the recommended foods are mainly fish and shellfish products, **as well as
> fruits and vegetables**. On the other hand, the not recommended foods are
> mainly **sausage products**, baked products, and sweets."

채소 16 + 과일 6 = 22/30 이고, 비추천 쪽은 소고기 18 · 소시지 6 · 돼지 3 이다.
남는 차이는 **어패류가 Top 30 에 없다**는 점이다.

두 평가 기준의 Top-30 측정이 처음으로 같은 방향을 가리킨다 — §4.2.3 추천군 22,
ModiMedDiet 처방군 22 / extras 1.

시각화: `ourkg/out/recommendation.png` (논문 Fig.4(b) 대응 t-SNE)

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

## 5. E 를 여러 근거로 만들기 (`build.py evidence`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

논문은 MENDA 한 소스로 E 를 만들었다(§3.1·§4.2.1). ProMENDA 하나만 쓰면
130 compound 중 66 개만 방향이 정해진다. 네 근거를 각각 부호 있는 점수로 환산해
함께 두고, 결합 방식 세 가지를 비교했다. `ourkg/out/compound_evidence.csv`

### 근거 네 가지

| 소스 | 내용 | 가중 | 방향이 정해지는 compound |
|---|---|---:|---:|
| `promenda` | ProMENDA (Pu et al. 2024) 995 연구 | 1.00 | 66 |
| `menda` | MENDA (Pu et al. 2020) 5,675 관계 — 논문이 실제 쓴 소스 | 0.60 | 40 |
| `rules` | 논문 85 compound 목록에 대해 재현 파이프라인이 정한 극성 (`analyse/knowledge_query_results.csv`). MENDA + 온톨로지·MiKG 규칙이 섞여 휴리스틱 포함 | 0.40 | 57 |
| `afs` | Antidepressant Food Score (LaChance & Ramsey 2018) 12 영양소. **양성만 있고 음성이 없다** | 0.50 | 10 |

가중치는 근거의 규모·최신성·휴리스틱 포함 여부로 실행 전에 정했고 `SOURCE_WEIGHTS`
로 바꿀 수 있다. 소스마다 점수 규모가 달라(`promenda` 는 축소 연속값 중앙값 0.16,
`rules`·`afs` 는 범주형 ±1) 결합 전에 소스별 최대 |score| 로 나눠 눈금을 맞춘다.

### 소스끼리 얼마나 맞는가

| 비교 | 겹치는 compound | 부호 일치 |
|---|---:|---:|
| promenda ↔ menda | 38 | **31 (82%)** |
| menda ↔ rules | 27 | 17 (63%) |
| promenda ↔ rules | 31 | **15 (48%)** |
| promenda ↔ afs | 5 | 3 (60%) |

ProMENDA 와 MENDA 는 같은 큐레이션 계보라 82% 일치한다. 반면 **재현 파이프라인이
논문의 85 compound 에 매긴 극성(`rules`)은 ProMENDA 와 48% — 동전 던지기 수준이다.**

### 결합 방식 세 가지

| | 정의 |
|---|---|
| `weighted` | 눈금 맞춘 점수의 가중 평균. 근거가 엇갈리면 0 에 가까워진다 |
| `priority` | 우선순위(`rules > promenda > menda > afs`) 첫 비영 소스의 부호 |
| `vote` | 모든 소스를 **부호로만** 보는 가중 투표 |

각각 `rules` 를 뺀 판(`_norules`)도 함께 낸다.

### 비교 — 판정 기준은 논문 §4.2.3

추천군 = 어패류·과일·채소, 비추천군 = 소시지·베이커리·과자·소고기·돼지고기·양고기.
`위반` 은 교차 위반(비추천군이 Top 에, 추천군이 Bottom 에 들어간 수)이다.
`ourkg/out/e_mode_comparison.csv`

| E 모드 | 방향 확정 compound | Top30 추천군 | Bottom30 비추천군 | Top30 주류 | Top30 위반 | shrunk 과의 ρ |
|---|---:|---:|---:|---:|---:|---:|
| **`shrunk`** (기본, ProMENDA 단독) | 66 | 7 | **29** | **12** | **4** | — |
| `binary` | 66 | 6 | 25 | 0 | 17 | +0.992 |
| `weighted` | 98 | 12 | 6 | 0 | 16 | **−0.784** |
| `priority` | 98 | 0 | 7 | 0 | 0 | **−0.677** |
| `vote` | 95 | 1 | 2 | 0 | 0 | **−0.500** |
| `weighted_norules` | 73 | 6 | 3 | 0 | 19 | +0.618 |
| `priority_norules` | 73 | 0 | 27 | 0 | 11 | +0.954 |
| **`vote_norules`** | 73 | 2 | **30** | **0** | 10 | +0.958 |

### 읽히는 것 셋

1. **`rules` 를 넣으면 순위가 뒤집힌다.** `rules` 가 들어간 세 모드는 전부 기본
   모드와 음의 상관(ρ −0.50 ~ −0.78)이고 Top30 이 한 개도 겹치지 않는다.
   ProMENDA 와 48% 밖에 맞지 않는 범주형 판정이 ±1 끝에 있어 결합을 끌고 간다.
   논문 §4.2.3 기준으로도 Bottom30 일치가 29 → 2~7 로 무너진다.
   **재현 파이프라인의 E 와 ProMENDA 의 E 는 같은 것을 재는 두 추정이 아니다.**
2. **`rules` 를 빼고 부호 투표를 하면 비추천 쪽이 완벽해진다.** `vote_norules` 는
   Bottom30 이 30/30(소고기 24·소시지 4·돼지고기 2)이고 **칵테일이 사라진다**
   (주류 12 → 0). 방향이 정해진 compound 도 66 → 73 으로 는다.
   부호만 보면 Ethanol 의 얕은 +신호가 다른 compound 들과 같은 크기가 되어
   프로파일을 지배하지 못하기 때문이다.
3. **어느 설정도 깨끗하지 않다.** `vote_norules` 의 Top30 은 시리얼·빵·쌀이고,
   논문 §4.2.3 이 **비추천**으로 든 "baked products" 가 7개 들어간다(위반 10).
   기본 모드는 반대로 Bottom 쪽이 좋지만 Top 에 칵테일 12개가 있다.
   탄수화물이 위로 오는 기전 자체는 논문 Fig.4(c) 그대로다(§3 참조).

### 근거를 KG 안에 싣는다

위의 네 소스와 결합값 여섯 가지는 분석 단계의 CSV 로만 두지 않고 KG 에 넣었다.
`npq:hasPositiveAssociation` / `hasNegativeAssociation` 자체는 ProMENDA 단독 극성
그대로 두고(§4.1 쿼리가 그것을 쓴다), 근거는 **소스마다 노드를 하나 두는 방식**으로
붙였다. 논문이 중량에 쓰는 reification 과 같은 꼴이다
(`npq:hasNutrientWeights` → 노드 → `rdf:value`).

```
<kegg:C00378>  our:hasEvidence  <our:evidence/C00378_promenda> .
               our:combinedE_weighted       "0.1906"^^xsd:double .
               our:combinedE_vote_norules   "1"^^xsd:double .

<our:evidence/C00378_promenda>
    our:fromSource   <our:source/promenda> ;
    our:aboutDisease <mesh:D003865> ;
    rdf:value        "0.295"^^xsd:double ;
    npq:hasPositiveAssociation <mesh:D003865> .

<our:source/promenda>  rdfs:label "ProMENDA (Pu et al. 2024)" ;
                       our:sourceWeight "1"^^xsd:double .
```

실린 양: 근거 노드 173개(ProMENDA 66 / MENDA 40 / rules 57 / AFS 10),
결합값 510개(98·98·95·73·73·73), 소스 노드 4개 — 합쳐 1,560 triple.
compound 98종이 근거를 갖는다.

이제 "어느 소스가 무슨 점수로 이 극성을 주장하는가"를 SPARQL 로 물을 수 있다.

```sparql
select ?cname ?slabel ?w ?v ?rel where {
  ?c rdfs:label ?cname ; our:hasEvidence ?e .
  ?e our:fromSource ?s ; rdf:value ?v ; ?rel mesh:D003865 .
  ?s rdfs:label ?slabel ; our:sourceWeight ?w .
  filter(?rel in (npq:hasPositiveAssociation, npq:hasNegativeAssociation))
}
```

Thiamine (C00378) 을 물으면 네 소스가 그대로 나온다 — ProMENDA +0.295(가중 1.0),
MENDA +0.125(0.6), rules −1.0(0.4), AFS +1.0(0.5). §5 표에서 본 충돌이
KG 안에서 그대로 조회된다.

### 기본값을 바꾸지 않은 이유

위 비교는 §4.2.3 을 **판정에도 쓰고 선택에도 썼다.** 같은 기준으로 고른 설정을
기본값으로 올리면 그 기준에서의 성적이 과대평가된다. 그래서 기본은 `shrunk`
(ProMENDA 단독) 그대로 두고, 다른 설정은 환경변수로 재현할 수 있게만 열어 둔다.

```bash
python3 ourkg/build.py evidence
E_MODE=vote_norules python3 ourkg/analyze.py recommend
python3 ourkg/analyze.py compare          # 위 표를 다시 만든다
```

독립 기준으로 가르려면 §5.1 방법 2(문헌 검증)를 모드별로 돌리는 게 맞지만,
표본이 15건이라 4/15 기준선에서 모드를 가를 만큼의 검정력이 없다.

---

## 6. 경로 비교 — gut-brain 축은 추천에 기여하는가 (`PATH_MODE`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

### 먼저 짚을 것: 추천 점수에는 미생물이 들어가 있지 않았다

논문은 §1·§3.1 에서 gut-brain axis 를 전면에 내세우지만, §4.2 의 추천 알고리즘이
실제로 쓰는 것은 `E`(compound-우울증)와 `F`(음식-compound) 둘뿐이다. 미생물은
`D = E × F^T` 어디에도 들어가지 않는다. 우리 구현도 같다 — 미생물 축은 KG 와
§4.1 쿼리(Q2·Q3)에만 쓰인다.

그래서 "정신건강만으로 추천"은 **이미 기본 동작**이고, 비교 대상이 되는 쪽은
반대로 gut-brain 경로를 거치는 compound 만 남기는 제한이다.

| `PATH_MODE` | 경로 | 쓰는 compound |
|---|---|---|
| `direct` (기본) | Food → Compound → Mental disorder | E 가 있는 전부 |
| `gutbrain` | Food → Compound → **Gut microbiota** → Mental disorder | KEGG compound-미생물 링크가 있고, 그 미생물이 MeSH F03 정신질환과 연관된 것만 |

### 이 경로가 KG 와 일치하는지 (`analyze.py pathcheck`)

`gutbrain` 필터는 속도 때문에 중간 CSV(`compound_microbe.csv` +
`microbe_disease.csv`)로 계산한다. 추천 코드는 SPARQL 을 쓰지 않는다 —
`ourkg.nt` 에 쿼리를 던지는 것은 §4.1 평가(`evaluate` PART A)뿐이다.

그래서 같은 집합을 KG 에서도 뽑아 대조했다. 논문 §4.1.1 Query 3 과 같은 패턴이다.

```sparql
select distinct ?c where {
  ?m mpq:hasMetabolites ?c ; mpq:hasAssociation ?d .
  ?d rdfs:subClassOf ent:MentalDisorder .
}
```

| 출처 | compound |
|---|---:|
| CSV (`compound_microbe` + `microbe_disease.is_mental`) | 52 |
| KG (`ourkg.nt` SPARQL) | 52 |
| 일치 / CSV 에만 / KG 에만 | **52 / 0 / 0** |

두 경로가 같은 집합을 낸다 — `build.py kg` 가 쓴 triple 과 중간 CSV 가 일관된다.
이 52종 중 E 의 방향까지 정해진 것이 아래 표의 35종(`shrunk` 기준)이다.
`PATH_SOURCE=kg` 로 추천에서도 KG 쪽 집합을 쓸 수 있다(적재 60초).

### 결과 (8 모드 × 2 경로)

`ourkg/out/e_mode_comparison.csv`

| E 모드 | 경로 | 방향 확정 compound | Top30 추천군 | Bottom30 비추천군 | Top30 주류 | Top30 위반 |
|---|---|---:|---:|---:|---:|---:|
| `shrunk` (기본) | direct | 66 | 7 | 29 | 12 | 4 |
| `shrunk` | gutbrain | 35 | 7 | 29 | 8 | 7 |
| `binary` | direct | 66 | 6 | 25 | 0 | 17 |
| `binary` | gutbrain | 35 | 6 | 26 | 0 | 14 |
| `weighted` | direct | 98 | 12 | 6 | 0 | 16 |
| `weighted` | gutbrain | 45 | 0 | **30** | 0 | 5 |
| `priority` | direct | 98 | 0 | 7 | 0 | 0 |
| `priority` | gutbrain | 45 | 0 | **30** | 0 | 4 |
| `vote` | direct | 95 | 1 | 2 | 0 | 0 |
| `vote` | gutbrain | 44 | 1 | **28** | 0 | 6 |
| `weighted_norules` | direct | 73 | 6 | 3 | 0 | 19 |
| `weighted_norules` | gutbrain | 37 | **14** | **30** | 0 | 8 |
| `priority_norules` | direct | 73 | 0 | 27 | 0 | 11 |
| `priority_norules` | gutbrain | 37 | 3 | 28 | 0 | 10 |
| `vote_norules` | direct | 73 | 2 | **30** | 0 | 10 |
| `vote_norules` | gutbrain | 37 | 8 | **30** | 0 | 10 |

같은 모드의 direct ↔ gutbrain 순위 상관:

| E 모드 | Spearman ρ | Top30 겹침 |
|---|---:|---:|
| `shrunk` | **+0.991** | 24/30 |
| `binary` | **+0.998** | 24/30 |
| `priority_norules` | **+0.995** | 21/30 |
| `vote_norules` | **+0.996** | 16/30 |
| `weighted_norules` | +0.922 | 10/30 |
| `weighted` | **−0.512** | 0/30 |
| `priority` | **−0.529** | 0/30 |
| `vote` | **−0.454** | 0/30 |

### 읽히는 것 둘

**1. ProMENDA 계열 E 에서는 경로 제한이 순위를 바꾸지 않는다.**
`shrunk` 는 compound 를 66 → 35 (47% 삭제)로 줄여도 ρ +0.991, Top30 24/30 이
그대로다. `binary` 는 ρ +0.998. §4.2.3 점수도 Bottom30 29→29, 25→26 으로 거의
변화가 없다.

즉 **gut-brain 축을 통과하는 compound 만 남겨도 추천 결과가 바뀌지 않는다.**
미생물 경로를 거치는 compound 가 그렇지 않은 것들의 대표 표본이거나(둘 다 FDC
주요 영양소라 성분 프로파일이 비슷하다), 순위를 만드는 것이 경로가 아니라 `F` 의
성분량 분포와 `E` 의 부호이기 때문이다. REPRODUCTION §16 의 V3(similarity 단계를
빼도 ρ +0.761 유지)와 같은 방향의 관찰이다.

**이것은 우리 구현의 한계가 아니라 Algorithm 1 의 정의 때문이다.** 논문 §4.2.2 의
식 (1)(2) 어디에도 미생물이 없다. 논문이 §1·§3.1 에서 내세우는 gut-brain axis 는
KG 의 서사와 §4.1 쿼리(Q2·Q3)에는 쓰이지만 추천 점수를 움직이지 않는다.

**2. 경로 제한이 `rules` 가 일으킨 역전을 되돌린다.**
`rules` 가 섞인 세 모드(`weighted`·`priority`·`vote`)는 direct ↔ gutbrain 상관이
ρ −0.45 ~ −0.53 으로 뒤집히고, §4.2.3 Bottom30 이 **6 → 30 / 7 → 30 / 2 → 28** 로
회복된다. 순위를 뒤집던 compound 들이 미생물 경로가 없는 쪽에 몰려 있다는 뜻이다.
§5 에서 본 "`rules` 가 ProMENDA 와 48% 밖에 맞지 않는다"는 관찰과 이어진다 —
경로 제한이 그 불일치를 걸러 내는 필터로 작동한다.

가장 좋은 §4.2.3 점수는 `weighted_norules` + `gutbrain` 이다
(Top30 추천군 14, Bottom30 비추천군 30, 주류 0, 위반 8). 다만 §5 끝에 적은 이유로
이것을 기본값으로 올리지는 않는다 — 같은 기준을 판정과 선택에 함께 썼다.

```bash
PATH_MODE=gutbrain python3 ourkg/analyze.py recommend
PATHS=direct,gutbrain python3 ourkg/analyze.py compare    # 위 16행 표
```

---

## 7. 외부 정답셋 — SMILES trial 의 ModiMedDiet (`analyze.py external`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

### 왜 필요했나

§5·§6 의 모든 판정이 논문 §4.2.3 서술 하나에 기대고 있었다. 그것은 논문이 자기
알고리즘의 **출력을 서술한 문장**이라, 같은 기준으로 설정을 고르면 성적이
과대평가된다. 그래서 기본값을 바꾸지 못하고 있었다.

**ModiMedDiet** (Jacka et al. 2017, *BMC Medicine* 15:23) 은 중등도~중증 우울증
환자 67명 대상 12주 RCT(SMILES)에서 **실제로 처방된** 식단이고, 1차 결과(MADRS)가
유의하게 개선됐다. 알고리즘의 출력이 아니라 임상 개입이므로 **출처가 독립이다.**

내용까지 독립인 것은 아니다 — 지중해식이라 "채소·생선 좋고 가공육·과자 나쁨"이라는
방향은 §4.2.3 과 겹친다. 겹치지 않는 지점이 중요한데, 그중 하나가 **붉은 고기**다.
§4.2.3 은 소고기·소시지를 비추천으로 두지만 ModiMedDiet 은 **lean red meat 를 주
3-4회 처방**한다.

### 처방 내용과 라벨 규칙

| 처방군 (+1) | 양 |
|---|---|
| whole grains | 5–8 / day |
| vegetables | 6 / day |
| fruit | 3 / day |
| low-fat, unsweetened dairy | 2–3 / day |
| raw, unsalted nuts | 1 / day |
| olive oil | 3 tbsp / day |
| legumes | 3–4 / week |
| fish | ≥ 2 / week |
| lean red meat | 3–4 / week |
| chicken | 2–3 / week |
| eggs | ≤ 6 / week |

**extras (−1)** — sweets, refined cereals, fried food, fast food, processed meats,
sugary drinks, 그리고 spirits/beer. 합쳐 **≤ 3 / week**.

처방이 조건부인 것들(`low-fat`·`unsweetened`·`raw`·`unsalted`·`lean`·`whole`·`olive`)은
카테고리만으로 가를 수 없어 이름 규칙을 뒀다. 규칙은 전부 위 처방 문구에서 그대로
가져왔고, 어느 쪽에도 걸리지 않는 음식은 **집계에서 뺀다**. 성인 RCT 이므로 이유식도
뺀다. 라벨 전수는 `ourkg/out/modimed_labels.csv` 에 규칙 출처와 함께 있다.

추천 코호트 12,574 중 **처방군 5,360 / extras 3,328 / 해당 없음 3,886**.

`separable lean only`(지방 제거 부위)만 lean red meat 로 보고 `separable lean and
fat` 은 해당 없음으로 둔 것이 중요하다 — 소고기 1,104종 중 459종만 처방군이다.

### 채점

**AUC** = 처방군 음식이 extras 음식보다 위에 올 확률(Mann–Whitney U / n₁n₂).
0.5 가 무작위다.

| E 모드 | 경로 | **ModiMedDiet AUC** | Top30 처방군 | Top30 extras | §4.2.3 Bottom30 |
|---|---|---:|---:|---:|---:|
| `vote` | direct | **0.665** | **24** | 4 | 2 |
| `priority` | direct | **0.610** | 18 | 10 | 7 |
| `weighted` | direct | **0.595** | 18 | 5 | 6 |
| `weighted_norules` | direct | 0.495 | 20 | 7 | 3 |
| **`shrunk` (기본)** | direct | **0.491** | 6 | 13 | **29** |
| `weighted_norules` | gutbrain | 0.486 | 27 | 2 | **30** |
| `vote_norules` | gutbrain | 0.485 | 14 | 10 | **30** |
| `vote_norules` | direct | 0.484 | 11 | 14 | **30** |
| `shrunk` | gutbrain | 0.482 | 6 | 14 | 29 |
| `binary` | direct | 0.481 | 5 | 18 | 25 |
| `priority_norules` | direct/gutbrain | 0.477 | 9 | 10~12 | 27~28 |
| `vote` | gutbrain | 0.465 | 15 | 7 | 28 |
| `priority` | gutbrain | 0.422 | 12 | 10 | **30** |
| `weighted` | gutbrain | 0.412 | 15 | 7 | **30** |

> **★ §11 D 에서 수정됨.** 아래 표와 해석은 처방 12군을 **동등가중**으로 둔
> 라벨 기준이다. ModiMedDiet 은 빈도 처방이고(채소 6회/일 vs 붉은 고기 주 3–4회),
> 빈도를 반영하면 기본 설정의 AUC 는 0.491 → **0.633** 이고 두 기준의 간극은
> 0.209 → 0.039 로 거의 사라진다. "기본 설정은 우연 수준" 과 "두 기준이 반대를
> 가리킨다"는 **동등가중 라벨에서만 성립한다.**

### 읽히는 것 — 두 기준이 반대를 가리킨다 (동등가중 라벨 기준)

**1. 기본 설정은 외부 기준에서 우연 수준이다.** `shrunk` 의 AUC 0.491 은 동전
던지기와 구별되지 않는다. §4.2.3 Bottom30 29/30 으로 가장 좋아 보이던 설정이,
임상에서 처방된 식단을 그 식단이 제한한 음식과 **전혀 가르지 못한다.**

**2. 두 기준의 순위가 거의 뒤집힌다.** AUC 상위 셋(`vote`·`priority`·`weighted`,
전부 direct)은 §4.2.3 Bottom30 이 2·7·6 으로 최하위권이다. 반대로 §4.2.3 Bottom30
30/30 을 받은 설정들은 AUC 0.41~0.49 다.

**3. 갈라지는 지점은 붉은 고기다.** §4.2.3 을 잘 맞추는 설정은 **모든 육류를
바닥으로** 보낸다. ModiMedDiet 은 지방을 제거한 붉은 고기를 주 3-4회 처방하므로,
그 설정들은 처방군의 상당수를 extras 와 같이 바닥에 두게 된다. §4.2.3 점수가
좋을수록 AUC 가 나빠지는 구조다.

**4. 그래도 AUC 0.665 는 높지 않다.** 가장 좋은 설정도 처방 식단을 2/3 정도만
가른다. 라벨 규칙의 잡음도 있고(이름 문자열 기반), 무엇보다 **알고리즘이 보는
것은 성분 85~130종의 중량뿐**이라 조리법·가공도·식품군을 모른다.

### 그래서 기본값은

`shrunk` 다. **§11 D 이후로는 적극적인 이유가 생겼다** — 빈도를 반영한 외부
기준에서 공개 소스 설정 중 가장 높다(0.633). 동등가중 라벨에서만 우연 수준으로
보였던 것이다.

```bash
python3 ourkg/analyze.py external                       # 정답셋 자체를 검수
PATHS=direct,gutbrain python3 ourkg/analyze.py compare  # 두 기준으로 16조합 채점
```

### 한계

- ModiMedDiet 은 **식품군·분량** 처방이고 우리 알고리즘은 **성분 중량**만 본다.
  같은 축에서 비교하는 것이 아니다.
- 라벨은 FDC 이름 문자열 규칙이라 잡음이 있다. `modimed_labels.csv` 를 열어
  규칙별로 검수할 수 있게 해 뒀다.
- SMILES 는 참가자 67명, 1개 시험이다. 메타분석 수준의 근거가 아니다.
- 내용이 §4.2.3 과 부분적으로 겹친다. 독립인 것은 근거의 출처이지 내용이 아니다.

---

## 8. E 의 부호를 역추정한다 (`analyze.py invert`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

### 먼저 상한을 쟀다

§7 에서 두 기준이 반대를 가리켰다. 그러면 "어느 E 가 맞나" 이전에
**성분 중량만으로 ModiMedDiet 을 가를 수 있기는 한가**를 물어야 한다.

ModiMedDiet 라벨 8,688개(처방군 5,360 / extras 3,328)에 성분 중량 130종으로
로지스틱 회귀를 학습하고 5-fold CV 로 쟀다.

| | AUC |
|---|---:|
| 성분 중량 130종, 지도학습 — **상한** | **0.816** |
| ProMENDA E 가 있는 66종만, 지도학습 | 0.782 |
| 근거가 하나라도 있는 98종만, 지도학습 | 0.813 |
| ProMENDA `e_shrunk` 로 `D = X·e` | **0.520** |

**커버리지는 병목이 아니다.** 66종만 써도 0.782 이고, 빠진 32종을 다 메워도
+0.034 다. 잃는 곳은 전부 **부호**다.

### 역추정 — 라벨 절반으로 E 를 배운다

누수 방지를 실행 전에 고정했다.

- 음식 단위 50/50 층화 분할(seed 0). E 는 train 음식만 보고 학습한다.
- 보고하는 AUC 는 **test 음식만**으로 잰다.
- 논문 §4.2.3 기준은 학습에 전혀 쓰지 않으므로 독립 체크로 남는다.
- 유사도 `S` 는 라벨을 쓰지 않는 비지도 단계라 전체 음식으로 계산한다.

| E | held-out AUC (`D = X·e`) |
|---|---:|
| ProMENDA `e_shrunk` | 0.520 |
| **역추정** | **0.803** |
| (상한) | 0.816 |

**역추정 E 는 상한에 거의 닿는다 (0.803 / 0.816).** 가설이 확인됐다 —
성분 중량은 신호를 갖고 있었고, 공개 소스 E 의 **부호**가 그것을 버리고 있었다.

### 어디서 갈리는가 — biomarker 방향 ≠ 식이 방향

둘 다 비영인 66종 중 **부호 일치 32 (48%)**. 동전 던지기다.
`ourkg/out/invert_comparison.csv` 에 전수가 있다.

| kegg | name | 역추정 | ProMENDA | MENDA | rules | AFS |
|---|---|---:|---:|---:|---:|---:|
| C00469 | Ethanol | **−0.512** | +0.200 | +0.125 | | |
| C07480 | Theobromine | **−0.490** | +0.091 | | | |
| C16525 | Eicosadienoic acid | **−0.481** | +0.333 | | | |
| C00253 | Nicotinic acid | **−0.460** | +0.050 | +0.217 | +1 | |
| C00378 | Thiamine | **−0.415** | +0.238 | +0.125 | −1 | +1 |
| C00047 | L-Lysine | **+0.412** | −0.240 | −0.183 | | |
| C02477 | Alpha-Tocopherol | +0.380 | −0.100 | | +1 | |
| C00255 | Riboflavin | −0.316 | +0.059 | +0.125 | −1 | |
| C00089 | Sucrose | −0.292 | +0.259 | +0.243 | +1 | |

**Ethanol 이 가장 분명한 사례다.** ProMENDA 는 +0.200 — 우울증 환자에서 에탄올
대사물이 낮게 관측된다는 뜻이다. 역추정은 −0.512 — 식단 기준으로는 제한 대상이다
(ModiMedDiet 은 spirits/beer 를 extras 로 둔다). 둘 다 맞을 수 있다. **재는 것이
다르기 때문이다.**

- ProMENDA·MENDA 는 **case-control 메타볼로믹스**다. "우울증 환자에서 이 대사물
  농도가 높/낮다"를 잰다. 원인인지 결과인지, 먹어서 생긴 것인지 병이 만든 것인지
  구별하지 않는다.
- 논문 §4.2.1 의 `E` 는 "compound 가 질병을 완화/악화시킨다"로 정의된다.

**논문은 이 둘을 동일시한다.** 48% 라는 숫자가 그 가정이 성립하지 않는다는 측정값이다.
이것이 §7 에서 본 "두 기준이 반대를 가리킨다"의 기전이기도 하다.

ProMENDA 가 0 인데 역추정 |e| > 0.3 인 compound 도 10종 있다 — Lutein+zeaxanthin
(+0.703), Vitamin K (+0.534), β-carotene (+0.523), Magnesium (+0.433) 등.
전부 식물성 미량영양소이고, 대사체 연구에서 측정되지 않아 E 에 빠져 있었다.

### 전체 파이프라인에 넣으면 — 유사도 단계가 신호를 깎는다

| | held-out AUC |
|---|---:|
| `D = X·e` (역추정 E) | **0.803** |
| 논문 Algorithm 1 전체 (`P = D × S`) | **0.698** |

**유사도 단계 `S` 가 0.803 을 0.698 로 떨어뜨린다.** REPRODUCTION §16 의
V3(“similarity 단계를 빼도 순위가 거의 같다”)와 같은 방향인데, 여기서는 더 세다 —
기여가 작은 정도가 아니라 **빼는 편이 낫다**.

그래도 0.698 은 지금까지의 어떤 설정보다 높다 (최고 `vote` direct 0.665,
기본 `shrunk` 0.491).

### 독립 체크 — §4.2.3 은 어떻게 나오나

학습에 쓰지 않은 기준이다.

| | Top30 추천군 | Bottom30 비추천군 |
|---|---:|---:|
| `learned` | 5 | 14 |
| `shrunk` (기본) | 7 | 29 |
| `vote` direct | 1 | 2 |

§4.2.3 기준으로는 기본 설정보다 나쁘고 `vote` 보다는 낫다. 다만 **Top30 첫 음식이
`Fish, haddock, raw`** 다 — 논문 §4.2.3 이 추천군 1순위로 든
"fish and shellfish products" 가 처음으로 맨 위에 왔다.

### 쓰는 법과 경고

```bash
python3 ourkg/analyze.py invert                  # 역추정 + 대조표
E_MODE=learned python3 ourkg/analyze.py recommend
```

**이 E 는 ModiMedDiet 라벨로 학습한 것이다.** ModiMedDiet 기준으로 성능을 말할
때는 반드시 held-out 음식만 써야 하고, 기본값으로 쓰지 않는다. 공개 소스만으로
만든 E 와는 성격이 다른 산출물이다.

---

## 9. ProMENDA 를 연구 설계별로 나눠 봤다 — 가설 반증 (`analyze.py stype`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

### 가설

§8 에서 공개 소스 E 의 부호가 ModiMedDiet 과 48% 밖에 맞지 않았고, 그 이유를
"case-control 메타볼로믹스(농도)와 식이 효과(먹으면 좋/나쁨)는 다른 것을 잰다"로
봤다. 그렇다면 **ProMENDA 안에서도 개입 효과를 재는 설계는 식이 방향에 더
가까워야 한다.** 이것을 직접 검정했다.

ProMENDA 의 `M_Study_type_Metabolite_level` (M_Groups 로 역추론, `map_promenda.py`)

| Type | 행 | 설계 | 읽기 |
|---|---:|---|---|
| Type1 | 14,370 | depression vs control, CUMS vs control | 환자에서 올라간 것. 원인인지 결과인지 모른다 |
| **Type2** | **6,169** | **CUMS + fluoxetine vs CUMS, post-ketamine vs baseline** | **치료로 올라간 것 — 개입 효과다** |
| Type3 | 1,717 | rTMS vs control (대상이 건강인) | 우울증 방향과 대응하지 않는다. 제외 |
| Type4 | 239 | responder vs non-responder | 반응자에서 올라간 것. 개입 효과 쪽 |
| Type5 | 24 | — | 표본이 작아 제외 |

### 결과 — 어떤 설계로 나눠도 우연 수준이다

학습이 없으므로 ModiMedDiet 라벨 전체(8,688)로 쟀다. `D = X·e` 의 AUC 다.

| 변형 | compound | **ModiMedDiet AUC** | 역추정 E 와 부호 일치 |
|---|---:|---:|---:|
| `paper` (현재 기본값) | 66 | 0.520 | 32/63 (51%) |
| `t1_paper` — Type1 만, up=+1 | 64 | 0.519 | 32/60 (53%) |
| `t1_harm` — Type1 만, up=−1 | 64 | 0.481 | 28/60 (47%) |
| **`t2` — Type2 만 (개입 효과)** | 53 | **0.504** | 26/52 (50%) |
| `t4` — Type4 만 | 16 | 0.308 | 8/16 (50%) |
| `t24` — Type2+4 | 53 | 0.471 | 27/52 (52%) |
| `semantic` — Type1 해롭다 + Type2/4 이롭다 | 65 | 0.487 | 29/61 (48%) |
| *(참고) 역추정 E, held-out* | 122 | *0.803* | — |
| *(참고) 성분 중량 상한* | 130 | *0.816* | — |

**가설이 반증됐다.** 개입 효과만 모은 `t2` 는 AUC 0.504 — 정확히 무작위다.
일곱 변형 전부 0.47~0.52 구간에 있고, 역추정 E 와의 부호 일치도 47~53% 로
전부 동전 던지기다. `t4` 의 0.308 은 compound 16종뿐이라 잡음으로 본다.

ModiMedDiet 기준 최고는 `paper` (0.520) — **현재 기본값이다. 바꿀 것이 없다.**

### 이게 말하는 것

문제는 **ProMENDA 를 어떻게 자르느냐가 아니다.** 어떤 설계로 잘라도 식이 효과
방향이 나오지 않는다. §8 의 결론이 오히려 강해진다 —

> 혈액·뇌의 **대사물 농도** 변화는, 그 대사물을 **음식으로 먹었을 때의 이해득실**을
> 담고 있지 않다.

치료로 어떤 대사물이 올라갔다는 것조차 그 대사물을 먹으라는 뜻이 아니다.
약물이 대사 경로를 바꾼 결과일 뿐이고, 경구 섭취로 같은 변화가 일어난다는 보장이
없다. 논문 §4.2.1 이 MENDA 의 up/down 을 그대로 `E` 로 쓴 것은 **규약을 잘못 고른
것이 아니라 소스의 종류가 맞지 않는 것**이다.

바꿔 말하면, 이 방향의 개선은 여기서 막힌다. `E` 를 식이 효과로 만들려면
**섭취-결과를 재는 소스**(RCT, 코호트 식이조사, 영양역학)가 필요하고, 그것이
§8 의 역추정이 한 일이다.

```bash
python3 ourkg/analyze.py stype                        # 위 표
E_MODE=stype:t2 python3 ourkg/analyze.py recommend    # 변형 하나로 추천
```

---

## 10. F 에 구조·가공 축을 더한다 (`build.py form`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

### 왜

§7 에서 ModiMedDiet 이 가르는 것은 상당 부분 성분이 아니라 **형태**였다
(`separable lean only` vs `lean and fat`, `whole` vs `refined`, `raw` vs `fried`).
지금 `F` 는 KEGG 에 매핑되는 영양소 130종만 담아 이걸 모른다. §8 에서 잰 상한
0.816 은 그 제약 아래의 상한이다. **상한 자체를 올리는 길이다.**

### 누수를 어떻게 막았나

ModiMedDiet 라벨은 **음식 이름 문자열** 규칙으로 만들었다(§7). 그러므로 형태 축을
이름에서 뽑으면 라벨을 특징으로 쓰는 셈이 되어 평가가 무의미해진다.
**FDC 가 측정한 영양소 값만 쓴다. 이름도 카테고리도 보지 않는다.**

더한 축 19개 — 전부 FDC 측정 영양소인데 KEGG 매핑이 없어 `F` 에서 빠져 있던 것들.

| | |
|---|---|
| 절대량 (13) | Energy, Protein, Fat, Carbohydrate, Water, Fiber, Added sugar, Total sugar, SFA, MUFA, PUFA, TFA, Ash |
| 비율 (6) | `added_sugar_share`(첨가당/탄수화물), `sugar_share`, `sat_share`(포화/지방), `unsat_ratio`((MUFA+PUFA)/SFA), `carb_share`·`fat_energy_share`(중량/열량) |

비율이 가공·형태의 대리 변수다 — 정제 곡물은 섬유가 적고 첨가당 비중이 높으며,
튀긴 것은 지방 비중과 에너지 밀도가 높다.

> 처음 판에서는 `energy_density = energy_kcal/100` 같은 열을 '비율'로 넣었는데,
> 절대량이 이미 100 g 당 값이라 같은 열의 복사본(완전 공선)이었다. 5개를 뺐다.

### 결과 — 구조 축 19개가 KEGG compound 130종보다 낫다

ModiMedDiet 라벨 8,688개, 음식 단위 50/50 분할(seed 0), 학습은 train 만.

| 특징 집합 | 특징 수 | 상한 (5-fold CV) | 역추정 held-out (`D = X·e`) |
|---|---:|---:|---:|
| `compound` — 논문 `F` 그대로 | 130 | 0.816 | 0.803 |
| **`form` — 구조·가공 축만** | **19** | **0.819** | **0.809** |
| **`both`** | 149 | **0.847** | **0.835** |
| *(참고) ProMENDA `e_shrunk`* | 130 | — | *0.520* |

**구조 축 19개만으로 KEGG compound 130종과 같거나 낫다** (0.819 vs 0.816).
그리고 둘은 **상호 보완적이다** — 합치면 0.847 로 둘 중 어느 쪽보다 높다.

### 무엇이 가르는가

`form` 만 썼을 때의 상위 가중치 (`learned_form.csv`)

| 축 | 가중치 |
|---|---:|
| fiber | **+1.000** |
| PUFA | +0.545 |
| water | +0.442 |
| protein | +0.437 |
| SFA | **−0.339** |
| carbohydrate | −0.253 |
| unsat_ratio | +0.241 |
| energy | −0.231 |
| total sugar | −0.205 |

섬유 많고 불포화지방·수분·단백질 많고, 포화지방·당·열량 적은 쪽 — 익숙한
건강식 서명이다. 중요한 것은 **이것을 가정한 적이 없다는 점이다.** ModiMedDiet
라벨에서 배운 결과다.

`both` 에서는 두 축이 섞여 나온다 (`learned_both.csv`)

| 축 | 가중치 |
|---|---:|
| fiber | +1.000 |
| **Magnesium (C00305)** | +0.813 |
| water | +0.596 |
| **Lutein + zeaxanthin (C06098)** | +0.504 |
| PUFA | +0.484 |
| **Ethanol (C00469)** | **−0.464** |
| **β-carotene (C02094)** | +0.374 |
| **Vitamin K (C02059)** | +0.369 |
| total sugar | −0.322 |

§8 에서 "ProMENDA 가 0 인데 역추정 |e| 가 큰 것"으로 지목했던 식물성 미량영양소
(마그네슘·루테인·β-카로틴·비타민 K)가 그대로 상위에 있다. 구조 축을 더해도
그 compound 들은 밀려나지 않는다 — 서로 다른 것을 재고 있다는 뜻이다.

### 전체 파이프라인에 넣으면 — 또 S 가 깎는다

| 특징 | `D = X·e` | Algorithm 1 전체 `P = D × S` |
|---|---:|---:|
| `compound` | 0.803 | 0.698 |
| `both` | **0.835** | 0.616 |

특징이 늘수록 유사도 단계가 더 많이 깎는다(§8 의 관찰이 더 강해진다).
`S` 는 성분 프로파일의 코사인 유사도라, 축이 늘면 "비슷한 음식"의 정의가
흐려지고 점수가 이웃으로 번진다.

### 한계

- 더한 축은 `F` 이지 KG 의 엔티티가 아니다. **KG 의 compound 축은 KEGG 그대로** 둔다.
  논문 §3.1 은 "nutrients ... quantified in weight" 라고만 하고 KEGG 매핑을
  요구하지 않으므로 `F` 확장은 논문 범위 안이지만, `E` 는 compound 축에만
  정의되므로 `form`/`both` 는 **논문 Algorithm 1 의 E 가 아니다.**
  `E_MODE=learned` 는 `compound` 축일 때만 쓸 수 있게 막아 뒀다.
- NOVA 같은 공인 가공도 분류를 쓰지 않았다. 측정값 대리 변수다.
- 여전히 ModiMedDiet 라벨로 학습한 결과다. 공개 소스만으로 이 축의 부호를
  정하는 길은 아직 없다.

```bash
python3 ourkg/build.py form                               # 구조 축 생성
FEATURES=form python3 ourkg/analyze.py invert             # 구조 축만
FEATURES=both python3 ourkg/analyze.py invert             # 합쳐서
```

---

## 11. 두 기준이 어디서 갈리는가 (`analyze.py disagree`)

> **이 절의 수치는 PCA 를 끈 경로에서 잰 것이다**(당시 기본값).
> 논문 §4.2.1 의 PCA 를 켜면 결론 일부가 바뀐다 — §12.

§7 에서 "§4.2.3 을 잘 맞추는 설정일수록 ModiMedDiet AUC 가 나쁘다"를 보고 그 이유를
"붉은 고기 때문"이라고 적었다. 서술이었지 측정이 아니었다. 여기서 쟀고,
**재는 과정에서 §7 의 결론이 정답셋의 결함 때문이었음이 드러났다.**

### A — 충돌하는 음식군은 정확히 둘이다

| 음식군 | n | 논문 §4.2.3 | ModiMedDiet 처방 | extras | 미분류 |
|---|---:|---|---:|---:|---:|
| **Beef Products** | 1,128 | 비추천군 | **459** | 24 | 645 |
| **Lamb, Veal, and Game** | 496 | 비추천군 | **149** | 19 | 328 |

다른 25개 음식군에서는 두 기준이 충돌하지 않는다. 충돌은 붉은 고기 하나의 축이다.
(FDC 의 `separable lean only` 항목이 ModiMedDiet 의 lean red meat 처방에 해당한다.)

### B — 음식군을 빼고 다시 재면

양수 = 그 군을 빼면 AUC 가 오른다 = 그 군이 점수를 깎고 있었다.

| 음식군 | n | ΔAUC (`shrunk`) | ΔAUC (`learned`) |
|---|---:|---:|---:|
| **Beef Products** | 1,128 | **+0.0309** | −0.0139 |
| Vegetables | 1,255 | −0.0253 | −0.0138 |
| Fruits and Fruit Juices | 562 | −0.0251 | +0.0012 |
| Sausages and Luncheon Meats | 388 | −0.0162 | −0.0014 |
| Poultry Products | 738 | +0.0125 | +0.0119 |

`shrunk` 에서 소고기를 빼면 AUC 가 가장 크게 오른다. 채소·과일을 빼면 내려간다 —
그쪽은 `shrunk` 가 이미 맞히고 있다.

### C — 설정을 바꾸면 무엇이 움직이나 (순위 백분위, 100 = 최상위)

| 음식군 | n | `shrunk` | `learned` | 이동 |
|---|---:|---:|---:|---:|
| **Lamb, Veal, and Game** | 496 | 16.9 | 81.1 | **+64.2** |
| **Beef Products** | 1,128 | 18.7 | 76.8 | **+58.1** |
| **Pork Products** | 406 | 21.3 | 71.6 | **+50.3** |
| Alcoholic Beverages | 83 | 98.4 | 56.0 | −42.4 |
| Fats and Oils | 252 | 68.3 | 30.4 | −37.9 |
| Beverages | 431 | 83.2 | 49.0 | −34.2 |

**붉은 고기 세 군이 바닥(17~21 백분위)에서 상위(72~81 백분위)로 통째로 올라간다.**
§7 의 서술이 측정으로 확인됐다 — 두 기준의 불일치는 이 한 축이다.

### D — ★ 그런데 정답셋이 처방 강도를 잃고 있었다

ModiMedDiet 은 **빈도** 처방이다. 채소 **6회/일**(주 42회)과 lean red meat
**주 3–4회**는 강도가 열 배 넘게 다른데, §7 의 라벨은 둘 다 똑같이 `+1` 로 뒀다.
충돌이 전부 붉은 고기에서 나온다면, **저빈도 처방군을 양성에서 빼도 결론이
유지되는지** 봐야 한다.

매일 처방되는 군만 양성으로 두고(채소·과일·통곡물·유제품·견과·올리브유,
2,754종) extras 3,326종과 가른 결과:

| 설정 | 양성 = 처방 12군 전부 (§7) | 양성 = 고빈도 처방군만 |
|---|---:|---:|
| `shrunk` (기본) | 0.491 | **0.633** |
| `learned` (역추정) | 0.700 | 0.672 |
| 차이 | **0.209** | **0.039** |

**§7 의 "기본 설정은 외부 기준에서 우연 수준"은 정답셋의 결함이 만든 것이었다.**
처방 빈도를 반영하면 기본 설정은 0.633 이고, 두 기준의 간극은 0.209 → 0.039 로
거의 사라진다.

공개 소스 설정 전체를 다시 채점해도 순서가 바뀐다.

| E 모드 | 양성 = 전부 (§7) | 양성 = 고빈도만 |
|---|---:|---:|
| **`shrunk` (기본)** | 0.491 | **0.633** ← 최고 |
| `vote` | 0.665 | 0.625 |
| `binary` | 0.481 | 0.622 |
| `vote_norules` | 0.484 | 0.618 |
| `weighted_norules` | 0.495 | 0.603 |
| `weighted` | 0.595 | 0.496 |

**기본값 `shrunk` 가 공개 소스 설정 중 가장 좋다.** §7 에서 "두 기준이 반대를
가리켜 기본값을 고를 근거가 없다"고 적은 것은 이제 성립하지 않는다 —
제대로 지정한 외부 기준에서도 기본값이 최고다.

### 무엇을 수정하는가

- §7 의 AUC 표는 **동등가중 라벨** 기준이다. 그대로 두되, 더 잘 지정된 기준은
  빈도를 반영한 쪽이다. `MODIMED_POSITIVES=high_freq` 로 재현할 수 있다.
- §7 의 "기본 설정은 우연 수준" 과 "두 기준이 반대를 가리킨다"는 **동등가중
  라벨에서만 성립한다.** 빈도를 반영하면 0.633 이고 간극은 0.039 다.
- §8 의 역추정 결과(held-out 0.803, 부호 일치 48%)는 영향을 받지 않는다 —
  그쪽은 `D = X·e` 를 직접 잰 것이고 상한 0.816 과의 비교였다.

```bash
python3 ourkg/analyze.py disagree
MODIMED_POSITIVES=high_freq python3 ourkg/analyze.py compare
```

### 남은 결함

빈도 처방을 **이분법**으로 근사한 것도 완전하지 않다. 제대로 하려면 주당 처방
횟수를 가중치로 둔 순위 상관(채소 42, 통곡물 35~56, 과일 21, 올리브유 21,
유제품 14~21, 견과 7, 달걀 ≤6, 붉은 고기 3~4, 생선 ≥2, extras ≤3)으로 재야 한다.

---

## 12. ★ 논문을 다시 읽고 찾은 것 — 우리가 건너뛴 PCA 단계

### 무엇을 빠뜨렸나

논문 §4.2.1 의 마지막 문단이다.

> "The resulting incidence matrix 𝐷 combines the effects of different compounds
> present in each food sample on depression, and **dimensionality reduction is
> required** to reduce computational complexity. In our data preprocessing, we
> employ **principal component analysis (PCA)** on the obtained incidence matrix
> to reduce its dimensionality while retaining a significant amount of its original
> characteristics. ... **To ensure that we preserve more than 80% of the variance**
> present in the original sample, **we select five principal components** as the
> final dimension of the matrix."

Fig.4(a) 의 x 축이 principal components 1~85 이므로 PCA 는 **compound 축**에
걸린다. 즉 유사도 `S` 를 85차원 원공간이 아니라 축소 공간에서 계산하라는 뜻이다.

**우리는 이 단계를 꺼 두고 돌려왔다.** 공식 `final.py` 에 PCA 가 없어서 그 경로를
따랐기 때문이다(`PCA_COMPONENTS=0`). 그런데 §8·§10 에서 "유사도 단계가 신호를
깎는다"고 지목한 것이 바로 이 단계다. 논문이 그 자리에 쓰라고 한 처리를 빼고
돌린 뒤 그 단계를 탓하고 있었다.

### 성분 수는 논문의 '5' 가 아니라 논문의 '규칙' 을 따른다

논문이 고정한 것은 숫자가 아니라 **분산 80% 보존**이라는 기준이다. 우리 `F` 의
누적 설명분산:

| 성분 | 1 | 3 | 5 | 8 | **10** | 15 | 20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 누적 분산 | 60.5% | 69.7% | 74.1% | 78.2% | **80.2%** | 83.9% | 86.8% |

**80% 를 넘는 최소 성분 수는 10 이다.** 논문이 5 를 쓴 것은 그쪽 데이터에서 5 가
80% 를 넘었기 때문이다. 같은 규칙을 우리 데이터에 적용하면 10 이고, 이것은 외부
기준으로 고른 값이 아니라 **논문 규칙의 적용**이다.
(`PCA_COMPONENTS=auto`, `PCA_VARIANCE=0.80` 이 기본값이 됐다.)

### 결과 — 공개 소스 E 가 학습한 E 를 이긴다

ModiMedDiet 은 빈도 반영(`MODIMED_POSITIVES=high_freq`, §11 D) 기준이다.

| E 모드 | PCA | **ModiMedDiet AUC** | §4.2.3 Top30 추천군 | Bottom30 비추천군 | Top30 위반 |
|---|---|---:|---:|---:|---:|
| `shrunk` (기본) | 없음 | 0.633 | 7 | 29 | 4 |
| `shrunk` | 5 (논문 숫자) | 0.703 | 2 | 21 | 9 |
| **`shrunk`** | **10 (논문 규칙)** | **0.714** | **7** | **27** | **0** |
| `shrunk` | 20 | 0.678 | 0 | 30 | 0 |
| `vote_norules` | 10 | 0.720 | 7 | 27 | 3 |
| `binary` | 10 | 0.710 | 7 | 30 | 1 |
| **`learned`** (ModiMedDiet 로 학습) | 10 | **0.678** | 1 | 8 | 17 |

**세 가지가 한꺼번에 뒤집힌다.**

1. **§8·§10 의 "유사도 단계가 신호를 깎는다"는 PCA 를 끈 상태에서만 참이다.**
   130차원 원공간에서 코사인 유사도를 재면 축이 많아 이웃 정의가 흐려지고 점수가
   번진다. 논문이 지시한 대로 80% 분산으로 줄이면 반대로 **돕는다**
   (0.633 → 0.714).
2. **학습 없이 공개 소스만으로 0.714 가 나온다.** ModiMedDiet 라벨로 학습한
   `learned` 는 같은 조건에서 0.678 이다. §8 에서 "역추정이 0.803, 공개 소스는
   0.520" 이라고 쓴 것은 `D = X·e` 단독 비교였고, **전체 파이프라인에서는 공개
   소스 E 가 이긴다.**
3. **두 기준이 처음으로 동시에 좋다.** `shrunk` + PCA 10 은 ModiMedDiet 0.714 에
   §4.2.3 Top30 추천군 7 / Bottom30 비추천군 27 / **교차 위반 0** 이다.
   지금까지 어떤 설정도 양쪽을 동시에 만족하지 못했다.

> **★ §13 에서 다시 바뀜.** 논문 §4.2.1 의 `F` 제한을 함께 넣으면 PCA 를 켜는
> 쪽이 Top 30 을 망가뜨린다. 기본값은 PCA 없음이 됐다.

### 그때 기본값을 논문이 명시한 5 로 뒀다

`PCA_COMPONENTS` 의 기본값이 `0`(공식 코드 경로) 에서 **`5`**(논문 §4.2.1 이
명시한 숫자) 로 바뀌었다. E 는 `shrunk` 그대로다.

논문은 같은 문장에서 숫자(5)와 규칙(분산 80%)을 함께 적는다. 논문 데이터에서는
둘이 같지만 우리 `F` 에서는 5 성분이 74.1% 라 어긋난다. **기본값은 논문이 명시한
숫자를 따르고**, 규칙 적용판(10 성분)은 `PCA_COMPONENTS=auto` 로 함께 낸다.
전체 대조는 `ourkg/out/pca_comparison.csv` 에 있다.

| PCA | ModiMedDiet AUC | §4.2.3 Top30 추천군 | Bottom30 비추천군 | Top30 위반 |
|---|---:|---:|---:|---:|
| 없음 (공식 `final.py`) | 0.633 | 7 | 29 | 4 |
| **5 (논문 숫자, 기본)** | **0.703** | 2 | 21 | 9 |
| 10 (논문 규칙 80%) | **0.714** | **7** | 27 | **0** |
| 20 (참고) | 0.678 | 0 | 30 | 0 |

**규칙 적용판이 두 기준 모두에서 낫다는 점은 분명히 남긴다.** 5 성분은 외부
기준에서 0.703 으로 PCA 없음(0.633)보다 좋지만, §4.2.3 에서는 교차 위반이
9 로 늘어난다(베이커리 7·과자 2가 Top 30 에 들어온다). 10 성분은 위반 0 이다.
숫자를 따를지 규칙을 따를지는 논문 자체가 결정해 주지 않는다.

`PCA_COMPONENTS=0` 으로 이전 동작을 재현할 수 있고,
**§5~§11 의 수치는 전부 PCA 를 끈 경로에서 잰 것이다.**

### 교훈

공식 구현과 논문 본문이 어긋날 때 어느 쪽을 따를지가 결과를 바꿨다. 우리는
`final.py` 를 따랐고(REPRODUCTION §3 에서 식 (1)·(2) 의 불일치를 다룬 것과 같은
상황), 그 선택이 §8·§10 의 "유사도 단계 무용론" 을 만들었다.
**논문 본문에만 있고 공개 코드에 없는 단계가 결정적이었다.**

---

## 13. ★ 논문의 `F` 제한과, AUC 가 Top-K 를 잘못 줄세운 일

### A. 논문의 `F` 는 우울증에 연결된 compound 만 갖는다

§4.2.1 첫 문장이다.

> "we apply the knowledge query and inference to obtain a dataset consisting of
> 135 food samples and their associated 85 component compounds, **with these
> compounds being linked to depression**"

우리 `F` 는 FDC 에서 KEGG 로 매핑되는 **130종 전부**였고, 그중 `E` 가 비영인 것은
66종뿐이다. `D = E × Fᵀ` 에는 영향이 없다(E=0 열의 기여가 0). 그러나
**유사도 `S` 가 쓸모없는 64개 축을 포함해 계산되고 있었다.**
`F_COLUMNS=linked` 가 기본값이 됐다 (`all` 로 이전 동작 재현).

### B. 조합을 전부 재 보니 AUC 와 Top-30 이 반대를 가리켰다

`ourkg/out/fcolumns_comparison.csv`. ModiMedDiet 은 빈도 반영 기준(§11 D)이다.

| `F` 열 | PCA | AUC | §4.2.3 추천군 | §4.2.3 비추천군 | 위반 | **MMD Top30 처방** | **MMD Top30 extras** | Top 1 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 130 (all) | 없음 | 0.633 | 7 | 29 | 4 | 5 | 13 | 설탕 대체재 |
| 130 | 5 | 0.703 | 2 | 21 | 9 | 9 | 6 | 밀기울 머핀 |
| 130 | auto(10) | 0.714 | 7 | 27 | 0 | 12 | 4 | 칠리파우더 |
| **66 (linked)** | **없음** | 0.592 | **22** | 27 | 2 | **22** | **1** | **야채주스** |
| 66 | 5 | 0.699 | 1 | 20 | 7 | 5 | 10 | 칠면조 껍질 |
| 66 | auto | **0.729** | 0 | 25 | 0 | **0** | **19** | **증류주** |

**AUC 가 가장 높은 설정의 Top 30 은 처방 0 / extras 19 이고 1위가 증류주다.
AUC 가 가장 낮은 설정의 Top 30 은 처방 22 / extras 1 이고 1위가 야채주스다.**

AUC 는 음식 6,000여 개 전체의 순서를 재므로 **맨 위에 무엇이 오는지에 둔감하다.**
Top-K 추천의 품질은 Top K 안의 구성으로 재야 한다. §7 에서 AUC 를 주지표로
삼은 것이 잘못이었다.

→ ModiMedDiet 채점의 **주지표를 Top K 처방/extras 로 바꿨고**, AUC 는
`modimed_AUC(참고)` 로 남긴다. §7·§11 의 AUC 기반 서열은 이 한계를 안고 읽어야 한다.
(§11 D 의 '빈도 반영' 교정 자체는 영향을 받지 않는다 — 라벨 정의의 문제였다.)

### C. 기본값 — 논문 본문과 논문 결과가 어긋날 때

`F_COLUMNS=linked` + **PCA 없음** 이 두 기준의 Top-30 에서 모두 압도적이다.
그런데 이것은 논문 본문이 쓰라고 한 PCA 를 끄는 설정이다.

- 논문 **본문** §4.2.1: PCA 로 차원을 줄여라
- 논문 **결과** §4.2.3: 추천은 어패류·과일·채소, 비추천은 소시지류

`F` 를 제한한 뒤에는 둘을 동시에 만족시킬 수 없다. PCA 를 켜면 Top 30 이
칠면조 껍질·크림치즈(5성분) 또는 증류주(10성분)가 되어 §4.2.3 서술에서 멀어진다.
**논문이 보고한 결과 쪽을 따라 PCA 를 껐다.**

이것은 §12 의 교훈을 한 겹 더한다. 거기서는 공식 코드와 논문 본문이 어긋났고,
여기서는 **논문 본문과 논문 자신의 결과가 어긋난다.**

```bash
python3 ourkg/analyze.py recommend                      # 기본: linked, PCA 없음
F_COLUMNS=all PCA_COMPONENTS=5 python3 ourkg/analyze.py recommend   # §12 설정
```

---

## 14. Algorithm 1 의 `Threshold` — 구현했고, 켜면 나빠진다

### 무엇이 빠져 있었나

§4.2.2 Algorithm 1 line 8 이다.

> `8: P = D × S : **Threshold** and Top K`

우리는 Top K 만 하고 Threshold 를 걸지 않았다. §12 의 PCA 와 같은 성격의 누락이다.
논문은 Threshold 가 무엇에 걸리는지 밝히지 않는데, 유사도로 인용한
**Sarwar et al. (2001) item-based CF** 에서 Threshold 는 **이웃 선택**을 뜻한다 —
약한 유사도를 예측에서 빼는 것이다. Top K 는 출력 `P` 에, Threshold 는 `S` 에
걸린다는 읽기다. 네 가지로 구현했다.

| `SIM_THRESHOLD` | 뜻 |
|---|---|
| `none` | 자르지 않는다 (기본) |
| `positive` | `S < 0` 을 0 으로 — 매개변수가 없어 사전 지정 가능 |
| `topn:<N>` | 음식마다 가장 닮은 N 개만 (Sarwar 의 model size) |
| `q<p>` | `|S|` 의 p 분위수 미만을 0 으로 |

### 결과 — 어떤 방식으로 잘라도 상위가 무너진다

`ourkg/out/threshold_comparison.csv`

| Threshold | §4.2.3 추천군 | 비추천군 | **MMD Top30 처방** | **extras** | Top 1 |
|---|---:|---:|---:|---:|---|
| **`none` (기본)** | **22** | 27 | **22** | **1** | 야채주스 |
| `positive` | 0 | 27 | 0 | 19 | 맥주 |
| `topn:1000` | 1 | 30 | 0 | 16 | 몰트비어 |
| `topn:100` | 1 | 24 | 0 | 16 | 프로즌 다이키리 |
| `q50` | 1 | 28 | 0 | 16 | 몰트비어 |
| `q90` | 1 | 27 | 0 | 16 | 하드셀처 |

Top 1 이 전부 술이 된다. §4.2.3 추천군은 22 → 0~1, ModiMedDiet 처방군은 22 → 0 이다.

### 왜 그런가 — 추천은 **음(−)의 유사도**가 만들고 있었다

`S` 의 양수 절반과 음수 절반을 따로 돌려 봤다.

| `S` | §4.2.3 추천군 | 비추천군 | MMD 처방 | extras | Top 1 |
|---|---:|---:|---:|---:|---|
| 전체 (기본) | 22 | 27 | 22 | 1 | 야채주스 |
| 양수만 (`positive`) | 0 | 27 | 0 | 19 | 맥주 |
| **음수만 (`negative`)** | **18** | 11 | **22** | 2 | **야채주스** |

**음수 절반만으로 상위가 거의 그대로 복원된다.** 양수 절반만 쓰면 술이 올라온다.

기전은 식 (2) 에 있다. `P_j = Σ_i D_i · S_ij` 에서, 해로운 음식(`D_i < 0`)과
**성분 구성이 반대인**(`S_ij < 0`) 음식은 곱이 양수가 되어 점수가 오른다.
즉 이 알고리즘이 실제로 하는 일은 **"이로운 음식과 닮은 것을 찾기" 가 아니라
"해로운 음식과 가장 다른 것을 찾기"** 다. 채소가 올라온 것은 육류와 성분
구성이 반대이기 때문이다.

반대로 Bottom 30 은 양수 쪽이 만든다(음수만 쓰면 비추천군이 27 → 11 로 준다).
해로운 음식과 닮은 음식이 음수 점수를 받는 경로다.

Threshold 를 걸면 이 음수 절반이 잘려 나간다. `positive` 는 말 그대로 다 자르고,
`topn`·`q` 도 절댓값이 큰 쪽을 남기지만 양수 이웃이 더 조밀해 음수가 먼저 빠진다.

### 그래서 기본값은 `none`

논문 본문에 있는 단계지만 **켜면 논문이 보고한 §4.2.3 결과에서 멀어진다.**
§13 의 PCA 와 같은 구도다 — 논문 본문과 논문 결과가 어긋나고, 결과 쪽을 따랐다.
`SIM_THRESHOLD=positive|topn:N|q<p>` 로 본문 쪽을 실행할 수 있고,
진단용 `negative` 도 남겼다.

### 부수 — REPRODUCTION §16 의 V3 를 설명한다

재현 쪽에서 "similarity 단계를 빼도 순위가 거의 같다(ρ +0.761)"는 관찰이 있었다.
여기서 보면 그 단계는 **양수·음수 두 반쪽이 서로 다른 끝을 만드는** 구조다.
통째로 빼면 둘이 함께 사라져 순위가 크게 흔들리지 않지만, 한쪽만 자르면
해당 끝이 무너진다.

---

## 15. 과정에서 드러난 것

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

## 16. 한계

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

## 17. 산출물

| 파일 | 내용 |
|---|---|
| `out/ourkg.nt` | RDF N-Triples 3,168,163 |
| `out/kg_stats.csv` | 논문 Table 1 대응 통계 |
| `out/foods.csv` | 음식 14,719 (fdc_id, 카테고리, 측정 compound 수) |
| `out/food_compound_long.csv` | 음식 × compound 중량 768,157 (g/100g) |
| `out/compound_depression.csv` | ProMENDA 극성 E (binary / shrunk / BH q) |
| `out/compound_depression_menda.csv` | MENDA 2020 극성 |
| `out/compound_evidence.csv` | 근거 4종 점수 + 결합 6가지 |
| `out/e_mode_comparison.csv` | E 구성 방식 비교표 (§4.2.3 + ModiMedDiet 두 기준) |
| `out/modimed_labels.csv` | ModiMedDiet 정답셋 라벨과 규칙 출처 |
| `out/compound_learned.csv` | ModiMedDiet 로 역추정한 E |
| `out/invert_comparison.csv` | 역추정 E vs 공개 소스 E 부호 대조 (전수) |
| `out/compound_depression_stype.csv` | 연구 설계별 E 7변형 |
| `out/stype_comparison.csv` | 설계별 E 채점표 |
| `out/food_form.csv` | 구조·가공 축 19 (FDC 측정값) |
| `out/learned_form.csv`, `out/learned_both.csv` | 그 축으로 역추정한 가중치 |
| `out/disagreement_by_group.csv` | 두 기준이 갈리는 지점의 음식군별 분해 |
| `out/pca_comparison.csv` | PCA 성분 수별 두 기준 채점 |
| `out/fcolumns_comparison.csv` | `F` 열 제한 × PCA 조합 채점 (§13) |
| `out/threshold_comparison.csv` | Algorithm 1 Threshold 변형 채점 (§14) |
| `out/compound_microbe.csv` | KEGG 재계산 compound-미생물 2,124 |
| `out/microbes.csv` | NCBI 갱신 미생물 127 |
| `out/microbe_disease.csv`, `out/microbe_disease_mikg.csv` | 미생물-질환 |
| `out/recommendation.csv`, `out/recommendation.png` | 추천 순위·시각화 |
| `out/eval_method1.csv`, `out/eval_method2.csv`, `out/eval_sparql.json` | §5.1·§4.1 평가 |

`out/` 의 결과표·평가 결과는 레포에 함께 올라가 있다. 대용량 둘만 제외한다 —
`ourkg.nt` (470 MB) 와 `food_compound_long.csv` (48 MB). 둘 다 `python3 ourkg/run_all.py`
로 재생성한다 (`food` 약 12분, `kg` 약 2분).
