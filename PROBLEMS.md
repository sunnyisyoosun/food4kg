# 현재 문제점

Food4healthKG 재현에서 **무엇이 막혀 있고 왜 막혔는지**를 정리한다.
조사 과정 전체는 [REPRODUCTION.md](REPRODUCTION.md), 현재 수치는
`python3 tools/scorecard.py`.

최종 갱신 2026-09-29.

---

## 한눈에

```
✅ 재현됨    compound 85/85, food 135/135, foodname.csv (135,88),
            F vs 논문 heatmap 행 코사인 0.981 (g 환산, REPRODUCTION §16.1),
            PCA 5성분 (§4.2.1), gold 8/9, Table 5 추론 11/15, 수동 입력값 0개

⚠️ 부분 재현  추천 순위 Top30 15/30 (우연 6.7), Bot30 3/30, Spearman +0.108
❌ 재현 실패  논문 주장 6개 중 1개 통과 (논문 순위 자신은 4/6) — §16.2
```

2026-09-29: 순위 실패의 큰 몫은 `E` 가 아니라 **단위 미환산**이었다.
논문 heatmap 에서 역산한 환산 계수(MG 10^-3, UG 10^-6)를 적용하자 Top30 이
5 → 15 로 올랐다. 남은 병목은 `E` 하나다. 논문 순위가 함의하는 `E` 와 현재 `E` 의
부호 일치는 30/55 다 (§16.3).

---

## 1. ⚠️ 추천 순위가 절반만 맞는다 — 유일한 본질적 문제

```
                g 환산 후 (현재)    g 환산 전
Spearman           +0.108            −0.071
Top30 겹침          15 / 30            5 / 30      우연 기대값 6.7
Bottom30 겹침        3 / 30            4 / 30      우연 기대값 6.7
논문 주장 (§16.2)     1 / 6              —         논문 순위 자신은 4/6
```

134개 중 30개를 무작위로 뽑아도 평균 6.7개가 겹친다.
g 환산으로 추천 쪽(Top30)은 우연을 넘었으나, **비추천 쪽(Bot30)은 여전히
우연 수준이고 논문 주장도 대부분 재현되지 않는다.**

> 이 지표는 `analyse/p5_foodname.txt` 의 줄 순서를 논문 순위로 본 것이다.
> 근거: 내용이 정렬되어 있고(앞 30줄 채소·과일, 뒤 30줄 육류), Fig. 4(c)
> 원본(`heatmap.xlsx`)의 행 순서와 Spearman 0.896 으로 일치하며,
> 공식 README 가 `p5_foodname.txt: The results of food names` 라고 적는다.

### 카테고리 지표에 속지 말 것

`카테고리 추천 2/2, 비추천 4/4` 는 만점처럼 보이지만 **상위 30개에 과일이
1개만 있어도 만점**이다. 논문이 추천한 오렌지 대신 우리가 키위를 올려도 통과한다.
2026-09-28 까지 이 지표로 보고하다 실패를 놓쳤다.

---

## 2. ❌ 원인 — `E` 가 어떤 공개 소스에서도 나오지 않는다

`E` 는 compound 가 우울증을 완화(+1)하는지 악화(−1)하는지를 담은 벡터다.
추천 점수 `u = Xn · E` 의 유일한 방향 입력이다.

```
E 근거 분포 (85종)                E 부호
  unknown           20  근거 없음   +50
  MENDA_both+orig   16  MENDA 원본  -17
  ontology          14               0=18
  MENDA_neg          9
  MENDA_both         7  미확정
  MENDA_pos          6
  MiKG               5
  MENDA_both+Q2      5
  group_prior        2
  Q2_bacteria_path   1
```

**85종 중 27종(32%)이 방향을 정할 근거가 없다.**
`unknown` 20종은 어떤 소스에도 없고(미네랄 10종 포함), `MENDA_both` 7종은
MENDA 원본에서도 동률이다(Oleic 10:11, Serine 17:18, Valine 26:23 등).

### 소진한 경로

