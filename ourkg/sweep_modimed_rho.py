"""빈도 가중 순위 상관이 Top-K 와 같은 방향인지 잰다 -> out/modimed_rho_comparison.csv

    MODIMED_RHO_TOP=200 python3 ourkg/sweep_modimed_rho.py

§13 에서 AUC 가 Top-K 와 어긋났던 설정 넷으로 잰다. 결론은 RESULTS.md §13b.
"""
import os, sys, importlib, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/yoosun/food_recom_w_paper/ourkg')
import pandas as pd
REC = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
       'Vegetables and Vegetable Products'}
NOT = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
       'Beef Products', 'Pork Products'}
CFG = [('linked', '0', '기본'), ('all', '0', 'all+0'),
       ('linked', 'auto', 'linked+PCA'), ('all', 'auto', 'all+auto(기각)')]
rows = []
for fc, pca, lab in CFG:
    os.environ['F_COLUMNS'], os.environ['PCA_COMPONENTS'] = fc, pca
    os.environ['GUTBRAIN_ALPHA'] = '0'
    import analyze; importlib.reload(analyze)
    res = analyze.recommend(save=False)
    sc = analyze.modimed_score(res, 30)
    t, b = res.head(30), res.tail(30)
    rows.append({'설정': lab,
                 'Top30_추천군': int(t.food_group.isin(REC).sum()),
                 'Bot30_비추천군': int(b.food_group.isin(NOT).sum()),
                 'AUC(참고)': sc.get('modimed_AUC(참고)'),
                 'rho_처방군': sc.get('modimed_rho_처방군만'),
                 'rho_전체': sc.get('modimed_rho_전체'),
                 'rho_상위': sc.get(f"modimed_rho_상위{os.environ.get('MODIMED_RHO_TOP','0')}")})
t = pd.DataFrame(rows)
t.to_csv('/home/yoosun/food_recom_w_paper/ourkg/out/modimed_rho_comparison.csv', index=False)
print(); print(t.to_string(index=False))
