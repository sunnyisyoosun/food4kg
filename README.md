# Food4healthKG 재현 및 확장 프로젝트

> 추천시스템 수업 프로젝트 — Food4healthKG (Fu et al., AIM 2023) 재현 + 확장

---

## 1. 프로젝트 개요

### 원 논문
- **제목:** Food4healthKG: Knowledge graphs for food recommendations based on gut microbiota and mental health
- **저널:** Artificial Intelligence in Medicine 145 (2023) 102677
- **핵심:** 음식–장내미생물–정신건강 Knowledge Graph 구축 → 우울증 대상 음식 추천
- **알고리즘:** Incidence matrix (compound↔disease) × Food-compound weight → Adjusted cosine similarity → Top-K 추천

### 재현 과정에서 발견한 문제
원 논문의 GitHub repo에 **핵심 입력 파일 3개**(`food.csv`, `foodname.csv`, `weight.csv`)와 **전처리 원본 데이터**(`metabolite_bacteria.xlsx`)가 누락되어 있음. 이를 아래 방법으로 역설계하여 재현:
- KG triple 데이터 11개 파일 활용
- FDC fatty acid → KEGG compound 수동 매핑 (46종)
- MiKG neurotransmitter-precursor inference chain
- ProMENDA (22,519 metabolite entries) 대규모 데이터 보강

### 최종 재현 상태

| 지표 | 우리 결과 | 논문 |
|------|-----------|------|
| Foods | 132/135 (97.8%) | 135 |
| Compounds (KEGG) | 134 | 85 |
| Compound-depression 매핑 | 73 (ProMENDA) | ~85 (MENDA) |
| Incidence assigned (≠0) | 103/134 (77%) | ~85/85 (100%) |
| 추천 패턴: 채소↑ 육류/설탕↓ | 부분 일치 | ✅ |

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

| 파일 | 출처 | 다운로드 |
|------|------|----------|
| ProMENDA Metabolite Dataset | Nature Supplementary Data 2 | https://www.nature.com/articles/s41398-024-02948-2 → Supplementary Data 2 (`41398_2024_2948_MOESM3_ESM.xlsx`) |

> ProMENDA 웹사이트(menda.cqmu.edu.cn)가 접속 불가할 수 있음. Nature 논문 페이지의 Supplementary Data 2로 다운로드.

### 디렉토리 구조 (실행 후)

```
Food4healthKG/                   ← 작업 디렉토리 (git clone)
├── food_nutrient.csv            ← FDC 원본 (repo 제공, 1M+ rows)
├── food_nutrient_updated.csv    ← [생성] fatty acid KEGG 매핑 추가
├── 41398_2024_2948_MOESM3_ESM.xlsx  ← [수동 다운] ProMENDA metabolite
├── foodkg_triply/               ← KG triple 데이터 (repo 제공, zip 해제)
│   ├── MENDA_Depression.jsonld
│   ├── KEGG_Compound.jsonld
│   ├── KEGG_Compound_Bacteria.jsonld
│   ├── Disease_Bacteria.jsonld
│   ├── Mental_health.jsonld
│   ├── Bacteria_Ontology.trig   (156MB)
│   ├── Food_Category.jsonld
│   ├── Food_Nutrient.trig       (132MB)
│   ├── Food_Ontology.jsonld
│   ├── Food_Chinese.jsonld
│   └── MESH_Disease.jsonld
├── analyse/
│   ├── final.py                 ← 원 논문 추천 알고리즘 (참고용)
│   ├── p5_foodname.txt          ← 135개 음식 이름 목록 (repo 제공)
│   ├── foodname.csv             ← [생성] food × compound + 이름
│   ├── food.csv                 ← [생성] food × compound + type
│   ├── weight.csv               ← [생성] incidence weight
│   ├── acs04.csv                ← [생성] 추천 확률
│   └── recommendation_results.png ← [생성] 시각화
├── preprocess/
│   ├── data_cleaning.py         ← 원 논문 전처리 (참고용, 입력 xlsx 없음)
│   └── spy_kegg.py              ← KEGG 크롤러 (참고용)
├── logs/                        ← [생성] 실행 로그
│   ├── YYYYMMDD_HHMMSS_step1_fatty_acid_kegg.txt
│   ├── YYYYMMDD_HHMMSS_step2_reconstruct.txt
│   ├── YYYYMMDD_HHMMSS_step3_inference.txt
│   ├── YYYYMMDD_HHMMSS_step4_promenda.txt
│   ├── YYYYMMDD_HHMMSS_step5_recommendation.txt
│   └── YYYYMMDD_HHMMSS_summary.txt
├── add_fatty_acid_kegg.py       ← [우리 코드] Step 1
├── reconstruct.py            ← [우리 코드] Step 2
├── knowledge_inference.py    ← [우리 코드] Step 3
├── map_promenda.py              ← [우리 코드] Step 4
├── run_recommendation.py        ← [우리 코드] Step 5
└── run_pipeline.py              ← [우리 코드] 전체 파이프라인 + 로그

MiKG-JAIMS/                      ← MiKG (별도 git clone)
└── MiKG_Schema_Data_20201007.ttl
```

