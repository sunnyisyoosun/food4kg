# ourkg 결과 정리

논문 Fu et al. (2023) *Food4healthKG* 의 **구축 방식과 평가 방식**을 그대로 쓰고,
데이터를 최신 공개본(FDC 2026-09 전체 + ProMENDA 2024 + KEGG/NCBI/MeSH 현재 조회)으로
바꿔 **다시 만들고 축을 넓힌** 결과다.

루트의 `reconstruct.py` → `run_recommendation.py` 트랙과는 **분리된** 산출물이다
(두 트랙을 왜 "재현"·"개선" 이라 부르지 않는지는
[`METHODS.md`](METHODS.md) §0).

| 찾는 것 | 문서 |
|---|---|
| 이 문서 — **실험과 기각 기록** (절 번호로 인용) | `RESULTS.md` |
| **절차에서 틀린 것들** — 무엇이 틀렸고 어떻게 드러났고 무엇으로 막았나 | [`PROCESS.md`](PROCESS.md) |
| 데이터 출처·받는 법·함정 | [`DATA.md`](DATA.md) |
| 전제·구축·추천·평가 자·정합 검사 | [`METHODS.md`](METHODS.md) |
| 전체 지도·실행법·설계 결정 | [`README.md`](README.md) |
| 루트 트랙 수치·미해결 | [`REPRODUCTION.md`](../REPRODUCTION.md) · [`PROBLEMS.md`](../PROBLEMS.md) |

다시 만드는 법: `python3 ourkg/run_all.py` (약 50 분) ·
검사: `python3 ourkg/check.py` (29 항목, 2 초)

> **읽는 순서.** 결론만 필요하면 [`README.md`](README.md) 의 "지금까지 찾은 것
> 세 가지". 이 문서는 시간순 기록이라 **옛 절의 수치는 그때 값**이다 — 현재 값은
> 각 절의 갱신 주석이나 README 를 본다.

---

## 1. 한눈에

| | 논문 (2023) | ourkg |
|---|---|---|
| triple | 13,346,991 | **3,459,231** |
| entity | 1,637,915 | 785,572 |
| relation | 140 | 30 |
| 음식 | 34,250 샘플 → 135 사용 | 14,886 (추천 코호트 12,420) |
| compound | 85 | 130 |
| 음식당 측정 compound 중앙값 | 33 | **47** |
| 우울증 극성이 확정된 compound | 85 (공개 소스로는 69) | 66 |
| §5.1 방법 1 20문항 (주지표 = 재현+타당) | — | **9 / 20** (공개 KG 13/20). 재현만 보면 10 vs 18 이지만 양쪽 다 논문 결함 재연을 포함한다 |
| §5.1 방법 2 문헌 검증 (같은 자로, 2항 기준) | 13 / 15 | **14 / 15** |
| └ 같은 자를 3항으로 조이면 | 1 / 15 | 2 / 15 — **자에 판별력이 없다** (§4.3) |
| Fig. 5 추천군 Top30 / 비추천군 Bottom30 | 서술 | **22 / 27** (교차 위반 2 = Sweets) |
| ModiMedDiet Top30 처방군 / extras (빈도 반영) | — | **22 / 1** |
| 같은 기준에서 ModiMedDiet 로 학습한 E | — | 0.678 — **공개 소스가 이긴다** (§12) |
| `D = X·e` 만 비교하면 (PCA 무관) | — | 공개 0.520 / 역추정 0.803 / 상한 0.816 (§8) |

추천 점수 `D = E × Fᵀ` 에는 미생물이 들어가지 않는다 — 논문 식 (1)(2) 의 정의가
그렇다. gut-brain 경로를 거치는 compound 만 남겨도 순위 상관이 +0.99 다 (§6).

triple 수가 논문의 1/4 인 것은 온톨로지 축 때문이다. FoodOn·중국 식품 온톨로지·KEGG
brite 는 2026-11-09 에 넣었고(+11만), 남은 격차는 SNOMED CT 429만과 NCBI taxonomy
전체 131만이다 — 전자는 배포되지 않았고 후자는 정신질환 연관 종만 쓴다.
**음식-성분 축만 보면 우리 쪽이 더 크다 (321만 vs 233만).**

`evidence` 행은 논문에 대응이 없다 — E 의 근거를 KG 안에서 추적하려고 우리가
추가한 축이다 (§5 끝).

---

## 2. KG 규모 (논문 Table 1 대응)

`ourkg/out/kg_stats.csv`

| source | relation | entity | triples |
|---|---:|---:|---:|
| FoodData Central | 9 | 794,404 | 3,206,541 |
| FoodOn/OLS | 3 | 10,452 | 119,841 |
| Chinese Food Ontology | 3 | 49,865 | 82,542 |
| FoodOn | 4 | 6,592 | 21,723 |
| KEGG | 5 | 2,932 | 8,797 |
| MiKG | 6 | 1,060 | 6,802 |
| MeSH | 2 | 245 | 5,400 |
| ProMENDA | 6 | 1,289 | 5,150 |
| evidence | 15 | 278 | 1,560 |
| NCBI taxonomy | 5 | 210 | 590 |
| SNOMED CT | 2 | 294 | 285 |
| **Total** | **31** | **857,317** | **3,459,231** |

논문 Table 1 과 대조:

| source | 논문 triples | ourkg triples | 비고 |
|---|---:|---:|---|
| FoodData Center | 2,332,603 | 3,206,541 | FDC 전체 배포본 사용 |
| FoodOn | 79,769 | **141,564** | 배포 subset 21,723 + **OLS 축 119,841** (음식 8,165 · 클래스 1,096) |
| Chinese Food Ontology | 215,863 | 82,498 | 영어 라벨·subClassOf. 카테고리 20 · 음식 149 연결 |
| KEGG | 74,286 | 5,890 | compound-미생물 경로 재계산 + brite 분류축 |
| NCBI taxonomy | 1,306,152 | 590 | 정신질환 연관 127종만 |
| MENDA | 5,675 | 5,150 (ProMENDA) | 후속판으로 교체 |
| MiKG | 1,234 | 6,802 | 신경전달물질 경로 포함 |
| SNOMED CT | 4,291,226 | 285 | 배포본에 id 284 개뿐 — 라벨·계층 없음 |
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
| Fig. 5 하단층 = 추천군 (과일·채소) 이 Top30 에 | **22 / 30** |
| Fig. 5 상단층 = 비추천군 (베이커리·소고기·소시지·돼지) 이 Bottom30 에 | **27 / 30** |
| 교차 위반 (비추천군이 Top 에) | **2** |
| ModiMedDiet Top30 처방군 / extras | **22 / 1** |
| ModiMedDiet AUC (참고) | 0.592 |

**논문 §4.2.3 을 양쪽 모두 재현한다.**

> "the recommended foods are mainly fish and shellfish products, **as well as
> fruits and vegetables**. On the other hand, the not recommended foods are
> mainly **sausage products**, baked products, and sweets."

채소 16 + 과일 6 = 22/30 이고, 비추천 쪽은 소고기 18 · 소시지 6 · 돼지 3 이다.

#### 어패류 — "빠진" 것이 아니라 Fig. 5 와 맞는다 (2026-11-09 정정)

예전 판은 이 지표를 "추천군(**어패류**·과일·채소)" 으로 적고 어패류가 Top 30 에 없는
것을 미달로 봤다. **재현 트랙의 판정과 어긋난 서술이었다.**

논문은 같은 것을 두 군데서 다르게 적는다.

| | 어패류의 위치 |
|---|---|
| §4.2.3 **본문** | "recommended foods are mainly **fish and shellfish products**, as well as fruits and vegetables" |
| **Fig. 5** 피라미드 | **중간 층**(general foods) — 하단(추천)은 채소·과일뿐 |

재현 트랙은 **Fig. 5 를 기준으로 고정**했다(`tools/core.PAPER_REC = {Fruits,
Vegetables}`, 근거는 `tools/core.py` 주석과 §16.7). 알고리즘 출력에서 직접 그린 그림
쪽을 따른다는 결정이다. 같은 기준을 여기에도 적용하면 **어패류가 Top 30 에 없는 것이
올바른 동작**이고, 수치는 22/30 그대로다(채소 16 + 과일 6).

왜 어패류가 밀리는지도 측정했다. 커버리지 문제가 아니다 —

```
우울증 연결 compound 측정 밀도 (중앙값)
  어패류 29   채소 29   과일 29        ← 같다
점수
  어패류 최고 13.23 (80위)   채소 최고 26.88 (1위)
```

원인은 **DHA**다. `C06429 Docosahexaenoic acid` 는 우리 E 에서 `direction = -1`
(pos 12 / neg 34, 28 편, e_shrunk −0.393) 이고, 어패류에 중앙값 0.123 g/100g 로
몰려 있다 — 채소의 비타민 C(0.0099) 보다 12 배다. 강한 음(−) 성분을 많이 가진 음식군이
`D = E × Fᵀ` 에서 내려가는 것은 식의 정의 그대로다.

그리고 **논문의 E 도 DHA 를 음(−)으로 적는다** — `eval/gold.py` 의
`C06429: ('-', 'Docosahexaenoic acid', 'Fig5 PMID 28439746')`. 즉 §4.2.3 본문의
"어패류 추천" 은 논문 자신의 Fig. 5 · E 부호와 맞지 않는다.

두 평가 기준의 Top-30 측정이 처음으로 같은 방향을 가리킨다 — §4.2.3 추천군 22,
ModiMedDiet 처방군 22 / extras 1.

교차 위반 2 는 **Sweets 2 종이 Top 30 에 든 것**이다(논문은 비추천군). 반대 방향
위반(추천군이 Bottom 30 에)은 0 이다.

시각화: `ourkg/out/recommendation.png` (논문 Fig.4(b) 대응 t-SNE)

#### 온톨로지 축을 넣어도 추천은 바뀌지 않는다 (2026-11-09 측정)

FoodOn·중국 식품 온톨로지·KEGG brite·SNOMED 을 넣기 전후로 `recommend` 를 다시 돌려
비교했다.

```
md5  8a875c246e8f1e739a6951db6a860015   통합 전
md5  8a875c246e8f1e739a6951db6a860015   통합 후
행수 12,480 = 12,480     점수 전부 동일     Top30 겹침 30/30
```

"비슷" 이 아니라 **동일**하다. 추천 경로가 읽는 것은 `food_compound_long.csv`(영양소
중량)와 `compound_depression.csv`(E) 뿐이고, 네 소스 중 어느 것도 거기 들어가지
않는다. 논문 식 (1)(2) 의 정의상 당연하지만, 추측하지 않고 재실행해 확인했다.

### §3.2 충실도 점검과 수정 (2026-11-09)

"논문 §3.2 를 따른다" 고 적어 두고 실제로는 **명시된 규칙 중 둘을 빼먹고 있었다.**
전수 대조한 결과다.

| 논문 §3.2 가 명시한 규칙 | 수정 전 | 수정 후 |
|---|:---:|:---:|
| FDC 고유 식별자 사용 | O | O |
| "removing unnecessary words that may follow the first comma" | **X** | **O** |
| "exact matching … merge foods with identical labels" | O | O |
| "transform plural words into singular form" | **X** | **O** |
| "convert uppercase letters to lowercase" | O | O |
| 카테고리 self-defined mapping rules | O | O |

수정 전에는 논문이 든 **바로 그 예시**가 작동하지 않았다 —
`Milk, whole, ready to drink` 가 그대로 남고 `Tomatoes`/`Tomato` 가 다른 키였다.

#### (1) 은 일괄 절단이 아니다 — 민감도로 확인

처음에는 "splitting the food labels by commas" 를 **첫 쉼표에서 통째로 자르는 것**으로
구현했다. 결과가 무너졌다.

| | 일괄 절단 | 불필요어만 제거 (채택) |
|---|---:|---:|
| 라벨 병합 후 | 303,515 | 475,627 |
| 추천 코호트 음식 | 2,171 | 12,393 |
| **Fig. 5 추천군 Top30** | **4/30** | **22/30** |
| **비추천군 Bottom30** | **8/30** | **27/30** |
| Top30 주류(Alcoholic Beverages) | 23 | 0 |

A층 지표가 크게 퇴행하므로 §18.9 적용 규칙 2 에 따라 기각이다. 그리고 **논문 자신의
표가 반증한다** — Table 2·3·4 의 음식명이 쉼표 뒤를 그대로 유지한다.

```
Lettuce, Romaine · Broccoli, raw · Goose egg, cooked · Milk, skim · Hot dogs, beef
```

첫 쉼표에서 잘랐다면 이 이름들이 나올 수 없다. 논문이 말한 것은 `'ready to drink'`
같은 **불필요어 제거**다. 그래서 불필요어 목록(`common.UNNECESSARY`)으로 구현했다.

```
Milk, whole, ready to drink  ->  milk, whole      (ready to drink 만 제거)
Lettuce, Romaine             ->  lettuce, romaine (유지)
Peaches                      ->  peach            (단수화)
```

#### 논문에 없는 규칙 둘 — 효과는 1.3% 다

괄호 제거와 꼬리 샘플코드(`- ABC123`) 제거는 §3.2 에 없다. FDC 신판의 branded_food
표기 때문에 넣은 것이고, 병합에 미치는 영향은 작다.

```
논문 규칙만 (괄호·꼬리코드 없음)   487,330
  + 꼬리 샘플코드 제거             483,516   (-3,814)
  + 괄호 제거 (현재)               481,139   (-2,377)
```

둘을 합쳐 1.3% 를 더 병합한다. **정확도를 보완하려고 더 쓰는 규칙이 아니다** —
논문 규칙을 충실히 따랐을 때 A층·방법 1 이 그대로였다는 것이 아래 표다.

#### 구현하면서 만든 버그 둘 — 추천 상위에서 눈에 띄어 잡았다

규칙을 넣고 Top 30 을 보다가 이상한 키가 보였다.

```
mustard spinach, , raw        ← 쉼표 두 개
mcdonald'                     ← 소유격이 깨짐
```

| 버그 | 원인 | 건수 | 수정 |
|---|---|---:|---|
| 빈 쉼표 구간 | 괄호 제거(`(tendergreen)`)가 양옆 쉼표를 붙여 놓음 | 66 | `,\s*,` 를 합침 |
| 소유격 파괴 | 단수화가 `'s` 의 `s` 를 복수형으로 오인 | 7 | 아포스트로피 앞 `s` 제외 |

```
Mustard spinach, (tendergreen), raw               ->  mustard spinach, raw
Artichokes, (globe or french), frozen, unprepared ->  artichoke, frozen
Rice, brown, parboiled, dry, UNCLE BEN'S          ->  rice, brown, parboiled, dry, uncle ben's
```

수정 후 빈 쉼표 0 건, 소유격 깨짐 1 건(`VEGAN IS BELIEVIN'` — 브랜드명이 실제로
아포스트로피로 끝난다. 정상).

**남겨 둔 것** — Top 30 의 3·4 위가 `mustard green, cooked, boiled, drained, with salt` /
`without salt` 로 거의 같은 음식이 두 자리를 차지한다. 소금 유무로 나트륨이 다르니 FDC
상 별개 항목이고 §3.2 도 합치라고 하지 않는다. 합치는 것은 논문 근거가 없는 C층
판단이라 손대지 않았다.

#### 수정 전후 — 모든 수치 재측정

| | 수정 전 | 수정 후 |
|---|---:|---:|
| 라벨 병합 후 | 482,937 | **475,623** |
| 음식 (compound ≥ 20) | 14,719 | **14,886** (Vitamin D 매핑 추가 후) |
| 추천 코호트 | 12,480 | **12,392** |
| 총 triple | 3,291,731 | **3,270,143** |
| Fig. 5 추천군 Top30 / 비추천군 Bottom30 | 22 / 27 | **22 / 27** (동일) |
| Top30 교차 위반 | 2 | **2** (동일) |
| **Top30 의 어패류** | **0** | **1** |
| §5.1 방법 1 | 8/20 | **8/20** (바뀐 문항 0) |
| §5.1 방법 2 | 4/15 | **1/15** (아래) |

A층·방법 1 은 그대로이고 어패류가 하나 들어왔다. 충실도는 올랐는데 지표는 거의
움직이지 않는다 — 병합 차이가 7,310 건(1.5%)뿐이기 때문이다.

#### 방법 2 가 4/15 → 1/15 로 떨어진 이유는 링킹이 아니다

표본이 바뀌면서 Diet 행의 음식 이름이 달라졌는데, 그 이름을 **PubMed 검색어로 그대로
넣고 있다.**

```
"Mustard greens, cooked, boiled, drained, with salt" and depression  ->  0 건
"Mustard spinach, (tendergreen), raw" and depression                 ->  0 건
```

FDC 라벨은 문헌 검색어가 될 수 없다. 논문은 `Lettuce`·`Onion`·`Garlic` 처럼 **일반명**을
썼다. 방법 2 를 고치려면 검색어를 일반명으로 정규화해야 한다 — 수치 자체보다 이쪽이
먼저다.

> **2026-11-17 보충.** 일반명 사다리는 넣었고(아래), 근거 물질 표기까지 정규화해도
> 수치는 움직이지 않았다. 방법 2 는 자 자체에 판별력이 없다 — §4.3 끝.

#### 정적 스냅샷 → 실시간 API (2026-11-09)

어느 축이 실시간이고 어느 축이 스냅샷인지 정리하고, 가능한 곳을 넓혔다.
받은 것은 `ourkg/cache/` 에 **TTL 30일**로 둔다 — 같은 창 안에서는 재현되고,
지나면 자동으로 다시 받아 최신성을 얻는다. 페처는 `common.cached_get` /
`common.kegg_rest` 로 올려 `build.microbe()` 와 `build.kg()` 가 공유한다.

| 축 | 상태 | 비고 |
|---|---|---|
| KEGG 대사 경로 | **실시간** `rest.kegg.jp` | compound → EC → KO → organism 직접 유도 |
| **KEGG brite 분류** | **실시간** (2026-11-09 전환) | `get/br:br08001·08002·08005` |
| NCBI taxonomy | **실시간** `eutils` | 학명·계통·rank |
| MeSH tree | **실시간** `id.nlm.nih.gov/sparql` | F03 판정 |
| PubMed | **실시간** `eutils` | §5.1 방법 2 |
| FDC | 스냅샷 1.9GB | **API 없음** — 벌크 배포만 |
| ProMENDA | 스냅샷 xlsx | 논문 부록 |
| FoodOn | 스냅샷(논문 KG) | OBO PURL 은 살아 있다(206). 재현 제약으로 보류 |
| 중국 식품 온톨로지 | 스냅샷(논문 KG) | **논문 각주 URL 이 404** — 원천이 사라졌다 |
| SNOMED CT | 스냅샷(논문 KG) | 라이선스 필요 |

#### KEGG brite 를 실시간으로 바꾼 효과

```
분류된 compound   646  ->  744   (+98)
brite 클래스    1,691  -> 2,729
brite triple    3,506  -> 6,413
```

논문 배포본의 KEGG 서브셋은 6,685 노드뿐이라 분류가 얇았다. 실시간으로 받으면
우리 compound 1,455 중 744 가 분류된다.

