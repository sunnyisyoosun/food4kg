# ourkg — 어떤 데이터를 어떻게 썼나

각 축이 **어디서 왔고 · 어떻게 받았고 · 무엇을 뽑았고 · 무엇과 이었고 · 무엇을
못 하는지**를 적는다. 수치는 `out/linking_stats.csv` 가 정본이고 여기 적은 값은
2026-11-19 빌드 기준이다.

설계 결정의 **이유**는 `README.md`, 실험과 기각 기록은 `RESULTS.md` 에 있다.

---

## 한눈에

| 축 | 소스 | 받는 법 | 우리 규모 |
|---|---|---|---|
| 음식·성분 | FoodData Central | 로컬 덤프 `fdc_raw/` | 항목 2,101,279 → 병합 475,769 |
| compound | KEGG | REST + 캐시 | KG 층 154 · F 층 130 |
| 음식 온톨로지 | FoodOn | **EBI OLS API** + 캐시 | 클래스 1,096 · 음식 8,165 |
| 음식 카테고리 | FDC SR / WWEIA | 로컬 덤프 | 세분 265 · 상위 27 |
| 우울증-대사물 | ProMENDA | 로컬 xlsx | 레코드 22,519 → compound 1,412 |
| 미생물 | NCBI taxonomy | efetch + 캐시 | 127 taxid |
| compound-미생물 | KEGG REST | REST + 캐시 | 2,124 링크 · compound 59 |
| compound-미생물 (예측) | **VMH / AGORA2** | 벌크 zip + 캐시 | 35,509 링크 · compound 1,014 |
| 미생물-정신질환 | MiKG 원본 TTL | 로컬 ttl | 406 쌍 |
| 질환 분류 | MeSH | **SPARQL** + 캐시 | 링크 244 · 트리 1,227 |
| 질환 식별자 | SNOMED CT | MiKG xref | 63 (배포본 자체는 1) |

---

## 1. 음식·성분 — FoodData Central (FDC)

- **받는 법**: USDA 전체 배포본(CSV)을 `fdc_raw/` 에 둔다. 네트워크로 받지 않는다.
  - `food.csv` 219 MB · `food_nutrient.csv` 1.79 GB · `nutrient.csv`
  - `survey_fndds_food.csv`, `wweia_food_category.csv` — FNDDS 음식의 카테고리
- **뽑는 것**: 2,710 만 행을 스트리밍하며 KEGG 로 매핑되는 nutrient 행만 보관.
- **단위**: `nutrient.csv` 가 정본이다. 매핑표만 보면 새로 넣은 성분의 단위가
  `NaN → 1.0` 이 되어 **mg 를 g 로** 취급한다(citric acid 가 1,740 g/100g 으로
  나왔다). `UNIT_TO_G` 로 g 환산하되 **IU 는 질량이 아니다** — 질량 측정치가
  있으면 그쪽을 쓴다(비타민 D 1 IU = 0.025 µg).
- **라벨 병합**: 논문 §3.2 "splitting the food labels by commas … exact matching".
  2,101,279 → **475,769**.
- **대표 항목**: 라벨을 공유하는 FDC 항목 중 큐레이션 순위로 하나를 고른다
  (`foundation > sr_legacy > survey_fndds > … > branded`). **값도 그 항목의 값**을
  쓴다 — 대표는 A 로 적고 값은 전체 평균을 쓰면 어긋난다.

### KG 층과 F 층을 나눈다

논문은 KG 의 compound(§3.2 23,212)와 추천 행렬 `F` 의 compound(§4.2.1 85)를
분리한다. 우리도 나눈다 — 한 표로 쓰면 "`F` 에 넣으면 추천이 무너지는 성분"이
KG 에서도 사라진다.

| | 산출물 | 내용 | 규모 |
|---|---|---|---|
| **KG 층** | `out/food_compound_kg.csv` | 성분별 측정치 **그대로** (`nutrient_id` 유지) | 음식 15,347 · nutrient 202 · compound 154 |
| **F 층** | `out/food_compound_long.csv` | KEGG 당 **대표 측정치 하나** | 음식 14,886 · compound 130 |

- 스트리밍은 **확장 매핑**(기본 182 + 후보 94 + B-6)으로 넓게 받고 `F` 는 뒤에서
  `setup/nutrient_kegg_map.csv` 로 좁힌다.
- `F` 의 대표 측정치 규칙: IU 는 뒤로, **DFE·RAE 는 등가 환산값이라 뒤로**
  (DFE = food folate + 1.7 × folic acid), `added`·`label entry`·`, food`·
  이성질체 분해값은 뒤로. `F` 가 재는 것은 **그 KEGG 화합물의 중량**이다.