| 시도 | 결과 |
|---|---|
| 공개 KG 의 pos/neg 목록 | 논문이 부호를 명시한 14건 중 13건이 `both` |
| **MENDA 원본 5,675 entries** | 16개 집계 규칙 역산 → **최고 8/12**. 다만 `both` tie-break 로는 유효 (아래) |
| ProMENDA 22,519 entries | 12개 구성 전부 더 나쁨 (Spearman 최대 −0.25) |
| Supplementary SPARQL Query 2 | `Disease_Bacteria.jsonld` 에 pos/neg 구분 없어 실행 불가 |
| KEGG BRITE 계층 전파 | 15종 중 2종. 당류를 `−` 로 뒤집어 논문 Fig. 5 와 충돌 |
| `metabolite_bacteria.xlsx` | repo git 히스토리 전수 확인 — 한 번도 커밋된 적 없음 |

MENDA 원본까지 확보하고도 논문 부호와 12종 중 8종이 한계다.
**즉 논문의 `E` 는 MENDA 집계가 아니다.** 논문에 기술되지 않은 별도 큐레이션이다.

### 부분적으로 효과가 있었던 것

MENDA 원본을 **`both` compound 의 tie-break 로만** 쓰면 21종 중 14종이
결정된다(`MENDA_BOTH_TIEBREAK=orig`, 마진 0.10). 논문이 실제로 인용한
소스이고 gold 가 떨어지지 않아 기본값으로 채택했다.

```
                방향 확보   gold   Spearman   Bot30
orig (현재)      67/85      8/9    -0.071     4/30
none (구 동작)   59/85      8/9    -0.063     3/30
```

**커버리지는 69% -> 79% 로 올랐으나 순위는 움직이지 않는다.**
§3 에서 본 대로 `E` 를 완벽히 복원해도 상한이 1비트 기준선에 못 미치기 때문이다.

### 유일하게 남은 길

`final.py` 가 직접 읽는 **`weight.csv`** 를 저자에게 받는 것.
이 파일 하나면 `E` 문제가 전부 해결된다. 공개 경로는 존재하지 않는다
(GitHub repo·Elsevier 보충자료·MENDA 사이트 모두 확인).

---

## 2b. 기준선 — repo 배포본만으로는 어디까지 가는가

공식 repo 가 배포한 4개만 써서 돌려봤다 (`tools/repo_only.py`).
외부 다운로드(FDC 전체·ProMENDA·MENDA 원본·MiKG)와 우리가 만든 매핑표를
전부 배제한다.

```
입력  analyse/heatmap.xlsx                  85 compound 목록
      analyse/p5_foodname.txt               135 food 이름 + 순위
      food_nutrient.csv                     (food_nutrient.csv.zip 에서)
      foodkg_triply/MENDA_Depression.jsonld (foodkg_triply.zip 에서)
```

| 항목 | repo 배포본만 | 현재 (외부 데이터 포함) | 논문 |
|---|---|---|---|
| compound 데이터 | 57/85 | 84/85 | 85 |
| **`E` 방향 확보** | **15/85** | 67/85 | 85 |
| food 매칭 | 116/135 | 135/135 | 135 |
| 측정 밀도 중앙값 | 10 | 28 | 33 |

`E` 가 **15/85** 인 이유는 MENDA 의 `both` 267종이 방향을 못 정하기 때문이다.
compound 결손 28종은 전부 지방산이다(KEGG 매핑 없음).

### 순위 결과

```
both 처리          E 부호          Spearman   Top30    Bot30
pos            +26/-9/0=50        -0.313     4/30     2/30
neg            +6/-29/0=50        +0.322    13/30     9/30
zero           +6/-9/0=70         -0.107     5/30     6/30

우연 기대값 약 8.1
```

`both -> neg` 가 Spearman +0.322 로 우연을 넘지만 **채택할 수 없다.**
267종을 전부 `-1` 로 모는 규칙이라 `E` 가 `+6/-29` 로 음수 편향되고,
논문이 부호를 명시한 compound 와 대조하면 무너진다(전역 반전 계열은 gold 1/9).
12개 중 최선을 사후에 고르는 순환 논증이다.

**결론: repo 배포본만으로는 재현되지 않는다.** 외부 데이터를 넣어야 위 수치가
올라가고, 그래도 순위는 재현되지 않는다. 이 실험이 아래 "문제의 성격" 1·2·7 을
정량적으로 입증한다.