**방법 1 은 8/20 그대로다.** brite 를 쓰는 문항(#14·#15·#16)이 이미 O 였기 때문이다.
추천도 불변이다 — brite 는 `D = E × Fᵀ` 에 들어가지 않는다. 온톨로지 통합 때와 같은
"능력은 늘고 지표는 그대로" 패턴이다.

`BRITE=static` 으로 두면 예전처럼 논문 배포본만 쓴다. 네트워크가 안 되면 자동으로
폴백한다.

#### compound 축 — 재현했고, F 에 적용하면 퇴행한다 (2026-11-09)

논문 §3.2 의 compound 링킹 절차를 직접 구현했다(REPRODUCTION §17.29). 결과
`kegg_alias.KEGG_ALIAS` 15 건을 얻었고 그중 9 건은 기존 `INCIDENCE_ALIAS` 와
독립적으로 일치했다.

**F 행렬에 적용해 봤다 — 기각이다.**

논문 ID 를 정식 ID 로 바꾸면 ProMENDA 의 E 와 아미노산 13 개가 추가로 만난다
(추천 입력 66 열 -> 79 열). 그런데 A층이 엇갈린다.

| | 적용 전 | F 에 적용 |
|---|---:|---:|
| 추천 입력 열 | 66 | 79 |
| **Fig. 5 추천군 Top30** | **22/30** | **15/30** |
| 비추천군 Bottom30 | 27/30 | **30/30** |
| 교차 위반 | 2 | 3 |
| Top30 어패류 | 1 | 0 |

비추천군은 완벽해지지만 추천군이 7 개 떨어지고, Top 5 가
`Orange drink` · `Italian dressing` · `mayonnaise` · `mayonnaise, light` ·
`Butter` 로 바뀐다. 아미노산이 E 에서 대부분 음(−)이라(+30/−49) 단백질이 많은
음식이 내려가고 지방·당이 올라간 결과다. 영양학적으로도 납득되지 않는다.

§18.9 적용 규칙 2(A층 퇴행이면 채택하지 않는다)에 따라 **F 에는 적용하지 않는다.**
`KEGG_ALIAS` 는 라벨·brite·대사 경로 **조회에만** 쓴다.

알게 된 것 하나 — `ourkg` 는 `kegg_alias` 를 **전혀 쓰지 않고 있었다.** 그래서
추천에 쓰이던 66 열 중 아미노산이 1 개뿐이었다. 지금은 그것이 의도된 상태임을
위 측정으로 확인하고 주석에 적어 뒀다.

#### 아직 논문 방식이 아닌 두 축

음식 축만 고쳤다. 나머지 둘은 **절차가 아니라 결과를 가져온 상태**이고, 그렇게 적어 둔다.

| 축 | 논문 §3.2 | 우리 |
|---|---|---|
| compound | "linked to KEGG **using their labels** … ignores case, singular and plural forms, as well as the word sequence" + 그리스문자 제약 | `setup/nutrient_kegg_map.csv` 사전 매핑표 180 개. 그중 **101 개는 공개 KG 의 `sameAs` 와 값까지 동일**하고 79 개는 자체 추가(지방산) |
| disease | MeSH·SNOMED 라벨 매칭 | `Disease_Bacteria.jsonld` 의 taxid–MeSH 쌍을 그대로 읽음. SNOMED 없음 |

### 엔티티 링킹 (논문 §3.2) — 우리가 수행한 것

재현 트랙의 `eval/paper_kg_stats.linking()` 이 **논문 수치를 검증**한다면, 여기서는
우리가 **직접 수행한** 링킹을 집계한다. `ourkg/out/linking_stats.csv`
(`build.py food` 가 `food_link.json` 에 중간 수치를 남기고 `build.py kg` 가 표로 합친다).

| 축 | 항목 | 값 | 논문 대응 |
|---|---|---:|---|
| food | FDC 원본 항목 | 2,101,279 | §3.1 34,250 food samples |
| food | 라벨 병합 전 (KEGG 측정 보유) | 1,949,651 | |
| food | **라벨 병합 후** (§3.2 exact matching) | **482,937** | "merge foods with identical labels" |
| food | 음식당 compound ≥ 20 필터 후 | 14,719 | §4.2.1 135 food |
| food | 세분 카테고리 (FDC category) | 265 | §3.2 128 distinct categories |
| food | 상위 카테고리 (SR food group) | 27 | |
| compound | nutrient → KEGG 매핑 | 180 | |
| compound | 음식 행렬의 KEGG compound | 130 | §3.2 23,212 / §4.2.1 85 |
| compound | ProMENDA E 의 KEGG compound | 1,412 | |
| compound | KEGG brite 로 분류된 compound | 646 | §3.1 compound ontology |
| microbe | NCBI taxonomy 링크 (taxid) | 127 | §3.2 984,031 gut microbiota |
| microbe | KEGG organism 매칭 | 82 | |
| disease | MeSH 링크 | 244 | §3.2 3,505 mental disorders |
| disease | SNOMED CT 링크 | 1 | 배포본에 라벨·계층 없음 |
| ontology | FoodOn ↔ 카테고리 | 19 | §3.1 FoodOn |
| ontology | 중국 온톨로지 ↔ 카테고리 / 음식 | 39 / 172 | §3.1 Chinese Food Ontology |

#### 병합이 실제로 일어난다 — 75%

```
1,949,651  →  482,937        (1,466,714 감소, 75.2%)
```

§3.2 의 핵심인 exact matching 병합이 작동한다. `foods.csv` 만 보면 `fdc_id` 14,719 =
`food_key` 14,719 라 **병합이 0 인 것처럼 보이는데**, 그건 `음식당 compound ≥ 20`
필터가 병합 **뒤에** 걸려 대표 항목만 남기 때문이다. 중간 수치를 산출물에 남기지
않았던 탓이고, 이 표를 만든 이유다.

#### 논문과의 규모 차이

음식 축은 논문(1,220,480)보다 **크다**(1,949,651 → 482,937). FDC 배포본 전체를 쓰고
branded_food 까지 포함하기 때문이다. 반대로 compound 축은 논문(23,212)보다 훨씬
**작다**(130) — 우리는 FDC 가 **측정값으로 보고한 영양소**만 KEGG 에 링크하고,
논문처럼 KEGG compound 전체를 싣지 않는다. 미생물 축(127 vs 984,031)도 같은 이유로,
정신질환 연관 종만 남긴다.

즉 **규모가 아니라 범위를 달리 잡은 것**이고, 그 선택이 §4.2 추천의 입력 밀도를
논문보다 높인다(음식당 측정 compound 중앙값 47 vs 33).

## 4. 평가 — 논문 §5.1

### 방법 1 (human annotation) — Supplement Table 1 의 20문항

논문은 전문가 3인과 대조해 정확도 0.95 / 0.90 / 0.95 를 보고한다. 전문가 답변 자체가
공개되지 않았으므로(`eval/m1.py` 서두) 그 수치는 재현 대상이 아니다.

**2026-11-06 변경.** 예전 판은 측면(aspect)마다 "축이 있는가" 를 손으로 O/△ 로 적고
20문항이 그 판정을 상속했다. 그건 답변 **가능성**이지 답이 아니었다 — "완전 답변 13 /
부분 7" 은 실제로 답을 맞혔다는 뜻이 전혀 아니다. 이제 `eval/m1.py` 의 **질의 함수
20개를 그대로 재사용**해 우리 KG 에서 답을 뽑고 논문 답과 대조한다. `m1.KG` 를 상속해
적재만 우리 산출물로 바꾼 어댑터(`OurKG`)를 쓰므로 질의는 한 줄도 다르지 않다.

| | 값 |
|---|---|
| 논문 답 재현 | **10 / 20** (온톨로지 축 통합 전 5, 2026-11-18 전 8) |
| 재현 + 타당 | 9 / 20 |
| 전문가 전원동의 16문항 중 | 6 |
| 같은 질의를 공개 KG 에 돌리면 (`eval/m1.py`) | 18 / 20 |

#### 2026-11-18 — 8/20 에서 10/20 으로, 그리고 왜 더는 안 오르나

막힌 12 문항을 원인별로 갈랐다. **우리 결함 둘을 고쳐 둘이 열렸다.**

| 문항 | 원인 | 결과 |
|---|---|---|
| #3 이유식 | 질의가 배포 KG 철자 `^Carrots, baby food` 를 박았다. FDC SR 은 `Babyfood, carrots, toddler` 로 쓴다 | 질의를 **철자가 아니라 주장**을 재도록 고쳐 **O**. 우리 KG 엔 Baby Foods 216 종, carrots·plums 모두 있다 |
| #9 B12 혼합식 | 집계·단위 수정으로 조합이 생겼다 | **재현 O / 타당 X** — 아래 |
| #4 엽산 | **우리가 평균을 냈다** (DFE 46 · total 29 · food 4 → 26.3) | 집계를 고쳤지만 여전히 X. 논문 값 0.046 은 **DFE** 이고 DFE 는 화합물 중량이 아니다 — 아래 |
| #6 citric acid | `setup/nutrient_kegg_map.csv` 가 FDC nutrient 477 중 **212 만** 덮는다. 유기산·폴리페놀 계열(acetic·benzoic·chlorogenic·citric·fumaric…)이 통째로 없다 | 원인 확정. 매핑표를 채워도 `Adlercreutzia` 의 C00158 대사 경로가 KEGG 에 없어 △ 가 한계다 |
| #2 soy milk | 배포 KG 는 `Beverages > Milk substitutes`. 우리는 SR `Legumes`(10) 와 WWEIA 1902 `Plant-based milk`(4) 다 | 카테고리 **이름**은 정규식으로 받게 고쳤지만 여전히 X — 우리 축에는 soy milk 가 Beverages **아래**에 없다. 이름 문제가 아니라 축 문제다. 억지로 Beverages 로 옮기지 않는다 |
| #5 retinol · #10 B6 | 논문 답이 Query 1 결함으로 틀렸음을 §17.31 에서 입증 · B-6 는 우리가 기각 | 고치지 않는다 |
| #12 | SNOMED CT 상위 분류가 필요하다고 봤다 | **틀렸다 — MeSH 트리에 있다. 아래** |

**질의를 고칠 때 공개 KG 가 18/20·타당 13/20 그대로인 것을 확인했다** — 우리 쪽만
유리해지는 변경이 아니다.

#### 재현 10/20 중 1 건은 논문의 결함을 재연한 것이다

`#9` 는 "orange + sausage 혼합식의 B12 = 0.072 mg" 를 **맞혔다.** 다만 그 값이
나온 경로가 `"Orange Blossom" 0 + "Veal, variety meats" 0.0725` 다 — 두 번째
음식이 질문의 음식이 아니다. Supplement Query 1 의 미결합 `?unit` 결함을 그대로
재연한 것이고, 교정판 SPARQL 로 Table 2 의 8 행이 모두 **8~82 배 과대**임을
확인했다 (§17.2 · §17.31).

**공개 KG 도 같다.** `#5` · `#9` · `#10` 세 문항이 모두 재현 O / 타당 X 다.
즉 배포 KG 의 18/20 에는 **결함 재연이 3 건**, 우리 10/20 에는 1 건 들어 있다.

| | 재현 | 그중 논문 결함 재연 | **재현 + 타당** |
|---|---:|---:|---:|
| 공개 KG (`eval/m1.py`) | 18 / 20 | 3 | **13 / 20** |
| `ourkg` | 10 / 20 | 1 | **9 / 20** |

**주지표는 재현+타당 쪽이다.** 분모에서 빼지는 않는다 — 분모를 우리가 고치면
비교가 흔들린다 — 대신 `eval/m1.PAPER_DEFECT` 로 표시하고 두 트랙 모두 실행할
때마다 몇 건인지 같이 찍는다.

#### ★ 매핑표를 94 종 확장했다가 기각했다 — 희소 열을 **더하면** 유사도가 무너진다

`#6` 의 원인이 "`C00158` 이 F 에 없다" 가 아니라 **매핑표를 안 만든 것**이었다.
`setup/nutrient_kegg_map.csv` 는 FDC nutrient 477 중 212 만 덮었고, 유기산·
폴리페놀 계열(acetic·benzoic·chlorogenic·citric·fumaric…)이 통째로 빠져 있었다.

미매핑 265 중 질량 단위·단일 화합물 203 을 KEGG REST `find/compound` 로 조회해
**이름이 정확히 일치하는 94 종**을 얻었다(부분 일치는 버렸다). 매핑표 212 → 306,
F 의 compound 130 → **157**. grape juice 에 citric acid 가 붙었다.

**그런데 두 주지표가 무너진다.**

| 설정 | compound | MMD Top30 처방/extras | §4.2.3 추천군 | 위반 |
|---|---:|---:|---:|---:|
| **기준선** | 130 | **23 / 1** | **22** | 2 |
| 전체 추가 | 157 | 4 / 9 | 7 | 0 |

계열별로 하나씩 빼 봐도(유기산·폴리페놀·당·기타) 어느 하나도 범인이 아니다 —
**27 종을 전부 빼야** 복구된다. 집합적 효과다.

눈에 띄는 차이는 **커버리지**다.

| | 측정된 음식 수 (중앙값) |
|---|---:|
| 기존 130 종 | **5,168 종 (34%)** |
| 추가 27 종 (그중 `E`≠0 이라 실제 열이 된 것 16) | **12 종 (0%)** |

citric acid 는 14,981 음식 중 **29 종**에만 값이 있다. 그래서 처음에는 "희소 열이
열별 정규화에서 소수 음식에 극단값을 주고 유사도를 그 축으로 끌고 간다" 고 적었다.

처음에는 이 설명이 반증된 줄 알았다. 기존 130 종에도 100 종 미만 열이 **18 개**
있는데 그것들을 빼면 성능이 **내려가기** 때문이다.

| `MIN_FOODS` (기존 130 에 적용) | compound | MMD 처방/extras | 추천군 | 위반 |
|---|---:|---:|---:|---:|
| **0 (현재)** | **130** | **23 / 1** | **22** | **2** |
| 25 | 122 | 22 / 2 | 21 | 2 |
| 50 | 116 | 21 / 3 | 18 | 3 |
| 250 | 107 | 21 / 4 | 19 | 3 |
| 1500 | 98 | 21 / 4 | 19 | 3 |

**그러나 둘은 모순이 아니었다.** 제거 실험만으로 결론을 낸 것이 성급했고,
가짜 열을 만들어 다시 가르니 기전이 나왔다.

**1단계 — `S`(유사도) 경로인가 `D = X·e`(점수) 경로인가**

추가된 16 열(추가분 27 중 `E`≠0 이라 실제로 열이 된 것)의 `E` 만 손댔다.

| 설정 | MMD 처방/extras | 추천군 | 위반 |
|---|---:|---:|---:|
| A 기준선 | 23 / 1 | 22 | 2 |
| B 추가 16 열 · `E` 그대로 | 4 / 9 | 7 | 0 |
| C 추가 16 열 · **`E`≈0** (부호만 남김) | 4 / 9 | 7 | 0 |
| D 추가 16 열 · **`E` 부호 반전** | 4 / 9 | 7 | 0 |

`E` 를 0 으로 줄여도 부호를 뒤집어도 **완전히 같다.** 점수 경로는 무관하고 손상은
전부 **유사도 `S`** 에서 난다.

**2단계 — 희소성인가 열 수인가**

기존의 **조밀한** 열 16 개를 복제해 가짜 KEGG 로 넣은 것과, **같은 내용**을 추가분과
같은 커버리지(2~46 종)로 마스킹해 넣은 것을 비교했다.

| 설정 | MMD 처방/extras | 추천군 |
|---|---:|---:|
| E 가짜 **조밀** 열 16 추가 | **20 / 4** | **17** |
| F 가짜 **희소** 열 16 추가 | **3 / 10** | **6** |

**같은 내용·같은 열 수인데 희소하게 만들면 무너진다.** 열 수가 아니라 희소성이다.

그래서 정확한 명제는 이렇다.

- ✗ "희소 열은 해롭다" — 틀렸다. 기존 희소 열 18 개는 빼면 나빠진다(신호를 갖고 있다).
- ✓ **"희소 열을 더하면 유사도가 무너진다"** — 조밀 열 추가는 멀쩡하고(20/4)
  희소 열 추가만 무너진다(3/10).

기존 희소 열은 **이미 포함된 상태로** 열별 정규화와 유사도가 맞춰져 있다. 거기에
희소 열을 더하면 그 소수 음식만 정규화 후 1.0 을 받아 유사도가 그 축으로 끌려간다.
`B-6` 를 기각했을 때(커버리지 99%)도 열 추가였지만 그쪽은 조밀 열이었으므로 이
기전으로 설명되지 않는다 — **그 건의 기전은 여전히 미해명이다.**

기각하고 매핑표를 원복했다. 94 종은 `setup/nutrient_kegg_candidates.csv` 에
KEGG ID · 측정 음식 수 · 커버리지와 함께 남긴다 — **없어서 못 쓴 것이 아니라
FDC 가 거의 측정하지 않아 못 쓴다**는 증거다.

**그래서 `#6` 은 여기서 결론이 난다.** 매핑해도 추천 행렬에 쓸 수 없고, 게다가
`Adlercreutzia equolifaciens` 의 C00158 대사 경로가 KEGG 에 없다.

#### ★ KG 층과 F 층을 나눈다 — `#4` 가 열린다

논문은 KG 의 compound(§3.2 **23,212**)와 추천 행렬 `F` 의 compound(§4.2.1 **85**)를
분리한다. 우리는 `food_compound_long.csv` **하나로 둘 다** 하고 있었다. 그래서
"`F` 에 넣으면 추천이 무너지는 성분"이 KG 에서도 통째로 빠졌다.

| 층 | 산출물 | 내용 |
|---|---|---|
| **KG** | `food_compound_kg.csv` | 성분별 측정치를 **그대로**. nutrient **202** · compound **154** · 값 868,442 |
| **F** | `food_compound_long.csv` | 대표 측정치만. compound **130** · 값 779,094 |

스트리밍은 확장 매핑(기본 182 + 후보 94 + B-6)으로 **넓게** 받고 `F` 는 뒤에서
`setup/nutrient_kegg_map.csv` 로 좁힌다. **`F` 는 정의상 바뀌지 않고**, 두 기준이
(23/1 · 추천군 21 · 비추천군 26 · 위반 0)으로 그대로인 것을 매 단계 확인했다.
`Vitamin B-6` 는 `F` 에서 기각한 상태 그대로 두고 KG 층에만 둔다 — KEGG 대응이
없는 것이 아니라(C00314) 추천을 무너뜨려 뺀 것이다.

어댑터도 KG 층에서 `nutrient_id` 로 바로 찾는다. 전에는 수작업 매핑
`NUT2KEGG` 8 줄로 KEGG 에 접어 `F` 에서 찾았고, 그래서 `Folate, DFE`(1190)·
`Vitamin B-6`(1175) 처럼 **질문이 요구하는 측정치**를 잃었다. 영양소축 7/8 → **202**.

**그리고 대표 항목과 값이 따로 놀고 있었다.**

```
Pie, peach   대표 = fdc_id 175020 (SR legacy, Folate DFE 46 µg)
             값   = 라벨을 공유하는 항목 전체의 평균 44 µg
```

`foods.csv` 는 큐레이션 순위(`_PRIORITY`)로 대표 fdc_id 를 고르면서 값만 평균을
썼다. "이 음식은 175020 이다" 라고 적고 값은 다른 항목과 섞는 **내부 불일치**다.
KG 층은 **대표 항목의 값**을 쓰도록 고쳤다(`F` 층은 논문 §3.2 라벨 병합 평균 유지
— 층을 나눈 덕에 가능한 선택이다).

**`#4` 가 O 가 됐다** — `Pie, peach` 의 `Folate, DFE = 0.046`, 논문 답과 일치.
**방법 1 재현 12 → 13/20, 타당 10 → 11/20.**

곁가지로 `#5` 의 주석이 `0.127 = "Cheese, ricotta, whole milk"` 로 바뀌었다 —
논문이 `milk` 를 라벨 부분 문자열로 찾아 리코타 치즈를 우유로 잡았다는 것을
이제 우리 KG 로 **재현해 보일 수 있다**(§4.1 Query 결함 3).


### ★ MiKG 원본을 다시 읽는다 (2026-11-19) — 네 가지를 버리고 있었다

**기준을 바꿨다.** 여기부터는 방법 1 점수를 올리는 것이 목표가 아니라 **우리
데이터를 두텁게** 하는 것이 목표다. 축별 실태를 보면 미생물 축이 가장 얇고
(NCBI 127 종 · KEGG organism 82), 그것이 gut-brain 경로 전체를 제약한다.

MiKG 원본(2,465 triple)에서 우리는 `hasGutMicrobiota`·`hasNeurotransmitter`·
`hasMentalDisorder` **세 술어만** 쓰고 있었다. 전수를 세어 보니 쓸 것이 더 있었다.

| 술어 | 수 | 내용 | 우리에게 |
|---|---:|---|---|
| `hasEvidenceLevel` | 82 | **A 4 · B 21 · C 47** | 관계의 **질**을 구분 |
| `hasRegulation` | 14 | **Promote 13 · Inhibit 1** | 관계의 **방향** |
| `hasMapID` | 56 | KEGG pathway id | 경로 층이 하나 더 |
| `owl:sameAs` | 114 | **SNOMED 63 · MeSH 51** | 이름 대신 **ID 로 연결** |

`hasMapID` 는 처음에 0 건이 나왔다 — statement 가 아니라 별도 `KEGG_pathway`
노드에 달려 신경전달물질과 이어지기 때문이다. 고쳐서 **90 링크 · 경로 56 종**을
얻었다(`out/neurotransmitter_pathway.csv`).

**SNOMED 축이 열린다.** 통계의 `SNOMED CT 링크` 는 줄곧 **1** 이었고 "배포본에
라벨·계층 없음" 이라 적어 두었다. 그런데 MiKG 가 자기 엔티티에 SCT id 를 **63 개**
달아 두었고 우리가 안 읽고 있었다. 측정하지 않으면 없는 것과 같으므로 통계 행을
출처별로 나눴다.

```
disease  SNOMED CT 링크 (배포본)        1
disease  SNOMED CT 링크 (MiKG xref)   63   <- 신규
disease  MeSH 링크 (MiKG xref)        51   <- 신규
microbe  MiKG 근거 등급 보유 관계       82   <- 신규
microbe  MiKG KEGG pathway 링크       90   <- 신규
```

KG 반영: MiKG triple **6,802 → 7,194**, 관계 종류 **6 → 9**.

```
<mikg:Microbe/Neurotransmitter>  our:evidenceLevel  "A"|"B"|"C"
                                 our:regulation     "Promote"|"Inhibit"
<mikg:Dopamine>   owl:sameAs      <http://id.nlm.nih.gov/mesh/D004298>
<mikg:Histamine>  our:hasPathway  <https://www.kegg.jp/pathway/map04974>
```

`F` 는 건드리지 않으므로 두 기준은 불변이다.

#### gutMDisorder — 서버가 닫혀 있다

논문이 related work 로 언급만 하고 쓰지 않은 소스라 우리 미생물–질환 축을 두껍게
할 후보였다. `bio-annotation.cn` 은 DNS 는 해석되지만(47.76.215.223) http·https·
8080 이 모두 connection refused 다. NAR 논문(2020 v1 · 2022 v2) 보충자료가 대안이다.

### 방법 1 — 20문항 판정 (2026-11-19 기준)

재현 **13/20** · 재현+타당 **11/20** (공개 KG 는 18/20 · 타당 13/20)

| # | 문항 | 재현 | 타당 | 비고 |
|---|---|---|---|---|
| 0 | Lists of fruits which contains Lysine | O | O | Lysine>0 인 과일 80종에 melons·oranges 포함. strawberries 는 Lysine 기록 17건이 전부 0 |
| 1 | The food categories of the cola | O | O | Beverages 아래 "soft drinks?" 계열에 속하는 음식 8개 |
| 2 | The food categories of the soy milk | O | △ | Beverages 아래 "milk substitut/plant[- ]based milk/plant derived beverage" |
| 3 | The lists of baby food | O | O | baby food 318종, carrots True · plums True |
| 4 | The weight of folate that peach pie can provid | O | O | Pie, peach 의 Folate, DFE = 0.046 |
| 5 | The difference of retinol between milk and yog | X | X | 0.127 = "Cheese, ricotta, whole milk", 0.702 = "?" — 라벨 부분 문자열 매칭. 실제 Mi |
| 6 | The weight of citric acid can Adlercreutzia eq | X | △ | "없음" = 309, Adlercreutzia equolifaciens 의 C00158 대사 경로 없음 |
| 7 | The weight of ascorbic acid can Bifidobacteriu | △ | △ | "101 GREENS JUICE, CUCUMBER, LETTUCE, APPLE" = 15, Bifidobacterium longu |
| 8 | The rank of Potassium weight in food | △ | △ | 순위 범위가 문항에 없다. KG 전체 1~3위는 ['RAW ITALIAN ALMOND BUT', 'FABULOUS FRIES',  |
| 9 | The weight of Vitamin B12 in mixed diet orange | O | X | 0.072 = "Orange Blossom" 0 + "Veal, variety meats and by-p" 0.0725 — 두 번 |
| 10 | The weight of Vitamin B6 in egg and whole milk | X | X | 합이 나오는 조합 없음 |
| 11 | The microbial related mental disorders | O | O | 세균 연관이 있는 질병: {'Autism': 78, 'Pervasive developmental disorder NOS': 30} |
| 12 | The difference between depression and autistic | O | O | 우울증 상위 ['Depressive Disorder', 'Mood Disorders'] / 자폐 상위 ['Child Develop |
| 13 | The list of diseases in mental disorders | O | O | KG 의 mentalDisorder 하위 11종: ['Anxiety disorders', 'Autistic disorder', ' |
| 14 | The vitamins may have effects on depression | O | O | MENDA 우울증 연관 비타민: ['Vitamin C', 'Vitamin D3', 'Vitamin D2', 'Vitamin B9' |
| 15 | The alkaloids involved from food | O | O | 음식 성분 중 alkaloid: ['Caffeine', 'Nicotinic acid (Vitamin B3)', 'Theobromi |
| 16 | The categories of biological compounds | O | O | KEGG 클래스 847개에 Peptides·Alkaloids 포함 |
| 17 | The Bacteroides may have effects on depression | △ | △ | MENDA 우울증 화합물을 대사하는 Bacteroides: ['fragilis', 'intestinalis', 'ovatus',  |
| 18 | The taxonomy tree of Escherichia coli | O | O | Escherichia → Enterobacteriaceae → Enterobacterales → Gammaproteobacteri |
| 19 | The top 3 genus of bacteria related to disease | △ | △ | 질병 연결 수 상위 속: [('Streptococcus', 49), ('Bacteroides', 46), ('Bifidobacte |

#### `KG_MIN_COV` 실험 (2026-11-19) — 개념은 맞고 결과는 퇴행이다

`#6` 을 열려고 **KG 층에서 `MIN_COV>=20` 을 풀었다.** 그 문턱은 F 층의 요구다 —
유사도를 계산하려면 음식당 성분이 충분해야 한다. KG 에는 그런 요구가 없고 논문
KG 는 FDC 항목 122 만 개를 담는다. compound 를 F 기준으로 자르던 혼동을 food 에
그대로 반복하고 있었다.

| | 전 | 후 |
|---|---:|---:|
| KG 층 음식 | 14,886 | **475,769** (라벨 병합 전수) |
| KG 층 값 | 868,442 | 3,406,998 |
| 파일 크기 | 73 MB | **463 MB** |
| 두 기준 | (23/1 · 21 · 26 · 0) | **동일** |
| 방법 1 | 13/20 · 타당 11 | **13/20 · 타당 11** |

**점수는 그대로인데 답의 질이 떨어졌다.**

```
#7  "Lettuce, arugula, raw" (15)  ->  "101 GREENS JUICE, CUCUMBER, LETTUCE, APPLE"
#8  Leavening agents (베이킹파우더)  ->  "RAW ITALIAN ALMOND BUT..."
#0  Lysine 과일 94 종            ->  80 종
```

브랜드·시료 항목 46 만 개가 들어오면서 상위를 차지한다. 판정은 △ 그대로지만
문항이 기대하는 것은 큐레이션된 식품이지 브랜드 주스가 아니다. **숫자가 안
바뀌었다고 중립이 아니다.**

그리고 **`#6` 은 열리지도 않았다.** grape juice 의 citric acid 가 2 건 들어왔지만
값이 110.2 와 216.7 이다. 논문의 309 를 가진 `fdc_id 2004671` 은
`sub_sample_food` 인데, 같은 라벨을 공유하는 항목 중 `foundation_food`(216.7)가
`_PRIORITY` 로 대표가 되기 때문이다.

**즉 `#6` 은 `#4` 를 열어 준 규칙과 정면으로 충돌한다.** 309 를 꺼내려면 "대표
항목의 값만 쓴다" 를 깨야 하고, 그러면 `Pie, peach` 의 DFE 가 다시 평균으로
돌아가 `#4` 가 닫힌다. 한 문항을 열면 다른 문항이 닫히는 교환이다.

> **상태**: 되돌릴지 결정 대기. 현재 작업 트리는 **퇴행 상태**다
> (`KG_MIN_COV=1`, 음식 475,769). 되돌리려면 `KG_MIN_COV` 를 `MIN_COV` 와 같게
> 두고 `build.py food` 를 다시 돌리면 된다.

#### `#6` citric acid — 단위 버그를 찾았고, 문항은 못 연다

`#6` 을 다시 보다 **KG 층의 단위가 1000 배 틀린 것**을 찾았다. `nutrient_name` 의
NaN 은 고치면서 같은 표의 `unit` 을 빠뜨려, 새로 넣은 후보 94 종 전부가
`fillna(1.0)` 으로 **mg 를 g 로** 취급하고 있었다.

```
Raspberries, raw  citric acid  1,740,000 mg  ->  1,740 mg
Pineapple, raw                   685,400     ->    685.4
```

단위는 `fdc_raw/nutrient.csv`(정본)에서 가져오고 F 매핑표 값으로 덮어쓴다.
질의가 조용히 1000 배 틀린 값을 쓰고 있었으므로 문항과 무관하게 고쳐야 할 결함이다.

**문항 자체는 열 수 없다.** 논문 답 309 는 실재한다 —
`fdc_id 2004671 GRAPE JUICE, WHITE, FROM CONCENTRATE …` = 309.0 mg. 그런데
FDC 전체에서 citric acid 측정은 **172 항목뿐이고 전부 `foundation`·`sub_sample`**
이다. `sub_sample_food` 는 특정 성분만 재는 시료라 성분 수가 적어
`MIN_COV >= 20` 을 못 넘긴다. 우리 코호트의 grape juice 9 종에 white/purple 은
하나도 없고, citric 을 가진 음식은 **5 종**(바나나·파인애플·라즈베리·딸기)뿐이다.

성분 프로파일이 풍부한 항목(SR legacy·FNDDS)은 citric acid 를 재지 않고, citric
acid 를 가진 항목은 프로파일이 빈약하다 — **FDC 데이터의 성격**이다. `MIN_COV` 를
낮추면 들어오지만 그것은 문항 하나를 위해 코호트 정의를 바꾸는 일이라 하지 않는다.
게다가 값이 맞아도 `Adlercreutzia equolifaciens` 의 C00158 대사 경로가 KEGG 에
없어 △ 가 한계다.

남은 X 셋은 `#6`(위), `#5`·`#10`(둘 다 `PAPER_DEFECT`) 이다.

#### ★ SNOMED CT 의 대체 축은 MeSH 트리였다 — `#12` 가 열린다

`#12`("우울증과 자폐의 차이")를 두 번 **"SNOMED CT 계층에만 있어 불가능"** 으로
닫았다. 틀렸다. 논문 답인 `Mood disorder` / `developmental disorder` 는 **MeSH F
트리의 이름**이고, 우리는 그 트리 번호를 **이미 갖고 있었다.**

```
D003865 Major Depressive Disorder   F03.600.300.375
  < F03.600.300  Depressive Disorder
  < F03.600      Mood Disorders               ← 논문 답
  < F03          Mental Disorders

D001321 Autism                      F03.625.164.113.500
  < F03.625.164  Child Development Disorders, Pervasive
  < F03.625      Neurodevelopmental Disorders ← 논문 답
```

번호는 **접두를 자르면 조상**이 되고, 번호 → 기술어 이름은 MeSH SPARQL 로 받는다
(`ourkg/cache/mesh_tree.json`, 트리 번호 1,227 개). FoodOn 때와 같은 '공개 API +
캐시' 방식이다. 우리는 번호만 들고 **이름으로 펼치지 않고** 있었다.

결과: `out/disease_tree.csv` 2,351 행 · 질환 **242 종**, KG 에 **4,702 triple**
(`mesh:Dxxxxxx rdfs:subClassOf mesh:Dyyyyyy` + 상위 라벨). KG 총계 3,459,231 →
**3,463,933**.

`q12` 도 X 하드코딩을 걷어내고 **실제 질의**로 바꿨다 — `kg.dtree` 가 있는 KG 에서만
답하고, 없으면 그 사실을 적는다. **배포 KG 는 여전히 X 다**(`Mental_health.jsonld`
는 SCT id 와 sameAs 뿐, `MESH_Disease.jsonld` 는 C 트리만, MiKG 는 mentalDisorder
한 단계). 공개 KG 18/20 · 타당 13/20 그대로임을 확인했다.

**방법 1 재현 11 → 12/20, 타당 9 → 10/20.** 두 기준은 변동 없다(23/1 · 추천군 21 ·
비추천군 26 · 위반 0) — 질환 축은 `F` 를 건드리지 않는다.

**다만 이것은 SNOMED CT 429 만 triple 을 대체하지 않는다.** 메운 것은 `#12` 가
요구하는 **정신질환 상위 분류 축**이고, 규모 격차는 그대로다.

#### ★ FoodOn 축을 OLS 에서 받아 붙인다 — `#2` 가 열린다

`#2` 를 "축 문제" 로 닫기 전에 **상위 분류가 어디엔가 있는지** 더 찾았다. 세 군데를
봤고 답은 세 번째에 있었다.

| 출처 | soy milk 를 뭐라고 분류하나 | 쓸 수 있나 |
|---|---|---|
| FDC/WWEIA 2021-2023 | `1902 Plant-based milk` (MILK AND DAIRY > Plant-based Dairy) | 음료 아님 |
| 배포 KG `Food_Category.jsonld` | `1404 Milk substitutes` → `14 Beverages` | **1404 가 FDC 2026 에 없다** |
| **FoodOn (OLS)** | `soybean milk` < `soybean beverage` < `plant derived beverage` < **`beverage food product`** | **된다** |

USDA 문서로 확인한 것 — [2021-2023 변경표](https://www.ars.usda.gov/ARSUserFiles/80400530/pdf/2123/WWEIA%20Food%20Category%20Changes%20between%20survey%20cyles%20%202021-2023.pdf)
는 `1404 Milk substitutes` 를 **Deleted**, `1902 Plant-based milk` 를 **New** 로
적는다. 같은 표에 **Renamed** 항목(`2806`)이 따로 있으므로 USDA 는 둘을 구분해
쓴다 — **개명이 아니다.** 그래서 `1902 → 14 Beverages` 를 우리가 잇는 것은
근거 없는 추정이고, 하지 않았다.

대신 **논문이 쓴다고 한 FoodOn**(§3.1)을 제대로 붙였다. 배포 KG 의
`Food_Ontology.jsonld` 는 12,913 노드짜리 **부분집합**이라 `soy milk` 가 없고,
있는 항목조차 상위 노드의 라벨이 빠져 **계층이 끊겨** 있다(`cashew milk` 의 부모
`FOODON_00001688` 이 ID 만 존재). 우리 FoodOn triple 이 10,237(논문 79,769)이던
이유다.

EBI OLS 에서 FOODON 클래스 **28,685** 개와 매칭된 클래스의 조상 계층을 받아
`ourkg/cache/` 에 캐시한다(KEGG·NCBI·MeSH 와 같은 방식). 규칙은
`ourkg/foodon_match.py` 한 곳에 있고 **이름 일치만** 쓴다.

**커버리지를 올리며 찾은 함정 셋을 전부 막았다.**

| 단계 | 커버리지 | 막은 것 |
|---|---:|---|
| 정확 일치만 | 44.4% | — |
| + 공백 무시 | 46.0% | 한 글자 토큰이 있는 라벨은 제외 — 색소 `Green S` 가 `greens` 로 무너진다 |
| + 복수형 | 56.0% | — |
| **− EFSA·모호 클래스** | **54.9%** | `40330 - fried or extruded cereal…`(동의어 `snacks`), `black or white pepper product`(동의어 `pepper` 로 피망이 후추가 된다) |

중간에 넣었던 "FoodOn 라벨이 질의보다 좁으면 버린다" 가드는 **역효과라 폐기했다** —
`Babyfood`(214)·`Soymilk`(7) 같은 정답을 자르면서 정작 `Peppers` 는 동의어 경로로
통과시켰다.

결과: **음식 8,165 / 14,886 (54.9%) · 클래스 1,096 · 조상 포함 링크 117,554**
(`out/food_foodon.csv`). 꼬리 쪽 소수 클래스도 표본 검수했다 — `Tahini→tahini`,
`Tofu→tofu (raw)`, `Papad→poppadum`, `Sugar-apples→custard apple fruit`.

**질의도 어휘 중립으로 고쳤다.** `_beverage_subclass` 가 상위군을 `'Beverages' in c`
로 **배포 KG 철자 그대로** 요구하고 있었다. 정규식·대소문자 무시로 바꿨고,
FoodOn 이 `milk substitute` 상위를 두지 않고 plant milk 를 `plant derived
beverage` 로 묶으므로 그것도 같은 개념으로 인정한다.

**`#2` 가 O 가 됐다 — 재현 10 → 11/20.** 공개 KG 는 18/20 · 타당 13/20 그대로이고
(우리 쪽만 유리해지는 변경이 아니다) 두 기준도 변동 없다(23/1 · 추천군 21 ·
비추천군 26 · 위반 0) — FoodOn 은 `F` 를 건드리지 않는다.

#### ★ 상위 식품군을 이름 추정에서 큐레이션 링크로 바꾼다

`#2` soy milk 를 "축 문제" 로 결론 낸 뒤 원본을 더 찾아보니, **상위 분류가 배포
KG 안에 있었다.** `Food_Category.jsonld` 에 WWEIA 4 자리 코드 → SR 식품군 링크가
**118 개** 들어 있다.

```
1404 Milk substitutes  → 14 Beverages        ← #2 가 요구하는 바로 그 링크
1002 Milk, whole       →  1 Dairy and Egg Products
```

접두 규칙이 아니다 — 4 자리의 앞 2 자리가 상위와 맞는지 세어 보니 **일치 1 /
불일치 117** 이다. 손으로 이은 링크이고, 논문 §3.2 의 "self-defined mapping
rules" 가 이것으로 보인다. SR 군 이름 18 종은 우리 `FDC_CATEGORY` 와 **어휘가
완전히 일치**해서 변환 없이 붙는다. `setup/wweia_srgroup.csv` 로 고정했다.

그때까지 우리 `food_group` 은 **음식 이름 정규식**으로 추정하고 있었다
(`cheese|milk|yogurt|…` → Dairy). 이제 WWEIA 코드에 링크가 있으면 그것을 쓰고,
없으면 이름 규칙으로 떨어뜨린다. **3,343 음식**에 적용됐고 **1,131 음식(7.6%)의
군이 바뀌었다.**

| 줄어든 군 | | 늘어난 군 | |
|---|---:|---|---:|
| Dairy and Egg Products | −267 | Beverages | +272 |
| Fast Foods | −214 | Baked Products | +222 |
| Sweets | −124 | Vegetables and Vegetable Products | +156 |
| Alcoholic Beverages | −83 | Soups, Sauces, and Gravies | +86 |

이동 방향이 **이름 규칙의 알려진 오분류를 바로잡는 쪽**이다. `Dairy → Baked
Products` 62 건과 `Dairy → Vegetables` 49 건은 `cheese|milk|cream` 규칙이 크림
수프·치즈 빵을 끌어가던 것이고, `Fast Foods → Baked Products` 133 건은
`pizza|burger|sandwich` 규칙이 빵류를 패스트푸드로 보내던 것이다.

**채점은 ModiMedDiet 동일(23/1), §4.2.3 은 추천군 22 → 21 · 위반 2 → 0 이다.**
Top 30 의 **순서는 전혀 바뀌지 않았고**(`F` 가 그대로다) 군 소속만 5 건 바뀐다.

| # | 음식 | 전 → 후 | 판정 |
|---:|---|---|---|
| 7 | Fruit juice **drink** | Fruits and Fruit Juices → Beverages | 추천군 → — |
| 10 | Caramel dip, light | Sweets → Soups, Sauces, and Gravies | **위반 → —** |
| 20 | Jam | Sweets → Soups, Sauces, and Gravies | **위반 → —** |
| 27·28 | Tomato juice, 100% | Fruits and Fruit Juices → Vegetables | 추천군 유지 |

추천군이 1 내려간 것은 **분류가 정확해진 결과다.** `Fruit juice drink` 는 100%
주스가 아니라 가당 음료이고, Top 30 의 다른 항목(`Orange juice, 100%` 등)과 달리
과일군에 둘 이유가 없다. 거꾸로 딥·잼 두 건이 거짓 위반에서 벗어났다.

**`#2` 는 그래도 X 다.** WWEIA 가 `1404 Milk substitutes` 를 `1902 Plant-based
milk` 으로 **개명**했는데, 우리 FDC 2026 배포본에는 1404 가 없고 배포 KG(2022)
에는 1902 가 없다. 그래서 어느 원본에도 `1902 → 14` 링크가 없다. 우리가 이으면
개명 사실을 USDA 문서로 확인하지 않은 **추정**을 넣는 것이고, 그것은 문항 하나를
열기 위해 링크를 지어내는 일이다. 하지 않는다. 우리 WWEIA 172 코드 중 링크가
있는 것은 **116 개**이고 1902 는 그 밖의 56 개에 속한다.

#### 카테고리 철자 통합 — FDC 가 같은 카테고리를 셋으로 쪼개 놓았다

브랜드 자유문자열 `food_category_id` 는 FDC 안에서 **구분자가 세 가지**다.

```
'Meat/Poultry/Other Animals  Prepared/Processed'   9,935   공백 둘
'Meat/Poultry/Other Animals - Prepared/Processed'  7,978   하이픈
'Meat/Poultry/Other Animals – Prepared/Processed'    380   en dash
```

**16 개 카테고리 51,108 항목**이 이렇게 갈려 있었다. 우리 버그가 아니라 FDC
데이터의 결함인데 그대로 받아 쓰고 있었다.

구두점·대소문자를 지운 키로 묶고 그 안에서 **가장 많이 쓰인 철자**를 대표로
삼는다 — 표시용 라벨을 새로 지어내지 않는다. **WWEIA 카테고리를 붙인 뒤에**
돌려야 한다(먼저 돌리면 나중에 붙는 WWEIA 철자가 통합을 비켜 간다 — 실제로
`Plant-based milk` 하나가 그렇게 남았다).

결과: **29 개 철자 병합**, 세분 카테고리 266 → **265**, `foods.csv` 의 중복 쌍
3 → **0**. 어휘가 다른 두 출처도 묶인다 — WWEIA `Plant-based milk` 과 브랜드
`Plant Based Milk` 이 한 카테고리가 되어 soy milk 가 흩어지지 않는다.

F 행렬은 영향이 없고(음식 14,886 · compound 130 · 값 779,094 그대로) 두 기준도
**기준선과 완전히 같다**(23/1 · 추천군 22 · 비추천군 26 · 위반 2). 방법 1 도
10/20 · 타당 9/20 그대로다.

**`#2` soy milk 는 여전히 X 다.** 카테고리가 한 덩어리로 모였지만 그 카테고리가
`Beverages` **아래**에 있지 않다. 이름 문제가 아니라 축 문제라는 진단이 그대로
확인된 셈이다.

#### 집계 규칙 — 평균을 버리고 대표 측정치를 고른다

한 KEGG 에 FDC nutrient 가 여럿 붙는다(엽산은 DFE·total·food·folic acid 넷).
전에는 **평균**을 냈는데 서로 다른 것을 재는 값이라 어느 쪽도 아닌 수가 됐다.

```
Pie, peach 엽산   DFE 46 / total 29 / food 4 / folic acid 25  (µg/100g)
  전: 평균 26.3        후: total 29        논문 답 0.046 mg = DFE 46
```

대표를 고르는 규칙은 두 번 뒤집었다.

1. **DFE·RAE 우선** — 표준 섭취 등가이므로. → §4.2.3 추천군 23 → **18**, 위반 2 → **4**.
2. **기본 측정치 우선** (채택) — DFE 는 `food folate + 1.7 × folic acid`, RAE 는
   카로티노이드를 접은 **등가 환산값**이라 '그 KEGG 화합물의 중량'이 아니다.
   F 가 재는 것은 화합물 중량이다. 논문은 Table 2 에서 DFE 를 중량처럼 썼지만
   그 혼동을 따라가지 않는다. → 퇴행 없음(아래).

| | 기준선 | DFE·RAE 우선 | **기본 측정치 (채택)** |
|---|---:|---:|---:|
| ModiMedDiet Top30 처방/extras | 22 / 1 | 24 / 3 | **23 / 1** |
| §4.2.3 추천군 | 23 | 18 | **22** |
| 비추천군 | 26 | 26 | 26 |
| 위반 | 2 | 4 | **2** |

겸사로 `UNIT_TO_G` 의 `IU: 1e-6` 도 막았다 — 비타민 D 는 1 IU = 0.025 µg 라
**40 배** 어긋난 값이었다. 질량 측정치가 있으면 그쪽을 쓴다.

#13(정신질환 목록)은 원래 질의가 MiKG 원본 TTL 을 **파일에서 직접** 읽어 평가 대상 KG 를
거치지 않았다. 그대로 두면 공개 KG 의 답을 우리 답으로 세게 된다. `m1.q13` 이 KG 가
`mental_disorders()` 를 주면 그쪽을 쓰도록 고쳤고, 어댑터는 우리
`microbe_disease_mikg.csv` 에서 공급한다. 공개 KG 쪽은 함수가 없어 기존 경로를 그대로
타므로 18/20 은 바뀌지 않는다. **양쪽 분모가 20 으로 같다.**

#### 온톨로지 축 통합 (2026-11-09)

논문 §3.1 의 9개 소스 중 빠져 있던 넷을 레포의 공개 KG 에서 가져와 넣었다. 외부
재수집은 하지 않는다. 연결 지점을 만들려고 **세분 카테고리 층**(음식 → FDC category →
food_group)도 새로 두었다 — 논문 §3.2 의 2단 매핑 구조다.

| 소스 | 추가 triple | 우리 엔티티와의 연결 | 방법 1 효과 |
|---|---:|---|---|
| 중국 식품 온톨로지 | 82,540 | 카테고리 39 · 음식 172 | **0 문항** |
| FoodOn | 21,723 | 카테고리 19 | **0 문항** |
| KEGG brite 분류축 | 3,506 | compound 646/1,469 분류 | **+3 문항** (#14 #15 #16) |
| SNOMED CT | 285 | 질병 1 | **0 문항** |

총 triple 3,168,163 → 3,291,731.

#### 각 소스의 **원 라벨**로 맞췄다

처음에는 라벨을 우리 쪽 이름으로 기록해 매핑이 `our == onto_label` 이 돼 버려 아무
정보도 늘지 않았다. 세 가지를 고쳤다.

1. **FoodOn 동의어를 가져온다** — `hasSynonym` 3,504 · `hasNarrowSynonym` 2,535.
   라벨(3,607)만으로는 우리 카테고리와 거의 안 붙는다.
2. **매핑에 그쪽 원 라벨을 적는다** — `Melons → melon plant`, `Carrots → carrot plant`,
   `Lamb, goat, game → lamb`. 230 건 중 198 건이 우리 라벨과 다르다.
3. **괄호·꼬리말 변형으로 매칭한다** — `Soy milk (milk) beverage` → `soy milk`.

연결이 FoodOn 8→19, 중국 카테고리 20→39 · 음식 149→172 로 늘었다. 어댑터도 이 라벨을
`cats()` 에 달아 질의가 볼 수 있게 했다(`category_ontology.csv`).

**그래도 방법 1 은 8/20 그대로다.** 품질은 올랐지만 막힌 문항이 요구하는 이름이 애초에
없기 때문이다 — 아래가 그 측정이다.

**FoodOn·중국 온톨로지가 0 인 이유는 측정했다.** 막힌 문항이 요구하는 카테고리 이름이
두 온톨로지 어디에도 없다.

```
라벨 + 동의어 전수 (FoodOn 14,809 · 중국 16,091)
  "milk substitute" (#2)  → FoodOn 0건,  중국 0건
  "baby food"       (#3)  → FoodOn 0건,  중국 0건
  "soy milk"              → FoodOn 0건,  중국 2건 "Soy milk (milk) beverage"
```

중국 온톨로지는 두유를 **beverage** 로 분류하지만, #2 가 요구하는 이름은
`Milk substitutes`(구 WWEIA 명칭)이고 그 문자열은 어디에도 없다.

FDC/WWEIA 어휘이기 때문이다. 추천 점수에도 영향이 없다 — `D = E × Fᵀ` 의 입력은
영양소 중량과 E 인데 두 온톨로지에는 중량이 없다.

**SNOMED 이 0 인 이유**: 공개 KG 의 SNOMED 은 `Mental_health.jsonld` 의 284 노드뿐이고
`rdf:value`(id 문자열)와 `sameAs` 10 건만 있다. **라벨도 상위 클래스도 없다.** 논문
Table 1 이 적은 4,291,226 triple 은 배포되지 않았다. 그래서 #12(Mood / developmental
상위 분류)는 여전히 답하지 못한다 — 공개 KG 도 못 하는 문항이다.

**KEGG brite 는 효과가 있었다.** 통합 뒤 어댑터에서 두 가지를 더 고쳐야 실제로 작동했다.

1. compound 라벨을 **KEGG 원 라벨**로 쓴다. 우리 ProMENDA 이름 `Thiamine` 은 KEGG 의
   `Thiamine (Vitamin B1)` 에서 괄호 표기를 잃어, 질의가 `'Vitamin'` 으로 거르면 전부
   떨어졌다.
2. `nut2kegg` 를 음식 행렬의 compound **전부**로 채운다. 8 종만 넣었더니 q15 가 볼
   성분이 없어 alkaloid 가 빈 목록이었다.

#### 여기서 멈춘 이유 — #6·#7 은 넣으면 순환이다

남은 KEGG 문항 #6·#7 은 **compound→미생물 대사 경로**를 묻는다. 공개 KG 의
`KEGG_Compound_Bacteria.jsonld` 를 그대로 가져오면 바로 맞출 수 있다. 하지만 그건
**평가가 검증하려는 대상 자체를 논문에서 복사해 오는 것**이다. q13 이 MiKG 원본 파일을
직접 읽어 공개 KG 의 답을 우리 답으로 세던 것과 같은 오류다.

경계는 이렇게 둔다.

| 가져와도 되는 것 | 가져오면 안 되는 것 |
|---|---|
| **참조 데이터** — 분류 체계, 온톨로지 계층 (KEGG brite, FoodOn, 중국, SNOMED) | **발견 데이터** — 평가가 묻는 관계 (compound-미생물 경로, 미생물-질병 연관) |

`ourkg` 의 compound-미생물 축은 KEGG REST 에서 compound → EC → KO → organism 으로
**직접 유도**한 것이고(59 compound × 82 taxa), 논문보다 좁다. 그 좁음이 측정 결과다.

#### 재현 못 한 12문항의 내역

| 사유 | 문항 | 성격 |
|---|---|---|
| compound→미생물 대사 경로가 얇다 | #6 (#7 △) | 직접 유도의 한계. 논문 것을 복사하면 순환 |
| FDC 카테고리·명명 어휘가 바뀜 | #2 #3 | 두유는 `Plant-based milk`, baby food 는 `Baby Toddler ..., Stage 1` |
| FDC 스냅샷 값이 다름 | #4 | peach pie folate 논문 0.046 vs ourkg 0.0255 |
| 음식 라벨 부재 ("Egg whites") | #8 | 코호트 차이. 공개 KG 도 △ |
| SNOMED 라벨·계층이 배포되지 않음 | #12 | 공개 KG 도 X |
| **논문 답 자체가 결함** | **#5 #9 #10** | **실패가 아니라 교정** |

마지막 줄이 중요하다. #5 는 논문 답 `retinol 0.127 (milk)` 이 실제로는
**"Ricotta cheese, whole milk"**, `0.702 (yogurt)` 가 **"Cereal (Kellogg's Special K
Fruit & Yogurt)"** 에 붙은 것이다 — 부분 문자열 매칭 산물이라 공개 KG 에서도
`valid=X` 다. #9·#10 은 논문 Query 1 의 미결합 `?unit` 결함이 만들어 낸
"달걀 값 + 아무 음식 값" 조합을 그대로 재연하는 문항이다(`eval/m1.py` 의 `_mixed_diet`).
우리 KG 는 중량 노드를 음식에 묶어 두었으므로 그런 조합이 **존재하지 않는다.**
논문 답을 재현하지 못하는 것이 올바른 동작이다.

반대로 #18(대장균 계통)은 예전 판에서 측면 단위로 O 였는데 실제 질의로는 어댑터를
고치기 전까지 틀렸다 — `bpar` 를 taxid 가 아니라 이름으로 키잉했기 때문이다. 측면
집계로는 이런 오류가 드러나지 않는다.

#### 단위

우리 long 표는 g, 공개 KG 는 FDC 원 단위(mg/µg)다. 공통 음식에서 잰 배율은
lysine·retinol·vitc·potassium·b12 모두 10³ 이었다(중앙값 747~1335, 흩어짐은 FDC
스냅샷 차이). 어댑터는 ×1000 으로 맞춘다. 8종 중 citric(C00158)·B-6 는 우리
long 표에 없어 축이 7/8 이다.

### 방법 2 (문헌 논증) — 추론 15건 PubMed 검증

논문은 수작업 검색으로 11 confirmed / 3 unknown / 1 contradicted 를 보고한다.
여기서는 E-utilities 로 자동화한다. `ourkg/out/eval_method2.csv`

#### 2026-11-09 — 자가 달랐다

그 전까지 "우리 1/15 vs 논문 11/15" 로 적어 두고 우리 쪽 결함으로 읽었다.
**비교 자체가 성립하지 않았다.** 우리 판정은 *두 엔티티 + 근거 물질* 세 항이 모두
함께 나오는 논문을 요구하는데, 논문의 판정 기준은 명시돼 있지 않다.

그래서 **우리 기준을 논문 자신의 15 건에 적용**해 보정값을 얻었다
(`eval_method2_calibration.csv`).

| 기준 | 우리 15건 | 논문 15건 |
|---|---:|---:|
| 3항 공출현 (엄격) | **2/15** | **1/15** |
| 2항 공출현 (논문에 가까움) | **14/15** | **13/15** |
| 논문이 보고한 값 | — | 11/15 |

**엄격 기준으로는 논문 자신도 1/15 다.** 논문이 보고한 11/15 는 2항 기준(13/15)에
가깝다 — 즉 두 엔티티가 함께 나오는 문헌을 찾아 사람이 읽고 판정한 것이다.

같은 자로 재면 `ourkg` 는 **14/15 로 논문(13/15)과 대등하다.** 예전의 "1/15" 는
능력 차이가 아니라 자의 차이였다.

#### 2026-11-17 — 두 자 중 쓸 수 있는 것이 없다

위 표는 "자가 달랐다"까지만 말한다. **두 자가 논문 자신의 라벨을 얼마나 가르는지**를
재면 둘 다 쓸 수 없다. 논문 Table 5 의 confirmed 11 건과 non-confirmed 4 건
(unknown 3 + contradicted 1)에 각 자를 댄 결과다.

| 기준 | confirmed 11건 중 통과 | non-confirmed 4건 중 통과 |
|---|---:|---:|
| 3항 공출현 | **1 / 11** | 0 / 4 |
| 2항 공출현 | 10 / 11 | **3 / 4** |

- **2항은 논문 값(11/15)에 가깝지만 판별을 못 한다.** 논문이 confirmed 아니라고 한
  4 건 중 3 건도 통과시킨다. `Anxiety AND depression` 이 194,413 건이니, 이 자가
  재는 것은 관계의 근거가 아니라 **두 주제가 함께 연구되는가**다.
- **3항은 논문 자신의 confirmed 11 건 중 1 건만 통과시킨다.** 신호가 없다.

분야별로 실패 위치가 다르다.

| | n | 3항 | 2항 |
|---|---:|---:|---:|
| 우리 Complication | 8 | 0 | 8 |
| 우리 Diet | 7 | 2 | 6 |
| 논문 Complication | 8 | 1 | 7 |
| **논문 Diet** | 7 | **0** | 6 |

#### ★ 2026-11-18 — 초록을 읽게 하니 판별력이 생긴다

"초록 판독이 필요해 자동화로 못 고친다" 는 틀렸다. `efetch` 로 초록을 받아
**문장 단위로** 보면 된다. 두 엔티티가 한 문장에 함께 나오고 연관 표현
(`associat|correlat|risk|comorbid|increas|…`)이 있으면 +1, 부정 표현
(`no significant association|not associated|failed to|…`)이면 −1 이다.
논문 15 건으로 세 자를 같이 쟀다.

| 기준 | confirmed 11 통과 | non-confirmed 4 통과 | 균형정확도 |
|---|---:|---:|---:|
| 3항 공출현 | 1/11 | 0/4 | 0.55 |
| 2항 공출현 | 10/11 | 3/4 | 0.58 |
| **초록 판독** | **10/11** | **1/4** | **0.83** |

민감도는 2항과 같은데 특이도가 산다. **색인 공출현 두 자는 버리고 초록 판독으로
교체했다** — 3항은 쿼리에서 뺐고(근거 이름을 넓혀도 0/7 이었다), 2항 적중 수는
`n_hits_pair_only` 로 참고만 남긴다.

논문 15 건을 우리 자로 재면 **11/15** 가 통과한다. 논문이 보고한 값도 11/15 다.

#### 어간 매칭이 느슨해 위양성이 있었다 — 고쳤다

처음 판에서는 우리 15 건이 13/15 였는데 인용문을 읽으니 근거가 아니었다.
`Mustard greens × depression` 이 *"mustard oil 로 내장통증을 유발했다"* 는
자극제 실험으로, `Pork × depression` 이 우울증 병력이 적힌 증례 보고로 잡혔다.
세 가지가 겹친 문제다.

| 문제 | 고친 방법 |
|---|---|
| 어간을 몇 글자로 잘라 매칭 (`Mustard` → `musta`) | **온전한 단어**로 맞춘다. 복수·소유격만 허용 (`\bmustard(s\|es\|'s)?\b`). autistic/autism 처럼 어미가 갈리는 질환명만 공통 어간 |
| 음식이 식이가 아닌 맥락으로 등장 (자극제·시약) | 음식 행은 문장에 **식이 맥락**(`diet\|intake\|consum\|…`)이 함께 있어야 센다 |
| `inbreeding depression`(근친교배 약세)을 우울증으로 셈 | 동형이의어 수식어 목록으로 그 문장을 버린다 (`st-segment`·`spreading`·`respiratory` 등도) |
| 증례 보고를 연관의 근거로 셈 | `PublicationType` 이 `Case Reports` 인 논문을 뺀다 |

여기에 두 가지를 더 했다. **여러 단어 이름은 구(句)로** 맞춘다(사이에 한 단어까지).
가장 긴 단어 하나만 쓰면 `Sex behavior disorder` 가 "REM sleep **behavior**
disorder" 를 잡는다. 그리고 **인용문을 두 엔티티가 가장 가까이 붙은 문장의 매치
주변**으로 고른다 — 첫 매치의 문장 앞 90 자를 쓰면 정작 두 엔티티가 나온 대목이
잘려 근거가 약해 보인다.

**논문 15 건의 판별력은 네 번의 수정 내내 0.83 그대로다**(10/11 vs 1/4).
우리 15 건은 13 → **8/15** 로 내려갔고, 남은 +1 의 인용문이 실제 근거로 바뀌었다.

```
Pork        …high monthly pork consumption (OR = 1.608)…
Beverages   …association between sugar-sweetened beverages (SSBs) and depression…
Bipolar     Is increased sexual behavior a symptom of bipolar disorder in children…
Anx × Pers  Patterns of anxiety and personality disorder comorbidity.
```

숫자가 내려간 것이 개선이다 — 13 중 5 건이 근거 없는 통과였다.

#### ★ -1 을 만들려 했고, 못 만들었다 (2026-11-20)

우리 15 건에 **-1(반대 증거)이 한 건도 안 나오는** 것이 남은 결함이었다.
`judge()` 에 -1 분기는 **이미 있었다**(`neg > pos`). 원인을 수치로 재니 셋이었다.

1. **NEG 어휘가 거의 안 걸렸다** — 30 건 중 음성 문장이 잡힌 행이 **1 행**.
   초록은 앞 문장에서 개체를 말하고 다음 문장에서 "No significant association
   was observed." 처럼 **개체 이름 없이** 끊어 쓴다.
2. **판정이 사실상 "연관 문장이 하나라도 있는가"였다** — `pos` 가 19·25·45 까지
   가는데 `neg` 는 0~1 이라 **한 건의 음성 증거로는 절대 못 뒤집는다**.
3. 혼합 문장이 음성으로 빠졌다 (`if NEG … elif ASSOC` 순서).

**고친 것 넷.** 검색 사다리를 **두 항 모두**에(꼬리의 `products`/`disorder`/
`disease` 를 떨군다), **문장 쌍 창**(개체는 앞 문장까지, 단서는 이 문장에서),
**NEG 어휘 확장**(특히 *보정 후 소실* — 논문 #10 의 -1 근거가 이것이다),
**개수 비교 → 비율**(`neg/(pos+neg) ≥ NEG_RATIO`).

| 구성 | 논문 15 일치 | `#10` Egg (정답 -1) | `#8` Garlic (정답 1) |
|---|---:|---|---|
| 시작 | 12/15 | 0 (초록 **1 건**) | 1 ✓ |
| + 사다리·창·NEG | 12/15 | **1 ✗** | 1 ✓ |
| **+ 독립 토큰** | **12/15** | **0** | 1 ✓ |
| + 독립 토큰 + 구간 | **11/15** | 0 | **0 ✗** |

**양성 조이기 둘 중 하나만 채택했다.**

- **독립 토큰 제약 — 채택.** 개체 매치가 하이픈으로 복합어에 묶여 있으면 뺀다.
  논문 #10 에서 `egg` 가 `vegetable-egg-beans-milk dietary pattern` 의 조각으로
  걸렸는데, 그 문장은 달걀이 아니라 **식이 패턴**을 말한다. **비용 없이 거짓
  양성만 제거**한다.
- **구간 제약 — 기각.** 연관 어휘가 두 개체를 걸치는 구간에 있을 때만 세는 규칙.
  #6 의 나열(`AD, PD, and ASD`)을 6→1 로 줄이지만 **#8 을 깬다.** 마늘 연구는
  `garlic extract`·`allicin` 으로 쓰지 `dietary` 를 안 써서, **식이 맥락 게이트와
  곱해지면** 통과 문장이 전부 떨어진다. `ASSOC_SPAN=1` 로 되돌릴 수 있다.

**`NEG_RATIO` 민감도 — 어떤 값도 돕지 않는다.**

| `NEG_RATIO` | 0.05 | 0.1 | 0.2 | 0.3 | 0.5(기본) |
|---|---:|---:|---:|---:|---:|
| 논문 15 일치 | 10 | 11 | 11 | 12 | 12 |
| -1 판정 | 3 | 2 | 2 | 1 | 0 |

-1 이 나오는 행은 **엉뚱한 행**(Learning disabilities × depression, 정답 0)이다.

#### 결론 — "-1 을 만든다" 는 목표 자체를 기각한다

**정답이 -1 인 사례가 전 세계에 1 건**(논문 #10)이다. 1 건으로는 어떤 문턱도
검증할 수 없고, 맞추려 들면 그 건에 과적합한다. **데이터의 한계로 적는다.**

**얻은 것은 점수가 아니라 근거의 질이다.** 논문 15 건 일치는 12/15 로 시작과
같지만 구성이 다르다 — `#11`(Coffee × Parkinson)이 **초록 0 건의 검색 실패**에서
20 건을 읽은 판정으로 바뀌었고(대신 `#6` 이 깨졌다), `#10` 의 양성이 엉뚱한
문장에서 온 것임이 드러났고, 음성 증거가 1 → **5 행**에서 CSV 에 남는다.

> 외부에서 -1 정답셋을 만드는 길은 있다 — Cochrane 리뷰의 "no evidence" 결론을
> 음성 정답으로 쓰는 것. 별도 과제 규모다.
>
> **갱신 (2026-11-25).** 그 길은 **접는다.** Cochrane 의 "insufficient evidence"
> 는 *치료 효과*에 근거가 없다는 뜻이고 *관계가 없다*는 뜻이 아니다 — 증거의
> 부재를 부재의 증거로 쓰는 셈이다 (§41 ①). 합병증 추론 쪽은 그 대신 **라벨
> 없는 진단**으로 답이 나왔는데(§41 ③), 여기 방법 2 는 사정이 다르다 —
> 집합 포개짐 문제가 아니라 **3 항이 문헌에 함께 안 나오는** 문제다. 그래서
> 방법 2 는 지표로 쓰지 않는다는 결론이 그대로다 (§18·§28).

#### 질환 쌍 제약은 재어 보고 기각했다

`Personality disorder × Sleep disorders` 의 인용문이 아직 약하다 — 여러 질환이
**나열된** 문장이다. 그래서 질환 쌍에만 거는 제약 둘을 논문 15 건으로 쟀다.

| 변형 | confirmed | non-conf | 균형정확도 |
|---|---:|---:|---:|
| **제약 없음 (현재)** | **10/11** | 1/4 | **0.83** |
| + 나열 제외 (두 엔티티 사이에 동사가 없으면 버림) | 8/11 | 1/4 | 0.74 |
| + 쌍 전용 cue (`comorbid\|co-occur\|…` 만, 치료 효과 제외) | 9/11 | 1/4 | 0.78 |
| + 둘 다 | 8/11 | 1/4 | 0.74 |

**둘 다 참을 떨어뜨리기만 한다.** 나열 문장을 버리면 `Alzheimer × autism` 같은
실제 confirmed 가 같이 날아간다 — 공통 기전을 다루는 리뷰가 질환을 나열하기
때문이다. 기각하고, 대신 인용문으로 사람이 보게 둔다.

참고로 위양성으로 보이던 `Learning disabilities × depression`(논문 라벨 0)의
인용문은 *"Depression among students with learning disabilities"* 다. 문헌이
실제로 있고, 논문이 0 으로 둔 쪽이 보수적이었을 수 있다.

그래도 이 8/15 를
논문의 11/15 와 **순위처럼 비교하지는 않는다.** 판별력은 논문의 라벨 분포에서 잰
값이고, `quote`·`sent_assoc`·`sent_negative` 로 사람이 검수하는 용도다.

#### 그 0/7 은 표기 문제가 아니었다

논문 Diet 7 건의 근거 표기가 문헌 표기와 어긋나 보였다 — `Threonine` 과
`L-Threonine` 을 따로 쓰고, `Ascorbate`(문헌은 ascorbic acid), `alpha-Tocopherol`.
그래서 3항 쿼리의 근거 이름을 한 번 넓혀 재 봤다 — 입체·염·locant
접두어(`L-` `alpha-` `11Z-` …) 제거와 `-ate` ↔ `-ic acid` 호환을 OR 로 묶어
우리 15 건과 논문 15 건에 같이 적용했다.

**30 행 전부 수치가 같았다** — 논문 Diet 여전히 0/7, 전체 1/15, 우리 2/15.
`("Ascorbate" OR "Ascorbic acid")` 로 넓혀도 `Onion AND depression` 과 함께
나오는 논문은 없다. **3항이 0 인 것은 검색어 표기가 아니라 기준 자체 때문이다.**
문헌에 음식·질환·물질 세 항이 한 논문에서 함께 명시되는 일이 드물다.

효과가 0 이므로 **그 확장은 코드에서 걷어냈다.** 쿼리 빌더는 `pubmed()` 하나,
자는 3항·2항 둘이다. 측정했고 아무것도 바뀌지 않았다는 사실만 남긴다 — 음성
결과를 코드 분기로 보존할 이유가 없다.

→ 남은 길은 초록 판독(논문이 한 것)이고, 자동화로는 대체되지 않는다. 방법 2 의
수치는 **둘 중 어느 자로도 품질 지표로 쓰지 않는다** — §6.3 의 모드 선택에
방법 2 를 쓰지 않은 이유가 이것이다.

#### 표본·검색어도 고쳤다

| | 전 | 후 |
|---|---|---|
| 근거 물질 고유 수 | 11 종 (15건 중 4건이 `Palmitic acid`+소고기) | **15 종** |
| 음식 검색어 | FDC 첫 구간 그대로 | **일반명 사다리** — `Mustard greens`(0건) → `Mustard`(194건) |
| 브랜드 토큰 | 남음 (`FUZE`, `McDONALD'S`) | 제거. 첫 구간이 브랜드뿐이면 다음 구간 |
| 세균 | 균주명 (`Lactococcus lactis subsp. lactis`) | **종 수준** (`Lactococcus lactis`) |

근거: 논문 Table 5 의 Diet 행이 `Garlic`·`Milk`·`Coffee`·`Lettuce`·`Onion` 처럼
일반명이고, Complication 행의 세균이 `Bifidobacterium longum`·`Escherichia coli`
처럼 종 수준이다. 같은 수준으로 맞춘 것이다.


### ★ 비교표 셋을 다시 쟀다 (2026-11-20)

`e_mode_comparison` · `fcolumns_comparison` · `invert_comparison` 이 **집계 수정·
WWEIA 군 링크·KG/F 층 분리·미생물 축 확장 이전** 수치였다. `RESULTS` 가 그 표들을
인용하고 있었으므로 전부 다시 쟀다.

`fcolumns_comparison.csv` 는 **만드는 스크립트가 저장소에 없었다** — 과거 임시
스크립트로 만들고 CSV 만 커밋한 것이라 아무도 다시 만들 수 없었다.
`ourkg/sweep.py fcolumns` 로 고정했다.

#### E 구성 방식 (`analyze.py compare`)

| e_mode · path | 비영 compound | §4.2.3 추천군 | 비추천군 | 위반 | MMD 처방/extras | AUC |
|---|---:|---:|---:|---:|---:|---:|
| **shrunk · direct (기본)** | 66 | **21** | **26** | **0** | **24 / 1** | 0.462 |
| shrunk · gutbrain | 35 | 20 | 20 | 0 | 24 / 1 | 0.454 |
| binary · direct | 66 | 20 | 20 | 0 | 23 / 3 | 0.455 |
| weighted · direct | 98 | 3 | 7 | **25** | 27 / 1 | 0.603 |
| vote · direct | 95 | 8 | 8 | 0 | 26 / 4 | **0.664** |

옛 표에서 `shrunk direct` 는 추천군 7 · 비추천군 27 이었다. 지금은 **21 · 26 ·
위반 0** 이다. **AUC 가 가장 높은 `vote direct`(0.664)의 §4.2.3 추천군은 8** 이고
기본 설정이 21 이다 — §13 의 "AUC 는 맨 위에 무엇이 오는지에 둔감하다" 가 그대로
재현된다.

`gutbrain` 경로가 compound 35 로 `direct`(66)의 절반인데 성적이 거의 같다 —
미생물 축을 162 종으로 넓힌 결과다.

#### F 열 × PCA (`ourkg/sweep.py fcolumns`)

| F 열 | PCA | AUC | 추천군 | 비추천군 | 위반 | MMD 처방/extras | Top 1 |
|---|---|---:|---:|---:|---:|---:|---|
| **linked** | **0 (기본)** | 0.585 | **21** | **26** | **0** | **23 / 1** | 야채주스 |
| linked | 5 | 0.698 | 3 | 19 | 9 | 7 / 12 | 칠면조 껍질 |
| linked | auto | 0.693 | 0 | 16 | 1 | 0 / 18 | 크림 리큐어 |
| all | 0 | 0.631 | 5 | 25 | 12 | 4 / 17 | 설탕 대체재 |
| all | 5 | 0.697 | 2 | 22 | 9 | 9 / 6 | 밀기울 머핀 |
| **all** | **auto** | **0.706** | **22** | 14 | 1 | **23 / 0** | 파프리카 |

**`all + auto` 가 요약 수치로는 기본값과 맞먹는다** — 추천군 22(기본 21) ·
MMD 23/0(기본 23/1) · AUC 0.706(기본 0.585). 옛 표에서 `all auto` 는 추천군
7 이었으니 집계·카테고리·미생물 축 수정이 누적된 결과다.

#### `all + auto` 를 Top 30 으로 다시 재고 기각했다

요약 수치가 가린 것이 있어 실제 목록을 봤다.

| | 기본 `linked+0` | 후보 `all+auto` |
|---|---|---|
| Top 1~5 | 야채주스 · 오렌지주스 · 게맛살 · 과일음료 · 샐러드 | **파프리카 · 칠리파우더 · 오레가노 · 타임 · 카이엔** |
| Top30 군 분포 | 채소 10 · 과일 10 · 음료 3 · 소스 2 · **어패류 1** | **채소 22** · 향신료 5 · 스낵 1 · 제과 1 · 이유식 1 |
| Bottom 5 | 볼로냐 · 소갈비 · 척아이롤 · 안심 | 칠면조 ×2 · **살코기 97% 간 소고기 ×3** |
| 비추천군 | **26** | 14 |

**세 가지가 걸린다.**

1. **상위 5 개가 전부 말린 향신료다.** 100 g 당 성분 농도가 극단적으로 높아
   성분 중량 기반 점수에서 위로 몰린다 — 1 회 섭취량이 1 g 미만인 것들이다.
2. **추천군 22 가 거의 전부 채소 한 군에서 나온다.** 논문 §4.2.3 서술은
   "어패류·과일·채소" 인데 **어패류 0 · 과일 0** 이다. 기본값은 채소 10 ·
   과일 10 · 어패류 1 로 세 군을 모두 덮는다.
3. **바닥이 저지방 육류다.** 논문이 비추천으로 든 소시지·제과·과자류가 아니라
   살코기 97% 간 소고기가 깔린다. 비추천군이 26 → 14 로 반 토막 난다.

AUC 가 0.585 → 0.706 으로 오르는 것은 §13 에서 확인한 대로 **Top-K 품질과
어긋나는** 지표다. **기각하고 `F_COLUMNS=linked` + `PCA_COMPONENTS=0` 을 유지한다.**

#### 역추정 (`analyze.py invert`)

held-out 음식 4,300 에서 전체 파이프라인 AUC **0.682**. §4.2.3 독립 체크는
Top30 추천군 9 / Bottom30 비추천군 18.

로그가 참고값을 **하드코딩**하고 있었다(`vote direct 0.665 / shrunk 0.491`).
데이터가 바뀌면 낡으므로 `e_mode_comparison.csv` 에서 읽어 오게 고쳤다.

### ★ PCA 재측정 (2026-11-18) — AUC 만 오르고 Top-K 는 무너진다

§12 의 PCA 수치는 `F_COLUMNS` 제한·집계 수정·WWEIA 군 링크 **이전**에 잰 것이고
주지표도 AUC 였다. 지금 데이터로 다시 쟀다 (재구축 없이 `recommend` 만 4 회).

| `PCA_COMPONENTS` | MMD 처방/extras | AUC | §4.2.3 추천군 | 비추천군 | 위반 | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| **0 (기본)** | **23 / 1** | 0.585 | **21** | **26** | **0** | 야채주스 |
| 5 (논문 §4.2.1 의 숫자) | 7 / 12 | 0.698 | 3 | 19 | 9 | 칠면조 껍질 |
| 10 | 0 / 18 | 0.693 | 0 | 16 | 1 | 크림 리큐어 |
| auto (분산 80% → 10 성분) | 0 / 18 | 0.693 | 0 | 16 | 1 | 크림 리큐어 |

**켜면 두 기준이 동시에 무너진다.** 처방군 23 → 7 → 0, 추천군 21 → 3 → 0 이고
`auto` 의 Top 1 은 크림 리큐어다. 오르는 것은 **AUC 뿐**(0.585 → 0.698) —
AUC 가 가장 높은 설정의 Top 30 이 처방 0 / extras 18 이고 1 위가 술이라는 §13 의
관찰이 그대로 재현된다.

**정정.** 이전 기록은 "`auto`(10 성분)가 AUC 0.714 에 교차 위반 0 으로 두 기준
모두에서 낫다" 였다. 지금은 성립하지 않는다. 설계 결정 #7(PCA 를 끈다)과 #8(기본값
5)이 서로 모순된 채 남아 있던 것도 이번에 확인해 #8 을 이 측정으로 교체했다.

기본값은 `PCA_COMPONENTS=0` 그대로다. 논문 **본문**(PCA 를 쓰라)과 논문 **결과**
(§4.2.3 서술)가 어긋날 때 결과 쪽을 따른다는 판단은 바뀌지 않는다.

### ★ `SHRINK_K` 민감도 — 처음 재 봤다 (2026-11-18)

`설계 결정 #4` 의 `SHRINK_K=10` 은 **실행 전에 고정**한 값이고 민감도를 잰 적이
없었다. `build.py promenda` 만 다시 돌리면 되므로(로컬 엑셀만 읽는다) 쟀다.

| `K` | 중앙 \|E\| | MMD 처방/extras | §4.2.3 추천군 | 비추천군 | 위반 | AUC |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (축소 없음 = `e_binary`) | 1.000 | **7 / 9** | **8** | 27 | 1 | 0.582 |
| 2 | 0.333 | 14 / 4 | 15 | 26 | 2 | 0.587 |
| 5 | 0.167 | 20 / 2 | 19 | 26 | 2 | 0.589 |
| **10 (현재 기본)** | 0.091 | **23 / 1** | **22** | 26 | 2 | 0.590 |
| **20** | 0.048 | **23 / 1** | **22** | 26 | 2 | 0.590 |
| 50 | 0.020 | 20 / 3 | 19 | 26 | 2 | 0.590 |
| 100 | 0.010 | 20 / 3 | 19 | 26 | 2 | 0.589 |

**1. 축소는 이 파이프라인에서 효과가 가장 큰 개선이다.** `K=0` 은 논문 §4.2.1 의
`e_binary` 와 같은 상태인데 ModiMedDiet 처방군이 **7/30**, §4.2.3 추천군이
**8/30** 이다. 켜면 23/30 · 22/30 이 된다.

**2. 꼭대기가 평평하다.** `K=10` 과 `K=20` 이 완전히 같고 양쪽으로 멀어지면
내려간다. 특정 값에 과적합된 설정이 아니다.

**3. `K=10` 은 결과를 보고 고른 값이 아니었고, 재 보니 평탄 구간 안이었다.**
운이 좋았던 것이고 그렇게 적는다. 바꿀 이유는 없다.

**4. 비영 compound 수는 `K` 와 무관하다**(1,287 고정, `K=0` 만 1,294). 축소는
방향을 지우지 않고 **크기만** 줄인다. `K=0` 에서 1,294 인 것은 `pos==neg` 인 7 개가
0 이 되지 않기 때문이다.

**5. AUC 는 거의 움직이지 않는다**(0.582~0.590). Top30 이 7/9 에서 23/1 로 바뀌는
동안 0.008 이다 — §13 에서 주지표를 Top-K 로 바꾼 이유가 다시 확인된다.

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

## 13b. ★ ModiMedDiet 을 빈도 가중으로 바꾸고, 지표의 진짜 결함을 찾았다 (2026-11-20)

### 왜 손댔나

ModiMedDiet 정답셋이 처방군/extras **이분법**이었다. 그러면 채소(주 42회)와
lean red meat(주 3-4회)가 같은 `+1` 이 되어 **정답셋이 처방 강도를 잃는다.**
SMILES 는 빈도 처방이므로 그 기울기를 그대로 쓰는 것이 맞다.

규칙의 `src` 문자열에 이미 적혀 있던 빈도를 `MODIMED_FREQ` 로 옮겼다
(범위는 중앙값: `5-8/day` → 45.5/주).

| 군 | 주당 | | 군 | 주당 |
|---|---:|---|---|---:|
| 통곡물 | 45.5 | | 달걀 | 6 |
| 채소 | 42 | | 콩류 | 3.5 |
| 과일 · 올리브유 | 21 | | 살코기 적색육 | 3.5 |
| 저지방 무가당 유제품 | 17.5 | | 닭고기 | 2.5 |
| 생견과 | 7 | | 생선 | 2 |
| | | | **extras** | **0** |

**extras 를 0 으로 둔다.** `≤3/주` 는 **상한**이지 처방량이 아니다. 상한 3 을
그대로 쓰면 생선(주 2회)보다 위에 놓인다. `MODIMED_EXTRAS_FREQ` 로 바꾼다.

### 결과 ① — 전역 순위 상관은 AUC 와 똑같이 실패한다

§13 에서 AUC 가 Top-K 와 어긋났던 설정 넷으로 쟀다
(`python3 ourkg/sweep.py modimed_rho` → `out/modimed_rho_comparison.csv`).

| 설정 | Top30 추천군 | Bot30 비추천군 | AUC(참고) | ρ 처방군 | ρ 전체 | **ρ 상위200** |
|---|---:|---:|---:|---:|---:|---:|
| `all+auto`(§12 에서 기각) | 22 | 14 | 0.539 | 0.382 | 0.224 | **+0.354** |
| **기본 `linked+0`** | **21** | **26** | 0.462 | **0.316** | 0.072 | **−0.070** |
| `all+0` | 5 | 25 | 0.492 | 0.371 | 0.139 | **−0.328** |
| `linked+PCA` | **0** | 16 | 0.544 | 0.332 | 0.215 | **−0.562** |

**전역 ρ 는 추천군 0 개인 `linked+PCA` 와 5 개인 `all+0` 를 기본값(21)보다
위에 놓는다.** AUC 와 거의 같은 순서다.

### ★ 진단을 정정한다 — 라벨이 아니라 **구간**이 문제였다

"이분법이라 순서의 가운데를 못 본다" 고 적었던 것은 **틀렸다.** 빈도 가중으로
가운데를 보게 만들어도 순서가 그대로 뒤집힌다. 문제는 가운데를 못 보는 것이
아니라 **맨 위를 안 보는 것**이었다. AUC 도 전역 ρ 도 음식 8,553 개의 순서를
재므로 상위 30 개에 무엇이 오는지에 둔감하다.

### 결과 ② — 상위 구간만 보면 뒤집히지 않는다

`MODIMED_RHO_TOP=200` 으로 상위 200 개 안에서만 재면
(기본 설정에서 그중 164 개에 빈도가 붙는다),

**ρ 상위200 의 순서가 Top30 추천군 순서와 4/4 일치한다.**
`all+auto`(22) > 기본(21) > `all+0`(5) > `linked+PCA`(0).

전역 지표 둘이 모두 뒤집은 순서를 상위 구간 ρ 는 보존한다.

### 채택 범위

- **빈도 가중 자체는 채택한다.** 라벨이 SMILES 에 더 충실해지고, `modimed_score`
  가 ρ 를 함께 내므로 기존 비교표들에 그대로 들어간다.
- **전역 ρ 는 AUC 와 같이 `(참고)` 다.** 설정 선택에 쓰지 않는다.
- **ρ 상위200 은 쓸 수 있는 지표다** — 다만 **n=4 설정에서 본 일치**이고,
  `all+auto` 를 기본값보다 위에 놓는다. 그 설정은 §12 에서 Top 30 을 직접 보고
  기각했다(상위 5 개가 1 회 섭취량 1 g 미만인 말린 향신료, 어패류 0 · 과일 0).
  **수작업 검수를 대체하지 못하고, 추천군 개수의 대리 지표로 쓴다.**

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

## 15b. ★ 논문 Fig.4(c) — 빠뜨렸던 성분군 비교를 했다 (2026-11-20)

논문을 다시 대조하다 찾았다. Fig.4(a) PCA 와 Fig.4(b) t-SNE 는 했는데 **(c) 만
빼놓고 있었다.** 이것은 §4.2.3 이 추천 결과의 **근거로 쓰는 그림**이다 — compound 를
생물학적 역할로 6 군으로 묶어 추천군과 비추천군의 조성을 비교한다.

재료는 이미 있었다(`out/compound_class.csv` 의 KEGG brite, FDC 영양소 이름).
`python3 ourkg/analyze.py groups` → `out/group_comparison.{csv,png}`.

### 정규화 기준이 두 가지로 읽힌다

논문은 "we normalize the compounds in the two groups of foods separately" 라고만
쓴다. 문자 그대로는 **군 안에서 전체 최대값으로** 나누는 것인데, 그러면 전분·
포도당(g)이 최대라 **mg·µg 단위 성분이 전부 0 에 깔린다** — 비타민·미량원소 칸이
양쪽 모두 0.000 이 된다. 그림에는 그 칸들에도 진한 칸이 있다. 그래서 기본값을
**compound 별 정규화**(`GROUP_NORM=compound`)로 뒀고, 문자 그대로의 쪽도
`GROUP_NORM=group` 으로 잴 수 있게 남겼다.

### 결과 — 논문의 세 주장 중 둘이 재현되고, 하나는 **부호가 반대다**

| 성분군 | n | 추천군 | 비추천군 | 차 | p | 논문 §4.2.3 |
|---|---:|---:|---:|---:|---:|---|
| **탄수화물** | 7 | 1.000 | 0.011 | **+0.989** | 0.0009 | "carbohydrates" ✓ |
| **비타민·조효소** | 25 | 0.677 | 0.321 | **+0.356** | 0.014 | "vitamins" ✓ |
| 다량무기질 | 5 | 0.889 | 0.506 | +0.382 | 0.12 | "macronutrients" **✗ 부호 반대** |
| 미량원소 | 6 | 0.565 | 0.429 | +0.136 | 0.74 | "trace elements" **✗ 부호 반대** |
| 지질 | 39 | 0.510 | 0.649 | −0.139 | 0.15 | "nonsignificant lipids" ✓ |
| **아미노산** | 21 | 0.235 | 0.963 | **−0.728** | 4e-08 | "nonsignificant amino acids" **✗** |

**둘은 그대로 재현된다.** "추천군이 탄수화물·비타민이 높다" 는 우리 데이터에서도
유의하다 — 탄수화물은 사실상 완전 분리(1.000 vs 0.011)다.

**둘은 부호가 반대다.** 논문은 비추천군이 미량원소·다량영양소가 높다고 했는데
우리는 **추천군이 높다**. 둘 다 유의하지 않으므로(p 0.12 · 0.74) "반대 방향의
유의한 결과" 가 아니라 **신호가 없는 자리**로 읽어야 한다. 논문이 이 자리에서
방향성 주장을 한 것은 표본 135 개의 노이즈일 가능성이 있다.

**하나는 논문이 "유의하지 않다" 고 한 곳에서 우리가 가장 강한 신호를 얻었다.**
아미노산이 비추천군에서 압도적이다(0.963 vs 0.235, p=4e-08). 우리 비추천군 바닥이
육류·소시지라 단백질 성분이 몰린 결과다 — 논문은 이 차이를 "원본 데이터의 결측"
탓으로 돌렸는데, 결측을 메운 우리 데이터에서는 **실재하는 차이**로 나온다.

### 이것이 지표를 하나 늘린다

§13 에서 AUC 가 Top-K 품질과 어긋난다고 결론 낸 뒤, 설정을 고를 때 쓸 수 있는
것이 **Top 30 수작업 검수뿐**이었다. 성분군 비교는 Top-K 목록을 직접 보지 않고도
조성이 무너졌는지 볼 수 있는 두 번째 눈이다.

---

## 15c. ★ gut-brain 경로를 추천에 넣어 보고 기각했다 (2026-11-20)

### 왜 손댔나

논문 §4.2.2 의 식 (1)(2) 에는 **미생물이 없다.** 그래서 KG 최대 소스인 VMH
44,094 쌍이 추천 점수에 **0 기여**한다 — §1·§3.1 이 내세우는 gut-brain axis 가
알고리즘에 연결되지 않는다. 기존 `PATH_MODE=gutbrain` 은 미생물을 안 거치는
compound 의 `E` 를 **0 으로 죽이는** 이분법이라 compound 가 절반으로 줄고
Top-K 가 흔들렸다.

### 설계 — 죽이지 않고 가중한다

```
w[c] = 1 + ALPHA · s[c]        s[c] ∈ [0, 1]
e'   = e ⊙ w
D    = e' × Fᵀ                 (이후는 논문 식 그대로)
```

`s[c]` 는 그 compound 를 대사하는 **정신질환 연관 균의 수**를 0~1 로 민 값이다.
정신질환 연관 균은 배포 `Disease_Bacteria`(MeSH F03) ∪ **Disbiome**(질환 23 종 ·
균 457 종)을 합쳐 쓴다. `ALPHA=0` 이면 `w` 가 전부 1 이라 **논문 경로와 완전히
같다**(기본값, 결과가 한 글자도 안 바뀜을 확인했다).

| 환경변수 | 기본 | 뜻 |
|---|---|---|
| `GUTBRAIN_ALPHA` | `0` | 가중 세기. 0 = 끔 |
| `GUTBRAIN_SOURCE` | `both` | `kegg` / `vmh` / `both` |
| `GUTBRAIN_RANK` | `species` | `all` 이면 속 수준 매칭도 (KEGG 링크의 55%) |
| `GUTBRAIN_SCALE` | `count` | `binary` / `log` |

`ALPHA=1` 에서 우울증 연결 compound 66 개 중 **42 개**가 미생물 경로를 갖는다
(경로당 균 중앙값 70).

### 결과 — 네 지표 모두 단조 악화

`python3 ourkg/sweep.py gutbrain` → `out/gutbrain_comparison.csv`

| `ALPHA` | Top30 추천군 | Bot30 비추천군 | Top30 위반 | MMD 처방군 | MMD extras | AUC(참고) |
|---:|---:|---:|---:|---:|---:|---:|
| **0 (논문 경로)** | **21** | **26** | **0** | **24** | **1** | **0.462** |
| 0.5 | 19 | 24 | 0 | 23 | 2 | 0.458 |
| 1 | 19 | 24 | 0 | 23 | 2 | 0.456 |
| 2 | 17 | 21 | 0 | 21 | 3 | 0.455 |
| 4 | 16 | 20 | 1 | 20 | 4 | 0.453 |
| 8 | 16 | 21 | 1 | 20 | 4 | 0.452 |

**예외 없이 단조다.** §4.2.3 두 기준, ModiMedDiet 두 지표, AUC 참고값이 전부
`ALPHA=0` 에서 최고다. §13 이후 처음으로 **AUC 와 Top-K 가 같은 방향**을 가리킨다.

**기본값 `ALPHA=0` 을 유지하고 기능은 선택지로 남긴다.**

### ★ 잴 자를 외부에서 만들었다 — 프로바이오틱스 RCT (2026-11-20)

처음에는 "두 평가 기준이 모두 compound 직접 경로로 만들어진 자라 이 가중이
옳은지 잴 자가 우리에게 없다" 고 적었다. **그 자를 만들었다.**

#### 정답표 — `setup/probiotic_rct.csv`

PMC 가 봇 차단(reCAPTCHA)을 걸어 메타분석 본문을 못 읽는다. **E-utilities 로
직접 만든다** — 재현 가능하고 차단이 없다 (`ourkg/probiotic_rct.py build`).

```
(probiotic* OR Lactobacillus OR Bifidobacterium OR …)
  AND (depression OR depressive OR anxiety)
  AND randomized controlled trial[pt] AND humans[mh]
→ RCT 203 편 → 초록에서 종명 추출 → NCBI taxonomy 해소
→ 25 종 · RCT 178 편 연결
```

| RCT | 종 | | RCT | 종 |
|---:|---|---|---:|---|
| 27 | *Bifidobacterium longum* | | 13 | *Lactobacillus acidophilus* |
| 22 | *Lacticaseibacillus rhamnosus* | | 13 | *Limosilactobacillus reuteri* |
| 21 | *Lactiplantibacillus plantarum* | | 13 | *Bifidobacterium animalis* |
| 15 | *Lactobacillus helveticus* | | 13 | *Lacticaseibacillus casei* |

> **개명 함정을 두 번 넘었다.** ① `[Scientific Name]` 정확 검색은 개명된 종을
> 전부 버린다 — `L. rhamnosus`(14편)·`L. casei`(13)·`B. lactis`(10) 가 통째로
> 빠졌다. 필드 제한을 풀고, 돌려받은 taxid 의 rank 를 확인해 아종·균주면 **종
> 수준 조상**으로 올라가게 했다(`B. lactis` → *B. animalis*).
> ② `L. plantarum`·`L. reuteri` 는 **옛 이름이 NCBI 검색 색인에서 아예 빠졌다.**
> taxid 레코드의 **동의어 목록**으로 확인했다 — `Lactobacillus reuteri Kandler
> et al. 1982` → 1598. [`DATA.md`](DATA.md) §6 의 개명 함정과 같은 자리다.

> **이 목록은 "효과가 입증된 균" 이 아니다.** RCT 에서 **시험된** 균이다.
> 메타분석 풀링 효과는 SMD −0.34(95% CI −0.76~0.09, **유의하지 않음**, I²=75%)
> 이고 균주별 결론은 저자들도 잠정적이라고 적는다. 그 전제로 읽어야 한다.

#### 검정 ① 커버리지 — 21/25, 그 전부 compound 연결 있음

**갱신 (2026-11-24)**: 축이 798 종으로 늘어 *B. bifidum*(9편)이 들어왔다 —
**21/25 (84%)**, 그 21 종 **전부** compound 연결이 있다. 빠진 4 종은
*L. helveticus*(15편) · *Lc. casei*(13) · *L. paragasseri*(1) ·
*L. crispatus*(1). **미생물 축은 이 자로 합격이다.**

(그 전 485 종 축에서는 20/25 였다.)

#### 검정 ② gut-brain 가정 — 약하고 일관되지 않다

"RCT 로 시험된 균이 우리 `E>0` compound 를 더 대사하는가" 를 순열 검정으로
봤다 (`ourkg/probiotic_rct.py test`, 무작위 n 종 × 2000 회).

| 통계량 | 485 종 축 (n=20) | **798 종 축 (n=21)** |
|---|---|---|
| 대사 compound 의 평균 E | −0.0195 vs −0.0257±0.0041 · **p=0.013** | −0.0194 vs −0.0287±0.0055 · **p=0.005** |
| E>0 비율 | 0.489 vs 0.483±0.006 · p=0.183 | 0.489 vs 0.481±0.0076 · p=0.132 |

**축을 1.6 배로 늘려도 그림이 그대로다** — 두 통계량 중 하나만 유의하고 효과
크기가 매우 작다(둘 다 음수 구간).

p 가 0.013 → 0.005 로 내려간 것을 "효과가 커졌다" 로 읽으면 안 된다. **관측값은
−0.0195 → −0.0194 로 사실상 그대로**다. 움직인 것은 **귀무 평균**이다
(−0.0257 → −0.0287) — 비교 모집단이 378 → 565 종으로 늘면서 평균 E 가 낮은 균이
많이 들어왔다. 즉 RCT 집합이 좋아진 게 아니라 **비교 상대가 달라졌다**. 표준편차는
0.0041 → 0.0055 로 넓어졌으니 그것만으로는 p 가 올라갔어야 한다.

#### 검정 ③ 외부 목록으로 가중해도 결과가 같다

`GUTBRAIN_MICROBES=rct` 로 **우리 Disbiome/F03 집합 대신 외부 RCT 목록**으로
가중했다 (`WHO=rct python3 ourkg/sweep.py gutbrain`).

| `ALPHA` | Top30 추천군 | Bot30 비추천군 | MMD 처방군 | extras | AUC |
|---:|---:|---:|---:|---:|---:|
| **0** | **21** | **26** | **24** | **1** | 0.462 |
| 1 | 18 | 22 | 22 | 2 | 0.455 |
| 4 | 18 | 19 | 22 | 2 | 0.451 |
| 8 | 18 | 21 | 22 | 2 | 0.449 |

`mental` 집합과 **같은 방향으로 단조 악화**다.

#### 검정 ④ 측정된 분변 대사체로 링크를 검정했다 — **음성**

해석 둘 중 2 번("우리 링크가 너무 거칠다")을 직접 쳤다. 필요한 것은 **측정값**
이다. [Gut Microbiome-Metabolome Dataset Collection](https://www.nature.com/articles/s41522-022-00345-5)
(Muller et al., npj Biofilms Microbiomes 2022) 이 짝지어진 분변 마이크로바이옴 +
대사체 14 코호트를 통일된 형식으로 큐레이션해 뒀고, **`mtb.map.tsv` 가 대사물을
KEGG id 로 직접 매핑**하므로 우리 축에 변환 없이 붙는다
(`ourkg/metabolome_check.py`).

**우울증 코호트는 이 모음에 없다.** 대신 둘을 쓴다 — **자폐**(우리 KG 의 F03
질환이고 Disbiome 에서 균 203 종으로 가장 두껍다)와 **IBS**(gut-brain disorder,
샘플 444). 우울증 전용은 MTBLS12050 이 있으나 EBI API 가 401 을 돌려주고 공개
FTP 경로도 404 다.

검정 — **우리가 예측한 (속, compound) 쌍이 측정에서도 더 강하게 연관되는가.**
부호는 보지 않는다: 대사는 소비(음)일 수도 생산(양)일 수도 있어 `|ρ|` 를 쓴다.

| 코호트 | 샘플 | 예측 쌍 | 평균 \|ρ\| 예측 / 나머지 | MW p | 순열 p |
|---|---:|---:|---|---:|---:|
| `KANG_AUTISM_2017` | 44 | 458 | 0.1449 / 0.1524 | 0.818 | 0.889 |
| `MARS_IBS_2020` | **444** | 557 | 0.1008 / 0.1073 | 0.978 | 0.959 |

**두 코호트 모두 음성이다.** 우리가 "이 균이 이 compound 를 대사한다" 고 예측한
쌍이 무작위 쌍보다 **더 연관되지 않는다** — 오히려 약간 낮다.

IBS 에서 전체 p<0.05 쌍 비율이 **0.41** 이다. 데이터에 강한 구조가 있는데
(n=444 라 검정력도 충분하다) **우리 링크가 그 구조와 무관하다.**

> **한계 셋.** ① 우울증 코호트가 아니다(자폐·IBS). ② 코호트가 속 수준까지만
> 주어 우리 종 수준 링크를 **속으로 올려** 맞췄다 — 종 수준 특이성이 희석된다.
> ③ 상관은 대사가 아니다. 다만 **예측 링크가 무작위와 구별되지 않는다**는
> 결론에는 ③ 이 영향을 주지 않는다.

#### 검정 ⑤ 측정 상관으로 링크를 **교체**해 봤다 — 역시 안 된다

검정 ④ 가 "우리 링크가 측정과 무관하다" 를 보였으니 다음은 당연히 **측정에서
링크를 만드는 것**이다 (`ourkg/metabolome_check.py build`).

**재현성을 두 겹으로 요구했다.** 한 코호트 안에서는 다중검정으로 상관이 쉽게
나온다(IBS 에서 BH 전 p<0.05 쌍이 41% 였다). 그래서 ① 코호트 안 BH q<0.05,
② 서로 다른 **2 개 이상** 코호트에서 **같은 부호로** 유의할 것을 요구한다.
부호를 맞추는 것은 소비/생산 방향이 코호트마다 뒤집히면 잡음이기 때문이다.

| 단계 | 수 |
|---|---:|
| 13 코호트 전체 (속, compound) 쌍 | 2,684,126 |
| BH q<0.05 | 437,149 |
| **2+ 코호트에서 같은 부호로 재현** | **39,574** (속 1,859 · compound 315) |

(`iHMP_IBDMDB_2019` 는 HTTP 오류로 빠졌다 — 대사물 81,867 짜리라 파일 구성이
다르다.)

| | 쌍 | 균 | compound |
|---|---:|---:|---:|
| 현행 예측 (KEGG 추론 ∪ VMH) | 52,998 | 379 | 1,113 |
| **측정 상관** (우리 taxid 로 펼침) | 7,052 | 298 | 252 |
| **두 집합의 교집합** | **916 (13%)** | | |

부호는 **음 26,196 / 양 13,378** 로 소비 방향이 2 배다 — 대사 상식과 맞는다.

**네 구성으로 쓸었다** (`python3 ourkg/sweep.py gutbrain`). `ALPHA=1` 기준:

| 구성 | Top30 추천군 | Bot30 비추천군 | 위반 | MMD 처방군 | extras |
|---|---:|---:|---:|---:|---:|
| **기준 `ALPHA=0`** | **21** | **26** | **0** | **24** | **1** |
| `mental` (KEGG∪VMH) | 19 | 24 | 0 | 23 | 2 |
| `mental/kegg` | 18 | 21 | 0 | 22 | 2 |
| **`mental/measured`** | **17** | 27 | 1 | 20 | 4 |
| `rct` | 18 | 22 | 0 | 22 | 2 |

**측정 링크가 예측 링크보다 낫지 않다** — 추천군이 오히려 가장 낮다(17).
비추천군만 27 로 유일하게 기준(26)을 넘지만 위반이 1 로 올라가 상쇄된다.
네 구성 모두 `ALPHA=0` 이 최고다.

#### 결론을 바꾼다

**검정 ③ 이 결정적이다.** 아래 §15c 에서 "평가 자가 편향돼서 그렇다" 고 적었는데,
**가중할 균 집합 자체를 외부 임상 근거로 바꿔 봤고 결과가 같았다.** 평가 자의
편향만으로는 설명되지 않는다.

해석은 둘이었다 — (1) 미생물 매개 경로가 실제로 기여하지 않거나, (2) 우리
compound-미생물 링크가 너무 거칠거나.

**검정 ④ 는 2 번을 지지했고, 검정 ⑤ 가 그것을 뒤집었다.** 측정에서 직접 만든
링크로 바꿔도 결과가 같다. 링크 품질만의 문제가 아니다.

**남는 가장 단순한 설명은 1 번이다 — 미생물 매개 가중이 `D = E × Fᵀ` 구조
안에서는 기여할 수 없다.** 이유는 구조를 보면 분명하다: 가중은 `e` 를 곱해
**compound 축의 상대 비중만** 바꾼다. 그런데 Top-K 를 지배하는 것은 **음식의
성분 중량**(`F` 는 g/100 g)이고, compound 비중을 어떻게 흔들어도 중량이 큰
성분이 계속 이긴다. 미생물 정보가 들어갈 자리가 **곱셈 한 번**뿐이다.

미생물을 실제로 쓰려면 `E`·`F` 를 곱하는 자리가 아니라 **점수 산출 구조 자체**를
바꿔야 한다 — 예컨대 음식 → 균 → 질환 경로를 따로 점수화해 합치는 식이다.
그것은 논문 Algorithm 1 이 아니고, 평가할 자도 아직 없다.

> **그래도 측정 링크 자체는 남길 가치가 있다.** 13 코호트 · 268 만 쌍에서 BH
> 보정과 코호트 간 재현으로 걸러 만든 것이라, 추천 가중에 못 쓰더라도 KG 의
> **독립적인 근거 축**이 된다. KEGG 추론·VMH 예측과 13% 만 겹치므로 서로를
> 보완한다. `출처: 측정 상관` 으로 KG 에 담았다.

### ★ 범인은 유사도 행렬이었다 (2026-11-23)

"구조 때문" 이라고 적고 넘어갔는데 **어디가** 구조인지는 안 짚었다. 쟀다.

| `ALPHA` | 전체 순위상관 | Top100 겹침 | Top30 겹침 |
|---:|---:|---:|---:|
| 1 | **0.9976** | 85/100 | 24/30 |
| 8 | **0.9907** | 62/100 | 20/30 |

**가중을 9 배로 걸어도 순위가 사실상 그대로다.** 미생물 정보가 점수에 거의
전달되지 않는다.

```
S 비영 비율 0.993      (12,420 x 12,420 중 99.3% 가 비영)
P = D x S
```

`S` 가 거의 **꽉 찬 행렬**이다. 그러면 `P = D x S` 는 각 음식 점수를 **전체
`D` 의 가중 평균**으로 만든다 — `D` 안의 compound 별 변조가 평균에 묻힌다.
§8·§10 에서 "유사도 단계가 신호를 깎는다" 고 적었던 것이 이것이고, 미생물
가중도 **같은 자리에서 지워진다.**

### 검정 ⑥ 미생물 축에 신호가 있는가 — E_microbe 유도

구조를 고치기 전에 **미생물 축에 신호가 있는지부터** 봤다. 알고리즘을 안
바꾸고 답할 수 있는 질문이다 (`python3 ourkg/analyze.py emicrobe`).

> compound `c` 를 대사하는 균이 우울증에서 **감소**한다면 `c` 는 이로운 쪽인가?
> 그렇게 만든 `E_microbe` 가 ProMENDA 의 `E` 와 일치하는가?

**방향 가정은 검증 대상이지 전제가 아니다.** "감소=이로움" 과 그 반대를 둘 다
쟀다. 부호일치 0.5 가 우연이고, 두 가정이 대칭이라 **크기**를 봐야 한다.

| 질환 범위 | 링크 | 방향 가정 | compound | 부호일치 | p | ρ |
|---|---|---|---:|---:|---:|---:|
| 정신질환 전체 | KEGG∪VMH | 감소=이로움 | 355 | 0.504 | 0.46 | **−0.132** |
| 정신질환 전체 | **측정** | 감소=이로움 | 202 | **0.569** | **0.029** | 0.033 |
| 우울증만 | KEGG∪VMH | 감소=이로움 | 181 | 0.475 | 0.77 | −0.095 |
| **우울증만** | **측정** | **감소=이로움** | 164 | **0.585** | **0.017** | 0.069 |

**세 가지가 나온다.**

1. **방향 가정은 맞는 쪽이 있다.** "우울증에서 감소한 균이 대사하는 compound 가
   이롭다" 가 유의하다(p 0.017~0.029). 반대 가정은 전부 p≈0.98 로 기각된다.
2. **단, 측정 링크에서만 나온다.** KEGG∪VMH 로는 부호일치 0.504(우연)이고
   **ρ 가 −0.13 으로 오히려 반대**다. 검정 ④ 의 "예측 링크가 측정과 무관하다"
   가 여기서도 재확인된다.
3. **효과 크기가 매우 작다.** 0.585 는 우연 대비 +8.5%p, ρ 는 0.069 다.
   "신호가 0 은 아니다" 수준이지 강한 독립 근거가 아니다.

**그래서 다음 수가 바뀐다.** 미생물 경로를 별도 점수로 내 순위를 융합하는
설계는 바탕 신호가 ρ=0.07 이라 **섞어도 잡음만 더할 공산이 크다.** 먼저
`SIM_THRESHOLD` 로 `S` 를 희소하게 만들어 **`D` 의 변조가 살아나는지**부터
봐야 한다 — 그것이 위 진단의 검증이기도 하다.

### 검정 ⑦ 유사도를 희소하게 만들어 봤다 — 기각, 그리고 **더 큰 것이 드러났다**

위 진단("`S` 가 꽉 차서 `D` 의 변조가 묻힌다")을 검증하는 자리다. `S` 를 상위
k 이웃만 남기면 `D` 의 변조가 살아나야 한다 (`python3 ourkg/sweep.py simthr`).

| 설정 | Top30 추천군 | Bot30 비추천군 | AUC(참고) | Top 1 |
|---|---:|---:|---:|---|
| **`none` (현행)** | **21** | **26** | 0.462 | 야채주스 |
| `positive` | **0** | 26 | 0.459 | 라이트 맥주 |
| `q50` | **0** | 26 | 0.456 | 몰트 맥주 |
| `q90` | **0** | 26 | 0.453 | 하드 셀처 |
| `topn:1000` | **0** | 29 | 0.513 | 몰트 맥주 |
| `topn:100` | **0** | 12 | 0.534 | Glug(글뤼바인) |
| `topn:30` | **0** | 13 | 0.538 | 위스키 사워 |

**예외 없이 추천군 0 이고 상위가 전부 술이다.** MMD 처방군도 24 → 0 이다.
`ALPHA=0` vs `2` 차이도 여전히 미미하다 — 미생물 변조는 살아나지 않는다.
(AUC 는 0.462 → 0.538 로 **오른다.** §13 의 역행이 또 재현됐다.)

#### 원인 — 첫 가설은 틀렸고, 진짜는 `E` 에 있다

"희소 조성 음식이 뜬다" 고 추측했는데 **상위 10 의 성분 수가 전부 48 로 전체
중앙값과 같다.** 틀렸다.

실제 원인은 `E` 가 **에탄올과 설탕을 이롭다고 표시**하는 것이다.

```
C00469  Alcohol, ethyl   e_shrunk = +0.200
C00089  Sucrose          e_shrunk = +0.259
```

`S` 가 꽉 차 있을 때는 전체 평균에 묻혀 드러나지 않다가, 희소화하면 **칵테일
끼리 서로를 강화**한다 — 이웃 100 개가 전부 다른 칵테일이니 그 안에서 양의
`D` 가 증폭된다.

> **★ 그래서 §15b 의 진단에 대한 답은 이렇다.** "`S` 가 꽉 차서 `D` 변조가
> 묻힌다" 는 **맞다.** 다만 그 평활화가 **`E` 의 오류를 가려 주고 있었다.**
> 희소화는 미생물 변조를 살리기 전에 에탄올·설탕 오류를 먼저 살린다.
>
> **지금 기본 설정이 잘 도는 것은 유사도 평활화가 그 오류를 덮고 있기
> 때문이고, 이것은 우연에 기대는 상태다.** 미생물 구조보다 `E` 의 극성이
> 먼저 고칠 자리다.

### 검정 ⑧ 에탄올·설탕을 지워 봤다 — 진단은 절반만 맞았다

검정 ⑦ 이 "유사도 평활화가 `E` 의 에탄올·설탕 오류를 덮고 있다" 로 끝났다.
그 말이 맞다면 그 둘의 `E` 를 0 으로 둘 때 **기본(`none`)에서는 거의 안 바뀌고
희소화(`topn:100`)에서는 크게 바뀌어야** 한다. `E_ZERO` 로 쟀다
(`python3 ourkg/sweep.py ezero`).

| 설정 | Top30 추천군 | Bot30 비추천군 | 위반 | MMD 처방군 | extras | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| `none` 원본 | **21** | 26 | 0 | **24** | 1 | 야채주스 |
| `none` **E_ZERO** | **17** | 26 | 0 | 21 | 2 | 야채주스 |
| `topn:100` 원본 | 0 | 12 | 0 | 0 | 16 | Glug(글뤼바인) |
| `topn:100` **E_ZERO** | 0 | 11 | **10** | 12 | 8 | 브랜플레이크 |

**맞은 것** — 희소화 상태에서 술이 사라진다. Top 1 이 Glug → 브랜플레이크로
바뀌고 MMD 처방군이 0 → 12 로 오른다. 에탄올·설탕이 술을 1 위로 올린 원인이
맞다.

**틀린 것** — **기본 설정에서도 영향이 작지 않다.** 추천군이 **21 → 17** 로
떨어진다. "평활화가 덮고 있어 기본에서는 거의 안 바뀔 것" 이라던 예측이
어긋났다. 그리고 희소화 쪽은 고쳐도 여전히 못 쓴다 — 추천군 0 이고 **위반이
0 → 10 으로 폭증**한다(제과·육류가 상위에 들어온다).

#### ★ 현재 점수는 "맞는 이유로 맞는" 상태가 아니다

에탄올·설탕의 `+` 극성은 **틀렸지만, 지우면 결과가 나빠진다.** 기본 설정의
추천군 21 은 **그 틀린 양수에 일부 기대고 있다** — 설탕 양수가 과일·주스를
밀어 올리기 때문이다. 의존 크기는 **추천군 4 개**다.

§9 의 결론(ProMENDA 의 up/down 은 식이 효과 소스가 아니다)이 Top-K 수준에서
구체적으로 드러난 자리다. 혈중 에탄올이 우울증 환자에서 높은 것은 **술을 더
마셔서**이지 에탄올이 이로워서가 아닌데, 우리 `E` 는 그것을 +0.200(근거 5 건 ·
연구 3)으로 읽는다.

**그래서 `E_ZERO` 를 기본값으로 켜지 않는다.** 켜면 측정값이 나빠지고, 켤
근거가 "에탄올이 양수인 게 이상하다" 는 판단뿐이다. 대신 이 의존을 **기록해
둔다** — 설정을 고를 때 이 점을 모르면 21 이라는 숫자를 잘못 읽게 된다.

진짜 해결은 §9 가 말한 대로 **섭취-결과를 재는 소스**로 `E` 를 바꾸는 것이다.
`E_MODE=learned`(ModiMedDiet 역추정)가 그 방향인데 §12 에서 더 나빴다.

### 아래 §15c 의 "잴 자가 없다" 는 이제 성립하지 않는다

### ★ 그런데 이 결과를 "gut-brain 가중이 틀렸다" 로 읽으면 안 된다

**두 평가 기준이 모두 compound 직접 경로로 만들어진 자다.**

- §4.2.3 서술은 논문이 **`D = E × Fᵀ`** 로 얻은 결과를 묘사한 것이다. 그 자로
  재면 같은 경로를 쓰는 설정이 이기는 것이 당연하다.
- ModiMedDiet 은 임상 식단이라 독립적이지만 라벨이 **음식군 단위**라 미생물
  매개 효과를 가릴 해상도가 없다.

즉 **미생물 매개 가중이 옳은지를 잴 자가 우리에게 없다.** 가중을 걸면 기존
자에서 멀어지는 것은 당연하고 그게 틀렸다는 뜻이 아니다. §13 에서 AUC 를
참고값으로 내린 것과 같은 종류의 문제다.

재려면 **미생물 매개 효과를 직접 측정한 외부 기준**(프로바이오틱스 RCT,
분변 대사체-우울증 코호트)이 필요하다.

> **★ 정정 (2026-11-20).** 그 외부 기준을 만들었다 — 프로바이오틱스 RCT 203 편
> 에서 뽑은 25 종(`setup/probiotic_rct.csv`). **가중할 균 집합을 외부 임상
> 근거로 바꿔도 결과가 같았다.** 위 "잴 자가 없다" 는 더 이상 성립하지 않고,
> 기각 근거가 평가 자의 편향이 아닌 것으로 좁혀졌다. 위 절을 보라.

---

## 15d. ★ E 를 섭취-결과 소스로 바꿨다 — NHANES (2026-11-23)

### 왜

검정 ⑧ 이 "현재 점수가 `E` 의 소스 불일치에 일부 기댄다" 로 끝났다. ProMENDA 의
up/down 은 "우울증 환자에서 이 대사물의 **농도**가 높다" 이지 "그것을 **먹으면**
좋다" 가 아니다(§9). 진짜 해결은 **섭취-결과를 재는 소스**로 바꾸는 것이다.

**NHANES** 는 같은 사람에게서 24 시간 식이회상과 PHQ-9 우울 척도를 잰다
(`ourkg/nhanes.py`). 섭취와 결과를 직접 잇는다.

```
NHANES 2017-2018 — DR1TOT(영양소 67 열) + DPQ(PHQ-9) + DEMO
→ 표본 4,774 (18세 이상) · PHQ-9>=10 이 425 (8.9%)
→ compound 47 추정, q<0.05 가 24
```

**보정**: 나이 · 성별 · **총열량**(log) · 소득(PIR). 총열량 보정이 핵심이다 —
안 하면 "많이 먹는 사람" 효과가 모든 영양소에 공통으로 실린다(영양역학의 표준).
부호는 우리 규약에 맞춘다 — 섭취가 늘수록 PHQ-9 가 낮으면 `+`(이로움).

의존성을 안 늘리려고 `statsmodels` 대신 **numpy 로 다중회귀를 직접** 구현했다
(계수·표준오차·t 검정, 15 줄). README 의 설치 목록을 늘리면 재현이 그만큼
번거로워진다.

### 개별 극성은 ProMENDA 보다 타당하다

| compound | β | q | E |
|---|---:|---:|---:|
| 엽산 | **−0.680** | <0.0001 | **+1.000** |
| 칼륨 | −0.549 | <0.0001 | +0.808 |
| 루테인+제아잔틴 | −0.451 | <0.0001 | +0.663 |
| 철 · 마그네슘 · 비타민 C · K | −0.30~−0.42 | <0.05 | + |
| **포화지방 18:0** | **+0.570** | <0.0001 | **−0.838** |

문헌과 맞고, **포화지방 9 종 전부** 일관되게 해롭다고 나온다. 결정적으로
**에탄올 부호를 바로잡는다**: ProMENDA +0.200(이로움) → NHANES −0.085(해로움).
설탕(`C00089`)은 NHANES 가 총당류만 주고 자당을 따로 안 줘 추정치가 없다.

ProMENDA 와의 부호일치는 **0.517(우연)**, ρ=+0.297 이다. 두 소스가 **다른 것을
재고 있다**는 §9 의 결론과 일치한다.

### 그런데 Top-K 에서는 진다

`python3 ourkg/sweep.py emode`

| E 모드 | Top30 추천군 | Bot30 비추천군 | 위반 | MMD 처방군 | extras | AUC(참고) | Top 1 |
|---|---:|---:|---:|---:|---:|---:|---|
| **`shrunk` (현행)** | **21** | **26** | **0** | **24** | **1** | 0.462 | 야채주스 |
| `binary` | 20 | 19 | 0 | 23 | 3 | 0.455 | 야채주스 |
| `nhanes` | 10 | **5** | 0 | 14 | 7 | 0.654 | 인스턴트 아침식사 분말 |
| `nhanes_all` | 19 | **2** | 3 | 21 | 5 | 0.673 | 고단백 영양 분말 |
| `learned` | 9 | 18 | 13 | **30** | 0 | **0.687** | 대구 |

**추천 쪽은 `nhanes_all` 이 거의 따라온다**(19 vs 21). **비추천 쪽이 무너진다**
(26 → 2~5). 상위 1 위가 **영양 강화 분말**이다 — NHANES `E` 가 엽산 +1.000,
칼륨 +0.808 처럼 미량영양소에 큰 양수를 주는데, 강화 분말은 그것들이
**g/100 g 기준으로 극단적으로 높다.**

(AUC 는 0.462 → 0.673 으로 크게 오른다. §13 의 역행이 또 재현됐다.)

### ★ 같은 벽에 두 번째로 부딪혔다 — 범인은 `F` 의 100 g 기준이다

**기본값으로 채택하지 않는다.** 다만 "NHANES 가 틀렸다" 가 아니다 — 개별
극성은 ProMENDA 보다 타당하다. **지는 이유가 `E` 가 아니라 `F` 다.**

| 기각된 설정 | 상위를 차지한 것 | 공통 원인 |
|---|---|---|
| `all+auto` (§12) | 말린 향신료 (파프리카·오레가노) | g/100 g 당 농도가 극단 |
| `E_MODE=nhanes` (여기) | 영양 강화 분말 | 〃 |

둘 다 **1 회 섭취량이 작은데 100 g 당 농도가 높은** 식품이다. `E` 를 고쳐도
`F` 의 중량 스케일이 Top-K 를 지배한다. 다음에 볼 것은 **1 회 섭취량(serving
size) 기준의 `F`** 다.

```bash
python3 ourkg/nhanes.py                           # E 산출
E_MODE=nhanes_all python3 ourkg/analyze.py recommend
python3 ourkg/sweep.py emode                      # 위 표
```

---

## 15e. ★ 서빙 기준 F 를 재고 기각했다 — 진단이 반증됐다 (2026-11-23)

### 가설

§15d 가 "`E` 를 고쳐도 `F` 의 중량 스케일이 Top-K 를 지배한다" 로 끝났다.
기각된 설정 둘이 같은 꼴이었다 — `all+auto` 는 말린 향신료, `E_MODE=nhanes` 는
영양 강화 분말이 상위를 차지했고 **둘 다 1 회 섭취량이 작은데 100 g 당 농도가
높은 식품**이다.

`F` 는 g/100 g 이라 "100 g 먹었을 때" 를 가정한다. 실제 섭취량으로 바꾸면 이
왜곡이 사라질 것인가.

### 서빙 데이터

FDC `food_portion.csv`(survey + sr_legacy). **논문을 벗어난다** — §4.1.2 는
"each food instance's unit weight is standardized to 100 g" 라고 명시한다.
그래서 `F_SCALE` 의 선택지로 두고 기본값은 `per100g` 다.

| | |
|---|---|
| portion 행 | 37,158 (고유 음식 13,129) |
| **추천 코호트 커버리지** | **6,970 / 12,513 (56%)** |
| 서빙 중앙값 | 117 g (25% 57 g · 75% 199 g) |

| 음식군 | 서빙 중앙값 | | 음식군 | 서빙 중앙값 |
|---|---:|---|---|---:|
| **향신료·허브** | **4.2 g** | | 음료 | 192.8 g |
| 유지류 | 14.0 g | | 수프·소스 | 215.5 g |
| 스낵 · 견과 | 28.4 g | | 레스토랑 | 200.0 g |
| 제과 | 36.4 g | | 소고기 | 187.0 g |

**향신료와 수프가 51 배 차이다.** 100 g 고정이 파프리카를 24 배 과대평가하고
있었다는 뜻이다. 결측 44% 는 음식군 중앙값으로 메웠다.

### 결과 — 반증됐다

`python3 ourkg/sweep.py fscale`

| 설정 | Top30 추천군 | Bot30 비추천군 | 위반 | MMD 처방군 | extras | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| **`per100g`/`shrunk` (현행)** | **21** | **26** | **0** | **24** | **1** | 야채주스 |
| `per100g`/`nhanes_all` | 19 | 2 | 3 | 21 | 5 | 고단백 분말 |
| **`serving`/`shrunk`** | **14** | **2** | 1 | 22 | 0 | 야채주스 |
| **`serving`/`nhanes_all`** | **2** | 4 | 5 | 10 | 5 | 유청 단백 분말 |

가설이 맞다면 `serving`+`nhanes_all` 에서 비추천군이 **회복**돼야 했다.
**회복은커녕 추천군이 19 → 2 로 무너진다.** Top 1 은 영양 분말에서 유청 단백
분말로 바뀌었을 뿐이다. `shrunk` 에서도 비추천군이 **26 → 2** 로 붕괴한다.

### 왜 틀렸나

서빙으로 곱하면 음료·수프(193~216 g)가 1 이상으로 커지고 향신료(4.2 g)가
0.04 배로 줄어든다. 향신료는 눌렀지만 **비추천군인 제과(36 g)·스낵(28 g)·견과도
같이 눌러** 바닥에서 사라지게 만든다. 비추천군 26 → 2 가 그것이다.

> **100 g 고정이 향신료를 과대평가한 것은 맞다. 그런데 그 왜곡이 비추천군
> 탐지에는 도움이 되고 있었다** — 소시지·제과가 100 g 기준이라 바닥에 머물렀다.

**"같은 벽" 이라고 묶었던 두 기각(`all+auto` 향신료, `nhanes` 분말)이 서로 다른
원인임이 드러났다.** 서빙으로 둘 다 해결되지 않는다.

### 남은 불확실성

서빙 결측 **44%** 를 음식군 중앙값으로 메웠다. 같은 군 안에서 실제 서빙이 다른
음식들이 같은 값을 받는다 — 이 근사가 결과를 얼마나 흔드는지는 재지 않았다.
위 수치는 그 불확실성을 안고 있다.

**기각한다.** `F_SCALE=serving` 은 선택지로 남기고 기본값은 `per100g` 다.

---

## 17. ★ 주지표가 잡음이었다 — Top-K 지표의 표집 변동 (2026-11-23)

### 재 본 적이 없던 것

지금까지의 채택·기각이 대부분 **"추천군 21 vs 19" 같은 차이 2~5** 위에 서
있는데, **그 차이가 잡음인지 잰 적이 없다.** Top 30 은 칸이 30 개뿐이라 음식
몇 개만 바뀌어도 쉽게 흔들린다.

음식을 **비복원 부분표집**해 다시 돌렸다 (`python3 ourkg/bootstrap.py`).
복원추출은 같은 음식이 여러 번 뽑혀 Top-K 칸을 중복 점유하므로 순위 문제에서
지표가 부풀려진다. 한 번 돌리는 데 3.5 초라 반복이 싸다.

| 부분표집 | 추천군 중앙값 | 범위 | 비추천군 중앙값 | 범위 |
|---|---:|---|---:|---|
| 100% | 21 | — | 26 | — |
| **95%** | **21** | **[6, 22]** | 26 | **[25, 27]** |
| 90% | 20 | [7, 22] | 26 | [25, 29] |
| 80% | 18 | [4, 23] | 26 | [22, 29] |

**중앙값에는 편향이 없다** — 95% 에서도 21·26 그대로다. **문제는 분산이다.**
음식을 **5% 만 빼도 추천군이 6 까지 떨어진다**(폭 16). 반면 비추천군은
[25, 27](폭 2)이고 위반은 [0, 1](폭 1)이다.

### 왜 추천군만 흔들리나

§17b 에서 Top 30 의 내용을 보면 답이 나온다 — **추천군 21 중 12 개가 주스**이고
그중 오렌지주스만 4 종이다. **거의 같은 음식의 변종**이라 부분표집으로 몇 개가
빠지면 한꺼번에 무너진다. 비추천군(소시지·제과·육류)은 서로 다른 음식이라
그렇지 않다.

### 주지표를 바꾼다

**`비추천군` 과 `위반` 이 주지표다. `추천군` 은 참고값이다.**
추천군 차이가 **5 이하면 잡음 구간**이라 그것만으로 채택·기각하지 않는다.
`sweep.py` 의 표도 열 순서를 바꿔 비추천군이 먼저 읽히게 했다.

### 기존 결정의 재검토

| 기각 | 추천군 차이 | 비추천군 차이 | 다시 읽은 결과 |
|---|---:|---:|---|
| `all+auto` (§12) | 1 | **12** | **유지** — 비추천군 근거가 유효 |
| gut-brain `ALPHA=1` (§15c) | 2 | 2 | **근거 약함** — 둘 다 잡음 구간. 단조 추세(ALPHA 8 까지)가 남은 근거다 |
| `E_MODE=nhanes_all` (§15d) | 2 | **24** | **유지** — 비추천군 26 → 2 |
| `serving/shrunk` (§15e) | 7 | **24** | **유지** |
| `linked+PCA` (§13) | 21 | 10 | **유지** |

**대부분의 기각이 비추천군 근거로도 성립한다.** 다만 **gut-brain 가중만은
근거가 약해진다** — `ALPHA=1` 의 차이는 잡음이고, 기각 근거는 "`ALPHA` 를
8 까지 올려도 단조로 나빠진다" 는 **추세**로 좁혀 읽어야 한다.

> 앞선 보고에서 "전체값 21 이 95% 구간 밖" 이라고 적었는데 **틀렸다.**
> R=30 의 2.5/97.5 분위수를 과신한 것이고, R 을 늘려 보니 중앙값은 21 그대로다.

---

## 17b. ★★ `E x F^T` 는 기여하지 않는다 — 알고리즘의 전부는 유사도다 (2026-11-23)

§17 이 "추천군 21 중 12 개가 주스" 를 가리켜 그 원인을 팠다. 그러다 **논문
§4.2.2 의 구조 자체**에 닿았다.

### 유사도 전후를 갈라 쟀다

| | 유사도 **전** `D = E × Fᵀ` | 유사도 **후** `P = D × S` |
|---|---:|---:|
| 하위 30 의 비추천군 | **1** | **26** |
| 상위 30 의 추천군 | **0** | **21** |
| 상위 30 겹침 | — | **0 / 30** |
| 하위 30 겹침 | — | **0 / 30** |

`D` 의 실제 순위:

```
하위(가장 나쁨)  버터 스틱 −1.231 · 버터오일 · 기버터 · 버터 ×3   ← 전부 유제품
상위(가장 좋음)  마마이트 +0.370 · 백설탕 +0.259 · 흑설탕 · 마가린
                 · 효모 · 100 proof 증류주 +0.200
```

**논문이 "metabolites score" 라고 부르는 `D` 는 설탕과 증류주를 최상위로, 버터를
최하위로 놓는다.** 음식 추천으로 쓸 수 없는 순위다.

> **★ 우리가 보고해 온 품질(추천군 21 · 비추천군 26)은 전부 유사도 단계가 만든
> 것이다.** `P` 와 `D` 는 상위 30 · 하위 30 이 **한 개도 겹치지 않는다.**
> `E` 와 `F` 를 곱한 결과는 버려지고, adjusted cosine 이 알고리즘의 전부다.

### 그 유사도가 작동하는 방식 — "안 닮아서 좋다"

1 위(야채주스) 점수를 `D_i × S_ij` 로 분해하면 상위 기여 8 개 중 **6 개가
음수 × 음수**다.

| 기여 | `D` | `S` | 음식 |
|---:|---:|---:|---|
| +0.172 | **+0.370** | +0.464 | yeast extract spread |
| +0.134 | +0.214 | +0.623 | yeast |
| **+0.077** | **−1.102** | **−0.070** | **버터 (무염)** |
| +0.076 | −1.102 | −0.069 | 버터 (가염) |
| +0.062 | −1.062 | −0.058 | 버터 (휘핑) |
| +0.060 | −1.231 | −0.049 | 버터 (스틱) |

**야채주스가 1 위인 이유는 "좋은 음식과 닮아서" 가 아니라 "버터와 안 닮아서"
다.** 주스는 지방이 0 이고 버터는 지방이 전부라 `S` 가 음수이고, 버터의 큰
음수 `D` 와 곱해져 **양수 기여**가 된다. 양수 기여 합 33.3 / 음수 −9.9 다.

**주스가 Top-K 를 점령하는 것도 이것으로 설명된다** — 주스는 추천군 후보의
6%(147/2,436)인데 Top 30 추천군의 **57%(12/21)** 다. 지방이 0 이라 지방 식품과
가장 크게 음의 유사도를 갖기 때문이다. (설탕 극성 때문이 아니다 — `E_ZERO`
로 설탕을 빼도 주스가 12 → 11 로만 준다.)

### 음수 유사도 가중을 재고 기각했다

식 (2) 에는 음수 유사도 처리가 없다. 0 으로 자르면(`positive`) 추천군이 0 이
되고 그대로 두면(`none`) 주스가 점령한다. 사이를 쟀다
(`SIM_THRESHOLD=neg:<w>`, `python3 ourkg/sweep.py negw`).

| `neg:w` | 비추천군 | 위반 | 추천군(참고) | Top 1 |
|---|---:|---:|---:|---|
| 0 (= `positive`) | 26 | 0 | **0** | 라이트 맥주 |
| 0.25 | 26 | 0 | 0 | Fuzzy Navel |
| 0.5 | 26 | 0 | 0 | Fuzzy Navel |
| 0.75 | 26 | 0 | 12 | 야채주스 |
| **1 (= `none`, 현행)** | **26** | **0** | **21** | 야채주스 |

**중간값이 없다.** 음수 가중을 조금만 줄여도 상위가 칵테일로 무너지고,
**비추천군은 어떤 값에서도 26 이다.** 기각한다.

### 이것이 §15 의 기각들을 다시 설명한다

| 기각 | 당시 설명 | 지금 설명 |
|---|---|---|
| 유사도 희소화 (⑦) | "`E` 의 에탄올·설탕 오류가 드러난다" | 희소화가 **`D` 의 순위를 노출**시킨다. `D` 상위가 설탕·증류주다 |
| gut-brain 가중 (§15c) | "`S` 가 꽉 차서 변조가 묻힌다" | `D` 를 바꿔도 `P` 에 거의 안 간다 — `D` 가 쓰이지 않는다 |
| `E_MODE=nhanes` (§15d) | "`F` 가 g/100 g 이라" | `E` 를 바꾸면 `D` 가 바뀌는데 **`D` 는 기여하지 않는다** |

**`E` 를 고치는 모든 시도가 안 먹힌 이유가 이것이다.** `E` 는 `D` 를 통해서만
작용하는데 `D` 의 순위가 `P` 에 전달되지 않는다.

---

## 17c. 유사도를 아예 빼 봤다 — `D` 단독은 쓸 수 없다 (2026-11-23)

§17b 가 "`P` 와 `D` 는 상위·하위 30 이 한 개도 안 겹친다" 를 보였다. 그 주장을
완성하려면 **`D` 단독이 어떤지**도 보여야 한다. `NO_SIM=1` 로 Algorithm 1 의
line 8 을 지우고 쟀다 (`python3 ourkg/sweep.py nosim`).

| 설정 | 비추천군 | 위반 | 추천군(참고) | MMD 처방군 | extras | AUC(참고) | Top 1 |
|---|---:|---:|---:|---:|---:|---:|---|
| **`P=D×S`/`shrunk` (현행)** | **26** | **0** | 21 | **24** | **1** | 0.462 | 야채주스 |
| `P=D×S`/`nhanes_all` | 2 | 3 | 19 | 21 | 5 | 0.673 | 고단백 분말 |
| **`P=D`/`shrunk`** | **1** | **6** | **0** | **3** | **21** | 0.527 | 마마이트 |
| **`P=D`/`nhanes_all`** | **0** | 1 | 11 | 16 | 0 | **0.701** | 마마이트 |

### 셋이 나온다

**① `D = E × Fᵀ` 는 단독으로 쓸 수 없다.** 비추천군 26 → **1**, 위반 0 → **6**,
MMD extras 1 → **21**. 상위가 마마이트이고 Top 30 에 extras 가 21 개다.
§17b 의 주장이 **양방향으로** 증명됐다 — `D` 는 `P` 에 전달되지도 않고, 단독
으로도 못 쓴다.

**② 그러면 알고리즘의 가치는 전부 adjusted cosine 에 있다.** 논문은 `E`·`F`
구축(§3·§4.2.1)에 지면의 대부분을 쓰는데, 결과를 만드는 것은 식 (1) 한 줄이다.

**③ AUC 가 또 역행한다.** `P=D` 가 AUC 0.527~0.701 로 현행(0.462)보다 **높다.**
비추천군이 1 인 설정이 AUC 는 더 좋다 — §13 의 역행이 가장 극단적으로 나온
사례다.

### 다음 — `S` 에 `E` 를 넣는다

②가 가리키는 길은 하나다. 지금 `S` 는 **성분 구성**(`F`)만 보고 `E` 를 전혀
쓰지 않는다. 그래서 "지방이 0 vs 지방이 전부" 가 유사도를 지배하고(§17b),
`E` 를 고치는 모든 시도가 `D` 에 갇혀 전달되지 않는다. `S` 를 **우울증
프로파일**(`e ⊙ F`)로 계산하면 `E` 가 비로소 유사도에 들어간다.

---

## 17d. ★ 유사도에 `E` 를 넣었다 — 상위가 고쳐지고 바닥이 나빠진다 (2026-11-23)

### 왜

§17c 가 가리킨 길은 하나였다. `S` 는 **성분 구성**(`F`)만 보고 `E` 를 **전혀
쓰지 않는다.** 그래서 "지방이 0 vs 지방이 전부" 가 유사도를 지배하고(§17b),
`E` 를 고치는 모든 시도가 `D` 에 갇혀 전달되지 않는다.

`SIM_SPACE=effect` 는 유사도를 **우울증 프로파일**(`e ⊙ F`)로 잰다 — "건강
효과가 비슷한 음식끼리" 가 된다. 한 줄 변경이고 `E` 가 비로소 유사도에 들어간다.

### 결과 — 혼합이다

`python3 ourkg/sweep.py simspace`

| 설정 | 비추천군(논문) | extras(외부) | 위반 | 추천군 | MMD 처방군 | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| **`composition`/`shrunk` (현행)** | **26** | **8** | **0** | 21 | 24 | 야채주스 |
| `composition`/`nhanes_all` | 2 | 2 | 3 | 19 | 21 | 고단백 분말 |
| `effect`/`shrunk` | 10 | 7 | 0 | **0** | **0** | 흰고래 지느러미 |
| **`effect`/`nhanes_all`** | 18 | 3 | 1 | **27** | **27** | **아티초크 (생)** |

**상위는 `effect`+NHANES 가 이긴다.** MMD 처방군 **27 vs 24**(역대 최고),
추천군 27 vs 21, 그리고 **Top 30 에 주스가 하나도 없다.**

```
Top     블랙베리 · 오크라 · 사과(생) · 라즈베리 · 아티초크   ← 통과일·통채소
Bottom  햄버거롤 · 팜유 · 송아지 · 롤로 캐러멜 · 버터오일 · 기버터 · 태피
```

| | 현행 Top 30 | `effect`/`nhanes_all` Top 30 |
|---|---|---|
| 군 분포 | 채소 10 · 과일 10(**주스 포함**) · 음료 3 · 소스 2 | **과일 15 · 채소 12** · 음료 1 |

**바닥은 현행이 이긴다.** 논문 기준 26 vs 18 이고 **외부 기준(ModiMedDiet
extras)도 8 vs 3** 이다.

> **정정.** 처음에 "비추천군 18 은 `NOT_OK` 에 유지류가 없어서 생긴 지표 결함"
> 이라고 적었다. **틀렸다.** 두 지표가 유지류·양고기를 안 세는 것은 맞지만,
> 그것과 무관한 **외부 기준으로도 현행이 낫다**(8 vs 3). 지표를 손봐서 유리하게
> 만들지 않으려고 `NOT_OK` 는 논문 §4.2.3 목록 그대로 두고 외부 기준을 표에
> **나란히** 띄웠다 — 어느 쪽을 셀지 우리가 정하지 않기 위해서다.

### 얻은 것 — 진단이 확인됐다

**`E` 개선이 처음으로 전달됐다.** NHANES `E` 는 `composition` 공간에서 비추천군
2 로 참패했는데(§15d) `effect` 공간에서는 상위가 역대 최고다. §17b·§17c 의
진단("`E` 가 `S` 에 안 들어가서 개선이 전달되지 않는다")이 맞았다는 확인이다.

**두 개선이 곱해져야 작동한다.** `shrunk`+`effect` 는 추천군 **0** 이다 —
좋은 `E` 가 없으면 `effect` 공간은 오히려 더 나쁘다. 거꾸로 `nhanes_all` 도
`composition` 에서는 쓸 수 없다. **`E` 의 질과 유사도 공간은 짝이다.**

**기본값은 바꾸지 않는다** — 상위를 얻고 바닥을 잃는 교환이고, 바닥 쪽 손실이
두 기준 모두에서 확인된다. `SIM_SPACE=effect E_MODE=nhanes_all` 로 돌릴 수 있다.

---

## 17e. ★★ 왜곡의 크기를 쟀다 — 현행 1 위는 123% 가 "안 닮아서" 다 (2026-11-23)

### 나쁜 음식의 기여를 0 이하로 묶어 본다

§17b 가 "야채주스 1 위는 버터와 안 닮아서" 를 보였다. 그것을 직접 치는 설계다
(`SIM_SIGN=clip`).

```
D_i >= 0 :  그대로        D_i * S_ij
D_i <  0 :  min(D_i * S_ij, 0) = D_i * max(S_ij, 0)
```

**나쁜 음식은 점수를 낮추기만 한다** — 닮으면 벌점, 안 닮으면 0.
이미 기각한 `SIM_THRESHOLD=positive` 와 다르다: 그쪽은 **모든** 음수 유사도를
버려 좋은 음식의 정보까지 잃는다. 이것은 `D<0` 인 쪽만 묶는다.
(`S` 가 12,420² 라 `relu(S)` 를 통째로 만들면 1.2 GB 가 더 든다 — `D<0` 인
행만 1,000 개씩 끊어 처리한다.)

### 결과 — 현행에는 치명적이고, `effect`+NHANES 에는 **아무 효과가 없다**

`python3 ourkg/sweep.py simsign`

| 설정 | 비추천군 | extras | 위반 | 추천군 | MMD 처방군 | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| `none`/`composition`/`shrunk` | 26 | 8 | 0 | **21** | 24 | 야채주스 |
| **`clip`**/`composition`/`shrunk` | 26 | 8 | 0 | **0** | 1 | **라이트 맥주** |
| `none`/`effect`/`nhanes_all` | 18 | 3 | 1 | **27** | **27** | 아티초크 |
| **`clip`**/`effect`/`nhanes_all` | 18 | 3 | 1 | **27** | **27** | 아티초크 |

마지막 두 줄이 **완전히 동일하다.** 환경변수가 안 읽힌 것이 아니다 —
`composition` 쪽은 21 → 0 으로 바뀐다.

### 왜 그런가 — 왜곡의 크기를 쟀다

1 위 음식의 점수 중 **음수 × 음수**가 차지하는 비중:

| `E` | 유사도 공간 | 1 위 점수 | 음수×음수 |
|---|---|---:|---:|
| `shrunk` | `composition` (**현행**) | 23.4 | **28.8 (123%)** |
| `shrunk` | `effect` | 10.8 | **11.7 (108%)** |
| `nhanes_all` | `composition` | 302.7 | 11.9 (4%) |
| **`nhanes_all`** | **`effect`** | 333.3 | **0.0 (0%)** |

> **★ 현행 1 위 점수는 음수×음수가 123% 다.** 양수 기여를 다 합친 것보다 크고,
> 나머지가 음수라 상쇄해 23.4 가 된다. **야채주스 1 위는 전적으로 "버터와 안
> 닮아서" 다.**
>
> **`effect`+`nhanes_all` 은 0% 다.** 그래서 `clip` 을 걸어도 한 글자도 안
> 바뀐다 — **고칠 왜곡이 애초에 없다.**

### 기각하되, 진단으로서 가치가 있다

`clip` 자체는 기본값을 개선하지 못한다. 현행에 걸면 추천군이 21 → 0 이 되고
상위가 라이트 맥주가 된다 — **현행의 상위 품질이 그 왜곡 위에 서 있어서**,
왜곡을 제거하면 받칠 것이 없다.

그러나 `clip` 이 진단을 완성했다. **같은 "추천군 21 vs 27" 이라도 생성 방식이
질적으로 다르다** — 하나는 123% 를 왜곡에서 가져오고 하나는 0% 다.
이것이 §17d 의 "기본값을 바꾸지 않는다" 를 다시 보게 만든다.

---

## 17f. 기본값을 바꿀지 재검토했다 — 유지한다 (2026-11-23)

§17e 가 "현행 1 위는 123% 가 왜곡, `effect`+NHANES 는 0%" 를 보였다. 기본값
변경을 재검토할 근거다. **기준을 결과보다 먼저 적어 두고** 부트스트랩으로 쟀다
(`python3 ourkg/bootstrap.py 현행 effect+nhanes`, R=120).

| | 현행 `composition`/`shrunk` | `effect`+NHANES |
|---|---|---|
| 추천군 | 21 [4, 22] · sd **5.2** | 27 [**0**, 28] · sd **8.9** |
| 비추천군 | 26 [21, 29] · sd **2.1** | 18 [**6**, 21] · sd **4.9** |
| 위반 | 0 [0, 1] · sd **0.5** | 1 [0, **6**] · sd **1.6** |

**세 지표 모두 분산이 2~2.4 배다.** 추천군은 0 까지, 비추천군은 6 까지 떨어진다.

| 미리 세운 기준 | 판정 |
|---|---|
| 왜곡 0% vs 123% | **`effect` 승** — 유일하게 분명한 우위 |
| 상위 품질 (MMD 27 vs 24) | **무효** — 추천군 sd 8.9, 구간 [0, 28]. 차이 3 은 잡음 |
| 바닥 품질 (26 vs 18) | 현행 승 — 다만 이쪽도 sd 4.9 라 약화 |
| `E` 근거 등급 | 현행 승 — NHANES 는 관찰 연구(역인과·교란) |
| **안정성** | **현행 승** — 세 지표 모두 |

§17 에서 세운 원칙("차이가 잡음 구간이면 그것만으로 결정하지 않는다")을 **이
결론에도 적용하면** 상위 품질 우위는 주장할 수 없다. 남는 것은 왜곡 0% 하나
인데, 그것만으로 더 불안정한 설정을 기본값으로 삼을 수는 없다.

> **★ 그래도 결론의 성격은 바뀐다.** "현행이 좋다" 가 아니라 **"현행은 맞는
> 이유로 맞는 것이 아닌데, 더 나은 대안을 아직 못 만들었다"** 이다.
> 상위 점수의 123% 가 음수×음수에서 오고 추천군 21 중 12 개가 주스다.

`SIM_SPACE=effect E_MODE=nhanes_all` 로 돌릴 수 있다.

---

## 18. ★★ 합병증 추론에 증거가 없다 (2026-11-24)

논문 §3.3 의 추론이다.

> "when observing that depression and anxiety are both mood disorders with
> shared associations with the same gut microbiota, we can infer an implicit
> relationship between depression and anxiety as 'complications'"

우리도 그대로 구현했고(`analyze.py` 추론 (a)), 방법 2 의 15 건 중 10 건이
이 합병증 추론이다. **그 10 건이 전부 `result=1` 이다.** 의심스러워 쟀다.

### ① 선택성이 0 이다 — 55/55 쌍이 통과한다

```
질환 11 종 → 가능한 쌍 55
공유 미생물이 1 개 이상인 쌍 → 55 (100%)
```

**"같은 미생물을 공유하면 합병증" 이라는 규칙이 아무것도 걸러내지 않는다.**
11 개 질환의 **모든 조합**을 합병증이라고 말한다.

### ② 원인 — 신경전달물질 **6 개**가 병목이다

```
미생물 48  →  신경전달물질 6  →  정신질환 11
```

MiKG 경로로 이어 붙인 미생물-질환 573 쌍이 **6 개 노드를 거쳐** 만들어진다.
같은 신경전달물질에 걸린 질환들은 그 물질의 미생물을 **통째로** 받는다.

| 질환 | 미생물 수 | | 질환 | 미생물 수 |
|---|---:|---|---|---:|
| 자폐 · 우울 · 양극성 | **48 (전부)** | | 인격 | 43 |
| 수면 | 47 | | 학습 | 32 |
| 불안 | 43 | | 인지 · 섭식 | 29 |

세 질환이 **48 종 전부**와 연결돼 있다.

### ③ 논문의 대표 예가 **p = 1.0** 이다

초기하 검정(`out/complication_hypergeom.csv`)으로 "공유가 우연보다 많은가" 를
물었다.

| 쌍 | 공유 | A | B | 기대 | p | q |
|---|---:|---:|---:|---:|---:|---:|
| **Anxiety × Depressive** | 43 | 43 | 48 | **43.0** | **1.0** | **1.0** |

**관측 43, 기대 43.0.** 우울증이 48 종 전부와 연결돼 있으니 불안의 43 종을
공유하는 것은 수학적으로 당연하다. **논문이 드는 바로 그 예에 아무 정보가 없다.**

### ④ 유의한 12 쌍도 못 쓴다 — 중첩 구조를 잡은 것이다

| a | b | 공유 | A | B | 기대 | q |
|---|---|---:|---:|---:|---:|---:|
| Cognition | Eating | **29** | 29 | 29 | 17.5 | 5e-12 |
| Cognition | Sex behavior | **29** | 29 | 30 | 18.1 | 5e-11 |
| Eating | Sex behavior | **29** | 29 | 30 | 18.1 | 5e-11 |

55 쌍 중 q<0.05 가 12 개인데 **상위가 전부 완전 포함**(공유 = min(A,B))이다.
두 질환이 **같은 신경전달물질 집합**을 거쳐 만들어졌다는 뜻이지 생물학적
발견이 아니다. 초기하가 잡아낸 것은 **데이터의 중첩 구조**다.

### ⑤ 방법 2 의 검증은 미생물을 보지 않는다

```python
'evidence': _species(random.choice(shared)),   # 미생물을 근거로 적지만
'terms': [a, b]                                # PubMed 질의는 질환 두 개뿐
```

**근거로 적은 미생물이 질의에 안 들어간다.** 검증하는 것은 "Anxiety disorders
와 Sleep disorders 가 문헌에 함께 나오는가" 이고, 이것은 미생물과 무관하게
참이다 — 잘 알려진 동반이환이다. 그래서 10 건이 전부 1 이다.

논문 Table 5 도 같은 방식이다. **"미생물 공유 → 합병증" 을 검증한 적이
양쪽 모두 없다.**

### 결론

**이것은 우리 구현의 결함이 아니라 논문 §3.3 추론의 구조적 결함이다.**
논문 자신도 "such inferences require careful validation and scrutiny" 라고
적었는데, 그 validation 이 추론을 검증하지 않는다.

3 항 질의(질환 A × 질환 B × 미생물)로 고치는 길은 §5.1 에서 이미 **0/7** 로
실패했다 — 문헌에 세 항이 함께 명시되는 일이 드물다. **합병증 추론은 지금
데이터로 검증할 수 없다고 적는 것이 정확하다.**

---

## 19. 중복 변종을 묶어 봤다 — 흔들림의 일부 원인이지 주원인이 아니다 (2026-11-24)

§17 이 "추천군 폭 16" 을, §17b 가 "추천군 21 중 12 개가 주스이고 오렌지주스만
4 종" 을 보였다. **거의 같은 음식의 변종이 Top-K 칸을 나눠 점유**하는 것이
흔들림의 원인이라는 가설이다. 묶어 봤다 (`DEDUP`).

| 기준 | 묶는 법 | 음식 |
|---|---|---:|
| `composition` | **성분 구성이 같은 것**(소수 3 자리) | 12,420 → **11,158** |
| `name2` | 이름 앞 두 구간이 같은 것 | 12,513 → **5,957** |

대표는 **그 군에서 측정 compound 가 가장 많은 것**을 쓴다. 평균을 내면 존재하지
않는 음식을 만들게 되고, 첫 번째를 쓰면 정렬 순서에 의존한다.

`composition` 이 묶는 것은 탄산음료 45 종·증류주 10 종처럼 **측정 성분이 거의
없어 알고리즘이 구별하지 못하는** 음식들이다. `name2` 는 `orange juice, 100%`
7 종을 하나로 만들지만 `pork, fresh` 194 개도 묶어 절반이 준다.

### 점수와 안정성

`python3 ourkg/sweep.py dedup` · `BOOT_R=100 python3 ourkg/bootstrap.py 현행 dedup-comp dedup-name2`

| 설정 | 음식 | 추천군 | **sd** | 비추천군 | sd | extras(외부) |
|---|---:|---|---:|---|---:|---:|
| **현행** | 12,420 | 21 [4, 22] | **5.27** | 26 [21, 29] | 1.96 | **8** |
| `composition` | 11,158 | 20 [8, 23] | **3.88** | 24 [22, 29] | 1.92 | 6 |
| `name2` | 5,957 | **1 [0, 8]** | 2.14 | 25 [18, 27] | 2.16 | **23** |

**`composition` 은 부분 성공이다.** 추천군 sd 가 **5.27 → 3.88 (−26%)** 로
내려가고 점수는 거의 유지된다. 가설이 **부분적으로** 확인된다.

**`name2` 는 기각이다.** sd 2.14 로 가장 안정적이지만 **추천군이 1** 이다.
"안정적으로 나쁜" 상태이고, 안정성은 값이 바닥에 붙어서 생긴 것이다.
(외부 바닥 지표 extras 가 8 → 23 으로 크게 오르는 것은 눈에 띈다 — 소시지·제과
변종이 하나로 줄면서 **다양한** extras 가 바닥에 들어오기 때문이다.)

### 기본값으로 켜지 않는다

`composition` 도 기본값으로 삼지 않는다. 이유 둘.

1. **이득이 작다.** sd 5.27 → 3.88 은 개선이지만 구간이 [4,22] → [8,23] 으로
   여전히 넓다. 추천군은 **여전히 못 믿을 지표**이고 §17 의 결론(비추천군·위반이
   주지표)이 바뀌지 않는다.
2. **주지표가 내려간다.** 비추천군 26 → 24, extras 8 → 6. 주지표를 희생해
   참고 지표의 분산을 줄이는 교환이다.

다만 **선택지로 남길 가치는 있다** — 알고리즘이 구별하지 못하는 음식 1,262 개를
걷어내는 것은 데이터 위생상 맞는 일이다. `DEDUP=composition` 으로 돌린다.

### 결론

> §17 의 불안정성은 중복 변종이 **일부** 원인이다 — 성분이 같은 것을 묶으면
> sd 가 26% 준다. 그러나 **주원인이 아니다.** 묶어도 추천군은 [8, 23] 으로
> 흔들리고, 그 흔들림의 본체는 §17b 가 밝힌 **"음수×음수" 메커니즘**이다.
> 버터와의 음의 유사도가 점수를 만드는 구조에서는 어떤 음식이 Top-30 에
> 들어오는지가 코호트 구성에 민감할 수밖에 없다.

---

## 20. ★ 데이터를 3 배로 늘렸더니 E 가 나빠졌다 — NHANES 다주기 (2026-11-24)

§17d 에서 `effect`+NHANES 가 **상위는 역대 최고(MMD 27 · Top 1 아티초크)인데
바닥이 약하다**(비추천군 18)고 기각했다. 원인으로 "NHANES 는 47 compound 중
24 만 유의해 **`E` 의 음수 쪽이 얇다**" 를 지목했다. 주기를 늘려 고쳐 보려 했다.

주기는 **고정효과로 보정한다** — 조사 연도마다 식이 보고 방식과 PHQ-9 분포가
달라 합치기만 하면 주기 간 차이가 영양소 계수에 실린다.

### 통계는 강해졌다

| | 단주기 (2017) | 3 주기 (2017·2015·2013) |
|---|---:|---:|
| 표본 | 4,774 | **14,792** |
| 유의 compound (q<0.05) | 24 | **38** (이로움 29 · 해로움 9) |

**에탄올이 처음으로 유의해졌다**(`C00469` q=0.039, 단주기 0.43). §15b·§17e 가
지적한 "ProMENDA 가 에탄올을 +0.200 으로 잘못 표시한다" 를 통계적으로 확정된
음수로 대체할 수 있게 됐다. 해로움 9 종은 포화지방 7 + 카페인 + 에탄올이다.

### 그런데 추천은 무너졌다

`python3 ourkg/sweep.py simspace`

| 설정 | 비추천군 | extras | 위반 | 추천군 | MMD 처방군 | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| `composition`/`shrunk` (현행) | **26** | 8 | **0** | 21 | **24** | 야채주스 |
| `composition`/`nhanes_all` | 17 | 16 | **8** | 3 | 11 | BLT 샌드위치 |
| **`effect`/`nhanes_all`** | **10** | 10 | **10** | **1** | 11 | **소고기 타코** |

단주기에서 같은 설정이 **추천군 27 · MMD 27 · Top 1 아티초크**였다.

### 원인 — `E` 가 육류 쪽으로 기울었다

| compound | 단주기 | 3 주기 | 어디 많은가 |
|---|---:|---:|---|
| **인(P)** | +0.613 | **+1.000 (최대)** | 육류·유제품·가공식품 |
| **아연** | 0 | **+0.464** | 붉은 고기 |
| **티아민** | 0 | **+0.448** | 돼지고기 |
| **나이아신** | 0 | **+0.433** | 육류·생선 |
| 포화지방 16:0 | **−0.613** | **0** (유의성 상실) | — |
| 포화지방 18:0 | −0.838 | **−0.385** (약화) | — |

**육류 연관 영양소가 최상위로 올라오고 포화지방의 음수는 약해진다.** 그래서
Top 1 이 소고기 타코·BLT 샌드위치가 된다.

### ★ 이것이 §9 의 결론을 다시 확인한다

**통계적으로는 강해졌는데 추천으로는 나빠졌다.** 늘어난 유의 compound 의
상당수가 **"고기를 많이 먹는 사람" 을 가리키는 대리변수**다. 총열량을 보정해도
"육류 중심 식단 vs 식물 중심 식단" 의 차이는 남고 그것이 영양소 계수에 실린다.

> **그리고 내 앞선 읽기가 확증 편향이었다.** 단주기에서 엽산·루테인·칼륨이
> 상위였던 것을 "문헌과 맞는다" 고 적었는데(§15d), **표본이 작아 우연히
> 식물성 쪽이 잡힌 것**이었다. 표본을 늘리니 그 패턴이 사라진다.

**기본값을 단주기(`NHANES_CYCLE=2017`)로 되돌린다.** 3 주기는 선택지로 남기되
**"더 많은 데이터가 더 나쁜 `E` 를 만든 사례"** 로 기록한다.

영양역학 연관을 `E` 로 쓰는 길은 **표본 크기의 문제가 아니다** — 설계의 문제다.
섭취-결과를 인과로 재려면 RCT 나 최소한 종단 코호트가 필요하고, 그것은
compound 수준이 아니라 **식단 수준**으로만 존재한다(ModiMedDiet 이 그것이다).

---

## 21. 지도학습 점수를 직접 써 봤다 — 분류는 풀리고 추천은 안 된다 (2026-11-24)

§20 이 "`E` 를 compound 수준에서 고치는 길은 설계상 막혔다" 로 끝났다. 남은
길은 `E` 를 거치지 않고 **음식 점수를 직접 학습**하는 것이다.

그런데 `invert`(§8)가 이미 그것을 한다 — ModiMedDiet 라벨로 로지스틱 회귀를
학습해 **계수를 `E` 로** 내놓는다. `D = E_learned × Fᵀ` 는 그 모델의 **결정함수
자체**다. 따라서 `E_MODE=learned` + `NO_SIM=1` 이 곧 "지도학습 점수 직접 사용"
이다. 새 코드가 필요 없다.

`python3 ourkg/sweep.py learned`

| 설정 | 비추천군 | extras | 위반 | 추천군 | MMD 처방군 | AUC | Top 1 |
|---|---:|---:|---:|---:|---:|---:|---|
| **현행 `shrunk` × S** | **26** | 8 | **0** | 21 | 24 | 0.462 | 야채주스 |
| `learned` × S | 18 | **20** | 13 | 9 | **30** | 0.687 | 대구(생) |
| **`learned` 단독** | **3** | 3 | 0 | 18 | 24 | **0.800** | **파프리카** |
| `shrunk` 단독 | 1 | 3 | 6 | 0 | 3 | 0.527 | 마마이트 |

> **AUC 를 읽을 때 주의.** `sweep` 이 내는 AUC 는 **순환이다** — `learned` 가
> ModiMedDiet 라벨로 학습됐는데 같은 라벨로 재기 때문이다. 위 0.800 은
> `invert` 자신의 **held-out** 수치다(50/50 음식 분할, train 만 보고 학습).
> 상한 0.813 · ProMENDA 0.520.

### 분류는 사실상 풀렸다

held-out AUC **0.800** 은 상한 0.813 에 거의 닿는다. **"처방군 vs extras 를
가르라" 는 문제로는 끝났다.**

### 그런데 추천은 안 된다

`learned` 단독의 **비추천군이 3** 이고 **Top 1 이 파프리카**다. §12 에서
`all+auto` 를 기각한 바로 그 실패 — **1 회 섭취량 1 g 미만의 말린 향신료**가
올라온다.

이유는 분명하다. 분류기는 두 군을 가르도록 학습했고, 그 경계를 가장 잘 긋는
특징이 **향신료의 극단적 성분 농도**다. **AUC 를 최대화하는 것과 Top-30 추천을
잘하는 것은 다른 문제다** — §13 에서 처음 본 역행이 가장 극단적으로 나타났다.

### `learned` × S 가 논문 서술에 가장 가깝다

유사도를 통과시키면 **extras 20**(현행 8 의 2.5 배) · **MMD 처방군 30**(최고)
이고 Top 1 이 **대구(생)** 다. 논문 §4.2.3 의 "fish and shellfish products" 에
가장 가까운 결과다. 다만 **위반 13** 으로 상위에 제과·육류가 섞인다.

**여기서도 유사도 단계가 분류기의 날것 순위를 쓸 만하게 바꾼다** — §17b·§17c
에서 본 것과 같은 구조다. `D` 가 무엇이든(ProMENDA든 학습한 것이든) 단독으로는
못 쓰고, `S` 를 통과해야 음식 추천이 된다.

---

## 21b. 위반 13 의 정체 — 두 기준의 충돌이었다 (2026-11-24)

§21 의 `learned` × S 는 바닥이 논문 서술에 가장 가까운데(extras 20 · MMD 30)
**위반 13** 이 걸렸다. 무엇인지 봤다.

**13 건 전부 `Beef, round, ... separable lean only, trimmed to 0" fat` 이고,
ModiMedDiet 라벨이 전부 `lean red meat 3-4/week`(처방군)다.** Top 30 전체가
30/30 처방군이다.

> **위반이 아니라 기준 충돌이다.** 논문 §4.2.3 은 `Beef Products` 를 비추천
> 으로 보는데 SMILES/ModiMedDiet 은 **살코기 적색육을 주 3-4 회 처방**한다.
> 학습 모델이 ModiMedDiet 로 배웠으니 "살코기 소고기는 좋다" 를 정확히 학습한
> 것이고, 논문의 군 라벨이 그것을 위반으로 센다. **모델이 틀린 것이 아니다.**

그리고 13 건이 **네 군의 변종**이었다 — `eye of round roast` 4 ·
`top round roast` 3 · `top round steak` 3 · `eye of round steak` 3.
§19 의 중복 변종 문제가 Top-30 의 **13 칸**을 먹고 있었다.

### 중복만 묶었다

`python3 ourkg/sweep.py learned_dedup`

| 설정 | 비추천군 | extras | 위반 | 추천군 | MMD 처방군 | Top 1 |
|---|---:|---:|---:|---:|---:|---|
| **현행 `shrunk`/none** | **26** | 8 | **0** | 21 | 24 | 야채주스 |
| `learned`/none | 18 | 20 | **13** | 9 | 30 | 대구(생) |
| `learned`/`composition` | 19 | 20 | 12 | 9 | 30 | 대구(생) |
| **`learned`/`name2`** | 17 | **24** | **2** | **22** | 26 | 모링가 잎(삶음) |

**위반 13 → 2.** 예측대로 같은 부위 변종이 묶이며 사라졌고 추천군도 9 → 22 다.

`learned`/`name2` 의 바닥은 **질적으로 논문 서술에 가장 가깝다** — 페이스트리 ·
소시지 그레이비 · 살라미 샌드위치 · 비스킷 · 베리파이 · 맥앤치즈+프랑크푸르터.
논문 §4.2.3 의 "sausage products, baked products, and sweets" 그대로다.
**현행 바닥은 평범한 소고기 부위 16 개다.**

### 안정성

`BOOT_R=80 python3 ourkg/bootstrap.py 현행 learned-name2`

| | 현행 | `learned`/`name2` |
|---|---|---|
| 추천군 | 21 [5, 21] · sd **5.14** | 22 [**15, 30**] · sd **4.18** |
| 비추천군 | 26 [22, 29] · sd **1.91** | 17 [**9**, 19] · sd 2.92 |
| 위반 | 0 [0, 1] · sd **0.48** | 2 [0, **5**] · sd 1.37 |

**추천군은 새 설정이 낫다** — 구간이 [5,21] → **[15,30]** 으로 올라가고 sd 도
준다. §17 이후 **추천군이 처음으로 쓸 만해진 설정**이다. 비추천군·위반은
현행이 낫다.

### 기본값은 유지한다

**순환 아닌 지표가 현행을 가리킨다.** `learned` 는 ModiMedDiet 로 학습했으니
extras·MMD 처방군은 쓸 수 없고, 남는 것은 논문 군 라벨인데 **비추천군 26 vs 17 ·
위반 0 vs 2** 로 현행이다.

그리고 **종류가 다르다** — `learned` 는 외부 임상 라벨로 지도학습한 시스템이라
기본값으로 삼으면 "Food4healthKG 재구축" 이 아니라 "ModiMedDiet 분류기" 가 된다.

> **다만 §17 의 결론을 부분적으로 뒤집는다.** "추천군은 못 믿을 지표" 라고
> 적었는데, 중복 변종을 묶고 학습 `E` 를 쓰면 구간이 [15,30] 으로 올라온다.
> 흔들림의 원인이 **지표 자체가 아니라 데이터·`E` 양쪽**에 있었다.

---

## 22. 두 E 소스를 합쳐 봤다 — 커버리지는 늘고 안정성을 잃는다 (2026-11-24)

`F` 열 134 중 `E` 가 비영인 것이 **66** 이다. 나머지는 점수에 전혀 기여하지
않는다. 두 소스를 **교체만 해 보고 합쳐 본 적이 없었다.**

| | compound |
|---|---:|
| ProMENDA 비영 | 66 |
| NHANES 유의(q<0.05) | 24 (겹침 11) |
| NHANES 전체 | 47 (겹침 29) |
| **`union`** (ProMENDA + NHANES 유의로 빈 칸) | **79** |
| **`union_all`** (ProMENDA + NHANES 전체로 빈 칸) | **84** |

겹치는 곳은 **ProMENDA 우선**이다 — 논문 경로를 기본으로 두고 빈 칸만 메우는
쪽이 바꾸는 폭이 가장 작다. NHANES 만 있는 18 개는 철·구리·콜린·칼륨·
마그네슘·셀레늄·비타민K·카로틴·루테인·인 — **ProMENDA(혈중 대사체)에 없던
미네랄과 카로티노이드 축**이다.

### 점수는 올랐다

| 설정 | 비추천군 | extras | 위반 | 추천군 | MMD 처방군 | AUC | ρ | Top 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **현행 `shrunk`** | 26 | **8** | **0** | 21 | 24 | 0.462 | 0.316 | 야채주스 |
| `union` | 26 | 0 | 1 | 21 | 26 | 0.518 | **0.364** | 그린빈(조리) |
| **`union_all`** | 28 | 0 | 1 | **23** | **27** | 0.516 | 0.360 | 야채수프(저염) |

MMD 처방군 24 → 27, AUC 0.462 → 0.516, ρ 0.316 → 0.360. Top 1 이 주스가 아닌
**통채소**다.

> **비추천군 28 은 우위로 세지 않는다.** 바닥 30 이 **전부
> `Beef, ... separable lean only`** 이고 ModiMedDiet 라벨이 **27/30 이
> 처방군**이다. §21b 와 **같은 충돌이 방향만 반대로** 나타난 것이다 — 거기서는
> 살코기 소고기가 상위에 와서 "위반 13" 이었고 여기서는 바닥에 와서
> "비추천군 28" 이다. 논문 군 라벨이 보상하고 임상 기준이 처벌한다.
> `extras 8 → 0` 이 그 다른 얼굴이다.

### 그런데 안정성이 무너진다

`BOOT_R=100 python3 ourkg/bootstrap.py 현행 union union_all`

| | 현행 | `union` | `union_all` |
|---|---|---|---|
| 추천군 | 21 [4,22] sd **5.27** | 21 [0,23] sd 5.66 | 23 [1,24] sd 5.88 |
| **비추천군** | 26 [21,29] sd **1.96** | 26 [**5**,30] sd **7.13** | 28 [**5**,30] sd **6.91** |
| **위반** | 0 [0,1] sd **0.48** | 1 [0,5] sd 1.40 | 1 [0,**8**] sd **2.08** |

**비추천군 sd 가 3.6 배**이고 하한이 21 → **5** 다. 위반도 sd 0.48 → 2.08 이다.

### 기각 — 그리고 진단

미리 세운 기준 셋 중 **안정성이 실패**했고, 상위 우위(MMD 차이 3)는 추천군
sd 5.9 앞에서 주장할 수 없다.

**원인은 두 소스의 이질성이다.** ProMENDA 는 "환자에서 이 대사물의 **농도**가
높/낮다", NHANES 는 "이것을 **먹으면** PHQ-9 가 높/낮다" 를 잰다. **의미가 다른
값을 한 벡터에 넣은** 것이고, 그 이질성이 분산으로 나타났다. `union`(유의한
것만 13 개 추가)도 sd 7.13 으로 같이 나쁜 것이 그 근거다 — 유의성 문제가
아니다.

> **다음 수는 "섞지 않는 것" 이다** — 각 `E` 로 따로 점수를 내고 **순위 수준**
> 에서 합치면 스케일·의미 차이가 사라진다(§23 예정).

### 그 밖 — 조건 분기 버그

처음 돌렸을 때 여섯 줄이 **전부 `shrunk` 와 동일**했다. union 코드를
`E_MODE.startswith('nhanes')` 분기 **안쪽**에 넣어 `union` 이 거기 못 들어가고
기본값으로 떨어진 것이다. **"효과 없음" 으로 잘못 결론 낼 뻔했다** — 여섯 줄이
한 글자도 다르지 않은 것이 단서였다.

---

## 23. ★★ 합의 Top-K — 불안정을 없애는 대신 쓴다 (2026-11-24)

§17 이 Top-K 지표의 표집 변동을 보인 뒤 세 번 **없애려** 했고 전부 실패했다
(중복 병합 §19 · `E` 교체 §15d·§20 · `E` 합치기 §22). 여기서는 **이용한다.**

```
선택도(food) = 부분표집 R 회 중 Top-K 에 든 비율
합의 Top-K  = 선택도 상위 K 개
```

**논문 Algorithm 1 을 바꾸지 않는다** — 같은 점수를 여러 번 재서 고르는 층을
위에 얹을 뿐이라 어떤 `E`·유사도 설정과도 같이 쓴다 (`ourkg/consensus.py`).

### 작동한다 — 겹침 29/30 vs 2~18/30

| | Top 30 겹침 |
|---|---|
| **합의** — 독립 블록 둘(각 50 회) | **29 / 30** |
| 단일 실행 — 부분표집 쌍들 | **7 · 18 · 2 / 30** |

단일 실행은 음식 20% 가 바뀌면 Top-30 이 2~18 개만 겹친다. 합의는 29/30 이다.

> **"이 음식은 코호트가 바뀌어도 상위에 남는다" 는 단일 실행으로는 할 수 없던
> 주장이다.** 지금까지 보고한 Top-30 은 전부 "이 코호트에서는 이렇다" 였다.

### 설정 비교 (R=60)

| 설정 | 추천군 | 비추천군 | 위반 | **선택도 중앙** | 1 위 |
|---|---:|---:|---:|---:|---|
| **현행** | 19 | **28** | **0** | 0.82 | **캐러멜 딥(라이트)** |
| `learned-name2` | **25** | 13 | 1 | 0.67 | 케일(삶음) |
| **`union_all`** | 21 | **28** | 1 | **0.84** | 현미+완두 |
| `effect+nhanes` | 23 | **7** | 0 | **0.61** | 아티초크(생) |
| `dedup-comp` | 18 | 27 | 1 | 0.80 | 크랜베리주스 |

**① 합의는 분산만 줄이고 편향은 고치지 않는다.** `effect+nhanes` 는 비추천군
18 → **7**, `learned-name2` 는 17 → **13** 으로 **더 떨어진다.** 단일 실행에서
우연히 높던 값이 평균으로 수렴한 것이다 — 기각 근거가 살아 있다.

**② 선택도 중앙값이 새 지표가 된다.** `effect+nhanes` 는 합의 Top-30 조차
**39% 의 부분표집에서 탈락**한다(0.61). §17d 의 "sd 8.9" 가 여기서도 확인된다.

**③ `union_all` 이 유일하게 현행과 대등하다.** 비추천군 28 동률, 선택도
**0.84 로 최고**, 추천군 21 > 19. §22 에서 "sd 6.91" 로 기각했는데 **합의가 그
분산을 흡수했다.**

### 현행 1 위가 캐러멜 딥이다

단일 실행에서는 야채주스였다. 합의로 보니 **가장 자주 Top-30 에 드는 음식이
캐러멜 딥(라이트)** 이다 — §17b 의 "안 닮아서 올라간다" 가 합의에서 더 분명히
드러난다. `union_all` 1 위는 **현미+완두**, `effect+nhanes` 는 **아티초크** 다.

**숫자는 현행이 좋은데 목록 품질은 아니다.** §17 이후 반복되는 패턴이다.

---

## 24. ★★ 기본 E 를 `union_all` 로 바꾼다 — 수치가 아니라 목록을 보고 (2026-11-24)

§22 에서 `union_all` 을 "안정성 악화(비추천군 sd 6.91)" 로 기각했는데, §23 의
**합의 Top-K 가 그 분산을 흡수한다.** 합의 아래에서 다시 쟀다.

| | 현행 `shrunk` | **`union_all`** |
|---|---:|---:|
| 합의 추천군 | 19 | **21** |
| 합의 비추천군 | **28** | **28** (동률) |
| 합의 위반 | **0** | 1 |
| **선택도 중앙** | 0.82 | **0.84** |

**수치로는 못 가른다.** 그래서 목록을 봤다.

### 상위 — `union_all` 이 분명히 낫다

| 현행 합의 Top 12 | `union_all` 합의 Top 12 |
|---|---|
| 야채주스 · **캐러멜 딥(라이트)** · 로메인 | 현미+완두 · 체리 · 블랙베리 |
| 강화음료(FUZE) · **맥도날드 베이컨랜치 샐러드** | 야채수프(저염) · **아티초크 3 종** |
| **잼** · 크랜베리주스 · **오렌지주스** · 과일주스음료 | 여름호박 · 베이비 그린빈 |

**현행 Top 12 에 캐러멜 딥 · 잼 · 맥도날드 샐러드 · 강화음료 · 주스 4 종**이
있다. `union_all` 은 **통채소·통과일·통곡물**이고 파이필링(저칼로리) 하나만
걸린다.

### 바닥 — 현행이 낫다

| | 바닥 |
|---|---|
| 현행 | `separable lean **and fat**` — **지방 포함 부위** |
| `union_all` | `separable lean **only**` — **살코기** |

ModiMedDiet 은 **살코기를 처방**하므로 현행 바닥이 임상적으로 맞다. §22 의
`extras 0` 이 이것이다. 다만 §21b 에서 확인한 **두 기준의 충돌**이라 어느 쪽이
맞다고 단정할 수 없다 — 논문 §4.2.3 은 `Beef Products` 를 통째로 비추천으로
본다.

### ★ 바꾼다 — 그리고 이것이 질적 판단임을 명시한다

**`E_MODE` 기본값을 `shrunk` → `union_all` 로 바꾼다.**

> **근거는 수치가 아니라 목록이다.** 합의 지표 넷 중 셋이 동률이거나 차이가
> 1~2 이고, 그 차이는 §17 의 기준으로 잡음 구간이다. **바꾸는 이유는
> "사용자가 보는 것은 Top-K 이고 거기에 캐러멜 딥과 잼이 있는 것은 명백한
> 오류" 라는 판단**이다.
>
> **이것은 측정이 아니다.** 이 문서의 다른 결정들(채택·기각)은 수치가
> 갈랐는데 이번은 아니다. 동의하지 않을 수 있고, `E_MODE=shrunk` 로 즉시
> 되돌아간다.

바꾸는 쪽의 보조 근거 둘을 적어 둔다.

1. **커버리지** — `F` 열의 비영 `E` 가 66 → **84**. NHANES 만 있던 18 개는
   철·구리·콜린·칼륨·마그네슘·셀레늄·비타민K·카로틴·루테인·인으로,
   ProMENDA(혈중 대사체)에 없던 **미네랄·카로티노이드 축**이다.
2. **선택도** — 0.84 로 다섯 설정 중 최고다(§23). 합의 Top-30 이 부분표집의
   84% 에서 유지된다.

유보도 적는다. `union_all` 은 **NHANES(관찰 연구)를 섞으므로** 역인과·교란이
일부 들어오고, **의미가 다른 두 값을 한 벡터에 넣는다**(ProMENDA = 환자 농도
방향, NHANES = 섭취-결과 연관). §22 가 보인 불안정의 원인이 그것이고, 합의로
가려졌을 뿐 사라진 것은 아니다.

### 기본값 변화 기록

| | 이전 | 이후 |
|---|---|---|
| `E_MODE` | `shrunk` | **`union_all`** |
| `F` 열 | 66 | **84** |
| Top 1 | 야채주스 | **야채수프(저염)** |
| 추천군 · 비추천군 · 위반 | 21 · 26 · 0 | **23 · 28 · 1** |

---

## 25. ★★ 순위 앙상블을 기본값으로 — 섞지 말고 합친다 (2026-11-24)

§22 의 진단은 **이질성**이었다. ProMENDA 는 "환자에서 이 대사물의 **농도**가
높/낮다", NHANES 는 "이것을 **먹으면** PHQ-9 가 높/낮다" 를 잰다. 한 벡터에
넣으니(`union_all`) 비추천군 sd 가 1.96 → **6.91** 이 됐다.

**섞지 않고 합친다.** 각 `E` 로 끝까지 점수를 낸 뒤 **백분위 순위**를 평균한다.

```
P_final(food) = mean( pct_shrunk(food), pct_nhanes_all(food) )
```

`recommend()` 가 한 번 가로채고 각 모드를 재귀 호출한다 — 쓸기·부트스트랩·
평가가 전부 앙상블을 쓴다. `ENSEMBLE=none` 으로 끈다.

### 두 소스는 거의 독립이다

**두 순위의 Spearman ρ = 0.188.** 앙상블의 전제가 확인된다 — 상보적이니 합칠
가치가 있다. 동시에 §9·§20 의 결론("두 소스는 다른 것을 잰다")이 **순위
수준에서도** 확인된다.

### 점수

| 설정 | 추천군 | 비추천군 | 위반 | 1 위 |
|---|---:|---:|---:|---|
| `shrunk` 단독 | 21 | 26 | **0** | 야채주스 |
| `nhanes_all` 단독 | 19 | **2** | 3 | 고단백 분말 |
| `union_all` (벡터 합치기) | 23 | **28** | 1 | 야채수프(저염) |
| **앙상블** (순위 합치기) | **27** | 26 | 1 | **오크라(조리)** |

`nhanes_all` 단독은 비추천군 **2** 로 참담한데 순위로 합치니 **26** 으로
회복된다.

### 안정성 — 진단이 절반 맞았다

| | 추천군 sd | **비추천군 sd** | 위반 sd |
|---|---:|---:|---:|
| `shrunk` | **5.27** | **1.96** | **0.48** |
| `union_all` | 5.88 | **6.91** | 2.08 |
| **앙상블** | 6.13 | **3.18** | 2.02 |

**비추천군 sd 6.91 → 3.18 (−54%)**, 구간도 [5,30] → **[18,29]**. §22 의 진단이
맞았고 순위 합치기가 그 절반을 해결한다. 다만 `shrunk` 의 1.96 에는 못 미치고
추천군·위반은 오히려 나쁘다 — **남은 불안정은 NHANES `E` 자체에서 온다.**

### 목록 — `union_all` 의 두 약점을 고친다

| | `union_all` | **앙상블** |
|---|---|---|
| 상위 | 현미+완두·체리·블랙베리·아티초크 / **파이필링** | 오크라 2 · 라즈베리 · 동부잎 · 겨울호박 · 사과 / **시럽 통조림 3 · 과일펀치** |
| **바닥** | `separable lean **only**` — **살코기** ✗ | `separable lean **and fat**` · **모르타델라** · **모짜렐라** ✓ |

둘 다 §24 의 기준(캐러멜 딥·잼·주스가 상위에 없을 것)은 통과한다. **바닥에서
갈린다** — `union_all` 은 ModiMedDiet 이 **처방하는** 살코기를 바닥에 두는데
(§22·§24 의 지적), 앙상블은 지방 포함 소고기·가공육·치즈를 둔다.

### 기본값을 앙상블로 바꾼다

| | §24 (`union_all`) | **§25 (앙상블)** |
|---|---|---|
| 추천군 | 23 | **27** |
| 비추천군 | **28** | 26 |
| 비추천군 sd | 6.91 | **3.18** |
| 바닥 | 살코기 ✗ | **지방 소고기·가공육** ✓ |

**§24 의 두 약점(바닥 살코기 · sd 6.91)을 모두 개선하면서 추천군은 더 높다.**

> **§24 와 마찬가지로 질적 판단이 섞여 있다.** 비추천군은 28 → 26 으로
> 내려가고 위반·추천군 sd 는 `shrunk` 보다 나쁘다. 바꾸는 근거는 **바닥 목록이
> 임상 기준과 어긋나지 않는다**는 점과 **sd 가 절반으로 준다**는 점이다.
> 앞의 것은 판단이고 뒤의 것은 측정이다. `ENSEMBLE=none` 으로 되돌아간다.

### 기본값 변화 기록

| | 2026-11-23 이전 | §24 | **§25 (현재)** |
|---|---|---|---|
| 점수 | `E_MODE=shrunk` | `E_MODE=union_all` | **앙상블 `shrunk`+`nhanes_all`** |
| Top 1 | 야채주스 | 야채수프(저염) | **오크라(조리)** |
| 추천군·비추천군·위반 | 21·26·0 | 23·28·1 | **27·26·1** |

---

## 26. 기본값을 바꾸니 E 해석 분기가 세 군데였다 (2026-11-24)

§24·§25 에서 기본값을 두 번 바꾼 뒤 방법 1·2 를 다시 쟀다. **점수는 그대로다.**

| | 결과 | 변화 |
|---|---|---|
| 방법 1 | 재현 **O 14 · △ 4 · X 2** / 타당 **O 12 · △ 5 · X 3** | 없음 (파일 무변경) |
| 방법 2 논문 15 | **12/15** | 없음 |
| 방법 2 우리 15 | 표본이 바뀜 | 분포는 거의 같음 |

방법 1 이 안 바뀐 것은 정상이다 — 20 문항이 KG 질의라 추천 점수를 쓰지 않는다.

### 그 과정에서 버그 둘이 드러났다

**① `basis()` 가 다른 `E` 를 봤다 — 실제 버그.**
새로 뽑힌 Diet recommendation 행의 근거가 이상했다 — **그린빈의 근거가
Palmitic acid**, 블랙베리가 Linoleic acid 였다. 원인은 `basis()` 가
`E['e_shrunk']` **단일 소스**를 보는 것이었다. **점수는 앙상블로 내고 근거는
ProMENDA 로 설명하는 불일치**다. 쓰인 모드들의 `E` 를 각자 정규화해 평균하도록
고쳤더니 그린빈의 근거가 **칼륨**으로 바뀐다 — 타당하다.

(이름도 안 붙었다. NHANES 로 메운 compound 는 ProMENDA 표에 없어
`C00238` 로 나왔다. `setup/nutrient_kegg_map.csv` 로 보충한다.)

**② `compare()` 가 모르는 모드를 조용히 `shrunk` 로 떨어뜨렸다 — 잠복 함정.**
기본 목록(`shrunk,binary,weighted,…`)에는 새 모드가 없어 **틀린 결과가 나온
적은 없지만**, `E_MODES=nhanes_all` 로 주면 이름만 다른 `shrunk` 결과가 나왔다.
이제 에러로 멈춘다.

### 원인은 하나다 — `E` 해석이 세 군데서 따로 자랐다

`recommend()` · `compare()` · `basis()` 가 각자 `E_MODE` 를 해석한다. 기본값이
`shrunk` 하나였던 동안에는 드러나지 않다가 §24·§25 에서 두 번 바꾸자 전부
나왔다.

`e_shrunk` 직접 참조 21 곳을 전수 점검했다. **19 곳은 정당하다** — `E` 를
만드는 곳(`build.py`·`common.py`), `E_MODE` 분기 내부, 그리고 **ProMENDA 와
명시적으로 대조하는 곳**(`invert`·`stype`·`emicrobe`·`nhanes.py`·`disagree`)
이다.

분기를 한 함수로 합치는 것이 근본 해결인데, 각자 필요한 형태가 달라
(비교표는 열 하나, 추천은 벡터) 섣불리 합치면 더 복잡해진다. **지금은 소리
나게 막아 두고** 다음 정리 때 합친다.

---

## 27. ★★ 질적 판단이 두 번 다 틀렸다 — 기본값을 되돌린다 (2026-11-24)

§24(`union_all`)와 §25(앙상블)에서 기본값을 두 번 바꿨는데 **둘 다 수치가 아니라
목록을 눈으로 보고** 내린 판단이었다. 이 문서의 다른 결정은 전부 수치가
갈랐는데 기본값만 다른 기준이었다. **그 판단을 규칙으로 적어 다시 쟀다.**

### 규칙 — 외부 기준에서 가져온다

| | 규칙 | 출처 |
|---|---|---|
| ① | **ModiMedDiet extras** (튀김·패스트푸드·가공육·과자·가당음료·주류·정제곡물) | 외부 임상 기준 |
| ② | **1 회 섭취량 < 5 g** | FDC `food_portion` 측정값 |
| ③ | 보충제·분말 (`powder`/`mix`/`isolate`/`shake`) | 이름 규칙 |
| ④ | 시럽 가공 (`heavy/light syrup`) | 이름 규칙 |

**이 규칙은 실패를 본 뒤에 썼다.** 현재 기본값에 유리하게 고르지 않으려고
① 은 외부 임상 기준 그대로, ② 는 FDC 측정값으로 두고, ③④ 만 이름 규칙이되
특정 음식이 아니라 일반 범주로 적었다. 그리고 **이미 기각한 설정까지 전부**
같은 자로 쟀다 (`python3 ourkg/toperr.py`).

### 결과 — 현재 기본값이 가장 나빴다

| 설정 | **오류/30** | extras | 분말 | 시럽 |
|---|---:|---:|---:|---:|
| **`shrunk`** (§24 이전) | **1** | 1 | 0 | 0 |
| `union_all` (§24) | **1** | 1 | 0 | 1 |
| **앙상블 (§25, 당시 기본값)** | **6** | **6** | 1 | **4** |
| `learned-name2` | 2 | 2 | 0 | 0 |
| `effect+nhanes` | 3 | 2 | 1 | 2 |

### 무엇을 잘못했나

§25 에서 **"§24 의 기준(캐러멜 딥·잼·주스가 상위에 없을 것)은 통과한다"** 고
적었다. 그 말은 맞다 — 캐러멜 딥과 잼은 없다.

**그런데 다른 종류의 오류로 바뀌었을 뿐이다.** 시럽 통조림 4 개와 과일펀치가
들어와 ModiMedDiet extras 가 **1 → 6** 이 됐다. 나는 Top 15 를 보면서 "시럽
통조림 3 · 과일펀치" 를 **흠으로 적어 놓고도** 캐러멜 딥과 같은 무게로 세지
않았다.

> **익숙한 오류는 크게 보이고 덜 익숙한 오류는 작게 보인다.** 눈으로 목록을
> 비교하는 방식 자체의 결함이고, 규칙으로 세니 **6 vs 1** 로 뒤집힌다.
> §24·§25 의 "질적 판단" 두 번이 **모두 틀렸다.**

### 되돌린다 — `E_MODE=shrunk`, 앙상블 끔

| | `shrunk` | `union_all` | 앙상블 |
|---|---:|---:|---:|
| **Top-K 오류** | **1** | **1** | 6 |
| 비추천군 | 26 | **28** | 26 |
| **비추천군 sd** | **1.96** | 6.91 | 3.18 |
| 바닥 | **지방 소고기** ✓ | 살코기 ✗ | 지방 소고기 ✓ |
| 커버리지 | 66 열 | **84 열** | — |

`shrunk` 와 `union_all` 이 오류 1 로 동률인데 **`shrunk` 가 안정성(sd 1.96 vs
6.91)과 바닥 품질에서 앞선다.** `union_all` 의 유일한 우위인 커버리지는 §22 에서
이미 "안정성과 바꾼 것" 으로 결론 났다.

`ENSEMBLE=shrunk,nhanes_all` · `E_MODE=union_all` 로 각각 돌아간다.

### 남는 교훈

1. **목록을 눈으로 보는 비교는 체계적으로 편향된다.** 쓰려면 **규칙으로 적고**
   모든 후보에 같이 적용해야 한다.
2. **"기준을 통과한다" 는 그 기준이 전부일 때만 의미가 있다.** §25 에서 §24 의
   기준(캐러멜 딥·잼)만 확인하고 넘어간 것이 실패의 형태다.
3. 그래도 §25 의 **측정** 부분은 남는다 — 순위 앙상블이 비추천군 sd 를
   6.91 → 3.18 로 줄이는 것은 사실이고, 그 진단(이질적 값을 한 벡터에)도
   유효하다. **틀린 것은 그것으로 기본값을 바꾼 판단이다.**

### 기본값 변화 기록 (최종)

| | §24 이전 | §24 | §25 | **§27 (현재)** |
|---|---|---|---|---|
| 점수 | `shrunk` | `union_all` | 앙상블 | **`shrunk`** |
| Top 1 | 야채주스 | 야채수프 | 오크라 | **야채주스** |
| Top-K 오류 | 1 | 1 | 6 | **1** |

---

## 28. 방법 2 의 지위를 못 박는다 — 우리 추론에는 판별력이 없다 (2026-11-24)

§4.3 에서 "방법 2 는 품질 지표가 아니라 검수 도구다" 라고 적었다. 지금은 **그보다
더 나쁜 상태**이고, 그것을 분명히 적어 둔다.

### 우리 15 건이 전부 1 이다

| 속성 | 건수 | 판정 |
|---|---:|---|
| Complication | 11 | **전부 1** |
| Diet recommendation | 4 | **전부 1** |

그중 **3 건은 연관 문장이 단 1 개**다(초록 20 건 중). 사실상 **"PubMed 에서
초록을 찾았는가" 를 재고 있다.**

### 왜 이렇게 되나 — 둘 다 구조적이다

**① Complication 11 건은 §18 에서 이미 결론 났다.** 질의가 `[질환 A, 질환 B]`
뿐이고 **근거로 적은 미생물이 질의에 안 들어간다.** 검증하는 것은 "두 정신질환이
문헌에 함께 나오는가" 이고, 그것은 미생물과 무관하게 참이다 — 잘 알려진
동반이환이다. 게다가 그 추론 자체가 **55/55 쌍을 통과**시켜 선택성이 0 이다.

**② Diet recommendation 4 건도 느슨하다.** 질의가 `[음식 일반명, depression]`
이라 "양배추와 우울증" 류의 논문이 하나만 있으면 1 이 된다. 음식-질환 쌍의
**방향이나 크기**를 보지 않는다.

**③ −1 은 구조적으로 안 나온다.** §4.3 의 작업에서 판독을 네 군데 고쳐 음성
증거가 1 → 5 행에서 드러나게 했지만, **정답이 −1 인 사례가 논문 #10 하나뿐**
이라 문턱을 검증할 수 없었다. 3 항 질의로 고치는 길은 §5.1 에서 **0/7** 로
실패했다.

### 그래서 어떻게 쓰나

**쓸 수 있는 것 — 논문 15 건에 대한 대조(12/15).** 이것은 *우리 자*를 *논문이
직접 라벨한 15 건*에 댄 것이라 의미가 있다. 균형정확도 0.83(10/11 vs 1/4)도
그 집합에서 잰 값이다.

**쓸 수 없는 것 — 우리 15 건의 숫자.** `1:15` 는 품질이 아니라 **구조의 결과**다.
설정을 비교하거나 개선을 주장하는 데 쓰지 않는다. 표본이 KG·설정이 바뀔 때마다
교체되므로 **시계열 비교도 안 된다**(§21 이후 네 번 바뀌었다).

> **논문도 같은 한계를 갖는다.** Table 5 의 11/15 는 같은 방식으로 얻은
> 것이고, 그중 8 건이 Complication 이다. 논문이 "only one is contradicted"
> 라고 적은 것은 **반대 증거를 찾는 질의를 하지 않았기 때문**이기도 하다.

### 고치려면

음식-질환-물질 **3 항**을 모두 질의에 넣어야 하는데 §5.1 에서 0/7 로 실패했다
— 문헌에 세 항이 함께 명시되는 일이 드물다. 당시에는 남은 길이 **외부에서 −1
정답셋을 만드는 것**(예: Cochrane 리뷰의 "no evidence")이라고 적었는데, 그
도구는 **접었다** — "치료 효과에 근거가 없다" 는 "관계가 없다" 가 아니다(§41 ①).
방법 2 의 막힌 자리는 집합 모양이 아니라 **3 항 공출현의 희소성**이라, §41 의
라벨 없는 진단이 그대로 옮겨지지 않는다.

**지금은 "방법 2 를 평가 지표로 쓰지 않는다" 고 선언하는 것이 정직하다.**

---

## 29. 지표 충돌의 크기를 재고 드러낸다 — 살코기 적색육 (2026-11-24)

§21b·§22·§24 에서 같은 충돌이 세 번 나왔다. 논문 §4.2.3 은 `Beef/Pork Products`
를 **통째로 비추천**으로 보는데 SMILES/ModiMedDiet 은 **살코기 적색육을 주
3-4 회 처방**한다. 크기를 쟀다.

| | |
|---|---:|
| 논문 비추천 군 음식 | 3,555 |
| 그중 `separable lean only` | **500 (14%)** — 충돌 구역 |
| 군별 | Beef 386 · Pork 114 |

### 설정에 따라 바닥을 메운다

| 설정 | Top30 위반 (그중 살코기) | Bot30 비추천군 (**그중 살코기**) |
|---|---|---|
| **현행 `shrunk`** | 0 (0) | 26 (**0**) |
| `union_all` | 1 (0) | 28 (**25**) |
| `learned-name2` | 2 (0) | 17 (0) |
| `effect+nhanes` | 1 (0) | 18 (6) |

**현행은 충돌이 0 이다** — 비추천군 26 이 전부 **지방 포함** 부위라 논문 기준과
임상 기준이 일치한다.

> **★ §22·§24 의 읽기를 정정한다.** "`union_all` 의 비추천군 28 이 현행 26 보다
> 높다" 고 적었는데, 그 **28 중 25 개가 충돌 구역**이었다. 논문 라벨은 +1 을
> 주고 임상 기준은 −1 을 주는 음식으로 쌓은 숫자다. §27 에서 `shrunk` 로
> 되돌린 판단이 **이 측면에서도 옳았다** — 당시엔 Top-K 오류만 근거로 들었다.

### 어느 쪽이 맞다고 정하지 않는다 — 드러낸다

논문의 피라미드(Fig 5)는 "barbecue products, beef products, sausages and
luncheon meats, pork products" 를 통째로 상단(비추천)에 둔다. ModiMedDiet 은
지방을 뗀 적색육을 처방군에 넣는다. **둘 다 자기 맥락에서 일관되고**, 우리가
한쪽을 고를 근거가 없다.

대신 `sweep.py` 의 비교표에 **`bot30_충돌(살코기)` 열을 더했다.** "비추천군 28"
같은 숫자를 읽을 때 **몇 개가 엇갈리는 음식인지** 바로 보인다.

---

## 30. 데이터 한계를 확정한다 (2026-11-24)

남은 미해결 중 **공개 데이터에 없어서 닫히는 것**들을 확정한다. 할 일이 아니라
한계다.

### `#7` — 세 번째 소스로도 안 열린다 (표를 2026-11-24 에 고쳤다)

> **먼저 정정.** 이 절을 처음 쓸 때 KEGG 칸에 ✗ 를 넣고 "성격이 다른 세 소스
> 모두에 없다" 고 썼다. **KEGG 칸이 틀렸다.** `compound_microbe.csv` 에
> `C00072,1685,bbv`(*Bifidobacterium breve*, 종 수준)가 **그때도 있었다**.
> 측정 상관에서 속 단위로 "ascorbate 없음" 을 확인한 뒤 나머지 두 칸을 재지
> 않고 속 전체로 넓혔다. 질문이 묻는 것은 속이 아니라 **종**이다.

`#7` 이 묻는 것은 ***Bifidobacterium longum*** 이다(taxid 216816). 그 종으로
다시 재면:

| 소스 | 성격 | *B. longum* 의 링크 | ascorbate |
|---|---|---:|---|
| KEGG | 유전체 효소 **추론** | 24 | ✗ |
| VMH/AGORA2 | 유전체 재구성 **예측** | 546 | ✗ |
| **측정 상관** (13 코호트) | **관측** | 23 (속 단위) | ✗ |

**종 수준에서는 세 소스 모두에 없다** — `△` 판정과 평가 노트는 맞았다. 다만
속으로 넓히면 *B. breve* 에 KEGG 링크가 있어, "*Bifidobacterium* 에 ascorbate
경로가 없다" 는 더 센 주장은 **성립하지 않는다**. ascorbate 를 가진 균은
KEGG 144 종 · VMH 1 종 · 측정 4 속이다.

### `#19` — Prevotella 의 근거가 가장 얇다

논문 답의 3 위가 `Prevotella` 인데 측정 상관 링크가 **6 개**로 우리가 가진
속 중 가장 적다(Escherichia 40 · Streptococcus 39 · Bacteroides 24).
그래서 상위 3 속에 못 든다.

| 속 | 측정 링크 |
|---|---:|
| Escherichia | 40 |
| Streptococcus | 39 |
| Bacteroides | 24 |
| Bifidobacterium · Adlercreutzia | 23 |
| **Prevotella** | **6** |

### 나머지

- **`#12` 분류** — FoodOn·중국 온톨로지에 `Milk substitutes`·`Baby Foods` 가
  없다(FDC/WWEIA 어휘다). SNOMED CT 배포본은 라벨·계층 없는 id 284 개뿐.
  **공개 KG 도 답하지 못한다.**
- **합병증 추론 검증** — 3 항 질의가 §5.1 에서 0/7 로 실패했다. 당시에는 외부
  −1 정답셋(예: Cochrane "no evidence")이 필요하다고 적었는데 **그 진단이
  틀렸다** — 라벨 없이 답이 나오고, 소스를 바꾸면 판별력이 생긴다 (§41).
- **미생물 속 수준 55%** — `match_rank` 로 구분해 담았고 평가 어댑터는 종
  수준만 쓴다 (§DATA 6).

---

## 31. ★★ gutMDisorder 가 살아 있었다 — 그리고 미생물 신호가 재현되지 않는다 (2026-11-24)

### 죽은 줄 알았던 것은 옛 호스트였다

[`DATA.md` §12](DATA.md) 에 "논문 §2 가 든 gutMDisorder 는 호스트가 죽어
Disbiome 으로 갈음한다" 고 적어 뒀다. **절반만 맞았다.** 죽은 것은 옛 호스트
(`bio-annotation.cn`, 지금도 타임아웃)이고, **v3 는 하얼빈의대 새 호스트에서
돌아간다**. 즉 Disbiome 은 대체재가 아니라 **병렬 소스**였다. 둘 다 올리고
출처 태그로 분리한다 ([`DATA.md` §12b](DATA.md)).

페이지가 SPA 라 HTML 에는 표가 없다. 번들의
`/gutMDisorder_api/api/resource/download?fileName=` 가 xlsx 를 준다.

### 이 소스가 Disbiome 보다 나은 두 가지

1. **질환이 MeSH descriptor 로 원본에 붙어 있다** (`Condition1ID = D003093`).
   §12 에서 가장 약한 고리였던 이름 매칭 사다리를 **안 탄다** — mesh_lookup
   해소율 38%, contains 오매칭을 별칭표로 덮던 수작업이 여기엔 없다.
2. 행마다 방향·p값·분류 계급·근거(PMID 또는 BioProject)가 있다.

### 함정 — 비교쌍의 62% 는 방향을 쓸 수 없다

`Alteration` 은 `Condition1` 의 `Condition2` 대비 증감이다. **Condition2 가
Health 인 행만** "질환에서 증가/감소" 로 읽을 수 있다. 나머지는

| 실제로 무엇인가 | 예 |
|---|---|
| 중재 vs 대조 | Yogurt vs No yogurt · Inulin vs Placebos |
| 질환 vs 질환 | 궤양성대장염 vs 크론병 · 위암 vs 위축성위염 |
| 중증도 | 임상적 악화 vs 자연완화 |
| 인구집단 | African American vs Non-Hispanic white |

그대로 합치면 **"요구르트를 먹으면 늘어나는 균" 이 "질환에서 늘어나는 균" 으로
뒤집혀 들어간다.** Human + `Condition2ID = D006262(Health)` + phenotype 세
조건으로 걸러 24,750 → **9,374 행(38%)** 만 쓴다. Health 가 Condition1 쪽에
온 행은 **0 행**으로 확인했다.

### 데이터가 얼마나 늘었나

| | 전 | 후 |
|---|---:|---:|
| focus 미생물 | 485 | **798** |
| KEGG organism 코드 연결 | 167→(종 182) | **564** (종 242 · 속 322) |
| compound-미생물 (KEGG 추론) | 10,257 | **14,918** (종 6,400 · 속 8,518) |
| 미생물-질환 (큐레이션) | Disbiome 1,193 | + **gutMDisorder 1,239** (균 499 · 질환 18) |
| KG triple | 3,535,812 | **3,553,206** (관계 36) → §32 로 **3,554,466** (38) |

우울증 관계가 **배포 KG 1 건 → 23 건**이 됐다. 파킨슨 663 · 자폐 117 ·
알츠하이머 116 이 따라 들어왔다.

### ★ 그런데 신호는 재현되지 않는다 — 이게 이번의 결론이다

데이터가 두 배가 됐으니 `emicrobe` 의 방향 검정을 **독립된 두 번째 소스로**
다시 할 수 있다. 전에 Disbiome 쪽에서 유일하게 0.5 를 넘겼던 칸이
`측정 상관 × 우울증만 × 감소=이로움` 의 **부호일치 0.585 (p=0.017)** 였다.

| 질환범위 | 링크 | 방향가정 | compound | 부호일치 | p | q(BH) |
|---|---|---|---:|---:|---:|---:|
| **gutMD/우울증만** | measured | **증가**=이로움 | 102 | 0.618 | 0.011 | 0.119 |
| **Disbiome/우울증만** | measured | **감소**=이로움 | 164 | 0.585 | 0.017 | 0.119 |
| 두 소스 합/정신질환 | measured | 감소=이로움 | 205 | 0.576 | 0.018 | 0.119 |
| Disbiome/정신질환 전체 | measured | 감소=이로움 | 202 | 0.569 | 0.029 | 0.143 |

**두 소스가 서로 반대 방향을 가리킨다.** Disbiome 은 "질환에서 줄어든 균이
대사하는 compound 가 이롭다", gutMDisorder 는 그 반대다. 둘 다 0.5 를 조금
넘겼고 둘 다 명목 p<0.05 다 — 즉 **0.585 는 신호가 아니라 소스에 딸린
잡음이었다.**

그리고 애초에 20 칸을 뒤져 가장 작은 p 를 집는 것은 검정이 아니다. BH 를
`emicrobe` 에 넣었다: **q<0.05 가 0/20**. 코드가 그 줄을 직접 출력한다.

> **판정**: 미생물 축의 데이터를 1.6 배로 늘리고 질환 식별을 개선했는데도
> E 를 유도할 방향 신호는 **없다**. §15c 에서 구조 진단(`S` 가 99.3% 꽉 차
> `D` 의 변조가 묻힌다)으로 기각했던 미생물 매개 가중은, 이제 **구조와 무관하게
> 재료 쪽에도 신호가 없다**는 것으로 두 번 기각된다. 데이터를 더 모아서
> 풀 문제가 아니다.

### 값어치는 추천 점수가 아니라 KG 쪽에 남는다

추천 순위는 바뀌지 않는다 — `E × Fᵀ` 에 미생물이 들어갈 자리가 없다는 §A 의
구조 문제가 그대로다. 남는 것은 **우리 데이터 구축의 질**이다: 논문 §2 가 든
DB 를 대체재가 아니라 원본으로 담았고, 질환 식별이 이름 매칭을 안 타고,
종 수준 compound 링크가 6,400 으로 늘었고, 방향·p값·근거 PMID 가 행마다 붙었다.

---

## 32. ★★ 방향을 쌍 단위로 합의 본다 — 그리고 신호는 단일 소스 잡음이었다 (2026-11-24)

§31 에서 두 소스가 반대 부호를 냈다. **왜** 그런지를 쌍 수준에서 쟀다.

### 두 큐레이션 소스는 방향에서 우연만큼 일치한다

| 범위 | 공유 (균, 질환) 쌍 | 방향 일치 | |
|---|---:|---:|---|
| 전체 질환 | 474 | 271 | 57.2% |
| **KG 가 담는 정신·신경** | **125** | **63** | **50.4%** (이항검정 p=0.5) |

> **갱신 (2026-11-25).** 이 수치는 같은 균을 두 taxid 로 보고 있었다. 정본으로
> 모아 다시 재면 **128 쌍 · 일치 62 (48.4%) · p=0.671** 이다 — §35.

**우리가 실제로 쓰는 쌍에서는 동전 던지기와 구별되지 않는다.** 질환별로 보면
더 나쁘다:

| 질환 | 일치 | 불일치 |
|---|---:|---:|
| 파킨슨 | 43 | 29 |
| **자폐** | **9** | **25** ← 우연보다 나쁘다 |
| 알츠하이머 | 6 | 4 |
| 우울증 | 1 | 3 |

각 소스는 **자기 안에서도** 어긋난다 — Disbiome 325/4,592(7.1%) ·
gutMDisorder 294/6,665(4.4%). 같은 균·질환을 다른 연구가 반대로 보고한 것이다.

> **정정.** 이 측정을 처음 보고할 때 "613 쌍 중 65% 일치" 라고 했다. 행 단위
> 조인이라 한 쌍이 여러 번 세어졌다. 쌍 단위로는 474 쌍 · 57.2% 이고, 정신·신경
> 으로 좁히면 **125 쌍 · 50.4%** 다.

### 고친 것 — 출처별로 올리던 방향을 쌍 단위 합의로 바꿨다

전에는 Disbiome 과 gutMDisorder 가 **각자** `our:abundanceIn` 을 올렸다. 출처
태그로만 갈라 두니 KG 를 쓰는 쪽이 모순을 직접 밟는다. `common.
microbe_disease_direction()` 이 쌍마다 판정하고 `kg()` 이 그 결과만 올린다.

| | triple |
|---|---:|
| `our:abundanceIn` (방향 합의 쌍) | **1,519** |
| `our:crossSourceAgreement` (합의 근거 — 어느 소스 몇 개) | 1,519 |
| `our:abundanceConflict` (모순 쌍 — 방향 **안** 올림) | **163** |

**불일치 쌍을 버리지 않는다.** "연관은 있고 방향은 모른다" 가 실제로 우리가 아는
것이고, 버리면 그 사실이 KG 에서 사라진다. `증가2:감소1|Disbiome+gutMDisorder`
처럼 어긋난 내용을 적어 감사 가능하게 둔다. `mpq:hasAssociation` 은 출처별로
그대로 남으므로 출처 추적은 잃지 않는다.
산출물 `out/microbe_disease_agreement.csv` (쌍 1,682).

### ★ 그래서 신호가 있나 — 가장 엄격한 부분집합에서 사라진다

`emicrobe` 에 합의 범위 둘을 넣고 다시 쟀다.

| 범위 | 링크 | compound | 부호일치 | p | q(BH) |
|---|---|---:|---:|---:|---:|
| Disbiome/우울증만 | measured | 164 | 0.585 | 0.017 | 0.125 |
| **합의 쌍만**/정신·신경 | measured | 210 | **0.595** | **0.0035** | 0.098 |
| **합의+2소스**/정신·신경 | measured | 164 | **0.476** | 0.759 | 0.998 |

읽는 법이 중요하다. 합의 쌍으로 좁히면 명목 p 가 0.017 → **0.0028** 로 가장
좋아진다. 그런데 **두 소스가 둘 다 말하고 둘 다 같은 방향인** 가장 엄격한
부분집합(n=164)은 **0.476 — 우연 이하**다.

> 즉 그 "신호" 는 **한 소스만 말한 쌍에 들어 있다.** 두 소스가 독립적으로
> 확인해 준 쌍만 남기면 없어진다. §31 의 결론이 더 강해진다 — 데이터를
> 더 모아서 풀 문제가 아니고, **독립 확인을 요구하면 남는 게 없다.**
> BH 보정 후 q<0.05 는 여전히 **0/28** 이다.

### 값어치

추천 순위는 바뀌지 않는다(`E × Fᵀ` 구조 문제 그대로). 남는 것은 두 가지다.
**(1)** KG 가 더 이상 스스로 모순되는 방향을 주장하지 않고, 모르는 것을
모른다고 말한다. **(2)** 소스를 두 개 둔 값어치가 규모가 아니라 **대조**에
있다는 것이 수치로 확인됐다 — 하나만 있었으면 0.585 를 신호로 보고했을 것이다.

---

## 33. ★★ 중재 데이터로 E 를 검정한다 — 예측이 틀렸다 (2026-11-24)

§31·§32 의 결론("미생물 축에 방향 신호가 없다")에는 빠져나갈 구멍이 하나
있었다. **그 자료가 전부 관측**이라는 것이다 — "질환에서 늘어난 균" 은 인과가
아니다. 환자가 아파서 그 균이 늘었을 수도 있다. 그래서 중재 자료로 다시 쟀다.

### 버린 62% 안에 `음식 → 미생물` 이 있었다

[`DATA.md` §12b](DATA.md) 에서 방향을 못 믿어 버린 행 중 **식이 중재**가 있다.
저쪽은 `Condition2 == Health` 를 요구해서 중재 행이 전부 탈락했는데, 중재 행은
음식을 주고 균이 변하는 것을 본 것이라 **방향이 음식 → 미생물** 이다. 우리
`E × Fᵀ` 에 미생물이 들어갈 자리가 없다는 구조 문제의 빠진 간선이다.

**여기서도 같은 규율을 적용했다.** 대조군이 무중재가 아니면 증감이 "다른 식단
대비" 다 — 식이 중재 메타행 147 중 **60(41%)이 다른 식단과의 대조**였다
(저항전분 저 vs 고 · 폴리덱스트로스 vs 옥수수섬유 · 저섬유/중지방 vs
저섬유/고지방). 섞으면 부호가 뒤집힌다.

| | 수 |
|---|---:|
| 식이 중재 메타행 (Human) | 147 |
| 그중 **무중재 대조** (`No X` · 위약 · 동반질환만) | **87** |
| 연관행 | 603 (방향 있는 것 547) |
| compound 링크가 있는 균으로 좁힌 뒤 | **318 행 / 중재 48 / 균 128** |

### ★ 예측을 먼저 고정하고 쟀다

`score = 늘어난 균이 대사하는 compound 의 평균 E − 줄어든 균의 평균 E`

48 개를 다 보고 양수인 걸 골라 "맞았다" 고 말하는 것을 막으려고, 계산 전에
코드에 두 줄을 적었다 (`diet_intervention.PRESPECIFIED`):

| 중재 | 예측 | 실제 | |
|---|---|---:|---|
| **지중해식** (ModiMedDiet 가 우울증에 처방한 식단) | > 0 | **+0.0253** | 맞음 |
| **고지방식** | < 0 | **+0.0418** | **틀림** |

**1/2 다. 그리고 틀린 쪽이 더 크다** — 고지방식이 지중해식보다 "좋은" 점수를
받았다. 판별력이 없다.

지중해식의 +0.0253 도 믿을 게 아니다. 두 변형이 서로 반대다:

| | n(증가·감소) | score |
|---|---|---:|
| `Diet, Mediterranean` | 4 · 2 | **−0.0020** |
| `Diet, Mediterranean(non-energy restricted)` | 2 · 3 | **+0.0477** |

합친 양수는 **한 연구에서 나온 것**이다. 순열검정(라벨만 섞기, 2000 회)으로
48 중재 중 29 개를 재서 BH 보정하면 **q<0.05 가 0/29**, 최소 q 가 0.875 다.
명목 p<0.05 는 `Probiotics`(0.034) 하나인데 그건 **균을 직접 먹인 것**이라
우리 가설과 무관하다(먹인 속이 늘어나는 건 당연하다).

> **판정**: 관측(§31·§32)에 이어 **중재 자료로도 판별력이 없다.** "관측이라
> 인과가 아니어서 안 보인 것" 이라는 구멍이 닫혔다. 미생물 매개 가중은 세 번
> 기각된다 — 구조(§15b) · 재료(§31·§32) · 인과 방향(여기).

### 단서 하나는 남는다 — 이 검정이 음수를 설명하지 못한다

`compound_microbe` 는 "이 균의 유전체에 이 compound 를 다루는 효소가 있다" 이고
**분해인지 생산인지 모른다**(§15b 와 같은 한계). 그래서 음수가 나와도 "가정이
틀렸다" 가 아니라 **"이 자료로는 못 본다"** 일 수 있다. 양수로 나왔을 때만
한 방향으로 강한 주장이 됐을 것이고, 그게 안 나왔다. 코드와 문서에 이 한계를
적어 둔다 — 이 검정으로 가설을 **반증**했다고 말하지 않는다.

### `food → microbe` 간선은 넣을 수 없다 — 매칭 노력이 아니라 자료 때문이다

문제를 처음 제시할 때 "159 표기 중 1 개만 음식명과 맞는다 — 매칭 작업이 필요"
라고 했다. 대조군 규율을 적용한 뒤 다시 세니 더 나쁘다:

| | 수 |
|---|---:|
| 쓸 수 있는 중재 표기 | 58 |
| FDC 음식 이름과 **정확** 일치 | **0** |
| F 층 compound 이름과 정확 일치 | **0** |
| 부분 일치 후보가 있는 표기 | 4 |

후보 4 개를 열어 보면 실제 음식은 **모유(55 행)와 연어(3 행) 둘**이다
(`Probiotics` 는 브랜드 제품명에 걸린 오탐, `Yogurt` 는 후보 146 개로
큐레이션이 필요하다). 나머지 54 개는 **식단 패턴**(지중해식·케토제닉·저FODMAP) ·
**분리 섬유**(이눌린·폴리덱스트로스·아라비노자일란) · **프로바이오틱스** ·
**생약**(triphala·Manjistha·Photinia) 이라 FDC 음식이 아니다.

> 즉 이건 큐레이션을 더 해서 열리는 문제가 아니다. **무중재 대조로 걸러낸
> 중재는 거의 전부 FDC 가 다루지 않는 것들이다.** `음식 → 미생물` 간선은
> 음식 2 개 · 58 행으로는 KG 에 올릴 의미가 없다.

산출물: `out/diet_intervention.csv`(318) · `out/diet_intervention_score.csv`(29)
· `out/diet_intervention_map.csv`(58). 코드 `ourkg/diet_intervention.py`,
`run_all.py` 의 `diet_iv` 단계.

---

## 34. ★★ 검정력 반론에 답한다 — 자폐로 `E` 를 측정에서 만들어 (2026-11-24)

§31~§33 이 전부 "미생물 축에 방향 신호가 없다" 로 끝났다. 거기엔 반론이 하나
남아 있었다 — **우울증 자료가 너무 얇다.** 배포 KG 의 우울증 미생물 관계는
1 건, gutMDisorder 를 넣어 23 건이다. 그 23 건으로 "신호가 없다" 고 말하는
것은 검정력 문제와 구별되지 않는다.

실제로 gutMDisorder 가 늘려 준 방향은 우울증이 아니었다:

| 질환 | 관계 | 비중 |
|---|---:|---:|
| 파킨슨 (+동반) | 672 | **54%** |
| 자폐 | 117 | 9% |
| 알츠하이머 | 116 | 9% |
| **우울증** | **23** | **1.9%** |

### 왜 파킨슨이 아니라 자폐인가

파킨슨이 가장 두텁지만 **`E` 를 만들 소스가 없다.** MENDA/ProMENDA 는 우울증
전용이고 파킨슨 쪽에는 그에 상당하는 큐레이션 대사물 DB 가 없다 — 개별 연구
표만 있다. 한 연구 표로 `E` 를 지어내면 995 연구 합의인 ProMENDA 와 비교할 때
비교 자체가 불공정해진다. **지어내지 않았다.**

자폐는 다르다. 우리가 이미 쓰는 분변 대사체 모음([`DATA.md` §13](DATA.md))에
**`KANG_AUTISM_2017`** 이 있다 — 자폐 23 명 vs 신경전형 21 명, KEGG 로 붙는
대사물 57. 문헌 투표가 아니라 **측정된 환자-대조 차이**다.
`ourkg/e_autism.py`, `run_all.py` 의 `e_autism` 단계.

- 효과크기는 **rank-biserial 상관**(Mann-Whitney 에서 `2U/n₁n₂ − 1`). 44 명
  표본에 평균차를 쓰면 이상치에 끌린다.
- 부호 규약은 `common.polarity` 와 같게 — **환자에서 감소 = 양수(이로움)**.
- **`e_autism` 자체가 약하다**: BH 후 q<0.05 가 **0/57**, `|e|>0.3` 이 5 개다.
  이걸 확립된 기준으로 쓰지 않는다 — 아래 결과를 읽을 때 같이 봐야 한다.

### ProMENDA 의 `E` 는 자폐의 측정 방향과 따로 움직인다

공통 compound 53(둘 다 0 아닌 것 47):

| | 값 | p |
|---|---:|---:|
| Spearman rho | **+0.187** | 0.208 |
| 부호일치 | 0.574 | 0.382 |

둘 다 유의하지 않다. 읽기는 **두 가지가 가능하고 가를 수 없다** — ProMENDA 의
`E` 가 질환 특이적이라 자폐와 따로 움직이는 것일 수도, 둘 다 잡음인 것일 수도
있다. `e_autism` 에 BH 유의 compound 가 하나도 없으므로 후자를 배제할 수 없다.

### 자폐에서 미생물 방향 검정 — 역시 안 된다

| 미생물 소스 | 링크 | 방향가정 | 균 | compound | 부호일치 | p | q(BH) |
|---|---|---|---:|---:|---:|---:|---:|
| 합의 쌍만 | species | **증가**=이로움 | 221 | 37 | **0.676** | 0.024 | 0.397 |
| 두 소스 합 | species | **증가**=이로움 | 275 | 37 | 0.676 | 0.024 | 0.282 |
| Disbiome | species | **증가**=이로움 | 203 | 35 | 0.657 | 0.045 | 0.358 |
| gutMDisorder | measured | **증가**=이로움 | 106 | 36 | 0.639 | 0.066 | 0.397 |

**BH 보정 후 q<0.05 가 0/24.** 그리고 자폐에서 가장 좋아 보이는 방향가정은
`증가=이로움` 인데, 우울증에서 가장 좋아 보였던 것은 `감소=이로움` 이었다
(§31). **질환을 바꾸면 부호가 또 뒤집힌다** — §32 에서 소스를 바꿨을 때와
같은 양상이다.

### ★ 그래서 검정력 반론은 어떻게 되는가 — 경계를 계산했다

처음에 이 절은 "끝까지 가를 수 없다" 로 끝났다. **그 서술이 과했다.**
검정력은 열려 있거나 닫혀 있는 것이 아니라 **크기가 있는 양**이고, 그 크기는
우리가 이미 돌린 검정들의 `n` 으로 계산된다. 안 하고 포기했을 뿐이다.

막히는 자리가 질환마다 다른 것은 그대로다:

| | `E` 의 폭 | 미생물 관계 | 검정에 쓰인 compound |
|---|---:|---:|---:|
| 우울증 (ProMENDA 문헌) | **1,412** | 23 | 164~209 |
| 자폐 (KANG 측정) | 57 | **117~290** | 37~40 |

> **둘을 동시에 가진 적이 없다.** 우울증은 `E` 가 넓고 미생물이 얇다. 자폐는
> 미생물이 두텁고 `E` 가 좁다(그리고 그 57 개 중 BH 유의가 0). 그래서
> "신호가 없다" 를 증명하지는 못한다.
>
> 하지만 검정력 **하나로** 설명하려면, **막히는 자리가 다른 두 번의 실패를
> 같은 이유로 묶어야 한다.** 그리고 두 질환에서 가장 좋아 보이는 방향가정이
> 서로 반대다. 신호가 있다면 적어도 부호는 일정해야 한다.

### ★ 최소검출효과 — "모른다" 가 아니라 "여기까지 닫힌다"

부호일치 검정은 이항검정이다. 그러면 주어진 `n` 에서 80% 검정력으로 잡히는
가장 작은 부호일치(MDES)가 닫힌 식으로 나온다. 우리가 돌린 **52 개** 부호일치
검정 전부에 대해 계산했다 (`e_autism.power_report`, `out/power_bound.csv`).

| | 값 |
|---|---:|
| 계산한 검정 | **52** |
| 가장 조인 경계의 `n` | **384** |
| 그 `n` 에서 MDES (α=0.05) | **0.564** |
| 그 `n` 에서 MDES (BH 28검정) | **0.596** |

(이 표의 수치는 README 쪽에 앵커로 묶여 있다 — `RESULTS.md` 는 시간순 기록이라
앵커 검사 범위에서 일부러 빼 둔다.)
| 자기 경계를 넘은 관측 | **0** / 52 |

> **부호일치 0.596 이상인 효과는 배제된다.** 있었으면 잡혔다. 관측 최대는
> 0.644 지만 그 행은 `n=45` 라 경계가 느슨하다 — 경계는 **`n` 이 가장 큰 검정**에서
> 조여지고, 그 검정의 관측은 0.482 로 우연 아래다.
>
> 0.50 ~ 0.596 구간은 열려 있다. **그건 "모른다" 가 아니라 경계가 있는 모름이다.**

그리고 그 열린 구간의 크기는 **쓰면 손해인 크기**다. §28 `gutbrain` 쓸기에서
미생물 가중 α 를 키울수록 비추천군이 **26 → 24 → 23 → 21 → 20** 으로 단조
감소한다 — 0.596 미만의 효과가 실재한다 해도 추천을 개선하지 못한다.
**그래서 미생물 축을 점수에 넣지 않는 결정은 검정력 반론과 무관하게 선다.**

닫히지 않은 쪽은 여전히 데이터다 — 파킨슨급으로 미생물이 두텁고 ProMENDA 급으로
`E` 가 넓은 질환이 공개 데이터에 없다 (§30 과 같은 종류의 한계다). 다만 그
공백의 크기를 이제 숫자로 적는다.

산출물: `out/compound_autism.csv`(57) · `out/e_autism_microbe.csv`(24) ·
`out/power_bound.csv`(52).
`analyze._measured_links` 를 `common.measured_links` 로 옮겼다 — 두 모듈이
쓰게 되면서 복사하면 또 갈라진다.

---

## 35. 폐기된 taxid 와 중복 statement 를 정리했다 (2026-11-25)

미생물 축을 다시 세다가 `focus 798` 중 `microbes.csv` 에 **791** 만 들어 있는
것을 봤다. 둘이 다른 이유를 따라갔다.

### 외부 소스는 폐기된 NCBI taxid 를 들고 있다

Disbiome 의 *Klebsiella* 는 `160674`, gutMDisorder 는 `570` 인데 NCBI 에서 둘 다
`570` 이다. 폐기·병합된 id 로 조회하면 NCBI 는 **현재** TaxId 로 돌려주고 요청한
id 를 `AkaTaxIds` 에 넣는다. `build.microbe()` 가 반환된 id 로만 키를 걸고 있었다.

| 결과 | 수 |
|---|---:|
| 요청한 id 가 캐시에 안 들어와 축에서 빠진 균 | **12** |
| 그 균의 노드 — 질환 관계는 있는데 라벨·rank·계통·compound 링크가 없다 | 12 |
| 아무 소스도 요청하지 않은 정본 id 가 새로 생긴 것 | **5** (compound 링크 144 개 보유) |
| `cached_covering` 이 요청을 못 덮어 매 실행마다 전체 재조회 | 798 건 |

빠진 12 건은 *Blautia producta* · *Megasphaera* · *Klebsiella* · *Dialister* ·
*Lactobacillaceae* 처럼 실재하는 장내 분류군이고, 그중 9 건은 KEGG organism
코드까지 붙는다. NCBI 는 정상 응답한다 — 우리 쪽 처리였다.

**고친 것**: `AkaTaxIds` 를 읽어 **요청한 id 로도** 키를 걸고 정본 id 를
`taxid_current` 열에 남긴다. 끝까지 안 오는 id 는 몇 개인지·어느 id 인지 출력한다.
적재는 캐시가 아니라 `focus` 로 한다(캐시는 지난 실행의 taxid 도 들고 있다).

### 정체성은 정본으로 모아야 한다 — 처음 판단이 틀렸다

처음에는 "두 id 를 그대로 두고 드러내기만 한다" 로 두었다. **그러면 안 된다.**

- **셀 때 두 번 센다.** compound 링크가 14,918 → 15,065 로 늘어 보이는데 고유
  (균, compound) 쌍은 **14,918 그대로**다. 늘어난 147 은 같은 균을 두 id 로 센
  것이다. 실제로 좋아진 것은 양이 아니라 **도달성** — 링크 144 개가 아무 소스도
  쓰지 않는 id 에서 소스가 쓰는 id 로 옮겨갔다.
- **두 소스가 서로 다른 균으로 보인다.** §32 의 방향 교차검사가 그 7 균을
  비교하지 못하고 있었다.

`common.taxid_alias()` 를 두고 `compound_microbe()` · `measured_links()` ·
`microbe_disease_direction()` · KG 미생물 URI 가 모두 정본을 쓴다. 원 id 는
`our:akaTaxid` 로 KG 에 남는다.

### §32 수치를 고친다 — 결론은 같은 방향으로 더 강해진다

| | 전 (id 분리) | **후 (정본)** |
|---|---:|---:|
| 두 소스 공유 (균, 질환) 쌍 | 125 | **128** |
| 방향 일치 | 63 (50.4%) | **62 (48.4%)** |
| 이항검정 p (>0.5) | 0.5 | **0.671** |

자폐는 9:25 → **9:26**. 제대로 비교하니 일치가 **우연 아래**다.

### KG 는 중복 statement 를 담지 않는다

RDF 그래프에는 같은 삼중항이 두 번 있을 수 없다. 그런데 음식마다 · 트리 번호마다
루프를 돌며 같은 삼중항을 다시 쓰고 있었다.

| | 수 |
|---|---:|
| 전 (쓴 줄 수) | 3,554,795 |
| **후 (고유 triple)** | **3,441,322** |
| 생성 쪽에서 없앤 반복 | 95,666 |
| writer 가 막은 중복 | 17,807 |

생성 쪽 둘:

| 자리 | 전 | 후 | 왜 |
|---|---:|---:|---|
| FoodOn/OLS 조상 | 119,841 | **25,759** | 클래스 계층을 **음식마다** 올렸다. 계층은 음식 수와 무관하다 |
| MeSH tree 조상 | 4,702 | **3,118** | 한 질환의 트리 번호마다 같은 조상·라벨을 다시 올렸다 |

`sort -u` 로 파일을 직접 확인했다 — 3,441,322 줄, 중복 0. 비용은 peak 733 MB ·
13 초다(128 비트 digest 를 int 로만 들고 있다).

> **중간에 한 번 더 틀렸다.** 중복 제거 **후**에 출처를 세게 두었더니
> `gutMDisorder` 가 3,717 → 745 로 떨어졌다. 내용이 줄어서가 아니라 먼저 쓴
> Disbiome 이 공유 삼중항을 가져가서였다 — **쓰는 순서에 의존하는** 수치다.
> 출처 집계를 중복 제거 **전**으로 옮겼다. 겹침은 버릴 정보가 아니다: VMH 와
> KEGG 가 같은 `hasMetabolites` 1,353 건을 독립적으로 주장하는 것은 서로를
> 뒷받침한다. `kg_stats.csv` 에 `Σ 출처 주장` 과 `Total (고유 그래프)` 두 줄을
> 따로 적고, 논문 Table 1 과 비교할 때는 고유 쪽을 쓴다.

`recommendation.csv` 는 재실행해서 무변동을 확인했다.

---

## 36. 정합 검사를 넣었다 — 그리고 넣다가 구멍 둘을 더 찾았다 (2026-11-25)

§35 까지 오면서 같은 모양의 문제가 반복됐다. **실패해도 출력이 그럴듯하다.**
그래서 전부 우연히 발견됐다 — 쓸기 하나가 안 돌고 있던 것, `union` 이 조용히
`shrunk` 로 떨어지던 것, `basis()` 가 점수와 다른 `E` 를 보여주던 것, 균 12 종이
축에서 빠진 것, 문서 수치가 갈린 것, KG 가 같은 statement 를 반복 기록한 것.

테스트는 하나도 없었고 환경변수는 55 개, 최장 함수는 821 줄이다.

### 겨냥해서 만들었다 — 통계적 결론은 검사하지 않는다

`ourkg/check.py`, 10 묶음 23 항목, **네트워크 없이 1.9 초**.

| 검사 | 무엇을 막나 |
|---|---|
| `schema` | 다른 모듈이 이름으로 집어 쓰는 열이 사라지는 것 |
| `microbe` | 질환 관계가 가리키는 균이 축에 없는 것 (§35 의 병합 taxid) |
| `links` | 같은 (균, compound) 를 두 번 세는 것 · 읽는 자리 정규화 누락 |
| `agreement` | 합의/모순 상태와 방향이 어긋나는 것 |
| `registry` | 등록만 하고 디스패치가 없는 쓸기 · 정의 없는 단계 |
| `emode` | 모드가 **같은 E** 를 돌려주는 것 · 모르는 모드의 조용한 통과 |
| `env` | 소스가 읽는 환경변수가 `--env` 에 안 나오는 것 |
| `recommend` | rank/score 정합 · NaN |
| `kg` | 출처 합 ≠ Σ 주장 · 파일에 중복 statement |
| `docs` | README 핵심 수치가 산출물과 다른 것 |

**"신호가 있는가" 는 검사하지 않는다.** 그건 실험이고 이 문서가 기록한다. 검사는
**구조가 스스로 어긋났는가**만 본다.

### 절대 실패하지 않는 검사는 쓸모가 없다 — 깨뜨려서 확인했다

전부 커밋된 상태라 `git checkout` 으로 되돌릴 수 있어, 일부러 고장을 넣었다.

| 넣은 고장 | 잡혔나 |
|---|---|
| `microbes.csv` 에서 `taxid_current` 열 제거 | `schema` FAIL · `links` 가 정규화 누락까지 연쇄 포착 |
| 축에서 균 20 종 제거 | `microbe` FAIL (어느 taxid 인지 출력) · `docs` FAIL |
| `kg_stats` 출처 합 +999 | `kg` FAIL (`3,460,128 != 3,459,129`) |

세 경우 모두 `exit 1`.

### 그 과정에서 구멍 둘이 나왔다

**① 검사가 예외로 죽어서 뒤 검사가 안 돌았다.** 열을 지우자 `AttributeError`
트레이스백으로 멈췄다 — 산출물이 어긋나면 예외가 나는 게 정상인데, 그걸 못
견디면 **검사기가 가장 필요한 순간에 아무것도 말하지 않는다.** 각 검사를 감싸
`FAIL <예외>` 로 보고하고 계속 가게 했다.

**② 환경변수 스캐너가 줄바꿈을 못 잡고 있었다.** `check.py env` 가 `E_MODES` 를
`--env` 목록에서 못 찾는다고 FAIL 했다. 원인은 `run_all.scan_env` 의 정규식이
`os.environ.get('NAME'` 만 보고 있던 것 — `analyze.py` 는

```python
    MODES = os.environ.get(
        'E_MODES', 'shrunk,binary,weighted,...').split(',')
```

처럼 괄호 뒤에서 줄을 바꾼다. 고치니 환경변수가 **48 → 55 개**로 잡혔다.
7 개를 놓친 채 "전수" 라고 적고 있었다.

> 검사기를 만든 첫 실행에서 바로 하나를 찾았다는 것이 이 절의 요점이다.
> 문서에 "환경변수 48 개" 라고 쓰여 있던 것도 그래서 틀린 수였다.

---

## 37. VMH 링크 5.3% 가 쓸 수 없는 식별자였다 (2026-11-25)

`analyze.py pathcheck` 를 돌리다 rdflib 경고를 봤다.

```
https://www.kegg.jp/entry/C00094|C11481 does not look like a valid URI
```

### 한 VMH 대사물이 KEGG 두 개에 매핑될 때 둘을 한 URI 로 붙이고 있었다

`vmh_metabolites.csv` 의 `kegg` 열에 `C00094|C11481` 처럼 파이프로 묶인 값이
있고, 그걸 그대로 `kegg.jp/entry/` 뒤에 붙였다.

| | 수 |
|---|---:|
| VMH 링크 44,094 중 파이프 포함 | **2,323 (5.3%)** |
| 고유 복합 값 | 40 |
| 그 안에 든 고유 KEGG id | **81** |
| 그중 **복합으로만** 존재해 닿지 않던 것 | **80** |
| 숨어 있던 id 중 `E` 에 있는 것 | 30 |
| 숨어 있던 id 중 **`F` 층**에 있는 것 | **8** (`C00047` L-Lysine · `C00806` · `C01536` · `C16434/5` 등) |

두 가지가 동시에 틀렸다. **SPARQL 로 쓸 수 없는 IRI** 2,323 개가 KG 에 있었고,
**F 층 compound 8 개의 미생물 링크가 숨어 있었다.** 미생물 매개 분석에 바로
들어가는 축이다.

### 고치면서 표기도 씻었다

쪼개기 전에 매핑표를 확인했다. 복합 값의 조각 131 개는 전부 `C#####` 로
깨끗했지만, **단일 값 쪽에 66 개가 형식을 벗어났다** —

- `C05450` 뒤에 **non-breaking space**, `C02992 ` 뒤에 공백 (링크에는 닿지
  않지만 매핑표에 남아 있다)
- `D00395`(DRUG) · `G00078`(GLYCAN) — COMPOUND 가 아닌 namespace

D·G 는 **버리지 않았다.** 실재하는 KEGG 항목이고 링크 49 건을 갖고 있다. 다만
`F`·`E` 층은 COMPOUND 전용이라 그쪽과는 조인되지 않는다 — 그래서 넓은 필터
(`[CDG]\d{5}`)를 쓰고 공백·nbsp 를 씻는다. **어느 쪽이 맞는 매핑인지 VMH 가
가리지 않았으므로 복합 값은 둘 다 올린다** — 예측 소스이고 출처 태그로
구분돼 있다.

### 결과

| | 전 | 후 |
|---|---:|---:|
| VMH 링크 | 44,094 | **46,495** |
| VMH compound | 1,069 | **1,109** |
| `F` 층 중 VMH 가 닿는 compound | 29 | **46** |
| `E` 중 VMH 가 닿는 compound | 409 | **438** |
| KG 고유 triple | 3,441,322 | **3,443,484** |
| 깨진 IRI | 2,323 | **0** |

**결론은 바뀌지 않는다.** 미생물 방향 신호는 여전히 BH 보정 후 전부 기각이다 —
`emicrobe` q<0.05 **0/28**(최소 q 0.098) · 자폐 **0/24** · 식이 중재 **0/29**.
§33 의 미리 고정한 예측도 **1/2 그대로**고 고지방식(+0.0418)이 지중해식
(+0.0253)보다 높다. `recommendation.csv` 는 무변동이다.

수치가 조금 움직인 곳은 문서에 반영했다 — §32 합의 쌍 0.598→0.595(q 0.098),
§33 지중해식 +0.0249→+0.0253 · 변형 −0.0042→−0.0020, §34 최소 q 0.282→0.397.

> **이걸 찾은 경로를 적어 둔다.** `check.py` 가 잡은 게 아니다 — `pathcheck`
> 를 손으로 돌리다 **rdflib 경고 한 줄**을 본 것이다. rdflib 는 경고만 하고
> 넘어가므로 사람이 로그를 읽어야 알았다.

### 그래서 검사에 IRI 유효성을 넣었다

`kg` 검사가 IRI 에 공백·꺾쇠·따옴표·파이프 등이 있으면 FAIL 한다. 깨진 IRI 를
일부러 한 줄 끼워 넣어 잡히는 것까지 확인했다.

넣자마자 **오탐 하나**를 만났다 — FoodOn 라벨 `"fat content < 50%, > 35% pufa"`
의 꺾쇠를 잡았다. 리터럴 안의 꺾쇠는 N-Triples 에서 정상이다(`"`·`\`·개행만
escape 가 필요하다). `<...>` 를 긁는 대신 **줄 구조대로**
`<주어> <술어> <목적어>` 를 읽게 고쳤다 — IRI 에는 `>` 가 들어갈 수 없으므로
`[^>]*` 로 끊어 읽으면 된다. 검사 26 항목이 됐다.

---

## 38. CSV 경로와 KG 경로가 어긋나 있었다 — 경고를 아무도 안 받았다 (2026-11-25)

§37 을 고치다 `analyze.py pathcheck` 를 돌렸는데 이렇게 나왔다.

```
CSV  52종 / KG 71종 / 일치 52 / KG 에만 19
⚠ 어긋난다.
```

`out/gutbrain_compounds.json` 은 **11-05 산출물**이었다 — 그 뒤 미생물 축이
162 → 791 종이 됐고 소스가 둘 늘었는데, **경고가 화면에만 찍혀서 20 일간
아무에게도 안 보였다.**

예전 README 에는 "현재 52종으로 정확히 일치한다" 고 적혀 있었다. 그 문장은
README 를 다시 쓸 때(§README 갱신) 경로 절을 접으면서 **이미 빠져 있었다** —
그러니 지금 문서가 틀린 것은 아니다. 다만 **맞는지 틀린지 아무도 모르는
상태**였다는 점은 같다.

### 원인이 둘이었다 — 하나로 짚었다가 틀렸다

처음에 "KG 가 외부 큐레이션으로 넓어졌는데 CSV 필터가 안 따라갔다" 로 짚었다.
확인해 보니 **그것만이 아니었다.**

| CSV 쪽 정의 | 집합 | KG 에만 | CSV 에만 |
|---|---:|---:|---:|
| `compound_microbe(kegg)` × `microbe_disease.is_mental` (현행) | 52 | 19 | 0 |
| 링크를 `kegg+vmh` 로 | 66 | 12 | 7 |
| 링크를 `kegg+vmh+measured` 로 | 75 | 3 | 7 |

어느 쪽도 맞지 않는다. **양쪽이 서로 어긋나고 있었다.**

### KG 질의를 글자대로 따라가니 맞았다

KG 쪽 질의는 이것이다.

```sparql
?m mpq:hasMetabolites ?c ; mpq:hasAssociation ?d .
?d rdfs:subClassOf ent:MentalDisorder .
```

여기서 **두 가지를 분리해야 한다.**

- `hasMetabolites` 는 KEGG 추론(종·속) · VMH/AGORA2 · 측정 상관을 **전부** 올린
  술어다. CSV 는 KEGG 만 보고 있었다.
- `subClassOf MentalDisorder` 는 `microbe_disease.csv` 의 `is_mental`(MeSH F03
  판정) **에만** 붙는다 — Disbiome·gutMDisorder 블록은 중립 `hasAssociation` 만
  올린다. 즉 **"정신질환" 의 정의는 MeSH 쪽**이고, 어느 소스가 그 질환에 균을
  붙였는지는 **별개**다. CSV 는 그 둘을 한 테이블에서 같이 읽어 섞고 있었다.

정의를 맞추니 **78 / 78 · 양쪽 0** 으로 정확히 일치한다. 남아 있던 7 종
(`C00768` · `C00806` · `C01536` · `C16434/5/6` · `C16439`)은 §37 에서 드러난
VMH compound 였고, 캐시된 json 이 새 KG 보다 오래된 것이었다.

### 고친 자리 — 정의를 `common` 한 곳으로

| 함수 | 뜻 |
|---|---|
| `mental_mesh()` | KG 가 `MentalDisorder` 하위로 올리는 MeSH (= `is_mental`) |
| `mental_taxids(mesh)` | 그 MeSH 에 붙은 균, **세 소스 전부** · 정본 taxid |
| `microbe_metabolites()` | `hasMetabolites` 와 같은 범위의 (taxid, kegg) |

`analyze.mental_taxids` 에는 **gutMDisorder 가 빠져 있었다**(나중에 들어온
소스다) 그리고 정본 정규화도 없었다 — `gutbrain_weight` 가 그걸 쓰고 있었다.
`common` 으로 옮기면서 둘 다 고쳤다.

### 그리고 경고를 사람이 안 봐도 되게 했다

이게 이 절의 요점이다. `pathcheck` 가 판정을 `gutbrain_compounds.json` 에
적고(`agree` · `only_csv` · `only_kg`), `check.py` 의 `pathcheck` 검사가
**결론과 신선도** 둘을 본다 — 어긋나면 FAIL, 판정이 `ourkg.nt` 보다 오래되면
FAIL. `pathcheck` 자체는 KG 적재에 76 초라 매번 돌릴 수 없으므로 이렇게 나눈다.
두 고장 모드를 일부러 만들어 FAIL 이 나는 것을 확인했다. 검사 27 항목.

---

## 39. 산출물 출처를 기록한다 — 그걸 따라가다 비결정성을 찾았다 (2026-11-25)

같은 종류로 **세 번** 당했다. 전부 우연히 발견했다.

| 사례 | 어떻게 드러났나 |
|---|---|
| `e_mode_comparison.csv` 가 기본값 아닌 `E_MODES` 로 생성 | 다른 작업 중 diff |
| `toperr_comparison.csv` 가 1 행만 든 부분 실행 결과 | 다른 작업 중 diff |
| 11-05 산출물 9 개가 입력 재구축 뒤 20 일 방치 | mtime 을 훑어봐서 |

마지막 것은 위험이 하나 더 있었다 — 옛 산출물은 `food_key` 표기가 다르다
(`'acerola, , raw'` → `'acerola, raw'`). 지금 산출물과 조인하면 Top/Bot30
60 개 중 **19 개가 조용히 안 맞는다**. 환경변수 55 개 · 단계 24 개에서 기억에
맡길 수 없다.

### 기록은 한 곳에서 — 쓰는 자리 50 곳을 건드리지 않는다

`out/` 에 쓰는 자리가 50 곳이라 하나씩 계측하는 것은 맞지 않다.
`common.enable_provenance()` 가 **프로세스가 끝날 때 이번 실행이 건드린 파일**을
모아 그때의 `argv` 와 **기본값이 아닌 환경변수만** `out/provenance.json` 에
적는다. 기본값은 소스에서 긁는다(`os.environ.get('X', '기본값')`). 단계 스크립트
12 개가 import 때 한 줄로 켠다.

```
recommendation.csv   analyze.py recommend   env={'E_MODE': 'binary'}
```

### 검사는 정본과 쓸기를 갈라야 한다

"비기본값 금지" 로 두면 **쓸기 산출물은 환경을 바꿔 돌리는 것이 목적**이라 검사가
늘 실패한다. 그래서 나눴다.

| | 규칙 |
|---|---|
| **정본 13 개** (`recommendation.csv` · `eval_*` · `kg_stats.csv` …) | 비기본값 환경이면 **FAIL** |
| 쓸기 산출물 (`*_comparison.csv` 등) | 예외 |
| **의존 8 쌍** (`recommendation ← foods · compound_depression · food_form` …) | 산출물이 입력보다 오래되면 **FAIL** |

검사 29 항목이 됐다.

### ★ 넣자마자 비결정성이 나왔다

신선도 검사가 `compound_microbe.csv < microbes.csv` 를 FAIL 했다. 둘은 같은
빌드에서 나오는데 mtime 이 28 분 어긋나 있었다. 쫓아가니 `microbes.csv` ·
`compound_microbe.csv` 는 **내용이 같고** MiKG 산출물 둘만 달랐다. 로그를 모아
보니 **같은 입력 · 같은 코드로 결과가 세 가지로 갈렸다.**

| 실행 수 | MiKG 방향 집계 |
|---:|---|
| 2 | `'' 59 · Promote 12 · Inhibit 1` |
| 1 | `'' 60 · Promote 12` |
| 2 | `'' 61 · Promote 11` |

근거등급도 `B` ↔ `C` 로 흔들렸다. 원인이 둘이다.

1. `_ev[0] if _ev else ''` — rdflib `objects()` 는 **순서 없는** 생성기다. 한
   statement 에 값이 여럿이면 실행마다 다른 것이 뽑힌다.
2. 더 큰 쪽: `set(g.subjects(...))` 순회 + `drop_duplicates(keep='first')` —
   같은 (균, 신경전달물질) 쌍에 statement 가 여럿일 때 **어느 것이 살아남는지**
   가 순회 순서에 달린다.

**정렬해서 돌고, 버리지 말고 모으도록** 고쳤다. 소스에 값이 여럿인 것은 사실
이므로 `B;C` 로 합쳐 적는 것이 하나를 고르는 것보다 정직하다.

| | 전 (임의 선택) | 후 |
|---|---|---|
| 방향 | `Promote 11~12 · Inhibit 0~1` (흔들림) | **`Promote 13 · Inhibit 1`** |
| 등급 | `B 19~23 · C 46~55` (흔들림) | `A 4 · B 19 · C 46` + **`B;C` 3** |

버려지던 `Promote` 2 건 · `Inhibit` 1 건이 돌아왔다. MiKG 블록을 세 번 돌려
**md5 동일**을 확인했다.

### 결론은 바뀌지 않았다

| | 값 |
|---|---|
| `recommendation.csv` | **무변동** |
| `emicrobe` | q<0.05 **0/28** (최소 0.098) |
| 방법 1 | 재현 O14 △4 X2 / 타당 O12 △5 X3 |
| 방법 2 | 11/11 · 2/4 · 0.75 · 논문 일치 12/15 |
| 자폐 · 식이 중재 | 0/24 · 0/29 |
| 미리 고정한 예측 (§33) | 1/2 — 고지방식(+0.0402)이 지중해식(+0.0477/−0.002)과 맞먹는다 |

KG 는 3,443,485 고유 triple (MiKG 7,193 → 7,196).

> **이 절의 요점.** 비결정성은 내가 찾으려던 게 아니다. **출처 기록이 잡아준
> 신호(mtime 불일치)를 따라가다 나왔다.** 세 번 우연에 기댄 뒤에 넣은 장치가
> 넷째를 우연 없이 잡았다.

### 구현 중 같은 유형을 또 만들었다

단계 12 개에 한 줄을 넣으려고 정규식으로 자동 삽입했는데, `import` 가 아니라
**문자열 상수에 인자를 붙여** `probiotic_rct.QUERY` 와
`metabolome_check.BASE_URL` 을 튜플로 만들었다. **문법은 통과하고 뜻만 바뀐**
경우라 `ast.parse` 로는 못 잡고 `import` 에서 터졌다. AST 로 전수 조사해 둘 다
고쳤다 — 이번 세션에 반복된 "실패해도 그럴듯한" 유형이 **내 수정 쪽에서도** 또
나왔다.

---

## 40. `run_all.py` 를 처음 끝까지 돌렸다 — 마지막 단계에서 죽었다 (2026-11-25)

`logs/` 최신이 **11-04** 였다. 그 뒤로 나는 늘 단계별로만 돌렸고 24 단계를
**순서대로 돌린 적이 없었다.** 돌려 보니 23 단계는 통과하고 **마지막 `sweep`
에서 죽었다**(exit 1).

```
ValueError: operands could not be broadcast together with shapes (5916,5) (66,)
sweep.py [] 실패 (exit 1)
```

### 원인 — 쓸기 사이로 환경변수가 샌다

`recommend_under` 가 `os.environ.update(env)` 만 하고 **이전 설정을 지우지
않았다.** 한 프로세스에서 쓸기 15 종을 이어 돌리면 앞 설정이 남는다.

| | |
|---|---|
| `simspace` 쓸기 | `SIM_SPACE=effect` 를 설정 |
| 그다음 `fcolumns` 쓸기 | `PCA_COMPONENTS=5` 를 설정 |
| 충돌 | PCA 로 5 열로 줄인 행렬 × compound 66 개 벡터 → broadcast 실패 |

재현으로 확정했다.

| | 전 | 후 |
|---|---|---|
| `sweep.py fcolumns` (단독) | 정상 | 정상 |
| `sweep.py simspace fcolumns` | **ValueError** | 정상 · **값이 단독 실행과 동일** |

> **단독 실행은 되고 이어 돌리면 깨지는 종류다.** 그래서 단계별로만 돌리는 동안
> 20 일 넘게 보이지 않았다. `check.py` 도 못 잡는다 — 산출물 **정합**은 보지만
> **생성 가능성**은 보지 않는다.

### 고친 것 — 호출 결과가 `env` 로만 정해지게

`recommend_under` 가 설정을 걸기 전에 **프로세스 최초 환경으로 되돌린다**
(`common._ENV_BASE`). 최초 환경으로 되돌리므로 **명령줄에서 준 값은 살고** 앞
쓸기가 남긴 것만 지워진다 — 한 번의 호출 결과가 `env` 와 `boot` 로만 정해진다.

### 완주 확인

| | |
|---|---|
| 단계 | **24/24 통과** (exit 0) |
| 쓸기 | **15/15** |
| 마지막 `check` 단계 | **29/29 통과** |
| 소요 | 약 50 분 (FDC 2,700 만 행 재스트리밍 포함) |

**전체 재빌드가 단계별 실행과 같은 결과를 낸다** — `bootstrap` 현행 전체값
추천군 21 · 비추천군 26 · 위반 0, `emode` 쓸기 전부 동일
(`shrunk` 26/0/8/0/21/24/1/0.462/0.316). 즉 데이터는 건전했고 깨진 것은
**오케스트레이션**이었다.

> 이 절을 포함한 절차상 실수는 [`PROCESS.md`](PROCESS.md) 에 유형별로 모았다 —
> 발견 경로가 **우연 9 · 사용자 지적 3 · 자동 검사 5** 다.

---

## 41. ★★ 합병증 추론 — "−1 정답셋이 필요하다" 가 틀린 진단이었다 (2026-11-25)

논문 §3.3 은 "두 질환이 미생물을 공유하면 합병증 관계" 로 추론한다. 우리가 그
추론에 초기하수 검정을 걸었더니 거의 모든 쌍이 통과했고, 그걸 **"외부 −1
정답셋(Cochrane 'no evidence' 류)이 없어서 판정 못 한다"** 로 적어 뒀다.

**그 진단이 틀렸다.** 세 단계로 틀렸다.

### ① Cochrane 류는 잘못된 도구다

Cochrane 의 "insufficient evidence" 는 **치료 효과**에 근거가 없다는 뜻이고
**동반이환이 없다**는 뜻이 아니다. 증거의 부재를 부재의 증거로 쓰는 셈이다.

### ② 정신질환 안에는 자연적으로 −1 이 없다

덴마크 전국 레지스트리 연구(**590 만 명 · 8,390 만 인년 · 90 쌍 전부**)의 결론이
**"정신질환 사이의 동반이환 위험 증가는 예외가 아니라 규칙"** 이다
([Plana-Ripoll et al., *JAMA Psychiatry* 2019](https://pubmed.ncbi.nlm.nih.gov/30649197/)).
완벽한 정답셋을 구해도 거의 전부 +1 이므로 **라벨이 변하지 않는다** — 어떤
방법도 판별력을 보일 수 없다. 이건 우리 방법의 결함이 아니라 영역의 성질이다.

### ③ 그리고 라벨 없이 답이 나온다 — 집합이 포개져 있었다

`ourkg/complication.py` 가 **검정 전에 입력의 판별력을 먼저 잰다.**

| | mikg (현행) |
|---|---:|
| 질환 | 11 |
| 미생물 universe | **48** |
| `공유 == min(|A|,|B|)` 인 쌍 | **46 / 55 (83.6%)** |
| universe 를 **전부** 가진 질환 | **3** (자폐 · 양극성 · 우울) |
| Jaccard 중앙값 | 0.667 |

세 질환이 universe 전체를 갖고 있으니 겹침은 작은 쪽 크기와 같아지고 "기대보다
많다" 가 **구조적으로 보장**된다. **p 값은 생물학이 아니라 집합 모양의 산물이다.**
외부 라벨이 전혀 필요 없이 설명된다.

원인은 소스다 — MiKG 경로가 미생물 → **신경전달물질 6 종** → 질환이라 모든
질환이 거의 같은 집합을 받는다. 그 병목이 포개짐을 만든다.

### 그래서 순서를 바꿨다 — 못 하는 것을 못 한다고 말한다

특이성을 먼저 재고 포개짐 비율이 임계(`COMP_NEST_MAX=0.30`)를 넘으면 검정을
**돌리지 않는다**. 그럴듯한 p 값을 내는 것보다 낫다.

### ★ 소스를 바꾸면 판별력이 생긴다

| 소스 | 질환 | universe | 쌍 | 포개짐 | Jaccard 중앙 | 검정 | q<0.05 |
|---|---:|---:|---:|---:|---:|---|---:|
| `mikg` | 11 | 48 | 55 | **0.836** | 0.667 | **거부** | — |
| `disbiome` | 22 | 452 | 231 | 0.004 | 0.060 | 수행 | **68 (29.4%)** |
| `gutmdisorder` | 16 | 494 | 120 | 0.017 | 0.025 | 수행 | 11 (9.2%) |
| `curated` (둘 합집합) | 31 | 759 | 465 | 0.009 | 0.041 | 수행 | **129 (27.7%)** |

**게이트가 늘 막는 것이 아니다.** 외부 큐레이션에서는 통과하고, 더 중요하게
**100% 가 아니라 ~28% 만 통과**한다 — 즉 판별이 일어난다. 상위 쌍은 문헌에
확립된 동반이환이다.

| a | b | 공유 | 기대 | q |
|---|---|---:|---:|---:|
| Alzheimer's Disease | Major Depressive Disorder | 38 | 9.5 | 5e-17 |
| Alcoholism | Major Depressive Disorder | 26 | 4.8 | 3e-13 |
| Autism Spectrum Disorder | Child Development Disorders, Pervasive | 32 | 13.7 | 7e-08 |
| Generalized Anxiety Disorder | Major Depressive Disorder | 14 | 2.2 | 2e-07 |
| Anorexia Nervosa | Major Depressive Disorder | 15 | 2.7 | 2e-07 |

> **부수로 버그를 하나 찾았다.** 처음에는 질환을 **이름으로** 묶어서
> `Parkinson Disease`(gutMDisorder) 와 `Parkinson's Disease`(Disbiome) 가
> **서로의 쌍**으로 검정에 올라왔다(q=1.0 — 같은 질환이니 당연하다).
> **MeSH id 로 묶게** 고쳤다: 질환 36 → 31, 쌍 630 → 465, 같은 질환끼리 쌍 0.

> **정정.** 전에 "55/55 통과" 라고 적었다. 현재 표에서 **q<0.05 는 12/55** 다.
> 55/55 는 더 느슨한 기준(공출현 존재)에서 나온 수였다. 결론은 같지만 수치를
> 바로잡는다.

> **산출 코드가 없었다.** `complication_hypergeom.csv` 는 커밋돼 있는데 만든
> 코드가 레포에 없었다(스크래치로 돌린 것이다). 이번에 `complication.py` 로
> 제대로 넣었다 — `run_all.py` 의 `complication` 단계. 거부는 정상 결과이므로
> **exit 0** 이다(파이프라인이 거기서 멈추면 안 된다).

### ★★ −1 정답셋은 **논문 자신이 주고 있었다**

외부에서 구할 것이 아니었다. 논문 Table 5 의 합병증 **8 문항**에 논문이 직접
`+1`(confirmed) / `0`(unknown) 을 붙여 둔다 — **그게 −1 정답셋이다.** 6 개가 +1,
**2 개가 0** 이다(#5 Learning disabilities–depression, #6 Parkinson–autism).

MiKG 경로로는 **8/8 을 통과**시켰다. 즉 논문이 0 으로 둔 둘이 **다 위양성**이었다.
`curated` 로 다시 재면:

| # | 문항 | 논문 | 우리 | 공유 | 기대 | q | |
|---|---|---:|---:|---:|---:|---:|---|
| 0 | Autistic disorder and depression | 1 | 1 | 39 | 18.3 | 1.1e-07 | 일치 |
| 1 | Parkinson disorder and depression | 1 | 1 | 48 | 30.0 | 3.4e-07 | 일치 |
| 2 | Learning disabilities and autism | 1 | — | | | | **못 잼** |
| 3 | Anxiety and depression | 1 | 1 | 14 | 2.2 | 1.5e-07 | 일치 |
| 4 | Bipolar disorder and depression | 1 | 1 | 8 | 1.1 | 6.8e-05 | 일치 |
| 5 | Learning disabilities and depression | 0 | — | | | | **못 잼** |
| 6 | **Parkinson disorder and autism** | **0** | **0** | 143 | **160.8** | **1.00** | **일치** |
| 7 | Alzheimer Disease and autism | 1 | 1 | 83 | 50.7 | 7.5e-08 | 일치 |

**잴 수 있는 6 개가 6/6 일치**한다. 핵심은 **#6** 이다 — 논문이 0 으로 둔 문항이
`q = 1.00` 으로 **올바르게 기각**된다. 공유 143 인데 **기대가 160.8** 이라
기대보다 **적다**. 미생물을 많이 공유한다고 합병증이 되는 것이 아니라는
반례를, 우리 데이터가 스스로 낸다.

**못 재는 2 개는 커버리지 한계다** — `Learning disabilities` 가 Disbiome ·
gutMDisorder 의 정신·신경 집합에 없다. 지어내지 않고 `못 잼` 으로 적는다.

`ourkg/complication.py` 의 `PAPER_PAIRS` · `paper_eval()` 이 이 표를 만든다
(`out/complication_paper_eval.csv`). 시험 셋으로 고정했다 — 문항 수 8 과 음성 2,
잴 수 있는 6 개의 전원 일치, **#6 이 0 으로 기각되는지**.

### 비통과 336 쌍을 문헌으로 점검했다 — 약하게, 그러나 맞는 방향으로

`curated` 로 ~28% 만 통과하니 **우리 데이터 안에서 −1 후보가 생겼다**(336 쌍).
그 후보가 진짜 음성 쪽인지 외부에서 봐야 한다. PubMed 동시언급으로 쟀다 —
원시 건수는 연구량에 끌려가므로 **lift = 관측 동시언급 / 주변분포 기대값**
(`N`=38M)을 쓴다. 465 쌍 중 464 쌍 조회 성공.

| | lift 중앙값 |
|---|---:|
| 통과 129 쌍 | **0.7** |
| 비통과 336 쌍 | **0.5** |

Mann-Whitney (통과 > 비통과): **AUC 0.574 · p 0.0068**.

> **방향은 맞다** — 우리 추론이 통과시킨 쌍이 문헌에서 더 함께 연구된다. 우연이면
> AUC 0.5 다. 그런데 **0.574 는 약하다.** 이 값으로 "336 쌍이 음성이다" 라고
> 말할 수 없고, "우리 통과/비통과가 문헌과 무관하지는 않다" 까지만 말할 수 있다.
>
> 한계가 측정 대상 자체에 있다: **lift 는 동반이환의 크기가 아니라 함께 연구된
> 정도**다. 연구되지 않은 실재 동반이환과 실재하지 않는 비동반이환이 같은 낮은
> lift 로 들어온다. 이 수치를 넘겨 읽지 않는다.

`out/complication_literature_curated.csv` · `complication.py literature`.

### 남은 것

정말 −1 로 쓸 셋은 ② 때문에 **정신 × 신체** 쌍이다 — 레지스트리 연구가
HR ≈ 1 (CI 가 1 포함)로 보고하는 쌍. 지금 `curated` 에 신체질환(뇌졸중 ·
뇌동맥류 · 하수체종양 등)이 섞여 있어 그 쌍을 만들 수 있다. 그건 lift 와 달리
**동반이환의 크기를 직접 재는 값**이라 위 한계를 넘는다.

---

## 42. 한계

- **식품 온톨로지를 넣어도 분류 질문이 풀리지 않는다** (2026-11-09 통합 완료).
  FoodOn·중국 식품 온톨로지를 넣었으나 논문이 요구하는 카테고리 이름("Milk substitutes",
  "Baby Foods")이 두 온톨로지 어디에도 없다. FDC/WWEIA 어휘이기 때문이다.
- **SNOMED CT 는 넣을 실체가 없다** — 배포본에 라벨·계층 없는 id 284 개뿐이다.
  #12(Mood / developmental 상위 분류)는 공개 KG 도 답하지 못한다.
- **미생물-정신질환** — 공개 `Disease_Bacteria` 에서 MeSH F03 으로 걸러지는 관계는
  115건(질환 6종)뿐이고 우울증은 1건이었다. MiKG 406쌍 + **Disbiome 1,193쌍**
  (질환 23종)으로 논문의 1,234 를 넘겼다 ([`DATA.md` §12](DATA.md)).
- **미생물 축을 넓히는 기준을 바꿨다 (2026-11-20)** — 그 전까지 유일한 확장 경로가
  `setup/microbes_added.csv`("평가가 요구하는 균")여서 **이미 아는 균만 늘어나는**
  자기참조였다. 외부 큐레이션(Disbiome)으로 바꿔 162 → **485종**이 됐다.
- **그 다음 벽은 "닿지 않는다" 였고, 그것도 고쳤다** — KEGG organism 코드가 붙은
  것이 167/485 뿐이었다. 원인은 매칭 방식이었다: 못 이은 318 중 **255 가 종이
  아니다**(속 200 · 과 47 · 목 6 · 문 5 · 강 2). 종 → 속 사다리로
  **378/485**, KEGG 링크 4,571 → **10,257**. **다만 그 55%가 속 수준 매칭**이라
  "이 속의 어떤 유전체가" 라는 더 약한 주장이다.
- **그 열을 쓰기만 하고 읽는 곳이 없었다** — 소비처 네 곳이 전부 따로 `read_csv`
  하며 `match_rank` 를 안 봤다. `common.compound_microbe(sources, rank)` 하나로
  합치고 거르는 기준을 거기 뒀다. 커버리지는 **종 수준 182종(38%) · 속 포함
  379종(78%)** 으로 갈라 적는다 — 직전에 78% 만 말한 것을 정정한다. 평가
  어댑터는 `rank='species'` 다(`#6`·`#7` 이 종 이름을 콕 집는다). 걸고 다시 재니
  방법 1 이 바이트 단위로 동일해 필터가 의도대로 동작함을 확인했다. KG 는
  버리지 않고 `KEGG` / `KEGG(속 수준)` 으로 출처를 가른다 (트리플 5,686).
  못 잇는 107종은 과·목·문 수준(60)과 KEGG 에 유전체가 없는 종(47)이다.
- **`#7` 은 균을 늘려도 안 열린다** — *Bifidobacterium longum* 은 이제 KEGG 24 ·
  VMH 546 링크를 갖지만 ascorbate(C00072)가 **양쪽 다 없다**. 외부 데이터의
  한계이지 축 크기의 문제가 아니라는 것이 확인됐다.
- **논문 §3.3 의 474만 추론을 재구현하지 않았다** — 전이 추론과 공통 세균 추론만 쓴다.
- **방법 2 의 자동 판정은 수작업 검색과 같지 않다** — 초록을 읽지 않으므로 논문의
  −1(반대 증거)을 만들지 못하고, 공출현만으로 1 을 준다.

---

## 43. 산출물

| 파일 | 내용 |
|---|---|
| `out/ourkg.nt` | RDF N-Triples 3,459,231 |
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
| `out/recommendation.csv`, `out/recommendation.png` | 추천 순위·시각화 (Fig.4(b) t-SNE) |
| `out/group_composition.csv`, `out/group_comparison.csv`, `out/group_comparison.png` | **Fig.4(c) 대응** — 추천/비추천군 성분군 조성 |
| `out/microbe_disease_disbiome.csv` | **Disbiome** 미생물-질환 (외부 큐레이션) |
| `out/gutbrain_comparison.csv` | **미생물 매개 가중** `ALPHA` 쓸기 (§15c) |
| `out/modimed_rho_comparison.csv` | **빈도 가중 순위 상관** vs Top-K (§13b) |
| `setup/probiotic_rct.csv` | **외부 정답표** — 우울/불안 RCT 에서 시험된 균 25 종 |
| `out/metabolome_check_*.csv` | **측정 분변 대사체** vs 우리 예측 링크 (§15c 검정 ④) |
| `out/compound_microbe_measured.csv` | **측정 상관 링크** 39,574 — 13 코호트 재현 (§15c 검정 ⑤) |
| `out/e_microbe.csv`, `out/e_microbe_compare.csv` | **미생물 경로에서 유도한 E** 와 ProMENDA 대조 (§15c 검정 ⑥) |
| `out/simthr_comparison.csv` | **유사도 희소화** 쓸기 (§15c 검정 ⑦) |
| `out/ezero_comparison.csv` | **에탄올·설탕 제거** 영향 (§15c 검정 ⑧) |
| `out/compound_depression_nhanes.csv` | **NHANES 섭취-결과 E** (§15d) |
| `out/emode_comparison.csv` | E 소스 다섯 비교 (§15d) |
| `out/fscale_comparison.csv` | **서빙 기준 F** x E 소스 (§15e) |
| `out/bootstrap_ci.csv` | **Top-K 지표의 표집 변동** (§17) |
| `out/negw_comparison.csv` | **음수 유사도 가중** 쓸기 (§17b) |
| `out/nosim_comparison.csv` | **유사도 제거** ablation (§17c) |
| `out/simspace_comparison.csv` | **유사도 공간** 성분 vs 효과 (§17d) |
| `out/simsign_comparison.csv` | **나쁜 음식 기여 묶기** x 공간 x E (§17e) |
| `out/complication_hypergeom.csv` | **합병증 추론**의 초기하 검정 (§18) |
| `out/dedup_comparison.csv` | **중복 변종 병합** 두 기준 (§19) |
| `out/learned_comparison.csv` | **지도학습 점수** 직접 사용 (§21) |
| `out/learned_dedup_comparison.csv` | learned x 중복 병합 (§21b) |
| `out/union_comparison.csv` | **두 E 소스 합치기** (§22) |
| `out/consensus_summary.csv`, `out/consensus_*.csv` | **합의 Top-K** (§23) |
| `out/ensemble_comparison.csv` | **순위 앙상블** vs 벡터 합치기 (§25) |
| `out/toperr_comparison.csv` | **Top-K 명백한 오류** 규칙 채점 (§27) |
| `out/eval_method1.csv`, `out/eval_method2.csv`, `out/eval_sparql.json` | §5.1·§4.1 평가 |

`out/` 의 결과표·평가 결과는 레포에 함께 올라가 있다. 대용량 둘만 제외한다 —
`ourkg.nt` (470 MB) 와 `food_compound_long.csv` (48 MB). 둘 다 `python3 ourkg/run_all.py`
로 재생성한다 (`food` 약 12분, `kg` 약 2분).
