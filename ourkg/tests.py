"""함수 단위 시험 — `check.py` 가 못 보는 자리.

`check.py` 는 **산출물**을 본다. 그래서 함수가 틀렸는데 산출물이 그럴듯하면
통과한다 — 쓸기 사이로 설정이 새던 버그가 그랬고, `run_all.py` 를 50 분 돌려야
드러났다 ([`PROCESS.md`](PROCESS.md) 2.6).

여기서는 **조용히 깨졌던 규칙들**을 함수 단위로 고정한다. 그 규칙이 바뀌면
산출물을 만들기 전에 여기서 터진다.

표준 라이브러리 `unittest` 만 쓴다 — 의존을 더하지 않는다. 네트워크를 쓰지
않고, 파일이 필요한 것은 임시 디렉토리에 **작은 fixture** 를 만들어 쓴다.

    python3 ourkg/tests.py            # 전부
    python3 ourkg/tests.py -v         # 자세히
    python3 ourkg/tests.py CanonTest  # 일부만
"""
import os
import re
import sys
import tempfile
import unittest

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common                                      # noqa: E402
import check                                       # noqa: E402


class PolarityTest(unittest.TestCase):
    """부호 규약 — **환자에서 감소 = 양수(이로움)**.

    이 규약은 `build.promenda` · `e_autism` · 문서가 공유한다. 뒤집히면 추천이
    통째로 반대가 되는데 산출물은 그럴듯하게 나온다.
    """

    def test_up_is_negative(self):
        for w in ('up', 'Increased', 'HIGHER', 'up-regulated'):
            self.assertEqual(common.polarity(w), -1, w)

    def test_down_is_positive(self):
        for w in ('down', 'Decreased', 'lower', 'down-regulated'):
            self.assertEqual(common.polarity(w), 1, w)

    def test_unknown_is_zero(self):
        for w in ('', 'nan', 'unchanged', None):
            self.assertEqual(common.polarity(w), 0, str(w))


class UnitTest(unittest.TestCase):
    """단위 환산 — 매핑표만 보면 **mg 를 g 로** 쓴다(citric acid 1,740 g/100g)."""

    def test_scale(self):
        self.assertEqual(common.UNIT_TO_G['G'], 1.0)
        self.assertAlmostEqual(common.UNIT_TO_G['MG'], 1e-3)
        self.assertAlmostEqual(common.UNIT_TO_G['UG'], 1e-6)

    def test_iu_is_not_mass(self):
        # IU 는 질량이 아니다. 값이 있다는 것이 "질량으로 쓰라" 는 뜻은 아니다 —
        # build 는 질량 측정치가 있으면 그쪽을 쓴다. 여기서는 상수만 고정한다.
        self.assertIn('IU', common.UNIT_TO_G)


class NormKeyTest(unittest.TestCase):
    """이름 비교 키 — 카테고리 통합·음식 대조·FoodOn 매칭이 **같은 규칙**을 쓴다."""

    def test_punctuation_to_space(self):
        self.assertEqual(common.normkey('Beef, ground (85%)'), 'beef ground 85')

    def test_case_and_space(self):
        self.assertEqual(common.normkey('  Milk,   WHOLE '), 'milk whole')

    def test_same_key_for_variants(self):
        self.assertEqual(common.normkey('Lamb, Veal, and Game'),
                         common.normkey('lamb veal and game'))


class LabelTest(unittest.TestCase):
    """라벨 정규화 — 괄호를 지우면 `", , raw"` 가 남는다(빈 쉼표 구간)."""

    def test_empty_comma_run_collapsed(self):
        out = common.normalize_label(pd.Series(['Acerola, (west indian cherry), raw']))
        self.assertNotIn(', ,', out.iloc[0])
        self.assertNotIn(',,', out.iloc[0])

    def test_no_leading_comma(self):
        out = common.normalize_label(pd.Series(['(raw), beef']))
        self.assertFalse(out.iloc[0].startswith(','))

    def test_no_trailing_comma(self):
        out = common.normalize_label(pd.Series(['Beef, raw, ']))
        self.assertFalse(out.iloc[0].endswith(','))


class GmdControlTest(unittest.TestCase):
    """gutMDisorder 의 **무중재 대조** 판정.

    이걸 틀리면 "요구르트를 먹으면 늘어나는 균" 이 "질환에서 늘어나는 균" 으로
    들어간다 ([`DATA.md`](DATA.md) §12c).
    """

    def test_parts_split(self):
        self.assertEqual(common._gmd_parts('Colitis，Ulcerative;Health'),
                         ['Colitis', 'Ulcerative', 'Health'])

    def test_star_dropped(self):
        self.assertEqual(common._gmd_parts('D003093;*'), ['D003093'])

    def test_null_control_patterns(self):
        for s in ('No yogurt', 'no supplemental fiber', 'Placebos', 'placebo',
                  'Habitual diet', 'Normal chow diet'):
            self.assertIsNotNone(common.GMD_NULL_CONTROL.match(s), s)

    def test_other_diet_is_not_null_control(self):
        for s in ('Soluble corn fiber', 'High resistant starch diet',
                  'Low-fibre/high-fat diet', 'Breast Feeding'):
            self.assertIsNone(common.GMD_NULL_CONTROL.match(s), s)


class ApplyEnvTest(unittest.TestCase):
    """설정이 **쓸기 사이로 새지 않는지** — `run_all.py` 가 이것 때문에 죽었다."""

    def setUp(self):
        self._saved = dict(os.environ)
        common._ENV_BASE = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def test_previous_setting_is_cleared(self):
        common.apply_env({'SIM_SPACE': 'effect'})
        self.assertEqual(os.environ.get('SIM_SPACE'), 'effect')
        common.apply_env({'PCA_COMPONENTS': '5'})
        self.assertIsNone(os.environ.get('SIM_SPACE'))      # ← 새면 여기서 터진다
        self.assertEqual(os.environ.get('PCA_COMPONENTS'), '5')

    def test_base_env_survives(self):
        os.environ['OURKG_TEST_BASE'] = 'keep'
        common._ENV_BASE = dict(os.environ)
        common.apply_env({'E_MODE': 'binary'})
        self.assertEqual(os.environ.get('OURKG_TEST_BASE'), 'keep')

    def test_boot_applied(self):
        common.apply_env({}, boot=(0.8, 7))
        self.assertEqual(os.environ.get('BOOT_FRAC'), '0.8')
        self.assertEqual(os.environ.get('BOOT_SEED'), '7')


class CachedCoveringTest(unittest.TestCase):
    """캐시가 **요청을 덮는지** — 같은 함정을 두 번 당했다(F03 15→6)."""

    def setUp(self):
        self._cache = common.CACHE
        self._dir = tempfile.TemporaryDirectory()
        common.CACHE = self._dir.name

    def tearDown(self):
        common.CACHE = self._cache
        self._dir.cleanup()

    def test_refetch_when_keys_missing(self):
        import json
        calls = []

        def fetch():
            calls.append(1)
            # 두 번째 호출에서야 b 를 돌려준다
            return json.dumps({'a': 1} if len(calls) == 1 else {'a': 1, 'b': 2})

        got = common.cached_covering('t.json', fetch, ['a', 'b'])
        self.assertIn('b', got)                 # 덮지 못하면 다시 받아야 한다
        self.assertEqual(len(calls), 2)

    def test_no_refetch_when_covered(self):
        import json
        calls = []

        def fetch():
            calls.append(1)
            return json.dumps({'a': 1, 'b': 2})

        common.cached_covering('t2.json', fetch, ['a'])
        self.assertEqual(len(calls), 1)


class _OutFixture(unittest.TestCase):
    """`OUT` 을 임시 디렉토리로 바꿔 작은 fixture 로 시험한다."""

    def setUp(self):
        self._out = common.OUT
        self._dir = tempfile.TemporaryDirectory()
        common.OUT = self._dir.name

    def tearDown(self):
        common.OUT = self._out
        self._dir.cleanup()

    def write(self, name, df):
        df.to_csv(os.path.join(common.OUT, name), index=False)


