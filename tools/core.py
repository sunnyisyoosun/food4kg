"""
진단 도구 공용 모듈
=====================
tools/ 아래 스크립트가 반복하던 로드·정규화·유사도·채점·지표를 한곳에 모았다.

쓰는 쪽은 보통 이렇게 한다.

    from core import Data, paper_ranking, metrics
    d = Data.load()
    p = d.score(d.E)
    print(metrics(d, p))
"""
import json
import os
import re
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'analyse')
FKG = os.path.join(BASE, 'foodkg_triply')
PROMENDA_XLSX = os.path.join(BASE, '41398_2024_2948_MOESM3_ESM.xlsx')

sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, 'eval'))
import gold          # noqa: E402
import kegg_alias    # noqa: E402

K = 30

# 논문 Fig. 5 의 피라미드 3층 기준.
#   상단(No-recommended)  Baked / Beef / Sausages and Luncheon Meats / Pork
#   중간(general)         Dairy and Egg / Finfish and Shellfish / Soups,Sauces / Fats and Oils
#   하단(Recommended)     Vegetables and Vegetable Products / Fruits and Fruit Juices
#
# 주의: §4.2.3 본문은 "recommended ... mainly fish and shellfish products,
# as well as fruits and vegetables" 라고 적어 Fig. 5 와 모순된다. Fig. 5 가
# 알고리즘 출력에서 직접 그려진 그림이므로 그쪽을 기준으로 삼는다.
CAT = {1.0: 'Dairy', 4.0: 'Oils', 5.0: 'Poultry', 6.0: 'Sauces',
       7.0: 'Sausages', 9.0: 'Fruits', 10.0: 'Pork', 11.0: 'Vegetables',
       12.0: 'Nuts', 13.0: 'Beef', 15.0: 'Fish', 16.0: 'Legumes',
       18.0: 'Baked', 19.0: 'Sweets', 20.0: 'Cereal', 25.0: 'Restaurant'}
PAPER_REC = {9.0, 11.0}            # Fruits, Vegetables
PAPER_NOT = {18.0, 13.0, 7.0, 10.0}  # Baked, Beef, Sausages, Pork
# 1비트 기준선의 '동물성' 카테고리: Dairy/Egg, Poultry, Sausages, Pork, Beef, Fish
ANIMAL = {1.0, 5.0, 7.0, 10.0, 13.0, 15.0}


def one_bit(Y):
    """식물성=+1 / 동물성=-1. compound 를 보지 않는 기준선."""
    return np.array([-1.0 if y in ANIMAL else 1.0 for y in Y])


def rowminmax(X):
    lo, hi = X.min(1, keepdims=True), X.max(1, keepdims=True)
    return np.divide(X - lo, hi - lo, out=np.zeros_like(X), where=hi > lo)


def cos_matrix(A, B):
    na = np.linalg.norm(A, axis=1, keepdims=True)
    nb = np.linalg.norm(B, axis=1, keepdims=True)
    return np.divide(A @ B.T, na * nb.T, out=np.zeros((len(A), len(B))),
                     where=(na * nb.T) > 0)


def gold_of_E(cols, E):
    """E 벡터로 gold 9종을 채점한다 (weight.csv 를 거치지 않는 변형용)."""
    ok = n = 0
    for j, c in enumerate(cols):
        if c in gold.GOLD:
            n += 1
            ok += np.sign(E[j]) == (1 if gold.GOLD[c][0] == '+' else -1)
    return f'{ok}/{n}'


# ------------------------------------------------------------------
# 데이터
# ------------------------------------------------------------------
@dataclass
class Data:
    """analyse/ 산출물을 읽어 점수 계산에 필요한 것을 모두 담는다."""
    cols: list
    X: np.ndarray            # 원본 amount (모든 food)
    Xn: np.ndarray           # 행별 min-max 정규화 (range 0인 행 제외)
    names: list              # Xn 행에 대응하는 food 이름
    Y: np.ndarray            # Xn 행의 food category
    w: pd.DataFrame          # weight.csv
    E: np.ndarray            # 논문 §4.2.1 의 E = pos - neg
    S: np.ndarray = field(repr=False, default=None)
    cs: np.ndarray = field(repr=False, default=None)

    @classmethod
    def load(cls):
        food = pd.read_csv(os.path.join(OUT, 'food.csv'))
        fn = pd.read_csv(os.path.join(OUT, 'foodname.csv'))
        w = pd.read_csv(os.path.join(OUT, 'weight.csv'))
        cols = [c for c in food.columns if c.startswith('C')]
        X = food[cols].values.astype(float)
        Y_all = food['type'].values
        names_all = fn['foodname'].tolist()

        rows, kept = [], []
        for i in range(X.shape[0]):
            r = X[i].copy()
            if r.max() - r.min() == 0:
                continue
            rows.append((r - r.min()) / (r.max() - r.min()))
            kept.append(i)
        d = cls(cols=cols, X=X, Xn=np.array(rows),
                names=[names_all[i] for i in kept], Y=Y_all[kept], w=w,
                E=w.values[0] - w.values[1])
        d.S, d.cs = similarity(d.Xn)
        return d

    def score(self, E=None):
        """공식 final.py 의 p = (Xn·E)·S / colsum(S)"""
        E = self.E if E is None else E
        u = self.Xn @ E
        return np.divide(u @ self.S, self.cs,
                         out=np.zeros_like(self.cs), where=self.cs != 0)

    def sign_of(self, kegg):
        if kegg not in self.w.columns:
            return 0
        return (1 if self.w[kegg].iloc[0] > 0
                else (-1 if self.w[kegg].iloc[1] > 0 else 0))

    def signs(self):
        return {c: self.sign_of(c) for c in self.cols}


