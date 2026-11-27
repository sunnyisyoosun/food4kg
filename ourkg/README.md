# ourkg — 최신 공개 데이터로 다시 만든 Food4healthKG

Fu et al. (2023) *Food4healthKG* 의 **구축 방식과 평가 방식을 그대로 쓰되**,
데이터를 지금의 공개본으로 바꿔 우리 지식그래프를 **다시 만들고 축을 넓힌다**.

레포 루트의 `reconstruct.py` → `run_recommendation.py` 경로는 다른 트랙이고
이 디렉토리와 **섞지 않는다**. 수치는 [`REPRODUCTION.md`](../REPRODUCTION.md),
미해결은 [`PROBLEMS.md`](../PROBLEMS.md).

> **이름에 대해.** 이 디렉토리를 "재현" 이라 부르지 않는다 — 논문이 고정한
> 135 음식 · 85 compound 를 쓰지 않고 FDC 전체로 다시 만들기 때문이다.
> "개선" 이라 부르지도 않는다 — 측정한 변경의 **대부분이 기각**됐고 추천 순위는
> 축을 162 → 791 종으로 늘려도 바뀌지 않았다. 개선이 입증된 곳은 **데이터 구축
> 축**(커버리지 · 출처 추적 · 정합성)이다. 루트 트랙도 그냥 "재현" 이 아니라
> **역설계 + 부분 재현**이다 — 논문이 적지 않은 변환 규약을 우리가 결과를 보고
> 골랐다. 자세한 근거는 [`METHODS.md`](METHODS.md) §0.

### 문서 네 개를 이렇게 나눠 뒀다

| 문서 | 무엇이 있나 | 언제 보나 |
|---|---|---|
| **이 문서** | 전체 지도 · 실행법 · 설계 결정 요약 | 처음 볼 때 |
| [`DATA.md`](DATA.md) | 축별 **출처·받는 법·뽑은 것·함정** (출처 링크 표 포함) | "이 숫자 어디서 왔나" |
| [`METHODS.md`](METHODS.md) | 전제 · 구축 · 추천 · **평가 자 9 개** · 정합 검사 | "어떻게 쟀나" |
| [`RESULTS.md`](RESULTS.md) | 실험 §1~§42 과 **기각 기록** (시간순) | "왜 그렇게 정했나" |
| [`PROCESS.md`](PROCESS.md) | **절차에서 틀린 것들** — 무엇이 틀렸고 어떻게 드러났고 무엇으로 막았나 | "이거 믿을 수 있나" |
| [`PERSONALIZE.md`](PERSONALIZE.md) | **개별 추천 계획** — KNHANES × ourkg. 아직 측정 전이다 | "다음에 뭐 하나" |

---

## 지금까지 찾은 것 세 가지

문서가 길어서 결론부터 적는다. 셋 다 **측정된 것**이고 근거가 `RESULTS.md` 에 있다.

**1. 추천 점수를 만드는 것은 음(−)의 유사도다.**
`D = E × Fᵀ` 에서 `E × Fᵀ` 는 사실상 기여하지 않는다 — `P` 와 `D` 의 Top/Bottom 30
교집합이 **0/30** 이다. 1 위 음식 점수의 **123% 가 음수×음수**에서 온다. "야채주스가
1 위인 이유는 버터와 성분 구성이 반대여서" 다. 이 하나가 `E` 를 고치려던 모든 시도
(NHANES · 미생물 가중 · 희소화)가 왜 실패했는지를 설명한다 → §14·§17

**2. 미생물 축은 추천에 닿지 않고, 방향 신호도 없다.**
논문 식 (1)(2) 에 미생물이 들어갈 자리가 없다. 축을 485 → **798 종**으로 늘리고
링크를 10,257 → **14,918** 로 늘려도 `recommendation.csv` 가 **한 줄도 바뀌지 않았다**(재실행으로 확인).
방향 신호는 세 번 기각됐다 — 구조(§15c) · 재료(§31·§32) · 인과 방향(§33).
검정력 반론까지 재 봤다(§34).

**3. 논문 §5.2(방법 2) 는 품질 지표로 쓸 수 없다.**
우리 추론 15 건이 **15/15 전부 통과**하는데 그중 11 건이 합병증 추론이고 질의가
질환 두 개뿐이라 **잘 알려진 동반이환을 확인할 뿐**이다. 쓸 수 있는 것은 논문
15 건과의 일치(**12/15**)뿐이다 → §18·§28

---

## 논문과 달라진 것