---

## 3. ⚠️ 논문 순위가 1비트로 설명된다

```
                              Spearman   Top30    Bot30
현재                            -0.071    5/30     4/30
ref부호 (순위에서 역산한 상한)    +0.687   22/30    17/30
동물성 기준선 (compound 무시)     +0.695   27/30    28/30
```

**"식물성이면 추천, 동물성이면 비추천" 한 줄이 Top30 27/30 을 낸다.**
compound 를 하나도 보지 않고서다. 논문 순위로부터 역산한 상한보다도 높다.

`E` 를 완벽히 복원해도 상한(0.687)이 1비트 기준선(0.695)에 못 미친다.
**85개 compound 모델이 그 위에 더하는 정보가 거의 없다는 뜻이다.**

확인: `python3 tools/sweep.py ceiling`

---

## 4. ⚠️ 남은 임의 상수

논문에 근거가 없는 값들. 결과에 영향을 준다.

| 위치 | 값 | 성격 |
|---|---|---|
| `map_promenda.py` | `confidence = total/10` | ProMENDA study 수 → 가중치 |
| `map_promenda.py` | `total >= 2` | 최소 study 수 |
| `kegg_alias.INFER_SCALE` | 근거별 크기 (MENDA 1.0, ontology 0.8 등) | infer 행에만 적용. 2026-09-29 전에는 네 소스에 배율로 복사했다 (REPRODUCTION §7) |

`MARGIN = 0.10` 은 독립 정답셋(gold)으로 튜닝했으므로 제외한다
(`tools/ab.py margin`).

---

## 5. ⚠️ 데이터 결손 — 메울 수 없음을 확인함

| 항목 | 현재 | 원인 |
|---|---|---|
| `E` 방향 확보 | 67/85 (79%) | 미네랄 10종은 대사체 DB 가 원소를 측정하지 않음 |
| 측정 밀도 | 28/33 (85%) | FDC 2026-04 vs 논문 2021~22 스냅샷 차이 |
| `C08319` alpha-Licanic acid | 함량·방향 둘 다 0 | 85열 중 유일한 이중 결손 |
| gold | 8/9 | `C06429 DHA` 는 논문(`−`)과 ProMENDA(`+` 28:18)가 충돌 |

---

## 6. 판단이 갈려 토글로 남긴 설정

어느 쪽도 명백히 옳지 않아 기본값을 정하고 근거를 기록했다.

| 토글 | 기본 | 트레이드오프 |
|---|---|---|
| `UNIT_MODE` | `grams` | 논문 heatmap 역산으로 확정 (REPRODUCTION §16.1). `raw` 는 이전 동작(원단위 혼용) — 판단이 갈리는 토글은 아니고 비교용이다 |
| `MENDA_POS_MEANS_RELIEF` | `1` | 논문 §4.2.1 을 따름. `0`(과학적 극성)이면 gold 8/9→7/9, Spearman −0.063→−0.155 |
| `GROUP_PRIOR_MODE` | `carbvit` | `literature`(수동값 21개)가 순위는 최고(+0.159)지만 출처 불명 |
| `MENDA_BOTH_DEFAULT_POS` | `0` | `1`(논문 추정 동작)이면 gold 동일, Spearman −0.063→−0.146 |
| `FIX_STUDY_TYPE` | `0` | `1`(의미론적 교정)이면 Spearman 개선, gold·Top30 악화 |
| `MENDA_BOTH_TIEBREAK` | `orig` | MENDA 원본 카운트로 `both` 를 가름. `none` 이면 방향 확보 79%→69% |
| `E_MODE` | `paper` | 논문 §4.2.1 의 `E = pos − neg`. 공식 `final.py` 는 단일 행 |

A/B 재현: `python3 tools/ab.py all` (끝나면 기본 설정으로 복원한다)

---

## 7. ⚠️ ProMENDA 극성 규약 불일치 — 결정 대기

2026-09-29 `weight.csv` 의 네 소스(infer / faecal / type1 / type2)를 독립 집계로
바꾸자 드러났다 (REPRODUCTION §7).

