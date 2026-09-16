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
원 논문의 GitHub repo에 **핵심 입력 파일 3개**(`food.csv`, `foodname.csv`, `weight.csv`)와 **전처리 원본 데이터**(`metabolite_bacteria.xlsx`)가 누락되어 있음. 이를 KG triple 데이터 + FDC fatty acid KEGG 매핑 + MiKG neurotransmitter inference로 역설계하여 재현.

### 현재 상태 요약

| 지표 | 우리 결과 | 논문 |
|------|-----------|------|
| Foods | 132/135 (97.8%) | 135 |
| Compounds (KEGG) | 134 | 85 |
| MENDA direct overlap | 47 | — |
| Incidence assigned (≠0) | 88/134 (66%) | ~85/85 (100%) |
| 추천 패턴: 채소↑ 육류/설탕↓ | 부분 일치 | ✅ |

---

## 2. 필요한 Repository

```bash
# 1. Food4healthKG 원본 (논문 데이터 + KG triple)
git clone https://github.com/ccszbd/Food4healthKG.git

# 2. MiKG (bacteria–neurotransmitter–mental disorder 관계)
git clone https://github.com/tingcosmos/MiKG-JAIMS.git
```

### 디렉토리 구조 (실행 후)

```
food_recom_w_paper/              ← 작업 디렉토리 (Food4healthKG clone)
├── food_nutrient.csv            ← FDC 원본 (repo 제공, 1M+ rows)
├── food_nutrient_updated.csv    ← fatty acid KEGG 매핑 추가된 버전
├── foodkg_triply/               ← KG triple 데이터 (repo 제공, zip 해제)
│   ├── MENDA_Depression.jsonld  ← compound↔depression 연관 (+/-)
│   ├── KEGG_Compound.jsonld     ← KEGG compound ontology
│   ├── KEGG_Compound_Bacteria.jsonld  ← compound↔bacteria 대사 관계
│   ├── Disease_Bacteria.jsonld  ← bacteria↔disease 연관
│   ├── Mental_health.jsonld     ← 질환 sameAs 매핑
│   ├── Bacteria_Ontology.trig   ← bacteria 분류 체계 (156MB)
│   ├── Food_Category.jsonld     ← 식품 카테고리
│   ├── Food_Nutrient.trig       ← food-nutrient 관계 (132MB)
│   ├── Food_Ontology.jsonld     ← 식품 온톨로지
│   ├── Food_Chinese.jsonld      ← 중국 식품 온톨로지
│   └── MESH_Disease.jsonld      ← MeSH 질환 온톨로지
├── analyse/                     ← 분석 코드 + 생성된 입력 파일
│   ├── final.py                 ← 원 논문 추천 알고리즘 코드
│   ├── p5_foodname.txt          ← 135개 음식 이름 목록 (repo 제공)
│   ├── heatmap.xlsx             ← 히트맵 데이터 (repo 제공)
│   ├── foodname.csv             ← [생성] food × compound 행렬 + 이름
│   ├── food.csv                 ← [생성] food × compound 행렬 + type
│   ├── weight.csv               ← [생성] 8 × compound incidence weight
│   ├── acs04.csv                ← [생성] 추천 확률 결과
│   └── recommendation_results.png  ← [생성] 시각화
├── preprocess/
│   ├── data_cleaning.py         ← 원 논문 전처리 (참고용, 입력 xlsx 없음)
│   └── spy_kegg.py              ← KEGG 크롤러 (참고용)
├── add_fatty_acid_kegg.py       ← [우리 코드] fatty acid KEGG 매핑
├── reconstruct_v2.py            ← [우리 코드] 입력 파일 역설계
├── knowledge_inference_v3.py    ← [우리 코드] knowledge inference
└── run_recommendation.py        ← [우리 코드] 추천 알고리즘 + 시각화

MiKG-JAIMS/                      ← MiKG clone (별도 디렉토리)
└── MiKG_Schema_Data_20201007.ttl ← bacteria–neurotransmitter–disease 관계
```

---

## 3. 환경 설정

```bash
# Python 3.8+
pip install pandas numpy scikit-learn matplotlib openpyxl
```

---

