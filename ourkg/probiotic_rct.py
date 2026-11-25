"""우울/불안 프로바이오틱스 RCT 정답표를 만들고 gut-brain 가정을 검정한다.

    python3 ourkg/probiotic_rct.py build     # setup/probiotic_rct.csv 생성
    python3 ourkg/probiotic_rct.py test      # 커버리지 + 순열 검정

왜 필요한가 — RESULTS.md §15c 에서 미생물 매개 가중을 기각하면서 "두 평가
기준이 모두 compound 직접 경로로 만들어진 자라 이 가중이 옳은지 잴 자가
없다" 고 적었다. 그 자를 외부에서 만든다.

PMC 는 봇 차단이 걸려 메타분석 본문을 못 읽는다. E-utilities 로 직접 만든다 —
재현 가능하고 차단이 없다.

**이 목록은 "효과가 입증된 균" 이 아니다.** RCT 에서 **시험된** 균이다.
메타분석 풀링 효과가 SMD -0.34 (95% CI -0.76~0.09, 유의하지 않음, I2=75%)
이고 균주별 결론은 저자들도 잠정적이라고 적는다.
"""
import collections, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from common import BASE, OUT, cached_get, compound_microbe, depression_e

UA = {'User-Agent': 'ourkg/1.0 (food4health reproduction+extension)'}
QUERY = ('(probiotic*[tiab] OR Lactobacillus[tiab] OR Bifidobacterium[tiab] OR '
         'Lactiplantibacillus[tiab] OR Limosilactobacillus[tiab]) AND '
         '(depression[tiab] OR depressive[tiab] OR anxiety[tiab]) AND '
         'randomized controlled trial[pt] AND humans[mh]')
GENUS = (r'(Lactobacillus|Lactiplantibacillus|Limosilactobacillus|Lacticaseibacillus|'
         r'Levilactobacillus|Ligilactobacillus|Bifidobacterium|Streptococcus|'
         r'Lactococcus|Saccharomyces|Clostridium|Akkermansia|Faecalibacterium|'
         r'Bacteroides|Enterococcus)')
# 둘째 토큰이 영어 낱말이면 종명이 아니다 ('Bifidobacterium and', 'Lactobacillus was').
STOP = (r'^(and|was|were|spp|species|abundance|decreased|increased|levels?|counts?|'
        r'group|strain|supplementation|intake|treatment|administration|genus|had|'
        r'has|may|is|are|in|to|of|the|before|did|without|strains)$')
# NCBI 가 옛 이름을 **검색 색인에서 지운** 둘. taxid 레코드의 동의어 목록으로 확인했다
# ('Lactobacillus reuteri Kandler et al. 1982' -> 1598).
RENAMED = {'Lactobacillus plantarum': ('1590', 'Lactiplantibacillus plantarum'),
           'Lactobacillus reuteri': ('1598', 'Limosilactobacillus reuteri')}


def _get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read().decode()


def _eu(cgi, **kw):
    out = _get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/' + cgi + '?'
               + urllib.parse.urlencode(kw))
    time.sleep(0.4)
    return out


