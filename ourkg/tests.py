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

    def test_report_picks_tightest_not_largest_effect(self):
        # **처음에 틀린 자리.** 부호일치가 가장 큰 행을 골라 0.77 이라는 느슨한
        # 경계를 냈다. 경계는 MDES 가 가장 작은 행에서 읽어야 한다.
        import pandas as pd, os
        f = os.path.join(self.e.OUT, 'power_bound.csv')
        if not os.path.exists(f):
            self.skipTest('power_bound.csv 없음')
        t = pd.read_csv(f)
        bh = [c for c in t.columns if c.startswith('최소검출효과(BH')][0]
        self.assertEqual(int(t.loc[t[bh].idxmin()].n), int(t.n.max()))
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
             'n_compound': 20}]))
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