---

## 3. 환경 설정

```bash
pip install pandas numpy scikit-learn matplotlib openpyxl
```

---

## 4. 실행 방법

### 방법 A: 한 번에 실행 (권장)

```bash
cd Food4healthKG
unzip foodkg_triply.zip
unzip food_nutrient.csv.zip

python3 run_pipeline.py
```

`run_pipeline.py`가 Step 1~5를 순서대로 실행하며:
- Step 1 후 `food_nutrient_updated.csv → food_nutrient.csv` 자동 복사
- 각 Step의 터미널 출력을 `logs/` 디렉토리에 타임스탬프 포함하여 저장
- 전체 요약을 `logs/YYYYMMDD_HHMMSS_summary.txt`에 저장
- 중간에 실패하면 해당 Step에서 중단

### 방법 B: 개별 실행

```bash
cd Food4healthKG
unzip foodkg_triply.zip
unzip food_nutrient.csv.zip

# Step 1: Fatty acid KEGG 매핑 추가 (88 → 134 compounds)
python3 add_fatty_acid_kegg.py
cp food_nutrient_updated.csv food_nutrient.csv

# Step 2: 입력 파일 역설계 (foodname.csv, food.csv, weight.csv)
python3 reconstruct_v2.py

# Step 3: Knowledge inference (MENDA + MiKG + ontology + literature)
python3 knowledge_inference_v3.py

# Step 4: ProMENDA 보강 (22,519 entries → incidence 확장)
python3 map_promenda.py

# Step 5: 추천 알고리즘 + 시각화
python3 run_recommendation.py
```

---

## 5. 각 Step 상세

### Step 1: `add_fatty_acid_kegg.py`

`food_nutrient.csv`의 fatty acid nutrient 235K rows (DHA, EPA, SFA, MUFA 등)에 KEGG compound ID를 수동 매핑. 원본 repo에서는 이 fatty acid들의 `nutrient_kegg` 값이 전부 0이었음.

| 지표 | 변경 전 | 변경 후 |
|------|---------|---------|
| KEGG compounds | 88 | **134** (+46) |
| KEGG 매핑된 행 | 647,710 | **843,508** |
| MENDA overlap | 24 | **47** (+23) |

