# ourkg — 어떤 데이터를 어떻게 썼나

각 축이 **어디서 왔고 · 어떻게 받았고 · 무엇을 뽑았고 · 무엇과 이었고 · 무엇을
못 하는지**를 적는다. 수치는 `out/linking_stats.csv` 가 정본이고 여기 적은 값은
2026-11-19 빌드 기준이다.

방법론 전체는 [`METHODS.md`](METHODS.md), 설계 결정의 **이유**는 [`README.md`](README.md),
실험과 기각 기록은 [`RESULTS.md`](RESULTS.md) 에 있다.

---

## 한눈에

| 축 | 소스 | 받는 법 | 우리 규모 |
|---|---|---|---|
| 음식·성분 | FoodData Central | 로컬 덤프 `fdc_raw/` | 항목 2,101,279 → 병합 475,769 |
| compound | KEGG | REST + 캐시 | KG 층 154 · F 층 135 |
| 음식 온톨로지 | FoodOn | **EBI OLS API** + 캐시 | 클래스 1,096 · 음식 8,165 |
| 음식 카테고리 | FDC SR / WWEIA | 로컬 덤프 | 세분 265 · 상위 27 |
| 우울증-대사물 | ProMENDA | 로컬 xlsx | 레코드 22,519 → compound 1,412 |
| 미생물 | NCBI taxonomy | efetch + 캐시 | **798 taxid = 791 균** (127 + Disbiome 333 + gutMDisorder 309 + 보탠 29; 7 쌍이 병합 전/후 id) |
| compound-미생물 | KEGG REST | REST + 캐시 | **고유 (균, compound) 쌍 14,918** · compound 76 (**58% 는 속 수준**) |
| compound-미생물 (예측) | **VMH / AGORA2** | 벌크 zip + 캐시 | 46,495 링크 · compound 1,109 |
| 미생물-정신질환 | MiKG 원본 TTL | 로컬 ttl | 406 쌍 |
| 미생물-질환 (외부) | **Disbiome** | REST 전수 + 캐시 | 1,193 관계 · 균 457 · 질환 23 |
| 미생물-질환 (외부) | **gutMDisorder v3** | xlsx 2 개 + 캐시 | 1,239 관계 · 균 499 · 질환 18 |
| 식이 중재 → 미생물 | **gutMDisorder v3** | 같은 xlsx | 603 관계 · 중재 58 · 균 243 (검정용) |
| compound-미생물 (관측) | **분변 대사체 13 코호트** | GitHub raw + 캐시 | 39,574 쌍 · 속 1,859 · compound 315 |
| 섭취-결과 | **NHANES 2017-18** | CDC xpt + 캐시 | 표본 4,774 · compound 47 |
| 1 회 섭취량 | **FDC food_portion** | 배포 zip + 캐시 | 13,129 음식 (코호트 커버리지 56%) |
| 질환 분류 | MeSH | **SPARQL** + 캐시 | 링크 244 · 트리 1,227 |
| 질환 식별자 | SNOMED CT | MiKG xref | 63 (배포본 자체는 1) |

---

## 출처 링크 — 어디서 받았나

받은 주소를 한자리에 모은다. **엔드포인트 주소까지 적는다** — 받는 페이지만
적으면 다시 받을 때 경로를 또 찾아야 하고, 실제로 그걸로 한 번 깨졌다(§15).

