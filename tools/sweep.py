"""
수식·부호·E 구성 스윕
=======================
파이프라인을 다시 돌리지 않고 analyse/ 산출물 위에서 변형을 비교한다.
(구 sweep_formula.py / sweep_sign.py / exp_paper_E.py / exp_promenda_first.py /
 diag_ranking_ceiling.py / diag_uvsp.py 통합)

실행
    python3 tools/sweep.py formula    논문 수식 vs 공식 코드 16조합
    python3 tools/sweep.py sign       E 부호 방향 6변형
    python3 tools/sweep.py sources    weight.csv 4개 소스 및 조합
    python3 tools/sweep.py menda      MENDA 원본을 주 근거로 E 구성
    python3 tools/sweep.py promenda   ProMENDA 를 주 근거로 둘 때
    python3 tools/sweep.py ceiling    E 가설별 상한 + u/p 어디서 뒤집히는가
    python3 tools/sweep.py all
"""
import itertools
import math
import sys

import numpy as np
from scipy import stats
from sklearn.decomposition import PCA

import core

K = core.K


def _rank(d, p):
    idx, rank, p5, ptop, pbot = core.paper_ranking(d.names)
    rho = stats.spearmanr(-p[idx], rank).statistic
    order = np.argsort(-p)
    top = {d.names[i] for i in order[:K]}
    bot = {d.names[i] for i in order[-K:]}
    return rho, len(top & ptop), len(bot & pbot)


def _line(label, d, p, width=26):
    rho, t, b = _rank(d, p)
    print(f'  {label:{width}s} Spearman={rho:+.3f}  Top30={t:2d}/{K}  '
          f'Bot30={b:2d}/{K}')


# ------------------------------------------------------------------
def formula():
    """논문 수식과 공식 final.py 가 갈리는 4지점 x 2 = 16조합.

    scope  분모 합 범위  all=공식 / common=논문
    form   분모 곱 구조  split=공식 sqrt(Σ²xΣ²) / joint=논문 sqrt(Σ[²·²])
    colsum p 를 열 합으로 나누는가  True=공식 final.py:100
    feat   유사도 계산 공간  X=공식 / pca5=논문 §4.2.1
    """
    d = core.Data.load()
    D_mat = d.Xn * d.E[np.newaxis, :]
    idx, rank, p5, ptop, pbot = core.paper_ranking(d.names)

    def sim(F, scope, form):
        Z = F - F.mean(1, keepdims=True)
        M = (F > 0).astype(float)
        ZM = Z * M
        num = ZM @ ZM.T
        if scope == 'all':
            if form == 'split':
                ss = (Z ** 2).sum(1)
                den = np.sqrt(np.outer(ss, ss))
            else:
                den = np.sqrt((Z ** 2) @ (Z ** 2).T)
        else:
            if form == 'split':
                A = (Z ** 2 * M) @ M.T
                den = np.sqrt(A * A.T)
            else:
                den = np.sqrt((Z ** 2 * M) @ (Z ** 2 * M).T)
        S = np.divide(num, den, out=np.zeros_like(num),
                      where=(den != 0) & ((M @ M.T) > 0))
        np.fill_diagonal(S, 0.0)
        return S

    # 벡터화가 공식 스칼라 구현과 같은지 확인
    def scalar(x, y):
        com = [i for i in range(len(x)) if x[i] > 0 and y[i] > 0]
        if not com:
            return 0
        a1, a2 = float(sum(x)) / len(x), float(sum(y)) / len(y)
        num = sum((x[j] - a1) * (y[j] - a2) for j in com)
        d1 = sum(math.pow(x[m] - a1, 2) for m in range(len(x)))
        d2 = sum(math.pow(y[m] - a2, 2) for m in range(len(y)))
        dd = math.sqrt(d1 * d2)
        return 0 if dd == 0 else num / dd

    Sv = sim(d.Xn, 'all', 'split')
    n = len(d.Xn)
    err = max(abs(Sv[i, j] - scalar(d.Xn[i], d.Xn[j]))
              for i in range(0, n, 17) for j in range(0, n, 23) if i != j)
    print(f'  벡터화 검증: 공식 스칼라 구현과 최대 오차 {err:.1e}\n')

    rows = []
    for scope, form, colsum, feat in itertools.product(
            ['all', 'common'], ['split', 'joint'], [True, False], ['X', 'pca5']):
        F = d.Xn if feat == 'X' else PCA(n_components=5).fit_transform(D_mat)
        S = sim(F, scope, form)
        p = d.Xn @ d.E @ S if False else (d.Xn @ d.E) @ S
        if colsum:
            cs = S.sum(0)
            p = np.divide(p, cs, out=np.zeros_like(p), where=cs != 0)
        rho = stats.spearmanr(-p[idx], rank).statistic
        order = np.argsort(-p)
        top = {d.names[i] for i in order[:K]}
        bot = {d.names[i] for i in order[-K:]}
        tag = ('★공식' if (scope, form, colsum, feat) == ('all', 'split', True, 'X')
               else '☆논문' if (scope, form, colsum, feat) ==
               ('common', 'joint', False, 'pca5') else '')
        rows.append((rho, scope, form, colsum, feat,
                     len(top & ptop), len(bot & pbot), tag))

    print(f"  {'scope':7s} {'form':6s} {'colsum':7s} {'feat':5s} "
          f"{'Spearman':>9s} {'Top30':>6s} {'Bot30':>6s}")
    for rho, sc, fo, co, fe, t, b, tag in sorted(rows, reverse=True):
        print(f'  {sc:7s} {fo:6s} {str(co):7s} {fe:5s} {rho:+9.3f} '
              f'{t:5d}/{K} {b:5d}/{K}  {tag}')