| 축 | 논문 (2023) | ourkg |
|---|---|---|
| 음식·성분 | FDC 34,250 샘플 (2022) | FDC 전체 **2,101,279 항목** (2026-09 배포본) → 병합 475,769 |
| 우울증-대사물 | MENDA 5,675 관계 | **ProMENDA** (Pu et al. 2024) 22,519 레코드 / 995 연구 |
| compound | KEGG 230 metabolite | KG 층 154 / **F 층 135** — 논문처럼 두 층을 나눈다 |
| 미생물 | NCBI taxonomy 322,917 | efetch 로 **현재 값** 갱신 **791 종** (요청 798 taxid = 배포본 127 + Disbiome 333 + **gutMDisorder 309** + 보탠 29, 그중 7 쌍이 병합 전/후 id 로 중복) |
| compound-미생물 | KEGG (2022) | KEGG REST 재계산 **고유 쌍 14,918<!--chk:links.unique-->**(종 6,439<!--chk:links.species--> · 속 8,626<!--chk:links.genus--> 주장) + **VMH/AGORA2 46,495<!--chk:links.vmh-->**(예측) + **측정 상관 39,574<!--chk:links.measured-->**(관측) |
| 미생물-질환 | MiKG 1,234 | MiKG 406 + **Disbiome 1,193** + **gutMDisorder 1,239** — 외부 큐레이션 **둘**을 쌍 단위로 맞춰 본다 |
| 질환 분류 | MeSH + SNOMED CT | MeSH SPARQL — tree number + 상위 계층 **242 종**. SNOMED 는 MiKG xref 63 |
| 식품 온톨로지 | FoodOn + 중국 온톨로지 | **FoodOn 을 EBI OLS 에서 직접** — 음식 8,165 · 클래스 1,096. 중국 온톨로지는 배포 subset |
| 외부 검정 | 없음 | 프로바이오틱스 RCT · 분변 대사체 13 코호트 · NHANES · 식이 중재 · ModiMedDiet RCT |

**compound-미생물 링크는 성격이 셋이고 섞지 않는다** — KEGG 는 유전체 효소
**추론**, VMH/AGORA2 는 유전체 재구성 **예측**, 분변 대사체 코호트는 **관측**이다.
KG 에서 출처 태그로 갈라 둔다.

---

## 실행

**`.venv` 를 켜야 한다** — 설치는 [루트 `README.md`](../README.md) 의 설치 절.

```bash
source .venv/bin/activate

python3 ourkg/run_all.py                  # 구축 → 분석 → 외부 검정 → 설정 쓸기 (전부)
python3 ourkg/run_all.py kg recommend     # 일부만
python3 ourkg/run_all.py --env            # 환경변수 전수 (소스에서 긁어 온다)

python3 ourkg/analyze.py recommend        # 분석 한 단계만
python3 ourkg/sweep.py emode              # 설정 쓸기 하나만
python3 ourkg/tests.py                    # 함수 단위 시험 + 메타 시험 (83 개, 0.9 초)
python3 ourkg/check.py                    # 산출물·문서 정합 검사 (16 항목, 네트워크 없음)
```

**무언가 고친 뒤에는 `check.py` 를 돌린다.** 산출물이 조용히 어긋나는 것을
막으려고 둔 것이고, 실패가 있으면 exit 1 이다. 무엇을 검사하고 왜 그것을
검사하는지는 [`METHODS.md`](METHODS.md) 의 검사 절, **그 검사가 어떤 사고를
막는지는** [`PROCESS.md`](PROCESS.md) 에 있다.

전체를 처음부터 다시 만들려면 `python3 ourkg/run_all.py` — 24 단계 약 50 분이다.
**단계별로만 돌리면 드러나지 않는 결함이 있다** (설정이 쓸기 사이로 새던 버그를
전체 실행으로 처음 찾았다, `PROCESS.md` 2.6).

### 커밋 전 검사를 자동으로 — 레포마다 한 번

```bash
git config core.hooksPath hooks     # hooks/pre-commit 을 켠다
```

`hooks/pre-commit` 이 커밋 때마다 `tests.py` → `check.py` 를 돌리고 **하나라도
실패하면 커밋을 막는다**(합쳐 약 2.5 초). 훅을 `.git/hooks/` 가 아니라 레포의 `hooks/` 에 두는 이유는 git 이
`.git/hooks/` 를 추적하지 않아 **받는 사람에게 안 따라가기** 때문이다.

의도한 상태를 커밋해야 하면 `SKIP_OURKG_CHECK=1 git commit ...` 또는
`git commit --no-verify`.

위 `git config` 를 안 쳤으면 `check.py` 의 `hooks` 검사가 FAIL 로 알려 준다.
git 은 클론 시 훅 자동 활성화를 보안상 막으므로 **강제할 수는 없다** — 훅을 안
켠 사람의 첫 커밋은 못 막는다. 훅을 쓰지 않기로 했으면 `OURKG_NO_HOOK_CHECK=1`.

### 미리 받아 둬야 하는 것 넷

용량이나 수동 승인 때문에 실행 중 받지 않는다. 나머지(KEGG · NCBI · MeSH ·
FoodOn · Disbiome · gutMDisorder · NHANES …)는 **실행 중 재조회**하고
`ourkg/cache/` 에 캐시한다. 받는 주소는 [`DATA.md` 출처 링크 표](DATA.md)에 있다.