class CanonTest(_OutFixture):
    """병합된 taxid 를 **정본으로 모으는지** — 안 모으면 같은 균을 두 번 센다."""

    def setUp(self):
        super().setUp()
        self.write('microbes.csv', pd.DataFrame([
            {'taxid': '570', 'taxid_current': '570', 'name': 'Klebsiella',
             'rank': 'genus', 'kegg_org': 'kpn', 'match_rank': 'genus',
             'lineage': ''},
            {'taxid': '160674', 'taxid_current': '570', 'name': 'Klebsiella',
             'rank': 'genus', 'kegg_org': 'kpn', 'match_rank': 'genus',
             'lineage': ''},
        ]))

    def test_alias_maps_old_to_current(self):
        a = common.taxid_alias()
        self.assertEqual(a['160674'], '570')
        self.assertEqual(a['570'], '570')

    def test_canon_collapses(self):
        got = common.canon(pd.Series(['160674', '570', '999']))
        self.assertEqual(list(got), ['570', '570', '999'])   # 모르는 id 는 그대로

    def test_compound_microbe_dedupes_on_canonical(self):
        self.write('compound_microbe.csv', pd.DataFrame([
            {'kegg': 'C00001', 'taxid': '570', 'taxid_current': '570',
             'kegg_org': 'kpn', 'n_ko': 3, 'match_rank': 'genus'},
            {'kegg': 'C00001', 'taxid': '160674', 'taxid_current': '570',
             'kegg_org': 'kpn', 'n_ko': 3, 'match_rank': 'genus'},
        ]))
        got = common.compound_microbe(sources=('kegg',))
        self.assertEqual(len(got), 1)            # 두 id 가 한 쌍으로 모여야 한다


class DirectionTest(_OutFixture):
    """방향 **합의/모순** 판정 — 두 소스가 반대면 방향을 주지 않는다."""

    def _md(self, rows):
        return pd.DataFrame(rows, columns=['taxid', 'mesh_id', 'disease',
                                           'outcome', 'is_mental', 'is_neuro'])

    def setUp(self):
        super().setUp()
        self.write('microbes.csv', pd.DataFrame([
            {'taxid': '1', 'taxid_current': '1', 'name': 'A', 'rank': 'genus',
             'kegg_org': '', 'match_rank': '', 'lineage': ''},
            {'taxid': '2', 'taxid_current': '1', 'name': 'A', 'rank': 'genus',
             'kegg_org': '', 'match_rank': '', 'lineage': ''},
        ]))

    def test_agreed_when_same_direction(self):
        self.write('microbe_disease_disbiome.csv', self._md(
            [['1', 'D1', 'Dep', 'Elevated', True, False]]))
        self.write('microbe_disease_gutmdisorder.csv', self._md(
            [['1', 'D1', 'Dep', 'Elevated', True, False]]))
        t = common.microbe_disease_direction()
        self.assertEqual(list(t.status), ['agreed'])
        self.assertEqual(list(t.direction), ['Elevated'])
        self.assertEqual(int(t.n_sources.iloc[0]), 2)

    def test_conflict_when_opposite(self):
        self.write('microbe_disease_disbiome.csv', self._md(
            [['1', 'D1', 'Dep', 'Elevated', True, False]]))
        self.write('microbe_disease_gutmdisorder.csv', self._md(
            [['1', 'D1', 'Dep', 'Reduced', True, False]]))
        t = common.microbe_disease_direction()
        self.assertEqual(list(t.status), ['conflict'])
        self.assertEqual(t.direction.iloc[0], '')      # 방향을 주지 않는다

    def test_merged_taxid_is_compared_as_one(self):
        # 두 소스가 같은 균을 **다른 id** 로 들고 있다. 정본으로 모아야 비교된다
        # — 안 모으면 각각 단일 소스 'agreed' 가 되어 모순을 놓친다.
        self.write('microbe_disease_disbiome.csv', self._md(
            [['1', 'D1', 'Dep', 'Elevated', True, False]]))
        self.write('microbe_disease_gutmdisorder.csv', self._md(
            [['2', 'D1', 'Dep', 'Reduced', True, False]]))
        t = common.microbe_disease_direction()
        self.assertEqual(len(t), 1)
        self.assertEqual(t.status.iloc[0], 'conflict')

    def test_non_directional_outcome_ignored(self):
        self.write('microbe_disease_disbiome.csv', self._md(
            [['1', 'D1', 'Dep', 'Present', True, False]]))
        self.write('microbe_disease_gutmdisorder.csv', self._md(
            [['1', 'D1', 'Dep', 'Elevated', True, False]]))
        t = common.microbe_disease_direction()
        self.assertEqual(list(t.status), ['agreed'])   # Present 는 방향이 아니다


class AdjustedCosineTest(unittest.TestCase):
    """식 (1) 의 **네 선택**을 손계산으로 고정한다.

    음식 3 × compound 3. 0 을 섞어 공통 성분 마스크가 작동하게 했다.

        X = [[1, 2, 0],
             [2, 4, 0],
             [0, 1, 3]]

    행 중심화하면 `Xc0 = [0, 1, -1]` · `Xc1 = [0, 2, -2]` 이고, 0·1 은 비례하므로
    `S[0,1] = 1.0` 이 될 것 같지만 **아니다** — 분자에는 마스크가 걸리고 분모에는
    걸리지 않으므로 `2 / (√2 · 2√2) = 0.5` 다. 그 비대칭이 공식 구현의 선택이고,
    여기서 그 값을 고정한다.
    """

    def setUp(self):
        import numpy as np
        self.np = np
        self.X = np.array([[1.0, 2.0, 0.0],
                           [2.0, 4.0, 0.0],
                           [0.0, 1.0, 3.0]])
        self.S = common.adjusted_cosine(self.X)

    def test_hand_computed_values(self):
        self.assertAlmostEqual(self.S[0, 1], 0.5, places=9)
        self.assertAlmostEqual(self.S[0, 2], -0.109108945, places=7)

    def test_diagonal_is_zero(self):
        # 대각이 남으면 P = D x S 가 자기 점수를 되먹인다.
        for i in range(3):
            self.assertEqual(self.S[i, i], 0.0)

    def test_symmetric(self):
        self.assertTrue(self.np.allclose(self.S, self.S.T))

    def test_row_not_column_centering(self):
        # 열 중심화를 쓰면 값이 달라진다 — 그 오류가 실제로 있었다(파스타 1 위).
        Xc_col = self.X - self.X.mean(axis=0, keepdims=True)
        M = (self.X != 0).astype(float)
        num = (Xc_col * M) @ (Xc_col * M).T
        nrm = self.np.sqrt((Xc_col ** 2).sum(axis=1))
        den = self.np.outer(nrm, nrm)
        S_col = self.np.divide(num, den, out=self.np.zeros_like(num), where=den > 0)
        self.np.fill_diagonal(S_col, 0.0)
        self.assertFalse(self.np.allclose(self.S, S_col))

    def test_mask_applies_to_numerator_only(self):
        # 분모에도 마스크를 걸면 S[0,1] 이 1.0 이 된다. 그러면 안 된다.
        Xc = self.X - self.X.mean(axis=1, keepdims=True)
        M = (self.X != 0).astype(float)
        both = (Xc * M)
        nrm_masked = self.np.sqrt((both ** 2).sum(axis=1))
        s01_masked = float((both[0] * both[1]).sum()
                           / (nrm_masked[0] * nrm_masked[1]))
        self.assertAlmostEqual(s01_masked, 1.0, places=9)
        self.assertNotAlmostEqual(self.S[0, 1], s01_masked, places=6)

    def test_zero_row_gives_zero_not_nan(self):
        import numpy as np
        X = np.array([[1.0, 1.0], [0.0, 0.0]])
        S = common.adjusted_cosine(X)
        self.assertFalse(np.isnan(S).any())


class ResolveETest(unittest.TestCase):
    """`E_MODE` 해석 — 모르는 모드는 **조용히 기본값으로 떨어지면 안 된다**."""

    def setUp(self):
        import analyze
        self.analyze = analyze
        self.E = pd.DataFrame({
            'kegg': ['C1', 'C2'], 'e_shrunk': [0.5, -0.5],
            'e_binary': [1.0, -1.0], 'q': [0.01, 0.5],
        }).set_index('kegg')

    def test_shrunk_and_binary_differ(self):
        a = self.analyze.resolve_e('shrunk', self.E)
        b = self.analyze.resolve_e('binary', self.E)
        self.assertEqual(list(a), [0.5, -0.5])
        self.assertEqual(list(b), [1.0, -1.0])

    def test_sig_zeroes_nonsignificant(self):
        got = self.analyze.resolve_e('sig', self.E)
        self.assertEqual(list(got), [1.0, 0.0])      # q=0.5 는 0 이 된다

    def test_unknown_mode_exits(self):
        with self.assertRaises(SystemExit):
            self.analyze.resolve_e('이런모드는없다', self.E)