- `Vitamin B-6`(C00314)는 **KG 층에만** 둔다. KEGG 대응이 없어서가 아니라 `F` 에
  넣으면 추천이 무너져 기각했다 (RESULTS §4.3).

---

## 2. compound — KEGG

- **매핑표**: `setup/nutrient_kegg_map.csv` (FDC nutrient_id → KEGG). 182 행.
- **후보**: `setup/nutrient_kegg_candidates.csv` — FDC 미매핑 nutrient 를 KEGG REST
  `find/compound` 로 **이름 정확 일치**만 조회해 얻은 94 종. **F 에는 넣지 않는다**
  (넣으면 두 기준이 무너진다, RESULTS §4.3). KG 층에만 쓴다.
- **brite 분류축**: `br08001`·`br08002`·`br08005` 를 REST 로 받아 744 compound 분류.
- **캐시**: `cache/kegg_*.txt`

---

## 3. 음식 온톨로지 — FoodOn (EBI OLS)

논문 §3.1 이 FoodOn 을 쓴다고 하지만, 배포 KG 의 `Food_Ontology.jsonld` 는
**12,913 노드짜리 부분집합**이라 `soy milk` 가 없고 상위 노드의 라벨조차 빠져
계층이 끊겨 있다. 그래서 **EBI OLS** 에서 직접 받는다.

- **받는 법**: `https://www.ebi.ac.uk/ols4/api/ontologies/foodon/…`
  - 클래스 전수 → `cache/foodon_terms.json` (**28,685**)
  - 매칭된 클래스의 `hierarchicalAncestors` → `cache/foodon_ancestors.json` (1,123)
- **매칭 규칙**: `foodon_match.py`. **이름 일치만** 쓴다. 검수로 함정 셋을 막았다.
  - 공백 무시는 **한 글자 토큰이 없을 때만** — 색소 `Green S` 가 `greens` 로 무너진다
  - EFSA FoodEx2 코드 클래스(`40330 - …`) 제외 — 동의어 `snacks` 로 걸린다
  - `black or white pepper product` 제외 — 동의어 `pepper` 로 피망이 후추가 된다
- **결과**: 음식 **8,165 / 14,886 (54.9%)** · 클래스 1,096 · 조상 포함 링크 117,554
  (`out/food_foodon.csv`, KG 에 119,841 triple)

---

## 4. 음식 카테고리 — FDC SR / WWEIA

- **철자 통합**: 브랜드 자유문자열 카테고리는 FDC 안에서 **구분자가 세 가지**다
  (공백 둘 · 하이픈 · en dash). 16 개 카테고리 51,108 항목이 갈려 있었다.
  구두점·대소문자를 지운 키로 묶고 **가장 많이 쓰인 철자를 대표**로 삼는다.
  라벨을 새로 지어내지 않는다. **WWEIA 적용 뒤에** 돌려야 한다.
- **상위 식품군**: WWEIA 4 자리 → SR 식품군 링크 **118 개**를 배포 KG
  `Food_Category.jsonld` 에서 추출해 `setup/wweia_srgroup.csv` 로 고정했다.
  접두 규칙이 **아니다**(앞 2 자리 일치 1 / 불일치 117). 3,343 음식에 적용된다.
  그 전까지 `food_group` 은 **음식 이름 정규식**으로 추정하고 있었다.

---

## 5. 우울증-대사물 — ProMENDA

- **받는 법**: Pu et al. (2024) 보충자료 `41398_2024_2948_MOESM3_ESM.xlsx` (로컬)
- **규모**: 22,519 레코드 / 995 연구 → KEGG compound **1,412**
- **극성**: `e_shrunk = (pos − neg) / (pos + neg + K)`, `K = 10`.
  `K` 민감도는 2026-11-18 에 처음 쟀다 — `K=0`(축소 없음)이 ModiMedDiet 처방군
  7/30 인데 `K=10·20` 이 23/30 으로 평탄한 꼭대기다 (RESULTS §5).

---

## 6. 미생물 — NCBI taxonomy

- **받는 법**: `efetch.fcgi` 로 taxid 의 학명·rank·lineage 를 **현재 값**으로 갱신.
  `cache/ncbi_taxonomy.json`
- **규모**: **127 taxid** (논문 322,917). 정신질환 연관 종만 쓴다 —
  **가장 얇은 축이고 gut-brain 경로 전체를 제약한다.**

---

## 7. compound-미생물 — KEGG REST

- **경로**: `compound → EC → KO → organism`. KEGG organism 에 매칭된 균 **82/127**.
- **규모**: **2,124 링크 · compound 59 · 미생물 82** (`out/compound_microbe.csv`)
- **한계**: KEGG 는 유전체가 등록된 균만 담는다. `Adlercreutzia equolifaciens` 의
  citric acid 경로, `Bifidobacterium longum` 의 ascorbic acid 경로가 없어
  §5.1 방법 1 `#6`·`#7` 이 △ 에 머문다.