## 4. 실행 순서

### Step 0: 데이터 준비

```bash
cd Food4healthKG

# KG triple 데이터 압축 해제
unzip foodkg_triply.zip
unzip food_nutrient.csv.zip
```

### Step 1: Fatty acid KEGG 매핑 추가

```bash
python3 add_fatty_acid_kegg.py
```

**하는 일:** `food_nutrient.csv`의 fatty acid nutrient 235K rows (DHA, EPA, SFA, MUFA 등)에 KEGG compound ID를 매핑. KEGG compound DB 기반 수동 매핑 테이블 사용.

**결과:**
- KEGG compounds: 88 → **134** (+46)
- MENDA overlap: 24 → **47** (+23)
- `food_nutrient_updated.csv` 생성

**⚠️ 중요:** 실행 후 반드시 덮어쓰기:
```bash
cp food_nutrient_updated.csv food_nutrient.csv
```

### Step 2: 입력 파일 역설계

```bash
python3 reconstruct_v2.py
```

**하는 일:** 논문 GitHub에 누락된 3개 입력 파일을 `food_nutrient.csv` + `p5_foodname.txt` + `MENDA_Depression.jsonld`로 역설계.

**생성 파일:**
- `analyse/foodname.csv` — 132 foods × 134 compounds + fdc_id, name, type
- `analyse/food.csv` — 132 foods × 134 compounds + type (알고리즘 입력)
- `analyse/weight.csv` — 8 × 134 (4 source × pos/neg, 초기 MENDA 기반)

### Step 3: Knowledge Inference

```bash
python3 knowledge_inference_v3.py
```

**하는 일:** 5가지 소스로 134개 compound 전체에 incidence (+1/-1/0) 부여 → `weight.csv` 재생성.

**Inference 소스 (우선순위 순):**

| # | Source | 방법 | 결과 |
|---|--------|------|------|
| 1 | MENDA direct | `MENDA_Depression.jsonld` 파싱, hasPositive/NegativeAssociation | 47개 (24 pos-only, neg-only, both) |
| 2 | MiKG precursor | `MiKG_Schema_Data_20201007.ttl`에서 depression→neurotransmitter→precursor 체인 | +5 (Tryptophan, Tyrosine, Phenylalanine, Histidine, Vitamin B-12) |
| 3 | Bacteria compound | `KEGG_Compound_Bacteria.jsonld` + `Disease_Bacteria.jsonld` + `Bacteria_Ontology.trig` name matching | +5 (Starch, Tocotrienol α/β/γ/δ) |
| 4 | Ontology | KEGG subClassOf 체인 (Vitamin E family, Folate family, Sugar family, Carotenoids, Vitamin D) | +19 |
| 5 | Literature | Nutritional psychiatry 문헌 기반 (Iron, Zinc, Mg, Se, Ca, K, Na, Caffeine 등) | +12 |

**결과:** 88/134 assigned (66%), positive 75, negative 13, neutral 46

### Step 4: 추천 알고리즘 + 시각화

```bash
python3 run_recommendation.py
```

**하는 일:** 논문 Algorithm 1 재현:
1. Food compound matrix normalization (row-wise min-max)
2. `D = weight × food^T` (incidence score)
3. Adjusted cosine similarity (Eq.1)
4. `P = D^T × S` (recommendation probability, Eq.2)
5. Top-K=30 ranking
6. PCA + T-SNE 시각화

**생성 파일:**
- `analyse/acs04.csv` — 4 source별 추천 확률
- `analyse/recommendation_results.png` — PCA + T-SNE + Pyramid 시각화

---

## 5. 현재 추천 결과

### Top 30 추천 (inference 기준)

| 순위 | 음식 | 카테고리 |
|------|------|----------|
| 1 | Pupusas, Bean | 채소 |
| 2-4 | MILK (Whole/2%/1%) | 유제품 |
| 5-6 | Mustard | 소스 |
| 7-9 | Rice flour | 곡물 |
| 10 | Egg | 유제품 |
| 19 | Hummus | 두류 |
| 20-21 | Chicken breast/drumstick | 가금류 |
| 23 | Tomatoes, diced | 채소 |
| 25 | Soybean oil | 채소 |
| 26 | Beans, snap | 채소 |