class ModimedTest(unittest.TestCase):
    """외부 기준 라벨 — **CSV 가 아니라 코드가 계산한다.**

    규칙이 드리프트하면 모든 쓸기 수치가 조용히 바뀐다(§4.5 에서 확인).
    """

    def setUp(self):
        import analyze
        self.analyze = analyze

    def _foods(self, rows):
        return pd.DataFrame(rows, columns=['food_name', 'food_group'])

    def test_prescribed_and_extras(self):
        f = self._foods([
            ['Broccoli, raw', 'Vegetables and Vegetable Products'],
            ['Candy, milk chocolate', 'Sweets'],
        ])
        lab, why = self.analyze.modimed_labels(f)
        self.assertEqual(lab.iloc[0], 1)
        self.assertEqual(lab.iloc[1], -1)

    def test_baby_food_excluded(self):
        # SMILES 는 성인 대상이다 — 이유식은 처방 대상이 아니다.
        f = self._foods([['Baby food, vegetable, carrots', 'Baby Foods']])
        lab, _ = self.analyze.modimed_labels(f)
        self.assertEqual(lab.iloc[0], 0)

    def test_score_counts_top_and_bottom(self):
        f = pd.DataFrame({
            'food_name': ['Broccoli, raw', 'Spinach, raw',
                          'Candy, milk chocolate', 'Cookies, sugar'],
            'food_group': ['Vegetables and Vegetable Products',
                           'Vegetables and Vegetable Products', 'Sweets', 'Sweets'],
            'score': [1.0, 0.9, -0.9, -1.0],
        })
        sc = self.analyze.modimed_score(f, 2)
        # 키 이름이 `top{K}_처방군` 꼴이다 — 추측하지 않고 실제 키로 고정한다.
        self.assertEqual(sc['top2_처방군'], 2)        # Top 2 가 채소 둘
        self.assertEqual(sc['top2_extras'], 0)
        self.assertEqual(sc['bot2_extras'], 2)        # Bottom 2 가 과자 둘
        self.assertAlmostEqual(sc['modimed_AUC(참고)'], 1.0)   # 완전 분리

    def test_score_empty_when_one_side_missing(self):
        # 한쪽이 없으면 AUC 가 정의되지 않는다 — 빈 dict 를 돌려준다.
        f = pd.DataFrame({'food_name': ['Broccoli, raw'],
                          'food_group': ['Vegetables and Vegetable Products'],
                          'score': [1.0]})
        self.assertEqual(self.analyze.modimed_score(f, 1), {})


class ComplicationGateTest(unittest.TestCase):
    """합병증 추론 — **포개진 집합이면 검정을 돌리지 않는다.**

    `-1` 정답셋이 없어서 판정 못 한다고 적어 뒀는데, 라벨 없이 답할 수 있다.
    집합이 포개져 있으면 "기대보다 많다" 가 구조적으로 보장되기 때문이다.
    """

    def setUp(self):
        import complication
        self.c = complication

    def test_nested_sets_detected(self):
        # 한 질환이 universe 전체를 갖는다 — 모든 쌍에서 자동 통과한다.
        sets = {'A': {1, 2, 3, 4}, 'B': {1, 2}, 'C': {3, 4}}
        t, s = self.c.specificity(sets)
        self.assertEqual(s['universe'], 4)
        self.assertEqual(s['universe 를 다 가진 질환'], 1)
        # A-B, A-C 는 포개짐, B-C 는 아니다
        self.assertEqual(s['포개진 쌍'], 2)
        self.assertAlmostEqual(s['포개짐 비율'], 2 / 3, places=3)

    def test_specific_sets_pass(self):
        sets = {'A': {1, 2, 3}, 'B': {4, 5, 6}, 'C': {7, 8, 9}}
        _, s = self.c.specificity(sets)
        self.assertEqual(s['포개진 쌍'], 0)
        self.assertEqual(s['Jaccard 중앙값'], 0.0)

    def test_jaccard_range(self):
        t, _ = self.c.specificity({'A': {1, 2}, 'B': {1, 2}})
        self.assertEqual(t.Jaccard.iloc[0], 1.0)
        self.assertTrue(bool(t['포개짐'].iloc[0]))

    def test_hypergeom_flags_excess_overlap(self):
        # universe 는 **sets 의 합집합**이다(여기서 31). 10 개짜리 두 집합이
        # 9 개를 공유하면 우연이 아니고, 안 겹치는 쌍은 p=1 이어야 한다.
        sets = {'A': set(range(10)), 'B': set(range(1, 11)),
                'C': set(range(50, 60)), 'D': set(range(90, 100))}
        h = self.c.hypergeom(sets)
        ab = h[(h.a == 'A') & (h.b == 'B')].iloc[0]
        self.assertEqual(ab['공유'], 9)
        self.assertLess(ab['p'], 1e-4)
        cd = h[(h.a == 'C') & (h.b == 'D')].iloc[0]
        self.assertEqual(cd['공유'], 0)
        self.assertAlmostEqual(cd['p'], 1.0, places=6)

    def test_paper_pairs_table_shape(self):
        # 논문 Table 5 의 합병증 문항은 8 개이고, 그중 2 개가 논문 판정 0 이다
        # — **그게 -1 정답셋이다**(외부에서 구할 필요가 없었다).
        self.assertEqual(len(self.c.PAPER_PAIRS), 8)
        labels = [p[4] for p in self.c.PAPER_PAIRS]
        self.assertEqual(sum(1 for x in labels if x == 0), 2)
        self.assertEqual(sum(1 for x in labels if x == 1), 6)

    def test_paper_eval_on_curated(self):
        # 잴 수 있는 6 개가 전부 일치하고, 못 재는 2 개는 사유가 적혀야 한다.
        pe, src = self.c.paper_eval('curated')
        self.assertEqual(src, 'curated')
        self.assertEqual(len(pe), 8)
        na = pe[pe['판정'] == '못 잼']
        self.assertEqual(len(na), 2)
        self.assertTrue((na['사유'] != '').all())
        got = pe[pe['판정'] != '못 잼']
        self.assertEqual(len(got), 6)
        self.assertTrue((got['판정'] == '일치').all(), got.to_string())

    def test_paper_negative_is_rejected(self):
        # #6 파킨슨-자폐는 논문이 0 으로 둔 문항이다. MiKG 경로로는 우리가 1 로
        # 통과시켰다(위양성). curated 에서는 0 이어야 한다.
        pe, _ = self.c.paper_eval('curated')
        r = pe[pe.no == 6].iloc[0]
        self.assertEqual(r['논문'], 0)
        self.assertEqual(r['우리'], 0)

    def test_source_must_be_known(self):
        import os
        old = os.environ.get('COMP_SOURCE')
        os.environ['COMP_SOURCE'] = '없는소스'
        try:
            with self.assertRaises(SystemExit):
                self.c.disease_sets()
        finally:
            if old is None:
                os.environ.pop('COMP_SOURCE', None)
            else:
                os.environ['COMP_SOURCE'] = old


class SignAgreeTest(unittest.TestCase):
    """부호일치 검정의 **귀무** (`common.sign_agree`) — §48 의 회귀 시험."""

    def test_skewed_marginals_give_null_above_half(self):
        # 양쪽이 치우쳐 있으면 무작위로 짝지어도 많이 맞는다. 0.5 를 귀무로
        # 쓰면 p 가 터진다 — 이 저장소가 p=4.9e-5 를 신호로 읽을 뻔한 자리.
        a = [1] * 77 + [-1] * 132
        b = [1] * 37 + [-1] * 172
        obs, null, p, n = common.sign_agree(a, b, n_perm=3000)
        self.assertEqual(n, 209)
        self.assertGreater(null, 0.55)          # 0.5 가 아니다
        self.assertTrue(0 <= p <= 1)

    def test_balanced_marginals_give_null_near_half(self):
        a = [1] * 100 + [-1] * 100
        b = [1] * 100 + [-1] * 100
        _, null, _, _ = common.sign_agree(a, b, n_perm=3000)
        self.assertAlmostEqual(null, 0.5, delta=0.03)

    def test_perfect_agreement_is_significant(self):
        a = [1] * 60 + [-1] * 60
        obs, null, p, _ = common.sign_agree(a, a, n_perm=2000)
        self.assertEqual(obs, 1.0)
        self.assertLess(p, 0.001)

    def test_empty_is_safe(self):
        obs, null, p, n = common.sign_agree([], [], n_perm=10)
        self.assertEqual(n, 0)

    def test_mdes_centre_moves_with_p0(self):
        # 귀무가 올라가면 경계도 올라간다. 0.5 를 박아 두면 경계가 낙관적이다.
        self.assertGreater(common.mdes(209, 0.05, p0=0.585),
                           common.mdes(209, 0.05, p0=0.5))