| # | 소스 | 받는 곳 | 실제 주소 |
|---|---|---|---|
| 1 · 4 · 14 | FoodData Central (FDC) | [다운로드 페이지](https://fdc.nal.usda.gov/download-datasets.html) → "Full Download of All Data Types" | [`FoodData_Central_survey_food_csv_2024-10-31.zip`](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_csv_2024-10-31.zip) |
| 2 · 7 | KEGG | [KEGG](https://www.kegg.jp/) · [REST 안내](https://www.kegg.jp/kegg/rest/keggapi.html) | `https://rest.kegg.jp/<operation>` |
| 3 | FoodOn | [EBI OLS4 — foodon](https://www.ebi.ac.uk/ols4/ontologies/foodon) | `https://www.ebi.ac.uk/ols4/api/ontologies/foodon/terms` |
| 5 | ProMENDA | [Pu et al. 2024, *Transl Psychiatry*](https://www.nature.com/articles/s41398-024-02948-2) → Supplementary Data 2 | `41398_2024_2948_MOESM3_ESM.xlsx` (로컬) |
| 6 | NCBI taxonomy | [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy) | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy&id=…` |
| 8 | VMH / AGORA2 | [VMH](https://www.vmh.life/) | `https://www.vmh.life/api/reconstructionFiles?download=AGORA2/version2.01/sbml_files_fixed/zipped/AGORA2_models/AGORA2_SBML.zip` (2.17 GB) |
| 9 · 11 | MiKG | [tingcosmos/MiKG-JAIMS](https://github.com/tingcosmos/MiKG-JAIMS) (git clone) | 원본 TTL (로컬) |
| 10 | MeSH | [MeSH RDF](https://id.nlm.nih.gov/mesh/) | `https://id.nlm.nih.gov/mesh/sparql` · `https://id.nlm.nih.gov/mesh/lookup/descriptor` |
| 12 | Disbiome | [Disbiome](https://disbiome.ugent.be/) | `https://disbiome.ugent.be:8080/experiment` (전수 1 회) |
| 12b | **gutMDisorder v3** | [gutMDisorder (하얼빈의대)](https://bio-computing.hrbmu.edu.cn/gutMDisorder/resource.dhtml) | `https://bio-computing.hrbmu.edu.cn/gutMDisorder_api/api/resource/download?fileName=gutMDisorder_v3_Literature-based_All.xlsx` (· `..._Rawdata-based_All.xlsx`) |
| 13 | 분변 대사체 13 코호트 | [Muller et al. 2022, *npj Biofilms Microbiomes*](https://www.nature.com/articles/s41522-022-00345-5) · [borenstein-lab/microbiome-metabolome-curated-data](https://github.com/borenstein-lab/microbiome-metabolome-curated-data) | `https://raw.githubusercontent.com/borenstein-lab/microbiome-metabolome-curated-data/main/data/processed_data/<코호트>/` |
| 15 | NHANES 2017-18 | [CDC NHANES 2017-2018](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017) | `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DR1TOT_J.xpt` (· `DPQ_J` · `DEMO_J`) |
| 비교 기준 | 논문 배포 KG | [ccszbd/Food4healthKG](https://github.com/ccszbd/Food4healthKG) (git clone) | `foodkg_triply/` (로컬) |

- **로컬** 로 적힌 넷(FDC · ProMENDA · MiKG · 논문 배포본)은 용량이나 수동
  승인 때문에 실행 중 받지 않는다. 루트 [`README.md`](../README.md) §2 가 받는
  법을 적어 둔다. 나머지는 전부 **실행 중 재조회**하고 `ourkg/cache/` 에 캐시한다.
- 라이선스로 못 받는 것은 [받지 못한 것](#받지-못한-것) 에 적는다.

---

## 1. 음식·성분 — FoodData Central (FDC)

- **받는 법**: [FDC 다운로드 페이지](https://fdc.nal.usda.gov/download-datasets.html)
  의 "Full Download of All Data Types"(CSV)를 `fdc_raw/` 에 둔다. 용량 때문에
  실행 중 네트워크로 받지 않는다.
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

- **받는 법**: [EBI OLS4 — foodon](https://www.ebi.ac.uk/ols4/ontologies/foodon) 의
  API `https://www.ebi.ac.uk/ols4/api/ontologies/foodon/terms`
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

- **받는 법**: [Pu et al. (2024) *Transl Psychiatry*](https://www.nature.com/articles/s41398-024-02948-2)
  의 Supplementary Data 2 `41398_2024_2948_MOESM3_ESM.xlsx` (로컬)
- **규모**: 22,519 레코드 / 995 연구 → KEGG compound **1,412**
- **극성**: `e_shrunk = (pos − neg) / (pos + neg + K)`, `K = 10`.
  `K` 민감도는 2026-11-18 에 처음 쟀다 — `K=0`(축소 없음)이 ModiMedDiet 처방군
  7/30 인데 `K=10·20` 이 23/30 으로 평탄한 꼭대기다 (RESULTS §5).

---

## 6. 미생물 — NCBI taxonomy

- **받는 법**: [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy) 의
  `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy` 로
  taxid 의 학명·rank·lineage 를 **현재 값**으로 갱신.
  `cache/ncbi_taxonomy.json`
- **규모**: **798 taxid** (논문 322,917). 배포 `Disease_Bacteria` 의 정신질환·
  신경퇴행 연관 127 종 + **Disbiome 333 종** + **gutMDisorder 309 종**(§12b)
  + 수작업으로 보탠 29 종.
- **보탠 근거** (`setup/microbes_added.csv`): MiKG 가 말하는 균 36 종과 평가가
  요구하는 균(논문 Table 3·5, 방법 1 `#6` 의 `Adlercreutzia equolifaciens`)이
  배포본에 없었다. **compound 링크를 17 배로 늘려도 균이 없으면 소용없다**는 것이
  `#6` 으로 드러났다.

### ★ 축을 넓히는 기준을 바꿨다 — 자기참조를 끊는다 (2026-11-20)

그 전까지 미생물 축을 넓히는 길은 `setup/microbes_added.csv` 하나였고 기준이
**"평가가 요구하는 균"** 이었다. 그러면 **이미 아는 균만 늘어난다** — 평가가
묻지 않는 균은 영원히 안 들어온다. 커버리지를 재는 자와 커버리지를 늘리는 기준이
같으니 자기참조다. 그래서 외부 목록으로 바꿨다 ([§12](#12-미생물-질환--disbiome)).

| | 이전 | 지금 |
|---|---:|---:|
| 미생물 | 162 | **798 id = 791 균** |
| KEGG 경로 연결 | 127 종 · 3,103 링크 | **167 종 · 4,571 링크** |
| compound 연결 합집합 (KEGG ∪ VMH) | 143 종 | **종 수준 182 종(38%)** / 속 포함 379 종(78%) |

`#7` 은 축을 3 배로 늘려도 안 열린다: *Bifidobacterium longum* 은 KEGG 24 ·
VMH 546 링크를 갖지만 **ascorbate(C00072)가 양쪽 다 없다.** 균이 없어서가 아니라
그 대사 자체가 두 소스에 없다 — 외부 데이터의 한계라는 기존 진단이 확인됐다.

### ★ 균을 늘린 다음 벽은 "닿지 않는다" 였다 — 종 → 속 사다리 (2026-11-20)

축을 485 종으로 넓히고 재 보니 **KEGG organism 코드가 붙은 것이 167 종뿐**이었다.
들여온 균의 2/3 가 추천 경로에도 §4.1 질의에도 못 닿는다. 원인을 재니 매칭
방식이었다 — 못 이은 318 종 중 **255 가 종(species)이 아니다.**

| rank | 속 | 과 | 목 | 문 | 강 | 종 |
|---|---:|---:|---:|---:|---:|---:|
| 미연결 | **200** | 47 | 6 | 5 | 2 | 56 |

Disbiome 은 속·과 수준으로도 보고하는데 우리는 **종 이름 2 단어**로만 맞추고
있었다. KEGG genome 이름의 첫 단어가 속이므로 **종 → 속 사다리**를 두면
추가 네트워크 요청 없이 붙는다.

| | 이전 | 사다리 적용 | gutMDisorder 추가 후 |
|---|---:|---:|---:|
| KEGG organism 매칭 | 167/485 | 378/485 (종 167 · 속 211) | **569/798** (종 243 · 속 326) |
| KEGG 경로 연결 | 167 종 · 4,571 링크 | 378 종 · 10,257 링크 | **569 종 · 고유 쌍 14,918** (행 15,065) |
| compound | 63 | **76** | 76 |
| Disbiome 균 중 연결됨 | 153/457 (33%) | **343/457 (75%)** | 343/457 |

> **속 수준 링크는 더 약한 주장이다.** 링크 중 **8,626(58%)**이 속 수준이고,
> "이 종이 이 compound 를 대사한다" 가 아니라 **"이 속의 어떤 유전체가"** 를
> 뜻한다.

#### 읽는 쪽이 안 거르면 과대평가가 된다

`match_rank` 열을 적어만 두고 **읽는 곳이 아무도 안 보고 있었다.** 소비처가
네 곳(`analyze.py` 3 · `build.kg` 1)인데 전부 따로 `read_csv` 하고 있었다.
읽는 자리를 `common.compound_microbe(sources, rank)` 하나로 합치고 거르는 기준을
거기 뒀다.

| | 전부 | 종 수준만 |
|---|---:|---:|
| compound 연결 합집합 | 379 종 (78%) · 52,998 링크 | **182 종 (38%)** · 47,538 링크 |
| gut-brain compound | 52 | 52 |

**커버리지 78% 는 속을 포함한 숫자다.** 종 수준만 세면 38% 다. 두 수치를 갈라
말해야 한다. gut-brain 경로는 52 로 같다 — 정신질환에 연결된 균이 대부분 배포
KG 의 종 수준 항목이라 속 링크가 그 경로엔 끼어들지 않았다.

**어디서 무엇을 쓰는지.**

- **평가 어댑터는 `rank='species'`.** 방법 1 `#6`·`#7` 은 *Adlercreutzia
  equolifaciens* · *Bifidobacterium longum* 을 **이름으로 콕 집는다.** 속 링크로
  답하면 "이 속의 어떤 유전체가" 를 "이 종이" 로 바꿔 읽는 것이다. 걸고 다시
  재니 방법 1 결과가 **바이트 단위로 동일**했다 — 사다리를 넣기 이전과 같은 링크
  집합을 보게 됐다는 뜻이고, 필터가 의도대로 동작한다는 확인이다.
  (이번 두 문항에서는 속 링크가 답을 바꾸지 않았다. 그건 운이고 구조를 고친
  것이 맞다 — 55% 가 속 수준인 상태에서 필터가 없으면 다른 종 이름 문항에서
  언제든 섞인다.)
- **KG 는 버리지 않고 출처를 가른다** — `KEGG` / `KEGG(속 수준)`. 속 링크도
  실재하는 정보다. 같은 태그를 달면 SPARQL 로 거를 수 없어서 나눴다.
  `kg_stats.csv` 도 두 행으로 분리했다.
- **VMH 쪽에는 `match_rank` 가 없다.** VMH 의 `ncbiId` 로 taxid 에 직접 붙으므로
  수준 문제가 없다 — 걸러낼 것이 없다.

**아직 못 잇는 107 종**은 과·목·문 수준(60)과 KEGG 에 유전체가 없는 종(47)이다.
과 이상은 NCBI 로 하위 속을 물어야 하고(60 요청) 그 수준의 링크는 속보다 더
약해지므로 하지 않았다.
- **이름 → taxid**: NCBI esearch. 학명이 바뀐 5 종은 **NCBI 동의어 목록으로 확인**
  했다 — `Bacteroides vulgatus → Phocaeicola vulgatus`,
  `Clostridium ramosum → Thomasclavelia ramosa`,
  `Lactobacillus plantarum → Lactiplantibacillus plantarum` 등. 동의어는
  "이름 저자 연도" 꼴이라 **접두 일치**로 봐야 한다.

> **함정 셋 — 데이터를 넣고 쓰는 쪽을 안 보면 조용히 빠진다.**
> ① 캐시 파일명이 겹치면 서로 덮어쓴다(`mesh_tree.json` 을 둘이 써서 F03 판정이
> 전부 실패했다). ② `focus` 필터가 질환 링크 있는 균만 추려 보탠 균이 탈락했다.
> ③ `cached()` 는 **입력 변화를 모른다** — 요청이 늘어도 옛 캐시를 돌려준다.
> 캐시가 요청을 덮는지 검사하도록 고쳤다.

---

### 함정 — 외부 소스는 **폐기된 taxid** 를 들고 있다

Disbiome 의 *Klebsiella* 는 `160674`, gutMDisorder 는 `570` 인데 NCBI 에서 둘 다
`570` 이다. 폐기·병합된 id 로 조회하면 NCBI 는 **현재** TaxId 로 돌려주고 요청한
id 를 `AkaTaxIds` 에 넣는다.

반환된 id 로만 키를 걸면 세 가지가 어긋난다.

| | |
|---|---|
| 요청한 id 가 캐시에 안 들어온다 | `microbes.csv` 에서 그 균이 빠진다(12 종) |
| 그 균의 노드가 비어 버린다 | 질환 관계는 남는데 **라벨·rank·계통·compound 링크가 없다** |
| 반환된 id 가 새로 생긴다 | 아무 소스도 요청하지 않은 5 종(*Palleronia*·*Thomasclavelia*·*Candida*·*Geotrichum*·*Fusarium*)이 들어와 compound 링크 144 개를 달고 있었다 |
| 캐시가 요청을 영구히 못 덮는다 | `cached_covering` 이 매 실행마다 전체를 다시 받는다 |

그래서 **요청한 id 로도 키를 걸어 잃지 않고**, 정본 id 는 `taxid_current` 열에
남긴다. NCBI 가 끝까지 주지 않는 id 가 있으면 몇 개인지·어느 id 인지 출력한다 —
조용히 빠지지 않게 한다.

### 정체성은 정본 taxid 로 모은다

요청 id 를 그대로 정체성으로 쓰면 같은 균이 두 행이 된다(7 쌍). 그러면

- **셀 때 두 번 센다** — compound 링크 147 행이 같은 (균, compound) 쌍이었다.
- **두 소스가 서로 다른 균으로 보인다** — 방향 교차검사에서 7 균이 비교에서
  빠졌다(공유 쌍 125 → 정규화하면 128, [`RESULTS.md`](RESULTS.md) §35).

`common.taxid_alias()` 가 원 id → 정본 id 표를 주고, `compound_microbe()` ·
`measured_links()` · `microbe_disease_direction()` · KG 미생물 URI 가 모두 정본을
쓴다. 원 id 는 KG 에 `our:akaTaxid` 로 남아 어느 소스가 무엇을 들고 있었는지
추적된다. 적재는 **캐시가 아니라 focus 로** 한다 — 캐시는 지난 실행의 taxid 도
들고 있어서 focus 가 줄어도 안 빠진다.

- **규모**: `microbes.csv` **798 행 = 고유 균 791 종** + 병합 전/후 id 중복 7 쌍.

---

## 7. compound-미생물 — KEGG REST

- **경로**: `compound → EC → KO → organism`. KEGG organism 에 매칭된 균
  **569/798** (종 243 · 속 326 — §6 의 사다리).
- **규모**: 행 15,065 = **고유 (균, compound) 쌍 14,918** · compound 76 ·
  미생물 **569 id = 564 균** (`out/compound_microbe.csv`). 행과 고유 쌍이 다른
  이유는 병합 전/후 taxid 를 둘 다 유지하기 때문이다(§6) — 셀 때는 `taxid_current`
  로 모아야 한다.
  **57% 가 속 수준 매칭**이다 — `match_rank` 열로 거른다. 종 수준만 쓰면
  6,400 링크 · 미생물 242 · compound 63.
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

받은 파일: [VMH](https://www.vmh.life/) 의
`api/reconstructionFiles?download=AGORA2/version2.01/sbml_files_fixed/zipped/AGORA2_models/AGORA2_SBML.zip`
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
[MiKG](https://github.com/tingcosmos/MiKG-JAIMS)(Liu et al. 2021) **원본 TTL**
(2,465 triple)을 직접 읽는다.

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

- **받는 법**: [MeSH RDF](https://id.nlm.nih.gov/mesh/) 의 SPARQL
  `https://id.nlm.nih.gov/mesh/sparql`
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

## 12. 미생물-질환 — Disbiome

- **받는 법**: [Disbiome](https://disbiome.ugent.be/) 의
  `https://disbiome.ugent.be:8080/experiment` 전수 덤프 하나.
  6.4 MB · 실험 10,866. `cache/disbiome_experiment.json`
- **왜 이것인가**: 우리 평가와 무관하게 큐레이션돼 있어 **축 확장의 자기참조를
  끊는다**. 그 전까지 미생물 축을 넓히는 길은 `setup/microbes_added.csv` 하나였고
  기준이 '평가가 요구하는 균' 이었다 — 이미 아는 균만 늘어난다.
- **처음 고른 이유는 틀렸다.** 논문 §2 가 VMH 와 나란히 든 gutMDisorder 가
  호스트(`bio-annotation.cn`) 연결 실패라 Disbiome 을 그 대체재로 적었는데,
  죽은 것은 **옛 호스트**였고 v3 는 하얼빈의대 새 호스트에 살아 있다
  ([§12b](#12b-미생물-질환--gutmdisorder-v3)). Disbiome 자체는 뺄 이유가 없어
  둘 다 올리고 출처 태그로 분리한다.
- **규모**: 정신·신경질환으로 걸러 **관계 1,193 · 균 457 · 질환 23**
  (`out/microbe_disease_disbiome.csv`)

### 질환명이 자유 표기다 — MeSH 로 해소해야 F03 판정이 된다

Disbiome 의 `disease_name` 은 MedDRA 계열 자유 표기라 그대로는 MeSH tree 에
못 넣는다. `common.mesh_lookup` 이 해소한다.

- **SPARQL 로 라벨 역조회를 하다 0 건을 받았다.** MeSH 의 라벨 술어는
  `meshv:prefLabel` 이 **아니라 `rdfs:label`** 이고, 용어 계층
  (descriptor → concept → term) 을 다 타야 한다. 전용
  `id.nlm.nih.gov/mesh/lookup/descriptor` REST 가 같은 일을 한 번에 한다.
- **`match=exact` 는 descriptor 라벨만 본다.** 그래서 표기 변형 사다리를 둔다 —
  원문 → 괄호 제거·쉼표 분해 → 소유격(`Parkinson's` → `Parkinson`) → 복수 제거
  → `disorders` → `Disorder`. exact 가 없으면 contains 로 내린다.
- **해소 355 표기 → 138** (exact 106 · contains 28 · 별칭 5, 고유 descriptor 137).
  38% 로 낮아 보이지만 **미해소는 거의 전부 비정신질환**(periodontitis, caries,
  HIV 등)이다.
- **별칭표** (`setup/disease_alias.csv`): lookup 으로 닿지 않는 5 건을 근거와 함께
  적어 넣는다 — ADHD(MeSH 는 어순이 다르다), PTSD(도치 표기),
  전반적 발달장애 NOS(NOS 는 MeSH 어휘가 아니다), 특발성 국소 뇌전증(focal =
  partial), 인지장애(아래 참조). 만성 스트레스는 MeSH 에 질환으로 없어 뺐다.

> **함정 — contains 를 거르는 규칙을 만들려다 틀렸다.**
> `Cognitive impairment` 가 `Chemotherapy-Related Cognitive Impairment` 로
> 붙었다(화학요법 후 인지장애는 다른 질환). 그래서 "찾은 라벨이 질의어로 시작할
> 때만 받는다"는 규칙을 걸었는데 **쓸 수 없는 기준이었다** — 걸려 떨어진 9 건 중
> 6 건이 `Caries → Dental Caries`, `Cirrhosis → Liver Cirrhosis` 처럼 앞 수식어가
> 질환을 바꾸지 않는 **올바른** 매칭이었다. 앞에 붙는 말이 해부 위치인지 원인인지는
> 문자열로 가를 수 없다. 규칙을 되돌리고, `match` 열에 적어 **감사 가능하게** 둔
> 뒤 틀린 것만 별칭표로 덮었다. 이 수작업은 질환 **이름**에만 걸리므로 어떤
> 미생물이 들어오는지는 바꾸지 않는다 — 축 확장 기준은 Disbiome 쪽에 그대로 있다.

> **함정 — `cached()` 가 또 입력 변화를 모른다.**
> `meshids` 가 Disbiome 으로 244 → 313 으로 늘었는데 옛 `mesh_tree.json` 을 쓰자
> 새 descriptor 69 개가 tree number 없이 떨어져 **F03 이 15 → 6 으로 줄었다.**
> `ncbi_taxonomy.json` 에 쓰던 커버리지 검사를 여기에도 걸었다. §6 함정 ③ 과
> 같은 것을 **두 번째로** 당했다.

### KG 반영

`Elevated`/`Reduced` 는 그 질환에서 그 균의 **존재비 변화**이지 이로움/해로움이
아니다. `hasPositiveAssociation`/`hasNegativeAssociation` 으로 바꾸면 뜻이
달라지므로 중립 `mpq:hasAssociation` 에 `our:abundanceIn` 속성(`질환|방향`)으로
붙인다. 출처 태그는 `Disbiome` 으로 MiKG 와 **분리**한다.

---

## 12b. 미생물-질환 — gutMDisorder v3

**§12 가 대체재였다. 원본이 살아 있었다.**

- **받는 법**: [gutMDisorder (하얼빈의대)](https://bio-computing.hrbmu.edu.cn/gutMDisorder/resource.dhtml).
  페이지는 SPA 라 표가 HTML 에 없고, 번들의
  `/gutMDisorder_api/api/resource/download?fileName=<파일>` 이 xlsx 를 준다.
  두 파일을 받는다 — `..._Literature-based_All.xlsx` (1.5 MB) ·
  `..._Rawdata-based_All.xlsx` (1.3 MB). `common.gutmdisorder` ·
  `cache/gutMDisorder_v3_*.xlsx`
- **왜 돌아왔나**: §12 에 "gutMDisorder 는 호스트가 죽었다" 고 적었다. 죽은 것은
  **옛 호스트**(`bio-annotation.cn`, 지금도 타임아웃)였고 v3 가 새 호스트에
  올라와 있다. 논문 §2 가 든 바로 그 DB 라 **대체재가 아니라 원본**이다.
  Disbiome 은 뺄 이유가 없어 둘 다 올린다(출처 태그로 분리).
- **Disbiome 보다 나은 두 가지**
  1. **질환이 MeSH descriptor 로 원본에 붙어 있다** (`Condition1ID = D003093`).
     §12 에서 가장 약한 고리였던 이름 매칭 사다리를 **안 탄다** — mesh_lookup
     해소율 38%, 잘못 붙은 contains 를 별칭표로 덮던 수작업이 여기엔 없다.
  2. 행마다 **방향**(increase/decrease) · **p값** · **분류 계급** ·
     근거(PMID 또는 BioProject 번호)가 있다. Rawdata 쪽은 LDA score 까지 있다.

### 방향을 믿을 수 있는 행만 남긴다 — 이게 이 소스의 함정이다

메타 시트의 `Condition1` vs `Condition2` 가 비교쌍이고 `Alteration` 은 1 의 2
대비 증감이다. **Condition2 가 Health 인 행만** "질환에서 증가/감소" 로 읽을 수
있다. 나머지 비-Health 행은

| 실제로 무엇인가 | 예 |
|---|---|
| 중재 vs 대조 | Yogurt vs No yogurt · Inulin vs Placebos · Exercise vs Sedentary |
| 질환 vs 질환 | 궤양성대장염 vs 크론병 · 위암 vs 위축성위염 |
| 중증도 | 임상적 악화 vs 자연완화 |
| 인구집단 | African American vs Non-Hispanic white |

라서 질환 방향이 아니다. 그대로 합치면 **"요구르트를 먹으면 늘어나는 균"이
"질환에서 늘어나는 균"으로 뒤집혀 들어간다.** 그래서

- `HumanOrMouse == Human` (마우스 행은 식품 추천의 근거가 못 된다),
- `Condition2ID == D006262` (MeSH *Health*),
- `ResearchType == 'Gut microbiota associated with phenotype'`

세 조건을 걸었다. Human 24,750 행 중 남는 것이 **9,374 행**(38%)이다. Health 는
항상 Condition2 쪽에 있어 방향을 뒤집을 일은 없다 — 반대 배치 0 행으로 확인했다.

- `Condition1ID` 는 동반질환이 `;` 로 붙고 MeSH 가 없으면 `*` 다
  (`D010300;D018680`, `D003424;*`). `D\d{6,}` 만 뽑아 한 질환씩 행으로 펼친다.
- `present`/`absent` 135 행은 **검출 여부**라 존재비 방향이 아니다. 표에는 두되
  `our:abundanceIn` 에는 올리지 않는다.
- `increased`/`decreased` 표기 혼용(36 행)은 `increase`/`decrease` 로 합친다.
- 질환 라벨은 우리 MeSH 라벨로 덮는다 — 원본 `Condition1` 에 전각 콤마가
  섞여 있어(`Colitis，Ulcerative`) 그대로 두면 같은 질환이 갈라진다.

### 규모

- 정제 후 **연관 9,374 · 균 1,253 · 질환 150**
  (`out/microbe_disease_gutmdisorder.csv`)
- 계급: 속 3,989 · 종 1,999 · 과 1,556 · 목 861 · 강 495 · 문 448
- **기존 485 균 대비 신규 936** (그중 종 계급 419). 미생물 축이 3 배가 된다.
- 같은 (균, 질환, 방향) 이 여러 논문·프로젝트에서 나오면 `n_evidence` 에 근거
  수로 접는다 — KG 에도 올린다.

### KG 반영 — 방향은 쌍 단위 합의를 본 뒤에 올린다

`mpq:hasAssociation` 은 §12 와 같이 **출처별로** 올린다(`Disbiome` ·
`gutMDisorder`). 출처 추적은 그쪽에 남는다.

**방향은 출처별로 올리지 않는다.** `Elevated`/`Reduced` 는 존재비 변화이지
이로움/해로움이 아니고, 그보다 먼저 **두 소스가 서로 안 맞는다**:

| 범위 | 공유 (균, 질환) 쌍 | 방향 일치 |
|---|---:|---:|
| 전체 질환 | 474 | 271 (57.2%) |
| **KG 가 담는 정신·신경** | **128** | **62 (48.4%)** — 우연 아래 |

각 소스는 자기 안에서도 어긋난다(Disbiome 7.1% · gutMDisorder 4.4%). 출처
태그로만 갈라 두면 KG 를 쓰는 쪽이 모순을 직접 밟는다. 그래서
`common.microbe_disease_direction()` 이 쌍마다 판정하고 `kg()` 은 그 결과만
올린다.

| 술어 | 쌍 | 뜻 |
|---|---:|---|
| `our:abundanceIn` | **1,509** | 방향이 하나로 모인 쌍 (`질환\|방향`) |
| `our:crossSourceAgreement` | 1,509 | 합의 근거 (`질환\|소스\|소스수`) |
| `our:abundanceConflict` | **165** | 어긋난 쌍 — **방향을 안 준다** (`질환\|증가2:감소1\|소스`) |

**모순 쌍을 버리지 않는다.** "연관은 있고 방향은 모른다" 가 우리가 실제로 아는
것이고, 버리면 그 사실이 KG 에서 사라진다. 산출물
`out/microbe_disease_agreement.csv` (쌍 1,674).

이 필터가 분석에서 무엇을 뜻하는지는 [`RESULTS.md`](RESULTS.md) §32 에 있다 —
합의 쌍으로 좁히면 명목 p 가 좋아지지만 **두 소스가 둘 다 확인한 쌍만 남기면
신호가 사라진다**.

---

## 12c. 식이 중재 → 미생물 — gutMDisorder (버린 쪽을 되살린다)

§12b 는 "질환에서 늘어나는 균" 을 뽑으려고 `Condition2 == Health` 를 요구한다.
그래서 **중재 행이 전부 탈락한다.** 그런데 중재 행은 음식을 주고 균이 변하는
것을 본 것이라 **방향이 음식 → 미생물** 이다 — 질환 행과 반대로, 우리가 추천에
필요한 쪽이다. `common.gutmdisorder_intervention()` 이 그쪽을 읽는다.

- **거르는 조건**: Human · `ResearchType = Interventions change the composition
  of gut microbiota` · `InterventionType = Diet, Food, and Nutrition`
- **대조군 규율** (§12b 와 같은 함정): Condition1 에서 Condition2 에도 있는 항
  (동반질환·인구집단)을 뺀 것이 **중재**다. 남은 Condition2 쪽 항이 없거나
  (동반질환만 적힌 대조군) 전부 `No …`/`Placebo`/`Habitual diet` 류면
  **무중재 대조**로 본다. 아니면 버린다.

| | 수 |
|---|---:|
| 식이 중재 메타행 (Human) | 147 |
| 그중 다른 식단과의 대조 — **버린다** | **60 (41%)** |
| 무중재 대조 | **87** |
| 연관행 | 603 (방향 있는 것 547) |

버리는 이유가 §12b 와 같다. `저항전분 저 vs 고` · `폴리덱스트로스 vs 옥수수섬유`
· `저섬유/중지방 vs 저섬유/고지방` 처럼 **둘 다 중재**인 비교가 많고, 그러면
증감이 "다른 식단 대비" 라서 "먹으면 늘어난다" 로 읽을 수 없다.

### 이 자료로 무엇을 했나 — KG 간선이 아니라 **검정**이다

중재 표기를 FDC 음식에 붙여 `food → microbe` 간선을 넣으려 했는데 **안 된다**:
정확 일치 0/58, 실제 음식은 모유와 연어 둘뿐이다. 나머지는 식단 패턴 ·
분리 섬유 · 프로바이오틱스 · 생약이라 FDC 가 다루지 않는다.

대신 **E 를 외부에서 검정하는 데** 썼다 — 이쪽은 미생물만 필요하므로 음식
매칭이 필요 없다. 결과는 [`RESULTS.md`](RESULTS.md) §33 이고 **미리 고정한
예측이 1/2 로 틀렸다**(고지방식이 지중해식보다 높은 점수를 받았다).

---

## 13. compound-미생물 (관측) — 분변 대사체 코호트

- **받는 법**: [Gut Microbiome-Metabolome Dataset Collection](https://www.nature.com/articles/s41522-022-00345-5)
  (Muller et al., npj Biofilms Microbiomes 2022) 의 GitHub raw. 차단 없다.
  `cache/gmm/<코호트>/` · `ourkg/metabolome_check.py build`
- **왜 이것인가**: KEGG 는 "유전체에 효소가 있다" 는 **추론**이고 VMH 는
  **예측**이다. 둘 다 실제 장내 대사량이 아니고, 측정된 분변 대사체와 무관함이
  확인됐다([`RESULTS.md`](RESULTS.md) §15c 검정 ④). 이쪽은 **관측**이다.
- **규모**: 13 코호트 · 268 만 쌍 → BH q<0.05 437,149 → **2 개 이상 코호트에서
  같은 부호로 재현 39,574** (속 1,859 · compound 315).
  우리 taxid 로 펼치면 7,052 쌍 · 균 298 · compound 252.
- **KEGG/VMH 와 13% 만 겹친다** — 서로 보완한다.
- **부호**: 음 26,196 / 양 13,378. 소비 방향이 2 배로 대사 상식과 맞는다.

### 재현성을 두 겹으로 요구한다

한 코호트 안에서는 **다중검정으로 상관이 쉽게 나온다** — IBS 에서 BH 보정 전
p<0.05 쌍이 **41%** 였다. 그래서 ① 코호트 안 BH q<0.05, ② 서로 다른 **2 개
이상** 코호트에서 **같은 부호로** 유의할 것을 요구한다. 부호를 맞추는 것은
소비/생산 방향이 코호트마다 뒤집히면 신호가 아니라 잡음이기 때문이다.

### 한계

- **우울증 코호트가 없다.** 14 개 중 정신질환은 자폐 하나이고 나머지는
  IBD·대장암·신장병·영아 등이다. 만들어지는 것은 "이 속과 이 compound 가 사람
  장에서 함께 움직인다" 는 **일반 사실**이지 우울증 특이적 지식이 아니다.
  우울증 전용 MTBLS12050 은 EBI API 가 401, 공개 FTP 가 404 다.
- **속 수준이다.** 코호트가 속까지만 준다. 우리 taxid 로 펼칠 때 같은 속의 종이
  전부 같은 링크를 받는다.
- **상관은 대사가 아니다.** 같이 사는 균과 대사물이 상관을 보일 뿐이다.
- `iHMP_IBDMDB_2019` 는 HTTP 오류로 빠졌다(대사물 81,867 짜리라 파일 구성이 다르다).

### KG 반영

`mpq:hasMetabolites` 에 출처 `측정 상관` 으로 담는다. 부호는 `our:measuredCorrelation`
속성(`KEGG|±|n코호트`)으로 남긴다 — 술어로 바꾸면
`hasPositive/NegativeAssociation`(이로움/해로움)과 뜻이 섞인다.
**14,126 트리플** (링크 7,063 + 속성).


### 같은 코호트를 두 번째 용도로 쓴다 — 자폐 `E`

`KANG_AUTISM_2017` 은 자폐 23 명 vs 신경전형 21 명의 **환자-대조** 설계다.
compound-미생물 상관(위)에만 쓰기엔 아깝다 — 대사물 57 개(KEGG 매핑)로
**자폐용 `E` 를 측정에서 직접** 만들 수 있다. `ourkg/e_autism.py`.

- **왜 만들었나**: 미생물 축 검정이 전부 우울증으로 돌아가는데 우울증 미생물
  관계가 23 건뿐이라 "검정력이 없어서 안 보이는 것" 과 구별이 안 된다. 자폐는
  미생물 관계가 117(gutMDisorder)·290(Disbiome) 이다
  ([`RESULTS.md`](RESULTS.md) §34).
- **효과크기**: rank-biserial 상관(Mann-Whitney `2U/n₁n₂ − 1`). 44 명에
  평균차를 쓰면 이상치에 끌린다.
- **부호 규약**: `common.polarity` 와 같게 — 환자에서 감소 = 양수.
- **한계를 먼저 적는다**: BH 후 **q<0.05 가 0/57** 이다. 확립된 기준이 아니라
  **검정력을 재 보려고 만든 보조 축**이다. `E_MODE` 선택지로 넣지 않았다.
- 산출물 `out/compound_autism.csv`
- **파킨슨은 못 만들었다.** 미생물이 가장 두터운 질환인데(관계 672) 코호트도
  큐레이션 대사물 DB 도 없다. 개별 연구 표로 지어내면 995 연구 합의인
  ProMENDA 와 비교가 불공정해져서 **하지 않았다**.
---

## 14. 1 회 섭취량 — FDC food_portion

- **받는 법**: [FDC 배포본](https://fdc.nal.usda.gov/download-datasets.html) zip 의
  `food_portion.csv`(survey + sr_legacy).
  `ourkg/cache/fdc_portion/` 에 둔다.
- **규모**: 행 37,158 / 고유 음식 13,129. **추천 코호트 커버리지 56%**
  (12,513 중 6,970). 결측은 음식군 중앙값으로 메운다.
- **왜 받았나**: `F` 가 g/100 g 이라 향신료(1 회 4.2 g)와 수프(215.5 g)를 같은
  양으로 가정한다. 기각된 설정 둘에서 그 왜곡이 드러났다
  ([`RESULTS.md`](RESULTS.md) §15e).
- **결과는 기각이다.** 서빙 기준으로 바꾸면 비추천군이 26 → 2 로 붕괴한다 —
  제과·스낵도 같이 눌리기 때문이다. `F_SCALE=serving` 으로 되돌릴 수 있고
  기본값은 `per100g`(논문 §4.1.2)다.

---

## 15. 섭취-결과 — NHANES

- **받는 법**: [CDC NHANES 2017-2018](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017)
  의 `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/<연도>/DataFiles/*.xpt`.
  **경로가 바뀌었다** — 예전 `Nchs/Nhanes/<주기>/` 는 404 대신 **HTML 오류
  페이지를 200 으로** 돌려준다(세 파일이 전부 20,905 바이트로 똑같아 눈치챘다).
  `ourkg/cache/nhanes/<주기>/` · `ourkg/nhanes.py`
- **쓰는 것**: `DR1TOT`(24 시간 식이회상 영양소 67 열) · `DPQ`(PHQ-9) ·
  `DEMO`(나이·성별·소득)
- **규모**: 2017-2018 주기, 18 세 이상 표본 **4,774** · PHQ-9≥10 이 425(8.9%).
  compound **47** 추정, q<0.05 가 24.
- **왜 필요한가**: ProMENDA 의 up/down 은 "환자에서 **농도**가 높다" 이지
  "**먹으면** 좋다" 가 아니다(§9). NHANES 는 섭취와 결과를 직접 잇는다.
- **한계**: 관찰 연구다. 역인과(우울해서 덜 먹는다)와 교란이 남는다.
  `E_MODE` 의 선택지로 두고 기본값으로 삼지 않는다.

---

## 받지 못한 것

| 소스 | 왜 |
|---|---|
| ~~**gutMDisorder**~~ | **받았다** — 닫힌 것은 옛 호스트(`bio-annotation.cn`, 여전히 timeout)였고 v3 는 하얼빈의대 새 호스트에 있다. [§12b](#12b-미생물-질환--gutmdisorder-v3) |
| **SNOMED CT 전체** | 라이선스. 배포본에 라벨·계층이 없다 |
| **중국 식품 온톨로지** | 배포 KG 의 subset 만 쓴다 (카테고리 39 · 음식 174) |

## KG 를 쓸 때 — 고유 statement 와 출처 주장

`out/ourkg.nt` 는 **중복 statement 를 담지 않는다.** RDF 그래프에는 같은 삼중항이
두 번 있을 수 없으므로 `build.kg()` 의 writer 가 쓰는 자리에서 막는다.

| | 수 |
|---|---:|
| 고유 triple (그래프 크기) | **3,443,485** |
| Σ 출처 주장 (겹침 포함) | 3,461,533 |
| 여러 출처가 같은 statement 를 주장한 몫 | 18,048 |

**출처별 표는 '주장 수' 로 센다.** 중복 제거 후에 세면 먼저 쓴 출처가 공유
삼중항을 가져가 뒤에 쓰는 출처가 줄어든다 — 쓰는 **순서에 의존하는** 수치가 되고
교차검증 정보도 사라진다(VMH 와 KEGG 가 같은 `hasMetabolites` 1,435 건을 독립적
으로 주장하는 것은 서로를 뒷받침하는 사실이다). 그래서 집계는 중복 제거 전에
하고 `kg_stats.csv` 에 두 줄(`Σ 출처 주장` · `Total (고유 그래프)`)을 따로 적는다.
논문 Table 1 과 비교할 때는 **고유** 쪽을 쓴다.

같은 삼중항을 반복 생성하던 자리 둘은 생성 쪽에서도 고쳤다.

| 자리 | 전 | 후 | 왜 |
|---|---:|---:|---|
| FoodOn/OLS 조상 | 119,841 | **25,759** | 클래스 계층을 **음식마다** 올리고 있었다. 계층은 음식 수와 무관하다 |
| MeSH tree 조상 | 4,702 | **3,118** | 한 질환의 트리 번호마다 같은 조상·라벨을 다시 올렸다 |

---

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
cache/gutMDisorder_v3_*.xlsx  gutMDisorder v3 전수 2 개 (2.8 MB)
```

바이너리(xlsx)는 `common.cached_bytes` 로 받는다. 텍스트판과 달리 **임시 파일에
받아서 다 받은 뒤에 옮긴다** — 받다가 끊긴 파일을 캐시로 굳히면 다음 실행이
조용히 깨진다.
