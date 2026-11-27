# `out/` — 산출물 배치

평평한 폴더에 97 개가 쌓여 **무엇을 봐야 하는지 알 수 없었다.** 루트에는 최종
산출물만 두고 나머지는 단계별로 내렸다 (§54·§56).

## 루트 — 찾는 것이 여기 있다

| 파일 | 무엇 |
|---|---|
| `ourkg.nt` | **KG 본체** (N-Triples, 502 MB) |
| `recommendation.csv` · `recommendation.png` | **추천 순위**와 그림 |
| `kg_stats.csv` | KG 규모 — 출처별 분해와 겹침 |
| `provenance.json` | 산출물마다 어느 스크립트가·언제·어떤 비기본값 환경변수로 만들었나 |

## 단계별 폴더

| 폴더 | 무엇 | 수 |
|---|---|---:|
| `food/` | F 층 — 음식·성분 구성, FoodOn·카테고리 | 9 |
| `compound/` | E 층 — compound 별 효과·근거·ProMENDA 원시 | 9 |
| `microbe/` | 미생물 축 — 균·질환 관계·compound 링크 | 11 |
| `eval/` | 평가 — 논문 §5.1 재질의, 외부 기준(ModiMedDiet), 부트스트랩 | 8 |
| `analysis/` | 검정 — `E_microbe`·검정력 경계·중재 | 9 |
| `kg/` | KG 구축 부산물 — 질환 계통·외부 식별자·링크 통계 | 5 |
| `sweep/` | 쓸기 민감도표 `*_comparison.csv` | 22 |
| `complication/` | 합병증 추론 — 소스별 초기하·포개짐·문헌 lift | 10 |
| `consensus/` | 부트스트랩 합의 — 설정별 선택도 | 6 |
| `metabolome/` | 코호트별 대사체-균 상관 | 2 |
| `legacy/` | **생산 코드가 없는 기록.** 지우지 않는 이유는 그 폴더 README 에 | 5 |

## 규칙은 코드에 있다

배치는 `common.OUT_SUB` **한 표**이고(순서대로 첫 일치), 쓰는 쪽·읽는 쪽이
모두 `common.outp(name)` 을 지난다. 그래서 배치를 바꾸려면 **표만** 고치면
된다 — 처음에는 `os.path.join(OUT, …)` 이 169 곳에 흩어져 있어 "정본은 못
옮긴다" 고 판단했는데, `outp()` 로 모은 뒤에는 표 한 줄이면 됐다.

검사가 세 가지를 본다 (`check.py outputs`).

| 검사 | 무엇을 막나 |
|---|---|
| `파생물 폴더 배치` | `outp()` 를 안 쓰고 루트에 떨어진 산출물 |
| `산출물 이름 ASCII` | 비ASCII **파일명** — 다른 OS·도구에서 깨져 읽힌다 |
| `산출물 열 이름 ASCII` | 비ASCII **열 이름** — `df.열이름` 속성 접근이 안 된다 |

**값**에는 비ASCII 를 허용한다. 1,372 셀 중 820 은 외부 데이터 그대로이고
(`(±)-Tryptophan` · `Sjögren Syndrome` · gutMDisorder 의 전각 쉼표), 바꾸면
출처와 어긋난다.
