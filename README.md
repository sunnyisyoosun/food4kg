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

### 최종 재현 상태 (2026-09-29, `python3 tools/scorecard.py`)

| 층위 | 우리 결과 | 논문 | 판정 |
|------|-----------|------|------|
| Foods | 135 / 135 | 135 | ✅ |
| Compounds | 85 / 85 | 85 | ✅ |
| 성분 행렬 F vs 논문 heatmap | 행 코사인 0.981 | — | ✅ |
| 측정 밀도 (compound 수 중앙값) | 28 | 33 | ⚠️ FDC 판 차이 |
| PCA 80% 도달 성분 수 (§4.2.1) | 5 | 5 | ✅ |
| E 방향 확보 | 67 / 85 | 85 | ⚠️ |
| 논문이 부호를 명시한 compound (gold) | 8 / 9 | 9 | ✅ |
| **추천 순위 Top30 겹침** (우연 6.7) | **15 / 30** | 30 | ⚠️ |
| **추천 순위 Bottom30 겹침** (우연 6.7) | **3 / 30** | 30 | ❌ |
| 순위 Spearman | +0.108 | 1.0 | ⚠️ |
| 논문 주장 6개 (§4.2.3, Fig. 4·5) | 1 / 6 | 논문 순위 자신 4 / 6 | ❌ |
| §5.1 문헌 검증 (Table 5) | 11 / 15 | 11 / 15 | ✅ |
| §5.1 전문가 20문항 | — | — | 설계상 재현 불가 |