def build():
    ids = json.loads(_eu('esearch.fcgi', db='pubmed', term=QUERY, retmax=300,
                         retmode='json', sort='relevance'))['esearchresult']['idlist']
    print(f'[1/3] RCT {len(ids)} 편')

    def fetch():
        docs = {}
        for i in range(0, len(ids), 100):
            txt = _eu('efetch.fcgi', db='pubmed', id=','.join(ids[i:i + 100]),
                      retmode='xml', rettype='abstract')
            for m in re.finditer(r'<PubmedArticle>.*?</PubmedArticle>', txt, re.S):
                a = m.group(0)
                pid = re.search(r'<PMID[^>]*>(\d+)</PMID>', a)
                if pid:
                    docs[pid.group(1)] = re.sub(r'<[^>]+>', ' ', ' '.join(re.findall(
                        r'<(?:ArticleTitle|AbstractText)[^>]*>(.*?)'
                        r'</(?:ArticleTitle|AbstractText)>', a, re.S)))
        return json.dumps(docs)

    docs = json.loads(cached_get('probiotic_rct_abstracts.json', fetch))
    sp = collections.defaultdict(set)
    for pid, body in docs.items():
        for m in re.finditer(GENUS + r'\s+([a-z]{3,})\b', body):
            sp[f'{m.group(1)} {m.group(2)}'].add(pid)
    print(f'[2/3] 초록 {len(docs)} 에서 후보 종 {len(sp)}')

    def resolve(name):
        """이름 -> 종 수준 taxid. **개명 함정을 두 번 넘어야 한다.**

        `[Scientific Name]` 정확 검색은 개명된 종을 전부 버린다(L. rhamnosus ->
        Lacticaseibacillus). 그래서 필드 제한 없이 찾되, 돌려받은 taxid 의 rank 를
        확인하고 아종·균주면 **종 수준 조상**으로 올라간다(B. lactis ->
        B. animalis). 옛 이름이 색인에서 아예 빠진 둘은 RENAMED 로 처리한다.
        """
        if name in RENAMED:
            return RENAMED[name]
        found = json.loads(_eu('esearch.fcgi', db='taxonomy', term=name,
                               retmode='json'))['esearchresult'].get('idlist') or []
        if not found:
            return None, None
        x = _eu('efetch.fcgi', db='taxonomy', id=found[0], retmode='xml')
        rank = re.search(r'<Rank>(.*?)</Rank>', x)
        cur = re.search(r'<ScientificName>(.*?)</ScientificName>', x)
        if not (rank and cur):
            return None, None
        if rank.group(1) != 'species':
            for t, n, r in re.findall(r'<Taxon>\s*<TaxId>(\d+)</TaxId>\s*'
                                      r'<ScientificName>(.*?)</ScientificName>\s*'
                                      r'<Rank>(.*?)</Rank>', x):
                if r == 'species':
                    return t, n
            return None, None
        return found[0], cur.group(1)

    by = collections.defaultdict(lambda: {'names': set(), 'pmids': set(), 'cur': ''})
    for i, (name, pmids) in enumerate(sorted(sp.items(), key=lambda kv: -len(kv[1]))):
        if re.match(STOP, name.split()[1], re.I):
            continue
        t, cur = resolve(name)
        print(f'\r  {i + 1}/{len(sp)} 해소 {len(by)}', end='', flush=True)
        if not t:
            continue
        b = by[t]
        b['names'].add(name)
        b['pmids'] |= set(pmids)
        b['cur'] = cur
    print()

    rows = sorted(by.items(), key=lambda kv: -len(kv[1]['pmids']))
    out = pd.DataFrame([{'taxid': t, 'species': b['cur'],
                         'names_in_abstracts': ';'.join(sorted(b['names'])),
                         'n_rct': len(b['pmids']),
                         'pmids': ';'.join(sorted(b['pmids'])[:10])} for t, b in rows])
    path = os.path.join(BASE, 'setup', 'probiotic_rct.csv')
    out.to_csv(path, index=False)
    print(f'[3/3] 종 {len(out)} / RCT 연결 {int(out.n_rct.sum())}  ->  {path}')


def test(n_perm=2000):
    rct = pd.read_csv(os.path.join(BASE, 'setup', 'probiotic_rct.csv'), dtype={'taxid': str})
    mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str}).fillna('')
    print('[1/2] 커버리지 — RCT 종이 우리 미생물 축에 있는가')
    have = set(rct.taxid) & set(mic.taxid)
    print(f'  {len(have)}/{len(rct)} 종 '
          f'(compound 연결 있는 것 {len(set(rct.taxid) & set(compound_microbe().taxid))})')
    print('  없는 종:', rct[~rct.taxid.isin(mic.taxid)].species.tolist())

    print('[2/2] 순열 검정 — RCT 종이 E>0 compound 를 더 대사하는가')
    E = depression_e('e_shrunk')
    cm = compound_microbe()
    cm = cm[cm.kegg.isin(E.index[E != 0])]
    pool = sorted(set(cm.taxid))
    inr = [t for t in pool if t in set(rct.taxid)]
    rng = np.random.default_rng(0)
    print(f'  대상 균 {len(pool)} (그중 RCT {len(inr)})')
    for lab, f in (('평균 E', lambda x: float(E.reindex(cm[cm.taxid.isin(x)].kegg).mean())),
                   ('E>0 비율', lambda x: float((E.reindex(cm[cm.taxid.isin(x)].kegg) > 0).mean()))):
        obs = f(inr)
        null = np.array([f(rng.choice(pool, len(inr), replace=False)) for _ in range(n_perm)])
        print(f'  {lab:9s} 관측 {obs:+.4f} / 귀무 {null.mean():+.4f}±{null.std():.4f} '
              f' p = {float((null >= obs).mean()):.4f}')


if __name__ == '__main__':
    {'build': build, 'test': test}[sys.argv[1] if len(sys.argv) > 1 else 'test']()