- step2 는 논문 §4.2.1 을 따라 MENDA **Up = +1** (`MENDA_POS_MEANS_RELIEF=1`).
- step3 `parse_regulation()` 은 ProMENDA **up = −1**.

```
                 Spearman  Top30  Bot30  gold(E≠0 중)
type1 (현재)       −0.782     0      0     1/5
type1 (논문 규약)   +0.782    21     14     4/5
type2 (현재)       +0.681    12     15     4/5   ← Type2 는 up 의미가 반대라 현재가 논문 규약
```

논문 규약을 Type 의미에 맞게 일관 적용하면 독립 기준(gold)과 논문 순위가
동시에 지지한다. infer 행에도 ProMENDA 로 채운 compound 15종이 반대 규약으로
들어가 있어, 고치면 보고 수치가 바뀐다. 순위로 소스를 비교한 순환 위험이 있어
기본값은 아직 바꾸지 않았다.

---

## 문제의 성격 — 우리 코드의 버그가 아니다

조사 과정에서 논문·배포본 쪽 결함을 다수 확인했다.

1. **배포된 `food_nutrient.csv` 가 Excel 한계로 잘려 있음** — 1,048,576줄.
   git 블롭에서 꺼내 확인. 자른 주체는 저자다.
2. **그 파일이 논문 85종 중 57종만 커버** — 지방산 28종의 KEGG 매핑이 없다.
   데이터는 있는데 매핑만 빠졌다(미매핑 107종 중 SFA/PUFA/MUFA/TFA 77종).
3. **§4.2 의 수식 서술로는 논문 결과가 재현되지 않음** — 16조합 비교에서
   논문 조합이 꼴찌(Spearman −0.543), 공식 `final.py` 가 8위권.
4. **§4.2.1 의 `E` 정의와 실제 데이터 의미가 반대** —
   `hasPositiveAssociation` 목록은 MENDA 의 `Up`(우울증에서 증가)과
   Jaccard 0.981 로 일치하는데, 논문은 이를 "relieving" 이라 적는다.
5. **§4.2.3 본문과 Fig. 5 가 모순** — 본문은 어류를 추천이라 하고
   Fig. 5 는 중간층에 둔다.
6. **Table 3/4 의 compound 가 Fig. 4(c) 85종 목록에 없음** —
   Glutamic acid, L-Threonine, Choline 등.
7. **`final.py` 가 읽는 입력 4개가 repo 에 없음** —
   `food.csv`, `foodname.csv`, `weight.csv`, `acs04.csv`.
8. **단위 환산을 적지 않음** — §3.1 은 "quantified in weight" 라고만 한다.
   heatmap 역산으로 g 환산(IU 는 µg 취급)임을 확인했다 (REPRODUCTION §16.1).
9. **§4.2.3 의 성분 차이 서술이 논문 자신의 데이터와 어긋남** — 본문은
   비추천 음식에 미량원소·다량영양소가 많다고 하나, heatmap 상·하위 30행에서는
   추천 쪽이 높다 (p=0.014, 0.004. REPRODUCTION §16.2).

우리 쪽 결함도 있었다. 단위 미환산(§16.1), IU·µg 혼합 평균, 네 소스를 배율로
복사한 `weight.csv` (REPRODUCTION §7) 는 모두 2026-09-29 에 고쳤다.

---

## 결론

**부분 재현이다.** 데이터와 알고리즘 구조는 재현됐다 — F 가 논문 heatmap 과
행 코사인 0.981, PCA 5성분 일치, 논문 자신의 F 로는 선형 `E` 모델이 논문 순위를
held-out 0.91 로 설명한다. 추천 순위는 Top30 15/30 으로 우연을 넘었으나
Bot30 과 논문 주장은 재현되지 않는다.

남은 격차는 `E` 하나다. 논문 순위가 함의하는 `E` 와 공개 소스 `E` 의 부호 일치가
우연 수준(30/55)이다. §7 의 극성 규약이 그 일부를 설명할 가능성이 있다.

**"공개된 자료만으로는 이 논문의 `E` 를 복원할 수 없고, 그래서 추천 순위가
부분적으로만 재현된다."**
