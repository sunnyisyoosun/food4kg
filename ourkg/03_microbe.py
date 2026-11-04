"""03 — 미생물 축 최신화: NCBI taxonomy + KEGG.

논문 §3.1 은 (a) NCBI taxonomy 322,917 미생물, (b) KEGG 230 metabolite,
(c) MiKG 1,234 미생물-정신질환 관계를 썼다.

여기서는
  미생물 - 정신질환 : Food4healthKG 배포본 Disease_Bacteria (MiKG 유래) 에서
                      taxid - MeSH 쌍을 뽑고, MeSH SPARQL 로 tree number 를
                      지금 받아 F03(Mental Disorders) 여부를 판정한다.
  미생물 이름/계통   : NCBI efetch 로 현재 학명·rank·lineage 로 갱신.
  compound - 미생물  : KEGG REST 로 지금 다시 계산한다.
                      compound -> enzyme(EC) -> KO -> organism.

출력 (모두 out/)
  microbe_disease.csv       taxid, name, mesh_id, disease, tree_numbers, is_mental
  microbes.csv              taxid, name(NCBI 현재), rank, lineage, kegg_org
  compound_microbe.csv      kegg, taxid, kegg_org, n_ko   (hasMetabolites)
캐시: ourkg/cache/
"""
import os
import re
import sys
import json
import time
import collections
import urllib.parse

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE, OUT

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE, exist_ok=True)
S = requests.Session()
S.headers['User-Agent'] = 'ourkg/1.0 (food4health reproduction+extension)'


def cached(name, fetch, ttl_days=30):
    p = os.path.join(CACHE, name)
    if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < ttl_days * 86400:
        return open(p, encoding='utf-8').read()
    txt = fetch()
    open(p, 'w', encoding='utf-8').write(txt)
    return txt


def kegg(path):
    def f():
        r = S.get(f'https://rest.kegg.jp/{path}', timeout=180)
        r.raise_for_status()
        time.sleep(0.34)
        return r.text
    return cached('kegg_' + path.replace('/', '_') + '.txt', f)


# ------------------------------------------------------------------
print('[1/5] Disease_Bacteria → taxid - MeSH 쌍')
HA = 'http://nlp_microbe.ccnu.edu.cn/pop/qualifier#hasAssociation'
LAB = 'http://www.w3.org/2000/01/rdf-schema#label'
graph = json.load(open(os.path.join(BASE, 'foodkg_triply', 'Disease_Bacteria.jsonld'),
                       encoding='utf-8'))[0]['@graph']
labels = {n['@id']: n[LAB][0]['@value'] for n in graph if LAB in n}
pairs = []
for n in graph:
    if HA not in n:
        continue
    m = re.search(r'/entity/(\d+)$', n['@id'])
    if not m:
        continue
    for o in n[HA]:
        d = o['@id'].rsplit('/', 1)[-1]
        if d.startswith('D'):
            pairs.append((m.group(1), d))
pairs = sorted(set(pairs))
taxids = sorted({t for t, _ in pairs})
meshids = sorted({d for _, d in pairs})
print(f'  관계 {len(pairs):,} / 미생물 {len(taxids):,} / 질환 {len(meshids):,}')

# ------------------------------------------------------------------
print('[2/5] MeSH tree number (id.nlm.nih.gov SPARQL) → F03 판정')


def fetch_tree():
    out = {}
    for i in range(0, len(meshids), 60):
        chunk = meshids[i:i + 60]
        values = ' '.join(f'mesh:{d}' for d in chunk)
        q = ('PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#> '
             'PREFIX mesh: <http://id.nlm.nih.gov/mesh/> '
             f'SELECT ?d ?tn WHERE {{ VALUES ?d {{ {values} }} '
             '?d meshv:treeNumber ?tn }')
        r = S.get('https://id.nlm.nih.gov/mesh/sparql',
                  params={'query': q, 'format': 'JSON', 'limit': 5000}, timeout=120)
        r.raise_for_status()
        for b in r.json()['results']['bindings']:
            d = b['d']['value'].rsplit('/', 1)[-1]
            out.setdefault(d, []).append(b['tn']['value'].rsplit('/', 1)[-1])
        time.sleep(0.5)
        print(f'\r  {min(i+60, len(meshids))}/{len(meshids)}', end='', flush=True)
    print()
    return json.dumps(out)


tree = json.loads(cached('mesh_tree.json', fetch_tree))
mental = {d for d, tns in tree.items() if any(t.startswith('F03') for t in tns)}
neuro = {d for d, tns in tree.items()
         if any(t.startswith('C10.574') or t.startswith('C10.228.140') for t in tns)}
print(f'  tree number 확보 {len(tree)}/{len(meshids)} / F03 정신질환 {len(mental)} '
      f'/ 신경퇴행 등 {len(neuro)}')

