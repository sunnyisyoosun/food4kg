"""04 — 앞 단계 산출물을 논문 §3.3 표현 규약대로 RDF 로 쓴다.

논문 Fig.1/Fig.2 의 prefix 와 관계를 그대로 쓰되 네임스페이스만 우리 것으로 분기한다.
  npq:  http://nutrition.vu.nl/pop/qualifier#        (food 쪽 qualifier)
  mpq:  http://nlp_microbe.ccnu.edu.cn/pop/qualifier# (microbe 쪽 qualifier)
  our:  http://nutrition.vu.nl/ourkg/                 (우리 KG 고유 엔티티)

관계 (논문 §3.3)
  self-defined : npq:hasNutrients, npq:hasNutrientWeights, mpq:hasMetabolites,
                 mpq:hasAssociation + hasPositiveAssociation/hasNegativeAssociation
  predefined   : rdf:type, rdfs:subClassOf, rdfs:label, owl:sameAs

출력
  out/ourkg.nt        N-Triples
  out/kg_stats.csv    논문 Table 1 대응 통계 (source, relation, entity, triples)
"""
import os
import sys
import csv
import hashlib
import collections

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT

NS = {
    'our': 'http://nutrition.vu.nl/ourkg/',
    'npq': 'http://nutrition.vu.nl/pop/qualifier#',
    'mpq': 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#',
    'ent': 'http://nutrition.vu.nl/entity#',
    'mic': 'http://nlp_microbe.ccnu.edu.cn/entity/',
    'kegg': 'https://www.kegg.jp/entry/',
    'mesh': 'http://id.nlm.nih.gov/mesh/',
    'mikg': 'http://ztonebv.com/MiKG#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
}

OUT_NT = os.path.join(OUT, 'ourkg.nt')
stats = collections.defaultdict(lambda: {'triples': 0, 'relations': set(), 'entities': set()})


def slug(s):
    return hashlib.md5(str(s).encode('utf-8')).hexdigest()[:12]


def esc(s):
    return (str(s).replace('\\', '\\\\').replace('"', '\\"')
            .replace('\n', '\\n').replace('\r', ''))


class Writer:
    def __init__(self, path):
        self.f = open(path, 'w', encoding='utf-8')
        self.n = 0

    def t(self, s, p, o, source, literal=False, dtype=None):
        obj = o if not literal else (
            f'"{esc(o)}"^^<{NS["xsd"]}{dtype}>' if dtype else f'"{esc(o)}"')
        if not literal:
            obj = f'<{o}>'
        self.f.write(f'<{s}> <{p}> {obj} .\n')
        self.n += 1
        st = stats[source]
        st['triples'] += 1
        st['relations'].add(p)
        st['entities'].add(s)
        if not literal:
            st['entities'].add(o)

    def close(self):
        self.f.close()


W = Writer(OUT_NT)
A = NS['rdf'] + 'type'
LABEL = NS['rdfs'] + 'label'
SUBCLASS = NS['rdfs'] + 'subClassOf'
SAMEAS = NS['owl'] + 'sameAs'
VALUE = NS['rdf'] + 'value'

print('[1/5] Food · Category (FDC)')
foods = pd.read_csv(os.path.join(OUT, 'foods.csv'))
long = pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))
food_uri = {k: NS['our'] + 'food/' + slug(k) for k in foods['food_key']}
cat_uri = {}
for _, r in foods.iterrows():
    u = food_uri[r['food_key']]
    W.t(u, A, NS['ent'] + 'Food', 'FoodData Central')
    W.t(u, LABEL, r['food_name'], 'FoodData Central', literal=True)
    W.t(u, NS['our'] + 'fdcId', str(r['fdc_id']), 'FoodData Central', literal=True)
    W.t(u, NS['our'] + 'dataType', r['data_type'], 'FoodData Central', literal=True)
    c = cat_uri.setdefault(r['food_group'], NS['our'] + 'category/' + slug(r['food_group']))
    W.t(u, SUBCLASS, c, 'FoodData Central')
for name, u in cat_uri.items():
    W.t(u, A, NS['ent'] + 'FoodCategory', 'FoodData Central')
    W.t(u, LABEL, name, 'FoodData Central', literal=True)
print(f'  음식 {len(foods):,} / 카테고리 {len(cat_uri)}')

print('[2/5] Food → Nutrient 중량 (npq:hasNutrients / hasNutrientWeights)')
for i, (fk, kegg, amt) in enumerate(long.itertuples(index=False), 1):
    fu = food_uri.get(fk)
    if fu is None:
        continue
    nu = f'{NS["our"]}weight/{slug(fk)}_{kegg}'
    cu = NS['kegg'] + kegg
    W.t(fu, NS['npq'] + 'hasNutrients', cu, 'FoodData Central')
    W.t(fu, NS['npq'] + 'hasNutrientWeights', nu, 'FoodData Central')
    W.t(nu, NS['npq'] + 'ofCompound', cu, 'FoodData Central')
    W.t(nu, VALUE, f'{amt:.10g}', 'FoodData Central', literal=True, dtype='double')
    if i % 200000 == 0:
        print(f'\r  {i:,}/{len(long):,}', end='', flush=True)
print(f'\r  중량 triple {len(long)*4:,}')

print('[3/5] Compound (KEGG) · depression 관계 (ProMENDA)')
E = pd.read_csv(os.path.join(OUT, 'compound_depression.csv'))
DEPRESSION = NS['mesh'] + 'D003865'
W.t(DEPRESSION, A, NS['ent'] + 'Disease', 'ProMENDA')
W.t(DEPRESSION, LABEL, 'Major depressive disorder', 'ProMENDA', literal=True)
food_cpds = set(long['kegg'].unique())
for kegg in sorted(food_cpds):
    cu = NS['kegg'] + kegg
    W.t(cu, A, NS['ent'] + 'Compound', 'KEGG')
    W.t(cu, NS['our'] + 'keggId', kegg, 'KEGG', literal=True)
