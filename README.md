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
| §3.1 Table 1 Relation 열 | 8 / 8 소스 일치 (합 정의) | 열 합 156 / Total 140 | ✅ |
| §3.2 Entity linking 5수치 | 5 / 5 일치 (확정 4 · 추정 1) | — | ⚠️ 128 은 미해결, 합계도 미해결 |
| §3.3 관계 어휘 | 6 / 6 존재 | 6 | ✅ |
| §3.3 hasAssociation 관계 계층 | 선언 0건, 방향 무시해도 공통 쌍 0건 | 본문은 묶인다고 적음 | ❌ 한 번도 작동 안 함 |
| §3.3 하위관계의 방향 특정 | pos∩neg 267쌍 | §3.3 은 "more specific" 이라 적음 | ⚠️ KG 가 방향을 못 정한다 |
| §3.3 추론 statements | 배포본 0, **규칙(a) 재구현 2,436,403** | 4,741,023 | ⚠️ 51.4% 설명 (§17.20) |
| §3.3 추론 규칙 (b) 구현 | 정신질환 45/45 쌍(트리플 90) · 질병 전체 7,552. Table 5 Complication **8/8**(근거 세균까지 7/8), Table 4 3/3 | 중간 분류 + 공통 미생물 | ⚠️ 규칙이 변별하지 못한다 (§17.24) |
| §3.1 Table 1 Entity 열 | 8 / 8 소스 일치 | 열 합 4,995,950 / Total 1,637,915 | ✅ |
| §3.1 본문 수치 3개 | FDC 34,250 ✅ · KEGG metabolites 230 ✅ · NCBI 326,533 | 34,250 / 230 / 322,917 | ⚠️ 2/3 일치 |
| Foods | 135 / 135 | 135 | ✅ |
| Compounds | 85 / 85 | 85 | ✅ |
| 성분 행렬 F vs 논문 heatmap | 행 코사인 0.981 | — | ✅ |
| 측정 밀도 (compound 수 중앙값) | 28 | 33 | ⚠️ FDC 판 차이 |
| PCA 80% 도달 성분 수 (§4.2.1) | 5 | 5 | ✅ |
| E 방향 확보 | 69 / 85 | 85 | ⚠️ 16종은 MENDA 에 데이터가 없다 (§17.28) |
| 논문이 부호를 명시한 compound (gold) | 8 / 9 | 9 | ✅ |
| **추천 순위 Top30 겹침** (우연 6.7) ※ | **18 / 30** | 30 | ✅ |
| **추천 순위 Bottom30 겹침** (우연 6.7) ※ | **15 / 30** | 30 | ✅ |
| 순위 Spearman ※ | **+0.786** | 1.0 | ✅ |
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
│   │                                  ※ acs04.csv 로 낼 때 4번째 소스는 'type4' 로 이름만 바꾼다
│   │                                    (공식 final.py 가 df['type4'] 를 읽는다)
│   ├── knowledge_query_results.csv ← compound 별 E 와 근거
│   └── acs04.csv, *.png            ← 추천 확률, 시각화
└── logs/                           ← [생성] 실행 로그
```

---

## 3. 환경 설정

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy scipy scikit-learn matplotlib openpyxl
pip install pyoxigraph        # eval/paper_sparql.py, eval/paper_kg_stats.py 에 필요
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
python3 tools/scorecard.py --check-docs   # 문서에 적힌 수치가 현재 값과 맞는가 (§17.19)
```

`run_pipeline.py` 는 step0~4 를 순서대로 실행하고, 각 step 의 출력을
`logs/YYYYMMDD_HHMMSS_<step>.txt` 에, 요약을 `..._summary.txt` 에 저장한다.
중간에 실패하면 그 step 에서 멈춘다.

