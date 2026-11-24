# ourkg — 최신 FDC + ProMENDA 로 다시 만든 Food4healthKG

논문 Fu et al. (2023) *Food4healthKG* 의 **구축 방식과 평가 방식**을 그대로 쓰되,
데이터를 최신 공개본으로 바꿔 우리 KG 를 만든다. 원 논문 **재현**은 레포 루트의
`reconstruct.py` → `run_recommendation.py` 경로이고, 이 디렉토리와 섞지 않는다.
(재현 수치는 [`REPRODUCTION.md`](../REPRODUCTION.md), 미해결 문제는 [`PROBLEMS.md`](../PROBLEMS.md))

**방법론 전체는 [`METHODS.md`](METHODS.md) 에 있다** — 전제·구축·추천·평가와
알려진 한계. **어떤 데이터를 어떻게 썼는지는 [`DATA.md`](DATA.md) 에 있다** — 축별로 출처·받는 법·뽑은 것·이어붙인 법·한계. 이 문서는 설계 **결정**, [`RESULTS.md`](RESULTS.md) 는 실험과 기각 기록이다.

## 바뀐 것

| 축 | 논문 (2023) | ourkg |
|---|---|---|
| 음식·성분 | FDC 34,250 샘플 (2022 배포본) | FDC 전체 2,101,279 항목 (2026-09 배포본) |
| 우울증-대사물 | MENDA 5,675 관계 | **ProMENDA** (Pu et al. 2024) 22,519 레코드 / 995 연구 |
| compound | KEGG 230 metabolite | **KG 층 154 / F 층 130** — 논문처럼 두 층을 나눈다 |
| 미생물 | NCBI taxonomy 322,917 | efetch 로 **현재 값** 갱신 **485종** (배포본 127 + **Disbiome 333** + 보탠 30) |
| compound-미생물 | KEGG (2022) | KEGG REST 재계산 **10,257**(55% 속 수준) + **VMH/AGORA2 44,094** (유전체 재구성 — 예측) |
| 미생물-정신질환 | MiKG 1,234 | MiKG 원본 TTL 406쌍 + **Disbiome 1,193** (외부 큐레이션) |
| 질환 분류 | MeSH + SNOMED CT | MeSH SPARQL — tree number + **상위 계층 242종**. SNOMED 는 MiKG xref 63 |
| 식품 온톨로지 | FoodOn + Chinese Food Ontology | **FoodOn 은 EBI OLS 에서 직접** — 음식 8,165 · 클래스 1,096. 중국 온톨로지는 배포 subset |

우리 KG 는 **triple 3,509,569 · 관계 34 · 엔티티 858,651** 이다(논문 13,346,991 ·
140 · 1,637,915). 격차는 SNOMED CT 429 만과 NCBI taxonomy 131 만을 통합하지 않은
데서 온다 — 전자는 배포되지 않았고 후자는 정신질환 연관 종만 쓴다. 음식-성분 축만
보면 우리 쪽이 더 크다(321 만 vs 233 만).

## 실행

**`.venv` 를 켜야 한다** — 설치는 [루트 `README.md`](../README.md) 의 설치 절.