---

## 8. compound-미생물 (예측) — VMH / AGORA2

논문이 related work 로 **언급만 하고 쓰지 않은** 소스다. 우리 병목(7번)을 메운다.

### 두 경로

| | REST API | **벌크 (채택)** |
|---|---|---|
| 주소 | `…/api/public/getMicrobeHandler?id=<균주명>` | `…/api/reconstructionFiles?download=<경로>` |
| 레이트 리밋 | **100 req/hr** | 없음 |
| 범위 | 우리 67 taxid 한정 | **AGORA2 전체 7,302 균주** |
| 결과 | 183,593 링크 · 66 taxid | **280,818 링크 · 308 균주 · 66 taxid** |

받은 파일: `AGORA2/version2.01/sbml_files_fixed/zipped/AGORA2_models/AGORA2_SBML.zip`
(2.17 GB, 범위 요청·이어받기 지원). `agora2_raw/` 에 둔다(git 추적 안 함).

### 이어붙이는 법

```
SBML <species id="M_<abbr>__91__<구획>__93__">
   -> vmh_metabolites.abbr -> kegg          (대사물)
파일명 Akkermansia_muciniphila_YL44.xml
   -> vmh_microbes.label   -> ncbiId        (미생물, 우리 taxid 와 직결)
```

### 커버리지 (2026-11-19)

| | 현재 우리 | VMH/AGORA2 | **합집합** |
|---|---:|---:|---:|
| (균, compound) 링크 | 2,124 | 35,509 | **36,769** |
| compound | 59 | 1,014 | **1,046** |
| 균 (taxid) | 82 | 66 | **95** |

겹침 **864** · 순증 **34,645**. 겹침은 KEGG 추론 경로와 AGORA2 유전체 재구성이
**독립적으로 같은 결론**에 이른 지점이라 서로를 교차 검증한다.

우리 compound 축에 미치는 효과:

| | 총수 | 기존 균 링크 | VMH | 합집합 |
|---|---:|---:|---:|---:|
| KG 층 | 154 | 59 | 46 | **78** |
| F 층 | 130 | 59 | 35 | **67** |

링크가 17 배 늘어도 `F` 층 증가는 +8 이다. VMH 의 compound 1,014 종 중 대부분이
**음식에 측정되지 않는 세포 내 대사 중간체**라 `F` 에 못 들어간다. 값어치는
`F` 확대가 아니라 **gut-brain 경로 필터를 59 → 78 종으로 넓히고 근거를 두 소스
교차로 바꾸는** 데 있다.

### 함정 (전부 실제로 당했다)

- **다운로드 파라미터**: 목록은 `?path=`, 다운로드는 **`?download=<URL 인코딩 경로>`**.
  틀리면 27 바이트 JSON 에러를 **HTTP 200 으로** 돌려주고 `curl` 이 성공 처리한다
  (종료 코드 0). **크기와 타입을 확인해야 한다.**
- **deflate64**: 파이썬 `zipfile` 이 못 읽는다(`compress_type 9`,
  "That compression method is not supported"). 시스템 `unzip` 으로 우회한다.
- **SBML 구획 인코딩**: `M_<abbr>_c` 가 아니라 `M_<abbr>__91__c__93__`
  (`[`=`__91__`, `]`=`__93__`).
- **API 레이트 리밋**: 페이싱·이어받기 없이 돌렸다가 31 분을 날렸다. 폭주한
  프로세스가 살아 있으면 창이 계속 막히므로 **PID 로 확인하고 끊어야 한다.**

### KG 반영 (2026-11-19)

```
<mic:239935>  mpq:hasMetabolites  <kegg:C00158>     출처 = VMH/AGORA2
```

기존 KEGG 추론 경로와 **같은 술어**를 쓴다 — 둘 다 "이 미생물이 이 compound 를
대사한다" 는 같은 주장이다. 다만 **출처를 따로 달아** 소스별 표에서 분리되고,
겹치는 864 쌍은 두 출처가 같은 triple 을 뒷받침하는 형태가 된다.

| | triple |
|---|---:|
| VMH/AGORA2 | **35,509** (compound 1,014 · 균 66) |
| KG 총계 | 3,484,620 → **3,489,732** |

통계도 출처를 나눠 적는다 — **"예측" 이라고 표에 박아** 두면 나중에 이 수치를
인용할 때 성격을 놓치지 않는다.

```
microbe  compound-미생물 (KEGG 추론)     2,124   compound→EC→KO→organism
microbe  compound-미생물 (VMH/AGORA2)   35,509   유전체 재구성 — 예측
```