**부분 재현이다.** 데이터와 알고리즘 구조는 재현됐다. 논문 자신의 F 로는 선형 E 모델이
논문 순위를 held-out Spearman 0.91 로 설명한다. 남은 격차는 E 하나다. 논문 순위가
함의하는 E 와 공개 소스로 만든 E 의 부호 일치가 우연 수준(30/55)이다.

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
```

---

## 4. 실행 방법

### 준비 (1회)

```bash
cd Food4healthKG && unzip foodkg_triply.zip -d ../foodkg_triply && cd ..
python3 setup/rebuild_food_nutrient.py fdc_raw    # → food_nutrient.csv
```

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
python3 eval/run_paper_eval.py   # 논문 §5.1 평가 (Table 5 문헌 검증, 전문가 문항 전사)
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

| 순위 | 음식 | 카테고리 |
|------|------|----------|
| 1 | Pollock, raw | 어류 |
| 2 | Ketchup | 소스 |
| 3 | Greek yogurt, non-fat | 유제품 |
| 4 | Apples, red delicious | 과일 |
| 5 | Mission Figs, Dried | 과일 |
| 6 | Beans, snap, canned | 채소 |
| 7 | Melons, cantaloupe | 과일 |
| 8 | Onions, white | 채소 |
| 9 | Bananas, overripe | 과일 |
| 10 | Beef, top round roast | 소고기 |

### Bottom 10 비추천

| 순위 | 음식 | 카테고리 |
|------|------|----------|
| 125 | Peaches | 과일 |
| 126 | Beef, porterhouse steak | 소고기 |
| 127–131 | Flour (pastry / rice ×3 / whole wheat) | 곡물 |
| 132–134 | Flour (corn / all-purpose / bread) | 곡물 — 점수가 −20 ~ −43 으로 튄다 (원인 미조사) |

### 카테고리 분포

| 카테고리 | Top 30 | Bottom 30 | 논문 (Fig. 5) |
|----------|--------|-----------|---------------|
| 채소 | 5 | 3 | 추천 |
| 과일 | 4 | **8** | 추천 ❌ |
| 소스 | 5 | 0 | 중간 |
| 유제품·계란 | 4 | 5 | 중간 |
| 가금류 | 5 | 2 | — |
| 어류 | 1 | 1 | 중간 (§4.2.3 본문은 추천) |
| 소고기 | 2 | 1 | 비추천 ❌ |
| 설탕 | 2 | 0 | 비추천 ❌ |
| 곡물 | 0 | 8 | — |

### 논문 순위(p5)와의 대조

| 지표 | 값 | 우연 기대값 |
|------|-----|------------|
| Top30 겹침 | 15 / 30 | 6.7 |
| Bottom30 겹침 | 3 / 30 | 6.7 |
| Spearman | +0.108 | 0 |
| NDCG@30 | 0.745 | — |

> **카테고리 분포로 판정하지 말 것.** "상위 30 에 과일이 있는가" 같은 지표는 과일이
> 1개만 있어도 만점이라 실패를 가린다. p5 순위 겹침과 논문 주장 검정으로 본다.

---

## 7. 논문과의 차이 및 원인

### 일치
- 성분 행렬 F: 논문 heatmap 과 행 코사인 0.981 (g 환산 후)
- PCA 5성분 (§4.2.1), gold 8/9, Table 5 문헌 검증 11/15
- 추천 쪽 순위: Top30 15/30 (우연의 2배 이상), 양파·사과·멜론·바나나 상위

### 불일치

| 차이점 | 원인 |
|--------|------|
| 비추천 쪽 순위가 우연 수준 (Bot30 3/30) | E 가 논문과 다르다. 논문 순위가 함의하는 E 와 부호 일치 30/55 (REPRODUCTION §16.3) |
| 과일이 비추천에 8개 | 위와 같음. 과일 주요 성분의 방향이 논문과 다르다 |
| 소고기·설탕이 추천 상위 | 위와 같음 |
| 논문 주장 1/6 | 위와 같음. 논문 순위 자신은 4/6 이다 |
| E 방향 18종 미확보 | 미네랄 10종은 대사체 DB 가 원소를 측정하지 않는다. 논문이 어디서 얻었는지 기술이 없다 |

### 근본 원인
**논문의 E 는 공개 자료에서 나오지 않는다.** MENDA 원본에 16개 집계 규칙을 적용해도
논문이 부호를 명시한 12종 중 최고 8종만 맞는다 (REPRODUCTION §14). 논문에 기술되지 않은
별도 큐레이션으로 보이며, `final.py` 가 읽는 `weight.csv` 가 배포되지 않았다.

### 논문 자체의 결함 (재현 중 확인)
- §4.2 수식(Eq. 1 분모, Eq. 2 첨자)이 조판 오류. 그대로 구현하면 16조합 중 꼴찌
- 단위 환산을 적지 않음
- Table 3/4 의 Glutamic acid·L-Threonine·Choline 이 Fig. 4(c) 85종 목록에 없음
- §4.2.3 본문과 Fig. 5 가 어류 위치에서 모순
- §4.2.3 의 성분 차이 서술이 논문 자신의 heatmap 과 어긋남 (미량원소·다량영양소)
- `final.py` 입력 4개와 `metabolite_bacteria.xlsx` 누락, `food_nutrient.csv` 절단

### 결정 대기
ProMENDA 극성 규약이 step2(Up = +1)와 step3(up = −1)에서 반대다. 논문 규약을 연구 유형에
맞게 적용하면 type1·type2 소스가 gold 4/5 와 논문 순위를 동시에 지지한다 (PROBLEMS §7).

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
| `run_paper_eval.py` | 실행기 |
| `paper_table1.py` | 전문가 20문항 (Supplementary Table 1) 전사 |
| `paper_table5.py` | 문헌 검증 15건 (Table 5) |
| `gold.py` | 논문이 부호를 명시한 compound 9종 — 파라미터를 고르는 독립 기준 |

### tools/ (진단·검증, 모두 `core.py` 공유)

| 파일 | 하위 명령 |
|------|-----------|
| `scorecard.py` | 재현 집계 — 먼저 볼 것 |
| `paper.py` | `units` 단위 역산 · `claims` 논문 주장 검정 · `invert` E 역추정 · `improve` 개선판 |
| `ab.py` | 설정 A/B: `rules` `fallback` `menda_both` `menda_tiebreak` `study_type` `merge` `margin` `units` |
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
| `run_recommendation.py` `E_MODE` | `paper` | `E = pos − neg`. `official` 은 final.py 단일 행 |

---

## 10. 프로젝트 확장

### 수행한 것 (`tools/paper.py`, REPRODUCTION §16)

재현 결과와 섞지 않는다. 판정 기준은 논문에서 가져와 실행 전에 고정했다.

**논문 주장 검정 (`claims`)** — §4.2.3·Fig. 4·5 의 서술을 명제 6개로 옮겼다.

| | 논문 순위 | 우리 | 식물/동물 1비트 |
|---|---|---|---|
| 통과 | 4 / 6 | 1 / 6 | 4 / 6 |

식물/동물만 보는 1비트 규칙이 논문 순위와 같은 수의 주장을 통과한다.
논문 순위 자체가 대부분 식물/동물 구분으로 설명된다는 뜻이다.

**E 역추정 (`invert`)** — 음식 절반으로 E 를 학습하고 나머지 절반에서 잰 Spearman.

| 데이터 | held-out Spearman | 1비트 기준선 |
|---|---|---|
| 논문 F (heatmap) | 0.91 | — |
| 우리 F | 0.75 | 0.69 |

**Ablation (`improve`)**

| 변형 | Spearman | Top30 | Bot30 | gold |
|---|---|---|---|---|
| R 재현 기준 | +0.108 | 15 | 3 | 8/9 |
| **V1 E 에 MENDA study 수로 신뢰도 가중** | **+0.466** | 16 | **9** | 8/9 |
| V2 미생물 경로 있는 compound 만 (Food → Nutrient → Microbiota → Disease) | −0.553 | 0 | 3 | 3/9 |
| V3 similarity 단계 제거 | +0.067 | 13 | 6 | 8/9 |

V2 가 무너지는 이유: 공개 KG 에서 미생물 경로가 있는 compound 는 85종 중 8종뿐이다.
논문이 내세운 gut-brain 경로는 공개 데이터로는 추천 입력의 약 9% 만 뒷받침된다.

**외부 기준 (보조)** — Antidepressant Food Score (LaChance & Ramsey 2018) 를 85 compound 로
근사했다. 논문 순위를 포함해 어떤 순위도 AFS 와 상관이 없다 (|ρ| ≤ 0.13).

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

- **2026-09-29** — 성분 g 환산(Top30 5 → 15), weight.csv 4소스 독립 집계, 논문 기준 검증·개선
  (`tools/paper.py`), 도구 통합(`tools/` 18 → 8개). 상세와 이전/이후 파일 대응은
  REPRODUCTION §16 과 §9.
- 그 이전 — 라벨 병합, FDC 원본 재조립, MENDA 원본 확보, 평가 지표 교체 등.
  REPRODUCTION 각 절에 날짜와 함께 기록.