md = pd.DataFrame(pairs, columns=['taxid', 'mesh_id'])
md['disease'] = md['mesh_id'].map(lambda d: labels.get(f'http://id.nlm.nih.gov/mesh/{d}', ''))
md['tree_numbers'] = md['mesh_id'].map(lambda d: ';'.join(tree.get(d, [])))
md['is_mental'] = md['mesh_id'].isin(mental)
md['is_neuro'] = md['mesh_id'].isin(neuro)
print(f'  정신질환 관계 {int(md.is_mental.sum()):,} '
      f'(미생물 {md[md.is_mental].taxid.nunique()} 종, 질환 {md[md.is_mental].mesh_id.nunique()} 종)')
for d, n in md[md.is_mental].disease.value_counts().head(12).items():
    print(f'     {n:4d}  {d}')

# ------------------------------------------------------------------
print('[3/5] NCBI taxonomy 로 학명·계통 갱신')
focus = sorted(set(md[md.is_mental | md.is_neuro]['taxid']))
print(f'  대상 {len(focus)} 종 (정신질환·신경퇴행 연관 미생물)')


def fetch_tax():
    recs = {}
    for i in range(0, len(focus), 200):
        chunk = focus[i:i + 200]
        r = S.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
                  params={'db': 'taxonomy', 'id': ','.join(chunk), 'retmode': 'xml'},
                  timeout=120)
        r.raise_for_status()
        import xml.etree.ElementTree as ET
        for tx in ET.fromstring(r.text).findall('Taxon'):
            recs[tx.findtext('TaxId')] = {
                'name': tx.findtext('ScientificName'),
                'rank': tx.findtext('Rank'),
                'lineage': tx.findtext('Lineage') or '',
            }
        time.sleep(0.4)
        print(f'\r  {min(i+200, len(focus))}/{len(focus)}', end='', flush=True)
    print()
    return json.dumps(recs)


tax = json.loads(cached('ncbi_taxonomy.json', fetch_tax))
print(f'  갱신된 taxon {len(tax)}')

# ------------------------------------------------------------------
print('[4/5] KEGG organism 매칭')
# KEGG 는 list/organism 을 내렸다(400). list/genome 형식: "T00202\tbfr; Bacteroides fragilis YCH46"
org_txt = kegg('list/genome')
orgs = []
for line in org_txt.strip().split('\n'):
    f = line.split('\t')
    if len(f) < 2 or '; ' not in f[1]:
        continue
    code, name = f[1].split('; ', 1)
    orgs.append({'tnum': f[0], 'org': code.strip(), 'name': name.strip()})
print(f'  KEGG organism {len(orgs):,}')
by_species = collections.defaultdict(list)
for o in orgs:
    sp = ' '.join(re.sub(r'\(.*?\)', '', o['name']).split()[:2]).lower()
    by_species[sp].append(o['org'])

tax_org = {}
for t, rec in tax.items():
    sp = ' '.join(rec['name'].split()[:2]).lower()
    if sp in by_species:
        tax_org[t] = by_species[sp][0]
print(f'  KEGG organism 코드 연결 {len(tax_org)}/{len(tax)}')

micro = pd.DataFrame([{'taxid': t, **rec, 'kegg_org': tax_org.get(t, '')}
                      for t, rec in tax.items()])
micro.to_csv(os.path.join(OUT, 'microbes.csv'), index=False)
md.to_csv(os.path.join(OUT, 'microbe_disease.csv'), index=False)

# ------------------------------------------------------------------
print('[5/5] KEGG compound → EC → KO → organism')
cpds = set(pd.read_csv(os.path.join(OUT, 'food_compound_long.csv'))['kegg'].unique())

c2ec = collections.defaultdict(set)
for line in kegg('link/enzyme/compound').strip().split('\n'):
    a, b = line.split('\t')
    c = a.split(':')[-1]
    if c in cpds:
        c2ec[c].add(b.split(':')[-1])
print(f'  compound -> EC: {len(c2ec)} compound, {sum(len(v) for v in c2ec.values()):,} 링크')

ec2ko = collections.defaultdict(set)
for line in kegg('link/ko/enzyme').strip().split('\n'):
    a, b = line.split('\t')
    ec2ko[a.split(':')[-1]].add(b.split(':')[-1])

c2ko = {c: {k for e in ecs for k in ec2ko.get(e, ())} for c, ecs in c2ec.items()}
print(f'  compound -> KO: 중앙값 {pd.Series([len(v) for v in c2ko.values()]).median():.0f}')

