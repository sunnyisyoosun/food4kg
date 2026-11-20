"""GUTBRAIN_ALPHA 를 쓸어 두 기준으로 잰다 -> out/gutbrain_comparison.csv

    python3 ourkg/sweep_gutbrain.py

미생물 매개 가중(analyze.gutbrain_weight)의 세기를 눈대중이 아니라 측정으로
고르려고 둔다. 결론은 RESULTS.md 에 있다.
"""
import os, sys, importlib
sys.path.insert(0, '/home/yoosun/food_recom_w_paper/ourkg')
import pandas as pd
REC_OK = {'Finfish and Shellfish Products', 'Fruits and Fruit Juices',
          'Vegetables and Vegetable Products'}
NOT_OK = {'Sausages and Luncheon Meats', 'Baked Products', 'Sweets',
          'Beef Products', 'Pork Products'}
rows = []
for spec in os.environ.get('WHO', 'mental,rct').split(','):
  who, _, src = spec.partition('/')
  os.environ['GUTBRAIN_SOURCE'] = src or 'both'
  for alpha in (0, 0.5, 1, 2, 4, 8):
      os.environ['GUTBRAIN_ALPHA'] = str(alpha)
      os.environ['GUTBRAIN_MICROBES'] = who
      import analyze; importlib.reload(analyze)
      res = analyze.recommend(save=False)
      K = 30
      top, bot = res.head(K), res.tail(K)
      sc = analyze.modimed_score(res, K)
      rows.append({'who': spec, 'alpha': alpha,
                   'top30_추천군': int(top.food_group.isin(REC_OK).sum()),
                   'bot30_비추천군': int(bot.food_group.isin(NOT_OK).sum()),
                   'top30_위반': int(top.food_group.isin(NOT_OK).sum()),
                   'MMD_처방군': sc.get(f'top{K}_처방군', ''),
                   'MMD_extras': sc.get(f'top{K}_extras', ''),
                   'AUC(참고)': sc.get('modimed_AUC(참고)', ''),
                   'top1': top.iloc[0].food_name[:38]})
t = pd.DataFrame(rows)
t.to_csv('/home/yoosun/food_recom_w_paper/ourkg/out/gutbrain_comparison.csv', index=False)
print(); print(t.to_string(index=False))
