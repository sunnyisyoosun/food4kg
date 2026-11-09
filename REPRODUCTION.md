# Food4healthKG 재현 기록

대상 논문: Fu et al., *Food4healthKG: Knowledge graphs for food recommendations
based on gut microbiota and mental health*, Artificial Intelligence In Medicine
145 (2023) 102677.
공식 repo: https://github.com/ccszbd/Food4healthKG (로컬 `Food4healthKG/`)

이 문서는 **무엇을 어디까지 재현했고, 무엇이 검증되지 않았는지**를 기록한다.
조사 과정 전체를 시간순으로 담고 있어 길다.
**현재 막힌 지점만 보려면 [PROBLEMS.md](PROBLEMS.md).**

---

## 1. 핵심 결론

> **대체로 재현됐다 (2026-09-29 갱신, §16).** 두 가지를 논문 산출물에서 역산해
> 고치자 추천 순위가 재현됐다.
> 1. 성분 단위 g 환산 (§16.1) — F 행 코사인 0.295 → 0.981, Top30 5 → 15
> 2. ProMENDA 극성 규약 통일 (§7, §16.6) — Spearman +0.108 → +0.786, Bot30 3 → 15
>
> 남은 격차는 논문 주장 3/6 (논문 순위 자신은 4/6) 과, `weight.csv` 가 없어 확정할 수
> 없는 `E` 다. 순위의 상당 부분은 식물/동물 1비트(+0.695)로도 설명된다.
>
> 이전 판 결론: "재현 실패다. 추천 순위는 우연 수준이다." — 실패의 대부분이
> `E` 의 출처가 아니라 **단위 미환산과 극성 규약 불일치**였다.

### 무엇이 되고 무엇이 안 되는가

| 층위 | 결과 |
|---|---|
| 파이프라인 실행 | ✅ 5단계 end-to-end, 약 9분 |
| 데이터 재구성 | ✅ 85 compound / 135 food / `foodname.csv` (135, 88) / 밀도 28 vs 33 |
| 핵심 입력 `E` 방향 확보 | ⚠️ 69/85 (81%) |
| 논문 명시 부호 일치 (gold 9종) | ✅ 8/9 |
| F (성분 행렬) vs 논문 heatmap | ✅ 행 코사인 0.981 (g 환산 후, §16.1) |
| 논문 §4.2.1 PCA 5성분 | ✅ `Xn⊙E` 80% 도달 5개 |
| **추천 순위** | ✅ **Spearman +0.786, Top30 18/30, Bot30 15/30 (우연 6.7)** |
| 논문 주장 6개 (§16.2) | ⚠️ 3/6 (논문 순위 자신은 4/6) |
| 개선판 V1~V3 (재현 아님, §16.4) | 모두 재현 기준 이하 |
| `weight.csv` 네 소스 | ✅ 독립 집계, 극성 규약 통일 (§7) |
| 논문 §5.1 방법2 (Table 5 추론) | ⚠️ 엄격 기준 Complication 7/8, Diet 2/7 (§16.10). 근거 존재만 보면 11/15 |
| 논문 쿼리 → Table 3 / Table 4 | ✅ 8/8, 5/5 (§16.9, §16.10) |
| 논문 §5.1 방법1 (전문가 20문항) | ⚠️ 공개 KG 로 답 재현 18/20, 재현되고 타당 13/20 (§16.8, §16.10). 전문가 대조 자체는 재현 불가 |

집계: `python3 tools/scorecard.py`

### 왜 실패하는가

논문의 핵심 입력 `E`(compound 의 우울증 완화/악화 방향)가 **어떤 공개 소스에서도
나오지 않는다.** 다섯 경로를 모두 소진했다.

| 시도 | 결과 |
|---|---|
| 공개 KG 의 pos/neg 목록 | 논문이 부호를 명시한 14건 중 13건이 `both` |
| **MENDA 원본 5,675 entries** | 16개 집계 규칙 역산 → 최고 8/12 (§14) |
| ProMENDA 22,519 entries | 12개 구성 전부 더 나쁨 (§12) |
| Supplementary SPARQL Query 2 | ~~pos/neg 구분 없음~~ 정정: 실행된다. 방향 있는 세균 연관은 `MENDA_Depression.jsonld` 에 있다 (§16.9) |
| `metabolite_bacteria.xlsx` | repo git 히스토리에 한 번도 없음 (§14) |

MENDA 원본까지 확보하고도 한계다. **논문의 `E` 는 MENDA 집계가 아니라
논문에 기술되지 않은 별도 큐레이션이다.**

> 이전 판은 "공개 MENDA 에 방향 정보가 없다"고 적었다. **부정확했다.**
> 방향 정보는 있다(§13). 논문이 그것을 쓰지 않았거나 다르게 썼다.

현재 막힌 지점만 따로 보려면 **[PROBLEMS.md](PROBLEMS.md)**.

### 부수 발견 — 순위는 1비트로 설명된다

"식물성이면 추천, 동물성이면 비추천" 한 줄 규칙이 Top30 27/30, Bot30 28/30 을
낸다. compound 를 하나도 보지 않고서다. 논문 순위로부터 역산한 상한(0.687)보다
높다. **85개 compound 모델이 그 위에 더하는 정보가 거의 없다** (§12).

### 방법론에 관한 경고

2026-09-28 까지 이 문서는 "추천 3/3, 비추천 3/4" 를 성과로 보고했다.
그 카테고리 지표는 상위 30개에 과일·채소·어류가 **각각 1개씩만 있어도 만점**이라
실패를 가린다. `Top30 겹침` 과 `Spearman` 으로 보고할 것 (§12).

### 논문 자체의 문제

- §4.2 의 수식 서술(PCA 5성분, 식 (1) 분모, 식 (2))로는 논문이 보고한 결과가
  재현되지 않는다. 저자의 공식 구현(`final.py`)이 실제로 Fig. 4/5 를 만든 코드다 (§3).
- §4.2.1 의 "85개 compound 가 전부 depression 에 연결"이라는 전제가 공개 데이터로
  뒷받침되지 않는다. 15종은 어떤 소스에도 없다 (§10).
- Table 3/4 와 Fig. 4(c) 의 compound 집합이 다르다. Table 3 의 Glutamic acid,
  L-Threonine, Choline 은 85종 목록에 없다 (§4).
- `final.py` 가 읽는 `food.csv`/`foodname.csv`/`weight.csv`/`acs04.csv` 가
  repo 에 없어 공식 코드를 그대로 실행할 수 없다 (§2).

---

## 2. 공식 repo에 없는 것

`final.py`는 다음 파일을 읽지만 repo에 **포함되어 있지 않다**:

- `food.csv`, `foodname.csv`, `weight.csv`, `acs04.csv`

즉 공식 코드는 그대로 실행할 수 없다. 이 저장소의 `reconstruct.py` /
`knowledge_query.py` / `map_promenda.py`는 **없는 입력을 KG에서 역으로 복원**하는
작업이며, 논문 재현이 아니라 재구성이다. 정답 대조가 원리적으로 불가능한
영역이므로 결과 해석 시 이 경계를 분리해야 한다.

---

## 3. 논문 본문 ↔ 공식 코드 불일치

| 항목 | 논문 | `final.py` |
|---|---|---|
| PCA | §4.2.1 "5 principal components를 최종 차원으로 선택" | **점수 경로에 없음** |
| 정규화 | 언급 없음 | 행별 min-max (`normalization`, L378) |
| 열 합 나누기 | 식 (2)에 없음 | `p[i] /= sum(S[:,i])` (L100-101) |
| 4개 소스 | 설명 없음 | `weight.csv` 8행 = 4소스 × (pos,neg) |

### 식 (1)의 분모

논문:

```
S_mn = Σ_{u∈U} (C_um − C̄_m)(C_un − C̄_n) / sqrt( Σ_{u∈U} (C_m − C̄_m)² (C_n − C̄_n)² )
```

코드와 두 군데 다르다.

1. **합의 범위** — 논문은 분모도 `Σ_{u∈U}`(공통 성분)이나, 코드는 분자만
   공통 성분이고 분모는 전체 성분.
2. **곱의 구조** — 논문은 `sqrt( Σ[(..)²(..)²] )`(단일 합), 코드는
   `sqrt( Σ(..)² × Σ(..)² )`(두 합의 곱). **수학적으로 다른 값.**

코드 쪽이 표준 adjusted cosine이고, 논문 수식은 첨자도 일관되지 않다
(분자 `C_um`, 분모 `C_m`). 조판 오류로 보인다.
또한 논문이 인용한 Sarwar et al. [45]의 adjusted cosine은 **user 평균**을
빼지만, 코드는 food 자신의 성분 평균을 뺀다.

### 식 (2)

```
P_{i,j} = Σ_{i=1}^{n} (D_i × S_j)
```

`i`가 좌변 자유 첨자이면서 동시에 합 첨자라 그대로는 계산 불가.
Algorithm 1의 `P = D × S`가 의도이고 코드는 그쪽을 따른다.

### 실증: 어느 쪽이 논문 결과를 재현하는가

`tools/sweep.py formula` — 갈리는 지점 4개를 토글해 16조합을 동일 데이터로 비교.
(벡터화 구현은 공식 스칼라 코드와 최대 오차 `2.4e-15` 로 일치 확인)

논문 순위(p5) 기준으로 재측정한 결과 (2026-09-29):

```
scope   form   colsum feat   Spearman  Top30  Bot30
common  joint  True   X        -0.047    2/30   9/30   <- 최상위
all     joint  True   X        -0.065    4/30   9/30
all     joint  True   pca5     -0.148   14/30   5/30   <- Top30 최다
...
all     split  True   X        -0.303    6/30   1/30   ★공식
...
common  joint  False  pca5     -0.543    0/30   5/30   ☆논문 (16개 중 최하)
```

**논문 수식 조합(☆)이 16개 중 꼴찌다** (Spearman −0.543, Top30 0/30).
공식 코드(★)는 8위권이다.

> 이전 판은 카테고리 지표(`top30_rec`)로 "공식 20점 vs 논문 15점"이라고 적었다.
> 순위 지표로 다시 재면 격차가 훨씬 크다. 다만 **16개 중 어느 것도 양수 Spearman 을
> 내지 못한다** — 수식 선택으로 해결되는 문제가 아니다 (§12).

> ### ⚠ 위 표는 ProMENDA 극성 교정(§16) 이전 값이다 — 2026-11-03 재측정
>
> 극성 규약을 고친 뒤 `python3 tools/sweep.py formula` 를 다시 돌리면 결과가 바뀐다.
> **16개 전부 양수 Spearman** 이고, 논문 수식은 꼴찌가 아니다.
>
> ```
> scope   form   colsum  feat   Spearman  Top30  Bot30
> all     split  False   X        +0.816    18/30   17/30
> all     split  True    X        +0.786    18/30   15/30   ★공식 (2위)
> common  split  False   X        +0.694    15/30   15/30
> all     joint  False   X        +0.673    15/30    7/30
> common  joint  False   X        +0.614    12/30   10/30
> common  joint  False   pca5     +0.602     7/30   22/30   ☆논문 (6위)
> ...
> all     joint  False   pca5     +0.388     9/30   13/30   (최하)
> ```
>
> 따라서 **"논문 수식을 그대로 구현하면 꼴찌" 라는 서술은 더 이상 맞지 않는다.**
> 정확한 서술: 논문 수식은 16개 중 6위(ρ +0.602)이고 공식 구현(+0.786)보다 낮다.
> 특히 Top30 이 7/30 으로 떨어지는 것이 차이의 핵심이다 (Bottom30 은 오히려 22/30).
> 수식 조판 오류 자체(§4.2 의 Eq.1 분모·Eq.2 첨자)는 원문 판독으로 확정되므로 유지한다.

`colsum`(열 합 나누기)은 일관되게 도움이 된다: 켠 8조합의 Spearman 이 모두
끈 조합보다 높다. 이는 공식 `final.py:100` 에만 있고 논문 식 (2)에는 없다.
`pca5`는 Spearman 을 깎지만 Top30 은 올리는 등 엇갈린다.

---

## 4. 85 compound 목록의 출처

`Food4healthKG/analyse/heatmap.xlsx`(Fig. 4(c) 원본 데이터)가 정확히 85열이며
상단 4행이 메타데이터다.

| 행 | 내용 |
|---|---|
| 0 | 원본 compound 인덱스 (0~84, 빠짐없이) |
| 1 | KEGG ID (85개 전부 유니크) |
| 2 | compound 이름 |
| 3 | 6개 biological group (§4.2.3의 "classified into 6 groups") |

그룹 분포: Lipids 39, Amino acid 18, Vitamins and cofactors 11,
Carbohydrates 7, Trace Elements 5, Macronutrient 5.

`build_paper85.py`(step0)가 이를 `analyse/paper85_compounds.csv`로 추출한다.
공식 `final.py:292`의 `np.zeros((85, n))`와 형상이 맞는다.

### KEGG ID alias

논문과 FDC 데이터가 같은 물질에 다른 ID를 쓴다. 매핑 실패가 아니다.

| 논문 | 우리 | FDC nutrient |
|---|---|---|
| C02823 Vitamin B12 | C05776 | `Vitamin B-12` |
| C16522 Eicosatrienoic acid | C03242 | `PUFA 20:3` |
| C08319 alpha-Licanic acid | — | **미해결**, 0으로 채움 |

C08319는 heatmap 원본에서도 138행 중 9행만 non-zero, 최댓값 5.96e-4로 희소.

### 논문 내부 불일치

85개 목록에 **Glutamic acid(C00025), L-Threonine(C00188), Choline(C00114)이
없다.** 셋 다 Table 3의 핵심 compound다. Table 3과 Fig. 4가 서로 다른 집합을
쓴다는 뜻이며, 이 셋은 추천 알고리즘 입력에 들어가지 않는다.

---

## 5. heatmap.xlsx 본문 구조 (조사 결과)

- **138행 = 잡음 3행(0,1,2) + 음식 135개**
- **행별 min-max 정규화** — 135행 전부 최댓값이 정확히 1.0.
  `final.py`의 `normalization()` 출력 그 자체.
- 열 순서는 `orig_idx`가 아니라 **표시 순서**(생물학적 그룹별).
  재정렬하면 `food.csv`와 열이 정확히 일치.

**행 정체는 확정하지 못했다.** `p5_foodname.txt` 순서와 무관(평균 cos 0.17),
헝가리안 1:1 배정으로도 129쌍 중 cos>0.9가 27개뿐(평균 0.32).
공식 `draw_heatmap()`은 Fig. 4(c)가 아니라 4×4 상관 히트맵이므로
**Fig. 4(c)를 만든 코드는 repo에 없다.**

`p5_foodname.txt`는 공식 파일과 md5 동일(`f10915443e4c33af1b6571d0c2ae5d1f`)
이지만, 공식 `final.py`는 이 파일을 **읽지 않는다**(repo 전체 grep 0건).
저자의 보조 메모로 보이며 순위표로 쓸 근거는 없다.

---

## 6. E의 정의 — `FLIP_SIGN` 해소

### 과거의 문제

공식 `score()`는 `infer`/`faecal`/`type1`에서 각 소스 쌍의 **2번째 행**을,
`type2`에서만 1번째 행을 쓴다(`weightneg`/`weightpos`). 즉 공식 `weight.csv`의
행 순서를 알아야 하는데 그 파일이 배포되지 않아 확정이 불가능했다.
어느 행을 pos로 보느냐에 따라 결과가 통째로 뒤집혔다(구 `FLIP_SIGN`).

### 해소

논문 §4.2.1:

> "We create an incidence matrix, denoted as E, in which a value of **1**
> indicates a positive relationship between a compound and depression
> (relieving the disease), and a value of **−1** indicates a negative
> relationship (causing the disease)."

논문의 `E`는 **하나의 행렬에 +1과 −1이 함께** 들어간다. 즉 `E = pos − neg`다.
pos와 neg를 **둘 다** 쓰므로 "어느 행이 pos인가"를 역추론할 필요가 없다.
우리 `weight.csv`의 행 규약은 `reconstruct.py:334-336`에서 우리가 직접 정한다
(짝수 행 = pos, 홀수 행 = neg).

`run_recommendation.py`의 `E_MODE`:

- `'paper'` (기본) — `E = pos − neg`, 논문 §4.2.1
- `'official'` — 단일 행, 공식 `final.py` 재현용

### 부수 효과

공식 방식대로 한 행만 쓰면 **negative 연관이 점수에 전혀 반영되지 않는다**
(`E: +58 / −0`). 나쁜 성분이 많은 음식이 감점되지 않으므로 소시지가 상위에
남는 구조적 원인이 된다. 논문 정의를 쓰면 `E: +57 / −13`으로 음의 기여가 살아난다.

검증 도구: `tools/sweep.py sign`

> 과거에 시도했던 독립 검증 두 경로(heatmap 행 순서, `draw_results()`의 보고
> 수치)는 모두 실패했다(§5, `tools/check_flip.py`). 논문 §4.2.1의 E 정의로
> 우회한 것이지, 공식 `weight.csv`의 행 순서를 알아낸 것은 아니다.

---

## 7. weight.csv 의 4개 소스

`weight.csv` 8행 = 4소스 × (pos, neg). 공식 이름 `infer`/`faecal`/`type1`/`type2`가
ProMENDA(`41398_2024_2948_MOESM3_ESM.xlsx`)에 **문자 그대로 실재**한다.

| 소스 | ProMENDA 컬럼 | 값 | 행 수 |
|---|---|---|---|
| `infer` | (전체) | — | 17,653 |
| `faecal` | `M_Tissue_Metabolite_level_1` | `Faece` | 1,845 |
| `type1` | `M_Study_type_Metabolite_level` | `Type1` | 10,927 |
| `type2` | 〃 | `Type2` | 5,090 |

`map_promenda.py`가 각 소스를 해당 부분집합에서 독립 집계한다.
(이전에는 소스 2~4를 소스 1에 `0.8`/`0.9`/`1.1`을 곱해 만들었다 — 근거 없음)

### Type1~Type5 의 의미 (역추론)

논문은 `type1`/`type2`가 무엇인지 적지 않았다. ProMENDA 의 `M_Groups`
컬럼에서 역추론했다 (`tools/diag.py promenda_types`).

| Type | 대표 비교 | 행 수 | `up` 의 의미 |
|---|---|---|---|
| Type1 | `depression vs control`, `CUMS vs control` | 14,370 | 우울증에서 증가 |
| Type2 | `CUMS + fluoxetine vs CUMS`, `post-ketamine vs baseline` | 6,169 | **치료로 증가** |
| Type3 | `rTMS vs control` (대상 Healthy individuals 100%) | 1,717 | 건강인 대상 개입 |
| Type4 | `responder vs non-responder` (Human 78%) | 239 | 반응자에서 증가 |
| Type5 | `paroxetine responder vs non-responder` | 24 | — |

**Type1 과 Type2 의 `up`/`down` 은 의미가 반대다.** Type1 의 `down` 은
"우울증에서 결핍"이고, Type2 의 `down` 은 "치료로 감소 = 질병에서 높았던 것"이다.
`map_promenda.py` 의 `parse_regulation()` 은 두 경우에 같은 해석을 적용해
전체 집계(`infer`)에서 부호가 섞인다.

### 보정 시도와 결과

`FIX_STUDY_TYPE=1` 로 Type2/Type4 를 반전하고 Type3/Type5 를 제외해 봤다
(5,201행 반전, 1,525행 제외).

```
보정 OFF (기본)  Spearman -0.303  Top30 6/30  Bot30 1/30  gold 7/9  E +42/-13/0=30
보정 ON          Spearman -0.190  Top30 3/30  Bot30 4/30  gold 6/9  E +48/-17/0=20
```

Spearman 과 커버리지는 좋아지나 gold 와 Top30 이 나빠진다. 특히
`C06424 tetradecanoic acid` 가 `-` -> `+` 로 뒤집히는데, 논문 §4.2.3 이
PMID 20524151 과 함께 **소시지의 악화 성분**으로 명시한 것이다.

즉 **논문의 근거 데이터는 보정하지 않은 혼합 집계처럼 거동한다.**
3개 지표 중 2개가 OFF 를 지지하므로 기본값을 OFF 로 두고 토글을 남겼다
(`tools/ab.py study_type`).

### 소스별 논문 순위 대조

평가는 `infer` 하나만 쓴다(공식 `final.py` 도 순위는 p1 으로 낸다).
나머지 소스로도 재보면:

```
           Spearman   Top30   Bot30
infer       -0.303     6/30    1/30
faecal      -0.039     8/30    4/30
type1       -0.250     3/30    3/30
type2       +0.137    12/30   11/30   <- 유일한 양수
faecal+type2 +0.182   12/30   11/30   <- 조합 최고
```

`type2` 만 부호가 반대로 거동하는데, 위에서 본 Type2 의 의미 차이와 일치한다.
다만 **12개 조합 중 최선을 사후에 고르는 것은 순환 논증**이므로 채택하지 않았다.
`tools/sweep.py sources` 로 확인할 수 있다.

### 2026-09-29 — 네 소스가 사실은 복사본이었다

위 표는 **독립 소스가 아니었다.** step2(`knowledge_query.py`)가 infer 의 `E` 를
근거 없는 배율(MENDA 1.0/0.8/0.9/1.1 등)로 네 행에 복사했고, step3 도 같은 표로
네 행을 다시 채웠다. step3 의 ProMENDA 부분집합 집계는 빈 자리만 채웠기 때문에,
네 소스의 부호가 85종 전부 같았다(infer 와 부호가 다른 compound 0개).

고쳤다. step2·3 은 infer 행만 쓰고(`kegg_alias.INFER_SCALE`),
faecal / type1 / type2 는 ProMENDA 의 Faece / Type1 / Type2 부분집합으로
독립 집계한다. **infer 행은 수정 전과 바이트 단위로 같다. 보고 수치는 불변이다.**

독립 집계 후 (g 환산 F, 공식 점수식):

```
                 E 부호          Spearman  Top30  Bot30  gold(E≠0 중)
infer           +50/-17/0=18      +0.108    15      3     8/9
faecal          +8/-14/0=63       +0.517     8      8     2/6
type1           +27/-8/0=50       −0.782     0      0     1/5
type1 (반전)                       +0.782    21     14     4/5
type2           +13/-21/0=51      +0.681    12     15     4/5
```

**극성 불일치가 드러났다.** step2 는 논문 §4.2.1 을 따라 MENDA 의 Up
(hasPositiveAssociation)을 +1 로 둔다(`MENDA_POS_MEANS_RELIEF=1`).
그런데 step3 의 `parse_regulation()` 은 ProMENDA 의 up 을 −1 로 둔다.
두 단계가 서로 반대 규약을 쓴다.

- 논문 규약(Up=+1)을 Type1(우울증 vs 대조군)에 적용하면 type1 반전이 된다.
  gold 4/5, Spearman +0.782 다.
- Type2(치료 vs 질병)는 up 의 의미가 반대이므로, 논문 규약에서는 up=−1 이 된다.
  이는 현재 파싱 그대로이며 gold 4/5, Spearman +0.681 이다.
- 즉 **논문 규약을 Type 의미에 맞게 일관 적용하면 두 소스 모두 독립 기준(gold)과
  논문 순위를 동시에 지지한다.**
- infer 행에도 ProMENDA 로 채운 compound 가 15종 있고, 이들은 반대 규약으로
  들어가 있다.

기본값은 아직 바꾸지 않았다. gold 가 독립 근거이긴 하지만, 소스를 순위로 비교하는
것은 순환 위험이 있어 별도 판단이 필요하다.

**토글로 비교했다** (`PROMENDA_POLARITY=legacy|paper`, `tools/ab.py polarity`).
`paper` 는 Type1 행만 up = +1 로 뒤집는다.

```
                Spearman  Top30  Bot30  gold  claims
legacy (기본)     +0.108    15      3    8/9   1/6
paper            +0.786    18     15    8/9   3/6
```

`paper` 에서 네 소스가 모두 양의 Spearman(+0.68 ~ +0.79)으로 모이고, 소스별 gold 가
faecal 2/6 → 5/6, type1 1/5 → 4/5 로 오른다. 상세는 PROBLEMS §7.

---

## 8. 독립 정답셋

논문에서 **방향이 명시된** compound. 카테고리 결과와 무관하므로 순환 논증 없이
파라미터를 고를 수 있는 유일한 기준이다.

| KEGG | compound | 논문 | 출처 |
|---|---|---|---|
| C06429 | Docosahexaenoic acid | − | Fig.5 PMID 28439746 |
| C06424 | Tetradecanoic acid | − | Fig.5 PMID 20524151 |
| C00031 | D-Glucose | + | Fig.5 PMID 30388595 |
| C00089 | Sucrose | + | Fig.5 PMID 33948112 |
| C01496 | Fructose | + | Fig.5 PMID 33984318 |
| C00037 | Glycine | + | Table 3 #1 Broccoli |
| C00072 | Ascorbic acid | + | Table 3 #3/#4, Table 5 #14 PMID 34293597 |
| C00864 | Pantothenic acid | + | Table 4 #0/#1 Peaches |
| C00253 | Nicotinic acid | + | Table 5 #12 PMID 30709646 |

채택 기준: 논문이 부호 또는 PMID로 방향을 **직접 못박은 것**만.
제외 — 85 목록에 없는 것(C00025, C00188, C00114, C00158, C00097, C00047)과
Table 5 #9 alpha-Tocopherol(Result=0, 방향 없음).

정의는 `tools/gold.py`에 단일 소스로 둔다.

현재 **8/9**. 유일한 실패는 `C06429 DHA`로, 논문은 `−`이나 ProMENDA는
`+`(pos 28 / neg 18)를 지지한다. 논문과 ProMENDA가 충돌하는 사례이며
어느 쪽도 틀렸다고 단정할 수 없어 실패로 남겨둔다.

### 마진 튜닝 결과

step4가 step3의 임의 기본값을 뒤집을 때 요구하는 최소 마진 `|pos-neg|/total`:

```
 margin  gold  top30_rec  bot30_not
   0.00   7/9         16          4
   0.05   8/9         15          4
   0.10   8/9         15          4     <- 채택 (안정 구간)
   0.15   8/9         15          4
   0.20   7/9         15          4
   0.50   7/9         15          4
```

마진 0에서는 Glycine(59:61, 마진 0.016)이 1.6% 차이로 뒤집혀 논문 Table 3과
어긋났다. **gold 기준으로 골랐으므로 카테고리 결과에 대한 순환 논증이 아니다.**
대가로 `top30_rec`이 16 -> 15로 1 감소한다.

튜닝 도구: `tools/ab.py margin`

---

## 8b. 규칙과 미근거 compound 처리 (`tools/ab.py rules|fallback`)

KG 소스(MENDA / ProMENDA / MiKG / ontology / Q2)가 방향을 주지 못하는
compound 를 어떻게 할 것인가. E 는 논문 §4.2.1 정의(`pos − neg`)를 쓴다.

### 2026-09-29 재측정 — 순위 지표로 결론이 바뀌었다

이전 판은 카테고리 지표로 비교해 "gold 가 네 안을 구분하지 못하므로 가장
보수적인 D(fallback 없음)를 택한다"고 적었다. 논문 순위로 다시 재니
**D 가 A 에 모든 지표에서 지배당한다.**

```
                  Spearman   Top30   Bot30   gold   E
A literature       +0.159    10/30    7/30   7/9    +51/-14/0=20
B group_full       -0.029     3/30    1/30   8/9    +46/-23/0=16
C group_carbvit    -0.063     5/30    3/30   8/9    +46/-13/0=26   <- 채택
D none (구 기본값)  -0.303     6/30    1/30   7/9    +42/-13/0=30
```

**C 를 채택했다.** 독립 기준(gold)이 최고(8/9)이고, 수동 입력값이 없으며,
논문 §4.2.3 을 인용할 수 있다. Spearman 도 D 보다 크게 낫다.

**A 가 순위는 가장 좋다** — 유일하게 Spearman 이 양수이고 Top30 이 우연
기대값(6.7)을 넘는 유일한 구성이다. 그러나 출처 불명의 수동값 21개에 의존한다.
`USE_LITERATURE=1 GROUP_PRIOR_MODE=none` 으로 재현할 수 있다.

> 두 선택 모두 근거가 완전하지 않다. C 는 §4.2.3(결과 서술)을 입력으로
> 되돌리는 역순환이고, A 는 논문에 없는 수동값이다. 무엇을 택하든
> **순위는 여전히 우연 수준을 크게 넘지 못한다** (§12).

