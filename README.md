# Food4healthKG 재현 및 확장 프로젝트

> 추천시스템 수업 프로젝트 — Food4healthKG (Fu et al., AIM 2023) 재현 + 확장

- **[PROBLEMS.md](PROBLEMS.md)** — 지금 무엇이 막혀 있고 왜 막혔는지
- [REPRODUCTION.md](REPRODUCTION.md) — 조사 과정 전체 기록 (절 번호로 인용)

---

## 1. 프로젝트 개요

### 원 논문
- **제목:** Food4healthKG: Knowledge graphs for food recommendations based on gut microbiota and mental health
- **저널:** Artificial Intelligence in Medicine 145 (2023) 102677
- **핵심:** 음식–장내미생물–정신건강 Knowledge Graph 구축 → 우울증 대상 음식 추천
- **알고리즘 (Algorithm 1):** 성분 행렬 F(food × compound) × incidence E(compound → depression, ±1)
  → adjusted cosine similarity S → `P = D × S` → Top-K 추천

### 재현 과정에서 발견한 문제
원 논문 repo 의 `final.py` 가 읽는 입력 4개(`food.csv`, `foodname.csv`, `weight.csv`, `acs04.csv`)와
전처리 원본(`metabolite_bacteria.xlsx`)이 누락되어 있다. 이를 아래 자료로 역설계했다.
- 논문 repo 의 KG triple 11개, `heatmap.xlsx`(Fig. 4(c) 원본), `p5_foodname.txt`(논문 순위)
- FDC Full Download 원본 (repo 의 `food_nutrient.csv` 는 Excel 행 한계에서 잘려 있었다)
- MENDA 원본 5,675 entries, ProMENDA 22,519 entries, MiKG

그 밖에 논문이 적지 않은 것을 논문 산출물에서 역산했다.
- **성분 단위:** 저자는 모든 성분을 g 으로 환산했다(heatmap 에서 계수 MG 10^-3, UG 10^-6 역산).
  이것을 빠뜨리면 F 가 논문과 전혀 다르다 (REPRODUCTION §16.1).
- **85 compound 목록:** `heatmap.xlsx` 의 열에서 추출했다.
- **ProMENDA 극성:** 논문 §4.2.1 규약("우울증에서 높으면 +1")을 연구 설계에 맞게 적용한다.
  이전에는 step2 와 step3 가 서로 반대 규약을 썼다 (PROBLEMS §7).

### 최종 재현 상태 (2026-09-29, `python3 tools/scorecard.py`)

| 층위 | 우리 결과 | 논문 | 판정 |
|------|-----------|------|------|
| Foods | 135 / 135 | 135 | ✅ |
| Compounds | 85 / 85 | 85 | ✅ |
| 성분 행렬 F vs 논문 heatmap | 행 코사인 0.981 | — | ✅ |
| 측정 밀도 (compound 수 중앙값) | 28 | 33 | ⚠️ FDC 판 차이 |
| PCA 80% 도달 성분 수 (§4.2.1) | 5 | 5 | ✅ |
| E 방향 확보 | 69 / 85 | 85 | ⚠️ |
| 논문이 부호를 명시한 compound (gold) | 8 / 9 | 9 | ✅ |
| **추천 순위 Top30 겹침** (우연 6.7) | **18 / 30** | 30 | ✅ |
| **추천 순위 Bottom30 겹침** (우연 6.7) | **15 / 30** | 30 | ✅ |
| 순위 Spearman | **+0.786** | 1.0 | ✅ |
| 논문 주장 6개 (§4.2.3, Fig. 4·5) | 3 / 6 | 논문 순위 자신 4 / 6 | ⚠️ |
| Query 2 → Table 3 | 8 / 8 | 8행 | ✅ |
| Query 3 → Table 4 | 5 / 5 (MiKG 로 SNOMED 이름 복원) | 5행 | ✅ |
| Query 1 → Table 2 | 6 / 8 값 재현 | 8행 | ⚠️ 논문 값이 쿼리 결함으로 틀림 |
| §5.1 문헌 검증 (Table 5) | Complication 7 / 8, Diet 2 / 7 (엄격) | 문헌 확인 11 / 15 | ⚠️ |
| §5.1 전문가 20문항 | 공개 KG 로 답 재현 18 / 20 | 전문가 정확도 0.95 / 0.90 / 0.95 | ⚠️ 재현되고 타당한 답은 13 / 20 |

**대체로 재현됐다.** 데이터와 알고리즘 구조가 재현됐고, 추천 순위는 Spearman +0.786
으로 추천·비추천 양쪽 모두 우연 수준을 크게 넘는다. 우리 Top30 과 논문 Bottom30 이
겹치는 음식은 0개다. 남은 격차는 E 다. 논문의 `weight.csv` 가 없어 E 를 확정할 수 없고,
논문 순위가 함의하는 E 와의 부호 일치는 38/57 이다.

