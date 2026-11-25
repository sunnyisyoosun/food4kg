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


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