두 경로로 받은 것을 **합쳐** 쓴다. 커버리지가 서로 다르다 — 벌크 30,397 /
API 34,992 / 합집합 35,509. 처음에 벌크만 넣었다가 문서 수치와 어긋나 고쳤다.

산출물 `out/compound_microbe_vmh.csv` (캐시는 git 추적을 안 하므로 KG 에 들어간
내용을 추적 가능한 자리에 남긴다). 캐시가 없으면 이 단계는 **건너뛴다** —
2.1 GB zip 없이도 빌드가 돈다.

`F` 를 건드리지 않으므로 두 기준은 불변이다(23/1 · 추천군 21 · 비추천군 26 ·
위반 0, 확인함).

> ⚠ **AGORA2 는 유전체에서 추론한 대사 능력이지 실측이 아니다.** MiKG 의
> `A/B/C` 근거나 ProMENDA 실측과 같은 무게로 쓰면 안 된다.

## 9. 미생물-정신질환 — MiKG 원본 TTL

배포 KG 의 `Disease_Bacteria` 만으로는 정신질환 관계가 얇다(F03 6 종, 우울증 1 건).
MiKG(Liu et al. 2021) **원본 TTL**(2,465 triple)을 직접 읽는다.

- **경로**: 미생물 → 신경전달물질 → 정신질환. 두 statement 를 이어 **406 쌍**.
- **2026-11-19 에 네 가지를 더 뽑았다** — 그 전에는 세 술어만 썼다.

| 술어 | 수 | 뽑은 것 |
|---|---:|---|
| `hasEvidenceLevel` | 82 | 근거 등급 **A 4 · B 21 · C 47** |
| `hasRegulation` | 14 | 방향 **Promote 13 · Inhibit 1** |
| `hasMapID` | 56 | KEGG pathway — **90 링크 · 경로 56 종** |
| `owl:sameAs` | 114 | **SNOMED 63 · MeSH 51** |

`hasMapID` 는 statement 가 아니라 **별도 `KEGG_pathway` 노드**에 달려 신경전달물질과
이어진다. 산출물 `out/mikg_xref.csv`, `out/neurotransmitter_pathway.csv`.

---

## 10. 질환 분류 — MeSH

- **받는 법**: MeSH SPARQL `https://id.nlm.nih.gov/mesh/sparql`
  - 링크 244 건, 트리 번호 → 기술어 이름 **1,227** (`cache/mesh_tree.json`)
- **계층**: 트리 번호는 **접두를 자르면 조상**이 된다.
  `F03.600.300.375 < F03.600 Mood Disorders < F03 Mental Disorders`.
  질환 **242 종** · KG 에 4,702 triple (`out/disease_tree.csv`).
- 논문은 이 축을 SNOMED CT 로 세웠다고 하지만 배포본에는 id 284 개뿐이고
  라벨·계층이 없다. **MeSH 로 대체된다** — 우리는 트리 번호를 이미 갖고 있었고
  이름으로 펼치지 않고 있었을 뿐이다.

---

## 11. 질환 식별자 — SNOMED CT

- 배포본 자체는 **1 건**(id·sameAs 뿐, 라벨·계층 없음). 라이선스 때문에 전체를
  받을 수 없다.
- **MiKG 가 자기 엔티티에 SCT id 를 63 개** 달아 두었다. 그것을 쓴다.

---

## 받지 못한 것

| 소스 | 왜 |
|---|---|
| **gutMDisorder** | 서버가 닫혀 있다. `bio-annotation.cn` 은 DNS 는 해석되나(47.76.215.223) http·https·8080 전부 connection refused. NAR 논문(2020 v1 · 2022 v2) 보충자료가 대안이다 |
| **SNOMED CT 전체** | 라이선스. 배포본에 라벨·계층이 없다 |
| **중국 식품 온톨로지** | 배포 KG 의 subset 만 쓴다 (카테고리 39 · 음식 174) |

## 캐시와 재현

네트워크로 받는 것은 전부 `ourkg/cache/` 에 둔다(**git 추적 안 함** — 재생성
가능하고 용량이 크다). 지우고 다시 돌리면 그때의 공개 데이터로 다시 받는다.
정적 스냅샷이 아니라 **실시간 재조회**가 기본이다.

```
cache/foodon_terms.json       FOODON 클래스 28,685
cache/foodon_ancestors.json   매칭 클래스의 조상 1,123
cache/mesh_tree.json          MeSH 트리 번호 → 기술어 1,227
cache/ncbi_taxonomy.json      NCBI efetch 결과
cache/kegg_*.txt              KEGG REST 응답
cache/vmh_*.csv               VMH SPARQL·REST 결과
```