class SimMaskTest(unittest.TestCase):
    """공통 성분 마스크 (`adjusted_cosine(X, reported)`) — §52.

    FDC 가 "측정했고 0" 으로 보고한 칸과 "보고하지 않은" 칸이 `0` 으로 같아져
    있었다. 마스크를 주입할 수 있게 하고, **주면 값이 실제로 달라지는지**를
    고정한다 — 안 달라지면 스위치가 있는 척만 하는 것이다.
    """

    def test_mask_changes_the_value(self):
        import numpy as np
        X = np.array([[1., 0., 2.], [1., 0., 3.]])
        allrep = np.ones_like(X, dtype=bool)
        a = common.adjusted_cosine(X)[0, 1]
        b = common.adjusted_cosine(X, allrep)[0, 1]
        self.assertNotAlmostEqual(a, b, places=3)

    def test_default_is_nonzero_mask(self):
        # 기본은 논문 식 (1) 그대로여야 한다 — 측정으로 기각된 쪽으로
        # 기본값이 조용히 넘어가면 안 된다.
        import numpy as np
        X = np.array([[1., 0., 2.], [1., 0., 3.]])
        self.assertTrue(np.allclose(common.adjusted_cosine(X),
                                    common.adjusted_cosine(X, X != 0)))

    def test_diagonal_zero_and_symmetry_hold_with_mask(self):
        import numpy as np
        rng = np.random.default_rng(0)
        X = rng.random((6, 5)) * (rng.random((6, 5)) > 0.3)
        R = rng.random((6, 5)) > 0.2
        S = common.adjusted_cosine(X, R)
        self.assertTrue(np.allclose(np.diag(S), 0))
        self.assertTrue(np.allclose(S, S.T))

    def test_sweep_registered(self):
        import sweep
        self.assertIn('simmask', sweep.SWEEPS)
        _, cfgs = sweep.SWEEPS['simmask']
        self.assertEqual(len(cfgs), 8)       # 마스크 2 x 공간 2 x 열 2


class EnvDefaultTest(unittest.TestCase):
    """환경변수 기본값의 **단일성** — 한쪽만 되돌아간 자리 (§51)."""

    def test_ensemble_default_is_one_place(self):
        import analyze
        self.assertEqual(analyze.ENSEMBLE_DEFAULT, 'none')
        self.assertEqual(analyze.ensemble_modes(), [])

    def test_basis_falls_back_to_scoring_mode(self):
        # 앙상블을 끄면 근거 E 는 점수 E(`shrunk`)와 같아야 한다. 대체값이
        # `union_all` 로 남아 있어 끄는 순간 또 다른 E 로 떨어졌다.
        src = open(os.path.join(_chk.HERE, 'analyze.py'), encoding='utf-8').read()
        self.assertIn("os.environ.get('E_MODE', 'shrunk')", src)
        # 반례 문자열을 그대로 쓰면 `env` 검사가 이 파일을 잡는다 — 쪼개서 쓴다.
        self.assertNotIn("os.environ.get('E_MODE', " + "'union_all')", src)

    def test_checker_catches_a_split_default(self):
        # 오류 주입 — 같은 변수에 다른 기본값을 쓰는 파일을 만들어 FAIL 을 본다.
        import tempfile
        d = tempfile.TemporaryDirectory()
        saved = _chk.HERE
        try:
            for name, body in (('a', "import os\nos.environ.get('X_SW', 'on')\n"),
                               ('b', "import os\nos.environ.get('X_SW', 'off')\n")):
                with open(os.path.join(d.name, name + '.py'), 'w') as f:
                    f.write(body)
            _chk.HERE = d.name
            _chk.RESULT.clear()
            try:
                _chk.check_env()
            except Exception:
                pass
            sts = [r[0] for r in _chk.RESULT if r[1] == '환경변수 기본값 단일성']
            self.assertEqual(sts, ['FAIL'])
        finally:
            _chk.HERE = saved
            _chk.RESULT.clear()
            d.cleanup()


class FoodSourceTest(unittest.TestCase):
    """음식 출처 기록 (`foods.csv` 의 `n_source`·`source_types`·`label_share`).

    `fdc_id`·`data_type` 은 큐레이션 순위로 고른 **대표 1 건**인데 성분값은 같은
    라벨 전체의 평균이다. 기록이 없으면 **1 건 측정과 2,456 건 평균을 구분할 수
    없다**(§50). 더 나쁜 것은 대표 선택이 그림을 뒤집는다는 것이다 — 라벨이
    출처의 0.04% 인 경우가 있다.
    """

    def setUp(self):
        import os
        p = os.path.join(common.OUT, 'foods.csv')
        if not os.path.exists(p):
            self.skipTest('foods.csv 없음')
        self.f = pd.read_csv(p)
        if 'n_source' not in self.f:
            self.skipTest('출처 열이 아직 없다 — build.py food 를 돌려라')

    @staticmethod
    def _parse(s):
        if not isinstance(s, str) or not s:
            return {}
        return dict((k, int(v)) for k, v in (p.split(':') for p in s.split(';')))

    def test_counts_match_source_types(self):
        for r in self.f.itertuples(index=False):
            d = self._parse(r.source_types)
            if d:
                self.assertEqual(sum(d.values()), int(r.n_source), r.food_name)

    def test_label_share_matches_types(self):
        for r in self.f.itertuples(index=False):
            d = self._parse(r.source_types)
            if d:
                exp = d.get(r.data_type, 0) / sum(d.values())
                self.assertAlmostEqual(float(r.label_share), exp, places=3,
                                       msg=r.food_name)

    def test_single_source_is_fully_its_own_label(self):
        one = self.f[self.f.n_source == 1]
        self.assertTrue((one.label_share == 1.0).all())

    def test_minority_label_exists_and_is_recorded(self):
        # 이 사실 자체가 §50 의 발견이다 — 사라지면 기록이 거짓이 된다.
        multi = self.f[self.f.n_source > 1]
        self.assertGreater(len(multi), 0)
        self.assertGreater(int((multi.label_share < 0.5).sum()), 0)


class DiseaseKeyTest(unittest.TestCase):
    """질환 묶음 키 (`common.disease_key`) — 같은 질환이 둘로 세어지던 자리."""

    def test_plural_and_possessive_fold(self):
        k = common.disease_key
        self.assertEqual(k('Learning disorder'), k('Learning disorders'))
        self.assertEqual(k("Parkinson's Disease"), k('Parkinson Disease'))

    def test_distinct_diseases_do_not_collide(self):
        # **과하게 접으면 다른 질환이 합쳐진다.** MiKG 의 11 개 이름에서
        # 의도한 하나(Learning disorder/disorders)만 합쳐져야 한다.
        names = ['Anxiety disorders', 'Autistic disorder', 'Bipolar disorder',
                 'Cognition disorders', 'Depressive disorder', 'Eating disorders',
                 'Learning disorder', 'Learning disorders', 'Personality disorder',
                 'Sex behavior disorder', 'Sleep disorders']
        keys = [common.disease_key(n) for n in names]
        self.assertEqual(len(set(keys)), 10)

    def test_empty_and_odd_input(self):
        for n in ('', None, 123, float('nan')):
            self.assertEqual(common.disease_key(n), '')

    def test_mikg_sets_group_by_key(self):
        # mikg 경로가 이름 그대로 묶으면 질환이 11 개가 된다.
        import os
        import complication
        if not os.path.exists(os.path.join(common.OUT,
                                           'microbe_disease_mikg.csv')):
            self.skipTest('microbe_disease_mikg.csv 없음')
        sets, src = complication.disease_sets('mikg')
        self.assertEqual(src, 'mikg')
        self.assertEqual(len(sets), 10)
        self.assertNotIn('Learning disorder', sets)      # 긴 표기를 쓴다
        self.assertIn('Learning disorders', sets)


