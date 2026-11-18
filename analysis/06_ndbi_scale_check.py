"""Step 6 - ΔNDBI 부호 차이 점검 (수정본 3.2절, 심사의견 2-1 대응).

격자 OLS에서 ΔNDBI 계수는 음(−0.948), 공간오차모형(SEM)에서는 양(+3.289)이다.
격자 OLS 잔차는 강한 공간자기상관(Moran's I = .816)을 보이므로 일반 OLS 표준오차는 과소 추정된다.
여기서는 집계구(707개)를 군집으로 한 강건 표준오차(CR1; 집계구가 배정되지 않은 격자는 별도 군집 1개)로
OLS의 ΔNDBI 계수를 다시 검정한다.

1) 주모형(N = 11,752): ΔRLST ~ RLST2020 + ΔSAVI + SAVI2020 + ΔNDBI + DEM
2) 읍면동 경계부 격자를 제외한 표본(N = 11,370)
3) 2020년 시가화 수준만 통제한 단순 모형: ΔRLST ~ ΔNDBI + NDBI2020
4) (탐색, 본문 미사용) ΔNDBI를 주변 평균(k×k 창)과 국지 편차로 나눈 분해 - 군집 표준오차에서는 유의하지 않아
   수정본에서는 근거로 쓰지 않았다(이전 판본의 Table 6).
5) SEM에 2020년 시가화 수준(NDBI2020)을 추가로 통제(GM, 02_grid_models.py와 같은 추정량)
SEM 주모형 결과는 02_grid_models.py(results/grid_results.json)를 그대로 인용한다.
Output: results/ndbi_scale_check.json
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats, sparse
from spatial_models import queen_grid, _optim

ROOT = Path(__file__).resolve().parents[1]
g = pd.read_csv(ROOT / 'data' / 'Bukgu_Grid_Master_v3.csv', dtype={'TOT_OA_CD': str})
g['cluster'] = g.TOT_OA_CD.fillna('NONE').replace('', 'NONE')


def ols_cluster(df, cols):
    """OLS 계수와 일반 SE, 집계구 군집 강건 SE(CR1: G/(G-1)·(n-1)/(n-k), t(G-1) 분포)."""
    df = df.dropna(subset=cols + ['dRLST'])
    X = np.column_stack([np.ones(len(df))] + [df[c].values for c in cols])
    y = df.dRLST.values
    n, k = X.shape
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    se_ols = np.sqrt(np.diag(e @ e / (n - k) * XtXi))
    cl = df.cluster.values
    G = len(np.unique(cl))
    meat = np.zeros((k, k))
    for c in np.unique(cl):
        m = cl == c
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    V = XtXi @ meat @ XtXi * G / (G - 1) * (n - 1) / (n - k)
    se_cl = np.sqrt(np.diag(V))
    res = {}
    for i, c in enumerate(cols):
        res[c] = dict(B=float(b[i + 1]), SE_ols=float(se_ols[i + 1]),
                      p_ols=float(2 * stats.t.sf(abs(b[i + 1] / se_ols[i + 1]), n - k)),
                      SE_cluster=float(se_cl[i + 1]),
                      p_cluster=float(2 * stats.t.sf(abs(b[i + 1] / se_cl[i + 1]), G - 1)))
    return dict(n=int(n), clusters=int(G), coef=res)


MAIN = ['RLST2020', 'dSAVI', 'SAVI2020', 'dNDBI', 'DEM']
out = {'main': ols_cluster(g, MAIN)}
strict = g[g.center_in_GEE_boundary.astype(str).str.lower() == 'true']
out['boundary_excluded'] = ols_cluster(strict, MAIN)
out['simple_NDBI2020'] = ols_cluster(g, ['dNDBI', 'NDBI20'])

# 4) 탐색: 주변 평균/국지 편차 분해
pos = {(r, c): i for i, (r, c) in enumerate(zip(g.row_index, g.col_index))}


def neigh_mean(col, h):
    vals, res = g[col].values, np.full(len(g), np.nan)
    for i, (r, c) in enumerate(zip(g.row_index, g.col_index)):
        idx = [pos[(r + a, c + b)] for a in range(-h, h + 1) for b in range(-h, h + 1)
               if (a or b) and (r + a, c + b) in pos]
        if idx:
            res[i] = vals[idx].mean()
    return res


out['exploratory_decomposition'] = {}
for k in (3, 11):
    g['nb_dNDBI'] = neigh_mean('dNDBI', k // 2)
    g['loc_dNDBI'] = g.dNDBI - g.nb_dNDBI
    out['exploratory_decomposition'][f'{k}x{k}'] = ols_cluster(g, ['RLST2020', 'SAVI2020', 'DEM', 'dSAVI', 'nb_dNDBI', 'loc_dNDBI'])

# 주거 격자(Track 2 대상)의 단순상관
t2 = pd.read_csv(ROOT / 'results' / 'Track2_grid.csv')
r, p = stats.pearsonr(t2.dNDBI, t2.dRLST)
out['track2_residential_r'] = dict(n=len(t2), r=r, p=p)
sem = json.load(open(ROOT / 'results' / 'grid_results.json'))
out['sem_dNDBI'] = {k: dict(B=sem[k]['sem_gm']['b'][4], SE=sem[k]['sem_gm']['se'][4], p=sem[k]['sem_gm']['p'][4])
                    for k in ('main', 'robust_gee_boundary')}



def gm_error_grid(y, X, W):
    """02_grid_models.py의 gm_error_grid와 같은 추정량(Arraiz et al. 2010 적률 조건, 이분산 강건 SE)."""
    n = len(y)
    WtW = (W.T @ W).tocsr()
    A1 = WtW - sparse.diags(WtW.diagonal())
    u = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    A1u, wu = A1 @ u, W @ u
    g_ = np.array([u @ A1u, u @ wu]) / n
    G = np.array([[2 * (wu @ A1u), -(wu @ (A1 @ wu))], [wu @ ((W + W.T) @ u), -(wu @ (W @ wu))]]) / n
    lam = _optim(G, g_)
    xs, ys = X - lam * (W @ X), y - lam * (W @ y)
    XtXi = np.linalg.inv(xs.T @ xs)
    b = XtXi @ xs.T @ ys
    ef = (y - X @ b) - lam * (W @ (y - X @ b))
    se = np.sqrt(np.diag(XtXi @ ((xs * (ef ** 2)[:, None]).T @ xs) @ XtXi))
    return b, se, 2 * stats.norm.sf(np.abs(b / se)), lam


cols5 = MAIN + ['NDBI20']
b5, se5, p5, lam5 = gm_error_grid(g.dRLST.values, np.column_stack([np.ones(len(g))] + [g[c] for c in cols5]),
                                  queen_grid(g.col_index.values, g.row_index.values))
out['sem_with_NDBI2020'] = {c: dict(B=float(b5[i + 1]), SE=float(se5[i + 1]), p=float(p5[i + 1])) for i, c in enumerate(cols5)}
out['sem_with_NDBI2020']['lambda'] = float(lam5)

(ROOT / 'results' / 'ndbi_scale_check.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))

for key in ('main', 'boundary_excluded', 'simple_NDBI2020'):
    c = out[key]['coef']['dNDBI']
    print(f"{key:18s} N = {out[key]['n']:,} (군집 {out[key]['clusters']})  ΔNDBI B = {c['B']:.3f}  "
          f"일반 SE {c['SE_ols']:.3f} (p = {c['p_ols']:.3f})  군집 SE {c['SE_cluster']:.3f} (p = {c['p_cluster']:.3f})")
for win, m in out['exploratory_decomposition'].items():
    a, b = m['coef']['nb_dNDBI'], m['coef']['loc_dNDBI']
    print(f"[탐색 {win}] 주변 평균 B = {a['B']:.3f} (군집 SE {a['SE_cluster']:.3f}, p = {a['p_cluster']:.3f}), "
          f"국지 편차 B = {b['B']:.3f} (군집 SE {b['SE_cluster']:.3f}, p = {b['p_cluster']:.3f})")
print(f"주거 격자 r(ΔNDBI, ΔRLST) = {r:.3f} (N = {len(t2):,}, p = {p:.2g})")
for k, v in out['sem_dNDBI'].items():
    print(f"SEM {k}: ΔNDBI B = {v['B']:.3f} (SE {v['SE']:.3f}, p = {v['p']:.2g})")
c = out['sem_with_NDBI2020']['dNDBI']
print(f"SEM + NDBI2020: ΔNDBI B = {c['B']:.3f} (SE {c['SE']:.3f}, p = {c['p']:.2g})")