| 경로 | 내용 |
|---|---|
| `fdc_raw/food.csv` · `food_nutrient.csv` · `nutrient.csv` | FDC Full Download (CSV) |
| `fdc_raw/survey_fndds_food.csv` · `wweia_food_category.csv` | FDC survey 배포본 — 없으면 FNDDS 545 종이 Unclassified 가 된다 ([survey zip](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_csv_2024-10-31.zip)) |
| `41398_2024_2948_MOESM3_ESM.xlsx` | ProMENDA ([Pu et al. 2024 보충자료 2](https://www.nature.com/articles/s41398-024-02948-2)) |
| `foodkg_triply/` · `MiKG-JAIMS/` | 논문 배포본 · MiKG (git clone — 루트 `README.md` §2) |

---

## 코드 지도

각 단계는 **앞 단계의 CSV 만 읽는다** — 따로 돌려도 된다.

### 구축 — `build.py`

| 단계 | 하는 일 | 주요 산출물 |
|---|---|---|
| `food` | FDC 2,700 만 행 스트리밍 → 단위 g 환산 → §3.2 라벨 병합 → 카테고리 정규화 | `foods.csv`, `food_compound_long.csv` |
| `form` | FDC 측정값에서 구조·가공 축 19 개 (F 확장) | `food_form.csv` |
| `promenda` | ProMENDA → compound 별 우울증 극성 `E` | `compound_depression.csv` |
| `evidence` | 근거 4 종(ProMENDA·MENDA·재현 규칙·AFS)으로 `E` 구성 6 가지 | `compound_evidence.csv` |
| `microbe` | MeSH tree → NCBI taxonomy → KEGG organism → compound 링크. **Disbiome · gutMDisorder** 적재 | `microbes.csv`, `compound_microbe.csv`, `microbe_disease*.csv` |
| `kg` | §3.3 표현 규약대로 RDF 출력. 근거와 **방향 합의**도 함께 싣는다 | `ourkg.nt`, `kg_stats.csv` |

### 분석 — `analyze.py`

| 단계 | 하는 일 | 주요 산출물 |
|---|---|---|
| `recommend` | 논문 Algorithm 1 (식 1·2) | `recommendation.csv`, `.png` |
| `compare` | `E` 구성 방식·경로를 §4.2.3 기준으로 대조 | `e_mode_comparison.csv` |
| `external` | SMILES trial **ModiMedDiet** 로 외부 정답셋 | `modimed_labels.csv` |
| `invert` | 그 라벨로 `E` 부호를 역추정해 공개 소스와 대조 | `compound_learned.csv` |
| `stype` | ProMENDA 를 연구 설계별로 쪼개 `E` 를 만들고 채점 | `stype_comparison.csv` |
| `emicrobe` | 미생물 방향에서 **독립된 `E`** 를 유도해 대조 (BH 보정) | `e_microbe_compare.csv` |
| `groups` | 논문 Fig 4(c) 성분군 조성 | `group_composition.csv` |
| `disagree` | 두 평가 기준이 갈리는 지점을 음식군별로 분해 | `disagreement_by_group.csv` |
| `pathcheck` | gut-brain compound 를 CSV 와 KG(SPARQL)에서 각각 뽑아 대조 — 현재 **78/78 일치**. 판정을 json 에 적고 `check.py` 가 본다 (§38) | `gutbrain_compounds.json` |
| `evaluate` | §4.1 SPARQL Q1~Q3 · §5.1 방법 1·2 | `eval_*.csv/json` |

### 외부 검정 — 우리 결과를 **우리 밖의 자**로 잰다

| 파일 | 자 | 결과 |
|---|---|---|
| `probiotic_rct.py` | 프로바이오틱스 RCT 203 편 → 25 종 | 커버리지 **21/25** 합격 · gut-brain 가정은 약함 |
| `metabolome_check.py` | 분변 대사체 13 코호트 (관측) | KEGG/VMH 링크와 측정 상관이 **무관** |
| `nhanes.py` | NHANES 2017-18 섭취 → PHQ-9 | `E_MODE=nhanes` 선택지. 기본값 아님 |
| `diet_intervention.py` | gutMDisorder **식이 중재** (인과 방향) | 미리 고정한 예측 **1/2 실패** → §33 |
| `e_autism.py` | KANG 코호트로 **자폐 `E`** 를 측정에서 | 검정력 반론을 재 봤다 → §34 |

### 지표와 쓸기

| 파일 | 하는 일 |
|---|---|
| `sweep.py` | 설정 쓸기 15 종 (`emode` `fcolumns` `gutbrain` `simthr` `fscale` `dedup` …) — 두 기준으로 채점 |
| `bootstrap.py` | Top-K 지표의 **표집 변동** (주지표 선정 근거) |
| `consensus.py` | **합의 Top-K** — 부분표집에서 반복 선택되는 음식 |
| `complication.py` | **논문 §3.3 합병증 추론** — 검정 전에 입력의 판별력(집합 포개짐)을 먼저 재고, 포개지면 **돌리지 않는다** (§41) |
| `toperr.py` | Top-K **규칙 기반 오류 수** (외부 임상 · 섭취량 · 분말 · 시럽) |
| `tests.py` | **함수 단위 시험 + 메타 시험** — 식 (1) 의 네 선택 · 조용히 깨졌던 규칙 · **검사기 자체** (83 개, 0.9 초) |
| `check.py` | **정합 검사** — 산출물·문서가 서로 맞는지 네트워크 없이 **16**<!--chk:check.names--> 항목 |
| `foodon_match.py` | FoodOn 매칭 (EBI OLS) |
| `common.py` | 경로 · 단위 환산 · 라벨 정규화 · **읽는·돌리는 자리 통합**(`compound_microbe` · `measured_links` · `microbe_disease_direction` · `depression_e` · `taxid_alias` · `recommend_under`) |
| `run_all.py` | 위를 순서대로. `--env` 로 환경변수 전수 |

---

## 결과

### KG 규모 (논문 Table 1 대응)

**고유 triple 3,497,295<!--chk:kg.triples--> · 관계 42<!--chk:kg.relations--> · 엔티티 859,544<!--chk:kg.entities-->** (논문 13,346,991 · 140 · 1,637,915)

| source | relation | entity | triples |
|---|---:|---:|---:|
| FoodData Central | 9 | 794,404 | 3,206,541 |
| Chinese Food Ontology | 3 | 49,865 | 82,542 |
| VMH/AGORA2 | 1 | 1,192 | 46,495<!--chk:links.vmh--> |
| FoodOn/OLS | 3 | 10,452 | 25,759 |
| FoodOn | 4 | 6,592 | 21,723 |
| 측정 상관 | 2 | 733 | 31,824 |
| KEGG | 5 | 3,092 | 13,112 |
| KEGG(속 수준) | 1 | 398 | 8,626<!--chk:links.genus--> |
| MiKG | 9 | 1,306 | 7,196 |
| MeSH | 2 | 245 | 5,400 |
| ProMENDA | 6 | 1,289 | 5,150 |
| NCBI taxonomy | 6 | 1,207 | 3,740 |
| gutMDisorder | 3 | 517 | 3,717 |
| 방향 합의 | 3 | 761 | 3,183 |
| MeSH tree | 2 | 628 | 3,118 |
| Disbiome | 2 | 476 | 2,386 |
| evidence | 15 | 278 | 1,560 |
| SNOMED CT | 2 | 294 | 285 |
| Σ 출처 주장(겹침 포함) | 39 | 859,544 | 3,517,015<!--chk:kg.claims--> |
| **Total (고유 그래프)** | **39** | **859,544** | **3,497,295**<!--chk:kg.triples--> |

**두 줄을 따로 적는 이유** — RDF 그래프는 같은 statement 를 두 번 갖지 않으므로
그래프 크기는 **고유** 기준이다. 출처 열은 '그 출처가 주장한 수' 라서 겹치는
만큼 합이 그래프보다 크다(19,720<!--chk:kg.overlap-->). 겹침은 버릴 정보가 아니다 — VMH 와 KEGG 가
같은 `hasMetabolites` 1,435 건을 독립적으로 주장하는 것은 **서로 교차검증**이다.
논문 Table 1 과 비교할 때는 고유 쪽을 쓴다.

논문과의 격차는 거의 전부 **온톨로지 축을 통합하지 않은 데서** 온다 — SNOMED CT
429 만(배포되지 않음) · NCBI taxonomy 131 만(정신질환 연관 종만 쓴다).
**음식-성분 축만 보면 우리 쪽이 더 크다**(321 만 vs 233 만)고, FoodOn 도 OLS 에서
직접 받아 141,564 triple 로 논문(79,769)을 넘었다.

논문에 대응이 없는 축 둘:
- **`evidence`** — `E` 의 근거와 결합값을 KG 안에서 추적하려고 넣었다 → §5
- **`방향 합의`** — 미생물 존재비 **방향**을 출처별로 올리지 않고 (균, 질환) 쌍
  단위로 합의를 본 뒤 올린다. 두 큐레이션 소스의 방향 일치가 **48.4%(우연 아래)**
  이라서다 → §32

규모: 음식 **14,886<!--chk:foods.count--> 종**(음식당 측정 compound 중앙값
**48**<!--chk:foods.median_compounds-->, 논문 heatmap 원본 33) · F 층 compound
**135**<!--chk:F.compounds--> · `E` 가 비영인 compound
**1,287**<!--chk:E.nonzero-->(ProMENDA 1,412<!--chk:E.compounds--> 중).

### 추천 (depression, Top/Bottom 30)

추천 코호트는 분석 측정 데이터 **12,420<!--chk:rec.rows--> 음식**이다.

| | ourkg | 논문 §4.2.3 |
|---|---|---|
| **Top 30** | 채소 10 · 과일·주스 10 · 음료 3 · 수프 2 · 어패류 1 … | "mainly fish and shellfish products, as well as **fruits and vegetables**" |
| **Bottom 30** | 소고기 16 · 소시지·런천미트 6 · 돼지고기 4 · 가금 2 · 이유식 2 | "sausage products, baked products, and sweets" / 피라미드 상단 "**beef products, sausages, and luncheon meats**" |

Top 10: 야채주스 / 오렌지주스(칼슘 강화) / 게맛살 / FUZE 오렌지망고 /
맥도날드 베이컨랜치 샐러드 / 오렌지주스 100% / 과일주스 / 갓(냉동, 조리) /
로메인 상추 / 카라멜 딥(라이트).

**양쪽이 §4.2.3 서술과 맞는다.** 예전 판은 Top 30 을 칵테일·당류가 차지했는데,
그건 `F` 를 논문 §4.2.1 대로 **우울증 연관 compound 로 제한하기 전**의 결과였다
(설계 결정 #6). 다만 상위에 주스·딥이 섞이는 것은 남아 있다 — 규칙 기반으로 세면
Top 30 오류 **1/30** 이다(`toperr.py`. 표의 다른 설정은 `toperr.py` 가
다른 이름(`effect+nhanes` 등)으로 재서 같은 행에 올리지 않았다).

채점은 두 기준으로 한다 (`sweep.py emode`):

| 설정 | Bot30 비추천군 | Top30 위반 | Top30 추천군 | MMD 처방군 | MMD extras | Top-K 오류 |
|---|---:|---:|---:|---:|---:|---:|
| **`shrunk` (기본값)** | **26** | **0** | 21 | **24** | **1** | **1/30** |
| `binary` (논문 §4.2.1 그대로) | 19 | 0 | 20 | 23 | 3 | — |
| `nhanes` | 5 | 0 | 10 | 14 | 7 | — |
| `learned` (ModiMedDiet 역추정) | 18 | 13 | 9 | 30 | 0 | — |

**AUC 는 주지표가 아니다** — AUC 가 가장 높은 설정의 Top 30 이 처방 0 / extras 18
이고 1 위가 술이다. 그래서 Top-K 로 바꿨다 → §13. 불안정은 **합의 Top-K** 로
따로 잰다(`consensus.py`) — 기본값이 60 회 부분표집에서 top-rate 중앙값 0.825 다.

### §5.1 방법 1 — Supplement Table 1 의 20 문항

전문가 3 인이 없으므로 논문의 정확도 0.95/0.90/0.95 자체는 재현 대상이 아니다.
**두 가지를 따로 센다** — 논문의 답을 재현하는가(`재현`), 우리 KG 가 그 측면을
답할 축을 갖췄는가(`타당`).

| | O | △ | X |
|---|---:|---:|---:|
| 논문 답 **재현** | **14** | 4 | 2 |
| 우리 KG 의 **타당성** | **12** | 5 | 3 |

측면 6 개(중량 계산 3 · compound 분류 3 · 음식·장내 compound 4 · 세균 분류 3 ·
음식 분류 4 · 질환 분류 3)에 모두 답할 축이 있다. 산출물 `eval_method1.csv`.

### §5.1 방법 2 — 추론 15 건 문헌 검증 (**지표로 쓰지 않는다**)

논문은 수작업 PubMed 검색으로 11 confirmed / 3 unknown / 1 contradicted 를 보고한다.
우리는 **초록 판독까지** E-utilities 로 자동화했다 — 두 엔티티가 **한 문장에** 함께
나오고 연관 표현이 있으면 +1, 부정 표현이면 −1.

판정 기준이 논문에 없으므로 같은 자를 **논문 자신의 15 건에 적용해** 판별력을 쟀다
(`eval_method2_calibration.csv`):

| 기준 | confirmed 통과 | non-confirmed 통과 | 균형정확도 |
|---|---:|---:|---:|
| 색인 3 항 공출현 | 1/11 | 0/4 | 0.55 |
| 색인 2 항 공출현 | 10/11 | 3/4 | 0.58 |
| **초록 판독 (현재)** | **11/11** | **2/4** | **0.75** |

색인 공출현 두 자는 버렸다 — 3 항은 신호가 없고, 2 항은 `Anxiety AND depression`
이 19 만 건이라 "두 주제가 함께 연구되는가" 를 잴 뿐이다.

**논문 15 건과의 일치는 12/15.** 위양성을 줄이는 수정을 여섯 번 넣었다(온전한 단어
매칭 · 식이 맥락 요구 · `inbreeding depression` 류 제외 · `Case Reports` 제외 ·
여러 단어는 구(句)로 · 인용문은 매치 주변). 그래도 **우리 15 건은 15/15 로 전부
통과**해서 **판별력이 없다** — 그래서 방법 2 는 품질 지표가 아니라 **검수 도구**로
쓴다. 모드·설정 선택에는 §4.2.3 서술과 ModiMedDiet 을 쓴다 → §18·§28

---

## 평가 기준 둘, 그리고 충돌

- **논문 §4.2.3** — 논문이 자기 알고리즘 출력을 서술한 문장. 재현·대조용.
- **ModiMedDiet** ([Jacka et al. 2017 SMILES trial](https://doi.org/10.1186/s12916-017-0791-y))
  — 우울증 RCT 에서 **실제로 처방된** 식단. 출처가 독립인 외부 기준.

**갈라지는 축은 붉은 고기 하나다.** §4.2.3 은 비추천으로 두지만 ModiMedDiet 은
lean red meat 를 주 3~4 회 처방한다. 크기를 쟀다 — `separable lean only` 로 표기된
소·돼지고기가 **500 종**(논문 비추천 3,555 중 14%)이고, 설정에 따라 Bottom 30 을
**0~25 개** 차지한다. **어느 한쪽을 고르지 않고** `sweep.py` 에 `bot30_충돌(살코기)`
열을 두어 드러낸다 → §29

처방 **빈도**(채소 6 회/일 vs 붉은 고기 주 3~4 회)를 반영하면 두 기준의 간극이
0.209 → 0.039 로 거의 사라지고 기본값이 공개 소스 설정 중 최고가 된다 → §11 D

**왜 반대 방향이 나오는지도 쟀다.** ProMENDA·MENDA 는 "우울증 환자에서 대사물
**농도**가 높/낮다" 를 재는 case-control 메타볼로믹스고, 논문 §4.2.1 의 `E` 는
"**먹으면** 완화/악화" 로 정의된다. 논문은 둘을 동일시한다 — **부호 일치 48%** 가
그 가정의 측정값이다 → §8

---

## 설계 결정

**전부 실행 전에 고정했고, 결과를 보고 고르지 않았다.** 각 항목은 환경변수로
되돌릴 수 있다. 근거와 수치는 `RESULTS.md` 의 해당 절에 있다.

| | 결정 | 되돌리기 | 왜 |
|---|---|---|---|
| 1 | 단위 **g 환산** | `UNIT_MODE` | §3.1 "quantified in weight". `nutrient.csv` 가 정본 — 매핑표만 보면 mg 를 g 로 쓴다 |
| 2 | **라벨 병합** (콤마 분리 + 정확 일치) | — | §3.2 그대로. 2,101,279 → 475,769 |
| 3 | 음식당 **최소 compound 20** | `MIN_COV` | 성분 1~2 개로는 유사도가 성립하지 않는다. **열 쪽에는 하한을 두지 않는다** — 희소한 열 18 개도 신호를 갖고 있었다 → §4.3 |
| 4 | `E` 의 **근거 축소** `(pos−neg)/(pos+neg+K)`, `K=10` | `E_MODE=binary`·`sig` | ProMENDA 가 MENDA 보다 커서 연구 2~3 건도 다수결로 ±1 을 받는다(Ethanol 이 4:1 로 +1 → 칵테일이 Top 30). `K` 민감도는 **10·20 에서 평탄한 꼭대기** → §5 |
| 5 | **성분(열)별 정규화** | `NORM=row_minmax` | 공식 `final.py` 의 행별 min-max 는 음식 135 종에선 되지만 14,000 종에선 무너진다. 열별은 Fig 4(c) 문장을 근거로 한다 |
| 6 | **`F` 를 우울증 연관 compound 로 제한** | `F_COLUMNS=all` | §4.2.1 의 `F` 정의 그대로. 제한하면 §4.2.3 추천군이 7 → **22** → 이 결정 하나가 Top 30 을 칵테일에서 채소·과일로 바꿨다 |
| 7 | **PCA 를 끈다** | `PCA_COMPONENTS=5`·`auto` | 논문 **본문**은 PCA 를 쓰라고 하지만, 켜면 Top 1 이 칠면조 껍질·크림 리큐어가 되어 논문 **결과**(§4.2.3)에서 멀어진다. 본문과 결과가 어긋나 **결과 쪽을 따랐다** → §12·§13 |
| 8 | Algorithm 1 의 **`Threshold` 를 걸지 않는다** | `SIM_THRESHOLD` | 네 방식으로 구현했는데 어떻게 잘라도 Top 1 이 술이 되고 추천군이 22 → 0~1 로 무너진다. 추천을 만드는 것이 **음의 유사도**이기 때문이다 → §14 |
| 9 | 식 (2) 에 **정규화 없음** | `SIM_NORM=colsum` | 공식 `final.py` 는 `p[i] /= sum(S[:,i])` 를 덧붙이는데 식 (2) 에 없다. adjusted cosine 은 음수라 열합이 0 근처가 되어 점수를 폭발시킨다 |
| 10 | 추천 코호트를 **분석 측정 데이터로** | `DATA_TYPES=all` | §4.2 의 135 음식은 전부 Foundation/SR Legacy/FNDDS 다. branded 는 라벨 신고값이라 결측이 많아 탄산수·파우더가 상위를 차지한다. **KG 자체는 FDC 전체를 담는다** |
| 11 | **서빙 기준 `F` 를 쓰지 않는다** | `F_SCALE=serving` | g/100g 이 향신료(1 회 4.2 g)와 수프(215.5 g)를 같게 본다는 지적은 맞다. 그런데 서빙으로 바꾸면 비추천군이 26 → 2 로 붕괴한다(제과·스낵도 같이 눌린다) → §15e |
| 12 | **앙상블·`union_all` 을 기본값으로 쓰지 않는다** | `ENSEMBLE`·`E_MODE` | 한때 둘로 바꿨는데 **내 질적 판단이 두 번 다 틀렸다**. 규칙 기반으로 세니 앙상블이 6/30 오류 vs `shrunk` 1/30 이었다. 되돌리고 실패를 §27 에 남겼다 |

---

## 알려진 한계

**데이터로 닫히는 것** (할 일이 아니라 한계다 → §30)

- **중국 식품 온톨로지는 배포 subset 만** — 카테고리 39 · 음식 174. FoodOn 은
  OLS 에서 직접 받아 음식 8,165 · 클래스 1,096 을 붙였다.
- **SNOMED CT 는 라이선스** — 배포본에 라벨·계층이 없다(id 284 개뿐). 질환 상위
  분류는 **MeSH 트리로 대체**했다. #12(Mood/developmental 상위 분류)는 **공개 KG 도
  답하지 못한다**.
- **논문 §3.3 의 474 만 추론을 재구현하지 않았다** — 전이 추론과 공통 세균 추론만.
  그리고 공통 세균 추론은 **정보가 없다**(45/45 쌍이 통과, 논문 대표 쌍 p=1.0) → §18·§49

**미생물 축 — 넓혔지만 추천에 닿지 않는다**

- 162 → **791 종**. 넓히는 기준이 "우리가 아는 균" 이라 **스스로를 가두던 구조**를
  외부 큐레이션(Disbiome · gutMDisorder v3)으로 끊었다. 닿는 균이 적던 문제
  (KEGG organism 167/485)는 **종 → 속 사다리**로 **569<!--chk:microbe.kegg_org-->/798<!--chk:microbe.ids-->** 로 고쳤다.
- **속 수준을 종 수준과 섞어 읽으면 과대평가다** — KEGG 링크의 **58%**가 속 수준
  매칭이고 "이 속의 **어떤** 유전체가" 라는 더 약한 주장이다. compound 연결은
  **종 수준 257 종(32%) · 속 포함 565 종(71%)** 으로 갈라서 읽는다. 읽는 자리는
  `common.compound_microbe(sources, rank)` 하나로 합쳤고 평가 어댑터는 종 수준만
  쓴다. KG 는 `KEGG` / `KEGG(속 수준)` 으로 출처를 가른다.
- 아직 못 잇는 226 종은 과 74 · 속 63 · 목 36 · 종 24(KEGG 에 유전체 없음) ·
  강 16 · 문 12 다.
- **두 큐레이션 소스가 방향에서 안 맞는다** — 공유 (균, 질환) 쌍 128 개 중 일치가
  **62(48.4%)로 우연 수준**이다(자폐는 9:26). 그래서 방향은 쌍 단위로 합의를 본
  뒤에만 올리고, 모순 쌍은 버리지 않고 `our:abundanceConflict` 로 담는다 —
  "연관은 있고 방향은 모른다" 가 우리가 아는 것이다 → §32
- **외부 소스는 폐기된 NCBI taxid 를 들고 있다** — Disbiome 의 *Klebsiella* 는
  160674, gutMDisorder 는 570 인데 NCBI 에서 둘 다 570 이다. 요청 id 로도 적재해
  **잃지 않고**, 정체성은 정본 taxid 로 모으고 원 id 는 `our:akaTaxid` 로 남긴다
  (`common.taxid_alias`). 안 모으면 같은 균을 두 번 세고, 두 소스가 서로 다른
  균으로 보여 방향 교차검사에서 7 균이 빠진다 → §35

**측정이 남긴 열린 문제**

- **음식 하나가 FDC 레코드 여러 건의 평균이고, 라벨은 그 값을 설명하지 않는다** —
  2 건 이상을 평균한 음식이 **2,731**<!--chk:food.multi_source--> 개(최대
  **2,456**<!--chk:food.source_max--> 건)이고, 그중 **570**<!--chk:food.label_minority--> 개는
  `data_type` 라벨이 출처의 **소수**다(`Ice cream, NFS` 는 0.04%). 라벨은 큐레이션
  등급이 높은 쪽을 고르므로 값의 출처를 **과대평가**한다. 대표 선택 규칙은 두고
  `n_source`·`source_types`·`label_share` 를 산출물과 KG 에 남겼다 → §50

- **`E` 의 95% 가 추천에 닿지 않는다** — 실제 점수 축은 `F ∩ E` = **73 compound**
  이고 ProMENDA 의 1,412 중 나머지는 FDC 가 그 대사물을 측정하지 않아 영향을 줄 수
  없다. 미생물 쪽 커버리지는 그 73 중 61(84%)로 넉넉하다 — **좁은 쪽은 반대편**이다.
- **소스 간 방향 일치의 배제 범위는 좁다** — 공유 쌍 **128**<!--chk:power.agree.n--> 개에서
  일치 0.484 로 우연 아래지만, 이 `n` 으로 80% 검정력으로 잡히는 것은
  **0.609**<!--chk:power.agree.mdes--> **이상**이다. 즉 *일치율이 55% 다* 를 배제하지
  못한다. 경계를 조이려면 소스를 늘리는 게 아니라 **같은 (균, 질환) 을 둘 이상이
  말한 쌍**이 늘어야 한다 → §46
- **합병증 문헌 lift 는 경계에 걸쳐서 검출됐다** — 통과 129 vs 비통과 336 의
  AUC **0.574**<!--chk:power.auc.obs-->, p=0.0068. 그 군 크기의 80% 검정력 경계가
  **0.575**<!--chk:power.auc.mdes--> 다. 유의하지만 **이보다 작은 효과는 놓쳤을 수
  있다** — "약하다" 에 숫자가 붙었다 → §46
- **부호일치 검정의 우연 수준은 0.5 가 아니었다** — 양쪽 부호가 치우쳐 있어
  (`E_shrunk` 양수 0.368 · `E_microbe` 양수 0.177) 무작위로 짝지어도 58.5% 맞는다.
  0.5 에 대고 재서 p=4.9e-5 를 **신호로 읽을 뻔했다**(올바른 중심에서는 0.075,
  BH 후 0/28). 순열로 귀무를 만들고 경계도 그 중심에서 낸다 → §48
- **검정력 반론은 닫히지 않지만 경계가 있다** — 처음엔 "닫지 못했다" 로 적었는데
  **그 서술이 과했다.** 돌린 부호일치 검정 **52**<!--chk:power.rows--> 개의 `n` 과
  **각 행의 귀무**로 최소검출효과를 계산하면(`out/analysis/power_bound.csv`), 귀무 위
  초과분이 가장 작은 자리가 `n`=**377**<!--chk:power.n--> · 귀무
  **0.524**<!--chk:power.null--> 이고 거기서 **0.620**<!--chk:power.mdes-->
  **이상인 효과는 배제된다** — 있었으면 잡혔다(자기 경계를 넘은 관측
  **0**<!--chk:power.over-->). 귀무~경계는 열려 있고, 그건 *모른다*가 아니라
  **경계가 있는 모름**이다.
  그리고 그 구간은 쓰면 손해인 크기다 — α 를 키울수록 비추천군이 26→20 으로 단조
  감소한다. 남은 공백은 데이터다: 미생물이 두텁고 `E` 가 넓은 질환이 공개 데이터에
  없다 → §34
- ~~합병증 추론 검증에는 외부 −1 정답셋이 필요하다~~ → **그 진단이 틀렸다.**
  ① Cochrane "no evidence" 는 *치료 효과*에 근거가 없다는 뜻이지 *동반이환이
  없다*는 뜻이 아니다. ② 정신질환 안에는 자연적으로 −1 이 없다 — 덴마크 전국
  레지스트리(590 만 명)가 "동반이환 증가는 예외가 아니라 규칙" 이라고 결론한다.
  ③ **라벨 없이 답이 나왔다**: 10 질환이 universe 48 을 나눠 갖는데 3 개가 전부를
  갖고 있어 겹침이 작은 쪽 크기와 같다(포개짐 88.9%) — p 값이 구조적으로
  보장된 것이다. `complication.py` 가 **특이성을 먼저 재고 포개지면 검정을
  돌리지 않는다**. 소스를 Disbiome·gutMDisorder 로 바꾸면 포개짐이 0.9% 로
  떨어지고 **~28% 만 통과**한다 — 판별이 일어난다.
  그리고 **−1 정답셋은 논문 자신이 주고 있었다** — Table 5 합병증 8 문항 중
  2 개가 논문 판정 `0` 이다. MiKG 경로로는 8/8 을 통과시켜 둘 다 위양성이었는데,
  `curated` 로는 **잴 수 있는 6/6 이 일치**하고 논문이 0 으로 둔
  **파킨슨–자폐가 q=1.00 으로 기각**된다(공유 143, 기대 160.8) → §41

---

## 산출물

`out/` 의 결과표·평가 결과는 **레포에 함께 올라가 있다**(리뷰용). 대용량 둘만
제외한다 — `ourkg.nt`(470 MB) · `food_compound_long.csv`(48 MB).
`python3 ourkg/run_all.py` 로 재생성한다. 파일별 내용은
[`RESULTS.md`](RESULTS.md) §8.