> ⚠ `reconstruct.py` 를 단독으로 돌리면 `weight.csv` 가 step1 초기값으로 덮어써져
> step2·3 의 `E` 가 사라진다. step1 을 건드렸으면 **반드시 `run_pipeline.py` 로 전체를
> 다시 돌릴 것.**

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
python3 eval/paper_data.py       # 논문 수치 29개 체크리스트 (상태·근거)
python3 tools/paper.py hunt 230  # 수치 탐색 (판정 전 필수). --paper 로 전부
python3 eval/paper_kg_stats.py   # 논문 §3 검증 (Table 1 Relation·Entity, 링킹, 관계) 약 1분
python3 eval/m1.py               # 논문 §5.1 방법 1(20문항) + 방법 2 추론 재현
python3 eval/paper_sparql.py     # 보충자료 SPARQL 을 공개 KG 에 실행 (Table 2~5, 약 4분)
python3 eval/paper_sparql.py replaceable   # §4.1 "엔티티 교체 가능" 주장 실증 (§17.21)
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
- **카테고리:** FDC 원본의 `food_category_id` 를 쓰고, **§3.2 의 병합 규칙을 적용한다**
  (`rollup_category()`). `Food_Category.jsonld` 의 `rdfs:subClassOf` 를 따라 WWEIA
  세분류를 FDC legacy 상위로 올린다. 135개 음식 기준 18 → **17 종**이 되어 논문
  Fig. 4(b) 범례와 일치한다 (REPRODUCTION §17.16).

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

> **공식 `final.py` 가 읽는 입력은 4개다** — `food.csv` · `weight.csv` · `foodname.csv` ·
> `acs04.csv`. 네 개 모두 배포본에 없어 step0~3 이 역설계한다.
> `jaccard01.csv` 도 코드에 나오지만 **저자가 주석 처리한 죽은 줄**이다
> (`# df = pd.read_csv('jaccard01.csv')` 바로 아래에서 `acs04.csv` 를 읽는다).
> 짝이 되는 `jaccard_similarity()` 도 정의만 있고 호출 0건이고, 논문 §4.2.2 가 쓰는
> 유사도는 adjusted cosine 하나다. **만들지 않는 것이 맞다.**
> (AP·hit·precision·recall 도 같은 상태 — 정의만 있고 `cal_results()` 에서 전부 주석.)

### Step 4: `run_recommendation.py`
논문 Algorithm 1 을 공식 `final.py` 에서 이식했다.
1. F 행별 min-max 정규화
2. `u = Xn · E`, E = pos − neg (논문 §4.2.1. `E_MODE=official` 은 final.py 의 단일 행)
3. adjusted cosine similarity S (Eq. 1, final.py 구현)
4. `p = u · S / colsum(S)` (Eq. 2. 열 합 나누기는 final.py 에만 있다)
5. Top-K = 30 + PCA / t-SNE 시각화

논문 수식(§4.2)과 final.py 가 네 군데서 다르다. 16조합 비교에서 final.py 가 2위(+0.786),
논문 수식이 6위(+0.602)로 final.py 쪽이 논문 결과에 더 가까워 그쪽을 따른다 (REPRODUCTION §3).

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

※ 이 세 줄은 **논문에 없는 지표**다. 논문 §5.1 의 두 평가 방법은 질의와 추론만 덮고
추천 알고리즘에는 평가가 없다(REPRODUCTION §17.27 ⑦). 또 `p5_foodname.txt` 를 논문
순위로 보는 것은 추정이다(`tools/core.paper_ranking` 주석). 논문이 추천 **결과에 대해**
직접 적은 기준은 Fig. 5 의 카테고리 층(Fruits·Vegetables 상위 / Baked·Beef·Sausages·
Pork 하위)뿐이며, 그쪽이 재현 판정의 1차 기준이다. 세 층 구분은 REPRODUCTION §18.9.

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

**KG 규모.** 공개 KG 는 4,314,742 트리플이다. 논문 Table 1 의 9개 소스 중 7개가 트리플 수까지
일치한다. SNOMED CT(429만)와 추론 트리플(474만)은 없고, MENDA 는 2,633 / 5,675 다
(누락이 아니라 집계 형태의 차이다. 논문은 원본 xlsx 의 행 수를, KG 는 compound 510종으로
집계한 트리플 수를 적었다 — REPRODUCTION §17.4).

**배포본 = 논문 KG − 추론 − SNOMED.** `13,346,991 − 4,741,023 − 4,291,226 = 4,314,742` 로
공개 KG 실측과 정확히 같다. 배포본은 논문 KG 의 32.3% 이고, 빠진 68% 가 논문이 기여로
내세운 두 가지다 (REPRODUCTION §17).

**쿼리 → 논문 표**

