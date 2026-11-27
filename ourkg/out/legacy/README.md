# `out/legacy/` — 생산 코드가 없는 산출물

`check.py outputs` 는 `out/*.csv` 마다 **만드는 코드가 레포에 있는지** 본다.
여기 있는 파일은 그 조건을 못 채운다. 지우지 않는 이유는 `RESULTS.md` 가
그 수치를 인용하고 있기 때문이고, `out/` 에 두지 않는 이유는 **재현 가능한
산출물과 섞이면 안 되기** 때문이다.

| 파일 | 왜 고아가 됐나 | 지금 봐야 할 것 |
|---|---|---|
| `pca_comparison.csv` | 생산 코드가 **커밋된 적이 없다** (`git log -S` 0 건). 일회성 스크립트 산물 | `out/sweep/fcolumns_comparison.csv` — `PCA_COMPONENTS` 축을 `F_COLUMNS` 와 교차해 다시 잰다 |
| `threshold_comparison.csv` | 같음, 0 건 | `out/sweep/simthr_comparison.csv` — 같은 `SIM_THRESHOLD` 축에 `GUTBRAIN_ALPHA` 를 더해 잰다 (§15b) |
| `complication_hypergeom.csv` | 소스별 접미사판(`_curated` 등)으로 갈라진 뒤 남은 구본. 질환을 **이름**으로 묶던 때의 값이다 (§41 에서 `mesh_id` 로 고쳤다) | `out/complication/complication_hypergeom_curated.csv` |
| `ensemble_recommendation.csv` | §25 앙상블 경로의 식품별 순위. 그 경로는 §27 에서 기각됐고(Top-K 오류 6/30) 비교표만 쓸기로 되살렸다 (`sweep.py ensemble`) | `out/consensus/consensus_current.csv` · `out/sweep/ensemble_comparison.csv` |

| `emicrobe_vote_sensitivity.csv` | 투표 규약 3 × §47 전후 × 28 칸 민감도 (§48). 일회성 스크립트 산물이고, **올바른 귀무로는 세 규약 어디서도 통과하지 않아** 본문에 쓸 말이 없다 — 기록으로만 둔다 | `out/analysis/e_microbe_compare.csv` (정본, `귀무(순열)` 열 포함) |

앞의 두 개는 **"재현 가능한 산출물" 이라고 §43 표에 올라가 있었다.** 그게
이 검사를 만든 이유다. 마지막 것은 **그 검사가 바로 잡아낸 첫 사례**다 —
§48 작업 중에 만들자마자 FAIL 이 떴다.