class GenusKeyTest(unittest.TestCase):
    """속 조인 키 (`common.genus_key`) — **두 분류체계를 맞추는 자리.**

    그냥 이름으로 조인해서 측정 쌍 39,574 중 35,450(89.6%)을 버리고 있었다.
    맞추는 것과 **일부러 안 맞추는 것**을 둘 다 고정한다 — 뒤에서 "커버리지를
    더 올리자" 며 대괄호를 떼면 틀린 쪽으로 늘어난다.
    """

    def test_gtdb_suffix_stripped(self):
        for a, b in (('Alistipes_A', 'Alistipes'), ('Eubacterium_R', 'Eubacterium'),
                     ('Ruminococcus_B', 'Ruminococcus')):
            self.assertEqual(common.genus_key(a), b)

    def test_plain_names_untouched(self):
        for n in ('Bacteroides', 'Bacteroides fragilis', 'Prevotella copri'):
            self.assertEqual(common.genus_key(n), n.split()[0])

    def test_candidatus_uses_second_token(self):
        # `Candidatus Soleaferrea` 의 속은 Soleaferrea 이고 측정 쪽에 있다.
        self.assertEqual(common.genus_key('Candidatus Soleaferrea'), 'Soleaferrea')
        self.assertEqual(common.genus_key('Candidatus'), '')

    def test_uncultured_has_no_genus(self):
        for n in ('uncultured bacterium', 'uncultured organism', 'uncultured'):
            self.assertEqual(common.genus_key(n), '')

    def test_brackets_are_kept(self):
        # **일부러 안 맞춘다.** NCBI 의 [Clostridium] innocuum 은 실제로
        # Clostridium 이 아니다 — 떼면 틀린 균에 측정 상관이 붙는다.
        self.assertEqual(common.genus_key('[Clostridium] innocuum'), '[Clostridium]')
        self.assertNotEqual(common.genus_key('[Clostridium] innocuum'),
                            common.genus_key('Clostridium innocuum'))

    def test_empty_and_odd_input(self):
        # NaN 이 'nan' 이라는 가짜 속이 되면 안 된다.
        for n in ('', '   ', None, float('nan'), 123):
            self.assertEqual(common.genus_key(n), '')

    def test_links_are_additive_not_lossy(self):
        # 정규화는 **순증**이어야 한다. 사라진 쌍이 있으면 키가 뭉갠 것이다.
        import pandas as pd, os
        if not os.path.exists(os.path.join(common.OUT,
                                           'compound_microbe_measured.csv')):
            self.skipTest('측정 표 없음')
        m = pd.read_csv(os.path.join(common.OUT, 'compound_microbe_measured.csv'))
        mic = pd.read_csv(os.path.join(common.OUT, 'microbes.csv'),
                          dtype={'taxid': str}).fillna('')
        mic['genus'] = mic['name'].astype(str).str.split().str[0]
        old = m.merge(mic[['taxid', 'genus']], on='genus')[['taxid', 'kegg']]
        old['taxid'] = common.canon(old['taxid'])
        o = set(map(tuple, old.drop_duplicates().values))
        n = set(map(tuple, common.measured_links().values))
        self.assertEqual(o - n, set(), '정규화가 기존 쌍을 잃었다')
        self.assertGreater(len(n), len(o))


class MdesTest(unittest.TestCase):
    """최소검출효과 — 검정력 경계를 계산으로 고정한다 (§34)."""

    def setUp(self):
        import e_autism
        self.e = e_autism

    def test_monotone_in_n(self):
        # n 이 커지면 잡아낼 수 있는 효과는 **작아진다.** 이 단조성이 깨지면
        # 경계를 "n 이 가장 큰 검정" 에서 읽는 §34 의 논법이 무너진다.
        v = [self.e.mdes(n, 0.05) for n in (45, 100, 200, 384)]
        self.assertEqual(v, sorted(v, reverse=True))
        self.assertTrue(all(0.5 < x < 1 for x in v))

    def test_stricter_alpha_raises_bound(self):
        # BH 보정은 alpha 를 낮춘다 -> 경계는 올라간다(더 큰 효과만 잡힌다).
        self.assertGreater(self.e.mdes(384, 0.05 / 28), self.e.mdes(384, 0.05))

    def test_auc_bound_is_tighter_with_balanced_groups(self):
        # 같은 전체 n 이면 두 군이 고를수록 AUC 경계가 조여진다.
        import common
        bal = common.mdes_auc(232, 233, 0.05)
        skew = common.mdes_auc(129, 336, 0.05)
        self.assertLess(bal, skew)
        self.assertTrue(all(0.5 < x < 1 for x in (bal, skew)))

    def test_auc_bound_monotone_in_n(self):
        import common
        v = [common.mdes_auc(int(n / 2), n - int(n / 2), 0.05)
             for n in (60, 200, 465, 2000)]
        self.assertEqual(v, sorted(v, reverse=True))

    def test_each_claim_has_its_own_multiplicity(self):
        # **처음에 틀린 자리.** 세 주장 전부에 alpha/28 을 걸었다. 28 은
        # 미생물 축에서 잰 칸 수고, 나머지 둘은 단일 검정이다.
        import pandas as pd, os
        f = os.path.join(self.e.OUT, 'power_bound.csv')
        if not os.path.exists(f):
            self.skipTest('power_bound.csv 없음')
        t = pd.read_csv(f)
        for claim, g in t.groupby('주장'):
            if claim == '미생물 축 부호일치':
                self.assertTrue((g['보정검정수'] > 1).all(), claim)
                self.assertTrue((g['경계(보정후)'] > g['경계(a=0.05)']).all())
            else:
                self.assertTrue((g['보정검정수'] == 1).all(), claim)
                self.assertTrue((g['경계(보정후)'] == g['경계(a=0.05)']).all())

    def test_detected_effect_is_not_called_excluded(self):
        # 유의한 관측에 "배제된다" 를 붙이면 거짓말이 된다. lift 는 p=0.0068 이다.
        import pandas as pd, os
        f = os.path.join(self.e.OUT, 'power_bound.csv')
        if not os.path.exists(f):
            self.skipTest('power_bound.csv 없음')
        t = pd.read_csv(f)
        sig = t[t.p < 0.05 / t['보정검정수']]
        self.assertTrue(len(sig) >= 1, '유의한 행이 하나는 있어야 이 시험이 산다')

    def test_report_picks_tightest_not_largest_effect(self):
        # **처음에 틀린 자리.** 부호일치가 가장 큰 행을 골라 0.77 이라는 느슨한
        # 경계를 냈다. 경계는 MDES 가 가장 작은 행에서 읽어야 한다.
        import pandas as pd, os
        f = os.path.join(self.e.OUT, 'power_bound.csv')
        if not os.path.exists(f):
            self.skipTest('power_bound.csv 없음')
        t = pd.read_csv(f)
        bh = '경계(보정후)'
        m = t[t['주장'] == '미생물 축 부호일치']
        # **귀무가 행마다 달라 경계끼리 바로 비교할 수 없다**(§48). 같은 귀무
        # 안에서는 n 이 클수록 경계가 낮다 — 그 불변식만 본다.
        for _, g in m.groupby(m['귀무'].round(3)):
            if len(g) > 1:
                self.assertLessEqual(
                    float(g.loc[g.n.idxmax()][bh]),
                    float(g.loc[g.n.idxmin()][bh]) + 1e-9)
        # 보고가 고르는 행은 **귀무 위 초과분**이 가장 작은 행이어야 한다 —
        # 관측이 가장 큰 행(n 이 작아 경계가 느슨하다)이 아니다.
        pick = m.loc[(m[bh] - m['귀무']).idxmin()]
        self.assertNotEqual(int(pick.n), int(m.loc[m['관측'].idxmax()].n))

    def test_null_is_not_hardcoded_half(self):
        # 0.5 를 박아 두고 p=4.9e-5 를 신호로 읽을 뻔했다 (§48).
        import pandas as pd, os
        f = os.path.join(self.e.OUT, 'power_bound.csv')
        if not os.path.exists(f):
            self.skipTest('power_bound.csv 없음')
        t = pd.read_csv(f)
        m = t[t['주장'] == '미생물 축 부호일치']
        self.assertGreater(m['귀무'].nunique(), 1, '귀무가 전부 같다 — 또 박혔다')
        self.assertTrue((m['경계(보정후)'] > m['귀무']).all())
        # 경계를 넘은 관측이 있으면 "배제된다" 고 쓸 수 없다.
        self.assertEqual(int(t['≥경계라면 잡혔다'].sum()), 0)