def similarity(Xn):
    """공식 user_similarity_on_modified_cosine 의 벡터화 (오차 1e-15)."""
    Z = Xn - Xn.mean(1, keepdims=True)
    M = (Xn > 0).astype(float)
    ZM = Z * M
    ss = (Z ** 2).sum(1)
    den = np.sqrt(np.outer(ss, ss))
    S = np.divide(ZM @ ZM.T, den, out=np.zeros((len(Xn),) * 2),
                  where=(den != 0) & ((M @ M.T) > 0))
    np.fill_diagonal(S, 0.0)
    return S, S.sum(0)


# ------------------------------------------------------------------
# 논문 순위 (p5_foodname.txt)
# ------------------------------------------------------------------
def paper_ranking(names):
    """p5 줄 순서를 논문 순위로 본다.

    근거: (1) 내용이 정렬되어 있다 — 앞 30줄 양파/멜론/자몽/바나나/케일,
    뒤 30줄 소고기/소시지/닭고기. 논문 §4.2.3 서술과 방향이 같다.
    (2) 논문 Fig. 4(c) 원본(heatmap.xlsx)의 행 순서와 Spearman 0.896.
    공식 final.py 는 이 파일을 읽지 않으므로 순위라는 해석은 추정이다.

    반환: (idx, paper_rank, p5, top30 이름집합, bottom30 이름집합)
    """
    p5 = [l.strip() for l in open(os.path.join(OUT, 'p5_foodname.txt'))
          if l.strip()]
    rank_of = {}
    for i, n in enumerate(p5):
        rank_of.setdefault(n, i)
    idx = [i for i, n in enumerate(names) if n in rank_of]
    rank = np.array([rank_of[names[i]] for i in idx], dtype=float)
    return idx, rank, p5, set(p5[:K]), set(p5[-K:])


def metrics(d, p, k=K):
    """논문 순위·카테고리 양쪽 지표를 한 번에."""
    idx, rank, p5, ptop, pbot = paper_ranking(d.names)
    rho = stats.spearmanr(-p[idx], rank).statistic if len(idx) > 2 else np.nan
    order = np.argsort(-p)
    topi, boti = order[:k], order[-k:]
    top_names = {d.names[i] for i in topi}
    bot_names = {d.names[i] for i in boti}
    gok, gn, gmiss = gold.score(d.w)
    return dict(
        spearman=rho,
        top_overlap=len(top_names & ptop),
        bot_overlap=len(bot_names & pbot),
        chance=k * k / max(len(idx), 1),
        top30_rec=sum(1 for i in topi if d.Y[i] in PAPER_REC),
        bot30_not=sum(1 for i in boti if d.Y[i] in PAPER_NOT),
        cat_rec=f'{len(PAPER_REC & {d.Y[i] for i in topi})}/{len(PAPER_REC)}',
        cat_not=f'{len(PAPER_NOT & {d.Y[i] for i in boti})}/{len(PAPER_NOT)}',
        gold=f'{gok}/{gn}', gold_miss=gmiss,
        E=f'+{int((d.E > 0).sum())}/-{int((d.E < 0).sum())}'
          f'/0={int((d.E == 0).sum())}',
    )


def fmt(m, label='', width=22):
    return (f'{label:{width}s} Spearman={m["spearman"]:+.3f}  '
            f'Top30={m["top_overlap"]:2d}/{K}  Bot30={m["bot_overlap"]:2d}/{K}  '
            f'gold={m["gold"]:>4s}  {m["E"]}')


# ------------------------------------------------------------------
# 근거 소스
# ------------------------------------------------------------------
def menda_sets():
    """Depression(mesh D003865) -> compound 의 pos / neg 집합."""
    with open(os.path.join(FKG, 'MENDA_Depression.jsonld')) as f:
        data = json.load(f)
    pos, neg = set(), set()
    for entry in data:
        for node in entry.get('@graph', []):
            for key, vals in node.items():
                short = key.rsplit('#', 1)[-1]
                if short not in ('hasPositiveAssociation',
                                 'hasNegativeAssociation'):
                    continue
                tgt = pos if short == 'hasPositiveAssociation' else neg
                for v in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(v, dict) and '@id' in v:
                        cid = v['@id'].rsplit('/', 1)[-1]
                        if cid.startswith('C'):
                            tgt.add(cid)
    return pos, neg