rows = []
orgcodes = sorted({v for v in tax_org.values() if v})
for i, org in enumerate(orgcodes, 1):
    try:
        txt = kegg(f'link/ko/{org}')
    except Exception as e:
        print(f'\n  ! {org}: {e}')
        continue
    kos = {l.split('\t')[1].split(':')[-1] for l in txt.strip().split('\n') if '\t' in l}
    for t, o in tax_org.items():
        if o != org:
            continue
        for c, cko in c2ko.items():
            n = len(cko & kos)
            if n:
                rows.append({'kegg': c, 'taxid': t, 'kegg_org': org, 'n_ko': n})
    print(f'\r  organism {i}/{len(orgcodes)}  링크 {len(rows):,}', end='', flush=True)
print()
cm = pd.DataFrame(rows)
cm.to_csv(os.path.join(OUT, 'compound_microbe.csv'), index=False)
print(f'  compound-미생물 {len(cm):,} 링크 / compound {cm["kegg"].nunique()} '
      f'/ 미생물 {cm["taxid"].nunique()}')


# ------------------------------------------------------------------
# 6. MiKG 원본 — 미생물 → 신경전달물질 → 정신질환 (gut-brain axis 경로)
#
# Disease_Bacteria 만으로는 정신질환 관계가 얇다(F03 6종, 우울증 1건).
# MiKG(Liu et al. 2021) 원본은 미생물-신경전달물질 statement 와
# 신경전달물질-정신질환 relationship 을 따로 두고, 둘을 이어야 논문이 말한
# "미생물-정신질환" 관계가 나온다.
# ------------------------------------------------------------------
print('[6/6] MiKG 원본 — 미생물 → 신경전달물질 → 정신질환')
from rdflib import Graph, URIRef

MI = 'http://ztonebv.com/MiKG#'
g = Graph()
g.parse(os.path.join(BASE, 'MiKG-JAIMS', 'MiKG_Schema_Data_20201007.ttl'), format='turtle')


def _p(n):
    return URIRef(MI + n)


def _local(u):
    return str(u).split('#')[-1].replace('-', ' ')


# 신경전달물질 → KEGG compound (KEGG 엔트리로 확인한 표준 ID)
NT_KEGG = {'Dopamine': 'C03758', 'Serotonin': 'C00780', 'GABA': 'C00334',
           'Norepinephrine': 'C00547', 'Acetylcholine': 'C01996',
           'Glutamate': 'C00025', 'Histamine': 'C00388', 'Melatonin': 'C01598',
           'Epinephrine': 'C00788', 'Glycine': 'C00037'}

mn = []
for s, _, mic in g.triples((None, _p('hasGutMicrobiota'), None)):
    for nt in g.objects(s, _p('hasNeurotransmitter')):
        mods = [str(o) for o in g.objects(s, _p('hasModulation'))]
        pmids = [str(o).split('pmid')[-1] for o in g.objects(s, _p('hasReference'))]
        mn.append({'microbe': _local(mic), 'neurotransmitter': _local(nt),
                   'nt_kegg': NT_KEGG.get(_local(nt), ''),
                   'modulation': ';'.join(mods), 'pmids': ';'.join(pmids)})
mn = pd.DataFrame(mn).drop_duplicates()

nd = []
for s, _, dis in g.triples((None, _p('hasMentalDisorder'), None)):
    for nt in g.objects(s, _p('hasNeurotransmitter')):
        pmids = [str(o).split('pmid')[-1] for o in g.objects(s, _p('hasReference'))]
        nd.append({'neurotransmitter': _local(nt), 'disease': _local(dis),
                   'nt_kegg': NT_KEGG.get(_local(nt), ''), 'pmids': ';'.join(pmids)})
nd = pd.DataFrame(nd).drop_duplicates()

mn.to_csv(os.path.join(OUT, 'microbe_neurotransmitter.csv'), index=False)
nd.to_csv(os.path.join(OUT, 'neurotransmitter_disease.csv'), index=False)

joined = mn.merge(nd[['neurotransmitter', 'disease']], on='neurotransmitter')
joined[['microbe', 'neurotransmitter', 'disease']].drop_duplicates().to_csv(
    os.path.join(OUT, 'microbe_disease_mikg.csv'), index=False)
print(f'  미생물-신경전달물질 {len(mn)} / 신경전달물질-정신질환 {len(nd)} '
      f'/ 이어 붙인 미생물-정신질환 {len(joined.drop_duplicates(["microbe", "disease"])):,}')
print(f'  미생물 {mn.microbe.nunique()} 종 / 정신질환 {nd.disease.nunique()} 종 '
      f'/ KEGG 로 연결된 신경전달물질 {int((mn.nt_kegg != "").sum() > 0) and mn[mn.nt_kegg != ""].neurotransmitter.nunique()}')
print('  정신질환:', ', '.join(sorted(nd.disease.unique())))
