"""Step 6 - ΔNDBI 부호 차이 점검 (수정본 3.2절, 심사의견 2-1 대응).

격자 OLS에서 ΔNDBI 계수는 음(−), 공간오차모형에서는 양(+)이다. 이를 두 가지로 점검한다.
1) ΔNDBI 상위 10% 격자와 나머지 격자의 2020년 상태 비교
   - "개발이 2020년에 서늘하고 식생이 많던 외곽에 집중되었다"는 설명이 성립하는지 확인
2) ΔNDBI(와 ΔSAVI)를 주변 평균(k×k 창, 자기 자신 제외)과 국지 편차(자기 값 − 주변 평균)로
   나누어 같은 통제변수로 OLS 재추정 - 두 계수의 부호가 서로 다른 공간 스케일에서 오는지 확인
Output: results/ndbi_scale_check.json
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
g = pd.read_csv(ROOT / 'data' / 'Bukgu_Grid_Master_v3.csv', dtype={'TOT_OA_CD': str})
out = {'n': len(g)}

# 1) 상위 10% 비교
cut = g.dNDBI.quantile(0.9)
top = g.dNDBI >= cut
comp = {}
for v in ['RLST2020', 'SAVI2020', 'NDBI20', 'DEM', 'dRLST', 'dSAVI']:
    a, b = g.loc[top, v], g.loc[~top, v]
    comp[v] = dict(top=round(a.mean(), 4), rest=round(b.mean(), 4), diff=round(a.mean() - b.mean(), 4),
                   welch_p=float(stats.ttest_ind(a, b, equal_var=False).pvalue))
q = pd.qcut(g.NDBI20, 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
out['top10'] = dict(cutoff=round(cut, 4), n_top=int(top.sum()), compare=comp,
                    share_by_NDBI2020_quartile=q[top].value_counts(normalize=True).sort_index().round(3).to_dict())

# 2) 스케일 분해
pos = {(r, c): i for i, (r, c) in enumerate(zip(g.row_index, g.col_index))}


def neigh_mean(col, h):
    vals, res = g[col].values, np.full(len(g), np.nan)
    for i, (r, c) in enumerate(zip(g.row_index, g.col_index)):
        idx = [pos[(r + a, c + b)] for a in range(-h, h + 1) for b in range(-h, h + 1)
               if (a or b) and (r + a, c + b) in pos]
        if idx:
            res[i] = vals[idx].mean()
    return res


def ols(cols):
    d = g.dropna(subset=cols)
    X = np.column_stack([np.ones(len(d))] + [d[c] for c in cols])
    y = d.dRLST.values
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    n, k = X.shape
    se = np.sqrt(np.diag(e @ e / (n - k) * np.linalg.inv(X.T @ X)))
    p = 2 * stats.t.sf(np.abs(b / se), n - k)
    return {c: dict(B=round(float(b[i + 1]), 4), SE=round(float(se[i + 1]), 4), p=float(p[i + 1]))
            for i, c in enumerate(cols)}


ctrl = ['RLST2020', 'SAVI2020', 'DEM']
out['scale_decomposition'] = {}
for k in (3, 11):
    h = k // 2
    for v in ['dNDBI', 'dSAVI']:
        g[f'nb_{v}'] = neigh_mean(v, h)
        g[f'loc_{v}'] = g[v] - g[f'nb_{v}']
    out['scale_decomposition'][f'{k}x{k}_cells_{k * 100}m'] = {
        'no_controls': ols(['nb_dNDBI', 'loc_dNDBI']),
        'controls_dSAVI_whole': ols(ctrl + ['dSAVI', 'nb_dNDBI', 'loc_dNDBI']),
        'controls_dSAVI_decomposed': ols(ctrl + ['nb_dNDBI', 'loc_dNDBI', 'nb_dSAVI', 'loc_dSAVI']),
    }

(ROOT / 'results').mkdir(exist_ok=True)
(ROOT / 'results' / 'ndbi_scale_check.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))

print(f"N = {out['n']:,};  ΔNDBI 상위 10% 기준 {cut:.4f} (n = {int(top.sum())})")
for v, r in comp.items():
    print(f"  {v:9s} 상위 {r['top']:9.3f}  나머지 {r['rest']:9.3f}  차이 {r['diff']:8.3f}  p = {r['welch_p']:.2g}")
for win, models in out['scale_decomposition'].items():
    for m, res in models.items():
        nb, lc = res['nb_dNDBI'], res['loc_dNDBI']
        print(f"  [{win} | {m}] 주변 평균 B = {nb['B']:.3f} (p = {nb['p']:.2g}), 국지 편차 B = {lc['B']:.3f} (p = {lc['p']:.2g})")