def promenda(subset=None):
    """ProMENDA 를 compound -> (pos, neg) 로 집계.

    subset: None(전체) 또는 (컬럼명, 값) 튜플. 예: ('M_Tissue_Metabolite_level_1', 'Faece')
    규제 해석은 map_promenda.py 와 같다 — down in depression = +1.
    """
    pm = pd.read_excel(PROMENDA_XLSX, sheet_name='M_Metabolite')
    pm['k'] = pm['M_KEGG'].astype(str).str.extract(r'(C\d{5})')[0]
    reg = pm['M_Up/Down_regulated '].astype(str).str.strip().str.lower()
    pm['inc'] = reg.map(lambda v: 1 if v.startswith('down')
                        else (-1 if v.startswith('up') else 0))
    pm = pm.dropna(subset=['k'])
    if subset:
        col, val = subset
        pm = pm[pm[col].astype(str) == val]
    g = pm.groupby('k')['inc'].agg(
        lambda s: (int((s == 1).sum()), int((s == -1).sum())))
    return dict(g)


def menda_orig(subset=None):
    """MENDA 원본(menda.xlsx, 5,675 entries / 464 studies)을
    compound -> (pos, neg) 로 집계한다.

    극성: MENDA 의 'Down'(우울증에서 감소) = 결핍 = 보충 가치 = pos(+1).
    'Up' = 질병에서 증가 = 악화 연관 = neg(-1).
    근거: KG 의 hasPositiveAssociation 목록이 MENDA 의 Up 집합과
    Jaccard 0.981 로 일치한다 (tools/diag.py menda_orig).

    subset: None 또는 (컬럼명, 값). 예: ('Tissue_Metabolite_level_2', 'Faece')
    """
    path = os.path.join(BASE, 'menda.xlsx')
    if not os.path.exists(path):
        return {}
    m = pd.read_excel(path, sheet_name='Metabolite')
    m['k'] = m['KEGG'].astype(str).str.extract(r'(C\d{5})')[0]
    r = m['Up/Down_regulated '].astype(str).str.strip().str.lower()
    m['inc'] = np.where(r.str.startswith(('down', 'decreas', 'lower')), 1,
                        np.where(r.str.startswith(('up', 'increas', 'higher')),
                                 -1, 0))
    m = m.dropna(subset=['k'])
    if subset:
        col, val = subset
        m = m[m[col].astype(str) == val]
    g = m.groupby('k')['inc'].agg(
        lambda s: (int((s == 1).sum()), int((s == -1).sum())))
    return dict(g)


def lookup(tab, kegg):
    """alias 를 고려해 표에서 값을 찾는다."""
    for k in kegg_alias.incidence_keys(kegg):
        if k in tab:
            return tab[k]
    return None


def direction(tab, kegg, margin=0.10, min_studies=2):
    c = lookup(tab, kegg)
    if c is None:
        return 0, '-'
    p_, n_ = c
    t = p_ + n_
    txt = f'{p_}:{n_}'
    if t < min_studies or abs(p_ - n_) / t < margin:
        return 0, txt
    return (1 if p_ > n_ else -1), txt


def paper85():
    return pd.read_csv(os.path.join(OUT, 'paper85_compounds.csv'))


def sources():
    """step3 가 부여한 compound 별 근거."""
    q = pd.read_csv(os.path.join(OUT, 'knowledge_query_results.csv'))
    return dict(zip(q['compound'], q['source'].astype(str)))


def heatmap():
    """논문 Fig. 4(c) 원본. 열을 food.csv 순서로 맞춰 돌려준다.

    반환: (B, kegg목록, 이름dict, 그룹dict)  — B 는 135 x 85
    """
    d = pd.read_excel(os.path.join(BASE, 'Food4healthKG/analyse/heatmap.xlsx'),
                      header=None)
    oidx = [int(v) for v in d.iloc[0]]
    perm = np.argsort(oidx)
    kegg_disp = list(d.iloc[1])
    name_disp = list(d.iloc[2])
    grp_disp = list(d.iloc[3])
    B = d.iloc[4:].apply(pd.to_numeric, errors='coerce').fillna(0).values[3:]
    return (B[:, perm], [kegg_disp[j] for j in perm],
            {kegg_disp[j]: name_disp[j] for j in range(len(kegg_disp))},
            {kegg_disp[j]: grp_disp[j] for j in range(len(kegg_disp))})


def run_steps(env_overrides, steps=('knowledge_query.py', 'map_promenda.py')):
    """파이프라인 일부를 환경변수와 함께 다시 돌린다 (A/B 용)."""
    import subprocess
    env = dict(os.environ, **{k: str(v) for k, v in env_overrides.items()})
    for sc in steps:
        r = subprocess.run([sys.executable, os.path.join(BASE, sc)],
                           capture_output=True, text=True, cwd=BASE, env=env)
        if r.returncode != 0:
            raise RuntimeError(f'{sc} 실패\n{r.stderr[-800:]}')