# ------------------------------------------------------------------
def sign():
    """E 부호 방향. 카테고리 지표로는 못 가리는 것을 순위로 가린다."""
    d = core.Data.load()
    w = d.w.values
    for label, E in (('paper+  (pos-neg)', w[0] - w[1]),
                     ('paper-  (neg-pos)', w[1] - w[0]),
                     ('row0',  w[0].copy()), ('row0-', -w[0]),
                     ('row1',  w[1].copy()), ('row1-', -w[1])):
        _line(label, d, d.score(E), 20)
    print()
    print('  ※ 순위만 보면 반전이 나아 보이나 compound 수준(gold)은 반대다.')
    print('     gold 는 9종 중 7종이 + 라 "모르면 +1" 기본값에 유리하다.')


# ------------------------------------------------------------------
def promenda():
    """ProMENDA 를 주 근거로 E 를 만들면 어떻게 되는가."""
    d = core.Data.load()
    mpos, mneg = core.menda_sets()
    PM = core.promenda()

    def menda_dir(c):
        ks = set(core.kegg_alias.incidence_keys(c))
        inp, inn = bool(ks & mpos), bool(ks & mneg)
        return 1 if (inp and not inn) else (-1 if (inn and not inp) else 0)

    _line('현재 (step3/step4)', d, d.score(), 30)
    for margin in (0.0, 0.10, 0.20, 0.30):
        for fb in (True, False):
            E = []
            for c in d.cols:
                dd, _ = core.direction(PM, c, margin=margin)
                if dd == 0 and fb:
                    dd = menda_dir(c)
                E.append(dd)
            lab = f'ProMENDA우선 m={margin:.2f} MENDA보조={"O" if fb else "X"}'
            _line(lab, d, d.score(np.array(E, dtype=float)), 30)


# ------------------------------------------------------------------
def ceiling():
    """u 와 p 중 어디서 뒤집히는가 + E 가설별 상한."""
    d = core.Data.load()
    p5df = core.paper85()
    grp = dict(zip(p5df.kegg, p5df.group))
    idx, rank, _, _, _ = core.paper_ranking(d.names)

    u = d.Xn @ d.E
    p = d.score()
    print('  [뒤집힘 지점]')
    _line('u (food 자신의 점수)', d, u, 26)
    _line('p (이웃 u 가중평균)', d, p, 26)
    print(f'  corr(u, p) = {np.corrcoef(u, p)[0, 1]:+.3f}  '
          f'-> 같은 부호이면 p 공식은 범인이 아니다')
    print(f'  S 음수 원소 {int((d.S < 0).sum())}개, '
          f'열 합이 음수인 열 {int((d.cs < 0).sum())}개')

    ref = {}
    for j, c in enumerate(d.cols):
        v = d.Xn[idx, j]
        ref[c] = (0.0 if np.count_nonzero(v) < 8
                  else -stats.spearmanr(v, rank).statistic)

    GS = {'Lipids': -1, 'Amino acid': -1, 'Carbohydrates': 1,
          'Vitamins and cofactors': 1, 'Trace Elements': 0, 'Macronutrient': 0}
    print()
    print('  [E 가설별]')
    _line('현재', d, p, 26)
    _line('그룹부호 (지질/아미노=-1)', d,
          d.score(np.array([GS.get(grp.get(c), 0) for c in d.cols], float)), 26)
    _line('ref부호 (상한, 순환)', d,
          d.score(np.array([np.sign(ref[c]) for c in d.cols], float)), 26)
    _line('동물성 기준선 (비교용)', d, core.one_bit(d.Y), 26)
    print()
    print('  [compound 그룹별 ref 평균]  +면 논문이 추천 쪽에 둔 성분')
    for g in sorted(set(grp.values())):
        vals = [ref[c] for c in d.cols if grp.get(c) == g]
        print(f'    {g:24s} {np.mean(vals):+.3f}  (n={len(vals)})')