n_rel = 0
for _, r in E.iterrows():
    if r['direction'] == 0:
        continue
    cu = NS['kegg'] + r['kegg']
    rel = 'hasPositiveAssociation' if r['direction'] > 0 else 'hasNegativeAssociation'
    W.t(cu, NS['npq'] + rel, DEPRESSION, 'ProMENDA')
    W.t(cu, NS['npq'] + 'hasAssociation', DEPRESSION, 'ProMENDA')
    W.t(cu, LABEL, r['name'], 'ProMENDA', literal=True)
    W.t(cu, NS['our'] + 'nStudy', str(int(r['n_study'])), 'ProMENDA', literal=True)
    n_rel += 1
print(f'  compound {len(food_cpds)} / depression 극성 관계 {n_rel}')

print('[4/5] Microbe (NCBI) · compound-microbe (KEGG) · microbe-disease')
mic = pd.read_csv(os.path.join(OUT, 'microbes.csv'), dtype={'taxid': str})
for _, r in mic.iterrows():
    u = NS['mic'] + r['taxid']
    W.t(u, A, NS['ent'] + 'Microbe', 'NCBI taxonomy')
    W.t(u, LABEL, r['name'], 'NCBI taxonomy', literal=True)
    W.t(u, NS['our'] + 'rank', str(r['rank']), 'NCBI taxonomy', literal=True)
    W.t(u, NS['our'] + 'lineage', str(r['lineage']), 'NCBI taxonomy', literal=True)
    if isinstance(r['kegg_org'], str) and r['kegg_org']:
        W.t(u, SAMEAS, f'https://www.kegg.jp/entry/gn:{r["kegg_org"]}', 'NCBI taxonomy')

cm = pd.read_csv(os.path.join(OUT, 'compound_microbe.csv'), dtype={'taxid': str})
for _, r in cm.iterrows():
    W.t(NS['mic'] + r['taxid'], NS['mpq'] + 'hasMetabolites',
        NS['kegg'] + r['kegg'], 'KEGG')
print(f'  미생물 {len(mic)} / compound-미생물 {len(cm):,}')

md = pd.read_csv(os.path.join(OUT, 'microbe_disease.csv'), dtype={'taxid': str})
for _, r in md.iterrows():
    du = NS['mesh'] + r['mesh_id']
    W.t(NS['mic'] + r['taxid'], NS['mpq'] + 'hasAssociation', du, 'MiKG')
    W.t(du, A, NS['ent'] + 'Disease', 'MiKG')
    if isinstance(r['disease'], str):
        W.t(du, LABEL, r['disease'], 'MiKG', literal=True)
    if r['is_mental']:
        W.t(du, SUBCLASS, NS['ent'] + 'MentalDisorder', 'MeSH')
    for tn in str(r['tree_numbers']).split(';'):
        if tn and tn != 'nan':
            W.t(du, NS['our'] + 'meshTree', tn, 'MeSH', literal=True)

print('[5/5] 신경전달물질 경로 (MiKG)')
mn = pd.read_csv(os.path.join(OUT, 'microbe_neurotransmitter.csv'))
nd = pd.read_csv(os.path.join(OUT, 'neurotransmitter_disease.csv'))
for _, r in mn.iterrows():
    mu = NS['mikg'] + str(r['microbe']).replace(' ', '-')
    nu = NS['mikg'] + str(r['neurotransmitter']).replace(' ', '-')
    W.t(mu, A, NS['ent'] + 'Microbe', 'MiKG')
    W.t(mu, LABEL, r['microbe'], 'MiKG', literal=True)
    W.t(mu, NS['mpq'] + 'hasMetabolites', nu, 'MiKG')
    if isinstance(r['nt_kegg'], str) and r['nt_kegg']:
        W.t(nu, SAMEAS, NS['kegg'] + r['nt_kegg'], 'MiKG')
for _, r in nd.iterrows():
    nu = NS['mikg'] + str(r['neurotransmitter']).replace(' ', '-')
    du = NS['mikg'] + str(r['disease']).replace(' ', '-')
    W.t(nu, A, NS['ent'] + 'Neurotransmitter', 'MiKG')
    W.t(nu, LABEL, r['neurotransmitter'], 'MiKG', literal=True)
    W.t(du, A, NS['ent'] + 'Disease', 'MiKG')
    W.t(du, SUBCLASS, NS['ent'] + 'MentalDisorder', 'MiKG')
    W.t(du, LABEL, r['disease'], 'MiKG', literal=True)
    W.t(nu, NS['mpq'] + 'hasAssociation', du, 'MiKG')

W.close()
print(f'\n총 triple {W.n:,}  →  {OUT_NT}')

rows = [{'source': s, 'relation': len(v['relations']),
         'entity': len(v['entities']), 'triples': v['triples']}
        for s, v in sorted(stats.items(), key=lambda kv: -kv[1]['triples'])]
all_rel = set().union(*[v['relations'] for v in stats.values()])
all_ent = set().union(*[v['entities'] for v in stats.values()])
rows.append({'source': 'Total', 'relation': len(all_rel),
             'entity': len(all_ent), 'triples': W.n})
st = pd.DataFrame(rows)
st.to_csv(os.path.join(OUT, 'kg_stats.csv'), index=False)
print()
print(st.to_string(index=False))