| 논문 | 재현 | 비고 |
|---|---|---|
| Query 2 → Table 3 | **8 / 8** | 원문 쿼리만으로는 **5/8**. (+)/(−) 부호는 8/8 이 KG pos·neg 양쪽이라 유도 불가 (§17.22) |
| Query 3 → Table 4 | **5 / 5** | 원문 Query 3 는 **0행** — SNOMED 이름을 MiKG 에서 보충. 음식–성분을 제대로 묶으면 4 / 5. 질병명 **2/5 불일치** (§17.23) |
| Query 1 → Table 2 | 6 / 8 | **값이 틀렸다.** 올바른 합의 30~70배 (아래) |

**§5.1 방법 1 — 전문가 20문항** (`eval/m1.py`). 전문가 3인의 수작업 대조는
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
- §4.2 수식(Eq. 1 분모, Eq. 2 첨자)이 조판 오류. 그대로는 구현 불가.
  구현 가능한 형태로 읽어 16조합을 비교하면 논문 수식은 6위(ρ +0.602, Top30 7/30),
  공식 `final.py` 는 2위(ρ +0.786, Top30 18/30)
- 단위 환산과 ProMENDA 극성 처리를 적지 않음
- Table 3/4 의 compound 6종(Glutamic acid·L-Threonine·Choline·Citric acid·Lysine·Cystine)이
  Fig. 4(c) 85종 목록에 없음
- §4.2.3 본문과 Fig. 5 가 피라미드에서 두 군데 모순: 어류 위치, 상단 층(본문 "barbecue products", 그림 "Baked Products")
- §4.2.3 의 성분 차이 서술이 논문 자신의 heatmap 과 어긋남 (미량원소·다량영양소)
- `final.py` 입력 4개와 `metabolite_bacteria.xlsx` 누락, `food_nutrient.csv` 절단
- **Supplementary Query 1 의 결함으로 Table 2 값이 틀렸다.** `?milkunit` 이 `?milk` 에 묶여 있지
  않아 두 번째 음식의 성분량이 다른 음식 값으로 들어간다. Table 2 의 "달걀 프라이 + 우유 =
  비타민 B6 6.591" 은 달걀 0.151 + Kellogg's Special K 시리얼 6.44 다. 실제 우유는 0.061