> 주의: 이 순위는 식물/동물 1비트 규칙(Spearman +0.695)으로도 상당 부분 설명된다.
> 85 compound 모델이 그 위에 더하는 정보는 +0.09 정도다.

---

## 2. 필요한 Repository & 데이터

### Git Clone

```bash
# 1. Food4healthKG 원본 (논문 데이터 + KG triple)
git clone https://github.com/ccszbd/Food4healthKG.git

# 2. MiKG (bacteria–neurotransmitter–mental disorder 관계)
git clone https://github.com/tingcosmos/MiKG-JAIMS.git
```

### 수동 다운로드

| 파일 | 출처 | 둘 위치 |
|------|------|---------|
| FDC Full Download (CSV) | https://fdc.nal.usda.gov/download-datasets.html → "Full Download of All Data Types" | `fdc_raw/` (`food.csv`, `food_nutrient.csv`, `nutrient.csv`) |
| ProMENDA Metabolite | Pu et al. 2024, https://www.nature.com/articles/s41398-024-02948-2 → Supplementary Data 2 | `41398_2024_2948_MOESM3_ESM.xlsx` |
| MENDA 원본 | Pu et al. 2020, Briefings in Bioinformatics 보충자료 (`Metabolite` 시트 5,675 entries) | `menda.xlsx` |

> **FDC CSV 를 Excel 로 열지 말 것.** 1,048,576행에서 경고 없이 잘린다.
> 논문 repo 의 `food_nutrient.csv` 가 바로 그렇게 잘려 있었다 (REPRODUCTION §11).
>
> ProMENDA 웹사이트(menda.cqmu.edu.cn)는 접속이 안 될 수 있다. Nature 보충자료로 받는다.

### 디렉토리 구조

```
food_recom_w_paper/
├── Food4healthKG/                  ← 논문 repo (git clone)
│   ├── analyse/final.py            ← 원 논문 추천 알고리즘 (참고용)
│   ├── analyse/heatmap.xlsx        ← Fig. 4(c) 원본 = 논문의 F (85 compound 목록 출처)
│   └── analyse/p5_foodname.txt     ← 135개 음식, 줄 순서 = 논문 순위
├── MiKG-JAIMS/                     ← MiKG (git clone)
├── foodkg_triply/                  ← 논문 KG triple 11개 (repo 의 zip 해제)
├── fdc_raw/                        ← [수동 다운] FDC 원본
├── food_nutrient.csv               ← [setup 생성] FDC 3개 조인 + KEGG 매핑 (2,719만 행)
├── menda.xlsx                      ← [수동 다운] MENDA 원본
├── 41398_2024_2948_MOESM3_ESM.xlsx ← [수동 다운] ProMENDA
│
├── run_pipeline.py                 ← 전체 실행 + 로그
├── build_paper85.py                ← step0
├── reconstruct.py                  ← step1
├── knowledge_query.py              ← step2
├── map_promenda.py                 ← step3
├── run_recommendation.py           ← step4
├── kegg_alias.py                   ← 논문 ID ↔ FDC/MENDA ID 대응표 (step1~3 공유)
│
├── setup/                          ← 1회성. FDC 원본 교체 시에만
├── eval/                           ← 논문 §5.1 평가 재현
├── tools/                          ← 진단·검증 (파이프라인 아님)
├── analyse/                        ← [생성] 산출물
│   ├── paper85_compounds.csv       ← 논문 85 compound (KEGG, 이름, 6개 그룹)
│   ├── foodname.csv / food.csv     ← food × 85 compound (g 환산)
│   ├── food_rawunit.csv            ← 환산 전 원단위 사본 (진단용)
│   ├── weight.csv                  ← 8 × 85 = 4소스(infer/faecal/type1/type2) × (pos, neg)
│   ├── knowledge_query_results.csv ← compound 별 E 와 근거
│   └── acs04.csv, *.png            ← 추천 확률, 시각화
└── logs/                           ← [생성] 실행 로그
```

---