### ontology 규칙은 유지한다

```
ontology O / literature O   Spearman=+0.159  Top30=10/30  gold=7/9
ontology O / literature X   Spearman=-0.303  Top30= 6/30  gold=7/9
ontology X / literature O   Spearman=-0.039  Top30=11/30  gold=5/9
ontology X / literature X   Spearman=-0.460  Top30= 3/30  gold=5/9
```

`ontology` 를 끄면 gold 가 7/9 -> 5/9 로 떨어진다. subClassOf 체인을 모사한
구조적 추론이고 독립 기준이 지지하므로 유지한다.
sugar 그룹은 수작업 목록 대신 논문 Carbohydrates 그룹에서 유도한다
(부모는 MENDA 에서 방향이 확정되는 유일한 당류 C00089 Sucrose).

### literature 규칙 21개의 성격

부호가 `+1` 10개 / `−1` 1개로 극단적 양성 편향이다. 특히 Trace Elements +
Macronutrient 미네랄 10종이 전부 여기서 왔고 그중 6개가 `+1` 인데, 이는
논문 §4.2.3 의 "nonrecommended foods 가 trace elements 와 macronutrients 가
높다"는 서술과 정면으로 반대다.

### 남은 커버리지

```
MENDA_both 24 | unknown 22 | ontology 13 | MENDA_neg 9
MENDA_pos   6 | MiKG      5 | MENDA_both+Q2 5 | Q2 1
```

`unknown` 22종은 KG 소스 어디에도 없다. 주된 원인은 미네랄 10종으로,
대사체 DB 가 원소를 측정하지 않아 ProMENDA 행이 0이다 (§10).

### KEGG alias 확장 (`kegg_alias.py`)

논문은 입체 비특이적 ID 를, MENDA/ProMENDA 는 L-form 을 쓴다.

| 논문 | MENDA/ProMENDA | ProMENDA 행수 |
|---|---|---|
| C01733 Methionine | C00073 L-Methionine | 87 |
| C16436 Valine | C00183 L-Valine | 116 |
| C16435 Proline | C00148 L-Proline | 115 |
| C02385 Arginine | C00062 L-Arginine | 62 |
| C16434 Isoleucine | C00407 L-Isoleucine | 116 |
| C00716 Serine | C00065 L-Serine | 89 |
| C01401 Alanine | C00041 L-Alanine | 163 |
| C00736 Cysteine | C00097 L-Cysteine | 20 |
| C16433 Aspartate | C00049 L-Aspartic acid | 96 |

이름 정확 대조로 확인했다(부분 문자열 함정: `Alanine` 은 `Phenylalanine` 에,
`Aspart` 는 `N-Acetylaspartate` 에도 걸린다).

---

## 9. 파이프라인과 도구

```
run_pipeline.py
├── step0  build_paper85.py        heatmap.xlsx -> 논문 85 compound 목록
├── step1  reconstruct.py          라벨 병합 -> analyse/food·foodname·weight.csv
├── step2  knowledge_query.py      incidence 결정 (MENDA/Q2/MiKG/ontology)
├── step3  map_promenda.py         ProMENDA 보정 + 4소스 구성
└── step4  run_recommendation.py   추천 (공식 final.py 이식 + 논문 §4.2.1 의 E)

kegg_alias.py   논문 ID <-> FDC / MENDA ID 대응표 (step1~3 공유)

eval/           논문 §5.1 평가 재현
  gold.py             방향 확정 compound 9종 (독립 기준)
  paper_table1.py     전문가 20문항 (Supplementary Table 1)
  paper_table5.py     문헌 검증 15건 (Table 5)
  m1.py               방법 1 질의 20개 + 방법 2 추론 재현

tools/          진단용. 모두 core.py 를 공유
  core.py         로드·정규화·유사도·채점·지표
  scorecard.py    재현 집계 (논문 순위 p5 대조, NDCG@30 포함)
  paper.py        units | claims | invert | improve   (§16)
  ab.py           rules | fallback | menda_both | menda_tiebreak | study_type |
                  merge | margin | units   (끝나면 기본값 복원)
  sweep.py        formula | sign | sources | menda | promenda | ceiling
  diag.py         kg | signs | lipids | unassigned | data | food |
                  menda_jsonld | menda_orig | menda_rule | promenda_types | supplements
  repo_only.py    repo 배포본만으로 돌린 기준선
  unused.py       미사용 파일 분류

setup/          1회성. FDC 원본 교체 시에만
  rebuild_food_nutrient.py  fdc_raw/ -> food_nutrient.csv 재조립
  nutrient_kegg_map.csv     nutrient_id -> KEGG (212행, 180 매핑)
  add_fatty_acid_kegg.py    지방산 KEGG 매핑 생성 (repo 배포본에 없는 77종)
```

### 재현성 (2026-09-29 수정)

같은 입력·설정이면 같은 출력이 나오도록 두 곳을 고쳤다.

**① `kegg_alias.incidence_keys()` 가 `set` 을 반환하고 있었다.**
호출부는 `next(k for k in ks if k in tab)` 로 첫 일치를 고르는데, 파이썬
해시 랜덤화 때문에 문자열 `set` 의 순회 순서가 프로세스마다 달라진다.
별칭이 2개 이상 걸리는 compound 에서 실행마다 다른 값이 선택되어
`weight.csv` 가 두 상태를 오갔다. 순서 있는 `tuple` 로 바꾸고
(논문 ID -> incidence alias -> food alias), 집합 연산을 쓰던 호출부 8곳을
`set(ks) & ...` 로 고쳤다.

**② `map_promenda.py` 가 `weight.csv` 를 제자리 수정했다.**
'비어 있거나 약한 자리만 채운다'는 규칙이라, 설정(`FIX_STUDY_TYPE`, `MARGIN`)을
바꿔 이 스크립트만 다시 돌리면 앞선 실행이 채운 값이 남아 새 설정이 반영되지
않았다(진단 중 실제로 두 번 혼선을 일으켰다). 이제 step3 의
`knowledge_query_results.csv` 를 기준으로 매번 새로 만든다.

검증: 연속 3회 실행에서 `weight.csv` md5 동일.

2026-09-29 기준 `tools/` 는 25개 2,195줄에서 8개 1,100여 줄로 통합했다.
14개 파일이 같은 채점 블록을 복사하고 있어 `core.py` 로 뽑았다.

같은 날 §16 작업 뒤 다시 늘어난 18개를 8개로 통합했다.

| 이전 | 이후 |
|---|---|
| `tools/units.py` `claims.py` `invert_e.py` `improve.py` | `tools/paper.py units` / `claims` / `invert` / `improve` |
| `tools/diag_menda_jsonld.py` | `tools/diag.py menda_jsonld` |
| `tools/diag_menda_orig.py` | `tools/diag.py menda_orig` |
| `tools/diag_menda_rule.py` | `tools/diag.py menda_rule` |
| `tools/diag_promenda_types.py` | `tools/diag.py promenda_types` |
| `tools/read_supplements.py` | `tools/diag.py supplements [검색어]` |
| `tools/tune_margin.py` | `tools/ab.py margin` |
| `eval/paper_ranking.py` | `tools/scorecard.py` |

공통 헬퍼(`one_bit`, `rowminmax`, `cos_matrix`, `gold_of_E`)는 `tools/core.py` 로,
weight.csv 배율 표는 `kegg_alias.INFER_SCALE` 한 곳으로 모았다(이전엔 step2·3 에
복사되어 있었다). 이때 두 가지를 함께 고쳤다.

- `tools/ab.py` 가 끝나도 기본 설정으로 복원하지 않아, 마지막 케이스의
  `weight.csv` 가 남았다. 이제 끝나면 파이프라인을 기본 설정으로 다시 돌린다.
- `tools/scorecard.py` 의 요약이 "Spearman 은 음수다" 같은 고정 문구였다.
  이제 수치에서 만든다.

---

## 10. `unknown` 15개 — 메울 수 없음을 확인한 기록

논문 §4.2.1은 85개 compound가 **전부** depression에 연결되어 있다고 한다.
현재 15개가 `E == 0`이다. 이를 메우려 시도했고, 불가능함을 확인했다.
**같은 길을 다시 파지 않기 위해 조사 과정을 남긴다.**

### 결손의 정체

`unknown`(step3 라벨)은 22개지만, step4(ProMENDA)가 7개를 채우므로
최종 `E == 0`은 **15개**다.

| 그룹 | 개수 | compound |
|---|---|---|
| Macronutrient | 5 | Phosphorus, Sodium, Magnesium, Calcium, Potassium |
| Trace Elements | 5 | Copper, Iron, Zinc, Manganese, Selenium |
| Vitamins and cofactors | 2 | Retinol(C00473), Phylloquinone(C02059) |
| Lipids | 3 | Rumenic(C04056), Heptadecenoic(C16536), alpha-Licanic(C08319) |

step4가 채운 7개(참고): C16513, C08320, C16537, C16527, C06426, C08322, C16522.

### 시도 1 — VMH / gutMDisorder: 대상이 아님

VMH[31]와 gutMDisorder[32]는 **논문의 데이터 소스가 아니다.**
§2 관련연구에서 "지속적 갱신과 자동 완성이 없다"는 비판 대상으로만 언급되며,
§3.1의 통합 목록(FDC, FoodOn, Chinese Food Ontology, KEGG, NCBI taxonomy,
MENDA, MiKG, SNOMED CT, MeSH)에 없다. 끌어오면 재현이 아니라 논문 확장이 된다.

### 시도 2 — 로컬 KG 전수 조사: 미네랄 0건

15개를 `foodkg_triply/` 전 파일과 MiKG에서 검색했다.

| 파일 | 미네랄 히트 |
|---|---|
| `MENDA_Depression.jsonld` | **0** |
| `KEGG_Compound_Bacteria.jsonld` | **0** |
| `KEGG_Compound.jsonld` | **0** |
| `MiKG_Schema_Data.ttl` | 1 (오탐) |
| `Food_Nutrient.trig` | 10 — 음식 쪽 **함량**일 뿐, depression 방향 아님 |

`MESH_Disease.jsonld`와 `Bacteria_Ontology.trig`의 히트는 검증 결과 전부 오탐
(MeSH tree number 등과의 부분 문자열 충돌).

**미네랄은 depression 연관도, 세균 대사 경로도, 화합물 온톨로지 소속도 없다.**
대사체 데이터베이스가 원소를 측정하지 않기 때문이며, 논문 저자도 같은 제약을
받았을 구조적 한계다.

### 시도 3 — KEGG BRITE 계층 전파: 최대 2개

`KEGG_Compound.jsonld`에 KEGG BRITE 화합물 분류(`br08001Class*`,
`br08002Class*`, compound 5,640개)가 들어 있다. 논문 §3.3이 명시한 추론이다:

> "saturated and unsaturated fatty acids are subclasses of fatty acids and
> fatty acids are a subclass of lipids, we can logically **infer** that
> instances of saturated fatty acids also belong to the classes of fatty acids
> and lipids"

같은 BRITE 클래스의 형제 compound에서 ProMENDA 방향을 다수결 전파했다
(마진 0.10, 좁은 클래스 우선):

```
C04056 Rumenic       br08002Class4    형제 28, 근거 14  pos=196 neg=117  margin=0.252  -> +1
C00473 Retinol       br08002Class292  형제 19, 근거  6  pos=  8 neg=  6  margin=0.143  -> +1 (br08001Class61과 충돌)
C16536 Heptadecenoic br08002Class3    margin=0.034  미달
C08319 alpha-Licanic br08002Class8    margin=0.000  미달
C02059 Phylloquinone br08002Class296  근거 0건       불가
미네랄 10종          BRITE 클래스 없음              불가
```

**15개 중 최대 2개.** 채택하지 않았다.

### 시도 4 — BRITE로 수작업 `ontology_rules` 대체: 역효과

부수 효과로 기대했으나 검증 결과 나빴다.

```
BRITE 커버 3/13, 부호 일치 1/3
  C00208 Maltose  수작업=+1  BRITE=-1  (br08001Class33: pos=9,  neg=16)
  C00243 Lactose  수작업=+1  BRITE=-1  (br08001Class33: pos=10, neg=18)
  C05443 Vit.D3   수작업=+1  BRITE=+1
```

당(sugar) 클래스 `br08001Class33`의 형제 다수결이 `−`로 나오는데, 이는
논문 Fig. 5가 D-Glucose(C00031) / Sucrose(C00089) / Fructose(C01496)를
**모두 `+`**로 명시한 것과 반대다. BRITE 클래스가 너무 넓어 전파가 부정확하다.
채택하지 않았다.

### 결론

> **논문 §4.2.1의 "85개 compound가 전부 depression에 연결되어 있다"는 진술은
> 공개된 데이터로 뒷받침되지 않는다.** 저자가 미네랄 10종의 방향을 어디서
> 얻었는지는 논문 어디에도 기술이 없다.

이는 재현 코드의 결함이 아니라 **논문의 재현 불가능 지점**이며, 재현 연구의
결과로 보고할 사항이다. `unknown` 15개는 `E = 0`으로 두는 것이 정직하다.

조사 스크립트는 일회성이라 보존하지 않았다. 재조사가 필요하면 이 절의
파일 목록과 BRITE 파싱 방식을 참고하면 된다.

---

## 11. 데이터 밀도 — 잘린 입력과 라벨 병합

### 증상

85개 compound 중 값이 있는 개수가 논문 원본(`heatmap.xlsx`)보다 크게 낮았고,
순위가 성분이 아니라 **데이터 밀도**에 지배되었다.

```
Beef    측정 18개  -> 순위 23~25
Beef    측정 49~57 -> 순위 78~92
Sausage 측정 17~24 -> 순위 21~34
Sausage 측정 47,62 -> 순위 83,115
```

### 원인 1 — 입력 파일이 Excel로 잘려 있었다

```
행 수        1,048,575   ← 정확히 Excel 행 한계 (2^20 − 1)
id 결번      11,006,343개,  id 비단조
fdc_id 최대  1,105,897   (실제 FDC는 270만대)
```

FDC Full Download(April 2026)의 실제 `food_nutrient.csv`는 **27,195,014행**으로
26배다. `rebuild_food_nutrient.py`로 재조립했다
(`food.csv` + `food_nutrient.csv` + `nutrient.csv` 조인 + `nutrient_kegg_map.csv` 적용).

**★ 받은 CSV를 Excel로 열지 말 것.** 경고 없이 같은 자리에서 잘린다.

효과: 음식 매칭 132/135 -> **135/135**, 비추천 카테고리 2/4 -> 3/4.
그러나 **밀도는 오히려 내려갔다**(중앙값 18.5 -> 15.0). 접두사형 항목의
커버리지가 전혀 변하지 않았기 때문이다. 절단은 밀도 격차의 원인이 아니었다.

### 원인 2 — 라벨 병합을 하지 않았다 (진짜 원인)

논문 §3.2:

> "The preprocessing steps involve **splitting the food labels by commas and
> removing unnecessary words** that may follow the first comma... Next,
> **exact matching is employed to merge foods with identical labels.**"

FDC Foundation Foods는 같은 음식을 **영양소군별로 따로 등재**한다:

```
Niacin,      American cheese, pasteurized process, KRAFT - NFY090HJK   (85중  1종)
Fatty Acids, American cheese, pasteurized process, KRAFT - NFY090HKC   (85중 25종)
Choline,     American cheese, pasteurized process, KRAFT - NFY090HJS
...                                                        총 21개 항목
```

접두사(`Fatty Acids,` `Niacin,` `Tocopherols,` …) / 샘플코드(`- NFY090HJK`) /
지역표기(`(CT,NC)`)를 제거하면 라벨이 같아진다. 병합 결과:

| 음식 | 항목 수 | 단일 최대 | 병합 후 |
|---|---|---|---|
| American cheese, KRAFT | 21 | 1 | **59** |
| Whole wheat bread, NATURES OWN | 27 | 8 | **53** |
| Cottage cheese 2%, BREAKSTONE | 24 | 25 | **47** |
| Tamale, Pork | 53 | 1 | **79** |

`reconstruct.py`의 `normalize_label()`이 이를 수행하고, 병합은 compound별
**평균**(`aggfunc='mean'`)으로 집계한다.

### 결과

| 85 중 측정 compound 수 | 논문 (135) | 개선 전 | 현재 (135) |
|---|---|---|---|
| 중앙값 | 33.0 | 15.0 | **28.0** |
| 평균 | 34.1 | — | **28.6** |
| 최대 | 73.0 | — | **73.0** |
| 5개 이하 | 2 | 35 | 14 |
| 매칭된 음식 | 135 | 132 | **135** |

`foodname.csv`가 **(135, 88)** 로 논문과 정확히 일치한다.

### 매칭 선택 규칙

후보 중 **첫 번째**를 집던 것을, 이름 유사도를 먼저 보고 동급(허용오차 0.08)
안에서 **커버리지가 가장 큰** 후보를 고르도록 바꿨다.
`manual_map`의 부분 문자열이 단어 경계를 넘던 버그도 수정
(`"rice flour, rice starch" ⊃ "flour, rice"`) — 앞부분 일치를 우선한다.

되돌린 시도:
- **커버리지만으로 선택**: 밀도는 올랐으나 `Ham -> Fast foods, hamburger`,
  `Chicken, dark meat -> Energy drink RED BULL` 등 오매칭 41건. 철회.
- **포함도 0.5 미만 거부**: 정당한 매칭 16개를 버리면서 정작 틀린
  `FLOUR, RICE -> Rolls, gluten-free`(0.50)는 통과. 비활성(`MIN_CONTAINMENT = 0.0`).

### 남은 격차

중앙값 28.0 vs 논문 33.0. 논문은 2021~2022년 FDC 스냅샷을, 우리는 2026-04판을
쓰므로 Foundation Foods의 샘플 단위 항목이 개정된 영향으로 보인다.
`Sweets`는 후보가 2개(Sugars, granulated)뿐이라 하위 30 진입이 사실상 우연이다.

---

## 12. ★ 평가 지표를 바꾼 뒤 드러난 것

### 카테고리 지표가 실패를 가리고 있었다

2026-09-28 까지 이 문서는 "추천 3/3, 비추천 3/4" 를 성과로 보고했다.
그 지표는 **상위 30개에 과일·채소·어류가 각각 1개씩만 있어도 만점**이다.
논문이 추천한 오렌지 대신 우리가 키위를 올려도 통과한다.

### p5_foodname.txt 는 논문의 순위표다

`analyse/p5_foodname.txt`(공식 repo 파일)의 줄 순서가 논문의 추천 순위다.

1. 내용이 정렬되어 있다. 앞 30줄은 양파/멜론/자몽/바나나/케일/복숭아/딸기/사과,
   뒤 30줄은 소고기/소시지/닭고기다.
2. 논문 Fig. 4(c) 원본(`heatmap.xlsx`)의 행 순서와 **Spearman 0.896** 으로 일치한다
   (신뢰 매칭 31쌍, 프로파일 코사인 > 0.95).

> 이전 판에서 "공식 `final.py` 가 p5 를 읽지 않으므로 순위로 볼 근거가 없다"고
> 적었던 것은 **철회한다**. heatmap 대조가 독립적 뒷받침이 된다.
> 초기 대조가 실패했던 것은 당시 데이터가 잘려 있고 라벨 병합도 없었기 때문이다
> (평균 코사인 0.32 -> 0.899 로 개선된 뒤에야 매칭이 성립했다).

### 순위로 재면 우연 수준이다

```
Spearman        -0.071        음수 = 역행
Top30 겹침        5 / 30        우연 기대값 6.7
Bottom30 겹침     4 / 30        우연 기대값 6.7
```

134개 중 30개를 무작위로 뽑아도 평균 6.7개가 겹친다.
**추천 순위는 재현되지 않았다.**

### 층위별 재현율 (`tools/scorecard.py`)

| 층위 | 값 |
|---|---|
| 데이터 재구성 (85 compound / 135 food / (135,88) / 밀도 28-33) | ~90% |
| 핵심 입력 E 방향 확보 | 67/85 (79%) |
| 논문 명시 부호 일치 | 8/9 (89%) |
| **추천 순위** | **0% (우연 수준)** |
| 논문 §5.1 방법2 (Table 5 추론) | 11/15 (73%) |

### 식물/동물 1비트 기준선이 순위를 거의 설명한다

`tools/sweep.py ceiling`:

```
                          Spearman   Top30    Bot30
현재                        -0.303    6/30     1/30
그룹부호 (지질/아미노=-1)     +0.576   15/30    17/30
ref부호 (상한, 순환 논증)     +0.687   22/30    17/30
동물성 기준선 (비교용)        +0.695   27/30    28/30
```

**"식물성이면 추천, 동물성이면 비추천" 한 줄 규칙이 Top30 27/30, Bot30 28/30 을 낸다.**
compound 를 하나도 보지 않고서다. 논문 순위로부터 역산한 상한(0.687)보다도 높다.

즉 논문의 추천 순위는 사실상 식물/동물 이분법이고, 85개 compound 모델이
그 위에 더하는 정보가 거의 없다. `E` 를 더 정교하게 복원해도 상한이
1비트 기준선에 못 미친다.

### 왜 E 를 복원할 수 없는가

`tools/diag.py kg`:

```
MENDA: hasPositiveAssociation 378종 / hasNegativeAssociation 399종 / 양쪽 267종
논문이 부호를 명시한 14건 중 13건이 both -> 판정 가능한 것은 Sucrose 하나뿐
```

공개된 `MENDA_Depression.jsonld` 는 Depression(mesh D003865) -> compound 목록
두 개뿐이고 스터디 단위 근거가 없다. **논문의 핵심 입력이 공개 자료에 남아
있지 않다.** 대체재인 ProMENDA 는 12개 구성 전부 더 나빴다
(`tools/sweep.py promenda`, Spearman 최대 -0.25, gold 0~3/9).

---

## 13. MENDA 원본 확보 — 극성 교정과 `E` 출처 규명

2026-09-29, MENDA 원본(`menda.xlsx`, Briefings in Bioinformatics 보충자료)을
확보했다. `Metabolite` 시트 **5,675 entries / 464 studies** 로 논문 §3.1 이
인용한 "5,675 associations" 와 정확히 일치한다.

### ★ 극성을 반대로 읽고 있었다

KG 의 목록과 MENDA 원본을 대조하면:

```
up -> pos / down -> neg    pos 일치 371/378 (Jaccard 0.981)
                           neg 일치 392/399 (Jaccard 0.982)

down -> pos / up -> neg    Jaccard 0.528 / 0.531   <- 우리가 쓰던 해석
```

**KG 의 `hasPositiveAssociation` 목록 = MENDA 의 'Up'(우울증에서 증가) 대사체다.**
즉 `positive association` 은 §4.2.1 이 말하는 "relieving" 이 아니라 역학의
통상 의미인 **"질병과 양의 상관"** 이다.

Supplementary Query 2 가 `?depression npq:hasNegativeAssociation ?compound` 로
compound 를 뽑는 것도 이것으로 설명된다 — **우울증에서 감소한 = 결핍된 =
보충할 가치가 있는** 성분을 고르는 것이다.

### 그런데 논문 자신이 이 반전을 범했다 — 재현에는 논문을 따른다

§4.2.1:

> "a value of **1** indicates a **positive relationship** between a compound
> and depression **(relieving the disease)**"

논문은 `positive relationship` 을 "relieving" 과 동일시한다. 그런데 그들의
`hasPositiveAssociation` 목록은 MENDA 의 'Up'(우울증에서 증가)이다.
**프로즈는 "완화"라 쓰고 데이터는 "질병에서 증가"를 담았다.**
Fig. 5 가 D-Glucose / Sucrose / Fructose(전부 MENDA 'Up')를 추천 식품의
성분으로 놓은 것도 이것으로 설명된다.

재현이 목적이므로 **논문의 코드 경로를 따른다**. 지표도 그렇게 말한다.

```
                      gold   Spearman
논문대로 (기본값)       8/9    -0.063
과학적으로 옳은 극성     7/9    -0.155
```

`MENDA_POS_MEANS_RELIEF=0` 으로 과학적 극성을 쓸 수 있다.

> §12 에 "공개 MENDA 에 방향 정보가 없다" 고 적었던 것은 **부정확했다.**
> 방향 정보는 있었다. 다만 논문이 그것을 반대 의미로 사용했다.

### 그러나 논문의 `E` 는 MENDA 에서 나오지 않았다

MENDA 원본을 주 근거로 E 를 만들어 봤다 (`tools/sweep.py menda`).

```
                       Spearman   Top30   Bot30
MENDA원본 margin=0.00   -0.016     4/30   15/30
MENDA원본 margin=0.10   -0.333     0/30    9/30
MENDA원본 + KG 목록     -0.332     0/30    9/30
MENDA원본 + ProMENDA    -0.407     0/30    6/30
현재 파이프라인          -0.155     3/30    2/30
```

**Top30 겹침이 0/30.** 보조 소스를 더해도 나아지지 않는다.

gold 9종을 MENDA 원본과 직접 대조하면 4/8 이다:

```
C00089 Sucrose         논문=+   MENDA  0 down : 7 up  (마진 1.00) -> -   X
C00253 Nicotinic acid  논문=+   MENDA  1 down : 8 up  (마진 0.78) -> -   X
C00072 Ascorbic acid   논문=+   MENDA  5 down : 6 up  (마진 0.09) -> -   X
C01496 Fructose        논문=+   MENDA 원본 498종에 아예 없음              X
```

Sucrose 는 7개 연구 전부가 `up` 인데 논문 Fig. 5 는 `+` 로 명시한다.
Fructose 는 MENDA 에 없는데 PMID(33984318)까지 달려 있다.

**결론: 논문은 MENDA 를 KG 로 옮기되(Jaccard 0.98), 추천 알고리즘의 `E` 는
별도로 만들었다.** `preprocess/data_cleaning.py` 가 읽는
`metabolite_bacteria.xlsx` 가 그 출처로 보이는데 repo 에 없다 (§14).

### 저자가 배포한 `food_nutrient.csv` 도 이미 잘려 있었다

공식 repo 의 git 히스토리에서 `food_nutrient.csv.zip` 블롭을 꺼내 보니:

```
1,048,576줄 = 정확히 Excel 행 한계
고유 compound 88종, 고유 food 80,305, id 비단조 (1,283,674 ~ 13,338,591)
날짜 2022-01-20
```

§11 에서 "입력 파일이 Excel 로 잘려 있었다" 고 적은 것은 맞지만,
**자른 주체는 논문 저자다.** 우리가 받은 파일이 그대로였다.
논문이 보고한 밀도(중앙값 33)는 이 배포 파일로는 나올 수 없다.

### README 가 확인해 준 것

공식 repo README:

> `p5_foodname.txt: The results of food names`

**p5 가 결과물(순위)이라는 §12 의 추론이 공식 문서로 확인됐다.**

---

## 13b. Fig. 5 의 피라미드 — 평가 기준을 고쳤다

논문을 처음부터 다시 읽으며 찾았다. Fig. 5 는 식품을 **3층**으로 나눈다.

```
상단 (No-recommended)  Baked Products / Beef Products /
                       Sausages and Luncheon Meats / Pork Products
중간 (general)         Dairy and Egg / Finfish and Shellfish /
                       Soups, Sauces, and Gravies / Fats and Oils
하단 (Recommended)     Vegetables and Vegetable Products /
                       Fruits and Fruit Juices
```

**어류는 추천이 아니라 중간층이다.** 그런데 §4.2.3 본문은

> "the recommended foods are mainly **fish and shellfish products**, as well as
> fruits and vegetables"

라고 적어 Fig. 5 와 모순된다. Fig. 5 는 알고리즘 출력에서 직접 그린 그림이므로
그쪽을 기준으로 삼았다.

이전 판은 본문만 보고 다음을 썼다.

```
추천  = {Fruits, Vegetables, Fish}        -> {Fruits, Vegetables}
비추천 = {Sausages, Baked, Sweets, Beef}  -> {Baked, Beef, Sausages, Pork}
```

`Sweets` 가 아니라 `Pork` 다. 수정 후 카테고리 지표는 **추천 2/2, 비추천 4/4**,
`bot30_not` 은 2 -> 10 으로 올랐다. 순위 지표(Spearman −0.071, Top30 5/30)는
카테고리 정의와 무관하므로 변하지 않는다.

`tools/core.py` 의 `PAPER_REC` / `PAPER_NOT` 에 근거와 함께 반영했다.