### Bottom 30 비추천

| 순위 | 음식 | 카테고리 |
|------|------|----------|
| 113 | Beef T-bone Steak | 육류 |
| 114 | Sugar, Granulated | 스위트 |
| 115 | Beef Eye of Round | 육류 |
| 117 | Chinese Fried Rice | 곡물 |
| 123 | White bread | 곡물 |
| 124 | Coconut oil | 유지 |
| 125 | Whole wheat bread | 곡물 |
| 129 | Greek yogurt (non-fat) | 유제품 |

### 카테고리 분포

| 카테고리 | 추천 Top 30 | 비추천 Bottom 30 | 논문 패턴 |
|----------|------------|-----------------|----------|
| 채소 | 5 | 1 | 추천 ✅ |
| 유제품 | 8 | 5 | 중간 |
| 가금류 | 6 | 4 | — |
| Beef | 2 | 5 | 비추천 ✅ |
| 곡물 | 4 | 5 | 비추천 ✅ |
| Sweets | 0 | 1 | 비추천 ✅ |
| 과일 | 0 | 3 | 논문과 다름 ❌ |

---

## 6. 논문과의 차이 및 원인

### 일치하는 점
- Beef steak, Sugar, Coconut oil(SFA 높음)이 비추천 → ✅
- 채소(Beans, Tomatoes), Hummus가 추천 → ✅
- Source 간 RMSE ≠ 0 (차등 가중치 작동) → ✅

### 불일치 및 원인

| 차이 | 원인 |
|------|------|
| 추천 Top에 우유/치즈 과다 | `metabolite_bacteria.xlsx` 원본 없이 역설계하여 dairy의 compound profile이 과대평가됨 |
| 과일이 추천에 없음 | Pears 등의 주요 compound (fructose, sucrose)가 MENDA에서 both(+/-)로 tie-break가 positive로 처리되나, 과일 특유의 antioxidant가 적게 반영됨 |
| 생선이 추천 상위가 아님 | 논문은 DHA/EPA를 강하게 positive로 처리했을 것이나, MENDA에서 EPA는 negative, DHA는 both로 되어 있음 |
| 알고리즘: similarity가 지배적 | `P = D^T × S`에서 S(food compound profile 기반)가 incidence weight보다 결과를 지배하여, weight 변화의 효과가 희석됨 |

### 근본 원인
논문 저자가 수동 큐레이션한 `metabolite_bacteria.xlsx` (54 bacteria × metabolite 행렬)이 GitHub에 없음. 이 파일이 85개 compound의 incidence를 결정하는 핵심 데이터이며, KG triple 파일에는 그 일부만 반영됨.

---

## 7. 프로젝트 확장 방향 (제안)

### A. 알고리즘 개선 (추천시스템 수업 적합)
- 현재 cosine similarity 기반 → KG embedding (TransE, RotatE) 또는 GNN (R-GCN) 대체
- Incidence를 similarity 계산 전에 food matrix에 곱하는 방식으로 수정
- Ablation: 미생물 경로 유무 (Model A vs B) 비교

### B. 데이터 확장
- ProMENDA (2024, 22,519 entries) 다운로드하여 MENDA 대체
- 저자 메일 (xpjiang@mail.ccnu.edu.cn)로 `metabolite_bacteria.xlsx` 요청

### C. 평가 강화
- SMILES trial (Jacka et al., 2017) ModiMedDiet 권장 식품을 ground truth로 활용
- 논문 Table 5 방식 literature-based validation 확장

---

## 8. 참고문헌

- Fu et al. (2023). Food4healthKG. *AIM*, 145, 102677. https://doi.org/10.1016/j.artmed.2023.102677
- Liu et al. (2021). MiKG. *Health Info Sci Syst*, 9(1), 1-9.
- Jacka et al. (2017). SMILES trial. *BMC Medicine*, 15(1), 23.
- Marx et al. (2021). Diet and depression. *Molecular Psychiatry*, 26(1), 134-150.
- Pu et al. (2020). MENDA. *Briefings in Bioinformatics*, 21(4), 1455-1464.