```bash
source .venv/bin/activate

python3 ourkg/run_all.py                    # 구축 → 분석 → 외부 검정 → 쓸기
python3 ourkg/run_all.py kg recommend       # 일부만
python3 ourkg/run_all.py --env              # 환경변수 전수 (소스에서 긁는다)

python3 ourkg/build.py                      # 구축만 (food promenda microbe kg)
python3 ourkg/analyze.py recommend          # 분석 한 단계만
python3 ourkg/sweep.py gutbrain             # 설정 쓸기 하나만
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

구축 4단계는 `build.py`, 분석 2단계는 `analyze.py` 에 함수로 들어 있다.
각 단계는 앞 단계의 CSV 만 읽으므로 따로 돌려도 된다.

| 파일 | 단계 | 하는 일 | 주요 산출물 |
|---|---|---|---|
| `build.py` | `food` | FDC 원본 2,700만 행 스트리밍 → 단위 g 환산 → 논문 §3.2 라벨 병합 → 카테고리 정규화 | `food_compound_long.csv`, `foods.csv` |
| | `form` | FDC 측정값에서 구조·가공 축 19개를 뽑는다 (F 확장) | `food_form.csv` |
| | `promenda` | ProMENDA → compound별 우울증 극성 E | `compound_depression.csv` |
| | `evidence` | ProMENDA·MENDA·재현 규칙·AFS 네 근거로 E 구성 (결합 6가지) | `compound_evidence.csv` |
| | `microbe` | MeSH tree / NCBI taxonomy / KEGG 로 미생물 축 | `microbes.csv`, `compound_microbe.csv`, `microbe_disease*.csv` |
| | `kg` | 논문 §3.3 표현 규약대로 RDF 출력. 근거 4종과 결합값 6가지도 함께 싣는다 | `ourkg.nt`, `kg_stats.csv` |
| `analyze.py` | `recommend` | 논문 Algorithm 1 (식 1·2) | `recommendation.csv`, `recommendation.png` |
| | `compare` | E 구성 방식·경로를 논문 §4.2.3 기준으로 대조 | `e_mode_comparison.csv` |
| | `pathcheck` | gut-brain 경로 compound 를 CSV 와 KG(SPARQL)에서 각각 뽑아 대조 | `gutbrain_compounds.json` |
| | `external` | SMILES trial ModiMedDiet 로 외부 정답셋을 만든다 | `modimed_labels.csv` |
| | `invert` | 그 라벨로 E 의 부호를 역추정하고 공개 소스 E 와 대조 | `compound_learned.csv`, `invert_comparison.csv` |
| | `stype` | ProMENDA 를 연구 설계별로 나눠 E 를 만들고 외부 기준으로 채점 | `stype_comparison.csv` |
| | `disagree` | 두 평가 기준이 갈리는 지점을 음식군별로 분해 | `disagreement_by_group.csv` |
| | `evaluate` | §4.1 SPARQL Q1~Q3, §5.1 방법 1·2 | `eval_*.csv/json` |
| `common.py` | — | 경로·단위 환산·라벨/카테고리 정규화 공유 | |
| `foodon_match.py` | — | FoodOn 매칭 (OLS) | `food_foodon.csv` |
| `probiotic_rct.py` | `build`·`test` | **외부 검정** — 프로바이오틱스 RCT 25 종 | `setup/probiotic_rct.csv` |
| `metabolome_check.py` | `build`·(기본) | **외부 검정** — 분변 대사체 코호트 | `compound_microbe_measured.csv` |
| `sweep.py` | `fcolumns`·`modimed_rho`·`gutbrain`·`simthr`·`ezero`·`emode`·`fscale`·`simspace`·`simsign`·`nosim`·`dedup`·`union`·`learned`… | 설정 쓸기 — 두 기준으로 채점 | `*_comparison.csv` |
| `consensus.py` | — | **합의 Top-K** — 부분표집에서 반복 선택되는 음식 | `consensus_*.csv` |
| `bootstrap.py` | — | **Top-K 지표의 표집 변동** (주지표 선정 근거) | `bootstrap_ci.csv` |
| `nhanes.py` | — | **섭취-결과 E** (NHANES) | `compound_depression_nhanes.csv` |
| `run_all.py` | — | 위를 순서대로 호출. `--env` 로 환경변수 전수 | |

## 결과

### KG 규모 (논문 Table 1 대응)

| source | relation | entity | triples |
|---|---|---|---|
| FoodData Central | 9 | 783,035 | 3,146,277 |
| MiKG | 6 | 1,060 | 6,802 |
| MeSH | 2 | 245 | 5,400 |
| ProMENDA | 6 | 1,289 | 5,150 |
| KEGG | 3 | 213 | 2,384 |
| evidence | 15 | 278 | 1,560 |
| NCBI taxonomy | 5 | 210 | 590 |
| **Total** | **30** | **785,572** | **3,168,163** |

`evidence` 는 논문에 대응이 없다 — E 의 근거(ProMENDA·MENDA·재현 규칙·AFS)와
결합값을 KG 안에서 추적하려고 추가한 축이다. [`RESULTS.md`](RESULTS.md) §5.

논문은 140 relation / 1,637,915 entity / 13,346,991 triple 이다. 차이의 대부분은
온톨로지 축(SNOMED CT 429만, NCBI taxonomy 전체 131만)을 통합하지 않은 데서 온다 —
FoodOn 은 OLS 로 직접 받아 141,564 triple 로 논문(79,769)을 넘어섰다. 음식-성분 축만 보면 우리 쪽이 더 크다 (321만 vs 233만).

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
| compounds categories | 3 | O | KEGG compound — KG 층 154 / F 층 130 |
| compounds in food and gut | 4 | O | FDC 성분 + compound-미생물 **37,633**(KEGG 2,124 + VMH 35,509) |
| bacteria taxonomy | 3 | O | NCBI taxonomy 127종, 학명·rank·계통 갱신 |
| food categories | 4 | O | FDC SR 27군 + WWEIA→SR 큐레이션 링크 + **FoodOn 클래스 1,096** |
| disease classification | 3 | O | MeSH tree number + **상위 계층 242종**. SNOMED 는 MiKG xref 63 |

완전 답변 16 / 부분 4 / 불가 0.

### §5.1 방법 2 — 추론 15건 문헌 검증

논문은 수작업 PubMed 검색으로 11 confirmed / 3 unknown / 1 contradicted 를 보고한다.
여기서는 **초록 판독까지** E-utilities 로 자동화한다 — `esearch` 로 상위 20 편을
관련도순으로 받고 `efetch` 로 초록을 읽어, 두 엔티티가 **한 문장에** 함께 나오고
연관 표현이 있으면 +1, 부정 표현이면 −1 로 판정한다 (`ABS_K` 로 편 수 조절).

판정 기준이 논문에 명시돼 있지 않으므로, 같은 자를 **논문 자신의 Table 5 15건에도**
적용해 판별력을 쟀다 (`out/eval_method2_calibration.csv`).

| 기준 | confirmed 11 통과 | non-confirmed 4 통과 | 균형정확도 |
|---|---:|---:|---:|
| 색인 3항 공출현 (두 엔티티 + 근거 물질) | 1/11 | 0/4 | 0.55 |
| 색인 2항 공출현 (두 엔티티만) | 10/11 | 3/4 | 0.58 |
| **초록 판독 (현재)** | **10/11** | **1/4** | **0.83** |

색인 공출현 두 자는 **버렸다.** 3항은 신호가 없고(근거 물질 이름을 넓혀도 논문
Diet 7건이 0/7), 2항은 `Anxiety AND depression` 이 19만 건이라 "두 주제가 함께
연구되는가"를 잴 뿐이다. 2항 적중 수는 `n_hits_pair_only` 로 참고만 남긴다.

논문 15건을 우리 자로 재면 11/15 가 통과한다 — 논문이 보고한 값과 같다.

**위양성을 줄이는 네 가지를 넣었다.** 처음 판은 우리 15건이 13/15 였는데
`Mustard greens × depression` 이 "mustard oil 로 내장통증을 유발한" 실험으로,
`Pork × depression` 이 증례 보고로 잡혔다. ① 어간을 자르지 않고 **온전한 단어**로
맞추고(복수·소유격만 허용), ② 음식 행은 문장에 **식이 맥락**을 요구하고,
③ `inbreeding depression` 같은 동형이의어를 버리고, ④ `Case Reports` 를 뺀다.
⑤ 여러 단어 이름은 **구(句)로** 맞춘다(`Sex behavior disorder` 가 "REM sleep
behavior disorder" 를 잡았다). ⑥ 인용문을 두 엔티티가 가장 가까이 붙은 문장의
**매치 주변**으로 고른다.

논문 15건 판별력은 여섯 번의 수정 내내 0.83 그대로이고 우리 15건은 **8/15** 로
내려갔다 — 13 중 5 건이 근거 없는 통과였으므로 내려간 것이 개선이다. 질환 쌍에만
거는 제약(나열 제외·쌍 전용 cue)도 재 봤지만 참을 떨어뜨리기만 해 기각했다
(RESULTS §4.3). 이 숫자를 논문의 11/15 와 순위처럼 비교하지는 않는다.

그래서 산출물에 `quote`(근거 문장)·`sent_assoc`·`sent_negative` 를 넣었다.
**방법 2 는 품질 지표가 아니라 검수 도구로 쓴다.** 모드·설정 선택에는 §4.2.3
서술과 ModiMedDiet 외부 정답셋을 쓴다.

## 설계 결정 (실행 전에 고정, 결과를 보고 고르지 않았다)

각 항목은 환경변수로 되돌릴 수 있다.

1. **단위 g 환산** (`UNIT_MODE`) — 논문 §3.1 "quantified in weight".
2. **라벨 병합** — 논문 §3.2 "splitting the food labels by commas ... exact matching".
   FDC 항목 1,949,651 → 음식 482,937.
3. **음식당 최소 compound 20** (`MIN_COV=20`) — 성분이 1~2개만 측정된 항목은
   유사도 계산이 성립하지 않는다.
   **열 쪽에는 하한을 두지 않는다.** `MIN_FOODS` 를 25~1500 으로 재 봤는데
   전부 기준선보다 나빴다 — 측정 음식이 100 종 미만인 기존 열 18 개도 **신호를
   갖고 있다.** 희소하다고 해로운 것이 아니다. (FDC 가 거의 측정하지 않는 성분을
   매핑표에 더 넣으면 두 기준이 무너지는 것은 사실이지만, 그 기전은 희소성으로
   설명되지 않는다 — [`RESULTS.md`](RESULTS.md) §4.3.)
4. **E 의 근거 축소** (`E_MODE=shrunk`, `SHRINK_K=10`) — ProMENDA 는 논문이 쓴
   MENDA 보다 커서 연구 2~3건짜리 compound 도 다수결로 ±1 을 받는다. 예: Ethanol 은
   연구 3건(4:1)으로 +1 이 되어 칵테일류를 Top 30 에 몰아넣었다. `(pos-neg)/(pos+neg+K)`
   로 0 쪽으로 축소한다. `E_MODE=binary` 가 논문 §4.2.1 그대로, `E_MODE=sig` 는
   이항검정 BH q<0.05 인 compound 만 (FDC compound 73종 중 5종만 남는다).
   **`K` 민감도는 2026-11-18 에 처음 쟀다** — `K=0`(축소 없음)이 ModiMedDiet
   처방군 7/30 · §4.2.3 추천군 8/30 인데 `K=10·20` 이 23/30 · 22/30 으로 평탄한
   꼭대기를 이룬다. 실행 전에 고른 10 이 그 구간 안이었다. [`RESULTS.md`](RESULTS.md) §5.
5. **성분(열)별 정규화** (`NORM=compound`) — 공식 `final.py` 의 행별 min-max 는
   음식 135종에서는 되지만 14,000종에서는 무너진다. 음식마다 '그 음식의 최대 성분'이
   1.0 이 되므로 최대 성분이 우연히 E=+1 인 음식이 전부 상위에 온다. 열별 정규화는
   논문 Fig.4(c) "we normalize the compounds in the two groups of foods separately"
   를 근거로 한다. `NORM=row_minmax` 로 공식 경로 실행 가능.
6. **논문 §4.2.1 의 `F` 제한** (`F_COLUMNS=linked`) — 논문의 `F` 는 "compounds
   being linked to depression" 만 열로 갖는다. 우리 `F` 는 130열 전부였고 `E` 가
   비영인 것은 66종이라, 유사도 `S` 가 쓸모없는 64축을 포함해 계산되고 있었다.
   제한하면 §4.2.3 Top30 추천군이 7 → **22** 가 된다. `F_COLUMNS=all` 로 되돌린다.
7. **PCA 는 끈다** (`PCA_COMPONENTS=0`) — 논문 본문 §4.2.1 은 PCA 를 쓰라고 하지만,
   `F` 를 제한한 뒤에는 PCA 를 켜면 Top 30 이 칠면조 껍질(5성분)·증류주(10성분)가
   되어 논문이 보고한 결과 §4.2.3 에서 멀어진다. 논문 본문과 논문 결과가 어긋나고,
   결과 쪽을 따랐다. `PCA_COMPONENTS=5|auto` 로 본문 쪽 실행. [`RESULTS.md`](RESULTS.md) §12·§13.
8. **논문 §4.2.1 의 PCA — 2026-11-18 재측정** (#7 과 같은 결정, 근거 갱신).
   유사도 `S` 를 compound 원공간이 아니라 PCA 축소 공간에서 계산하는 단계다.
   공식 `final.py` 에는 없다. 논문은 같은 문장에서 숫자(5)와 규칙(분산 80%)을
   함께 적는데 우리 `F` 에서는 5 성분이 74.1% 라 어긋나, `auto` 는 10 성분이 된다.

   | `PCA_COMPONENTS` | MMD 처방/extras | AUC | §4.2.3 추천군 | 비추천군 | 위반 | Top 1 |
   |---|---:|---:|---:|---:|---:|---|
   | **0 (기본)** | **23 / 1** | 0.585 | **21** | **26** | **0** | 야채주스 |
   | 5 (논문의 숫자) | 7 / 12 | 0.698 | 3 | 19 | 9 | 칠면조 껍질 |
   | 10 · auto (분산 규칙) | 0 / 18 | 0.693 | 0 | 16 | 1 | **크림 리큐어** |

   **AUC 만 오르고 Top-K 는 무너진다.** AUC 가 가장 높은 설정의 Top 30 이 처방
   0 / extras 18 이고 1 위가 술이다 — §13 에서 주지표를 Top-K 로 바꾼 이유가
   그대로 재현된다. 그래서 끈다.

   > **이전 판 정정.** 여기에는 "`auto`(10 성분)가 AUC 0.714 에 교차 위반 0 으로
   > **두 기준 모두에서 낫다**" 고 적혀 있었다. 그것은 `F_COLUMNS` 제한·집계
   > 수정·WWEIA 군 링크 **이전**에 AUC 를 주지표로 쓰던 때의 기록이고, 지금
   > 데이터에서는 성립하지 않는다(추천군 21 → 0, 처방군 23 → 0). 설계 결정 #7
   > 과도 모순이었다. 상세는 [`RESULTS.md`](RESULTS.md) §12.
9. **Algorithm 1 의 `Threshold` 는 걸지 않는다** (`SIM_THRESHOLD=none`) —
   §4.2.2 line 8 의 "Threshold and Top K" 를 Sarwar et al. (2001) 의 이웃 선택으로
   읽어 네 가지로 구현했는데, 어떤 방식으로 잘라도 Top 1 이 술이 되고 §4.2.3
   추천군이 22 → 0~1 로 무너진다. 추천을 만드는 것이 **음(−)의 유사도**이기
   때문이다 — 해로운 음식과 성분 구성이 반대인 음식이 점수를 받는다.
   [`RESULTS.md`](RESULTS.md) §14.
10. **식 (2) 에 정규화 없음** (`SIM_NORM=none`) — 공식 `final.py` 는 `p[i] /= sum(S[:,i])`
   를 덧붙이는데, 식 (2) 에는 없다. adjusted cosine 은 음수를 가지므로 이 열합이
   0 근처가 될 수 있고, 성분이 적은 음식의 열합이 ~15 (중앙값 3,894)까지 떨어져
   점수를 폭발시켰다. `SIM_NORM=colsum` 으로 공식 경로 실행 가능.
11. **추천 코호트를 분석 측정 데이터로 제한** (`DATA_TYPES=curated`) — 논문 §4.2 의
   135개 음식은 전부 Foundation / SR Legacy / FNDDS 다. branded_food 는 라벨 신고값이라
   대부분 성분이 결측이고, 성분이 거의 없는 탄산수·단백질파우더가 상위를 차지한다.
   KG 자체(04)는 FDC 전체를 담는다. `DATA_TYPES=all` 로 포함 가능.

## 평가 기준 둘

판정에 두 기준을 쓴다.

- **논문 §4.2.3** — 논문이 자기 알고리즘의 출력을 서술한 문장. 재현·대조용.
- **ModiMedDiet** (Jacka et al. 2017 SMILES trial) — 우울증 RCT 에서 실제로
  처방된 식단. 출처가 독립인 외부 기준.

갈라지는 지점은 **붉은 고기 하나의 축**이다 — §4.2.3 은 비추천으로 두지만
ModiMedDiet 은 lean red meat 를 주 3-4회 처방한다. 음식군별로 분해해 확인했다:
충돌하는 군은 Beef 와 Lamb/Veal 둘뿐이고, 설정을 바꾸면 붉은 고기 세 군이
바닥(17~21 백분위)에서 상위(72~81)로 통째로 올라간다 (§11 A·C).

그리고 처방 **빈도**(채소 6회/일 vs 붉은 고기 주 3-4회)를 반영하면 두 기준의
간극이 0.209 → 0.039 로 거의 사라지고, 기본값이 공개 소스 설정 중 최고가 된다
(§11 D). 상세는 [`RESULTS.md`](RESULTS.md) §7·§11.

왜 반대인지는 §8 에서 측정했다 — ProMENDA·MENDA 는 "우울증 환자에서 대사물 농도가
높/낮다"를 재는 case-control 메타볼로믹스고, 논문 §4.2.1 의 `E` 는 "먹으면 완화/악화"
로 정의된다. 논문은 둘을 동일시한다. 부호 일치 48% 가 그 가정의 측정값이다.

## 경로

추천 점수 `D = E x F^T` 에는 미생물이 들어가지 않는다 — 논문 §4.2.2 식 (1)(2) 의
정의가 그렇다. 미생물 축은 KG 와 §4.1 쿼리에만 쓰인다. `PATH_MODE=gutbrain` 으로
미생물을 거치는 compound 만 남겨 비교할 수 있다. compound 가 절반으로 줄어도
순위 상관이 +0.99 다 — [`RESULTS.md`](RESULTS.md) §6.

추천 코드는 SPARQL 을 쓰지 않고 중간 CSV 를 읽는다(속도). 그 CSV 가 KG 와 같은
경로를 내는지는 `analyze.py pathcheck` 로 검사한다 — 현재 52종으로 정확히 일치한다.

## 한계

- **중국 식품 온톨로지는 배포 subset 만.** FoodOn 은 EBI OLS 에서 직접 받아
  음식 8,165 · 클래스 1,096 을 붙였지만(논문 79,769 triple 대비 141,564),
  중국 온톨로지는 카테고리 39 · 음식 174 에 머문다.
- **SNOMED CT 는 라이선스.** 배포본에 라벨·계층이 없어 전체를 못 쓴다. MiKG 가
  자기 엔티티에 단 SCT id 63 개만 쓴다. 질환 상위 분류는 **MeSH 트리로 대체**했다.
- **미생물 축이 얇다 — 다만 기준은 고쳤다.** 162 → **485종**(논문 322,917).
  넓히는 기준이 "우리가 아는 균" 이라 **스스로를 가두던 구조**를 Disbiome
  (외부 큐레이션)으로 바꿨다. **닿는 균이 적던 문제**(KEGG organism 167/485)는
  종 → 속 사다리로 고쳤다 — **378/485**, KEGG 링크 4,571 → **10,257**.
  compound 연결 합집합은 **종 수준 182종(38%) · 속 포함 379종(78%)** 으로
  **갈라서 읽어야 한다** — KEGG 링크의 55%가 속 수준 매칭이고 "이 속의 어떤
  유전체가" 라는 더 약한 주장이기 때문이다. 읽는 자리를
  `common.compound_microbe(sources, rank)` 하나로 합쳤고, 평가 어댑터는 종
  수준만 쓴다. KG 는 `KEGG` / `KEGG(속 수준)` 으로 출처를 가른다. 아직 못 잇는
  107종은 과·목·문 수준(60)과 KEGG 에 유전체가 없는 종(47)이다.
  [`DATA.md`](DATA.md) §6·§7·§12.
- **미생물-정신질환.** 공개 Disease_Bacteria 에서 MeSH F03 으로 걸러지는 관계는
  115건(질환 6종)뿐이고 우울증은 1건이었다. MiKG 406쌍 + Disbiome 1,193쌍
  (질환 23종, 우울증만 균 32종)을 보태 논문의 1,234 를 넘겼다.
- **논문 §3.3 의 474만 추론을 재구현하지 않았다.** 전이 추론과 공통 세균 추론만 쓴다.
- **방법 2 를 평가 지표로 쓰지 않는다.** 우리 15 건이 **15/15 가 1** 이고 그중
  11 건이 합병증 추론인데 질의가 질환 두 개뿐이라 잘 알려진 동반이환을 확인할
  뿐이다(RESULTS §18·§28). 쓸 수 있는 것은 **논문 15 건 대조(12/15)** 뿐이다.
- (이전 기록) **방법 2 는 품질 지표가 아니라 검수 도구다.** 초록 판독으로 판별력 0.83 을
  얻었지만(논문 15건 기준), 우리 15건의 숫자를 논문의 11/15 와 순위처럼 비교하지
  않는다. [`RESULTS.md`](RESULTS.md) §4.3.

## 산출물

`out/` 의 결과표·평가 결과는 레포에 함께 올라가 있다(리뷰용). 대용량 둘만 제외한다 —
`ourkg.nt` (470 MB), `food_compound_long.csv` (48 MB). `python3 ourkg/run_all.py` 로
재생성한다. 파일별 내용은 [`RESULTS.md`](RESULTS.md) §8.