## 3. 환경 설정

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy scipy scikit-learn matplotlib openpyxl
pip install pyoxigraph        # eval/paper_sparql.py 에만 필요
```

---

## 4. 실행 방법

### 준비 (1회)

```bash
cd Food4healthKG && unzip foodkg_triply.zip -d ../foodkg_triply && cd ..
cp Food4healthKG/analyse/p5_foodname.txt analyse/  # 논문 순위. 라이선스가 없어 이 repo 에는 넣지 않았다
python3 setup/rebuild_food_nutrient.py fdc_raw    # → food_nutrient.csv
```

`analyse/` 에 들어 있는 csv·png 는 2026-09-29 기본 설정으로 파이프라인을 돌린 산출물이다.
다시 돌리면 덮어쓴다.

### 방법 A: 한 번에 실행 (권장)

```bash
python3 run_pipeline.py          # step0~4, 약 9분. 로그는 logs/
python3 tools/scorecard.py       # 재현 집계
```

`run_pipeline.py` 는 step0~4 를 순서대로 실행하고, 각 step 의 출력을
`logs/YYYYMMDD_HHMMSS_<step>.txt` 에, 요약을 `..._summary.txt` 에 저장한다.
중간에 실패하면 그 step 에서 멈춘다.

### 방법 B: 개별 실행

```bash
python3 build_paper85.py         # step0: 논문 85 compound 목록
python3 reconstruct.py           # step1: food / foodname / weight 역설계
python3 knowledge_query.py       # step2: E 결정 (MENDA/MiKG/Q2/ontology)
python3 map_promenda.py          # step3: ProMENDA 보강 + 4소스 구성
python3 run_recommendation.py    # step4: 추천 + 시각화
```

### 평가·검증

```bash
python3 eval/run_paper_eval.py   # 논문 §5.1 평가 (전문가 20문항을 KG 에 질의, Table 5)
python3 eval/paper_sparql.py     # 보충자료 SPARQL 을 공개 KG 에 실행 (Table 2~5, 약 3분)
python3 tools/paper.py all       # 논문 기준 검증·개선 (REPRODUCTION §16)
python3 tools/ab.py <항목>        # 설정 A/B 비교 (끝나면 기본값 복원)
```

---

## 5. 각 Step 상세

### Step 0: `build_paper85.py`
`heatmap.xlsx`(Fig. 4(c) 원본)의 85개 열에서 논문 compound 목록을 뽑는다.
KEGG ID, 이름, 6개 생물학적 그룹(Lipids 39, Amino acid 18, Vitamins 11,
Carbohydrates 7, Trace Elements 5, Macronutrient 5)이 들어 있다.
공식 `final.py` 의 `np.zeros((85, n))` 과 형상이 맞는다. → `analyse/paper85_compounds.csv`

### Step 1: `reconstruct.py`
`food_nutrient.csv` 와 `p5_foodname.txt` 로 누락 입력을 역설계한다.
- **라벨 병합 (§3.2):** FDC 는 같은 음식을 영양소군별로 따로 등재한다
  (`Fatty Acids, American cheese ...`, `Niacin, American cheese ...`).
  논문이 말한 대로 쉼표 앞 접두사와 샘플코드를 떼고 같은 라벨을 합친다.
  측정 밀도 중앙값이 15에서 28로 오른다.
- **g 환산 (§3.1):** MG 10^-3, UG 10^-6, IU 10^-6. 피벗 **전에** 행 단위로 환산한다
  (Retinol·Vitamin E 는 IU 행과 µg 행이 섞여 있다). `UNIT_MODE=raw` 는 이전 동작.
- **카테고리:** FDC 원본의 `food_category_id` 를 쓴다.

출력: `foodname.csv` (135, 88), `food.csv` (135, 86), `food_rawunit.csv`

### Step 2: `knowledge_query.py`
논문 Query Type 2·3 과 §3.3 knowledge inference 로 compound 별 방향 E 를 정한다.

| 우선순위 | 근거 | 방법 |
|---|---|---|
| 1 | MENDA KG | `MENDA_Depression.jsonld` 의 hasPositive/NegativeAssociation. 양쪽에 다 있으면(`both`) MENDA 원본 study 수로 가른다 |
| 2 | Q2 bacteria path | compound → bacteria(`KEGG_Compound_Bacteria`) → depression(`Disease_Bacteria`) |
| 3 | MiKG | depression → neurotransmitter → precursor 체인 |
| 4 | ontology | subClassOf 체인 (sugar 그룹, vitamin family 등) |
| 5 | group prior | 논문 §4.2.3 의 Carbohydrates/Vitamins 그룹 |

극성은 논문 §4.2.1 을 따른다(MENDA Up = +1, `MENDA_POS_MEANS_RELIEF=1`).
weight.csv 의 infer 행만 쓴다. 근거별 크기는 `kegg_alias.INFER_SCALE`.

### Step 3: `map_promenda.py`
ProMENDA 로 E 를 보강하고 weight.csv 의 4소스를 만든다.
- **극성:** 논문 §4.2.1 규약. Type1(우울증 vs 대조군)의 up 을 +1, Type2~5(치료·반응 비교)의
  up 을 −1 로 본다 (`PROMENDA_POLARITY=paper`, 기본). `legacy` 는 모든 Type 에서 up = −1.
- **infer 행:** step2 가 비워 둔 자리와 근거가 약한 자리만 ProMENDA 전체 다수결로 채운다
  (마진 0.10, study ≥ 2).
- **faecal / type1 / type2 행:** ProMENDA 의 Faece / Type1 / Type2 부분집합에서 각각
  독립 집계한다. 공식 `final.py:54-57` 의 소스 이름이 ProMENDA 컬럼에 그대로 있다.

### Step 4: `run_recommendation.py`
논문 Algorithm 1 을 공식 `final.py` 에서 이식했다.
1. F 행별 min-max 정규화
2. `u = Xn · E`, E = pos − neg (논문 §4.2.1. `E_MODE=official` 은 final.py 의 단일 행)
3. adjusted cosine similarity S (Eq. 1, final.py 구현)
4. `p = u · S / colsum(S)` (Eq. 2. 열 합 나누기는 final.py 에만 있다)
5. Top-K = 30 + PCA / t-SNE 시각화

논문 수식(§4.2)과 final.py 가 네 군데서 다르다. 16조합 비교에서 final.py 쪽이 논문 결과에
더 가까워 그쪽을 따른다 (REPRODUCTION §3).

---

## 6. 최종 추천 결과

### Top 10 추천 (전체 30개는 `logs/*_step4_recommendation.txt`)

| 순위 | 음식 | 카테고리 | 논문 순위 |
|------|------|----------|-----------|
| 1–3 | Flour (bread / all-purpose / corn), enriched | 곡물 | 46 / 43 / 25 — ⚠️ 점수 발산 (아래) |
| 4 | Ketchup | 소스 | |
| 5 | Melons, cantaloupe | 과일 | |
| 6 | Apples, red delicious | 과일 | |
| 7 | Mission Figs, Dried | 과일 | |
| 8 | Beans, snap, canned | 채소 | |
| 9 | Onions, white | 채소 | |
| 10 | Bananas, overripe | 과일 | |

### Bottom 10 비추천

| 순위 | 음식 | 카테고리 |
|------|------|----------|
| 125 | Beef, Porterhouse Steak | 소고기 |
| 126–131 | Cheddar / Swiss cheese (6종) | 유제품 |
| 132 | Tuna, canned in water | 어류 |
| 133 | Butter, unsalted | 유제품 |
| 134 | Coconut oil | 유지 |

### 카테고리 분포

| 카테고리 | Top 30 | Bottom 30 | 논문 (Fig. 5) |
|----------|--------|-----------|---------------|
| 채소 | 8 | 0 | 추천 ✅ |
| 과일 | 4 | 0 | 추천 ✅ |
| 소스 | 5 | 0 | 중간 |
| 유제품·계란 | 5 | 12 | 중간 |
| 소고기 | 0 | 6 | 비추천 ✅ |
| 소시지 | 0 | 4 | 비추천 ✅ |
| 가금류 | 0 | 4 | — |
| 유지 | 0 | 3 | 중간 |
| 어류 | 0 | 1 | 중간 (§4.2.3 본문은 추천) |
| 설탕 | 2 | 0 | Fig. 5 에 없음. 논문 순위 31·32위 |
| 빵류 | 2 | 0 | Fig. 5 는 비추천, §4.2.3 본문은 언급 없음. 논문 순위 33·35·37위 |
| 곡물 | 3 | 0 | — (점수 발산 3종) |

### 논문 순위(p5)와의 대조

| 지표 | 값 | 우연 기대값 |
|------|-----|------------|
| Top30 겹침 | 18 / 30 | 6.7 |
| Bottom30 겹침 | 15 / 30 | 6.7 |
| Spearman | +0.786 | 0 |
| NDCG@30 | 0.875 | — |
| 우리 Top30 ∩ 논문 Bottom30 | 0 | — |
| 우리 Bottom30 ∩ 논문 Top30 | 0 | — |

> **점수 발산 3종.** 밀가루 3종은 측정 성분이 3개뿐이라 유사도 열 합 `colsum(S)` 가
> 0.03 수준이다(전체 중앙값 22). 공식 `final.py` 의 `p = u·S / colsum(S)` 에서 분모가 0 에
> 가까워 점수가 103, 99, 50 으로 튄다. 공식 코드의 성질이라 재현에서는 그대로 둔다.
>
> **카테고리 분포로 판정하지 말 것.** "상위 30 에 과일이 있는가" 같은 지표는 과일이
> 1개만 있어도 만점이라 실패를 가린다. p5 순위 겹침과 논문 주장 검정으로 본다.

---

### 논문의 쿼리·평가를 공개 KG 로 재현 (`eval/`)

`foodkg_triply/` 11개 파일을 SPARQL 저장소에 올리고 보충자료의 쿼리를 원문대로 실행했다
(`eval/paper_sparql.py`, 약 3분, `pyoxigraph` 필요). 공개 KG 에는 SNOMED CT 가 없어,
질병 이름과 "mental disorder" 분류는 논문이 출처로 든 MiKG 에서 가져왔다.

**KG 규모.** 공개 KG 는 431만 트리플이다. 논문 Table 1 의 9개 소스 중 7개가 트리플 수까지
일치한다. SNOMED CT(429만)와 추론 트리플(474만)은 없고, MENDA 는 2,633 / 5,675 다.

**쿼리 → 논문 표**

| 논문 | 재현 | 비고 |
|---|---|---|
| Query 2 → Table 3 | **8 / 8** | 5행은 쿼리 원문, 3행은 세균 조건만 neg 로 |
| Query 3 → Table 4 | **5 / 5** | SNOMED 이름을 MiKG 에서. 음식–성분을 제대로 묶으면 4 / 5 |
| Query 1 → Table 2 | 6 / 8 | **값이 틀렸다.** 올바른 합의 30~70배 (아래) |

**§5.1 방법 1 — 전문가 20문항** (`eval/run_paper_eval.py`). 전문가 3인의 수작업 대조는
재현할 수 없어, KG 에 20문항을 직접 질의했다. 재현 = 논문이 보고한 답이 KG 에서 나오는가,
타당 = 그 답이 질문에 맞는가.

| | O | △ | X | 판정 제외 |
|---|---|---|---|---|
| 재현 | 18 | 1 | 1 | — |
| 타당 | 13 | 3 | 3 | 1 |

재현되고 타당한 문항은 13 / 20 이다. 재현되지만 틀린 답이 3건(#5, #9, #10) 있다.

**§5.1 방법 2 — 문헌 검증 15건 (Table 5).** PubMed 재검색은 하지 않고, 논문이 든 근거가
KG 에서 성립하는지를 엄격하게 봤다.

| | 엄격 기준 | 기준 |
|---|---|---|
| Complication 8건 | **7 / 8** | 그 세균이 두 질병 모두에 연결되는가 |
| Diet recommendation 7건 | 2 / 7 | 그 음식에 그 성분 기록이 있고, 성분→세균→질병 경로가 있는가 |

Diet 는 음식과 성분을 묶지 않으면 5 / 7 이다. 마늘·커피·과자류의 Threonine 3건은 KG 에서
그 음식에 Threonine 기록이 없다.

**찾은 쿼리 결함 (보충자료 원문 기준)**

1. Query 1: `?milkunit` 이 `?milk` 에 묶여 있지 않다. Table 2 의 "달걀 프라이 + 우유 =
   B6 6.591" 은 달걀 0.151 + Kellogg's Special K 6.44 다. 실제 우유는 0.05~0.08.
2. Query 3: `?food pq:hasNutrients ?nutrient` 의 `?nutrient` 가 `?nutrition` 과 다른 변수라
   음식이 성분과 묶이지 않는다. Table 4 의 "Hot dogs, beef — L-Threonine" 은 KG 에서 그
   음식에 Threonine 기록이 없다.
3. 음식을 라벨 부분 문자열로 찾는다. "milk" 가 "Ricotta cheese, whole milk" 에 걸린다.

우울증–세균의 방향 있는 연관(pos 14종, neg 23종)은 `MENDA_Depression.jsonld` 에 있다.
다만 Table 3 의 compound (+)/(−) 표기는 쿼리에서 나오지 않아 `E` 의 방향은 정해지지 않는다.

---

## 7. 논문과의 차이 및 원인

### 일치
- 성분 행렬 F: 논문 heatmap 과 행 코사인 0.981 (g 환산 후)
- PCA 5성분 (§4.2.1), gold 8/9, Table 5 문헌 검증 11/15
- 추천 순위: Spearman +0.786, Top30 18/30, Bottom30 15/30. 양쪽 끝이 뒤바뀐 음식 0개
- 채소·과일 추천, 소고기·소시지 비추천 (Fig. 5)
- 논문 주장: 추천 카테고리(C1a), 피라미드 순서(C2), 성분 공간 분리(C5)

### 불일치

| 차이점 | 원인 |
|--------|------|
| 밀가루 3종이 1~3위 | 공식 점수식의 분모 발산 (§6) |
| 유제품이 비추천에 12개 | Fig. 5 는 중간층. 지질(치즈·버터)의 − 가 강하게 작용 |
| 논문 주장 C1b·C3·C6 실패 | C1b 는 설탕·빵이 비추천이 아니어서인데, 논문 순위도 이들을 31~37위에 둔다(아래). C3·C6 은 논문 순위 자신도 실패 |
| gold 1개 불일치 | Pantothenic acid(Table 4, 복숭아) 가 `−`. ProMENDA Type1 이 `−` 를 지지 |
| E 방향 16종 미확보 | 미네랄 10종은 대사체 DB 가 원소를 측정하지 않는다. 논문이 어디서 얻었는지 기술이 없다 |

### 피라미드 상단: 본문은 고기류, 그림은 빵류
§4.2.3 본문은 상단 층을 "barbecue products, beef products, sausages, and luncheon meats" 로,
Fig. 5 그림은 "Baked Products / Beef / Sausages and Luncheon Meats / Pork" 로 적는다.
**논문 순위(p5)는 본문 쪽이다.** 빵·과자 3종이 33·35·37위, 설탕이 31·32위로 비추천이
아니라 상위권 끝에 있다. 평가 기준은 Fig. 5 그대로 두고, 본문 기준을 민감도 검사로 함께 본다
(`tools/paper.py claims`).

| | 논문 순위 | 우리 |
|---|---|---|
| C1b 비추천 = 소시지·빵·과자 (§4.2.3 앞 문장) | PASS | fail |
| C1b′ 비추천 = 본문 피라미드 상단 (소고기·소시지) | PASS | **PASS** |
| C2 피라미드 순서, Fig. 5 그림 기준 | ρ +0.75 | ρ +0.52 |
| C2′ 피라미드 순서, 본문 기준 | **ρ +0.89** | **ρ +0.65** |

논문 순위 자신이 그림(+0.75)보다 본문(+0.89)에 더 잘 맞는다.

### 근본 원인
**논문의 E 는 공개 자료에서 그대로 나오지 않는다.** MENDA 원본에 16개 집계 규칙을 적용해도
논문이 부호를 명시한 12종 중 최고 8종만 맞는다 (REPRODUCTION §14). `final.py` 가 읽는
`weight.csv` 가 배포되지 않았다.

### 논문 자체의 결함 (재현 중 확인)
- §4.2 수식(Eq. 1 분모, Eq. 2 첨자)이 조판 오류. 그대로 구현하면 16조합 중 꼴찌
- 단위 환산과 ProMENDA 극성 처리를 적지 않음
- Table 3/4 의 Glutamic acid·L-Threonine·Choline 이 Fig. 4(c) 85종 목록에 없음
- §4.2.3 본문과 Fig. 5 가 피라미드에서 두 군데 모순: 어류 위치, 상단 층(본문 "barbecue products", 그림 "Baked Products")
- §4.2.3 의 성분 차이 서술이 논문 자신의 heatmap 과 어긋남 (미량원소·다량영양소)
- `final.py` 입력 4개와 `metabolite_bacteria.xlsx` 누락, `food_nutrient.csv` 절단
- **Supplementary Query 1 의 결함으로 Table 2 값이 틀렸다.** `?milkunit` 이 `?milk` 에 묶여 있지
  않아 두 번째 음식의 성분량이 다른 음식 값으로 들어간다. Table 2 의 "달걀 프라이 + 우유 =
  비타민 B6 6.591" 은 달걀 0.151 + Kellogg's Special K 시리얼 6.44 다. 실제 우유는 0.061
- 음식을 라벨 부분 문자열로 찾아, "milk" 가 "Ricotta cheese, whole milk" 에 걸린다 (Table 1 #5)
- 공개 KG 에 SNOMED CT 계층(논문 Table 1 의 429만 트리플)이 없다. 이름과 mental disorder
  분류는 MiKG 로 복원할 수 있다
- Query 3 도 음식과 성분이 묶여 있지 않다 (Table 4 의 핫도그 행, Table 5 의 Threonine 3건)

---

## 8. 데이터 소스 요약

| Source | 용도 | 크기 | 비고 |
|--------|------|------|------|
| FDC Full Download | 음식–영양소 | `food_nutrient.csv` 2,719만 행 | 2026-04 판. 논문은 2021~22 판 |
| `heatmap.xlsx` | 논문 F, 85 compound 목록 | 135 × 85 | 논문 repo |
| `p5_foodname.txt` | 논문 순위 | 135 | 논문 repo. heatmap 행 순서와 Spearman 0.896 |
| `MENDA_Depression.jsonld` | compound–depression ± | pos 378 / neg 399 / 양쪽 267 | 논문 KG |
| MENDA 원본 | compound–depression study 단위 | 5,675 entries / 464 studies | Briefings in Bioinformatics |
| ProMENDA | compound–depression 보강, 4소스 | 22,519 entries | Nature 보충자료 |
| `KEGG_Compound_Bacteria.jsonld` | compound–bacteria 대사 | 201 bacteria | 논문 KG |
| `Disease_Bacteria.jsonld` | bacteria–disease | 741 bacteria | 논문 KG |
| `Bacteria_Ontology.trig` | bacteria ID–이름 | 322K | 논문 KG |
| MiKG TTL | bacteria–neurotransmitter–disease | 48 bacteria, 6 NTM | GitHub |
| `KEGG_Compound.jsonld` | compound ontology | — | 논문 KG |
| `MESH_Disease.jsonld` | disease 분류 | 235K labels | 논문 KG |

---

## 9. 코드 파일 목록

### 파이프라인

| 파일 | 역할 | 입력 | 출력 |
|------|------|------|------|
| `run_pipeline.py` | step0~4 실행 + 로그 | 아래 스크립트 | `logs/` |
| `build_paper85.py` | step0: 논문 85 compound | `heatmap.xlsx` | `paper85_compounds.csv` |
| `reconstruct.py` | step1: 입력 역설계, 라벨 병합, g 환산 | `food_nutrient.csv`, `p5_foodname.txt`, `fdc_raw/food.csv` | `foodname.csv`, `food.csv`, `food_rawunit.csv`, `weight.csv`(초기) |
| `knowledge_query.py` | step2: E 결정 | KG triple, MiKG, `menda.xlsx` | `weight.csv` infer 행, `knowledge_query_results.csv` |
| `map_promenda.py` | step3: ProMENDA 보강 + 4소스 | ProMENDA, `knowledge_query_results.csv` | `weight.csv` |
| `run_recommendation.py` | step4: 추천 + 시각화 | `food.csv`, `weight.csv`, `foodname.csv` | `acs04.csv`, `*.png` |
| `kegg_alias.py` | ID 대응표, `INFER_SCALE` | — | — |

### setup/ (1회성)

| 파일 | 역할 |
|------|------|
| `rebuild_food_nutrient.py` | `fdc_raw/` → `food_nutrient.csv` 조립 |
| `nutrient_kegg_map.csv` | FDC nutrient_id → KEGG (212행, 180 매핑) |
| `add_fatty_acid_kegg.py` | 지방산 KEGG 매핑 생성 (repo 배포본에 없던 77종) |

### eval/ (논문 §5.1)

| 파일 | 역할 |
|------|------|
| `run_paper_eval.py` | §5.1 방법 1(20문항을 KG 에 질의)·방법 2(근거 존재) |
| `paper_sparql.py` | 공개 KG 에 보충자료 SPARQL 을 실행해 Table 2~5 대조 (`pyoxigraph`) |
| `paper_table1.py` | 전문가 20문항 (Supplementary Table 1) 전사 |
| `paper_table5.py` | 문헌 검증 15건 (Table 5) |
| `gold.py` | 논문이 부호를 명시한 compound 9종 — 파라미터를 고르는 독립 기준 |

### tools/ (진단·검증, 모두 `core.py` 공유)

| 파일 | 하위 명령 |
|------|-----------|
| `scorecard.py` | 재현 집계 — 먼저 볼 것 |
| `paper.py` | `units` 단위 역산 · `claims` 논문 주장 검정 · `invert` E 역추정 · `improve` 개선판 |
| `ab.py` | 설정 A/B: `rules` `fallback` `menda_both` `menda_tiebreak` `study_type` `merge` `margin` `units` `polarity` |
| `sweep.py` | 수식·부호 스윕: `formula` `sign` `sources` `menda` `promenda` `ceiling` |
| `diag.py` | 진단: `kg` `signs` `lipids` `unassigned` `data` `food` `menda_jsonld` `menda_orig` `menda_rule` `promenda_types` `supplements` |
| `repo_only.py` | 논문 repo 배포본만으로 돌린 기준선 |
| `unused.py` | 미사용 파일 분류 |

### 주요 설정 (환경변수)

| 위치 | 기본값 | 의미 |
|------|--------|------|
| `reconstruct.py` `UNIT_MODE` | `grams` | g 환산. `raw` 는 이전 동작 |
| `reconstruct.py` `MERGE_LABELS` | `1` | 라벨 병합 (§3.2) |
| `knowledge_query.py` `MENDA_POS_MEANS_RELIEF` | `1` | 논문 §4.2.1 극성 |
| `knowledge_query.py` `MENDA_BOTH_TIEBREAK` | `orig` | MENDA `both` 를 원본 study 수로 가름 |
| `knowledge_query.py` `GROUP_PRIOR_MODE` | `carbvit` | §4.2.3 group prior |
| `knowledge_query.py` `USE_LITERATURE` | `0` | 수동 문헌값 21개 (출처 불명) |
| `map_promenda.py` `PROMENDA_MARGIN` | `0.10` | gold 로 튜닝 (`tools/ab.py margin`) |
| `map_promenda.py` `FIX_STUDY_TYPE` | `0` | ProMENDA Type2/4 방향 보정 |
| `map_promenda.py` `PROMENDA_POLARITY` | `paper` | ProMENDA 극성. 논문 §4.2.1 규약. `legacy` 는 이전 동작 (PROBLEMS §7) |
| `run_recommendation.py` `E_MODE` | `paper` | `E = pos − neg`. `official` 은 final.py 단일 행 |

---

## 10. 프로젝트 확장

### 수행한 것 (`tools/paper.py`, REPRODUCTION §16)

재현 결과와 섞지 않는다. 판정 기준은 논문에서 가져와 실행 전에 고정했다.

**논문 주장 검정 (`claims`)** — §4.2.3·Fig. 4·5 의 서술을 명제 6개로 옮겼다.

| | 논문 순위 | 우리 | 식물/동물 1비트 |
|---|---|---|---|
| 통과 | 4 / 6 | 3 / 6 | 4 / 6 |

식물/동물만 보는 1비트 규칙이 논문 순위와 같은 수의 주장을 통과한다.
논문 순위 자체가 대부분 식물/동물 구분으로 설명된다는 뜻이다.

**E 역추정 (`invert`)** — 음식 절반으로 E 를 학습하고 나머지 절반에서 잰 Spearman.

| 데이터 | held-out Spearman | 1비트 기준선 |
|---|---|---|
| 논문 F (heatmap) | 0.91 | — |
| 우리 F | 0.75 | 0.69 |

학습 없이 공개 소스로 만든 현재 E(+0.786)가 논문 순위로 학습한 E(0.75)보다 높다.

**Ablation (`improve`)**

| 변형 | Spearman | Top30 | Bot30 | gold | 주장 |
|---|---|---|---|---|---|
| **R 재현 기준** | **+0.786** | 18 | **15** | 8/9 | 3/6 |
| V1 E 에 MENDA study 수로 신뢰도 가중 | +0.651 | 16 | 12 | 8/9 | 3/6 |
| V2 미생물 경로 있는 compound 만 (Food → Nutrient → Microbiota → Disease) | +0.683 | 12 | 15 | 2/9 | 3/6 |
| V3 similarity 단계 제거 | +0.761 | **19** | 12 | 8/9 | **4/6** |

- 극성 규약을 고친 뒤로는 어떤 변형도 재현 기준을 넘지 못한다. V1 은 극성을 고치기 전
  (+0.108 → +0.466) 에만 효과가 있었다. 신뢰도 가중이 틀린 부호의 영향을 줄여 준 것으로 보인다.
- V2: 공개 KG 에서 미생물 경로가 있는 compound 는 85종 중 8종뿐이다. 그 8종만으로도
  Spearman +0.683 이지만 gold 가 2/9 로 무너진다.
- V3: similarity 단계를 빼도 순위가 거의 같다 (+0.761). Algorithm 1 의 S 단계 기여가 작다.

**외부 기준 (보조)** — Antidepressant Food Score (LaChance & Ramsey 2018) 를 85 compound 로
근사했다. 논문 순위를 포함해 어떤 순위도 AFS 와 상관이 없다 (|ρ| ≤ 0.11).

### 남은 방향
- **KG embedding** (TransE, RotatE) → food–depression link prediction
- **GNN** (R-GCN, CompGCN) → food node embedding
- **SMILES trial** (Jacka et al. 2017) ModiMedDiet 권장 식품을 ground truth 로 평가
- Table 5 방식 문헌 검증 확장
- 저자에게 `weight.csv` 요청 — E 를 확정할 수 있는 유일한 경로

---

## 11. 참고문헌

- Fu et al. (2023). Food4healthKG. *Artificial Intelligence in Medicine*, 145, 102677.
- Liu et al. (2021). MiKG. *Health Information Science and Systems*, 9(1), 1–9.
- Pu et al. (2024). ProMENDA. *Translational Psychiatry*, 14, 229.
- Pu et al. (2020). MENDA. *Briefings in Bioinformatics*, 21(4), 1455–1464.
- Sarwar et al. (2001). Item-based collaborative filtering recommendation algorithms. *WWW '01*, 285–295.
- LaChance & Ramsey (2018). Antidepressant foods: An evidence-based nutrient profiling system for depression. *World Journal of Psychiatry*, 8(3), 97–104.
- Jacka et al. (2017). SMILES trial. *BMC Medicine*, 15(1), 23.
- Marx et al. (2021). Diet and depression. *Molecular Psychiatry*, 26(1), 134–150.
- Parker & Brotchie (2011). Tryptophan and tyrosine. *Acta Psychiatrica Scandinavica*, 124(6), 417–426.

---

## 변경 이력

- **2026-09-29** — 성분 g 환산(Top30 5 → 15), weight.csv 4소스 독립 집계, ProMENDA 극성
  규약 통일(Spearman +0.108 → +0.786, Bot30 3 → 15), 논문 기준 검증·개선(`tools/paper.py`),
  도구 통합(`tools/` 18 → 8개). 상세와 이전/이후 파일 대응은 REPRODUCTION §16·§9.
- 그 이전 — 라벨 병합, FDC 원본 재조립, MENDA 원본 확보, 평가 지표 교체 등.
  REPRODUCTION 각 절에 날짜와 함께 기록.
