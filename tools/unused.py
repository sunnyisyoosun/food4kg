"""
미사용 파일 분류
==================
파이프라인·도구·문서에서 참조되지 않는 파일을 찾아 등급으로 나눈다.
**삭제하지 않는다.** 판단 근거만 출력한다.

    python3 tools/unused.py
"""
import os
import re
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 참조를 찾을 대상 (여기 안의 텍스트에서 파일명이 언급되는지 본다)
SEARCH_DIRS = ['.', 'tools', 'eval', 'setup']
SEARCH_EXT = ('.py', '.md')

# 데이터·산출물이라 '참조 없음'이 곧 미사용을 뜻하지 않는 것
DATA_LIKE = ('.csv', '.xlsx', '.png', '.docx', '.jsonld', '.trig', '.ttl',
             '.txt', '.zip')


def human(n):
    for u in ('B', 'K', 'M', 'G'):
        if n < 1024 or u == 'G':
            return f'{n:.0f}{u}' if u == 'B' else f'{n:.1f}{u}'
        n /= 1024


def corpus():
    text = []
    for d in SEARCH_DIRS:
        p = os.path.join(BASE, d)
        if not os.path.isdir(p):
            continue
        for f in os.listdir(p):
            if f.endswith(SEARCH_EXT):
                try:
                    text.append(open(os.path.join(p, f), errors='ignore').read())
                except OSError:
                    pass
    return '\n'.join(text)


TEXT = corpus()


def referenced(name):
    base = os.path.basename(name)
    stem = os.path.splitext(base)[0]
    return (base in TEXT) or (f'import {stem}' in TEXT)


def size(path):
    try:
        if os.path.isdir(path):
            return sum(os.path.getsize(os.path.join(r, f))
                       for r, _, fs in os.walk(path) for f in fs)
        return os.path.getsize(path)
    except OSError:
        return 0


print('=' * 76)
print('A. 확실히 안 씀 — 지워도 파이프라인에 영향 없음')
print('=' * 76)
total_a = 0
legacy = os.path.join(BASE, 'legacy')
if os.path.isdir(legacy):
    for f in sorted(os.listdir(legacy)):
        p = os.path.join(legacy, f)
        s = size(p)
        total_a += s
        print(f'  legacy/{f:34s} {human(s):>8s}  구버전. REPRODUCTION.md 에 기록됨')
for d in ('__pycache__', 'tools/__pycache__', 'eval/__pycache__'):
    p = os.path.join(BASE, d)
    if os.path.exists(p):
        s = size(p)
        total_a += s
        print(f'  {d + "/":41s} {human(s):>8s}  파이썬 캐시')
print(f'  -> 합계 약 {human(total_a)}')

print()
print('=' * 76)
print('B. 중복 데이터 — 재생성 가능, 용량 큼')
print('=' * 76)
total_b = 0
cand = [
    ('food_nutrient_updated.csv',
     '구 step1 의 출력. step1 은 legacy/ 로 옮겨 파이프라인에서 빠졌다. '
     'food_nutrient.csv 와 바이트까지 동일 (cmp 로 확인)'),
    ('fdc_raw',
     'FDC 원본. setup/rebuild_food_nutrient.py 로 food_nutrient.csv 를 '
     '다시 만들 때만 필요. 보관하면 재다운로드 불필요'),
]
for f, why in cand:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        s = size(p)
        total_b += s
        print(f'  {f:41s} {human(s):>8s}')
        print(f'    {why}')
print(f'  -> 합계 약 {human(total_b)}')

print()
print('=' * 76)
print('C. 로그 — 오래된 실행 기록')
print('=' * 76)
logs = os.path.join(BASE, 'logs')
if os.path.isdir(logs):
    runs = {}
    for f in os.listdir(logs):
        m = re.match(r'(\d{8}_\d{6})_', f)
        if m:
            runs.setdefault(m.group(1), []).append(f)
    keep = sorted(runs)[-1:] if runs else []
    old = sum(size(os.path.join(logs, f))
              for r in runs if r not in keep for f in runs[r])
    print(f'  실행 {len(runs)}회분, 파일 {sum(len(v) for v in runs.values())}개')
    print(f'  최신 {keep[0] if keep else "-"} 만 남기면 약 {human(old)} 정리')

print()
print('=' * 76)
print('D. 참조가 없는 코드 — 확인 필요')
print('=' * 76)
found = False
for d in SEARCH_DIRS:
    p = os.path.join(BASE, d)
    if not os.path.isdir(p):
        continue
    for f in sorted(os.listdir(p)):
        if not f.endswith('.py') or f == 'unused.py':
            continue
        rel = f if d == '.' else f'{d}/{f}'
        # 자기 자신을 제외한 참조
        others = TEXT.replace(open(os.path.join(p, f), errors='ignore').read(), '')
        if f not in others and f'import {os.path.splitext(f)[0]}' not in others:
            print(f'  {rel:41s} {human(size(os.path.join(p, f))):>8s}  '
                  f'다른 파일에서 언급 없음')
            found = True
if not found:
    print('  없음')

print()
print('=' * 76)
print('E. 유지해야 하는 것')
print('=' * 76)
print('  analyse/            파이프라인 산출물 + p5_foodname.txt(논문 파일)')
print('  Food4healthKG/      공식 repo 사본 (heatmap.xlsx, final.py, Supplements)')
print('  foodkg_triply/      논문 KG')
print('  MiKG-JAIMS/         MiKG')
print('  41398_..._ESM.xlsx  ProMENDA')
print('  food_nutrient.csv   파이프라인 입력 (fdc_raw 에서 재생성 가능)')
print('  setup/              nutrient_kegg_map.csv 는 재조립에 필수')