> 2026-10-01 추가: 상단 층도 본문과 그림이 다르다. 본문은 "barbecue products", 그림은
> "Baked Products" 이고, 논문 순위는 본문 쪽이다. 기준은 그림으로 두고 본문 기준을
> 민감도 검사로 함께 본다 (§16.7).

---

## 14. `E` 의 출처 — MENDA 집계 규칙 역산과 `metabolite_bacteria.xlsx`

### MENDA 집계로는 논문 부호가 나오지 않는다

KG 목록은 `both` 가 267/498(70%)이라 방향이 모호하다. 논문이 Table 3/4/Fig. 5
에서 부호를 명시했으니, MENDA 원본의 study 단위 데이터에 어떤 집계 규칙을
적용해야 그 부호가 나오는지 16개 규칙을 역산했다 (`tools/diag.py menda_rule`).

```
규칙                       일치    판정가능
any-up -> +1 [전체]        8/12       12     <- 최고
표본수 가중 [전체]           7/12       12
최대 표본 연구 [전체]         7/10       10
다수결 [Type1]             6/12       12
다수결 [Human]             6/11       11
다수결 [전체]                5/12       12
...
다수결 [Faece]             1/2         2
```

**최고가 8/12.** 조직·생물종·연구유형·표본수·연도 어느 축으로 잘라도
논문 부호를 재현하지 못한다.

최고인 `any-up -> +1` 은 "한 연구라도 up 이면 +1" 이므로 사실상
`hasPositiveAssociation` 목록 그대로다(both 면 +1). 즉 우리가 이미
`MENDA_both→pos` 로 쓰던 규칙이다. 실제로 적용하면:

```
                gold   Spearman   Top30
MENDA_both -> +1  8/9   -0.146     3/30
MENDA_both -> 0   8/9   -0.063     5/30
```

gold 는 같고 순위는 현재가 낫다. 기본값을 유지한다.

> **결론: 논문의 `E` 는 MENDA 집계가 아니다.** MENDA 원본을 확보하고
> 16개 규칙을 시험했는데도 12종 중 8종이 한계다.

### `metabolite_bacteria.xlsx` 의 역할 재평가

`Food4healthKG/preprocess/data_cleaning.py` 의 `metabolite_bacteria_cleaning()`
이 읽는 파일이다. 시트 `NutrientRequirementReferences`, 5행이 헤더,
2~55열이 행렬이고 `if row_temp == -1` 인 셀만 뽑아 PMID 와 저장한다.

처음에는 이것이 `E` 의 출처라고 보았으나, 출력 형식을 다시 보면
`(metabolite, bacteria, pmids)` 쌍이다. 즉 **compound x 세균 관계**이고,
우리 KG 의 `KEGG_Compound_Bacteria.jsonld`(`hasMetabolites` 201건)에 해당한다.
Table 1 도 metabolite-bacteria 를 KEGG 에서 가져왔다고 적는다.

**따라서 `E` 의 직접 출처가 아닐 가능성이 크다.** `-1` 은 방향이 아니라
관계의 존재 표시로 보인다.

그렇다면 `E` 는 어디서 왔는가 — MENDA 도 아니고(위) 이 파일도 아니라면,
논문에 기술되지 않은 별도 큐레이션이라는 뜻이다. 이는 §12 의 결론을
약화시키지 않고 오히려 강화한다.

### 그래도 찾는다면

repo git 히스토리 전수 확인 결과 한 번도 커밋된 적이 없다.

```
git log --all --pretty=format: --name-only | sort -u
-> analyse/{figure.png, final.py, heatmap.xlsx, heat_result.png, p5_foodname.txt}
   foodkg_triply.zip, food_nutrient.csv.zip
   preprocess/{data_cleaning.py, spy_kegg.py}
   README.md, Supplements.docx
```

1. **저자 요청** — 교신저자 Xingpeng Jiang `xpjiang@mail.ccnu.edu.cn`,
   repo 소유자 GitHub `ccszbd`. 요청 목록:
   `final.py` 가 읽는 `food.csv` / `foodname.csv` / `weight.csv`(가장 중요),
   `metabolite_bacteria.xlsx`, `bacteria_metabolism_compound.xlsx`.
   **`weight.csv` 하나면 `E` 문제가 전부 해결된다.**
2. 선행 논문 보충자료 — Fu et al. 2020 ICHIS [37], Liu et al. 2021 MiKG [36]
3. MiKG 원본 배포처 — 로컬 `MiKG-JAIMS/` 가 부분 사본일 수 있다

---

## 14b. git 블롭 조사 — 누락 파일 복원과 FDC 카테고리

2026-09-29, 공식 repo 의 git 히스토리를 블롭 단위로 뒤졌다.

### `Food_Ontology.jsonld` 가 우리 사본에서 빠져 있었다

`foodkg_triply.zip`(블롭 `4f799b6`, 24MB)을 꺼내 내용을 비교하니:

```
repo zip   12개 파일
로컬 사본   11개 파일
-> Food_Ontology.jsonld (9.5MB) 누락
```

FoodOn 이다 — 노드 12,913, `subClassOf` 8,314, `hasSynonym` 3,504,
`hasDbXref` 5,531. 복원해 `foodkg_triply/` 에 넣었다.

### 저자가 배포한 `food_nutrient.csv` 도 확인

`food_nutrient.csv.zip`(블롭 `3d6b615`, 10.6MB)을 꺼내니
**1,048,576줄 = 정확히 Excel 행 한계**, 날짜 2022-01-20,
고유 compound 88종 / food 80,305 / id 비단조.

§11 에서 "입력이 Excel 로 잘렸다"고 한 것은 맞지만 **자른 주체는 저자다.**
논문이 보고한 밀도(중앙값 33)는 이 배포 파일로 나올 수 없다.

### zip 내용 전수 검증

`foodkg_triply.zip` 의 12개 파일을 CRC 로 로컬 사본과 대조했다.
**전부 일치**한다. 복원한 `Food_Ontology.jsonld` 포함.

### ★ repo 가 배포한 `food_nutrient.csv` 는 논문 85종을 담지 못한다

블롭에서 꺼낸 파일의 KEGG 매핑을 논문 85종과 대조하면:

```
repo food_nutrient.csv 고유 KEGG   88종
논문 85종
교집합                            57종
```

**논문에만 있는 28종이 거의 전부 지방산이다:**

```
Arachidonic, Hexadecanoic, Oleic(2종), Octadecanoic, Decanoic, Caproic,
Butanoic, Dodecanoic, Tetradecanoic, Icosanoic, gamma-Linolecic,
alpha-Linolenic, Docosahexaenoic, Docosanoic, alpha-Licanic, Tetracosanoic,
Myristoleic, Nervonic, Palmitoleic, Docosapentaenoic, Eicosatrienoic,
Icosenoic, Docosatetraenoic, Heptadecenoic, Pentadecanoic, Rumenic,
Vitamin B12 ...
```

지방산 **데이터 자체는 파일에 있다**. 매핑이 없을 뿐이다:

```
repo 파일 고유 nutrient_name 211종
  KEGG 매핑됨  104
  미매핑       107  (그중 SFA/PUFA/MUFA/TFA 77종)
```

`setup/add_fatty_acid_kegg.py`(구 step1)가 바로 이 매핑을 채우던 스크립트다.
그 결과가 `setup/nutrient_kegg_map.csv`(212행, 180 매핑)에 보존되어 있어
지금 파이프라인이 85종을 다룰 수 있다.

> 즉 **repo 데이터만으로는 논문 85종 중 57종밖에 다루지 못한다.**
> 나머지 28종(지방산)은 KEGG 매핑을 직접 만들어야 한다.
> §14b 의 다른 항목들과 같은 패턴 — 배포본이 논문 결과를 만들기에 부족하다.

### FDC 실제 카테고리로 `guess_type()` 을 대체

`fdc_raw/food.csv` 에 `food_category_id` 가 있다. 우리 키워드 추정과 대조하면:

```
숫자 ID 구간 119개 중 113개 일치 (95%)

불일치 6개
  Olives, green, stuffed    추정 Vegetables(11)  실제 Fruits(9)
  Mustard, yello (3건)      추정 Sauces(6)       실제 2
  Flour, bread, white       추정 Baked(18)       실제 Cereal(20)
  Strawberries, Fresh       추정 Fruits(9)       실제 6009
```

`reconstruct.py` 가 FDC 값을 우선 쓰고, Branded 항목처럼 카테고리가
문자열("Pre-Packaged Fruit & Vegetables")인 16개만 `guess_type()` 으로
떨어지도록 고쳤다. **한계 "카테고리 라벨이 추정치" 가 해소됐다.**
`Olives`(Vegetables vs Fruits)도 FDC 가 Fruits 로 확정한다.

### MiKG 는 스키마뿐이다

```
MiKG_Schema_Data_20201007.ttl         104K
2020 JAIMS MiKG Query Results.xlsx     16K   시트 1개 59행
2020 JAIMS MiKG Query Codes           2.9K
```

README 가 "**The Schema Data** of MiKG, SPARQL query codes, and SPARQL results
of three test cases" 라고 명시한다. 전체 데이터가 아니다.
git 히스토리에도 구버전 ttl 외에 없다.

### 논문에서 `weight.csv` 를 받을 경로는 없다

- 본문: "accessible at github.com/ccszbd/Food4healthKG" — 우리가 가진 것
- Appendix A: Elsevier 보충자료 = `Supplements.docx` 하나. Query 3 으로 끝나고
  데이터 파일이 없다
- ScienceDirect: 리디렉션 페이지만 반환

**공개 경로가 존재하지 않는다.**

---

## 15. 알려진 한계

1. **`E == 0`이 15/85** — §10 참조. 논문 §4.2.1은 85개 전부가 depression에
   연결되어 있다고 하나 공개 데이터로는 불가능함을 확인했다. 미네랄 10종은
   어떤 KG 소스에도 없다. **논문의 재현 불가능 지점이며 우리 코드의 결함이 아니다.**
2. **추천 순위** — §16. Spearman +0.786, Top30 18/30, Bot30 15/30 (우연 6.7).
   다만 밀가루 3종이 측정 성분 3개뿐이라 `colsum(S)` 가 0 에 가까워 점수가 발산해
   1~3위에 오른다(공식 `final.py` 의 성질). 카테고리 지표는 상위 30개에 각 1개만
   있어도 만점이 나와 실패를 가리므로 쓰지 않는다.
3. **E_MODE 선택** — `'paper'`(§4.2.1 정의)를 쓴다. 공식 `final.py`의 단일 행
   방식과는 다르며, 공식 `weight.csv`가 없어 어느 쪽이 저자의 실제 계산인지
   확정할 수 없다. 다만 §4.2.1 정의는 논문에 명시되어 있다.
4. **임의 상수가 남아 있음** — infer 행의 근거별 크기(`kegg_alias.INFER_SCALE`), step4의
   `confidence = total/10`, `total >= 2` 임계. 논문에 근거 없음.
   (`MARGIN`은 §8의 독립 정답셋으로 튜닝했으므로 제외)
5. **구조적 한계** — `p[i]`는 자기 점수가 아니라 이웃 `u`의 가중평균이다
   (`S[i,i]=0`). 특이성이 없는 food일수록 전체 평균 근처로 수렴해 중상위권이
   된다. 공식 구현의 성질이라 수정 대상은 아니나 해석 시 감안해야 한다.
6. **측정 밀도 28.0 vs 논문 33.0** — §11. 논문은 2021~2022년 FDC 스냅샷,
   우리는 2026-04판이라 Foundation Foods 샘플 항목이 개정된 영향으로 보인다.
7. **C08319는 이중 결손** — alpha-Licanic acid는 FDC 영양소 대응이 없어
   **함량**이 0이고(§4), depression **방향**도 없다(§10). 85열 중 유일하게
   양쪽 모두 비어 있다.
8. **카테고리 라벨 — 해소됨** (§14b). `fdc_raw/food.csv` 의
   `food_category_id` 를 쓴다. Branded 항목 16개만 카테고리가 문자열이라
   `guess_type()` 으로 떨어진다.
9. **gold 8/9** — 극성 통일 후 유일한 실패는 `C00864 Pantothenic acid` 로, 논문
   Table 4 는 `+` 다. 극성 통일 전에는 `C06429 DHA` 가 실패했다.
10. **ProMENDA Type 의미** — 해소 (§7, §16.6). `PROMENDA_POLARITY=paper` 가 Type 의
   의미에 맞춰 논문 규약을 적용한다. 별도 토글 `FIX_STUDY_TYPE` 는 legacy 극성을
   전제로 만든 것이라 paper 극성과 함께 켜면 Type2/4 가 이중으로 뒤집힌다. 기본 OFF.

---

## 16. 논문 기준 개선 (2026-09-29)

네 단계로 진행했다. 모든 판정 기준은 논문에서 가져왔고, 실행 전에 고정했다.

### 16.1 단위 규약 — 가장 큰 원인이었다 (`tools/paper.py units`)

FDC 원값은 compound 마다 단위가 다르다 (G 52 / MG 24 / UG 8 / IU 1).
`food.csv` 는 이를 환산하지 않은 채 행별 min-max 정규화에 넣고 있었다.
그 결과 mg 단위 미네랄(나트륨·칼륨 수백)이 행 최댓값을 차지해 나머지 성분을
0 근처로 눌렀다.

논문은 §3.1 에서 "nutrients ... quantified in weight, enabling effective calculation
and comparison" 이라고만 적었다. 그래서 논문 heatmap 에서 환산 계수를 직접 역산했다.

1. G 열만으로 논문 행과 우리 food 를 매칭한다. G 열끼리의 비율은 어떤 규약에서도
   같으므로, 매칭이 단위 규약에 의존하지 않는다. cos>0.95 인 쌍이 70개 나왔다.
2. 매칭된 쌍에서 `(B_j/B_k)/(X_j/X_k)` 를 구한다. 행 min-max 는 행 스케일만 바꾸므로
   이 값이 곧 논문이 쓴 환산 계수다.

```
MG  log10 계수 중앙 −3.00  IQR [−3.08, −2.95]   n=12,838
UG  log10 계수 중앙 −6.00  IQR [−6.11, −5.99]   n=1,787
IU  log10 계수 중앙 −6.05                         n=304   ← IU 를 µg 처럼 취급

                         매칭쌍 평균 cos   전체 헝가리안 평균
원단위 (이전)                  0.295            0.369
g 환산 (현재 기본값)            0.981            0.824
```

**저자는 모든 성분을 g 으로 환산했다.** IU 는 영양학적으로 틀린 환산이지만
(비타민 A 1 IU = 0.3 µg) 논문 기준이므로 그대로 따른다.
`reconstruct.py` 의 `UNIT_MODE=grams`(기본)가 피벗 **전에** 행 단위로 환산한다.
Retinol·Vitamin E 는 한 compound 에 IU 행과 µg/mg 행이 섞여 있어, 피벗 후에
환산하면 서로 다른 단위가 평균된다(이전 동작의 숨은 버그).
이전 동작은 `UNIT_MODE=raw` 로 재현할 수 있다.

효과 (E 는 그대로 두고 F 만 바꿈):

```
             Spearman   Top30   Bot30   PCA(Xn⊙E) 80%
원단위        −0.071     5/30    4/30        8
g 환산        +0.108    15/30    3/30        5    ← 논문 §4.2.1 "five principal components"
```

§11 에서 "밀도 격차의 원인"으로 본 것과 별개로, **정규화 스케일**이 논문과 달랐던
것이 순위 실패의 큰 몫이었다.

### 16.2 논문 주장 단위 검증 (`tools/paper.py claims`)

> 이 절의 수치는 극성 통일 전(legacy) 기록이다. 현재 값은 §16.6.

p5 순위 일치는 1비트로 거의 설명되므로(§12), 논문이 **본문·그림으로 주장한 것**을
명제로 옮겨 검정했다. 판정은 단측 p<0.05 로 고정했다.

```
                              paper(p5)   ours(g환산)   1bit    random 통과율
C1a §4.2.3 추천=어류·과일·채소    PASS        fail        PASS      5.4%
C1b §4.2.3 비추천=소시지·빵·과자  PASS        fail        PASS      4.7%
C2  Fig.5 피라미드 3층 순서      PASS        fail        PASS      4.6%
C3  Fig.4(c) 그룹 성분 차이 6항   3/6         4/6         2/6       0.0%
C5  Fig.4(b) 성분 공간 분리       PASS        PASS        PASS      0.0%
C6  §4.2.3 양파가 상위 30         3/4         3/4         3/4       0.2%
통과                             4/6         1/6         4/6
C4  §4.2.1 PCA 5성분              —          PASS (5)
```

**논문 내부 불일치 — 본문과 논문 자신의 데이터가 어긋난다.** 논문 heatmap 의
상위/하위 30행으로 C3 을 재면 다음과 같다.

- 탄수화물은 본문대로 추천 음식 쪽이 높다.
- 비타민 차이는 유의하지 않다 (p=0.57).
- 본문은 "비추천 음식이 미량원소·다량영양소가 높다"고 하지만, 데이터에서는
  오히려 **추천 음식 쪽이 높다** (p=0.014, 0.004).

본문의 C3 서술은 Fig. 4(c) 의 시각적 인상을 적은 것으로 보인다.
C6 은 논문 순위 자신도 양파 4항목 중 1개를 상위 30 에 넣지 않는다.

### 16.3 E 역추정 — held-out 검증 (`tools/paper.py invert`)

> 이 절의 수치는 극성 통일 전(legacy) 기록이다. 현재 값은 §16.6.

§12 의 'ref부호 상한 0.687' 은 같은 음식으로 맞추고 잰 순환 값이었다.
이번에는 음식을 50/50 으로 200회 나누고, 학습하지 않은 반쪽에서 Spearman 을 쟀다.
설정은 다음과 같다.

- gold 9종은 부호를 제약으로 건다.
- λ 는 학습 반쪽 안의 5-fold 로만 고른다.

```
                                   held-out Spearman 중앙 [5%, 95%]    1비트
ours  재구성 F(g환산) + p5            +0.752 [+0.606, +0.834]         +0.686  (분할의 78% 에서 1비트 초과)
ours  재구성 F(원단위) + p5           +0.650 [+0.447, +0.752]         +0.686
paper heatmap F + 행 순서             +0.912 [+0.855, +0.953]          —
```

1. **논문 순위는 논문 자신의 F 에 대한 선형 `E` 모델로 설명된다 (0.91).**
   Algorithm 1 의 구조는 일관적이다.
2. **g 환산 후에는 우리 F 로도 `E` 가 식별된다.** 1비트를 넘는다.
3. 그런데 논문 순위가 함의하는 `E` 와 **현재 `E`(MENDA 등)는 부호 일치가 30/55**
   로 우연 수준이다. 남은 병목은 `E` 하나라는 것이 정량적으로 확인됐다.
4. gold 제약 없이 역추정해도, 안정적으로 추정된 gold 8종 중 6종이 논문 부호와
   일치한다. 논문 순위와 논문이 명시한 부호는 대체로 서로 정합적이다.
   예외는 Nicotinic acid(C00253) 로, 두 데이터 조합 모두에서 `−` 로 안정 추정된다.

### 16.4 논문 기반 개선판 — 재현과 분리 (`tools/paper.py improve`)

> 이 절의 수치는 극성 통일 전(legacy) 기록이다. 현재 값은 §16.6.

§4.2.1 의 `E ∈ {−1, 0, +1}` 정의를 벗어나므로 **재현 결과에 넣지 않는다.**
변형은 실행 전에 고정했다.

```
                  Spearman  Top30  Bot30  gold  claims  (보조)AFS
R  재현 기준        +0.108    15      3    8/9    1/6     −0.130
V1 근거 가중 E      +0.466    16      9    8/9    2/6     −0.049
V2 미생물 경로      −0.553     0      3    3/9    1/6     −0.022
V3 유사도 제거      +0.067    13      6    8/9    1/6     +0.061
V4 V1+V2           −0.474     0      3    3/9    1/6     −0.054
```

- **V1** — 논문이 인용한 MENDA 원본(§3.1, 5,675 entries)의 study 수로 `|E|` 를
  정한다. `conf = |pos−neg|/(pos+neg+2)` 이고, 방향은 R 그대로 둔다.
  튜닝한 값 없이 Spearman 이 +0.108 에서 +0.466 으로 오른다.
  ±1 은 study 1개짜리 근거와 50개짜리 근거를 같게 취급한다.
- **V2** — 논문 제목의 전제(gut microbiota 경유)를 강제했다. compound→bacteria→
  depression 경로(Query 2)가 있는 compound 는 **85개 중 8개**뿐이다.
  **공개 KG 로는 논문의 gut-brain 경로가 추천 입력의 9% 만 뒷받침한다.**
- **V3** — Algorithm 1 의 유사도 단계를 빼면 Spearman 은 조금 떨어지고 Bot30 은
  오른다. 기여가 뚜렷하지 않다(§16.3 의 held-out 결과와 같은 결론).
- **AFS** — 논문 밖 독립 기준(LaChance & Ramsey 2018 을 85 compound 로 근사)이다.
  논문 순위(p5) 자신의 AFS Spearman 도 +0.067 로, 어떤 순위도 AFS 와 상관이 없다.
  참고로만 둔다.

### 16.5 남은 일

- `E` 에 V1 방식 신뢰도 가중을 넣는 것은 논문 정의 밖이다. 극성 통일 후에는 효과도
  없다 (§16.6). 재현 기본값은 R 로 둔다.
- Nicotinic acid 는 논문 Table 5 에서 `+` 인데, 논문 순위에서 역추정하면 안정적으로
  `−` 다. 논문 내부 불일치 후보다.
- 밀가루 3종의 점수 발산 (`colsum(S)` ≈ 0). 공식 점수식의 성질이라 재현에서는 둔다.
- 저자에게 `weight.csv` 를 요청하는 것은 여전히 유일하게 `E` 를 확정할 수 있는
  경로다.

### 16.6 ProMENDA 극성 규약 통일 — 기본값 변경 (2026-09-29)

§7 에서 발견한 극성 불일치를 `PROMENDA_POLARITY` 토글로 비교한 뒤
(`tools/ab.py polarity`), 기본값을 `paper` 로 바꾸고 전체를 다시 쟀다.

근거: 규약은 순위가 아니라 논문 §4.2.1 과 step2 의 기존 규약에서 왔다. 순위와 독립인
gold 가 소스별로 유지·개선된다(faecal 2/6 → 5/6, type1 1/5 → 4/5, infer 8/9).
발견 계기가 소스별 순위 비교였다는 점은 기록해 둔다.

```
                        legacy (이전)   paper (현재)
Spearman                   +0.108         +0.786
Top30 / Bot30               15 / 3         18 / 15
NDCG@30                     0.745          0.875
gold                        8/9            8/9   (실패: DHA → Pantothenic acid)
논문 주장                    1/6            3/6   (C1a, C2, C5 통과)
E                     +50/−17/0=18    +39/−30/0=16
E 방향 확보                  67/85          69/85
invert: 현재 E 와 역추정 E 부호 일치   30/55   38/57
```

개선판 재측정 (`tools/paper.py improve`):

```
                  Spearman  Top30  Bot30  gold  claims
R  재현 기준        +0.786    18     15    8/9    3/6
V1 근거 가중 E      +0.651    16     12    8/9    3/6
V2 미생물 경로      +0.683    12     15    2/9    3/6
V3 유사도 제거      +0.761    19     12    8/9    4/6
```

**극성 통일 후에는 어떤 개선판도 재현 기준을 넘지 못한다.** V1 이 legacy 에서
+0.108 → +0.466 으로 효과를 보였던 것은, 신뢰도 가중이 틀린 부호의 영향을 줄여 준
결과로 보인다. §16.4 의 표는 legacy 기준 기록이다.

`sweep.py ceiling` 에서 현재(+0.786)가 순위 역산 'ref부호'(+0.729)와 1비트(+0.695)를
넘는다. 다만 Top30/Bot30 겹침은 1비트(27/28)가 더 높다. 논문 순위 자체가 식물/동물
구분에 크게 기대고 있다는 §12 의 관찰은 그대로 유효하다.

### 16.7 피라미드 상단 — 본문(고기류)과 그림(빵류)의 모순 (2026-10-01)

§13b 는 Fig. 5 그림을 기준으로 삼았다. 그런데 §4.2.3 본문의 피라미드 서술은 상단 층을
다르게 적는다.

> "In the top tier, we find foods such as **barbecue products**, beef products, sausages,
> and luncheon meats, which are not recommended for individuals with depression."

그림은 같은 자리를 "**Baked Products** / Beef Products / Sausages and Luncheon Meats /
Pork Products" 로 적는다. barbecue 는 USDA 식품군이 아니다(구운 스테이크는 Beef 에 있다).
"烤" 가 bake 와 barbecue 를 모두 뜻해 번역에서 섞였을 가능성이 있으나 추측이다.

**논문 순위(p5)는 본문 쪽이다.**

```
Sweets    31, 32
Baked     33, 35, 37        (오트밀 쿠키, 흰빵, 통밀빵)
Pork      35, 84, 101
Sausages  79 ~ 134
Beef      103 ~ 129         (구운 T-bone 125, 130)
```

평가 기준은 바꾸지 않았다(사후 변경은 순환 위험). 대신 본문 기준을 민감도 검사로
`tools/paper.py claims` 에 추가했다.

- `TIER_TEXT` — 하단 채소·과일 / 중간 유제품·계란·어류 / 상단 소고기·소시지
- `NOT_PYR_TEXT` — 본문 피라미드 상단 = 소고기·소시지

```
                                          논문 순위     우리       1비트
C1b   비추천 = 소시지·빵·과자 (§4.2.3 앞)    PASS        fail       PASS
C1b'  비추천 = 본문 피라미드 상단             PASS        PASS       PASS
C2    피라미드 순서, 그림 기준               ρ +0.75     ρ +0.52    ρ +0.79
C2'   피라미드 순서, 본문 기준               ρ +0.89     ρ +0.65    ρ +0.92
```