def sources():
    """weight.csv 의 4개 소스를 각각 순위로 써 본다.

    infer / faecal / type1 / type2 는 map_promenda.py 가 ProMENDA 의
    부분집합(전체 / Tissue=Faece / Study type=Type1 / Type2)에서
    독립 집계한 것이다. 공식 final.py 는 순위를 p1(infer)로 내고
    나머지는 RMSE/MAE 비교에만 쓴다. 다른 소스가 논문 순위를 더 잘
    맞추는지 확인한 적이 없어 여기서 본다.
    """
    d = core.Data.load()
    w = d.w.values
    names = ('infer', 'faecal', 'type1', 'type2')
    Es = {n: w[k] - w[k + 1] for n, k in zip(names, (0, 2, 4, 6))}
    for n, E in Es.items():
        _line(f'{n}  (+{int((E>0).sum())}/-{int((E<0).sum())})', d,
              d.score(E), 26)
    print()
    print('  [부호 반전]  ProMENDA 의 up/down 의미는 Type 마다 다르다')
    print('    Type1 = 우울증군 vs 대조군      -> down = 우울증에서 결핍')
    print('    Type2 = 치료군 vs 미치료 질병군  -> down = 치료로 감소(질병에서 높았던 것)')
    print('    map_promenda.py 는 두 경우에 같은 해석을 적용한다.')
    for n in names:
        _line(f'{n} (반전)', d, d.score(-Es[n]), 26)

    print()
    print('  [소스 조합]')
    import itertools
    for r in (2, 3, 4):
        for comb in itertools.combinations(names, r):
            E = sum(Es[n] for n in comb)
            _line('+'.join(comb), d, d.score(E), 26)


def menda():
    """MENDA 원본(menda.xlsx)을 주 근거로 E 를 구성.

    지금 파이프라인은 KG 의 이진 목록(pos 378 / neg 399)만 쓴다. 원본은
    compound 별 study 단위 down:up 카운트를 주므로 마진 규칙을 적용할 수 있다.
    극성은 down = 결핍 = +1 (core.menda_orig 주석 참조).
    """
    d = core.Data.load()
    MO = core.menda_orig()
    PM = core.promenda()
    kgp, kgn = core.menda_sets()
    p85 = core.paper85()
    grp = dict(zip(p85.kegg, p85.group))

    def kg_dir(c):
        ks = set(core.kegg_alias.incidence_keys(c))
        inp, inn = bool(ks & kgp), bool(ks & kgn)
        # KG 극성도 동일: hasPositiveAssociation = up in depression = -1
        return -1 if (inp and not inn) else (1 if (inn and not inp) else 0)

    print('  [MENDA 원본 단독]  마진별')
    for mg in (0.0, 0.10, 0.20, 0.30, 0.50):
        E = np.array([core.direction(MO, c, margin=mg)[0] for c in d.cols],
                     dtype=float)
        nz = int((E != 0).sum())
        _line(f'margin={mg:.2f}  (방향 {nz}종)', d, d.score(E), 28)

    print()
    print('  [MENDA 원본 + 보조]  margin=0.10')
    base = {c: core.direction(MO, c, margin=0.10)[0] for c in d.cols}
    variants = {
        'MENDA원본만': lambda c: base[c],
        '+ KG 목록': lambda c: base[c] or kg_dir(c),
        '+ ProMENDA': lambda c: base[c] or core.direction(PM, c, 0.10)[0],
        '+ KG + ProMENDA': lambda c: (base[c] or kg_dir(c)
                                      or core.direction(PM, c, 0.10)[0]),
    }
    for name, f in variants.items():
        E = np.array([f(c) for c in d.cols], dtype=float)
        nz = int((E != 0).sum())
        _line(f'{name}  (방향 {nz}종)', d, d.score(E), 28)

    print()
    print('  [현재 파이프라인]')
    _line('현재 (step3/step4)', d, d.score(), 28)

    print()
    print('  [gold 9종 — MENDA 원본은 무엇을 말하는가]')
    for k, (sign, nm, ref) in core.gold.GOLD.items():
        hit = core.lookup(MO, k)
        cur = core.gold.direction(d.w, k) or '-'
        if hit:
            p_, n_ = hit
            t = p_ + n_
            mo = '+' if p_ > n_ else ('-' if n_ > p_ else '0')
            txt = f'{p_}:{n_} (마진 {abs(p_-n_)/t:.2f})' if t else '-'
        else:
            mo, txt = '-', '원본에 없음'
        mark = 'O' if mo == sign else ('X' if mo in '+-' else ' ')
        print(f'    {k}  {nm[:22]:23s} 논문={sign}  현재={cur}  '
              f'MENDA원본={mo} {txt:20s} {mark}')


FUNCS = {'formula': formula, 'sign': sign, 'sources': sources,
         'menda': menda,
         'promenda': promenda, 'ceiling': ceiling}

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for k in (list(FUNCS) if which == 'all' else [which]):
        if k not in FUNCS:
            sys.exit(f'알 수 없는 항목: {k}\n가능: {", ".join(FUNCS)}, all')
        print(f'=== {k} ===')
        FUNCS[k]()
        print()