class AnchorRegexTest(unittest.TestCase):
    """문서 수치 앵커 — 검사가 **스스로를 속였던** 자리의 회귀 시험."""

    def test_uppercase_name_matched(self):
        # 처음 판은 이름을 [a-z_.]+ 로 받아 이 앵커를 **아예 못 봤다**.
        got = check._ANCHOR.findall('**135**<!--chk:F.compounds-->')
        self.assertEqual(got, [('135', 'F.compounds')])

    def test_number_must_be_adjacent(self):
        # 표에서 앞 칸 숫자를 집던 버그. 사이에 글자가 끼면 안 걸려야 한다.
        self.assertEqual(check._ANCHOR.findall('| 1 | 1,192 | 46,495<!--chk:links.vmh-->'),
                         [('46,495', 'links.vmh')])
        self.assertEqual(check._ANCHOR.findall('46,495 링크<!--chk:links.vmh-->'), [])

    def test_malformed_is_countable(self):
        txt = '설명 <!--chk:kg.triples-->'
        self.assertEqual(len(check._ANCHOR_ANY.findall(txt)), 1)
        self.assertEqual(len(check._ANCHOR.findall(txt)), 0)

    def test_digit_in_name_matched(self):
        # 세 번째 재발. `[A-Za-z_.]+` 는 숫자가 들어간 이름을 못 봤다.
        got = check._ANCHOR.findall('7<!--chk:repro.t5_complication-->')
        self.assertEqual(got, [('7', 'repro.t5_complication')])
        got2 = check._ANCHOR.findall('8<!--chk:repro.table3-->')
        self.assertEqual(got2, [('8', 'repro.table3')])

    def test_unknown_name_is_parsed_not_ignored(self):
        # 틀린 이름은 **못 보고 지나가는 것**이 아니라 잡혀서
        # "모르는 앨커" 로 FAIL 해야 한다.
        got = check._ANCHOR.findall('1<!--chk:없는.사실-->')
        self.assertEqual(len(got), 1)

    def test_comma_format(self):
        got = check._ANCHOR.findall('음식 **14,886<!--chk:foods.count--> 종**')
        self.assertEqual(got, [('14,886', 'foods.count')])


class CompoundMicrobeRankTest(_OutFixture):
    """속 수준 링크를 **거를 수 있어야** 한다 — 이름 지정 종 질문에는 종만 쓴다."""

    def setUp(self):
        super().setUp()
        self.write('microbes.csv', pd.DataFrame([
            {'taxid': '1', 'taxid_current': '1', 'name': 'A b', 'rank': 'species',
             'kegg_org': 'x', 'match_rank': 'species', 'lineage': ''}]))
        self.write('compound_microbe.csv', pd.DataFrame([
            {'kegg': 'C1', 'taxid': '1', 'taxid_current': '1', 'kegg_org': 'x',
             'n_ko': 1, 'match_rank': 'species'},
            {'kegg': 'C2', 'taxid': '1', 'taxid_current': '1', 'kegg_org': 'x',
             'n_ko': 1, 'match_rank': 'genus'},
        ]))

    def test_species_filter(self):
        self.assertEqual(set(common.compound_microbe(sources=('kegg',),
                                                     rank='species').kegg), {'C1'})

    def test_all_by_default(self):
        self.assertEqual(set(common.compound_microbe(sources=('kegg',)).kegg),
                         {'C1', 'C2'})


# ======================================================================
# 검사기를 검사한다 (메타 시험)
#
# `check.py` 가 틀리면 **조용히 통과한다.** 이미 두 번 그랬다 — 예외로 죽어
# 뒤 검사가 안 돌았고, 대문자 앵커를 못 보면서 "15 개 통과" 라고 보고했다.
# 그때마다 손으로 고장을 넣어 확인했는데 그 확인이 자동화돼 있지 않았다
# ([`PROCESS.md`](PROCESS.md)). 여기서 자동화한다.
#
# 각 검사마다 **두 번** 본다 — 정상 fixture 에서 PASS 하고, 고장을 넣으면 FAIL.
# 둘 다 봐야 의미가 있다. 늘 FAIL 하는 검사는 쓸모없고, 늘 PASS 하는 검사는
# 있는 척만 한다.
import check as _chk                                   # noqa: E402


