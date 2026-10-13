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
  run_paper_eval.py   실행기

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
있다. `eval/run_paper_eval.py` 의 `KG` 클래스가 `foodkg_triply/` 를 읽어 20문항에 답한다.

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
| MENDA | 5,675 | 2,633 | 절반 이하 |
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