매핑 근거: KEGG Compound Database (https://www.genome.jp/kegg/compound/)

### Step 2: `reconstruct_v2.py`

논문 GitHub에 누락된 3개 입력 파일을 역설계:
- `food_nutrient.csv` + `p5_foodname.txt` (135개 음식) → 132개 매칭
- `MENDA_Depression.jsonld` → compound별 positive/negative association
- `Food_Category.jsonld` + keyword 규칙 → food type 분류

생성 파일:
- `foodname.csv`: 132 foods × 134 compounds + fdc_id, name, type
- `food.csv`: 132 foods × 134 compounds + type
- `weight.csv`: 8 × 134 (초기 MENDA 기반, Step 3-4에서 업데이트됨)

미매칭 3개: 밀가루 변형 (FLOUR, PASTRY / all-purpose / bread) — FDC 이름과 불일치

### Step 3: `knowledge_inference_v3.py`

논문 Section 3.3의 knowledge inference를 5가지 소스로 구현:

| 우선순위 | Source | 방법 | 결과 |
|---------|--------|------|------|
| 1 | MENDA direct | `MENDA_Depression.jsonld`의 hasPositive/NegativeAssociation | 47개 compound |
| 2 | MiKG precursor | `MiKG_Schema_Data_20201007.ttl`에서 depression → neurotransmitter → precursor 체인. Serotonin→Tryptophan, Dopamine→Tyrosine 등 | +5 |
| 3 | Bacteria compound | `KEGG_Compound_Bacteria.jsonld` + `Disease_Bacteria.jsonld` + `Bacteria_Ontology.trig` name matching | +5 |
| 4 | Ontology | KEGG subClassOf 체인 (Vitamin E/A/D family, Folate family, Sugar family, Carotenoids) | +19 |
| 5 | Literature | Nutritional psychiatry 문헌 기반. Iron[PMID:22578925], Zinc[PMID:23567517], Mg[PMID:28654669] 등 | +12 |

### Step 4: `map_promenda.py`

ProMENDA (Pu et al., Translational Psychiatry, 2024)의 22,519 metabolite entries로 incidence 보강:
- KEGG ID 기반 매핑: 1,412 compounds, 17,653 entries
- Regulation 방향: **Up in depression → negative(-1)**, **Down in depression → positive(+1)**
- Study ≥ 2 필터 적용 (신뢰도)
- 기존 weight=0인 compound만 채움 (기존 inference 유지)

| 지표 | Step 3까지 | Step 4 후 |
|------|-----------|-----------|
| ProMENDA overlap | — | 73 |
| Incidence assigned | 88/134 | **103/134 (77%)** |
| New compounds | — | +15 |

주요 ProMENDA 결과 (study 수 기반 consensus):
- DHA (C06429): pos:28, neg:18 → **positive** ✅
- EPA (C06428): pos:12, neg:10 → **positive** ✅
- Palmitic acid (C00249): pos:46, neg:49 → **negative** ✅
- Sucrose (C00089): pos:5, neg:12 → **negative** ✅

### Step 5: `run_recommendation.py`

논문 Algorithm 1 재현:
1. Food compound matrix normalization (row-wise min-max)
2. `u = X × weight` (4 source별 food score)
3. Adjusted cosine similarity `S` (Eq.1)
4. `P = u^T × S` (recommendation probability, Eq.2)
5. Top-K=30 ranking + T-SNE/PCA 시각화

---

## 6. 최종 추천 결과

### Top 30 추천

| 순위 | 음식 | 카테고리 | Score |
|------|------|----------|-------|
| 1 | Pupusas, Bean | 채소 | 1.42 |
| 2-4 | MILK (Whole/2%/1%) | 유제품 | 1.24 |
| 10 | Egg | 유제품 | 0.73 |
| 19 | Hummus | 두류 | 0.60 |
| 20-21 | Chicken breast/drumstick | 가금류 | 0.58 |
| 23 | Tomatoes, diced | 채소 | 0.53 |
| 25 | Soybean oil | 유지 | 0.49 |
| 26 | Beans, snap | 채소 | 0.48 |

### Bottom 30 비추천

| 순위 | 음식 | 카테고리 | Score |
|------|------|----------|-------|
| 113 | Beef T-bone Steak | 육류 | -0.01 |
| 114 | Sugar, Granulated | 스위트 | -0.01 |
| 115 | Beef Eye of Round | 육류 | -0.01 |
| 123 | White bread | 곡물 | -0.17 |
| 124 | Coconut oil | 유지 | -0.20 |
| 127-128 | Ground turkey | 육류 | -1.27 |

### 카테고리 분포

| 카테고리 | 추천 Top 30 | 비추천 Bottom 30 | 논문 패턴 일치 |
|----------|------------|-----------------|-----------|
| 채소 | 5 | 1 | ✅ 추천 |
| 가금류 | 6 | 4 | — |
| 유제품 | 8 | 5 | — |
| Beef | 2 | **5** | ✅ 비추천 |
| 곡물/빵 | 4 | **5** | ✅ 비추천 |
| Sweets | 0 | **1** | ✅ 비추천 |
| Fats/Oils (coconut) | 0 | **1** | ✅ 비추천 |
| 과일 | 0 | 3 | ❌ 논문과 다름 |

---

## 7. 논문과의 차이 및 원인

### 일치
- Beef steak, Sugar, Coconut oil(SFA), White bread → 비추천 ✅
- 채소(Beans, Tomatoes), Hummus, Soybean oil → 추천 ✅
- Source 간 RMSE ≠ 0 (차등 가중치 작동) ✅
- ProMENDA 22,519 entries 기반으로 DHA/EPA positive, SFA/Sugar negative 확인 ✅

### 불일치

| 차이점 | 원인 |
|--------|------|
| 추천 Top에 우유/치즈 과다 | `metabolite_bacteria.xlsx` 원본 없이 역설계하여 dairy compound profile이 과대평가됨 |
| 과일이 추천 안 됨 | 과일 주요 compound(fructose, sucrose)가 MENDA/ProMENDA에서 negative 또는 tie |
| 생선이 추천 상위 아님 | Tuna만 1종 포함. 논문은 더 많은 생선 포함 가능 |
| **알고리즘 구조적 한계** | `P = u^T × S`에서 similarity S(compound amount 기반)가 incidence weight보다 결과를 지배. weight 변화 효과가 희석됨 |

### 근본 원인
논문 저자의 `metabolite_bacteria.xlsx` (54 bacteria × metabolite 수동 큐레이션 행렬)이 GitHub에 없음. `data_cleaning.py`가 이 파일을 읽는 코드이나, 입력 파일이 미공개.

---

## 8. 데이터 소스 요약

| Source | 용도 | 크기 | 비고 |
|--------|------|------|------|
| FDC `food_nutrient.csv` | 음식-영양소 | 80K foods, 211 nutrients | repo 제공 |
| `MENDA_Depression.jsonld` | compound-depression +/- | 5,675 entries | repo KG |
| ProMENDA (MOESM3) | compound-depression 보강 | 22,519 entries | Nature Suppl. |
| `KEGG_Compound_Bacteria.jsonld` | compound-bacteria 대사 | 201 bacteria | repo KG |
| `Disease_Bacteria.jsonld` | bacteria-disease 연관 | 741 bacteria | repo KG |
| `Bacteria_Ontology.trig` | bacteria ID-name 매핑 | 322K bacteria | repo KG |
| MiKG TTL | bacteria-neurotransmitter-disease | 48 bacteria, 6 NTM | GitHub |
| `KEGG_Compound.jsonld` | compound ontology (subClassOf) | 867 pairs | repo KG |
| `MESH_Disease.jsonld` | disease 분류 | 235K labels | repo KG |

---

## 9. 코드 파일 목록

| 파일 | 역할 | 입력 | 출력 |
|------|------|------|------|
| `run_pipeline.py` | 전체 파이프라인 실행 + 로그 저장 | 모든 아래 스크립트 | `logs/` 디렉토리 |
| `add_fatty_acid_kegg.py` | Step 1: Fatty acid KEGG 매핑 | `food_nutrient.csv` | `food_nutrient_updated.csv` |
| `reconstruct_v2.py` | Step 2: 입력 파일 역설계 | `food_nutrient.csv`, `p5_foodname.txt`, `MENDA_Depression.jsonld` | `foodname.csv`, `food.csv`, `weight.csv` |
| `knowledge_inference_v3.py` | Step 3: 5-source inference | `MENDA_Depression.jsonld`, `MiKG TTL`, `KEGG_Compound_Bacteria.jsonld`, `Disease_Bacteria.jsonld`, `Bacteria_Ontology.trig` | `weight.csv` (업데이트) |
| `map_promenda.py` | Step 4: ProMENDA 보강 | `41398_2024_2948_MOESM3_ESM.xlsx`, `weight.csv` | `weight.csv` (업데이트) |
| `run_recommendation.py` | Step 5: 추천 + 시각화 | `food.csv`, `weight.csv`, `foodname.csv` | `acs04.csv`, `recommendation_results.png` |

---

## 10. 프로젝트 확장 방향 (제안)

### A. 알고리즘 개선 (추천시스템 수업 적합)
현재 알고리즘의 구조적 한계(similarity S가 지배적)를 해결:
- **방법 1:** Incidence를 similarity 계산 전에 food matrix에 곱하여 "depression에 좋은 compound만 높은 값"으로 변환 후 similarity 계산
- **방법 2:** KG embedding (TransE, RotatE) → food-disease link prediction
- **방법 3:** GNN (R-GCN, CompGCN) → food node embedding으로 추천
- **방법 4:** Content-based neural → 영양소 벡터 feature + depression label로 분류

### B. Ablation Study
- Model A: Food → Nutrient → Disease (직접 경로만)
- Model B: Food → Nutrient → Microbiota → Disease (미생물 포함)
- 비교 지표: Precision@K, NDCG@K, 문헌 기반 validation

### C. 평가 강화
- SMILES trial (Jacka et al., BMC Medicine, 2017) ModiMedDiet 권장 식품을 ground truth
- 논문 Table 5 방식 literature-based validation 확장

---

## 11. 참고문헌

- Fu et al. (2023). Food4healthKG. *AIM*, 145, 102677.
- Liu et al. (2021). MiKG. *Health Info Sci Syst*, 9(1), 1-9.
- Pu et al. (2024). ProMENDA. *Translational Psychiatry*, 14, 229.
- Pu et al. (2020). MENDA. *Briefings in Bioinformatics*, 21(4), 1455-1464.
- Jacka et al. (2017). SMILES trial. *BMC Medicine*, 15(1), 23.
- Marx et al. (2021). Diet and depression. *Molecular Psychiatry*, 26(1), 134-150.
- Parker & Brotchie (2011). Tryptophan and tyrosine. *Acta Psychiatrica Scand*, 124(6), 417-426.