class _CheckFixture(unittest.TestCase):
    """`check.OUT` · `common.OUT` 을 임시 디렉토리로 돌리고 정상 fixture 를 깐다."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self._saved = (_chk.OUT, common.OUT, _chk.HERE, list(_chk.RESULT))
        _chk.OUT = common.OUT = self._dir.name
        _chk.RESULT.clear()
        self.good()

    def tearDown(self):
        _chk.OUT, common.OUT, _chk.HERE, res = self._saved
        _chk.RESULT.clear()
        _chk.RESULT.extend(res)
        self._dir.cleanup()

    def w(self, name, df):
        df.to_csv(os.path.join(_chk.OUT, name), index=False)

    def good(self):
        """모든 검사가 통과하는 최소 fixture."""
        self.w('microbes.csv', pd.DataFrame([
            {'taxid': '1', 'name': 'A b', 'rank': 'species', 'lineage': 'x',
             'kegg_org': 'ab', 'match_rank': 'species', 'taxid_current': '1'}]))
        self.w('compound_microbe.csv', pd.DataFrame([
            {'kegg': 'C1', 'taxid': '1', 'taxid_current': '1', 'kegg_org': 'ab',
             'n_ko': 2, 'match_rank': 'species'}]))
        md = pd.DataFrame([{'taxid': '1', 'mesh_id': 'D1', 'disease': 'Dep',
                            'outcome': 'Elevated', 'is_mental': True,
                            'is_neuro': False}])
        self.w('microbe_disease_disbiome.csv', md)
        self.w('microbe_disease_gutmdisorder.csv', md)
        self.w('microbe_disease_agreement.csv', pd.DataFrame([
            {'taxid': '1', 'mesh_id': 'D1', 'disease': 'Dep', 'status': 'agreed',
             'direction': 'Elevated', 'n_sources': 2, 'sources': 'a+b',
             'n_elevated': 2, 'n_reduced': 0}]))
        self.w('recommendation.csv', pd.DataFrame([
            {'rank': 1, 'food_key': 'a', 'score': 1.0, 'food_group': 'G',
             'food_name': 'A'},
            {'rank': 2, 'food_key': 'b', 'score': 0.5, 'food_group': 'G',
             'food_name': 'B'}]))
        self.w('foods.csv', pd.DataFrame([
            {'food_key': 'a', 'food_name': 'A', 'data_type': 't',
             'n_compound': 20, 'n_source': 1, 'source_types': 't:1',
             'label_share': 1.0}]))
        self.w('compound_depression.csv', pd.DataFrame([
            {'kegg': 'C1', 'e_shrunk': 0.5, 'e_binary': 1.0, 'q': 0.01}]))
        self.w('kg_stats.csv', pd.DataFrame([
            {'source': 'S1', 'relation': 1, 'entity': 2, 'triples': 10},
            {'source': 'Σ 출처 주장(겹침 포함)', 'relation': 1, 'entity': 2,
             'triples': 10},
            {'source': 'Total (고유 그래프)', 'relation': 1, 'entity': 2,
             'triples': 10}]))

    def run_check(self, fn):
        _chk.RESULT.clear()
        import contextlib
        import io as _io
        with contextlib.redirect_stdout(_io.StringIO()):
            fn()
        return [st for st, *_ in _chk.RESULT]

    def assertPasses(self, fn):
        sts = self.run_check(fn)
        self.assertNotIn('FAIL', sts, f'정상 fixture 인데 FAIL: {_chk.RESULT}')

    def assertFails(self, fn):
        sts = self.run_check(fn)
        self.assertIn('FAIL', sts, f'고장을 넣었는데 FAIL 이 없다: {_chk.RESULT}')


class MetaSchemaTest(_CheckFixture):
    def test_passes_when_good(self):
        self.assertPasses(_chk.check_schema)

    def test_fails_on_missing_column(self):
        m = pd.read_csv(os.path.join(_chk.OUT, 'microbes.csv'))
        self.w('microbes.csv', m.drop(columns=['taxid_current']))
        self.assertFails(_chk.check_schema)


class MetaMicrobeTest(_CheckFixture):
    def test_passes_when_good(self):
        self.assertPasses(_chk.check_microbe)

    def test_fails_when_disease_taxid_absent_from_axis(self):
        # 질환 관계가 축에 없는 균을 가리킨다 — 병합 taxid 버그의 모양.
        md = pd.read_csv(os.path.join(_chk.OUT, 'microbe_disease_disbiome.csv'),
                         dtype={'taxid': str})
        md.loc[0, 'taxid'] = '999'
        self.w('microbe_disease_disbiome.csv', md)
        self.assertFails(_chk.check_microbe)


class MetaLinksTest(_CheckFixture):
    def test_passes_when_good(self):
        self.assertPasses(_chk.check_links)

    def test_fails_on_duplicate_pair(self):
        cm = pd.read_csv(os.path.join(_chk.OUT, 'compound_microbe.csv'),
                         dtype={'taxid': str, 'taxid_current': str})
        self.w('compound_microbe.csv', pd.concat([cm, cm]))
        self.assertFails(_chk.check_links)


class MetaAgreementTest(_CheckFixture):
    def test_passes_when_good(self):
        self.assertPasses(_chk.check_agreement)

    def test_fails_when_conflict_has_direction(self):
        a = pd.read_csv(os.path.join(_chk.OUT, 'microbe_disease_agreement.csv'),
                        dtype={'taxid': str})
        a.loc[0, 'status'] = 'conflict'          # 방향은 그대로 남겨 둔다
        self.w('microbe_disease_agreement.csv', a)
        self.assertFails(_chk.check_agreement)

    def test_fails_on_unknown_status(self):
        a = pd.read_csv(os.path.join(_chk.OUT, 'microbe_disease_agreement.csv'),
                        dtype={'taxid': str})
        a.loc[0, 'status'] = 'maybe'
        self.w('microbe_disease_agreement.csv', a)
        self.assertFails(_chk.check_agreement)


class MetaRecommendTest(_CheckFixture):
    def test_passes_when_good(self):
        self.assertPasses(_chk.check_recommend)

    def test_fails_on_broken_rank(self):
        r = pd.read_csv(os.path.join(_chk.OUT, 'recommendation.csv'))
        r.loc[1, 'rank'] = 5
        self.w('recommendation.csv', r)
        self.assertFails(_chk.check_recommend)

    def test_fails_on_non_monotone_score(self):
        r = pd.read_csv(os.path.join(_chk.OUT, 'recommendation.csv'))
        r.loc[1, 'score'] = 9.0                  # rank 2 가 rank 1 보다 높다
        self.w('recommendation.csv', r)
        self.assertFails(_chk.check_recommend)


class MetaKgStatsTest(_CheckFixture):
    def test_passes_when_good(self):
        self.assertPasses(_chk.check_kg)

    def test_fails_when_source_sum_mismatches(self):
        k = pd.read_csv(os.path.join(_chk.OUT, 'kg_stats.csv'))
        k.loc[0, 'triples'] = 999
        self.w('kg_stats.csv', k)
        self.assertFails(_chk.check_kg)

    def test_fails_when_unique_exceeds_claims(self):
        k = pd.read_csv(os.path.join(_chk.OUT, 'kg_stats.csv'))
        k.loc[2, 'triples'] = 99                 # 고유 > Σ 주장 은 불가능하다
        self.w('kg_stats.csv', k)
        self.assertFails(_chk.check_kg)


class MetaPathcheckTest(_CheckFixture):
    def _write(self, d):
        import json
        json.dump(d, open(os.path.join(_chk.OUT, 'gutbrain_compounds.json'), 'w'))

    def test_passes_when_agree(self):
        self._write({'kegg': ['C1'], 'agree': True, 'n_csv': 1, 'n_kg': 1,
                     'only_csv': [], 'only_kg': []})
        self.assertPasses(_chk.check_pathcheck)

    def test_fails_when_disagree(self):
        self._write({'kegg': ['C1'], 'agree': False, 'n_csv': 1, 'n_kg': 2,
                     'only_csv': [], 'only_kg': ['C2']})
        self.assertFails(_chk.check_pathcheck)


class MetaProvenanceTest(_CheckFixture):
    def test_passes_when_good(self):
        import json
        json.dump({'recommendation.csv': {'at': 'x', 'argv': 'y', 'env': {}}},
                  open(os.path.join(_chk.OUT, 'provenance.json'), 'w'))
        self.assertPasses(_chk.check_provenance)

    def test_fails_on_nondefault_env_for_canonical(self):
        import json
        json.dump({'recommendation.csv':
                   {'at': 'x', 'argv': 'y', 'env': {'E_MODE': 'binary'}}},
                  open(os.path.join(_chk.OUT, 'provenance.json'), 'w'))
        self.assertFails(_chk.check_provenance)

    def test_fails_when_output_older_than_input(self):
        import json
        import time
        json.dump({}, open(os.path.join(_chk.OUT, 'provenance.json'), 'w'))
        rec = os.path.join(_chk.OUT, 'recommendation.csv')
        old = time.time() - 600
        os.utime(rec, (old, old))                # 입력보다 오래된 산출물
        self.assertFails(_chk.check_provenance)


class MetaOutputsTest(_CheckFixture):
    """`outputs` 검사 — 산출물의 **생산자가 코드에 있는지**를 실제로 잡는지.

    코드를 줄이는 커밋이 문서가 가리키는 산출물의 생산자를 지워도 아무것도
    FAIL 하지 않던 자리다. 그래서 이 검사 자신을 오류 주입으로 본다.
    """

    def _code(self, body):
        """임시 디렉토리를 `check.HERE` 로 돌리고 .py 하나를 깐다."""
        src = os.path.join(self._dir.name, 'src')
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, 'mod.py'), 'w', encoding='utf-8') as f:
            f.write(body)
        _chk.HERE = src

    def test_passes_when_producer_exists(self):
        self._code("import os\nx = os.path.join(OUT, 'alpha.csv')\n")
        self.w('alpha.csv', pd.DataFrame([{'a': 1}]))
        for f in os.listdir(_chk.OUT):          # fixture 산출물은 치운다
            if f.endswith('.csv') and f != 'alpha.csv':
                os.remove(os.path.join(_chk.OUT, f))
        self._doc('`out/alpha.csv`')
        self.assertPasses(_chk.check_outputs)

    def test_fails_on_orphan_output(self):
        self._code("x = 'alpha.csv'\n")
        self.w('alpha.csv', pd.DataFrame([{'a': 1}]))
        self.w('beta.csv', pd.DataFrame([{'a': 1}]))   # 생산자 없음
        self.assertFails(_chk.check_outputs)

    def test_fstring_pattern_covers_variants(self):
        # `learned_{FEATURES}.csv` 가 learned_form.csv 를 덮어야 한다.
        self._code("n = 'form'\nx = f'learned_{n}.csv'\n")
        for f in os.listdir(_chk.OUT):
            if f.endswith('.csv'):
                os.remove(os.path.join(_chk.OUT, f))
        self.w('learned_form.csv', pd.DataFrame([{'a': 1}]))
        self._doc('`out/learned_form.csv`')
        self.assertPasses(_chk.check_outputs)

    def test_declared_outputs_reads_fstrings(self):
        self._code("x = f'a_{k}.csv'\ny = 'b.csv'\n")
        got = _chk.declared_outputs(_chk.HERE)
        self.assertEqual(set(got), {'a_*.csv', 'b.csv'})

    def _doc(self, text):
        """`check.HERE` 에 README.md 하나를 깐다 (DOCS 의 첫 항목)."""
        with open(os.path.join(_chk.HERE, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(text)

    def _only(self, *names):
        for f in os.listdir(_chk.OUT):
            if f.endswith('.csv') and f not in names:
                os.remove(os.path.join(_chk.OUT, f))

    def test_fails_on_undocumented_output(self):
        self._code("x = 'alpha.csv'\ny = 'beta.csv'\n")
        self._only()
        self.w('alpha.csv', pd.DataFrame([{'a': 1}]))
        self.w('beta.csv', pd.DataFrame([{'a': 1}]))
        self._doc('`out/alpha.csv` 만 적었다')
        self.assertFails(_chk.check_outputs)

    def test_bare_wildcard_token_does_not_cover_everything(self):
        # **조용히 PASS 했던 자리.** 문서에 `out/*.csv` 라는 말이 한 번
        # 나오는데 그걸 패턴으로 받으면 ^.*$ 가 되어 전부 통과한다.
        self._code("x = 'beta.csv'\n")
        self._only()
        self.w('beta.csv', pd.DataFrame([{'a': 1}]))
        self._doc('산출물은 `out/*.csv` 에 있다')
        self.assertFails(_chk.check_outputs)

    def test_doc_placeholder_covers_variants(self):
        # `complication_hypergeom_{소스}.csv` 가 _curated 를 덮어야 한다.
        self._code("s = 'curated'\nx = f'comp_{s}.csv'\n")
        self._only()
        self.w('comp_curated.csv', pd.DataFrame([{'a': 1}]))
        self._doc('| `out/comp_{소스}.csv` | 소스별 |')
        self.assertPasses(_chk.check_outputs)

    def test_missing_provenance_is_not_a_failure(self):
        # **일부러 통과시키는 자리.** 기본값 아닌 환경에서만 나오는 산출물은
        # 기본 실행에 기록이 안 남는다. 그걸 FAIL 로 하면 검사가 거짓말을 한다.
        self._code("x = 'alpha.csv'\n")
        for f in os.listdir(_chk.OUT):
            if f.endswith('.csv'):
                os.remove(os.path.join(_chk.OUT, f))
        self.w('alpha.csv', pd.DataFrame([{'a': 1}]))
        pv = os.path.join(_chk.OUT, 'provenance.json')
        if os.path.exists(pv):
            os.remove(pv)
        self._doc('`out/alpha.csv`')
        self.assertPasses(_chk.check_outputs)


class IoGraphTest(unittest.TestCase):
    """의존 그래프를 **코드에서 뽑는** 부분 (`check.io_graph`).

    손으로 쓴 `DEPENDS` 가 9 쌍뿐이라 아무도 적어 주지 않은 산출물은 신선도
    검사를 한 번도 안 받았다. 뽑는 쪽의 위험은 **없는 의존을 만드는 것**이라
    거기에 시험을 몰아 둔다.
    """

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._dir.cleanup()

    def _mods(self, **srcs):
        for name, body in srcs.items():
            with open(os.path.join(self._dir.name, name + '.py'), 'w',
                      encoding='utf-8') as f:
                f.write(body)
        return _chk.io_graph(self._dir.name)

    def test_cross_module_edge(self):
        g = self._mods(
            a="import pandas as pd\npd.DataFrame().to_csv('x.csv')\n",
            b="import pandas as pd\npd.read_csv('x.csv').to_csv('y.csv')\n")
        self.assertEqual(g, {'y.csv': {'x.csv'}})

    def test_intra_module_edge_is_dropped(self):
        # **없는 의존 84 개를 만들었던 자리.** 한 모듈이 한 번 돌며 읽고 쓰는
        # 것끼리는 기록 순서가 내부 사정이라 mtime 선후에 뜻이 없다.
        g = self._mods(
            a="import pandas as pd\npd.DataFrame().to_csv('x.csv')\n"
              "pd.read_csv('x.csv').to_csv('y.csv')\n")
        self.assertEqual(g, {})

    def test_unproduced_input_is_dropped(self):
        # 아무 모듈도 만들지 않는 입력(원시 다운로드)은 변을 만들지 않는다.
        g = self._mods(a="import pandas as pd\n"
                         "pd.read_csv('raw.csv').to_csv('y.csv')\n")
        self.assertEqual(g, {})

    def test_no_self_edge(self):
        g = self._mods(
            a="import pandas as pd\npd.DataFrame().to_csv('x.csv')\n",
            b="import pandas as pd\npd.read_csv('x.csv').to_csv('x.csv')\n")
        self.assertNotIn('x.csv', g.get('x.csv', set()))

    def test_checker_is_not_a_consumer(self):
        # check.py·tests.py 는 전부 읽지만 소비자가 아니다.
        g = self._mods(check="import pandas as pd\n"
                             "pd.read_csv('x.csv').to_csv('z.csv')\n")
        self.assertEqual(g, {})

    def test_real_repo_graph_is_nonempty(self):
        g = _chk.io_graph()
        self.assertGreater(sum(len(v) for v in g.values()), 20)
        for o, deps in g.items():
            self.assertNotIn(o, deps)


class MetaHooksTest(_CheckFixture):
    """커밋 훅 검사 — **새 클론**(설정 없음)을 잡는지.

    `BASE` 를 임시 git 레포로 돌려서 본다. 실제 레포의 설정을 건드리지 않는다.
    """

    def _repo(self, with_config, executable=True):
        import subprocess
        root = os.path.join(self._dir.name, 'repo')
        os.makedirs(os.path.join(root, 'hooks'), exist_ok=True)
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        h = os.path.join(root, 'hooks', 'pre-commit')
        open(h, 'w').write('#!/bin/sh\nexit 0\n')
        os.chmod(h, 0o755 if executable else 0o644)
        if with_config:
            subprocess.run(['git', 'config', 'core.hooksPath', 'hooks'],
                           cwd=root, check=True)
        _chk.BASE = root
        return root

    def setUp(self):
        super().setUp()
        self._base = _chk.BASE
        os.environ.pop('OURKG_NO_HOOK_CHECK', None)

    def tearDown(self):
        _chk.BASE = self._base
        super().tearDown()

    def test_passes_when_configured(self):
        self._repo(with_config=True)
        self.assertPasses(_chk.check_hooks)

    def test_fails_on_fresh_clone(self):
        # 훅 파일은 있는데 core.hooksPath 가 없다 — 새로 클론한 상태.
        self._repo(with_config=False)
        self.assertFails(_chk.check_hooks)

    def test_ignores_ambient_git_env(self):
        # **커밋 훅 안에서만 깨졌던 자리.** `git commit` 이 GIT_DIR 을 내보내면
        # cwd 가 무시되고 훅을 띄운 레포의 설정을 읽는다 — 임시 레포를 본다는
        # 전제가 무너진다. 검사는 GIT_* 를 걷어내고 불러야 한다.
        self._repo(with_config=False)
        os.environ['GIT_DIR'] = os.path.join(self._base, '.git')
        try:
            self.assertFails(_chk.check_hooks)
        finally:
            os.environ.pop('GIT_DIR', None)

    def test_fails_without_exec_bit(self):
        self._repo(with_config=True, executable=False)
        self.assertFails(_chk.check_hooks)

    def test_skips_when_opted_out(self):
        self._repo(with_config=False)
        os.environ['OURKG_NO_HOOK_CHECK'] = '1'
        try:
            sts = self.run_check(_chk.check_hooks)
        finally:
            os.environ.pop('OURKG_NO_HOOK_CHECK', None)
        self.assertEqual(sts, ['SKIP'])

    def test_skips_when_hook_absent(self):
        root = self._repo(with_config=True)
        os.remove(os.path.join(root, 'hooks', 'pre-commit'))
        self.assertEqual(self.run_check(_chk.check_hooks), ['SKIP'])


class MetaDocsTest(_CheckFixture):
    """`docs` 검사 — 앵커 값·형식·부재를 모두 잡는지."""

    def _doc(self, text):
        _chk.HERE = self._dir.name
        open(os.path.join(self._dir.name, 'README.md'), 'w',
             encoding='utf-8').write(text)

    def test_passes_when_anchor_matches(self):
        fx = _chk.facts()
        self._doc(f"triple {fx['kg.triples']}<!--chk:kg.triples-->\n")
        self.assertPasses(_chk.check_docs)

    def test_fails_when_anchor_drifts(self):
        self._doc("triple 1,234,567<!--chk:kg.triples-->\n")
        self.assertFails(_chk.check_docs)

    def test_fails_when_no_anchor(self):
        self._doc("수치가 적혀 있지만 앵커가 없다 3,443,485\n")
        self.assertFails(_chk.check_docs)

    def test_fails_on_malformed_anchor(self):
        fx = _chk.facts()
        self._doc(f"triple {fx['kg.triples']}<!--chk:kg.triples-->\n"
                  "설명만 있는 자리 <!--chk:kg.relations-->\n")
        self.assertFails(_chk.check_docs)

    def test_unknown_anchor_name_fails(self):
        self._doc("값 1<!--chk:없는.사실-->\n")
        self.assertFails(_chk.check_docs)


class MetaDocsScopeTest(unittest.TestCase):
    """검사 **범위**가 좁아지지 않았는지.

    앵커를 39 자리에 달아 두고도 `DOCS` 에 루트 문서를 빼먹어 `3,443,484` 가
    남아 있었다. 범위를 좁히는 것은 조용한 후퇴라 여기서 막는다.
    """

    def test_root_docs_included(self):
        for f in ('../README.md', '../PROBLEMS.md'):
            self.assertIn(f, _chk.DOCS, f'{f} 가 검사 범위에서 빠졌다')

    def test_ourkg_docs_included(self):
        for f in ('README.md', 'DATA.md', 'METHODS.md', 'PROCESS.md'):
            self.assertIn(f, _chk.DOCS)

    def test_results_excluded_on_purpose(self):
        # 시간순 기록이라 옛 수치가 맞다 — 빼는 것이 의도다.
        self.assertNotIn('RESULTS.md', _chk.DOCS)
        self.assertIn('RESULTS.md', _chk.DOCS_EXCLUDED)

    def test_every_doc_path_exists(self):
        for f in _chk.DOCS:
            p = os.path.join(_chk.HERE, f)
            self.assertTrue(os.path.exists(p), f'{f} 가 없다 — 경로가 틀렸거나 지워졌다')


class MetaRobustnessTest(_CheckFixture):
    """검사가 **예외로 죽지 않는지** — 죽으면 뒤 검사가 안 돈다."""

    def test_main_reports_fail_instead_of_crashing(self):
        # 열을 지워 검사 안에서 AttributeError 가 나게 한다.
        m = pd.read_csv(os.path.join(_chk.OUT, 'microbes.csv'))
        self.w('microbes.csv', m.drop(columns=['taxid_current']))
        import contextlib
        import io as _io
        _chk.RESULT.clear()
        with contextlib.redirect_stdout(_io.StringIO()):
            rc = _chk.main(['microbe'])          # 예외가 새면 여기서 터진다
        self.assertEqual(rc, 1)
        self.assertIn('FAIL', [st for st, *_ in _chk.RESULT])


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