- 음식을 라벨 부분 문자열로 찾아, "milk" 가 "Ricotta cheese, whole milk" 에 걸린다 (Table 1 #5)
- **§3.3 의 관계 계층이 선언돼 있지 않고, 데이터에서 한 번도 작동하지 않는다.**
  `hasAssociation`(세균→질병) 2,743 쌍과 하위관계(질병→compound·세균) 556 쌍 사이에 방향을
  무시해도 공통 쌍이 0 이다. 우울증 한정으로 보면 일반관계 1 종 vs 하위관계 45 종, 공통 0 종.
  "categorized under" 는 이름 짓기 규약일 뿐이다 (REPRODUCTION §17.13)
- **우울증의 `hasAssociation` 미생물 연결이 1 종뿐이다.** §3.3 의 "공통 미생물 → complication"
  추론을 일반관계만으로는 세울 수 없다 (REPRODUCTION §17.13)
- **`hasPositiveAssociation` 과 `hasNegativeAssociation` 이 배타적이지 않다.** 같은
  (우울증, compound) 쌍 267 개가 양쪽에 달려 있다 — compound 방향이 KG 만으로 정해지지 않는
  근본 원인이다 (REPRODUCTION §17.13)
- **Table 1 의 Relation 열과 Triples 열이 다른 파일을 센다.** FDC 의 relation 9 는
  `Food_Nutrient`(5)+`Food_Category`(4) 인데, triples 2,332,603 은 `Food_Nutrient` 단독이다.
  `Food_Category` 의 34,574 트리플은 어느 행에도 없다 (REPRODUCTION §17.9)
- **Table 1 의 Relation Total 140 이 자기 열의 합(156)과 다르다.** Total 만 중복을 제거한 값이다
- **Table 1 의 Total 행이 자기 소스 열 합보다 37,604 많다.** 미등재 파일
  `Food_Category`(34,759)+`Disease_Bacteria`(5,887)=+40,646 에서 MENDA 과대계상 −3,042 을 빼면
  정확히 37,604 이다 (REPRODUCTION §17.14)
- ⚠ **§3.2 의 "normalized entities" 서술이 모호하다.** food 1,220,480 · compounds 23,212 ·
  microbiota 984,031 은 Table 1 Entity 열 그대로이고 정의는 RDF 노드 수다. 동의어 병합 규칙을
  설명한 직후에 제시되어 병합 결과로 읽히지만, §3.2 서두가 normalization 을 "URI 부여 + 속성
  보존" 으로 정의하므로 자기 정의로는 모순이 아니다 (REPRODUCTION §17.10·§17.14)
- **Table 1 의 Entity Total 1,637,915 가 자기 열의 합(4,995,950)이 아니다.** §3.2 의 네 수치
  합(1,010,876)도 아니다
- **§3.2 의 "128 distinct food categories" 가 설명되지 않는다.** 논문이 서술한 병합
  (`rdfs:subClassOf` 롤업, 예시까지 배포 파일과 일치)을 끝까지 적용하면 **64** 개가 남는다.
  부분집합 6 × 라벨 정규화 12 = 72 조합 어디서도 128 이 나오지 않는다(범위 18~185).
  128 = 64×2 는 우리 재구성이다 (REPRODUCTION §17.16)
- **§3.2 의 "3,505 mental disorders" 는 MENDA(2,367)+MiKG(1,138) 로 정확히 맞는다** — 논문은
  "link ... to the MeSH and SNOMED CT databases" 라고 적었다. 일치는 정확하지만 인과는 추정이다
  (REPRODUCTION §17.12·§17.14)
- **§3.2 의 합계 1,637,915 가 자기 문장대로 더해지지 않는다.** 네 수치 합은 1,010,876 이다
- **Table 3 의 (+)/(−) 부호가 쿼리에서 유도되지 않는다.** Query 2 는 neg 목록만 뽑는데
  Table 3 의 compound 8/8 이 KG 에서 pos·neg 양쪽에 있다. "L-threonine 이 우울증을
  악화시킨다" 는 인과 방향은 배포 KG 로 뒷받침되지 않는다 (REPRODUCTION §17.22)
- **§3.3 의 합병증 추론 규칙이 아무것도 걸러내지 못한다.** 세균 연결이 있는 정신질환
  10종의 **가능한 45쌍이 전부 세균을 공유**해서 조건 (1) 은 완전그래프를 만든다. 조건
  (2)("both mood disorders")도 MiKG 계층이 `mentalDisorder` → 리프 10개로 평평해
  중간 분류가 없다. 게다가 **논문 Table 5 의 Complication 3행(Parkinson ×2,
  Alzheimer ×1)은 정신질환이 아니어서 논문이 적은 조건 (2) 를 스스로 위반**한다 —
  규칙 서술보다 넓은 규칙으로 표를 만든 것이다 (REPRODUCTION §17.24)
- **Table 4 의 질병명이 논문 자신의 Table 5 와 어긋난다.** Table 4·Fig 3 은 2·3 행을
  "Intellectual disability" 로 적지만, Table 5 No 9 는 같은 사례를 "Milk and **Learning
  disabilities**" 로 적는다. 배포 KG 에서 `D008607`(Intellectual Disability) 은 `sameAs`
  0건·세균 연결 0건의 고립 노드이고, E. coli·L. plantarum 에 붙는 것은
  `D007859`(Learning Disabilities) 다. Table 5 쪽이 KG 와 일관된다 (REPRODUCTION §17.23)
- **§4.2.1 의 `E ∈ {+1,−1}` 은 배포 자료로 충족할 수 없다.** 85종 중 **16종이 0** 인데,
  15종은 KG 의 pos/neg 목록에 **아예 없고** 12종은 ProMENDA 에도 없다. 특히 Fig. 4(c) 의
  **Trace Elements 5/5 · Macronutrient 5/5 가 통째로 비어 있다** — 미네랄은 우울증
  대사체 DB 인 MENDA 에 있을 수 없다. 논문은 이 10종에 어떻게 부호를 주었는지 적지 않는다
  (REPRODUCTION §17.28)
- **§5.1 의 0.95/0.9/0.95 는 정확도가 아니라 전문가별 동의율이다.** Supplement Table 1
  의 V0/V1/V2 열 합(19/18/19)이 그 수치를 정확히 재현한다. 논문은 "accuracy against the
  **gold standard** answers" 라 적었으나 단일 gold 가 없고 전문가 판정이 4문항에서
  갈린다 (REPRODUCTION §17.27)
- **그 20문항 테스트는 포화되어 변별력이 거의 없다.** 3인 만장일치 16/20 이고 **2인
  이상이 "KG 가 틀렸다" 고 본 문항은 0개**다. 전문가 간 일치도(IAA)도 보고되지 않는다
  (REPRODUCTION §17.27)
- **"15 inferred results" 중 7건은 추론 산출물이 아니다.** Table 5 의 Attributes 는
  Complication 8 + **Diet recommendation 7** 인데 후자는 §4.1 쿼리 결과다. "randomly
  select" 의 모집단도 명시되지 않는다 (REPRODUCTION §17.27)
- **"11 confirmed" 의 분모가 불명확하다.** confirmed 11 / unknown 3 / contradicted 1 로
  확인율은 **0.73** 이다(unknown 제외 시 0.92). 레이블링은 저자 본인이 했고 블라인드도
  음성 대조군도 없다 (REPRODUCTION §17.27)
- **추천 알고리즘(§4.2)에는 평가가 아예 없다.** 방법 1 은 질의를, 방법 2 는 추론을
  덮는다. 논문이 내세운 주 응용인 food recommendation 은 어느 쪽에서도 채점되지 않고,
  `K=30` 근거도 정답 정의도 없다. 따라서 우리 §16 의 Spearman·Top/Bottom-K 는
  **논문에 없는 지표를 우리가 도입한 것**이며 재현 점수와 분리한다 (REPRODUCTION §17.27)
- **Table 5 Diet 7행 중 5행이 배포 KG 에서 성립하지 않는다.** 음식도 성분 노드도 다
  있는데, ① 아미노산 측정이 비타민의 **1/20**(Cystine 95 · Threonine 255 vs Niacin
  8,007)이라 Garlic·Coffee·Sweets·Egg products 에 기록이 0건이고(논문도 §4.2.3 에서
  "missing values" 로 인정), ② 대사 세균 201종과 질병연관 세균 764종의 **교집합이
  72종**뿐이라 Lettuce–anxiety 경로가 끊긴다 (REPRODUCTION §17.25)
- **Table 5 #1 의 근거 세균이 KG 와 맞지 않는다.** 논문은 Parkinson–depression 합병증의
  근거로 *Streptococcus mutans* 를 들지만, taxon 1309 가 붙는 질병 8개에 우울증이 없다.
  두 질병을 실제로 잇는 세균은 4종이고 S. mutans 는 거기 없다 (REPRODUCTION §17.26)
- **§4.1 의 "질환을 바꿀 수 있다" 가 사실이 아니다.** Q2·Q3 는 `hasPositive/Negative
  Association` 을 가진 질환에서만 돌아가는데 배포 KG 에서 그런 질환은 `Major depressive
  disorder` **하나뿐**이다. MiKG 의 mental disorder 10종 중 1종. 반면 Q1 의 영양소·음식
  교체는 사실이다 (REPRODUCTION §17.21)
- **Query 1 은 변수 미결합 때문에 계산적으로도 실행 불가능하다.** `count(*)` 가 20분에도
  끝나지 않는다. 값이 틀린 것에 더해 쿼리 자체가 폭발한다 (REPRODUCTION §17.21)
- **§3.3 이 추론 예시로 든 것(KEGG compound 계층)이 실제 생성량의 0.1% 다.** 규칙 (a) 를
  재구현하면 2,436,403 건이 나오는데 그 **90%가 NCBI 계통수**의 조상 닫힘이고 KEGG 는
  1,858 건뿐이다. 서술과 실제 기여원이 다르다 (REPRODUCTION §17.20)
- **공개 KG 에 질병 계층이 전혀 없다.** SNOMED CT 는 0 트리플, MeSH 는 라벨 23만 개를 담고도
  연관에 쓰인 253개 질병 중 트리번호 보유 **0개**다. MiKG 가 `mentalDisorder` 단층 10종을 줘
  Query 3 의 "mental disorder" 분류는 복원되지만(Table 4 5/5), §3.3 이 추론 근거로 든
  **"mood disorder" 같은 중간 분류는 어떤 배포 자료에도 없다** (REPRODUCTION §17.17)
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
| `m1.py` | §5.1 방법 1(20문항을 KG 에 질의)·방법 2 추론 재현(`table5_inference`) |
| `m1.py` | §5.1 방법 1 — (질문, 논문 정답, 검증쿼리) 20삼중항 + 전문가 전원동의 분리. 공개 KG 공통 로더도 여기 |
| `paper_data.py` | **논문 전사 자료 한 곳** — Supplement Table 1(20문항) · Table 5(15건) · 논문 수치 29개 체크리스트. MISMATCH 는 `tools/paper.py hunt` 탐색 후에만 표시 가능(코드 강제) |
| `paper_kg_stats.py` | §3 전체 검증 — §3.1 Table 1 Relation·Entity 열·본문 수치, §3.2 Entity linking, §3.3 관계 표현 |
| `paper_sparql.py` | 공개 KG 에 보충자료 SPARQL 을 실행해 Table 2~5 대조 (`pyoxigraph`) |
| `gold.py` | 논문이 부호를 명시한 compound 9종 — 파라미터를 고르는 독립 기준 |

### tools/ (진단·검증, 모두 `core.py` 공유)

| 파일 | 하위 명령 |
|------|-----------|
| `scorecard.py` | 재현 집계 — 먼저 볼 것. `--check-docs` 로 문서 수치 검사(§17.19) |
| `paper.py` | `units` 단위 역산 · `claims` 논문 주장 검정 · `invert` E 역추정 · `improve` 개선판 · **`hunt` 수치 탐색기**(논문 값이 안 나온다고 말하기 전 필수) |
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

### 남은 방향 (상세는 REPRODUCTION §18, 우선순위대로)

논문 지표를 움직이는 크기 / 비용으로 매겼다. 판정은 §5.1 방법 1·2 와 §3·§4 수치로만 한다.

| | 항목 | 논문 근거 | 성공 기준 |
|---|---|---|---|
| ~~1~~ | ~~§3.2 Entity linking 검증~~ | §3.2 수치 4개 | **완료 — 0/5 일치 (§17.7)** |
| 2 | §3.3 추론 재구현 (474만) | §3.3 규칙 (a) 전이 (b) 공통 세균 | Table 5 Complication 8/8, 생성 수 대조 |
| 3 | **E 보강 69 → 85/85** | §4.2.1 | gold 8/9·Spearman +0.786 유지 이상 |
| 4 | 방법 2 PubMed 재검색 | §5.1 | 11/15 재현 |
| 5 | 방법 1 문항 확장 | §5.1 "further evaluations ... necessary" | 확장 문항 재현율이 18/20 수준 유지 |
| 6 | SNOMED 284 개념 | — | Query 3 원문 실행 (수치는 거의 불변, §17.6) |

논문 범위 밖(§5.2 가 든 한계를 따라가는 확장, 재현 수치와 분리): KG embedding
(TransE/RotatE), 미생물 없이 성립하는 nutrient→neurotransmitter 경로, 개인화.
외부 ground truth 로는 SMILES trial (Jacka et al. 2017) ModiMedDiet.

여전히 유효한 지름길: 저자에게 `weight.csv` 요청 — E 를 확정할 수 있는 유일한 경로다.

---

### 최신 데이터로 다시 만든 우리 KG (`ourkg/`)

논문의 구축 방식·평가 방식을 그대로 쓰고 데이터만 최신 공개본으로 바꾼 별도
파이프라인이다. **재현 결과와 섞지 않는다** — 재현은 `reconstruct.py` →
`run_recommendation.py` 경로이고, 이쪽은 `ourkg/run_all.py` 다.

- FDC 2026-09 전체(2,101,279 항목) + ProMENDA(Pu et al. 2024) + KEGG/NCBI 재조회
- RDF 3,166,603 triple / 음식 14,719 / compound 130 / 음식당 측정 compound 중앙값 47
- 추천 Bottom 30 은 논문 §4.2.3(소시지·소고기류)과 일치, Top 30 은 부분 일치
- §5.1 방법 2 자동 문헌검증 4/15 (논문 11/15)

상세·설계 결정·한계는 `ourkg/README.md`.

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