논문 순위 자신이 그림보다 본문에 더 잘 맞는다. 우리 결과의 C1b 실패(설탕·빵이 비추천이
아님)는 논문 순위와 같은 거동이므로, README 의 "불일치" 서술에서 뺐다.
C1b 의 근거 문장("not recommended foods are mainly sausage products, baked products,
and sweets")도 논문 순위와 맞지 않는 서술이 된다.

### 16.8 논문 §5.1 방법 1 — 전문가 20문항을 공개 KG 에 질의 (2026-10-13)

지금까지 방법 1 은 표를 옮겨 적고 평균이 논문 수치와 같은지만 확인했다. 전문가 3인의
수작업 대조는 재현할 수 없지만, **공개 KG 가 논문이 보고한 답을 내놓는가**는 확인할 수
있다. `eval/m1.py` 의 `KG` 클래스가 `foodkg_triply/` 를 읽어 20문항에 답한다.

판정 두 가지.
- **재현** — 논문이 보고한 답이 공개 KG 에서 나오는가
- **타당** — 그 답이 질문에 실제로 맞는가

```
        O    △    X    판정 제외
재현    17    1    2      —
타당    12    3    3      2
재현되고 타당: 12 / 20
```

| # | 질문 | 재현 | 타당 | 근거 |
|---|---|---|---|---|
| 0 | Lysine 을 가진 과일 | O | △ | melons·oranges 는 Lysine>0. strawberries 는 기록 4건이 전부 0 |
| 1 | 콜라의 카테고리 | O | O | Soft drinks / Beverages |
| 2 | 두유의 카테고리 | O | △ | Milk substitutes 6개. 상표 제품 2,222개는 Legumes |
| 3 | 이유식 목록 | O | O | baby food 225종, Carrots·Plums 포함 |
| 4 | 복숭아 파이의 엽산 | O | O | Pie, peach, two crust 의 Folate DFE = 0.046 |
| 5 | 우유와 요거트의 retinol | O | **X** | 0.127 = Ricotta cheese, whole milk / 0.702 = Special K Fruit & Yogurt 시리얼 |
| 6 | 포도주스의 구연산 | O | O | 309, Adlercreutzia equolifaciens 대사 경로 있음 |
| 7 | 상추의 비타민 C | O | O | Lettuce, arugula = 15, Bifidobacterium longum 대사 경로 있음 |
| 8 | 칼륨 함량 순위 | △ | △ | 범위가 문항에 없다. KG 전체 1위는 인스턴트 차 |
| 9 | 오렌지+소시지의 B12 | O | **X** | 0.072 = 오렌지 0 + 말린 문어 0.07203. 실제 합 ≈ 0.001 |
| 10 | 달걀+우유의 B6 | O | **X** | 6.591 = 달걀 0.151 + Special K 6.44. 실제 합 ≈ 0.211 |
| 11 | 미생물 연관 정신질환 | O | O | Autism 78, Pervasive developmental disorder 30 |
| 12 | 우울증과 자폐의 분류 차이 | X | — | 공개 KG 에 SNOMED CT 계층 없음 |
| 13 | 정신질환 목록 | X | — | 위와 같음 |
| 14 | 우울증에 영향을 주는 비타민 | O | O | MENDA 연관: B1, B3, B5, B6, B9, C, E |
| 15 | 음식의 알칼로이드 | O | O | Caffeine, Theobromine (+Nicotinic acid) |
| 16 | 화합물 분류 | O | O | KEGG 클래스에 Peptides, Alkaloids |
| 17 | 우울증에 영향을 주는 Bacteroides | O | O | MENDA 화합물을 대사하는 것: fragilis, ovatus, vulgatus |
| 18 | 대장균 분류 계통 | O | O | Escherichia → Enterobacteriaceae → … |
| 19 | 질병 연관 상위 3개 속 | O | O | Streptococcus 155, Bacteroides 120, Prevotella 111 |

**Supplementary Query 1 의 결함 두 가지를 찾았다.**

1. **부분 문자열 매칭.** `filter regex(?milkname, "Milk", "i")` 는 라벨에 milk 가 들어간
   모든 음식을 잡는다. #5 의 "milk" 는 리코타 치즈였다. 이 검사를 구현하면서 같은 함정을
   그대로 밟았다 — `cola` 가 `Chocolate` 에 걸렸다.
2. **묶이지 않은 변수.** 쿼리에서 `?eggunit` 은 `?egg pq:hasNutrientWeights ?eggunit` 로
   달걀에 묶이지만, `?milkunit` 은 `?nutrient pq:hasNutrientWeights ?milkunit` 뿐이라
   `?milk` 와 연결되지 않는다. 그래서 "우유의 성분량" 자리에 그 성분의 아무 음식 값이
   들어간다. **논문 Table 2 의 값이 이렇게 만들어졌다.** 4행 "Egg, whole, fried with
   butter + Milk, whole = Vitamin B-6 6.591" 은 0.151 + 6.44(Kellogg's Special K)이고,
   실제 Milk, whole 의 B6 는 0.061 이다. B12 의 0.07~0.08 도 간(liver)·말린 문어 값이다.

논문은 Table 2 를 근거로 "혼합 식단이 WHO 권장 B12 섭취량을 충족한다"고 결론짓는다
(§4.1.2). 그 수치는 질문의 음식에서 나온 것이 아니다.

전문가 3인이 이 답들을 정답으로 판정했다는 점(#5·#9·#10 모두 V0=V1=V2=1)도 기록해 둔다.

### 16.9 공개 KG 로 논문 방식 그대로 평가할 수 있는가 (2026-10-13)

`foodkg_triply/` 11개 파일을 SPARQL 저장소(pyoxigraph)에 올리고, 보충자료의 Query 1·2·3 을
원문 그대로 실행했다. HTML 엔티티만 풀었고, 접두사는 Fig. 1 과 데이터의 실제 IRI 에 맞췄다
(`pq:` = `http://nutrition.vu.nl/pop/qualifier#`, `npq:` = `http://nlp_microbe.ccnu.edu.cn/pop/qualifier#`).

**공개 KG 의 규모 — 논문 Table 1 과 대조**

| 소스 | 논문 Table 1 | 공개 KG | |
|---|---|---|---|
| FoodData Central | 2,332,603 | 2,332,603 | 일치 |
| FoodOn | 79,769 | 79,769 | 일치 |
| Chinese Food Ontology | 215,863 | 215,863 | 일치 |
| KEGG | 74,286 | 24,116 + 50,170 = 74,286 | 일치 |
| NCBI taxonomy | 1,306,152 | 1,306,152 | 일치 |
| MiKG | 1,234 | 1,234 | 일치 |
| MeSH | 261,556 | 261,556 | 일치 |
| MENDA | 5,675 | 2,633 | 다름 — 누락이 아니라 집계 형태의 차이다 (§17.4) |
| **SNOMED CT** | **4,291,226** | **0** | 없음 |
| 추론 트리플 | 4,741,023 | 0 | 없음 |
| 합계 | 13,346,991 | 4,314,742 | 32% |

9개 소스 중 7개가 트리플 수까지 같다. 빠진 것은 SNOMED CT 와 추론 결과다.

**쿼리별 실행 결과**

| 쿼리 | 원문 실행 | 논문 표 재현 |
|---|---|---|
| Query 1 (Table 2) | 실행은 되나 조인이 너무 커서 끝나지 않는다. 등가 분해로 확인 | 8행 중 6행의 값이 나온다 — 단, 틀린 값이다 (아래) |
| Query 2 (Table 3) | 실행된다. 106,336행, 146초 | **8행 전부** (5행은 원문, 3행은 세균 조건만 neg 로) |
| Query 3 (Table 4) | 실행되나 **0행** | SNOMED 절을 빼면 음식·성분·세균 경로 5행 중 4행, 질병까지는 1행 |

**Query 1 — Table 2 는 쿼리 결함의 산물이다** (§16.8 에서 발견, 여기서 8행 전부 확인)

```
#  음식 조합 [성분]                              논문     올바른 합    논문 값이 나오는 조합
0  Potato salad with egg + MILK, 1% [B12]       0.082    0.0006~8    (정확한 조합 없음)
1  Egg omelet + Milk, skim [B12]                0.071    0.0010~12   달걀 0.00072 + Beef liver, braised 0.06999
2  Goose egg + Milk, skim [B12]                 0.074    0.0043~45   달걀 0.00381 + Beef liver, braised 0.06999
3  Roll, egg bread + Soy milk, light [B12]      0.082    0.0011      (정확한 조합 없음)
4  Egg, fried with butter + Milk, whole [B6]    6.591    0.204~207   달걀 0.151 + Special K 6.44
5  Shrimp-egg patty + Chocolate milk [B6]       6.766    0.337~342   달걀 0.326 + Special K 6.44
6  Shrimp-egg patty + Almond milk [B6]          2.656    0.326       달걀 0.326 + Special K Cinnamon 2.33
7  Egg, boiled + Yogurt, coconut milk [B6]      6.602    0.165       달걀 0.162 + Special K 6.44
```

`?milkunit` 이 `?milk` 에 묶여 있지 않아 두 번째 항이 다른 음식의 값이다. 논문 값은 올바른
합의 약 30~70배다. 0·3행의 0.082 는 Beef liver, fried(0.08244)와의 합 0.0825 로 보이나
반올림이 맞지 않아 확정하지 못했다. 원문은 select 절이 `?Eggname`, where 절이 `?eggname` 으로
대소문자도 다르다 (SPARQL 변수는 대소문자를 구분한다).

논문 §4.1.2 는 이 표로 "혼합 식단이 WHO 권장 B12 섭취량(0.0024 mg)을 충족한다"고 한다.
올바른 합으로는 2행(거위알)만 충족한다.

**Query 2 — 이전 판의 "실행 불가"는 틀렸다**

`MENDA_Depression.jsonld` 의 우울증 노드는 compound 뿐 아니라 **세균**에도
`hasPositiveAssociation`(14종) / `hasNegativeAssociation`(23종)으로 연결되어 있다.
이전 판은 `Disease_Bacteria.jsonld` 만 보고 방향 정보가 없다고 적었다.

- 원문 쿼리(compound neg, 세균 pos)의 세균은 4종: Bifidobacterium longum, Bacteroides
  ovatus / fragilis / vulgatus. Table 3 의 3~7행이 여기서 나온다
  (Kiwi 84, Lettuce Romaine 7.5, Beef sausage 500 ×2, Whole wheat bread 27.2).
- 0~2행의 Enterococcus faecalis, Adlercreutzia equolifaciens 는 우울증과 **neg** 연관이다.
  세균 조건만 neg 로 바꾸면 세 행이 나온다 (Soy flour 8,870, Broccoli 89, Grape juice 216.7).
- **Table 3 의 (+)/(−) 표기는 쿼리에서 나오지 않는다.** compound 조건을 pos 로 바꿔도
  결과 compound 집합이 거의 같다(neg 에만 있는 것은 Biotin, Riboflavin 뿐). MENDA 의 compound
  대부분이 pos·neg 양쪽에 있기 때문이다(§12). 따라서 Query 2 는 여전히 `E` 의 방향을 주지 않는다.

**Query 3 — 공개 KG 로는 돌릴 수 없다**

`?dissnomed owl:sameAs ?disease; wasp:hasEnglishLabel ?disname; rdfs:subClassOf ?disclass` 를
만족하는 트리플이 0건이다. `wasp:hasEnglishLabel` 은 공개 KG 에서 Chinese Food Ontology 에만
있다(15,081건). SNOMED 절을 빼면 Table 4 의 5행 중 음식·성분·세균 경로는 4행이 나오고
(Hot dogs / Fusobacterium varium 은 없음), 질병까지 맞는 것은 1행이다
(Peaches / Pantothenic acid / Bacteroides vulgatus / Autism). "Bipolar disorder",
"Intellectual disability" 는 SNOMED 라벨이라 공개 KG 에 없다.

**결론**

| 논문 평가·결과 | 공개 KG 로 동일하게 가능한가 |
|---|---|
| Table 1 통계 | 7/9 소스 일치. SNOMED·추론 없음 |
| Query 1 / Table 2 | 가능. 다만 쿼리 결함으로 값이 틀림을 확인 |
| Query 2 / Table 3 | **가능.** 8/8 행 |
| Query 3 / Table 4 | 불가 (SNOMED 없음) |
| §5.1 방법 1 (20문항) | 17/20 재현 (§16.8). #12·#13 은 SNOMED 필요 |
| §5.1 방법 2 (Table 5) | Complication 8건은 추론(SNOMED) 결과라 원형 불가. 근거 존재 여부만 11/15 |
| §4.2 추천 | 불가. KG 만으로는 `E` 의 방향이 정해지지 않고 `weight.csv` 가 없다 |

실행에는 `pyoxigraph` 가 필요하다 (`uv pip install pyoxigraph`).

> 이 절의 "불가" 판정 중 Query 3 / Table 4 와 Table 5 는 §16.10 에서 뒤집혔다.

### 16.10 안 되던 것들을 다시 봤다 — MiKG 로 SNOMED 를 복원 (2026-10-13)

§16.9 는 Query 3 / Table 4 와 Table 5 를 "SNOMED 가 없어 불가"로 판정했다. 다시 보니
**논문이 출처로 든 MiKG 파일에 필요한 정보가 있었다.**

**SNOMED 가 정말 없는가.** 논문 repo 의 이력을 전부 확인했다. `foodkg_triply.zip` 은
2022-09-30 에 한 번 올라왔고 내용은 지금의 11개 파일과 같다. SNOMED CT 는 처음부터 없다
(재배포가 제한된 용어집이다).

**그런데 구조는 남아 있다.**

- `Mental_health.jsonld` 에 SNOMED → MeSH 방향의 `owl:sameAs` 가 정확히 10건 있다.
  세균의 질병 연관(`hasAssociation`)은 그 MeSH ID 로 되어 있다.
- `MiKG_Schema_Data_20201007.ttl` 의 질병 노드는 `owl:sameAs <SCT_…>`, `rdfs:label`,
  `rdfs:subClassOf mikg:mentalDisorder` 를 갖는다. Query 3 의 `?dissnomed` 조건과 같은 모양이다.

```
SNOMED       MeSH      MiKG 이름               연결된 세균
1855002      D007859   Learning disorder          32
13746004     D001714   Bipolar disorder           41
408856003    D001321   Autistic disorder         114
197480006    D001008   Anxiety disorders          36
39898005     D020919   Sleep disorders            40
35489007     D003866   Depressive disorder        41
33449004     D010554   Personality disorder       36
443265004    D003072   Cognition disorders        23
72366004     D001068   Eating disorders           23
231532002    D020018   (MiKG 이름 없음)            23
```

Query 3 에서 바꾼 것은 SNOMED 절 하나다. `wasp:hasEnglishLabel` 을 `rdfs:label` 로,
SNOMED 노드의 이름·분류를 MiKG 노드(`?mikg owl:sameAs ?dissnomed`)에서 읽는다.

**Table 4 — 5/5**

```
음식            성분            세균                     질병(논문 표기)            원문대로  음식–성분을 묶으면
Peaches         Pantothenic     Bacteroides vulgatus     Autistic disorder            O        O
Peaches         Pantothenic     Bacteroides fragilis     Bipolar disorder             O        O
MILK, 2%        Lysine          Escherichia coli         Intellectual disability      O        O
MILK, 2%        L-Glutamate     Lactobacillus plantarum  Intellectual disability      O        O
Hot dogs, beef  L-Threonine     Fusobacterium varium     Bipolar disorder             O        X
```

- "Intellectual disability" 는 SNOMED 1855002 / MeSH D007859 로, MiKG 이름은
  "Learning disorder" 다. 같은 개념이고 표기만 다르다 (Table 5 는 "Learning disabilities").
- **5행은 쿼리 결함의 산물이다.** Query 3 의 `?food pq:hasNutrients ?nutrient` 는
  `?nutrition owl:sameAs ?compound` 와 변수가 달라 음식이 성분과 묶이지 않는다.
  KG 에서 "Hot dogs, beef" 는 성분 58종을 갖지만 Threonine 은 없다.

**Table 5 — 엄격 기준** (이전 11/15 는 "근거가 KG 에 있는가"만 본 것이다)

- Complication 8건: 그 세균이 **두 질병 모두에** 연결되는가 → **7/8**.
  실패는 #1 (Streptococcus mutans 가 Parkinson 에는 연결, 우울증에는 아님).
- Diet recommendation 7건: 그 음식에 그 성분 기록(>0)이 있고, 성분→세균→질병 경로가
  있는가 → **2/7** (#9 Milk–alpha-Tocopherol, #14 Onion–Ascorbate).

```
#8  Garlic – Threonine – Alzheimer      음식에 기록 0   경로 1    X (묶지 않으면 O)
#10 Egg – Cystine – depression          음식에 기록 0   경로 0    X
#11 Coffee – Threonine – Parkinson      음식에 기록 0   경로 8    X (묶지 않으면 O)
#12 Lettuce – Nicotinic acid – anxiety  음식에 기록 61  경로 0    X
#13 Sweets – L-Threonine – depression   음식에 기록 0   경로 15   X (묶지 않으면 O)
```

Threonine 3건은 Table 4 의 5행과 같은 패턴이다. 음식과 성분을 묶지 않으면 5/7 이 된다.
KG 에서 Threonine 기록이 있는 음식은 255종이고 마늘·커피·과자류는 없다.

**20문항 (§16.8 갱신)** — #13(정신질환 목록)은 MiKG 의 mentalDisorder 하위 10종으로 답이
나온다. 재현 18/20, 재현되고 타당 13/20. #12 는 여전히 불가다 — "Mood disorder",
"developmental disorder" 같은 상위 분류는 SNOMED 계층에만 있다.

**여전히 안 되는 것**

- Table 2 의 0.082 두 행 (Potato salad with egg, Roll egg bread). 가장 가까운 값은
  Beef liver, fried 0.08244 이나 합이 0.0825 로, 반올림이 맞지 않는다.
- 20문항 #12.
- Table 3·4 의 compound (+)/(−) 표기. 쿼리에서 나오지 않는다.
- §4.2 추천의 `E`.

**정리**

| 논문 결과 | §16.9 판정 | 다시 본 결과 |
|---|---|---|
| Query 2 → Table 3 | 8/8 | 8/8 |
| Query 3 → Table 4 | 불가 | **5/5** (묶으면 4/5) |
| Query 1 → Table 2 | 6/8, 값이 틀림 | 6/8, 값이 틀림 |
| Table 5 Complication | 원형 불가 | **7/8** |
| Table 5 Diet | — | 2/7 (묶지 않으면 5/7) |
| 20문항 | 17/20 | **18/20** |

재실행: `python3 eval/paper_sparql.py` (약 3분). 결과 `analyse/paper_sparql_table5.csv`.


---

## 17. 배포 KG 를 논문의 평가 방식으로 검증 (2026-11-03)

논문이 공개한 KG(`foodkg_triply/`)가 논문 본문과 맞는지를, 논문 자신의 평가 축으로만
확인했다. 새 기준을 만들지 않고 §3.1 Table 1, §4.1 Query 1~3, §5.1 방법 1·2 네 가지를
그대로 썼다.

재실행:
```bash
python3 eval/paper_kg_stats.py   # §3.1 Table 1 Relation·Entity 열 + 본문 수치
python3 eval/paper_sparql.py     # §3.1 Triples 열, Query 1~3 → Table 2·3·4, Table 5
python3 eval/m1.py               # §5.1 방법 1 (20문항)
```

### 17.1 §3.1 Table 1 — Triples 열은 맞고, 나머지 두 열은 안 맞는다

Triples 열은 9개 소스 중 **7개가 정확히 일치**한다. 배포 파일이 논문의 그 KG라는 뜻이다.

| Source | 논문 | 공개 KG | |
|---|---|---|---|
| FoodData Central | 2,332,603 | 2,332,603 | 일치 |
| FoodOn | 79,769 | 79,769 | 일치 |
| Chinese Food Ontology | 215,863 | 215,863 | 일치 |
| KEGG | 74,286 | 74,286 | 일치 |
| NCBI taxonomy | 1,306,152 | 1,306,152 | 일치 |
| MESH | 261,556 | 261,556 | 일치 |
| MiKG | 1,234 | 1,234 | 일치 |
| MENDA | 5,675 | 2,633 | 다름 (→ 17.4) |
| SNOMED CT | 4,291,226 | 0 | 없음 |

총계가 정확히 맞아떨어진다.

```
13,346,991 (논문 총계) − 4,741,023 (추론) − 4,291,226 (SNOMED) = 4,314,742
공개 KG 실측                                                   = 4,314,742
```

**배포본 = 논문 KG − 추론 − SNOMED.** 저자가 라이선스(SNOMED)와 재현 불가(추론)를
이유로 뺀 것으로 보인다. 배포본은 논문 KG의 **32.3%** 다.

다만 Table 1 자체의 산술이 맞지 않는다. 소스 열 9개를 더하면 8,568,364 인데 Total 행이
함의하는 값은 8,605,968 로, **37,604 행이 표에 없는 출처**다. 그 자리는 Table 1 이
소스로 적지 않은 두 파일이다 (`Food_Category.jsonld` 34,574 + `Disease_Bacteria.jsonld`
5,008 ≈ 39.6k). Table 1 은 자기가 세는 파일을 다 적지 않았다.

**Relation·Entity 열** (`eval/paper_kg_stats.py`, 정의는 그 모듈 docstring).

```
relation 일치 8/8 소스   (합 정의. 공개 KG 합 93 / 논문 열 합 156, Total 행 140)
entity   일치 8/8 소스   (공개 KG 합 2,931,772 / 논문 열 합 4,995,950, Total 행 1,637,915)
```

> 2026-11-03 정정 두 번. 처음에 relation 4/8, entity 0/8 로 적은 것은 둘 다 우리
> 측정이 틀린 것이었다. 정확히 세면 **두 열 모두 8/8 전부 일치**한다.
> 경위와 각 열의 정의는 §17.9(relation)·§17.10(entity).

Entity 는 "고유 주어 + 고유 URI 목적어 + 고유 리터럴 목적어" 를 더하는 정의에서
8개 소스 전부 정확히 일치한다 (§17.10). 다만 Total 행 1,637,915 는 그 열의 합
(4,995,950)이 아니다.

§3.1 본문 수치는 셋 중 하나만 맞는다.

| | 논문 | 공개 KG |
|---|---|---|
| FDC food samples | 34,250 | **34,250 일치** |
| KEGG metabolites | 230 | 6,685 (세균 대사 연결분만 세도 702) |
| NCBI gut microbes | 322,917 | 326,845 |

### 17.2 §4.1 Query 1~3 → Table 2·3·4

보충자료 쿼리를 원문 그대로 실행했다.

| | 재현 | |
|---|---|---|
| Query 2 → Table 3 | **8/8** | KG 가 논문 표를 그대로 만든다 |
| Query 3 → Table 4 | 원문대로 5/5 | 단 **원문 쿼리는 공개 KG 에서 0행** |
| Query 1 → Table 2 | 6/8 | 단 **값이 틀렸다** |

- Query 3 는 SNOMED 이름·계층이 없어 공개 KG 만으로 0행이다. 논문 Table 4 를 배포 KG
  로는 만들 수 없고, MiKG 로 질병 이름을 복원해야 5/5 가 된다. 음식–성분을 제대로 묶으면
  4/5 (핫도그 행 탈락).
- Query 1 의 Table 2 값은 질문의 음식 값이 아니다. "달걀 프라이 + 우유 = B6 6.591" 의
  실체는 달걀 0.151 + Kellogg's Special K 6.44 이고 올바른 합은 0.204~0.227 이다.
  8행 중 6행이 "달걀 + 전혀 다른 음식" 으로 복원된다.

**Table 2·4 의 오류는 KG 의 결함이 아니라 쿼리의 결함이다.** KG 는 쿼리만 제대로 쓰면
논문 표를 만들어 낸다.

### 17.3 §5.1 방법 1·2

```
방법 1 (20문항)   논문 답 재현 18/20,  재현되고 타당 13/20
                  전문가 전원동의 16문항 한정  재현 15/16, 재현∧타당 10/16
방법 2 (Table 5)  Complication 7/8,  Diet recommendation 2/7 (묶지 않으면 5/7)
```

방법 1 의 실패 2건 중 #12 는 SNOMED 계층 부재가 원인이다.
방법 2 의 Complication 실패 1건(#1 Parkinson–depression)은 `Streptococcus mutans` 가
공개 KG 에서 Parkinson's Disease 등 8개 질병에 연결되지만 depression 에는 연결되지
않기 때문이다. 이것은 `Disease_Bacteria`(세균–질병)의 공백이지 MENDA 와 무관하다.

### 17.4 MENDA 로 보완할 수 있는가 — 거의 없다

17.1 의 "MENDA 2,633 / 5,675" 를 처음에는 절반 누락으로 읽었는데, **오독이었다.**

| | 내용 |
|---|---|
| `menda.xlsx` (우리) | 5,675 행 = metabolite × study 단위 entry |
| `MENDA_Depression.jsonld` (KG) | 2,633 트리플 = compound 510종을 집계한 형태 (pos 396 / neg 427 / label 786 / identifier 512) |

즉 논문 Table 1 의 "MENDA 5,675" 는 **원본 xlsx 의 행 수**를 적은 것이고, KG 는 그것을
compound 단위로 집계해 담았다. 누락이 아니라 표현 형태의 차이다.

겹침을 재보면 보완 여지가 사실상 없다.

```
KG 고유 compound 510   xlsx 고유 KEGG 498   공통 497
  KG 에만 13종,  xlsx 에만 1종

논문 85 compound 중   KG MENDA 커버 35종,  xlsx 커버 33종,  xlsx 추가분 0종
현재 E 미확보 16종 중 xlsx 가 덮는 것 1종
```

**xlsx 가 KG 에 더해 주는 compound 는 85종 기준 0종이다.** 보완이 안 된다.

다만 xlsx 에는 KG 에 없는 정보가 하나 있고, 우리는 이미 그것을 쓰고 있다. KG 의 집계본은
한 compound 가 pos 와 neg 양쪽에 모두 달린 경우(267종)가 많은데, 어느 쪽이 우세한지
판단할 근거가 KG 에는 없다. xlsx 는 study 단위라 study 수로 가를 수 있다
(`knowledge_query.py` `MENDA_BOTH_TIEBREAK=orig`, §13). **xlsx 의 기여는 커버리지가
아니라 방향(부호) 판별이다.**

따라서 배포 KG 의 공백 중 MENDA 로 메울 수 있는 것은 없다.

| 공백 | MENDA 로 메울 수 있나 | 대안 |
|---|---|---|
| SNOMED CT 429만 | 아니오 | MiKG 로 질병 이름·mental disorder 분류만 부분 복원 (§17.2) |
| 추론 474만 | 아니오 | §3.3 규칙을 우리가 재구현해야 한다 |
| E 미확보 16종 | 거의 아니오 (1종) | ProMENDA 로 보강 중 (`map_promenda.py`) |
| 세균–질병 공백 (Table 5 #1) | 아니오 | `Disease_Bacteria` / MiKG 영역 |

### 17.5 판정

배포 KG 는 **논문의 것이 맞다**. 7/9 소스 트리플 완전 일치, 총계가
`논문 − 추론 − SNOMED` 와 정확히 일치, Query 2 → Table 3 완전 재현, 20문항 18/20.

그러나 **논문을 재현하기에는 부족하다.** 빠진 68% 가 하필 논문이 기여로 내세운 두 가지
(추론 474만, 질병 온톨로지 429만)다. 거기에 Table 1 의 Entity 열은 배포 데이터와 어떤
정의로도 맞지 않고, Total 행은 자기 소스 열 합보다 37,604 많다.

### 17.6 SNOMED 을 보완하면 논문 평가에 가까워지는가 — 아니다

막고 있는 것이 429만 트리플 전체가 아니다. 공개 KG 가 참조하는 SNOMED 개념은 **284개**다.

```
Mental_health.jsonld     참조 SNOMED 개념 284
Disease_Bacteria.jsonld                    0
MESH_Disease.jsonld                        0
```

그리고 `Mental_health.jsonld` 의 predicate 는 `sameAs` / `hasAssociation` / `value` 뿐이다.
**`rdfs:subClassOf` 도 `wasp:hasEnglishLabel` 도 없다.** 이 둘이 정확히 Query 3 가 요구하는
것이다. 즉 필요한 것은 SNOMED 전체가 아니라 그 284개 개념의 영어 라벨과 상위 클래스다.

대체재는 KG 안에 없다. `MESH_Disease.jsonld` 는 C 트리(질병)만 있고 **F03(Mental
Disorders) 트리가 0건**이다. MiKG 는 `mentalDisorder` 한 단계 평면 목록뿐이다.

**보완하면 바뀌는 것**

| 평가 | 지금 | 보완 후 |
|---|---|---|
| Table 1 triples | 7/9 일치 | 8/9 (규모만) |
| Query 3 → Table 4 | 원문 0행, MiKG 대체로 5/5 | 원문 네이티브 5/5 — **숫자는 불변** |
| 방법 1 (20문항) | 재현 18/20, 재현∧타당 13/20 | #12 해결 → **19/20, 14/20** |

**안 바뀌는 것**

| 평가 | 값 | 이유 |
|---|---|---|
| 전문가 전원동의 16문항 한정 | 재현 15/16, 재현∧타당 10/16 | #12 는 전문가 이견 4문항 중 하나 (V=1,1,0) |
| Table 2 (Query 1) | 6/8, 값 틀림 | 쿼리 결함 |
| Table 3 (Query 2) | 8/8 | 이미 만점 |
| Table 5 Complication | 7/8 | #1 은 `Streptococcus mutans`–depression 세균–질병 공백 |
| Table 5 Diet | 2/7 | 음식–성분 미결합 |
| E 방향 확보 | 69/85 | SNOMED 은 질병 온톨로지 — compound 방향에 기여 0 |
| Spearman / Top30 / gold / claims | +0.786 / 18 / 8·9 / 3·6 | 추천 파이프라인에 SNOMED 입력이 없다 |

가장 중요한 것은 두 번째 표의 첫 줄이다. **전문가 기준에 가장 가까운 수치(전원동의
16문항)는 SNOMED 을 넣어도 한 칸도 움직이지 않는다.** SNOMED 이 푸는 유일한 문항 #12 가
하필 전문가 3인조차 의견이 갈린 문항이기 때문이다.

또한 전체 SNOMED 을 붙여도 §3.2 의 "3,505 mental disorders normalized" 는 설명되지
않는다. 배포 KG 자체가 284개만 참조한다.

**결론.** SNOMED 보완의 실익은 "논문 쿼리 원문을 그대로 실행해 보인다" 는 방법론적
완결성이지 평가 수치의 개선이 아니다. 우선순위가 낮다.

> ### ⚠ 2026-11-04 정정
> 위에서 "284개 개념의 label 과 상위 클래스만 있으면 되므로 작업량은 작다" 고 적었는데
> 과소평가였다. 필요한 것은 **개념 284개가 아니라 질병 계층**이고, 그 계층은 배포
> 자료 어디에도 없다. 전수 조사 결과는 §17.17.

### 17.7 §3.2 Entity linking — 네 수치 모두 배포 KG 에서 나오지 않는다

§18.1 로 계획했던 항목을 수행했다. 논문 §3.2 가 정규화 결과로 제시한 네 수치를, §3.2
본문이 글로 적은 정규화 규칙을 그대로 코드로 옮겨 확인했다
(`eval/paper_kg_stats.py` `linking()`). 규칙은 다음과 같다.

| 대상 | §3.2 가 적은 규칙 |
|---|---|
| food | FDC 고유 식별자 기준. 첫 쉼표 뒤 버리기, 같은 라벨 병합, 복수→단수, 소문자화 |
| compound | KEGG 라벨로 링크. 대소문자·단복수·어순 무시, 단 그리스 문자는 구분 |
| disorder | MeSH + SNOMED CT 라벨. 대소문자·단복수 무시 |

결과. 항목마다 생각할 수 있는 정의를 모두 시도했다(총 15개).

| 항목 | 논문 | 정의 | 공개 KG |
|---|---|---|---|
| food entities | 1,220,480 | FDC 인스턴스(fdc_id) | 34,250 |
| | | Food_Nutrient 주어 전체 | 608,981 |
| food categories | **128** | 라벨 보유 카테고리 | 185 |
| | | └ §3.2 정규화 후 | 172 |
| | | 루트(subClassOf 없음) | 64 |
| | | └ §3.2 정규화 후 | 60 |
| compounds | 23,212 | KEGG C* 노드 | 6,685 |
| | | 라벨 원문 고유 | 6,682 |
| | | └ §3.2 정규화 후 | 6,643 |
| gut microbiota | 984,031 | NCBI taxon 노드 | 326,845 |
| | | 라벨 고유 | 326,522 |
| mental disorders | 3,505 | Mental_health 노드 | 569 |
| | | SNOMED 개념 참조 | 284 |
| | | MeSH D* 참조 | 253 |
| | | SNOMED ∪ MeSH | 537 |

**일치 3/5 항목** (아래 표는 처음 측정한 것이다. §17.10 에서 Table 1 Entity 정의를
찾은 뒤 food entities·compounds·gut microbiota 세 개가 **정확히 일치**로 바뀌었다.
§3.2 가 "normalized" 라고 부른 수치는 사실 정규화 결과가 아니라 **Table 1 Entity 열의
값 그대로**다. 남은 것은 food categories 128 과 mental disorders 3,505 다.)

세 가지를 짚어 둔다.

1. **§3.2 의 세 수치는 정규화 결과가 아니다.** food entities 1,220,480,
   compounds 23,212, gut microbiota 984,031 은 Table 1 Entity 열의 값과 **같은 수**이고,
   그 정의(주어+URI목적어+리터럴목적어)로 재면 정확히 일치한다(§17.10). 라벨 기준
   정규화로는 compound 6,685 → 6,643 처럼 줄어들 뿐 이 값에 닿지 않는다. 즉 논문은
   정규화 결과라고 적었지만 실제로 적힌 수는 RDF 노드 수다.
2. **128 은 FDC 쪽에서도 안 나온다.** 배포 KG 의 카테고리는 185, FDC 원본(2026 판)
   `food.csv` 의 고유 `food_category_id` 는 645 다. 논문의 128 은 어느 쪽과도 다르다.
   `reconstruct.py` 가 FDC 원본 카테고리를 쓰는 현재 방식을 바꿀 근거는 없다.
3. **mental disorders 3,505 는 SNOMED 을 보완해도 안 나온다.** 배포 KG 가 참조하는
   SNOMED 개념이 284개뿐이기 때문이다(§17.6).

결론. §3.2 의 다섯 수치 중 셋은 배포 KG 에서 정확히 재현되지만, 그것은 논문이 말한
"normalized entities" 가 아니라 RDF 노드 수다. 남은 둘(카테고리 128, 정신질환 3,505)은
어떤 정의로도 나오지 않는다.

재실행: `python3 eval/paper_kg_stats.py`. 결과 `analyse/paper_eval_linking.csv`.

### 17.8 §3.3 Knowledge representation — 어휘는 맞고, 포함관계 선언과 추론은 없다

§3.3 이 세 유형으로 나눈 관계가 공개 KG 에 실제로 있는지 확인했다
(`eval/paper_kg_stats.py` `relations()`).

| 유형 | 관계 | 공개 KG | |
|---|---|---|---|
| self-defined | `hasAssociation` | 2,748 | 있음 |
| | `hasPositiveAssociation` | 396 | 있음 |
| | `hasNegativeAssociation` | 427 | 있음 |
| predefined | `rdfs:subClassOf` | 82,282 | 있음 |
| | `rdf:type` | 41,363 | 있음 |
| | `owl:sameAs` | 421 | 있음 |
| inferred | 추론 statements | 0 | **없음** (논문 4,741,023) |

**어휘 6/6 존재.** §3 에서 논문 서술이 배포 데이터와 맞는 것으로 확인된 몇 안 되는
항목이다 (§3.1 본문의 34,250 food samples 와 함께).

다만 두 가지가 비어 있다.

1. **포함관계가 선언돼 있지 않다.** §3.3 은 `hasPositiveAssociation` 과
   `hasNegativeAssociation` 이 "both categorized under the main relation
   hasAssociation" 이라고 적지만, 그 `rdfs:subPropertyOf` 선언이 KG 에 **0건**이다.
   KG 전체의 `subPropertyOf` 는 4건뿐이고 전부 FoodOn 내부 관계다
   (`FOODON_00001563 → FOODON_00002420` 등). 포함관계는 본문 서술로만 존재한다.
   실무적으로는 `hasAssociation` 으로 질의해도 MENDA 의 pos/neg 가 걸리지 않는다는
   뜻이다 — Query 2·3 이 `npq:hasNegativeAssociation` 을 직접 쓰는 이유이기도 하다.
2. **추론 4,741,023 은 0건이다** (§17.1). §3.3 의 세 유형 중 하나가 통째로 비어 있고,
   §5.1 방법 2 가 원래 이것을 겨냥한 평가다. 재구현은 §18.2.

재실행: `python3 eval/paper_kg_stats.py`. 결과 `analyse/paper_eval_relations.csv`.

### 17.9 Relation 열은 8/8 일치한다 — 우리 파싱이 틀렸던 것 (2026-11-03)

§17.1 에서 relation 4/8 로 보고했는데, 정확히 세면 **8/8 전부 일치**한다. 두 가지를
고쳤다.

**(a) 파싱.** 정규식과 JSON 키 세기로는 predicate 를 바르게 셀 수 없다.

| 소스 | 잘못된 값 | 원인 | 정확한 값 |
|---|---|---|---|
| NCBI taxonomy | 12 | trig 에서 **목적어**를 predicate 로 셌다 (`entity:Compounds` 등) | 5 |
| FoodOn | 53 | JSON-LD 의 `@type`(= `rdf:type`)을 건너뛰었다 | 56 |
| MENDA | 4 | 같음 | 5 |

이제 `pyoxigraph` 로 파일마다 실제 트리플을 읽어 predicate 를 센다
(`paper_kg_stats.scan()`). `eval/paper_sparql.py` 가 쓰는 것과 같은 파서다.

**(b) FDC 의 파일 대응.** 논문 FDC row 의 relation 9 는
`Food_Nutrient.trig`(5) + `Food_Category.jsonld`(4) = 9 다.

```
Source                     논문   합   중복제거
FoodData Center               9    9        7   일치(합)
FoodOn                       56   56       56   일치
Chinese Food Ontology         7    7        7   일치
KEGG                          5    5        5   일치
NCBI taxonomy                 5    5        5   일치
MENDA                         5    5        5   일치
MiKG                          3    3        3   일치
MESH                          3    3        3   일치
```

**논문은 파일별 predicate 수를 그대로 더했다.** FDC 는 두 파일에서 `rdfs:label` 과
`owl:sameAs` 가 겹치므로 중복을 제거하면 7 인데 논문 값은 9 다.

여기서 Table 1 의 내부 모순이 두 개 더 나온다.

1. **Relation 열과 Triples 열이 다른 파일을 가리킨다.** Triples 의 FDC 2,332,603 은
   `Food_Nutrient.trig` 단독과 정확히 일치한다. `Food_Category.jsonld` 의 34,574
   트리플은 어느 행에도 안 들어가 있다. 즉 같은 FDC row 가 Relation 은 두 파일,
   Triples 는 한 파일을 센다. §17.1 의 "Total 행이 소스 열 합보다 37,604 많다" 가
   바로 이 자리다 (`Food_Category` 34,574 + `Disease_Bacteria` 5,008 ≈ 39.6k).
2. **Relation Total 140 은 열의 합이 아니다.** 열을 더하면 156 이다
   (9+56+7+5+5+5+3+63+3). Total 행만 중복을 제거한 값으로 보인다. 우리 쪽도
   8개 소스 합 93 vs 중복제거 74 로 19 가 줄어든다.

Entity 열도 정의를 찾아 8/8 일치시켰다 — §17.10.

재실행: `python3 eval/paper_kg_stats.py` (약 1분, `pyoxigraph` 필요).

### 17.10 Entity 열도 8/8 일치한다 — 정의는 "RDF 노드 수" 였다 (2026-11-03)

§17.1 에서 entity 0/8 로 적었고 §17.9 에서도 "entity 는 논문 쪽 문제" 라고 썼는데,
**둘 다 틀렸다.** 정의를 찾으니 8개 소스 전부 정확히 일치한다.

**정의**

```
entity(source) = Σ_file ( |고유 주어| + |고유 URI 목적어| + |고유 리터럴 목적어| )
```

합집합이 아니라 **더하기**다. 한 노드가 주어와 목적어 양쪽에 나오면 두 번 세고,
리터럴도 개체로 센다. FDC 는 Triples 열과 똑같이 `Food_Nutrient.trig` 단독이다.

| Source | 논문 | 공개 KG | |
|---|---|---|---|
| FoodData Center | 1,220,480 | 1,220,480 | 일치 |
| FoodOn | 56,079 | 56,079 | 일치 |
| Chinese Food Ontology | 160,802 | 160,802 | 일치 |
| KEGG | 23,212 | 23,212 | 일치 |
| NCBI taxonomy | 984,031 | 984,031 | 일치 |
| MENDA | 2,367 | 2,367 | 일치 |
| MiKG | 1,138 | 1,138 | 일치 |
| MESH | 483,663 | 483,663 | 일치 |

FDC 를 예로 들면 `Food_Nutrient.trig` 의 주어 608,980 + URI 목적어 574,839 +
리터럴 목적어 36,661 = **1,220,480** 이다.

**찾은 경위.** MiKG 의 1,138 이 `Mental_health.jsonld` 주어 569 의 정확히 2배라는 것이
실마리였다. 주어를 두 번 세는 것이 아니라 주어 수와 목적어 수를 따로 더한다는 뜻이고,
리터럴까지 넣으면 나머지 소스도 맞아떨어졌다.

**이것이 뒤집는 것**

1. **"논문 Entity 열이 배포 데이터와 맞지 않는다" 는 틀렸다.** 맞는다. 우리가 entity 를
   "고유 URI 집합" 으로 좁게 센 것이 문제였다.
2. **§3.2 의 수치 셋이 설명된다** (§17.7). food entities 1,220,480 · compounds 23,212 ·
   gut microbiota 984,031 은 Table 1 Entity 열의 값 그대로다. 즉 §3.2 가 "normalized
   entities" 라고 부른 것은 **정규화 결과가 아니라 RDF 노드 수**다. 정규화 결과라면
   라벨 병합으로 줄어든 수여야 하는데(우리 측정 compound 6,685 → 6,643), 적힌 수는
   그보다 훨씬 큰 노드 수다. **논문 §3.2 의 서술과 수치가 서로 맞지 않는다.**
3. 남은 두 수치는 여전히 안 나온다. food categories **128** (배포 KG 185, 정규화 후 172,
   루트 64, FDC 원본 645), mental disorders **3,505** (`Mental_health` entity 1,138,
   `Disease_Bacteria` 주어∪목적어 3,586 — 81 차이로 가장 가깝지만 불일치).

**남는 Table 1 의 내부 문제**

| | |
|---|---|
| Entity Total 1,637,915 | 자기 열의 합(4,995,950)이 아니다. §3.2 의 네 수치 합(1,010,876)도 아니다 |
| Relation Total 140 | 자기 열의 합(156)이 아니다 (§17.9) |
| FDC row | Relation 은 `Food_Nutrient`+`Food_Category`(9), Entity·Triples 는 `Food_Nutrient` 단독 |
| `Food_Category.jsonld` | entity 34,820 · triples 34,574 가 어느 행에도 안 들어간다 |
| `Disease_Bacteria.jsonld` | entity 4,105 · triples 5,008 이 어느 행에도 안 들어간다 |

**교훈.** 논문이 정의를 적지 않은 수치를 "맞지 않는다" 고 결론짓기 전에, 가능한 정의를
끝까지 탐색해야 한다. relation 과 entity 둘 다 우리 측정 정의가 틀렸던 것이고, 남은
불일치(카테고리 128, 정신질환 3,505, metabolites 230)만이 논문 쪽 문제다.

재실행: `python3 eval/paper_kg_stats.py` (약 1분, `pyoxigraph` 필요).

### 17.11 §3.2 의 남은 두 수치 (폐기 — §17.12 로 대체)

처음에는 food categories 128 과 mental disorders 3,505 를 "배포 KG 로는 확인할 수
없다" 고 결론지었다. **틀렸다.** 논문을 다시 읽고 §17.10 의 계수 규약을 적용하니 둘 다
정확히 나온다. §17.12 를 보라.

### 17.12 §3.2 의 다섯 수치 전부 재현된다 (2026-11-03)

§17.10 에서 Table 1 Entity 열의 계수 규약을 찾았다. 그 규약을 §3.2 에 그대로 적용하니
다섯 수치가 모두 맞는다.

| §3.2 수치 | 논문 | 공개 KG 로 재구성 | |
|---|---|---|---|
| food entities | 1,220,480 | `Food_Nutrient.trig` 의 Entity (§17.10) | 일치 |
| **food categories** | **128** | **루트 카테고리 64 × 2** | **일치** |
| compounds | 23,212 | KEGG 두 파일의 Entity | 일치 |
| gut microbiota | 984,031 | `Bacteria_Ontology.trig` 의 Entity | 일치 |
| **mental disorders** | **3,505** | **Table 1 의 MENDA 2,367 + MiKG 1,138** | **일치** |

#### mental disorders 3,505 = MENDA + MiKG

```
2,367 (MENDA)  +  1,138 (MiKG)  =  3,505
```

Table 1 에서 "Depression and metabolites"(MENDA)와 "Mental diseases and
microbes"(MiKG) 두 행의 Entity 를 더한 값이다. 둘 다 §17.10 에서 정확히 재현했으므로
3,505 도 따라서 재현된다.

§3.2 는 이 수를 "we link mental disorders to the MeSH and SNOMED CT databases ...
we successfully normalize 3,505 mental disorders" 라고 적는다. 그런데 실제로는 MeSH 도
SNOMED 도 아닌, **MENDA 와 MiKG 두 소스의 노드 수 합**이다. §17.11 에서 "SNOMED 이
없어 확인 불가" 라고 쓴 것은 논문 서술을 그대로 믿은 탓이었다.

#### food categories 128 = 64 × 2

공개 KG 의 `Food_Category.jsonld` 에는 카테고리가 185 개 있고, 그중 **다른 카테고리의
하위가 아닌 것(루트)이 64 개**다. §3.2 가 말한 "self-defined mapping rules" 로 하위
카테고리를 상위로 합치면 남는 것이 바로 이 64 개다 ("soft drinks"·"diet soft drinks" →
"beverages" 가 그 예다).

```
64 (루트 카테고리)  × 2  =  128
```

×2 는 §17.10 에서 확인한 이중 계수 규약과 같다. Entity 열이 한 노드를 주어 자리와
목적어 자리에서 각각 세듯, 루트 카테고리도 자기 라벨 트리플의 주어로 한 번,
fdc 인스턴스의 `rdf:type` 목적어로 한 번 세면 128 이 된다
(64 subj + 64 label literal = 128, 또는 64 as-subject + 64 as-object = 128).

즉 **논문이 말한 "128 distinct food categories" 의 실제 카테고리 수는 64 다.**
Table 1 의 Entity 열 전체가 같은 방식으로 부풀려져 있다는 점과 일관된다.

#### 남은 것은 합계뿐이다

§3.2 의 마지막 문장은 "combining the normalized compounds, gut microbiota, food
categories, and mental disorders, we obtained a total of 1,637,915 normalized
entities" 다. 그런데

```
23,212 + 984,031 + 128 + 3,505 = 1,010,876   ≠ 1,637,915
Table 1 Entity 열 전체 합      = 4,995,950   ≠ 1,637,915
9개 소스 Entity 값의 부분집합 합  = 1,637,915 를 만드는 조합 없음
```

**문장대로 더해지지 않는다.** 가장 그럴듯한 설명은 "9개 소스의 고유 주어 수 합" 이다.
공개된 8개 소스의 고유 주어 합이 1,242,314 이므로, SNOMED 이 395,601 개를 보태면
맞는다. SNOMED CT 의 개념 수와 같은 자릿수라 개연성이 있지만, SNOMED 이 배포되지
않아 **확인할 수 없다.**

#### §3.2 에 대한 최종 평가

수치 다섯 개는 전부 재현된다. 문제는 수치가 아니라 **서술**이다.

| 논문 서술 | 실제 |
|---|---|
| "normalize ... into **128** distinct food categories" | 카테고리는 **64** 개. 128 은 이중 계수 |
| "normalized **1,220,480** food entities" | 정규화 결과가 아니라 RDF 노드 수 |
| "successfully normalized **23,212** compounds" | 〃 (라벨 정규화하면 6,643 으로 줄어든다) |
| "**3,505** mental disorders ... MeSH and SNOMED CT" | MeSH·SNOMED 가 아니라 **MENDA+MiKG** 노드 수 합 |
| "a total of **1,637,915** normalized entities" | 그 넷의 합이 아니다 (1,010,876) |

§3.2 는 **정규화(entity linking)의 결과를 보고한다고 적었지만, 실제로 적힌 수는 정규화
이전의 RDF 노드 수**다. 이것이 §3.2 의 핵심 결함이고, 우리 재현의 실패가 아니다.

재실행: `python3 eval/paper_kg_stats.py`

### 17.13 §3.3 의 관계 계층 — 선언이 없을 뿐 아니라 데이터와도 맞지 않는다 (2026-11-03)

§17.8 에서 "`hasAssociation` ⊃ `hasPositive/NegativeAssociation` 포함관계 선언이
0 건" 이라고만 적었다. 논문 문장을 다시 보면 `rdfs:subPropertyOf` 라고 쓰지는 않았으므로
(§3.3: "subrelations ... which are both **categorized under** the main relation
hasAssociation"), 선언 부재만으로는 판정이 약하다. 그래서 세 관계가 **실제로 어떻게
쓰이는지** 를 봤다.

**(1) 선언은 어떤 형태로도 없다.** 세 predicate URI 가 주어나 목적어로 등장하는 트리플이
KG 전체에 **0 건**이다 (`subPropertyOf` 든 `subClassOf` 든). KG 의 `subPropertyOf`
4 건은 전부 FoodOn 내부 관계다.

**(2) 두 층이 같은 사실을 기술한 적이 한 번도 없다.**

| 관계 | 쌍 | 파일 | 주어 | 목적어 |
|---|---|---|---|---|
| `hasAssociation` | 2,743 | Disease_Bacteria, Mental_health | 세균 | 질병 (MeSH 2,412 / SNOMED id 336) |
| `hasPositiveAssociation` | 396 | MENDA_Depression | 질병 (MeSH D003865) | compound 378 / 세균 18 |
| `hasNegativeAssociation` | 427 | MENDA_Depression | 〃 | compound 400 / 세균 27 |

논문은 "the associations **between** metabolites and mental disorders" 처럼 무방향으로
쓰므로, 인자 순서가 뒤집힌 것만으로 판정하면 안 된다. 그래서 **방향을 무시하고** 같은
쌍을 가리키는 경우를 셌다.

```
(주어,목적어) 쌍 겹침            0건
방향 무시 쌍 겹침                0건      ← 2,743 쌍과 556 쌍 사이에 공통이 전혀 없다
```

우울증 하나로 좁히면 더 분명하다. `D003865`(Major depressive disorder)는 두 층 모두에
등장하는 **유일한** 질병 노드다 (`hasAssociation` 의 목적어로 1 회, 하위 관계의 주어로
823 회).

```
세균 hasAssociation 우울증            1 종   (Streptococcus vestibularis)
우울증 hasPos/NegAssociation 세균     45 종
공통                                   0 종
```

같은 질병 노드를 공유하면서도 연결된 미생물 집합이 완전히 분리돼 있다.

**따라서 포함관계는 데이터에서 한 번도 작동하지 않는다.** `hasPositiveAssociation ⊑
hasAssociation` 을 선언해도 기존 2,743 쌍 중 어느 것도 정제되지 않고, 556 쌍이 반대
인자 순서로 추가될 뿐이다. 논리적 모순은 아니지만 **공허하다.** 논문의
"categorized under" 는 RDF 공리가 아니라 **이름 짓기 규약**으로 읽어야 한다.

> 2026-11-03 정정. 앞서 "하위관계 목적어 ∩ 일반관계 주어 19 개 → 역관계이므로 선언하면
> 모순" 이라고 적었는데 틀렸다. 그 19 는 **개체**가 겹치는 수일 뿐 **쌍**은 0 이다
> (그 미생물들은 우울증이 아닌 다른 질병에 연결돼 있다). 모순이 아니라 공허다.

실무적 귀결은 그대로다 — `hasAssociation` 으로 질의해도 MENDA 의 pos/neg 는 걸리지
않고, 그래서 보충자료 Query 2·3 이 `npq:hasNegativeAssociation` 을 직접 쓴다.

**(2b) 부수적 발견 — 우울증의 일반관계 연결이 사실상 비어 있다.**

위 표의 "1 종" 은 §3.3 의 추론 규칙 (b)("depression 과 anxiety 가 같은 gut microbiota
를 공유하면 complications 로 추론") 에 직접 영향을 준다. 일반관계만 쓰면 우울증이
공유할 수 있는 미생물이 1 종뿐이라 그 추론이 성립할 여지가 거의 없다. 추론을
재구현하려면(§18.2) MENDA 의 하위관계 층을 반드시 함께 써야 한다 — 그런데 그 층은
`hasAssociation` 으로는 닿지 않는다.

**(3) 하위 관계가 방향을 특정하지 못한다.**

```
hasPositive ∩ hasNegative = 267 쌍
```

같은 (우울증, compound) 쌍이 긍정과 부정 양쪽에 달려 있다. pos 396 / neg 427 중
267 이 겹치므로 **compound 의 절반 이상이 방향 미정**이다.

> 판정 주의. 논문은 두 하위 관계가 배타적이라고 **적지 않았다.** MENDA 는 study 단위
> 자료이고 한 compound 가 어떤 연구에서는 상승, 다른 연구에서는 하강으로 보고될 수
> 있으므로, 양쪽에 달리는 것 자체는 KG 의 오류가 아니다. 따라서 이것을 "논문 주장 위반"
> 으로 보지 않고 **§3.3 과 §4.2.1 사이의 간극**으로 기록한다. §3.3 은 하위 관계가
> "more specific details" 를 준다고 하지만, §4.2.1 의 `E` 는 compound 마다 +1 또는 −1
> **하나**를 요구한다. KG 만으로는 그 하나를 고를 수 없다.

이것은 우리 파이프라인의 `MENDA_BOTH_TIEBREAK` 가 다루는 바로 그 문제다(§13). KG 집계본
에는 어느 쪽이 우세한지 가를 근거가 없어 MENDA 원본의 study 수로 가른다(§17.4).

#### 정리

| §3.3 주장 | 판정 |
|---|---|
| self-defined 관계 3개가 KG 에 있다 | ✅ 있다 (§17.8) |
| predefined 관계 3개가 KG 에 있다 | ✅ 있다 (§17.8) |
| 두 하위 관계가 `hasAssociation` 아래 묶인다 | ❌ 선언 0건. 방향을 무시해도 두 층의 공통 쌍이 0 이라 포함관계가 한 번도 작동하지 않는다 (모순은 아니고 공허) |
| 하위 관계가 "more specific details" 를 준다 | ⚠ 267 쌍이 양쪽. 배타성을 논문이 주장한 적은 없으므로 §3.3↔§4.2.1 간극으로 본다 |
| inferred 4,741,023 | ⚠ 배포본에 0건 (§17.1). 배포 범위 문제이지 논문 오류가 아니다 |

재실행: `python3 eval/paper_kg_stats.py`

### 17.14 "논문 결함" 주장 전수 재검증 (2026-11-03)

§17.9·§17.10·§17.12·§17.13 에서 우리 판정이 네 번 뒤집혔다. 모두 같은 유형이었다 —
**가능한 정의를 다 써보기 전에 "논문이 틀렸다" 고 단정**. 그래서 그때까지 쌓인
"논문 자체의 결함" 주장 22 개를 전부 적대적으로 다시 봤다. 각 주장에 대해
"이것을 뒤집을 수 있는 읽기가 무엇인가" 를 먼저 적고 그 읽기를 실제로 검사했다.

#### 철회 1건 — §3.1 "230 metabolites"

**철회한다. 재현된다.** 우리는 KEGG compound 전체(6,685)와 세균 대사 연결분(702)만
세보고 "어느 정의로도 230 이 나오지 않는다" 고 적었다. 놓친 읽기는 §3.1 문장 자체였다.

> "Within our dataset, we included **230 metabolites** and leveraged the compound
> ontology from KEGG compounds."

230 은 KEGG compound ontology 의 크기가 아니라 **음식에 실제로 붙은 영양소의 수**다.

```
pq:hasNutrients 의 고유 목적어 = 230        ← 논문 값과 정확히 일치
  그중 KEGG 로 owl:sameAs 된 것 = 123
```

§3.1 본문 수치는 이제 3 개 중 2 개가 정확히 일치한다 (34,250 / 230).

#### 정정 1건 — Table 1 Total 의 37,604 공백

"미등재 파일 `Food_Category`·`Disease_Bacteria` 가 그 자리" 라고 적었는데, 두 파일의
정확한 트리플 수는 40,646 이라 3,042 가 남는다. 정확한 회계는 이렇다.

```
미등재 파일          Food_Category 34,759 + Disease_Bacteria 5,887 = +40,646
MENDA 과대계상       논문 5,675 vs 배포본 2,633               = −3,042
───────────────────────────────────────────────────────────
                                                        = +37,604  ✓
```

공백의 정체는 두 효과의 합이다. 이것으로 공개 KG 총계가 정확히 맞는다.

```
논문 열의 8 개 소스(SNOMED 제외) 4,277,138 + 37,604 = 4,314,742 = 공개 KG 실측
```

#### 완화 3건

| 주장 | 뒤집는 읽기 | 조치 |
|---|---|---|
| §3.2 가 "normalized entities" 라고 쓴 수치가 정규화 결과가 아니다 | §3.2 서두는 normalization 을 **URI 부여**로 정의한다 — "ensure proper representations of entities through the use of URIs ... we **preserve** the various descriptions and attributes". 중복 병합이 아니다. 그 읽기에서는 노드 수를 세는 것이 일관된다 | ❌ → ⚠ **서술이 모호하다**. 동의어 병합 규칙을 설명한 직후에 수치를 제시해 병합 결과로 읽히지만, 자기 정의로는 모순이 아니다 |
| §3.1 "322,917 gut microbes" 가 안 나온다 | 공개 KG 는 술어별로 326,533~326,845 로 **1.2% 차이**다. NCBI taxonomy 스냅샷·필터 차이로 설명될 수 있는 크기다 | ❌ → ⚠ **미확인**. 결함 주장으로 쓰지 않는다 |
| §3.2 "3,505 mental disorders" = MENDA 2,367 + MiKG 1,138 | 정확히 일치하지만 **우연일 수 있다.** 같은 탐색에서 `versionIRI.subj(1) + hasSynonym.subj(3504) = 3505` 같은 명백한 우연도 나왔다 | 유지하되 **"가장 그럴듯한 설명"** 으로 신뢰도 표기. 근거는 두 행이 Table 1 의 mental-disease 블록이고 인접하다는 것뿐이다 |

#### 확장 1건

Table 3/4 의 compound 가 Fig. 4(c) 85 목록에 없는 것은 3 개가 아니라 **6 개**다 —
Glutamic acid(C00025), L-Threonine(C00188), Choline(C00114), Citric acid(C00158),
Lysine(C00047), Cystine(C00097).

#### 유지 (추가 검사 통과)

| 주장 | 뒤집기 시도 | 결과 |
|---|---|---|
| 우울증의 `hasAssociation` 미생물이 1 종 | SNOMED `sameAs` 상대(SCT_268621008, SCT_36923009)로도 받는가 | 포함해도 **1 건**. 유지 |
| §3.3 관계 계층이 작동하지 않는다 | 방향 무시 쌍 겹침 | **0**. 유지 (§17.13) |
| Eq.1·Eq.2 조판 오류 | 인쇄된 수식 자체를 읽어 판정 — Eq.1 은 분모의 합 범위에 `u` 첨자가 빠지고 두 제곱항이 하나의 제곱근 아래 곱으로 묶여 있다. Eq.2 는 좌변과 합 지표가 모두 `i` 다 | 읽기만으로 확정. 유지 |
| 본문 vs Fig. 5 피라미드 모순 | 두 서술을 직접 대조 | 유지 (§13b) |
| Query 1·3 의 변수 미결합 | 보충자료 원문 대조 + 결과 재구성 | 유지 (§17.2) |
| Table 1 Relation Total 140 ≠ 열 합 156 | 논문 자체 수치의 산술 | 유지 |
| Table 1 Entity Total 1,637,915 ≠ 열 합 4,995,950 | 〃 | 유지 |
| 128 의 실제 카테고리 수는 64 | 정규화 27 조합 + 구조적 집계에서 128 없음 | 유지. 단 "×2" 유도는 재구성이지 논문이 밝힌 바가 아니다 |
| `final.py` 입력 누락, `food_nutrient.csv` 절단 | repo 직접 확인 | 유지 |

#### 남은 리스크

- **128 의 "×2" 설명은 우리 재구성이다.** 64 라는 숫자는 확실하지만, 논문이 왜 128 로
  적었는지는 추정이다. 발표에서는 "카테고리 실체는 64 이고 128 은 설명되지 않는다"
  까지만 말하는 것이 안전하다.
- **3,505 도 같은 성격이다.** 일치는 정확하지만 인과는 추정이다.
- 이번 재검증으로 **22 개 중 1 개 철회, 1 개 정정, 3 개 완화, 1 개 확장**됐다.
  남은 주장들은 산술이거나 원문 대조로 확정되는 것들이다.

### 17.15 극성 주장 재검증 — KG 의 pos/neg 는 방향이 아니라 '출현 플래그' 다 (2026-11-03)

`PROBLEMS.md` #4 는 이렇게 적혀 있었다.

> §4.2.1 의 `E` 정의와 실제 데이터 의미가 반대 — `hasPositiveAssociation` 목록은
> MENDA 의 `Up`(우울증에서 증가)과 Jaccard 0.981 로 일치하는데, 논문은 이를
> "relieving" 이라 적는다.

이 주장은 **E 의 부호 전체를 좌우**하는데 적대적 검증을 거치지 않았다. 세 단계로 확인했다.

#### (1) 논문의 (+)/(−) 를 KG 로 판정할 수 있는가 — 없다

논문은 Fig. 5 · Table 3 · Table 4 · Table 5 에서 compound 14 종의 부호를 직접 적는다.
그것을 KG 의 pos/neg 와 대조했다.

```
일치 1 / 반대 0 / 양쪽 12 / KG에 없음 1
```

**14 종 중 12 종이 KG 에서 pos 와 neg 양쪽에 달려 있다.** 유일하게 명확한 것은
Sucrose(pos, 논문 +, 일치) 뿐이다. 즉 "KG 가 논문과 반대" 라고 말할 근거 자체가 없다 —
KG 는 대부분의 compound 에 대해 방향을 말하지 않는다.

#### (2) Jaccard 0.981 은 무엇을 재는가 — 방향이 아니라 출현

```
Jaccard(KG pos, MENDA 한 번이라도 Up)    = 0.981      ← 주장된 수치, 재현됨
Jaccard(KG neg, MENDA 한 번이라도 Down)  = 0.982      ← 똑같이 높다
Jaccard(KG pos, MENDA 다수결 Up)         = 0.489
Jaccard(KG pos, MENDA 한 번이라도 Down)  = 0.528      (대조)
```

0.981 은 "KG 의 positive = MENDA 에서 **한 번이라도 Up 으로 보고된 적 있음**" 이라는
뜻이다. negative 도 0.982 로 대칭이므로, 이 수치는 **positive 의 의미를 특정하지
않는다.** 다수결 방향과의 일치는 0.489 로 동전 던지기 수준이다.

그래서 MENDA 전체 500 여 종 중 267 종, 85 목록 안에서는 커버된 35 종 중 **20 종이
양쪽**이다 (pos 만 6, neg 만 9).

#### (3) 논문의 부호가 MENDA 다수결과 맞는가 — 통계적으로 판정 불가

Type1(환자 vs 대조군) 행 1,648 건에서 compound 별 Up/Down 다수를 구해 논문 부호와
대조했다.

```
Up = relieving (논문 규약) 지지   3
Up = causing              지지   6
동률 2 / MENDA Type1 에 없음 3
```

판정 가능한 9 종 중 6 종이 "Up = causing" 쪽이다. 방향은 그쪽으로 기울지만
**n=9 에 6 대 3 이면 단측 p≈0.25 로 유의하지 않다.** "반대다" 라고 단정할 수 없다.

#### 결론 — 주장을 교체한다

| | |
|---|---|
| 폐기 | "논문의 `E` 정의와 데이터 의미가 **반대**다" |
| 대체 | **KG 의 `hasPositive/NegativeAssociation` 은 방향이 아니라 study 단위 출현 플래그다.** 그래서 논문의 `E` 는 KG 로도 MENDA 다수결로도 유도되지 않는다 |

이것은 §14 의 결론("`E` 의 출처가 공개 자료에서 나오지 않는다")과 같은 말이지만,
**메커니즘이 분명해졌다.** 반대로 뒤집힌 것이 아니라, 애초에 뒤집힐 방향이 데이터에
없다.

#### 우리 파이프라인에 주는 함의 — 위험이 생각보다 작다

`MENDA_POS_MEANS_RELIEF` 토글이 직접 지배하는 것은 **방향이 명확한 15 종**(pos 만 6 +
neg 만 9)뿐이다. 나머지 20 종은 `MENDA_BOTH_TIEBREAK=orig`(MENDA 원본 study 수
다수결)가 정한다. gold 9 종의 결정 근거를 보면 더 분명하다.

| 결정 근거 | 종수 |
|---|---|
| `MENDA_both+orig` (원본 다수결 tiebreak) | 3 |
| `MENDA_both+Q2_bacteria` | 3 |
| `ontology(Sugar)` | 2 |
| `MENDA_pos` (pos/neg 라벨 단독) | **1** (Sucrose) |

**gold 9 종 중 KG 의 pos/neg 라벨만으로 결정되는 것은 1 종뿐이다.** 따라서 이 토글이
뒤집혀도 재현 수치 전체가 흔들리지는 않는다. 앞서 "E 부호 전체가 걸린 load-bearing
주장" 이라고 평가한 것은 과대평가였다.

(점검 중 발견: `knowledge_query_results.csv`(step2)와 최종 `weight.csv`(step3)의 부호가
다른 compound 가 있다. Pantothenic acid 는 step2 에서 `+1`, ProMENDA 보강 후 `−1` 이
되어 gold 실패 1 건이 된다. README 의 기술이 맞다 — 단계별 산출물을 혼동하지 말 것.)

### 17.16 "128 distinct food categories" — 논문 서술대로 구현하면 64 다 (2026-11-04)

§17.12 에서 128 = 64×2 로 설명하고 "일치" 로 처리했는데, 그 ×2 는 우리 재구성이다.
논문을 다시 읽고 서술된 방법을 그대로 구현한 뒤, 128 이 나오는 다른 경로를 전수
탐색했다.

#### 논문이 서술한 병합은 실제로 수행돼 있다

§3.2 의 예시가 `Food_Category.jsonld` 에 글자 그대로 들어 있다.

```
[Beverages]      자식 16: Soft drinks, Diet soft drinks, Milk substitutes, ...
[Baked Products] 자식 12: Rolls and buns, Yeast breads, Pizza, ...
```

> "both 'soft drinks' and 'diet soft drinks' are classified as subclasses of
> 'beverages'" / "'rolls and buns' ... categorized under 'baked products'"

즉 §3.2 의 self-defined mapping rules 는 `rdfs:subClassOf` 로 저장돼 있다. **방법은
재현 가능하다.**

#### 구조

```
카테고리 185
 ├─ 루트 64   ├─ 자식 보유 18 (FDC legacy: Dairy and Egg Products, Beverages, ...)
 │            └─ 자식 없음 46 (Popcorn, Nachos, Tap water, Human milk, ...)
 └─ 하위 121  (WWEIA 세분류: Milk whole, Soft drinks, Rolls and buns, ...)
```

각 음식은 카테고리를 **정확히 1 개** 갖는다(34,250 전부). 서술된 병합을 끝까지
적용하면 하위 121 이 부모로 흡수되어 **18 + 46 = 64** 가 남는다.

FDC 원본으로도 교차 확인했다. KG 의 34,250 개 중 현행 FDC `food.csv` 와 매칭되는
27,135 개는 **legacy 카테고리 18 개**만 쓴다 — 위의 "자식 보유 18" 과 정확히 같다.

#### 128 전수 탐색 — 나오지 않는다

부분집합 6 종 × 라벨 정규화 12 종 = **72 조합**을 돌렸다
(원문/소문자/쉼표절단/괄호제거/단수화/Other 제거/and 절단/첫단어/두단어/콜론절단/영문자만).

```
            원문 lower comma paren  sing c+s noOther noAnd first1 first2 slash alnum
전체185      185   185   174   185   185  172   185    184   138    175   180   185
루트64        64    64    61    64    64   60    64     64    59     62    64    64
하위121      121   121   114   121   121  113   121    121    91    113   116   121
부모18        18    18    18    18    18   18    18     18    18     18    18    18
고아46        46    46    43    46    46   42    46     46    41     44    46    46
```

범위 18~185. **128 은 한 번도 나오지 않는다.** 구조적 집계(type 대상 185, sameAs 보유
11, FDC 원본 645)와 그 쌍별 합/차까지 포함해도 128 을 만드는 것은 `루트 64 × 2` 뿐이다.

#### 조치

`eval/paper_kg_stats.py` 의 food categories 항목을 바꿨다.

| 정의 | 값 | 표기 |
|---|---|---|
| **§3.2 서술대로 병합 (subClassOf 롤업)** | **64** | 논문 서술의 재현 결과 |
| └ ×2 (Entity 열 계수 규약 적용) | 128 | **일치(추정)** |
| 병합 전 전체 | 185 | |
| └ §3.2 라벨 정규화 후 | 172 | |
| FDC legacy (KG 음식이 쓰는 것) | 18 | |
| FDC 원본 전체 (2026 판) | 645 | |

scorecard 도 `5/5 일치 (확정 4, 추정 1)` 로 바꿨다. 이전의 `5/5` 는 추정을 확정처럼
보이게 했다.

#### heatmap.xlsx 에는 카테고리 정보가 없다

`Food4healthKG/analyse/heatmap.xlsx` 는 142행 × 85열이고, 헤더 4행이
index / KEGG / compound 이름 / **compound 그룹**(Amino acid, Carbohydrates, ...) 이다.
데이터 138행 = 잡음 3행 + 음식 135개(§16 에서 확인). **음식 카테고리 열이 없다.**
85 compound 와 단위 계수는 여기서 역산했지만, 128 은 여기서 나올 수 없다.

#### 논문 Fig. 4(b) 범례가 답을 준다 — 17 종

논문이 카테고리를 실제로 쓴 유일한 곳은 Fig. 4(b) t-SNE 범례다. 거기 적힌 카테고리는
**17 종**이고, 전부 FDC legacy 카테고리다.

```
Dairy and Egg / Finfish and Shellfish / Fruits and Fruit Juices /
Vegetables and Vegetable Products / Nut and Seed / Legumes and Legume /
Cereal Grains and Pasta / Spices and Herbs / Fats and Oils / Poultry /
Soups Sauces and Gravies / Sausages and Luncheon Meats / Pork / Beef /
Baked Products / Sweets / Restaurant Foods
```

우리 135개 음식의 카테고리와 대조하니 **17 종이 정확히 일치**했다. 즉 논문 자신의
그림도 128 이 아니라 **17** 수준에서 동작한다. 128 은 논문의 어떤 산출물에도 쓰이지
않는다.

#### 그 과정에서 우리 파이프라인의 결함 1건을 찾아 고쳤다

대조하다 보니 우리는 **18 종**이었다. 여분 1 종은 `Strawberries, Fresh` 가 WWEIA
세분류 `6009 Strawberries` 를 그대로 달고 있었기 때문이다. `6009` 는
`Food_Category.jsonld` 에서 `9 Fruits and Fruit Juices` 의 하위다 — **§3.2 가 서술한
병합을 우리가 적용하지 않고 있었다.**

`reconstruct.py` 에 `rollup_category()` 를 추가해 `Food_Category.jsonld` 의
`rdfs:subClassOf` 를 따라 상위로 올리도록 고쳤다 (병합 규칙 121 건 로드).

```
수정 전  135개 음식 → 18 종 (legacy 17 + WWEIA 6009)
수정 후  135개 음식 → 17 종   ← 논문 Fig. 4(b) 범례와 일치
```

**영향 없음.** 전체 파이프라인 재실행 후 Spearman +0.786, Top30 18/30, Bottom30 15/30,
gold 8/9, PCA 5성분, claims 3/6 — 전부 동일하다. Strawberries 가 55/134 위라 Top30·
Bottom30 밖이고, C1a 통계만 5.87 → 5.58 로 미세하게 움직인다(판정 불변).

> ⚠ 운영 주의. `reconstruct.py` 를 단독 실행하면 `weight.csv` 가 step1 초기값으로
> 덮어써져 step2·3 이 만든 `E` 가 사라진다(Spearman +0.786 → +0.310). step1 을
> 건드리면 **반드시 `run_pipeline.py` 로 전체를 다시 돌릴 것.**

#### 발표용 문장

> 논문이 서술한 카테고리 병합은 배포 파일에 `rdfs:subClassOf` 로 구현돼 있고, 예시
> ("soft drinks"·"diet soft drinks" → "beverages")까지 일치한다. **그 병합을 끝까지
> 적용하면 64 개가 남고, 추천에 쓰인 135개 음식 기준으로는 17 종이 되어 논문
> Fig. 4(b) 범례와 정확히 일치한다.** 논문의 128 은 72 가지 조합 어디서도 나오지 않고
> 논문 자신의 그림에서도 쓰이지 않는다.

"×2" 는 말하지 않는 것이 안전하다. Entity 열에서 그 규약이 쓰인 것은 8/8 로 확정됐지만,
카테고리에도 적용됐다는 증거는 없다.

### 17.17 질병 계층 — 레포 전수 조사와 정정 (2026-11-04)

"정신 질환 쪽이 가장 약하다" 는 진단을 어떻게 고칠지 검토하다가, 앞서 내놓은 방안
두 가지가 모두 틀렸음을 확인했다. **논문과 레포만을 기준으로** 다시 전수 조사했다.

#### 철회한 방안 둘

| 방안 | 철회 이유 |
|---|---|
| **Fix 1 — 질병 식별자를 MeSH 로 통일** (SNOMED 10종을 KG 내부 `sameAs` 로 치환) | ① **정보 이득 0.** 10종 전부 SNOMED 쪽과 MeSH 쪽이 **같은 미생물 집합**을 가리킨다(새로 생기는 연결 0건). ② **논문 설계를 깨뜨린다.** 보충자료 Query 3 은 `?dissnomed owl:sameAs ?disease` 로 **두 ID 가 별개 노드임을 전제**한다. 합치면 논문 쿼리를 원문대로 돌릴 수 없다 |
| **Fix 2 — NLM MeSH 트리 다운로드** | 외부 데이터다. "논문·레포 기준" 원칙에 어긋난다 |

#### 레포 전수 조사 — 질병 계층은 없다

| 후보 | 내용 | 계층 |
|---|---|---|
| `Mental_health.jsonld` | `sameAs` 254 · `hasAssociation` 41 · `rdf:value` 275 | ❌ `rdf:value` 는 SCT 숫자 그 자체(`SCT_10087007` → `10087007`) |
| `MESH_Disease.jsonld` | label 235,539 · treeNumber 4,844 · parentTreeNumber 13,978 | ❌ **F/M 트리 0건.** 연관에 쓰인 253개 MeSH 중 트리번호 보유 **0개** |
| `Disease_Bacteria.jsonld` | 세균→질병 연관 | ❌ |
| `MiKG-JAIMS` | `mentalDisorder` 하위 10종 | ⚠ **단층뿐** |
| SNOMED CT | — | ❌ 배포 안 됨 |

MiKG 의 `subClassOf` 는 `gutMicrobiota`(48) · `mentalDisorder`(10) ·
`Neurotransmitter`(6) 로 **전부 1단계**다. "mood disorder" 같은 중간 클래스가 없다.

#### 논문의 요구를 셋으로 나누면

| 논문이 요구하는 것 | 상태 |
|---|---|
| Query 3 의 `?disclass` = "mental disorder" | ✅ **이미 해결.** MiKG 의 `mentalDisorder` 로 복원해 Table 4 **5/5** 재현 (§17.2) |
| M1 #12 "Mood disorder / developmental disorder" 구분 | ❌ **불가능.** 중간 분류가 배포본·MiKG 어디에도 없다 |
| §3.3 추론 규칙 (b) "둘 다 mood disorder + 공통 미생물" | ⚠ 상위 클래스는 MiKG 단층으로 대체 가능하나, **공통 미생물 쪽이 비어 있다** — 우울증의 `hasAssociation` 미생물이 1종뿐(§17.13) |

#### 정정된 서술

> 배포 KG 에는 질병 **계층**이 없다. SNOMED CT 는 0 트리플이고, MeSH 는 라벨 23만 개를
> 담고 있지만 연관에 쓰인 253개 질병 중 트리번호를 가진 것이 **0개**다. MiKG 가
> `mentalDisorder` 단층 10종을 제공해 Query 3 의 "mental disorder" 분류는 복원되지만
> (Table 4 5/5), §3.3 이 추론 근거로 든 **"mood disorder" 같은 중간 분류는 어떤 배포
> 자료에도 없다.** 따라서 §3.3 의 추론 규칙 (b) 는 배포본만으로 전제를 세울 수 없다.
> 추론 474만이 빠진 것과 같은 뿌리다.

#### 논문·레포 범위 안에서 할 수 있는 것

| | 방안 | 성격 | 비용 |
|---|---|---|---|
| A | **MiKG `mentalDisorder` 단층을 상위 클래스로 명시 사용** — §3.3 (b) 의 "같은 상위 분류" 조건을 10종 단위로 판정 | 재현(이미 `paper_sparql.py` 가 하는 방식의 확장) | 낮음 |
| B | **규칙 (a) 전이 추론만 먼저 구현** — subClassOf 전이는 계층이 있는 곳(KEGG compound, NCBI taxonomy)에서 성립한다. 질병 계층이 없어도 가능 | 재현 | 낮음 |
| C | MENDA 하위관계 층을 세균→질병 방향으로도 적재 | **개선 트랙 전용** | 중간 |

§18.2 는 (a) 와 (b) 를 나눠서 착수해야 한다. **규칙 (a) 는 지금 가능하고, 규칙 (b) 는
질병 계층 부재 때문에 MiKG 단층으로 근사하거나 포기해야 한다.**

### 17.18 판정 신뢰도 장치 — 절차로 고정한다 (2026-11-04)

이 조사에서 "논문이 틀렸다" 는 판정이 **일곱 번** 뒤집혔다.

| 뒤집힌 판정 | 실제 | 발견 경로 |
|---|---|---|
| Relation 4/8 | **8/8** | 지시 |
| Entity 0/8 | **8/8** | 지시 |
| §3.2 0/5 | **5/5** | 지시 |
| "계층 선언하면 모순" | 공허(쌍 겹침 0) | 지시 |
| "230 은 안 나온다" | **정확히 재현** | 전수 감사(지시) |
| "논문 수식은 꼴찌(−0.543)" | **6위(+0.602)**, 문서가 낡음 | 자체 발견 |
| "KG pos/neg 가 논문과 반대" | 방향이 아니라 출현 플래그 | 지시 |

원인은 하나다 — **정의를 좁게 잡고 곧바로 결함으로 단정**. 자체 발견은 1/7 이었다.
결심이 아니라 절차로 막는다.

#### 장치 1 — `tools/paper.py hunt` (수치 탐색기)

"논문 값이 안 나온다" 고 말하기 전에 반드시 돌린다. 레포에서 뽑을 수 있는 후보
**459개**(파일별 triples/subj/objURI/objLit/nodes/union, predicate 별 subj/obj/sum,
라벨 정규화 10변형)를 만들고 단일값·배수·쌍합으로 목표를 찾는다.

```
python3 tools/paper.py hunt 230 128 3505
python3 tools/paper.py hunt --paper        # 논문 수치 전부
python3 tools/paper.py hunt --rebuild 230  # 후보 캐시 재생성 (약 1분)
```

신뢰도를 세 등급으로 나눠 출력한다.

```
[단일 일치]              ← 가장 신뢰도 높음
[배수 일치]              ← 재구성. 확정으로 쓰지 말 것
[두 값의 합 — 1차 지표끼리] ← 검토 가치 있음
[두 값의 합 — 그 외]      ← 우연 가능
```

이미 알려진 세 사례로 검증했다.

| 목표 | 결과 |
|---|---|
| 230 | **단일 일치** `Food_Nutrient:hasNutrients.obj = 230` |
| 3,505 | **쌍합 ★** `MENDA:nodes(2,367) + Mental_health:nodes(1,138)` |
| 128 | **일치 없음** — 이 경우에만 "나오지 않는다" 고 말할 수 있다 |

#### 장치 2 — `eval/paper_data.py` (논문 수치 체크리스트 + 강제 규칙)

논문이 제시한 수치 **29개**를 전부 목록으로 고정하고 상태를 붙인다
(MATCH / MATCH_EST / MISMATCH / UNTESTED / NA).

```
total 29  MATCH 17  MATCH_EST 3  MISMATCH 6  UNTESTED 0  NA 3
```

핵심은 **코드로 강제되는 규칙**이다.

> `MISMATCH` 로 표시하려면 `HUNTED` 에 탐색 기록이 있어야 한다.
> 없으면 `_check()` 가 `AssertionError` 를 내고 **import 자체가 실패**한다.

즉 탐색을 건너뛴 결함 주장은 **파일이 로드되지 않아** 파이프라인에 들어갈 수 없다.
작동을 확인했다.

```
✔ 가드 작동: MISMATCH 인데 탐색 기록이 없다. tools/paper.py hunt 을 돌리고 HUNTED 에 적을 것
```

`MATCH_EST`(재구성 유도)를 `MATCH` 와 분리한 것도 같은 취지다 —
3,505(MENDA+MiKG)와 5,675(xlsx 행 수)는 일치하지만 인과는 추정이다.

#### 장치 3 — scorecard 에 상시 노출

```
논문 수치 체크리스트   29개 — 일치 17 · 추정 3 · 불일치 6 · 미검증 0 · 대상외 3
                      불일치는 tools/paper.py hunt 탐색 후에만 표시 가능
```

새 수치를 발견하면 `UNTESTED` 로 등록되고 scorecard 에 미검증 건수가 뜬다.
**빠뜨린 검증이 눈에 보이게 된다** — 지금까지는 그게 안 보여서 외부 지적에 의존했다.

#### 남는 한계

이 장치는 **수치 주장**만 막는다. 구조·서술 주장("관계 계층이 작동하지 않는다",
"Query 1 이 변수를 묶지 않는다")은 여전히 수작업 판단이다. 다만 그런 주장도
§17.13 처럼 **반증 가능한 측정**(방향 무시 쌍 겹침 0)으로 환원해 적는 습관을
§17.14 에서 정했다.

### 17.19 수치 자동화 — 손으로 옮겨 적지 않는다 (2026-11-04)

§17.18 이 "틀린 판정" 을 막는 장치라면, 이것은 **"맞았던 값이 낡아 거짓이 되는 것"**
을 막는 장치다. 실제로 당했다.

> "논문 수식을 그대로 구현하면 16조합 중 **꼴찌(−0.543)**" 라는 서술이 극성 교정
> (2026-09-29) 이후에도 README·PROBLEMS·REPRODUCTION 세 곳에 **약 5주간** 남아 있었다.
> 다시 돌리면 **6위(+0.602)** 다. 재실행 한 번이면 드러나는 것이었고, 발견은 우연이었다.

#### (1) scorecard 의 하드코딩 제거

`[5]` 섹션의 4줄(`Complication 7/8`, `Diet 2/7`, `Table 3 8/8`, `Table 2 6/8`)과
`[0]` 의 Triples 줄이 상수로 박혀 있었다. 출처는 `eval/paper_sparql.py` 인데 실행에
약 4분이 걸려 scorecard 가 직접 계산할 수 없었다.

그래서 `paper_sparql.py` 가 끝에 요약을 저장하게 했다.

```json
analyse/paper_sparql_summary.json
{ "kg_total": 4314742, "table1_match": 7, "table1_n": 9,
  "table2": 6, "table3": 8, "table4_raw": 5, "table4_joined": 4,
  "t5_complication": 7, "t5_diet": 2, "t5_diet_loose": 5 }
```

scorecard 는 이것을 읽는다. 캐시가 없으면 값을 지어내지 않고 **"먼저 실행하라" 고 말한다.**
이로써 scorecard 안의 손으로 적은 수치는 **0개**가 됐다.

#### (2) `python3 tools/scorecard.py --check-docs`

문서에 인용된 수치를 정규식으로 긁어 **현재 값과 대조**한다. 등록 10건.

| 문서 | 항목 |
|---|---|
| README | Spearman · Top30 · Bottom30 · E 방향 · 측정 밀도 · gold · KG 총 트리플 |
| PROBLEMS | Spearman |
| REPRODUCTION | Table 5 Complication · Diet |

```
$ python3 tools/scorecard.py --check-docs
  일치 10 / 불일치 0 / 확인불가 0   (등록 10건)
```

고의로 틀린 값을 넣어 검출을 확인했다.

```
$ sed -i 's/\*\*+0.786\*\*/**+0.999**/' README.md
$ python3 tools/scorecard.py --check-docs
  ✘  README.md        spearman   문서 "+0.786" 자리에 "+0.999" — 현재 "+0.786"
  ⚠ 문서를 고치거나, 값이 바뀐 이유를 기록할 것     (exit 1)
```

**exit code 1** 을 내므로 훅이나 CI 에 걸 수 있다.

세 가지 상태를 구분한다.

| 상태 | 뜻 |
|---|---|
| 일치 | 문서 값 = 현재 값 |
| **불일치** | 문서가 낡았다 — "꼴찌" 가 이 경우였다 |
| **확인불가** | 정규식이 안 맞는다 = 문서 표현이 바뀌었다. 이것도 신호다 |

#### 한계와 다음

- 등록 10건은 **자주 바뀌고 자주 인용되는 것**만 골랐다. 문서의 모든 수치가 아니다.
- `tools/sweep.py formula`(= "꼴찌" 의 출처)는 아직 캐시를 쓰지 않아 등록하지 못했다.
  같은 방식으로 요약을 저장하게 하면 등록할 수 있다. **남은 일 1건.**
- 검사는 수치만 본다. 서술("꼴찌" 라는 **단어**)은 못 잡는다. 그래서 문서에서는
  순위·등수도 숫자로 적는 편이 안전하다.

### 17.20 §3.3 추론 규칙 (a) 재구현 — 논문 4,741,023 의 51.4% (2026-11-04)

§18.2 의 첫 조각. 논문이 기여의 35% 로 내세운 추론 트리플을 **배포 KG 에서 직접
생성**해 수를 대조했다. 배포본에는 추론 트리플이 0건이므로(§17.1) 우리가 만들어야 한다.

#### 논문이 적은 규칙

> "considering that both saturated and unsaturated fatty acids are subclasses of
> fatty acids and fatty acids are a subclass of lipids, we can logically infer that
> **instances** of saturated fatty acids also belong to the classes of fatty acids
> and lipids."

두 가지를 말한다.

| | 규칙 |
|---|---|
| (a1) 계층 전이 | `A ⊑ B`, `B ⊑ C` ⊢ `A ⊑ C` |
| (a2) 타입 전파 | `x type A`, `A ⊑ B` ⊢ `x type B` |

배포 KG 의 계층 간선은 `rdfs:subClassOf` 와 `npq:isChildOf`(NCBI 계통수) 두 가지다.
둘 다 계층으로 쓴다.

#### 결과

```
계층 간선 406,438개 / 노드 369,855개 (다부모 36,526 = 9.9%, 즉 트리가 아니라 DAG)

(a1) 계층 전이로 생성    1,749,977
(a2) 타입 전파로 생성      686,426
───────────────────────────────────
합계                     2,436,403   논문 4,741,023  (51.4%)
```

#### 소스별 (a1) 기여 — 논문 설명과 실제가 다르다

| 소스 | 생성 | 비중 |
|---|---|---|
| `Bacteria_Ontology` (NCBI 계통수) | 1,574,035 | **90%** |
| `Food_Chinese` | 137,898 | 7.9% |
| `Food_Ontology` | 36,139 | 2.1% |
| `KEGG_Compound` | **1,858** | **0.1%** |
| `Food_Category` | 45 | — |
| `Disease_Bacteria` | 2 | — |

논문이 §3.3 에서 든 예시는 "포화지방산 ⊂ 지방산 ⊂ 지질", 즉 **KEGG compound 계층**인데
실제 생성량의 **0.1%** 에 불과하다. 추론 트리플의 정체는 사실상 **NCBI 계통수의 조상
닫힘**이다. 서술과 실제 기여원이 다르다 — §3.2 의 "normalized" 와 같은 성격의 괴리다.

#### 나머지 48.6% 는 어디서 오나

규칙 (b)(공통 미생물 → complication)로는 그만한 양을 만들 수 없다. 전제가 비어 있기
때문이다(§17.17) — 질병 계층 0, 우울증의 `hasAssociation` 미생물 1종. Table 5 의
complication 8건 규모다.

가장 그럴듯한 설명은 **SNOMED CT** 다. 배포본에서 빠진 4,291,226 트리플에 63개
relation 의 계층이 들어 있고, 그 조상 닫힘이면 230만 규모가 충분히 나온다.
**확인할 수는 없다** — SNOMED 이 없기 때문이다.

#### 우리 파이프라인에 주는 함의

`knowledge_query.py` 의 `ontology_rules` 는 손으로 적은 부모-자식 매핑 14종이고 코드
주석에도 "KG 의 subClassOf 체인을 **모사한**" 임시방편이라고 적혀 있다. 이제 KEGG
compound 계층에서 **1,858건의 실제 전이 관계**가 나옴을 확인했으므로, §18.3(E 보강)에서
수동 매핑을 이 계층으로 대체할 수 있다. **논문 근거가 있는 교체**다(§3.3 규칙 (a)).

#### 구현 메모

첫 구현은 스택 메모이제이션이었는데 재방문마다 후보를 다시 계산해 사실상 2차였고
**20분 넘게 끝나지 않았다.** 위상정렬(Kahn)로 바꿔 `O(V+E+Σ|anc|)` 가 되어 몇 분에
끝난다. 순환에 걸린 노드는 처리된 부모만으로 근사한다.

```
python3 -c "import sys; sys.path.insert(0,'eval'); import paper_kg_stats as K; K.inference()"
```

결과는 `analyse/paper_eval_inference.json` 에 저장되고 scorecard `[0]` 에 표시된다.

### 17.21 §4.1 "엔티티 교체 가능" 주장 실증 (2026-11-04)

논문은 세 쿼리 모두 엔티티를 바꿀 수 있다고 적는다.

| 쿼리 | 논문 서술 |
|---|---|
| Query 1 | "the entities 'vitamin B' and 'milk or egg products' **can be replaced** with other similar entities" |
| Query 2 | "'depression' **can be replaced** with other mental disorders of interest" |
| Query 3 | "**any** mental disorder of interest can replace 'depression'" |

우리 `eval/paper_sparql.py` 는 질환 필터가 `filter regex(?depressionname,
"depression|depressive|depressed")` 로 하드코딩돼 있어 이 주장을 검증한 적이 없었다.
인자로 빼고 실제로 바꿔 돌렸다.

```
python3 eval/paper_sparql.py replaceable
```

#### 결과 — 쿼리마다 갈린다

```
Q2·Q3 가 요구하는 hasPositive/NegativeAssociation 을 가진 질환: 1종
   Major depressive disorder

MiKG 의 mentalDisorder 하위 10종 중 조건 만족: **1종**
   O Depressive disorder
   X Anxiety / Autistic / Bipolar / Cognition / Eating /
     Learning / Personality / Sexual dysfunction / Sleep

Q1 — 영양소·음식 교체
   Vitamin B × Egg/Milk       5행(limit 5)  0.1s   교체 가능
   Vitamin C × Apple/Orange   5행(limit 5)  0.0s   교체 가능
   Calcium   × Cheese/Yogurt  5행(limit 5)  0.0s   교체 가능
```

| 논문 서술 | 판정 |
|---|---|
| Q1 영양소·음식 교체 | ✅ **사실** |
| Q2 질환 교체 | ❌ **거짓** — 10종 중 1종 |
| Q3 "any mental disorder" | ❌ **거짓** — 같은 이유 |

**Q2·Q3 는 `hasPositive/NegativeAssociation` 을 가진 질환에서만 돌아가는데, 배포 KG 에서
그 관계를 가진 질환은 `Major depressive disorder` 하나뿐이다.** 다른 질환으로 바꾸면
0행이다. §17.13 에서 "pos/neg 의 주어가 D003865 한 노드" 라고 측정한 것의 직접적
귀결이고, 이제 논문 주장에 대한 **반증 가능한 형태**가 됐다.

#### 덤 — Query 1 은 계산적으로도 실행 불가능하다

`count(*)` 로 전체 해를 세려 했더니 **20분 넘게 끝나지 않아 중단**했다(100% CPU).
원인은 이미 아는 결함이다 — `?milkunit` 이 `?milk` 에 묶이지 않아 "모든 영양소-무게
노드 × 모든 milk 음식" 으로 조인이 터진다. `limit 5` 로는 0.1초다.

**즉 Query 1 의 변수 미결합은 값만 틀리게 하는 것이 아니라 쿼리를 사실상 실행 불가능하게
만든다.** Table 2 가 8행만 실린 것도 이것으로 설명된다.

#### 구현 메모

- `with_disorder()` · `with_nutrient()` · `Q_DISORDERS` · `replaceable()` 을
  `eval/paper_sparql.py` 에 추가했다(새 파일 없음). 결과는
  `analyse/paper_sparql_replaceable.json` 에 저장되고 scorecard `[5]` 에 표시된다.
- 보충자료 **Query 1 원문이 코드에 없었다.** `table2()` 는 결함 분석용 자체 질의를
  쓰기 때문이다. 이번에 원문을 `Q1` 상수로 넣었다.
- 부록 Query 1 의 SELECT 절은 `?Eggname?Milkname?Nutrientname` 로 대문자로 시작한다.
  SPARQL 변수는 대소문자를 구분하므로 그대로면 투영 변수가 전부 미바인딩이다.
  **Word 자동 대문자화 흔적일 수 있어 결함으로 단정하지 않고**, 실행 가능한 소문자형을
  쓴다고 코드 주석에 남겼다.

### 17.22 Table 3 "8/8" 이 가리고 있던 것 (2026-11-04)

§17.2 에서 "Query 2 → Table 3 **8/8**" 이라고 보고했다. 틀린 수치는 아니지만 세 가지를
가린다. `table3()` 이 그것들을 함께 출력하도록 고쳤다.

#### 검증하는 것 — 느슨하지 않다

```
음식 패턴 ∧ compound 패턴 ∧ |무게 − 논문값| < 0.06 ∧ 세균 정확히 일치
```

네 요소를 모두 본다. 소시지 행이면 `L-Threonine 500 mg/100g` + `Bacteroides ovatus`
가 다 맞아야 통과한다. 논문이 강조한 **음식 → 영양소 → 미생물 경로는 재현된다.**

#### (1) 원문 쿼리만으로는 **5/8**

```
원문 Query 2            5/8   (Bacteroides fragilis·ovatus·vulgatus, Bifidobacterium longum)
세균 조건 pos→neg 변경   3/8   (Enterococcus faecalis, Adlercreutzia equolifaciens)
```

Query 2 는 `?depression npq:hasPositiveAssociation ?bac` 으로 **세균이 우울증과 양성
연관**일 것을 요구하는데, Table 3 의 0~2 행 세균은 KG 에서 **음성 연관**이다. 조건을
뒤집어야 나온다.

#### (2) 논문의 (+)/(−) 부호는 쿼리에서 유도되지 않는다 ← 가장 중요

Query 2 는 `?depression npq:hasNegativeAssociation ?compound` 로 **neg 목록만** 뽑는다.
그런데 Table 3 의 compound 는 **8/8 이 KG 에서 pos·neg 양쪽**에 있다.

| compound | 논문 | KG |
|---|---|---|
| Glutamic acid / Glycine / Citric acid / Ascorbic acid | **(+)** | pos·neg 양쪽 |
| L-Threonine / Choline | **(−)** | pos·neg 양쪽 |

그래서 "neg 만 뽑는" 쿼리가 논문이 (+) 로 적은 것까지 반환한다. **Table 3 의 부호는
쿼리 결과가 아니라 논문이 따로 붙인 것**이고, 출처가 배포 자료에 없다.

§17.15 에서 측정한 "KG 의 pos/neg 는 방향이 아니라 study 단위 출현 플래그" 의 직접적
귀결이다. 즉 Case Study 2 의 간판 주장인

> "L-threonine ... has the potential to **aggravate** the symptoms of depression"

의 **인과 방향은 배포 KG 로 뒷받침되지 않는다.** 기전(경로)은 재현되지만 방향은 아니다.

#### (3) 매칭된 음식 라벨은 논문 표기와 다르다

이제 어느 라벨로 통과했는지 출력한다.

| 논문 표기 | 실제 매칭된 FDC 라벨 |
|---|---|
| Beef sausage | `BEEF BREAKFAST SAUSAGE, BANQUE...` |
| Lettuce, Romaine | `Vitamin C, Lettuce, Romaine, f...` |
| Kiwi | `Kiwi, Pass 2, Region 2, n/a, Y` |
| Grape juice | `Grape juice, white, with added` |
| FLOUR, SOY | `FLOUR, SOY (DEFATTED)` |

`"Beef sausage"` 라벨도 KG 에 1건 있지만 500 mg/100g 를 만족하는 것은
`BEEF BREAKFAST SAUSAGE` 쪽이다. 부당한 완화는 아니나 **논문 표기 그대로는 아니다.**

#### 정정된 서술

> Query 2 → Table 3 은 (음식, 영양소, 무게, 미생물) 4요소 기준 8/8 로 재현된다. 다만
> **원문 쿼리만으로는 5/8** 이고, **(+)/(−) 부호는 8/8 이 KG 의 pos·neg 양쪽에 있어
> 쿼리에서 유도되지 않는다.** 매칭된 음식 라벨도 논문 표기가 아니라 FDC 원라벨이다.

---

### 17.23 Table 4 "Intellectual disability" — 논문 내부 표기 불일치 (2026-11-04)

Table 4 의 2·3 행은 질병명을 **"Intellectual disability"** 로 적는다. 우리 `TABLE4` 는
이를 MiKG 의 **`Learning`**(Learning disorder) 으로 매칭해 왔다. 서로 다른 MeSH 개념이라
"임의 완화 아니냐" 는 의심이 들어 §17.18 절차대로 전수 조사했다. **결론은 반대였다 —
매칭이 옳고 논문 Table 4 의 표기가 어긋난다.**

#### (1) `D008607` 은 공개 KG 에서 도달 불가능한 고립 노드

| 확인 | 결과 |
|---|---|
| `MESH_Disease.jsonld` 에 `D008607` 노드 | **있음** (`rdfs:label "Intellectual Disability"@en` + treeNumber 2개뿐) |
| `D008607` 의 `owl:sameAs` | **0건** — SNOMED·MiKG 어느 쪽에도 붙지 않는다 |
| `D008607` 의 세균 연결 | **0건** (`Mental_health` 의 질병 객체 20개에 없음) |
| 라벨 `intellectual|mental retard` 유사 노드 220건 | 전부 MeSH 보조개념(C 번호) 희귀증후군, 세균 연결 0건 |
| `SCT_1855002` 의 라벨 | 없음. `owl:sameAs D007859` ("Learning Disabilities") 뿐 |

Query 3 의 어떤 조인 경로로도 `D008607` 에는 닿을 수 없다.

#### (2) KG 가 실제로 담은 것은 `D007859`

`Mental_health.jsonld` 는 주체가 **NCBI taxon id** 다(Disease_Bacteria 가 아니다 —
처음 조사에서 파일을 잘못 잡아 0건이 나왔다).

```
D007859 (Learning Disabilities)  등장 32회      SCT_1855002  등장 32회
  entity/562  (Escherichia coli)        → 둘 다 있음
  entity/1590 (Lactobacillus plantarum) → 둘 다 있음
  D008607 → 둘 다 없음
```

Table 4 2·3 행의 세균이 바로 이 둘이다.

#### (3) 결정적 근거 — 논문 자신의 Table 5

같은 저자가 **같은 추론 결과를 Table 5 에서는 "Learning disabilities" 로 적는다.**

| Table 5 | Question | Food4healthKG | Table 4 와의 대응 |
|---|---|---|---|
| No 9 | **Milk** and **Learning disabilities** | alpha-Tocopherol | Table 4 2·3 행의 `MILK, 2%` 와 같은 food–disease 쌍 |
| No 2 | **Learning disabilities** and autism | *Escherichia coli* | Table 4 2 행의 세균과 동일 |
| No 5 | **Learning disabilities** and depression | Bacillus cereus | — |

Table 5 No 9 는 우리 `table5()` 에서도 **O 로 재현된다**(Milk 중 alpha-Tocopherol 기록
있는 음식 66, 성분→세균→Learning disabilities 경로 1). 즉 **Table 5 와 KG 가 일관되고,
Table 4 와 Fig 3 의 질병명만 어긋난다.**

#### 판정

- Table 4 재현은 **원문대로 5/5**. `'Learning'` 매칭은 논문 Table 5 가 직접 뒷받침한다.
- 확정 결함 1건: **Table 4·Fig 3 의 질병명 표기가 논문 Table 5·배포 KG 와 불일치**.
  근거가 전부 논문 내부와 배포 자료 안에 있어 §17.18 기준을 충족한다.
- 근거는 `eval/paper_sparql.py` 의 `TABLE4` 주석에 박아 두었고, `table4()` 가
  `질병명 불일치 2/5` 를 매 실행 출력한다.

#### 함께 드러난 것 — Table 4 의 나머지 세 가지

1. **원문 Query 3 는 0행이다.** 위 5/5 는 SNOMED 이름을 MiKG 로 보충한 결과다
   (공개 KG 에 SNOMED 라벨·계층이 없다, §17.3).
2. **(+)/(−) 부호는 Table 3 과 똑같이 유도되지 않는다** — Table 4 의 compound 도
   KG 에서 pos·neg 양쪽에 속한다 (§17.22).
3. **"complication 추론" 자체는 검증되지 않았다.** 우리는 세균을 공유하는 질병 쌍을
   확인할 뿐, 논문 §3.3 의 규칙 (b) 는 미구현이다 (§17.20).

### 17.24 §3.3 규칙 (b) 합병증 추론 — 구현과 그 결과 (2026-11-04)

§17.20 에서 규칙 (a)(전이·타입 전파)만 구현했고 (b) 는 미구현으로 남겨 뒀다. 이번에
구현했다. 실행: `python3 eval/paper_kg_stats.py complication`.

> "when observing that depression and anxiety are both **mood disorders** with
> **shared associations with the same gut microbiota**, we can infer an implicit
> relationship between depression and anxiety as 'complications'" (§3.3)

조건 두 개다 — **(1) 같은 gut microbiota 공유**, **(2) 같은 상위 분류**.

#### 구현상 맞춰야 했던 세 가지

- `Mental_health.jsonld` 는 **주어가 NCBI taxon id**(세균)이고 목적어가 질병이다.
  처음에 `Disease_Bacteria.jsonld` 를 뒤져 0건이 나왔다 (§17.23 과 같은 실수).
- 질병 식별자가 셋으로 흩어져 있다. MiKG 는 MeSH 를 `/mesh/2020/D...`, 배포 KG 는
  `/mesh/D...` 로 쓴다. MiKG 네임스페이스는 `ztonebv.com/MiKG#` 다. `owl:sameAs` 로
  union-find 병합했다.
- **질병이 두 파일에 나뉘어 있다.** 정신질환 10종은 `Mental_health.jsonld`, 나머지
  241종은 `Disease_Bacteria.jsonld` 다. 처음 측정에서 전자만 보고 "Parkinson·Alzheimer
  는 KG 에 없다" 고 적었는데 **틀렸다** — `Parkinson Disease`(D010300, 세균 52종),
  `Alzheimer Disease`(D000544, 세균 2종) 둘 다 후자에 있다. 라벨 출처도 다르다(MiKG
  영어 라벨 vs MeSH `rdfs:label`). 아래 수치는 두 파일을 모두 포함한 것이다.

#### 결과 — 두 범위로 나눠 센다

```
세균 연결이 있는 질병            250종  (정신질환 10 + 그 밖 240)

범위 A  정신질환 10종만 (조건 (2) 를 지킨 경우)
        조건 (1) 세균 공유    45/45 쌍   → 트리플 90개      ← 완전그래프
범위 B  질병 250종 전체 (조건 (2) 를 뺀 경우)
        조건 (1) 세균 공유 3,776/31,125 쌍 → 트리플 7,552개
```

**조건 (1) 은 정신질환 안에서 변별력이 0 이다.** 가능한 45쌍이 **전부** 세균을
공유한다(공유 23~114종). 이 조건만으로는 모든 정신질환이 서로의 합병증이 된다.

**조건 (2) 도 변별하지 못한다.** MiKG 계층이 평평하기 때문이다 — `mentalDisorder`
바로 아래 10개 리프뿐이고 논문이 말한 "mood disorders" 같은 **중간 층이 없다**. MeSH
`treeNumber` 로 보완할 수도 없다(이 10종 중 2종만 treeNumber 를 가진다). 즉 조건 (2) 는
"정신질환인가" 라는 이분 필터로만 작동하고, 그 안에서는 아무것도 걸러내지 않는다.

#### 논문 표와 대조

| 논문 | 조건(1) | 조건(1)+(2) |
|---|---|---|
| Table 5 Complication 8행 | **8/8** | **5/8** |
| Table 4 Complication 3행 | **3/3** | **3/3** |

**8행 전부 조건 (1) 로 생성된다.** 그런데 그중 3행(`Parkinson disorder` ×2,
`Alzheimer Disease` ×1)은 **정신질환이 아니어서 논문이 적은 조건 (2)
("both mood disorders")를 위반한다.** 논문은 자기가 서술한 규칙보다 넓은 규칙으로
Table 5 를 만들었다 — 또는 규칙 서술이 실제 구현을 좁게 적었다.

#### 추론 트리플 총계에 미치는 영향 — 거의 없다

```
규칙 (a)   2,436,403      (§17.20)
규칙 (b)   90 ~ 7,552     ← 범위 A ~ B
논문 주장  4,741,023
```

가장 넓게 잡아도 7,552 개다. §17.20 에서 남은 2,304,620 개의 간극을 설명하지 못한다.
논문의 "4,741,023 Inferred" 는 여전히 재현되지 않으며, 그 대부분은 규칙 (a) 의
적용 범위(배포되지 않은 SNOMED 계층)에 있다고 보는 것이 타당하다.

### 17.25 Table 5 Diet 7행 중 5행이 성립하지 않는 이유 (2026-11-04)

`table5()` 엄격 기준으로 Diet recommendation 은 **2/7** 이다(묶지 않으면 5/7). 왜인지
분해했다. 실행: `python3 eval/paper_kg_stats.py coverage`.

음식도 성분 노드도 전부 KG 에 **있다.** 끊기는 곳은 두 군데였다.

#### 원인 1 — 아미노산 측정이 비타민의 1/20 수준이다 (4행)

| 성분 | 분류 | 그 성분이 >0 으로 기록된 음식 수 |
|---|---|---|
| Cystine | 아미노산 | 95 |
| Lysine | 아미노산 | 254 |
| Threonine | 아미노산 | 255 |
| Glutamate | 아미노산 | 261 |
| Ascorbate | 비타민 | 5,085 |
| alpha-Tocopherol | 비타민 | 7,114 |
| Niacin | 비타민 | 8,007 |

아미노산 최대 261 vs 비타민 최소 5,085 — **19.5배**. 그래서 Garlic(음식 56종),
Coffee(143), Sweets(27), Egg products(1,314) 안에 Threonine·Cystine 기록이 **0건**이다.
음식이 없어서가 아니라 그 음식들에 아미노산이 측정되지 않았다.

**논문도 이 사실을 알고 있다.** §4.2.3 에서 "there are some nonsignificant differences
in certain **amino acids** and lipids, which could be attributed to **missing values in
the original data**" 라고 적는다. 같은 결손이 Table 5 의 Diet 행 4개를 무너뜨린다.

#### 원인 2 — 대사 세균과 질병연관 세균이 거의 겹치지 않는다 (1행, Lettuce)

Lettuce 는 측정이 있다(Niacin 기록 음식 61종). 끊긴 곳은 **성분 → 세균 → 질병** 이다.

```
Niacin(C00253) 을 대사하는 세균   3종  Burkholderia contaminans, Alcaligenes aquatilis,
                                        Bordetella hinzii
anxiety 에 연결된 세균           36종  (위 3종은 포함되지 않는다)
```

구조적인 문제다.

```
hasMetabolites 를 가진 세균 (KEGG 대사)   201
hasAssociation 를 가진 세균 (질병 연관)   764
둘 다 가진 세균                            72     ← 4단 경로를 완성할 수 있는 전부
```

KEGG 쪽 세균(환경·병원성 종 포함)과 MiKG/MENDA 쪽 장내세균이 서로 다른 집합이라,
**음식–성분–세균–질병** 네 단계를 잇는 통로가 72종으로 좁다.

#### 평가 방식에 대한 함의

Table 5 의 Diet 행이 "묶지 않으면 5/7" 로 올라가는 것은 KG 가 그 경로를 담고 있어서가
아니라, **변수를 묶지 않은 쿼리가 아무 음식의 성분량이나 끌어오기 때문**이다 (Table 2 의
`?milkunit` 미결합과 같은 결함, §17.2). 엄격히 묶으면 2/7 이다.

### 17.26 `table5()` 7/8 과 `complication()` 8/8 의 조정 (2026-11-04)

두 코드 경로가 Table 5 Complication 에 다른 수를 냈다. 조사해 보니 **서로 다른 질문을
재고 있었고**, 그 과정에서 결함 1건과 우리 쪽 버그 2건이 나왔다.

#### 세 가지 기준은 다른 질문이다

| 기준 | 묻는 것 | 결과 |
|---|---|---|
| 조건 (1) | 규칙 (b) 가 그 쌍을 **생성할 수 있는가** | 8/8 |
| 조건 (1)+(2) | 논문이 적은 분류 조건까지 지키는가 | 5/8 |
| 근거 세균 | 논문이 Table 5 에 적은 **그 세균**이 두 질병에 붙는가 | **7/8** |

맨 아래가 `table5()` 의 기준이다. 이제 `complication()` 도 같이 출력하며 **7/8 로 일치한다.**

#### 확정 결함 — Table 5 #1 의 근거 세균이 KG 와 맞지 않는다

논문은 `Parkinson disorder`–`depression` 합병증의 Food4healthKG 근거로
**Streptococcus mutans** 를 든다. 배포 KG 에서 taxon 1309(S. mutans)가 붙는 질병은
8개이고 그중 Parkinson(D010300)은 있지만 **우울증은 없다.** 두 질병을 실제로 잇는
세균은 4종(`1590` L. plantarum, `1598`, `1689`, `817`)이고 S. mutans 는 거기 없다.
Table 5 의 8행 중 유일하게 근거가 KG 로 뒷받침되지 않는 행이다.

#### 조정 과정에서 고친 우리 쪽 버그 2건

1. **MENDA 하위관계를 빼먹었다.** 우울증 연결이 두 경로로 들어온다 — MiKG 의
   `hasAssociation`(세균→질병)과 MENDA 의 `hasPositive/NegativeAssociation`
   (질병→세균, 방향이 반대, §17.13). §3.3 이 "subrelations ... both categorized under
   the main relation hasAssociation" 이라 적었으므로 규칙 (b) 의 입력에 둘 다 넣는 것이
   맞다. 이걸 빼면 `Bifidobacterium longum`–우울증처럼 MENDA 로만 이어진 연결을 놓친다.
2. **세균 노드 판별을 파일에 의존했다.** `isChildOf` 유무로 골랐는데 계통수가
   `Bacteria_Ontology.trig` 에 있어 `.jsonld` 만 보면 놓친다. URI 패턴
   (`/entity/<숫자>`)으로 바꿨다.

#### 드러낸 가정 — 우울증 노드가 둘이다

배포 KG 에 우울증 노드가 **둘이고 그 사이에 `owl:sameAs` 가 없다.**

```
D003865   MENDA 가 하위관계로 쓰는 쪽
D003866   MiKG 가 hasAssociation 으로 쓰는 쪽 (= MiKG#Depressive-disorder)
```

둘을 한 개념으로 볼지는 KG 가 정해 주지 않는다. `table5()` 는 예전부터 손으로 합쳐
왔는데 근거를 적지 않았다. 이제 `complication()` 의 `MERGE_ASSUMED` 상수로 **가정임을
명시**하고 양쪽이 같은 병합을 쓴다.

### 17.27 §5.1 평가 방식 자체의 문제 (2026-11-04)

지금까지는 "논문의 평가 지표로 우리 재현을 채점" 해 왔다. 이번에는 **그 지표 자체**를
본다. 실행: `python3 eval/paper_data.py audit`. 아래 수치는 전부
`eval/paper_data.py` 의 `TABLE1`(Supplement Table 1)·`TABLE5` 에서 계산된다 — 손으로
옮겨 적은 값이 없다.

#### ① 0.95/0.9/0.95 는 정확도가 아니라 전문가별 동의율이다

Supplement Table 1 의 V0/V1/V2 열 합이 **19/18/19 → 0.95/0.90/0.95** 로 논문 수치와
정확히 일치한다. 즉 이 열은 "전문가 i 가 보기에 KG 답이 맞다" 는 플래그다.

논문은 이렇게 적는다.

> "The accuracy of our results against the **gold standard answers of the three
> experts** are found to be 0.95, 0.9, and 0.95, respectively."

그런데 **단일 gold standard 는 존재하지 않는다.** 전문가 3인의 판정이 4문항에서 갈리고
(아래), 논문은 그 갈림을 합의로 수렴시키지 않은 채 **각 전문가와의 일치율 세 개**를
따로 보고한다. "accuracy ... against the gold standard" 라는 표현이 실제 계산과 맞지
않는다.

#### ② 그 테스트는 포화되어 변별력이 거의 없다

```
vsum 분포            {3: 16, 2: 4, 1: 0, 0: 0}
3인 만장일치          16 / 20
2인 이상이 오답으로 본 문항   0 / 20      ← 하나도 없다
전문가 쌍별 일치      V0-V1 17, V0-V2 18, V1-V2 17  / 20
```

**다수가 "KG 가 틀렸다" 고 본 문항이 단 하나도 없다.** 20문항 중 16문항은 만장일치
정답, 나머지 4문항도 2:1 이다. 이런 분포에서는 어떤 KG 든 0.9 이상이 나온다 — 질문
집합이 시스템을 변별하지 못한다.

전문가 간 일치도(IAA)는 **논문에 보고되지 않는다.** 위 쌍별 일치(17~18/20)를 보면
전문가끼리도 완전히 일치하지는 않는데, 그 불일치가 측정의 불확실성으로 반영되지 않았다.

질문 20개는 저자가 직접 설계했고(§5.1), 선정 절차나 난이도 통제에 대한 기술이 없다.

#### ③ "15 inferred results" 중 7건은 추론 산출물이 아니다

논문은 이렇게 적는다.

> "We randomly select 15 **inferred results** from our knowledge graph, as shown in
> Table 5."

그런데 Table 5 의 Attributes 열 구성은

```
Complication         8건     ← §3.3 규칙 (b) 의 산출물
Diet recommendation  7건     ← §4.1 쿼리 결과
```

Diet recommendation 행은 추론이 아니라 **쿼리 결과**다. 추론 검증을 표방한 평가에서
절반 가까이가 추론이 아니다. 그리고 "randomly select" 라고 했으나 모집단이 무엇인지
적혀 있지 않다 — 규칙 (b) 의 산출 모집단은 정신질환 45쌍 / 질병 전체 3,776쌍인데
(§17.24), 뽑힌 8건 중 3건은 조건 (2) 를 위반한다.

#### ⑥ "11 confirmed" 는 프레이밍이다

```
confirmed 11 / unknown 3 / contradicted 1      (총 15)
확인율 0.73      unknown 을 분모에서 빼면 0.92
```

논문 서술은 "only one is contradicted ... while 11 are confirmed" 로, 분모를 명시하지
않는다. unknown 3건을 포함하면 **73%** 다. 레이블링은 저자 본인이 PubMed 를 검색해
수행했고 블라인드가 아니며 음성 대조군이 없다 — 지지 문헌을 찾는 방식은 구조적으로
지지 쪽으로 기운다. §5.1 도 "the results labeled as 'unknown' ... should not be
considered conclusive contradictions" 라고 적어 unknown 을 실패로 세지 않는 쪽을
택한다.

#### ⑦ 추천 알고리즘(§4.2)에는 평가가 없다 ← 가장 큰 공백

논문의 두 평가 방법이 덮는 범위는 이렇다.

| 평가 | 대상 |
|---|---|
| 방법 1 (전문가 20문항) | 지식 **질의** 결과 |
| 방법 2 (문헌 15건) | 지식 **추론** 결과 |
| — | **추천 알고리즘** |

§4.2 의 food recommendation 은 논문이 내세운 주 응용인데(초록: "particularly in
providing convincing food recommendations"), **어느 평가에서도 채점되지 않는다.**

- Fig 4(c) 의 성분 차이 분석은 추천군/비추천군의 **기술 통계**이지 정답 대비 검증이 아니다.
  추천 결과로 나눈 두 집단의 성분이 다르다는 것은 알고리즘이 성분을 썼으니 당연하다.
- `K = 30` 의 근거가 없다.
- 추천 순위의 정답(ground truth)이 정의되지 않아, 정밀도·재현율·순위 상관 같은 지표가
  하나도 계산되지 않았다.

**이것이 우리 §16 지표의 위치를 결정한다.** 우리가 쓰는 Spearman·Top/Bottom-K 겹침·NDCG 는
**논문에 없는 지표를 우리가 도입한 것**이다. 논문 재현의 기준으로 쓸 수 없고(비교 대상이
없으므로), §18 개선안의 자체 기준으로만 쓸 수 있다. 재현 점수와 분리해 둔다.

### 17.28 E 의 빈칸 16종을 pos/neg 로 채울 수 있는가 — 없다 (2026-11-05)

§4.2.1 은 `E ∈ {+1, −1}` 을 요구하는데 우리 재현은 85종 중 **16종이 0** 이다. 이것을
KG 의 `hasPositiveAssociation`/`hasNegativeAssociation` 으로 채울 수 있는지 끝까지
확인했다. 재현 가능: `python3 tools/paper.py improve`.

#### (1) KG 에는 study 다중성이 없다

`MENDA_Depression.jsonld` 는 그래프 1개, 노드 513개이고 pos/neg 는 **질병 노드
`D003865` 하나에 긴 목록 두 개**로 들어 있다.

```
hasPositiveAssociation  1건 (396 compound)
hasNegativeAssociation  1건 (427 compound)
양쪽에 들어간 compound    268 / 합집합 512
```

RDF 집합 의미라 **study 별 횟수가 남아 있지 않다.** §17.15 에서 "방향이 아니라 study
단위 출현 플래그" 라고 판정한 것의 파일 수준 근거다. 다수결을 KG 안에서 복원할 방법이
없다.

#### (2) 빈칸 16종은 모호한 게 아니라 **데이터가 없다**

| 확인 | 결과 |
|---|---|
| KG pos/neg 목록에 있는가 | **15종 없음**, 1종(Hydroxyproline)만 양쪽 |
| ProMENDA 원표에 카운트가 있는가 | **12종 없음**, 3종만 있고 전부 거의 동률 |

있는 3종도 Serine 17:18, Hydroxyproline 2:2, CYSTEINE 7:6 으로 `margin=0.10`
(`tools/core.direction`) 아래라 0 이 된다. 미네랄이 MENDA 에 없는 것은 당연하다 —
MENDA 는 우울증 **대사체** 데이터베이스다.

#### (3) 빈칸이 Fig. 4(c) 그룹과 정확히 겹친다

| 그룹 | + | − | 0 |
|---|---|---|---|
| Carbohydrates | 7 | 0 | 0 |
| Vitamins and cofactors | 7 | 4 | 0 |
| Amino acid | 8 | 7 | 3 |
| Lipids | 17 | 19 | 3 |
| **Trace Elements** | 0 | 0 | **5** |
| **Macronutrient** | 0 | 0 | **5** |

**Trace Elements 와 Macronutrient 는 통째로 비어 있다.** 그리고 §4.2.3 이 바로 그 두
그룹에 방향을 적는다.

> "the nonrecommended foods seem to contain higher levels of **trace elements and
> macronutrients** that might not be beneficial for individuals with depression"

#### (4) 그 서술대로 채우면 재현이 무너진다

| 변형 | Spearman | Top30 | Bot30 | gold | A층 rec/not | E 0개수 |
|---|---|---|---|---|---|---|
| R 재현 기준 | **+0.786** | 18/30 | **15/30** | 8/9 | 12 / **10** | 16 |
| V5 §4.2.3 대로 (−1) | **+0.590** | 16/30 | **8/30** | 8/9 | 11 / **7** | 6 |
| V5b 반대 부호 (+1) 대조 | +0.756 | 19/30 | 15/30 | 8/9 | **17** / 10 | 6 |
| V7 ProMENDA 엄밀 다수결 | +0.789 | 18/30 | 15/30 | 8/9 | 12 / 10 | 14 |

V5 는 §18.9 A층(`bot30_not` 10→7)과 C층(Spearman, Bot30) **양쪽에서 퇴행**한다.
§18.9 적용 규칙 2에 따라 채택하지 않는다.

**왜 실패하는지가 중요하다.** §4.2.3 의 문장은 **산출물**에 대한 관찰이다 — 추천/비추천
두 집단의 heatmap 차이를 기술한 것이다. 그런데 이 10종은 `E = 0` 이라 애초에 `D = E × Fᵀ`
에 **기여하지 않았다.** 따라서 그 관찰된 차이는 방향의 증거가 아니라 음식 조성의
부산물이다. 출력 관찰을 입력 부호로 되먹이는 것은 순환이고, 수치가 그것을 보여 준다.

대조군 V5b(부호를 뒤집음)가 A층 `top30_rec` 을 12→17 로 **올린다**는 점도 같은 이야기다 —
데이터는 §4.2.3 이 함의하는 방향과 오히려 반대쪽을 선호한다. 논문 근거가 없으므로
이것도 채택하지 않는다.

V7(ProMENDA 엄밀 다수결)은 2종(Serine −, CYSTEINE +)을 채우고 Spearman 이
+0.786 → +0.789 로 움직일 뿐 나머지는 전부 동일하다. 17:18, 7:6 이라는 **1건 차이**에
기댄 부호라 통계적 의미가 없다. 채택하지 않는다.

#### 결론 — 새 결함

**`E = 0` 인 16종은 "증거가 없다" 의 충실한 표현이고, §4.2.1 의 `E ∈ {+1, −1}` 은
논문이 배포한 자료로는 충족할 수 없다.** 85종 중 10종(미량원소·다량영양소)은 MENDA 에
처음부터 존재할 수 없는 물질이고, 논문은 그 10종에 어떻게 부호를 주었는지 적지 않았다.
Fig. 4(c) 가 이들을 85종에 포함시킨 것과 §4.2.1 의 E 정의가 서로 맞지 않는다.

### 17.29 §3.2 compound 링킹을 재현하니 논문 ID 가 자기 KG 에 없다 (2026-11-09)

§3.2 의 compound 링킹은 그동안 **절차가 아니라 결과를 물려받은** 상태였다 —
`setup/nutrient_kegg_map.csv` 180 개 중 101 개가 공개 KG 의
`nutrient_id owl:sameAs KEGG` 와 값까지 같다. 논문이 적은 절차를 직접 구현해
그 101 개를 독립적으로 재현할 수 있는지 봤다. 실행:
`python3 eval/paper_kg_stats.py clink`.

#### 구현한 규칙 (논문 §3.2 그대로)

> "compounds are linked to the KEGG database **using their labels** … The matching
> process **ignores case, singular and plural forms, as well as the word sequence**"
> / "we use the **Greek alphabet as a constraint**. For example, 'Tocopherol, gamma'
> and 'Tocopherol, alpha' are recognized as two distinct compounds"

- 매칭 키 = (어순 무시 토큰 집합, **그리스문자 집합**). 그리스문자는 따로 묶어
  반드시 일치해야 하므로 `Tocopherol, gamma` ≠ `Tocopherol, alpha` 가 된다.
- 단복수는 `ourkg/common.singularize` 와 같은 규칙.
- 동의어는 KEGG 라벨의 괄호 표기에서 얻는다 — `Ascorbic acid (Vitamin C)`,
  `alpha-Tocopherol (Vitamin E)`. 논문이 든 "vitamin E = alpha-tocopherol" 이 이것이다.

#### 결과

```
KEGG 노드 6,685 / 매칭 키 8,000
FDC nutrient 477 중 1:1 매칭 119 (모호 5)
논문 매핑 123 과 대조 — 일치 51, 다름 15
```

절반도 재현되지 않는다. 그런데 불일치 쪽을 보면 원인이 우리가 아니다.

#### 다름 15 건 중 14 건은 **배포된 KEGG 서브셋에 논문 ID 가 없다**

```
Tryptophan     논문 C00806 (서브셋에 없음)  재현 C00078 "Tryptophan (Trp)"
Isoleucine     논문 C16434 (〃)             재현 C00407 "Isoleucine (Ile)"
Leucine        논문 C16439 (〃)             재현 C00123 "Leucine (Leu)"
Methionine     논문 C01733 (〃)             재현 C00073 "Methionine (Met)"
… Tyrosine · Valine · Arginine · Histidine · Alanine · Phenylalanine …
```

전부 아미노산이다. 논문이 가리킨 ID 는 배포된 `KEGG_Compound.jsonld`(6,685 노드)에
없어서 **그 KG 안에서는 라벨도 brite 분류도 붙지 않는다.**

#### 정정 — 논문 ID 는 틀린 것이 아니다 (2026-11-09, KEGG REST 확인)

처음에 이 절은 논문 ID 를 "비정식" 인 것처럼 적었다. **틀린 서술이었다.**
미해소 27 건을 KEGG REST(`rest.kegg.jp/get/<ID>`)로 전수 조회한 결과 **27/27 이 유효한
KEGG 화합물**이고 이름도 정확히 대응한다.

```
C00806 = Tryptophan      C01733 = Methionine     C16434 = Isoleucine
C00070 = Copper          C01496 = Fructose       C01529 = Selenium  …
```

논문은 **입체 비특이적(generic) 형태**를 골랐고, 그것은 FDC 가 아미노산을 L-/D- 구분
없이 **총량으로** 보고하는 것과 오히려 맞는 선택이다. 재현이 L-form 을 찾은 이유는
배포된 서브셋에 L-form 만 라벨과 함께 들어 있기 때문이지, 그쪽이 "정답" 이어서가 아니다.

따라서 이 절의 결함 주장은 다음으로 좁힌다.

> **배포된 KEGG 서브셋(6,685 노드)이 자기 85 목록 중 27 개를 담고 있지 않다.**
> 논문의 ID 선택이 아니라 **배포 범위**의 문제다.

#### 범위 — Fig 4(c) 85 중 27 개가 해소 불가

| 그룹 | 미해소 |
|---|---:|
| Amino acid | 14 |
| Macronutrient | 5 |
| Trace Elements | 5 |
| Carbohydrates | 2 |
| Vitamins and cofactors | 1 |
| **합계** | **27 / 85** |

§17.28 과 맞물린다. 거기서 `E = 0` 이던 16 종 중 미량원소 5 + 다량영양소 5 가
"MENDA 에 없다" 였는데, **같은 10 종이 KEGG 파일에도 없다.** 논문의 85 목록에는
자기 KG 가 이름조차 붙이지 못하는 compound 가 27 개 들어 있다.

#### 조치 — `kegg_alias.KEGG_ALIAS`

재현으로 얻은 15 건(아미노산 14 + Vitamin B12)을 `kegg_alias.py` 에 세 번째 방향으로
넣었다. **ID 를 고치는 표가 아니라 generic ↔ L-form 을 잇는 조인 표**다 —
`INCIDENCE_ALIAS`(ProMENDA 가 L-form 을 쓴다)와 같은 성격이다. 기존 `FOOD_ALIAS`(양 조회) · `INCIDENCE_ALIAS`(방향 조회) 와 같은 패턴이다.

**교차검증**: 15 건 중 9 건은 예전에 ProMENDA 이름을 손으로 대조해 만든
`INCIDENCE_ALIAS` 와 **독립적으로 같은 답**이다(9/9 일치). 서로 다른 경로로 같은
대응에 도달했다.

적용 범위는 **라벨·brite 분류·대사 경로 조회뿐**이다. 85 목록의 정본 ID 는 그대로 둔다.

```
Fig 4(c) 85 중 KEGG 해소   58/85  ->  73/85   (alias 적용 시)
```

남은 12 건(미네랄 10 · Fructose · Galactose)은 재현되지 않는다 — 배포된 KEGG
서브셋에 해당 라벨 자체가 없다.

## 18. 개선 방안 (논문 근거 기준)

재현(§1~17)과 **코드·수치를 섞지 않는다.** 아래는 전부 논문이 스스로 적은 내용을 근거로
하고, 판정은 논문의 평가 지표(§5.1 방법 1·2)와 §3·§4 의 수치로만 한다.
각 항목은 "논문 근거 → 측정된 격차 → 할 일 → 성공 기준" 순이다.

우선순위는 **논문 지표를 움직이는 크기 / 비용** 으로 매겼다.

### 18.1 (우선 1) §3.2 Entity linking 검증 — **완료 (2026-11-03, 결과는 §17.7)**

**논문 근거** §3.2 가 수치 네 개를 명시한다. food 1,220,480 → 128 categories,
compounds 23,212, microbiota 984,031, mental disorders 3,505. 합계 1,637,915
"normalized entities".

**격차** 우리 코드에 이 숫자가 한 번도 등장하지 않는다(grep 0건). §17.1 에서 Table 1 의
Entity 열이 어떤 정의로도 맞지 않음을 확인했으므로, §3.2 의 네 수치도 정의부터
불확실하다. 거친 측정으로는 categories 185 / KEGG compound 노드 6,685 /
Mental_health 노드 569 / bacteria entity 326,845 로 전부 어긋난다.

**할 일** `eval/paper_kg_stats.py` 에 §3.2 절을 추가한다. 논문이 적은 정규화 규칙
(쉼표 앞 접두 분리, 복수→단수, 소문자화, 그리스 문자 구분, FDC ID 기준 병합)을 코드로
옮기고, 그 규칙을 적용했을 때 네 수치가 나오는지 본다. 나오지 않으면 **어떤 정의에서도
나오지 않는다는 것 자체가 결과**다 (§17.1 Entity 열과 같은 성격).

**성공 기준** 네 수치 각각에 대해 "일치 / 불일치(배율 포함)" 를 수치로 보고. 128
categories 는 `reconstruct.py` 의 라벨 병합과 직결되므로, 일치하면 측정 밀도 28 → 33
격차의 원인 하나를 지울 수 있다.

**결과 (§17.7)** 일치 0/5, 시도한 정의 15개 중 0개. 128 은 배포 KG(185)에서도 FDC
원본(645)에서도 나오지 않아, 측정 밀도 격차의 원인은 여기가 아니다. 다음은 18.2 다.

### 18.2 (우선 2) §3.3 Knowledge inference 재구현 — 논문이 기여로 내세운 474만

**논문 근거** §3.3 이 추론 규칙 두 가지를 글로 적는다. (a) subClassOf 전이
("saturated fatty acid ⊂ fatty acid ⊂ lipid"), (b) 공통 gut microbiota 를 공유하는 두
mood disorder 를 "complications" 로 추론. Table 1 은 결과를 4,741,023 statements 로
적는다. §5.1 방법 2 는 **그 추론 결과를 검증하는 평가**다.

**격차** 배포 KG 에 추론 트리플이 0건이다(§17.1). 즉 **논문 기여의 35%(474만/1,335만)가
검증 불가 상태**이고, 방법 2 는 원래 이 추론을 겨냥한 평가인데 우리는 "근거가 KG 에
있는가" 로 우회해 재고 있다.

**할 일**
1. (a) 전이 추론: `KEGG_Compound.jsonld` 의 subClassOf 체인과 `Bacteria_Ontology.trig`
   의 isChildOf 체인에 transitive closure 를 적용하고 생성 트리플 수를 센다.
2. (b) complication 추론: `Disease_Bacteria.jsonld` 에서 세균을 공유하는 질병 쌍을
   뽑아 Table 5 의 Complication 8건이 재생성되는지 본다.
3. 생성 수가 474만에 가까운지, 어느 규칙이 대부분을 만드는지 보고한다.

**성공 기준** Table 5 Complication 8/8 재생성 (현재 7/8, #1 은 세균–질병 공백이라
추론으로도 안 될 가능성이 높다 — 그 경우 "논문 추론의 전제가 배포 KG 에 없다" 가 결론).
생성 트리플 수를 474만과 대조.

> **전제 점검 (2026-11-04, §17.17).** 규칙 (b) 는 "둘 다 mood disorder" + "공통 미생물"
> 두 조건인데 배포본에는 **중간 분류가 없고**(질병 계층 전무) **우울증의 미생물 연결도
> 1종뿐**이다. 규칙 (a) 전이 추론은 KEGG·NCBI 계층이 있어 지금 가능하므로 **(a) 를 먼저
> 분리해서 착수**하고, (b) 는 MiKG 단층으로 근사하되 한계를 명시한다.

### 18.3 (우선 3) E 보강 — 재현의 핵심 격차

**논문 근거** §4.2.1 이 incidence matrix `E` 를 85 compound 전체에 정의한다
(+1 relieve / −1 cause).

**격차** 69/85 확보, gold 8/9, Spearman +0.786. 미확보 16종 중 10종이 미네랄로,
대사체 DB 가 원소를 측정하지 않는다(§7). MENDA 원본으로는 더 못 메운다 — §17.4 에서
85 기준 추가분 0종으로 확인했다.

**할 일** MENDA·ProMENDA 밖의 경로를 쓴다. (a) KEGG compound ontology 의 상위 그룹
전이로 미확보 compound 에 그룹 수준 방향을 내려보낸다(§3.3 (a) 규칙의 응용이므로
논문 근거가 있다). (b) 18.2 의 추론 결과로 compound→세균→질병 경로를 넓힌다.
**논문 순위(p5)를 학습에 쓰지 않는다** — 그러면 순환이 된다(§16 invert 참조).

**성공 기준** E 69 → 85/85, gold 8/9 유지 이상, Spearman +0.786 유지 이상.
셋 중 하나라도 내려가면 채택하지 않는다.

### 18.4 (우선 4) §5.1 방법 2 를 논문 방식 그대로 — PubMed 재검색

**논문 근거** §5.1 "We searched the biomedical literature to determine if there was
evidence to support or contradict the conclusion." 결과 11 true / 1 false / 3 unknown.

**격차** 우리는 논문이 든 PMID 를 그대로 받고 "KG 가 같은 추론을 만드는가" 만 본다.
11/15 는 우리가 측정한 값이 아니다.

**할 일** PubMed E-utilities 로 15건을 재검색해 true/false/unknown 을 우리 손으로
매긴다. 논문이 든 PMID 가 실제로 그 주장을 지지하는지도 확인한다.

**성공 기준** 11/15 재현. 어긋나면 어느 건이 왜 달라졌는지 보고 — 2023년 이후 새 문헌이
논문의 판정을 뒤집었다면 그 자체가 §5.2 "new evidence may emerge" 의 실증이다.

### 18.5 (우선 5) 방법 1 문항 확장

**논문 근거** §5.1 "this evaluation approach is limited to the current set of
questions. As the knowledge graph expands, further evaluations and validations will be
necessary."

**할 일** 20문항을 6 aspect 비율을 유지한 채 60~100문항으로 늘린다. 논문과의 연속성을
위해 기존 20문항은 그대로 두고 확장분을 따로 집계한다.

**성공 기준** 확장 문항에서 재현율이 기존 20문항(18/20)과 비슷한 수준으로 유지되는가.
크게 떨어지면 18/20 은 문항 선택 편향이었다는 뜻이다.

### 18.6 (우선 6) SNOMED 284 개념 보완

§17.6 참조. 실익은 "Query 3 를 논문 원문 그대로 실행" 이라는 방법론적 완결성뿐이고
평가 수치는 사실상 안 움직인다. 비용이 작아 여력이 있으면 한다.

### 18.7 논문 범위 밖 — 분리해서 다룬다

논문 §5.2 가 스스로 든 한계를 따라가는 확장이다. 재현 수치와 같은 표에 올리지 않는다.

- **deep learning 추천** — §5.2 "incorporating state-of-the-art deep learning methods
  for recommendation could potentially further enhance the accuracy". KG embedding
  (TransE/RotatE) 로 §4.2.2 를 대체. 판정은 논문 순위 대비 Spearman 으로, 기준선은
  현재 재현값 +0.786.
- **미생물 없이 성립하는 경로** — §4.1.2 Table 3 의 Glutamic acid·L-Threonine·Choline 이
  Fig. 4(c) 85종에 없다(논문 내부 불일치, §7). nutrient→neurotransmitter 직접 경로를
  별도 relation 으로 넣고 §5.1 방법 1·2 로 측정.
- **개인화** — §5.2 "personal health profiles". 논문에 지표가 없으므로 새 지표가 필요하다.

### 18.9 추천 알고리즘의 판정 기준 — 논문에 평가가 없다 (2026-11-04)

§17.27 ⑦ 에서 확인했다. 논문의 두 평가 방법은 **질의**(방법 1)와 **추론**(방법 2)만
덮고, 주 응용인 §4.2 추천 알고리즘은 어느 쪽에서도 채점되지 않는다. 정답 정의도
`K=30` 의 근거도 없다. 그래서 "개선했다" 를 판정할 기준이 비어 있다.

메모리 규칙(**재현 기준·개선은 논문 근거 필수, 개선판은 재현과 분리**)을 지키려면
기준을 출처별로 나눠야 한다. 세 층으로 고정한다.

#### A층 — 논문이 직접 적은 산출물 주장 (재현 점수에 올릴 수 있다)

논문이 추천 **결과에 대해** 명시적으로 쓴 문장만 쓴다. 이미 코드에 있다.

| 기준 | 논문 근거 | 구현 |
|---|---|---|
| 추천 상위 30 중 Fruits·Vegetables 개수 | Fig. 5 하단 층 | `metrics()['top30_rec']` — 현재 **12/30** |
| 추천 하위 30 중 Baked·Beef·Sausages·Pork 개수 | Fig. 5 상단 층 | `metrics()['bot30_not']` — 현재 **10/30** |
| 상단 층 본문 기준 민감도 | §4.2.3 본문 vs Fig. 5 모순 | `tools/paper.py` 의 `TIER_TEXT` (§16.7) |
| 입력 형상 135 음식 × 85 compound | §4.2.1 | `tools/scorecard.py` `[1]` |
| E ∈ {+1, −1} | §4.2.1 | `metrics()['E']` |
| PCA 5 성분 > 80% 분산 | §4.2.1 | `tools/scorecard.py` `[1]` |
| 유사도 = adjusted cosine (식 1) | §4.2.2 | `tools/sweep.py formula` |

**집합 형태(`cat_rec`·`cat_not`)가 아니라 개수 형태(`top30_rec`·`bot30_not`)를 쓴다.**
`cat_rec` 은 "상위 30 에 Fruits 와 Vegetables 가 하나씩이라도 있는가" 라서 과일 1개만
있어도 2/2 만점이 된다 — §17.27 ② 에서 지적한 포화와 같은 함정이다. 실제로 지금
`cat_rec 2/2`, `cat_not 2/4` 인데 개수로 보면 12/30, 10/30 이다. 개수 쪽만 판정에 쓴다.

**fish and shellfish 는 A층에 넣지 않는다.** §4.2.3 본문은 추천군에 fish 를 넣지만
Fig. 5 는 fish 를 **중간 층**에 둔다. 알고리즘 출력에서 직접 그린 Fig. 5 를 기준으로
삼았고, 그 판단 근거는 `tools/core.py` 주석과 §16.7 에 적혀 있다.

#### B층 — 논문의 평가 *방법* 을 새 대상에 적용 (방법은 논문 것, 문항은 우리 것)

지표가 아니라 **절차**를 논문에서 가져온다. 결과는 재현 점수와 별도 표에 싣는다.

- **방법 1 양식** (§5.1): 6개 측면 × 문항, 답을 원 데이터에서 독립 확인. 추천 결과용
  문항은 우리가 만들어야 하므로 **실행 전에 문항을 고정**하고 `eval/` 에 커밋한다
  (§18.5 와 같은 절차). 단 §17.27 ② 를 피해야 한다 — 포화되지 않도록 **오답이 나올 수
  있는 문항**을 반드시 섞는다.
- **방법 2 양식** (§5.1): 추천 상위·하위 각 n 건을 뽑아 PubMed 로 지지/반박/불명을
  라벨링. §17.27 ⑥ 을 피하려면 **unknown 을 분모에 포함**해 확인율을 보고하고,
  라벨링 전에 검색식을 고정한다.

#### C층 — 논문에 없는 지표 (개선 전용, 재현 점수에 올리지 않는다)

| 지표 | 성격 |
|---|---|
| 논문 순위 대비 Spearman | `p5_foodname.txt` 를 순위로 본다는 **추정**에 의존 (`core.paper_ranking` 주석) |
| Top30 / Bottom30 겹침 | 같은 추정에 의존 |
| NDCG | 논문에 정답 순위가 없다 |
| 1비트 기준선 대비 이득 | 우리가 만든 기준선 |

이 네 가지는 **우리가 도입한 지표**다. 값이 올라가도 "논문을 더 잘 재현했다" 가 아니라
"우리 기준에서 좋아졌다" 로만 말한다. `tools/scorecard.py` 는 지금처럼 재현 수치만
싣고, C층은 `tools/sweep.py` 쪽 별도 집계로 둔다.

#### 적용 규칙

1. 개선안을 돌리기 **전에** A·B·C 중 어디로 판정할지 적는다. 끝난 뒤 고르지 않는다.
2. A층이 퇴행하면 그 개선안은 채택하지 않는다 — 재현이 기준이기 때문이다.
3. C층만 올라간 결과는 §18 안에서만 보고하고 README 재현 표에 넣지 않는다.
4. B층 문항·검색식은 실행 전 커밋으로 고정 시각을 남긴다.

### 18.8 작업 분리 규칙

- 재현 코드(`run_pipeline.py`, `eval/`)와 개선 코드를 같은 경로에서 돌리지 않는다.
- 개선의 판정 기준은 **실행 전에** 고정하고 논문에서 가져온다(§16 과 같은 방식).
  어떤 기준을 쓸 수 있는지는 §18.9 의 A·B·C 세 층으로 정해 둔다.
- `tools/scorecard.py` 는 재현 수치만 싣는다. 개선 결과는 별도 집계로 둔다.
