"""
Food4healthKG 재현 전체 파이프라인 실행 + 로그 저장
===================================================
모든 Step의 터미널 출력을 logs/ 디렉토리에 저장

실행: python3 run_pipeline.py
"""

import subprocess
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

steps = [
    ('step1_fatty_acid_kegg', 'add_fatty_acid_kegg.py'),
    ('step2_reconstruct',     'reconstruct_v2.py'),
    ('step3_inference',       'knowledge_inference_v3.py'),
    ('step4_promenda',        'map_promenda.py'),
    ('step5_recommendation',  'run_recommendation.py'),
]

# Step 1 후 food_nutrient_updated.csv → food_nutrient.csv 복사 필요
COPY_AFTER_STEP1 = True

print(f"{'='*60}")
print(f"Food4healthKG 재현 파이프라인")
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"로그 디렉토리: {LOG_DIR}")
print(f"{'='*60}\n")

all_logs = []
success = True

for i, (step_name, script) in enumerate(steps):
    script_path = os.path.join(BASE_DIR, script)
    log_file = os.path.join(LOG_DIR, f'{timestamp}_{step_name}.txt')
    
    if not os.path.exists(script_path):
        print(f"  ❌ {script} 파일 없음 — 건너뜀")
        continue
    
    print(f"[{i+1}/{len(steps)}] {step_name} 실행 중...")
    
    # 실행 + stdout/stderr 캡처
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )
    
    output = result.stdout + ('\n--- STDERR ---\n' + result.stderr if result.stderr.strip() else '')
    
    # 로그 파일 저장
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"# {step_name}\n")
        f.write(f"# Script: {script}\n")
        f.write(f"# Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Return code: {result.returncode}\n")
        f.write(f"{'='*60}\n\n")
        f.write(output)
    
    all_logs.append((step_name, log_file, result.returncode, output))
    
    # 터미널에도 출력
    print(output)
    
    if result.returncode != 0:
        print(f"  ❌ {step_name} 실패 (return code: {result.returncode})")
        success = False
        break
    else:
        print(f"  ✅ {step_name} 완료 → {log_file}\n")
    
    # Step 1 후 파일 복사
    if i == 0 and COPY_AFTER_STEP1:
        src = os.path.join(BASE_DIR, 'food_nutrient_updated.csv')
        dst = os.path.join(BASE_DIR, 'food_nutrient.csv')
        if os.path.exists(src):
            import shutil
            shutil.copy2(src, dst)
            print(f"  📋 food_nutrient_updated.csv → food_nutrient.csv 복사 완료\n")

# 전체 결과 요약 저장
summary_file = os.path.join(LOG_DIR, f'{timestamp}_summary.txt')
with open(summary_file, 'w', encoding='utf-8') as f:
    f.write(f"Food4healthKG 재현 파이프라인 결과\n")
    f.write(f"실행: {timestamp}\n")
    f.write(f"{'='*60}\n\n")
    
    for step_name, log_file, returncode, output in all_logs:
        status = '✅' if returncode == 0 else '❌'
        f.write(f"{status} {step_name} (code={returncode})\n")
        f.write(f"   로그: {log_file}\n\n")
    
    f.write(f"\n{'='*60}\n")
    f.write(f"전체 결과: {'성공' if success else '실패'}\n")
    
    # 마지막 Step 5 결과에서 핵심 지표 추출
    if all_logs:
        last_output = all_logs[-1][3]
        f.write(f"\n{'='*60}\n")
        f.write(f"최종 추천 결과 (Step 5)\n")
        f.write(f"{'='*60}\n\n")
        # 카테고리 분포 이후 부분 저장
        for line in last_output.split('\n'):
            if any(kw in line for kw in ['카테고리', 'Top 30', 'Bottom', '===', 'type=', 
                                          '논문', 'RMSE', 'MAE', 'PCA', 'Foods:', 'Compounds:']):
                f.write(line + '\n')

print(f"\n{'='*60}")
print(f"파이프라인 {'완료 ✅' if success else '실패 ❌'}")
print(f"{'='*60}")
print(f"  로그 디렉토리: {LOG_DIR}/")
print(f"  요약: {summary_file}")
print(f"  개별 로그:")
for step_name, log_file, returncode, _ in all_logs:
    status = '✅' if returncode == 0 else '❌'
    print(f"    {status} {os.path.basename(log_file)}")
