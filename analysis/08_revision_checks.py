"""Step 8 - 재심 전 점검 수치 (수정본 2.4·2.5·3.3절).

1) LST와 고령인구 비율의 단순상관(통제 이전), 분석 대상의 인구가중 고령인구 비율
(4~7은 각 절 머리 주석 참조) 8) 고령인구 비공개 셀 2.5명 대체 SEM  9) 격자 SEM의 집계구 군집 강건 표준오차
2) LST 고정 공백으로 평가하지 못한 거주 집계구 67개와 분석 대상 832개의 물리 특성 비교
   (고도, NDBI2025, SAVI2025) 및 832개로 적합한 LST 회귀식으로 추정한 67개의 참고 LST
3) 공간가중행렬 민감도: 집계구 SEM을 Queen 대신 k-최근접(k = 4, 6, 8, 행 표준화)으로 재추정
   비대칭 가중행렬이므로 로그 행렬식은 고윳값 대신 slogdet(I - λW)로 직접 계산한다.
Output: results/revision_checks.json
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.spatial import cKDTree
from spatial_models import read_gal, ml_error

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'data'
d = pd.read_csv(D / 'Bukgu_OA_Master_v3_base.csv', dtype={'TOT_OA_CD': str}).set_index('TOT_OA_CD')
z = pd.read_csv(D / 'Bukgu_OA_zonal_areaweighted.csv', dtype={'TOT_OA_CD': str}).set_index('TOT_OA_CD')
out = {'n': len(d)}

# ---- 1) 단순상관, 인구가중 비율 -------------------------------------------------------------
r, p = stats.pearsonr(d.Abs_mean, d.Elderly_Ratio)
out['r_LST_elderly'] = dict(r=r, p=p)
out['elderly_ratio'] = dict(pop_weighted=100 * d.eld65.sum() / d.to_in_001.sum(), oa_mean=d.Elderly_Ratio.mean(),
                            eld65=d.eld65.sum(), pop=d.to_in_001.sum())

# ---- 2) 평가 미실시 67개 ---------------------------------------------------------------------
t = pd.read_csv(D / 'sgis_2024_total_population.csv', header=None, names=['yr', 'oa', 'item', 'v'], dtype={'oa': str})
pop = pd.to_numeric(t[t.item == 'to_in_001'].set_index('oa').v, errors='coerce')
z['pop'] = pop.reindex(z.index)
miss = z[(z['pop'] > 0) & (z.LST25_abs.isna() | z.dRLST.isna())].copy()
ana = z.loc[d.index].copy()
assert len(miss) == 67
cmp_ = {}
for v in ['DEM', 'NDBI25', 'SAVI25_max']:
    a, b = miss[v], ana[v]
    cmp_[v] = dict(unassessed=a.mean(), analysed=b.mean(), welch_p=stats.ttest_ind(a, b, equal_var=False).pvalue)
# 832개로 적합한 LST2025 ~ NDBI2025 + SAVI2025 + 고도, 67개에 적용(참고값)
X = lambda f: np.column_stack([np.ones(len(f)), f.NDBI25, f.SAVI25_max, f.DEM])
b = np.linalg.lstsq(X(ana), ana.LST25_abs.values, rcond=None)[0]
fit = X(ana) @ b
r2 = 1 - ((ana.LST25_abs - fit) ** 2).sum() / ((ana.LST25_abs - ana.LST25_abs.mean()) ** 2).sum()
pred = X(miss) @ b
cmp_['LST2025_predicted'] = dict(unassessed=pred.mean(), analysed_observed=ana.LST25_abs.mean(),
                                 share_above_analysed_median=float((pred > ana.LST25_abs.median()).mean()), r2=r2)
out['unassessed_67'] = dict(n=len(miss), pop=miss['pop'].sum(), compare=cmp_)

# ---- 3) 공간가중행렬 민감도 -----------------------------------------------------------------
names = ['Intercept', 'dNB_mean', 'Elderly_Ratio', 'Old_housing_Ratio', 'SAVI2025', 'DEM']
Xo = np.column_stack([np.ones(len(d)), d.dNB_mean, d.Elderly_Ratio, d.Old_housing_Ratio, d.SAVI, d.DEM])
y = d.Abs_mean.values
n, k = Xo.shape


def ml_error_any(y, X, W):
    """ML 공간오차모형(비대칭 W 허용). 계수 SE는 GLS 공분산, λ는 프로파일 우도 최대화."""
    I = np.eye(len(y))

    def fit(l):
        B = I - l * W
        ys, Xs = B @ y, B @ X
        bb = np.linalg.lstsq(Xs, ys, rcond=None)[0]
        e = ys - Xs @ bb
        return bb, e, Xs

    def nll(l):
        _, e, _ = fit(l)
        s2 = e @ e / len(y)
        return len(y) / 2 * np.log(s2) - np.linalg.slogdet(I - l * W)[1]
    l = optimize.minimize_scalar(nll, bounds=(-0.99, 0.99), method='bounded', options={'xatol': 1e-8}).x
    bb, e, Xs = fit(l)
    s2 = e @ e / len(y)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(Xs.T @ Xs)))
    return dict(coef=bb, se=se, p=2 * stats.norm.sf(np.abs(bb / se)), lam=l,
                aic=2 * nll(l) + len(y) * (np.log(2 * np.pi) + 1) + 2 * (X.shape[1] + 1))


Wq, _, _ = read_gal(D / 'queen_oa_v3.gal', d.index.tolist())
res = {'queen_ml_error': ml_error(y, Xo, Wq), 'queen_check': ml_error_any(y, Xo, Wq)}
xy = d[['cx', 'cy']].values
tree = cKDTree(xy)
for kk in (4, 6, 8):
    _, idx = tree.query(xy, k=kk + 1)
    W = np.zeros((n, n))
    for i, row in enumerate(idx):
        W[i, [j for j in row if j != i][:kk]] = 1 / kk
    res[f'knn{kk}'] = ml_error_any(y, Xo, W)
out['W_sensitivity'] = {}
for key, m in res.items():
    c = m['coef']
    out['W_sensitivity'][key] = {nm: dict(B=float(c[i]), SE=float(m['se'][i]), p=float(m['p'][i]))
                                 for i, nm in enumerate(names)}
    out['W_sensitivity'][key]['lambda'] = float(m['lam'])

# ---- 4) SAVI 합성 기간·방식: 5~10월 최댓값(주모형) 대신 5~9월 평균(LST와 같은 기간) -------------
out['savi_may_sep_mean'] = {'r_with_max_composite': float(d[['SAVI', 'SAVI25_mean']].corr().iloc[0, 1])}
Xm = np.column_stack([np.ones(len(d)), d.dNB_mean, d.Elderly_Ratio, d.Old_housing_Ratio, d.SAVI25_mean, d.DEM])
m = ml_error(y, Xm, Wq)
out['savi_may_sep_mean']['sem'] = {nm: dict(B=float(m['coef'][i]), SE=float(m['se'][i]), p=float(m['p'][i]))
                                   for i, nm in enumerate(names)}

# ---- 5) 시가화 수준 통제: NDBI2020(기저) 또는 NDBI2025(현재)를 추가한 집계구 SEM ------------------
# NDBI2025 = NDBI2020 + ΔNDBI 이므로 두 모형은 같은 모형이다(고령인구 계수 동일). 다만 ΔNDBI 계수의 뜻이 달라서,
# NDBI2020 통제 시에는 "같은 기저 수준에서 더 개발된 곳", NDBI2025 통제 시에는 "같은 현재 수준에서 기저가 낮았던 곳"을 비교한다.
out['sem_built_up_level'] = {}
for lv in ('NDBI20', 'NDBI25'):
    Xl = np.column_stack([Xo, d[lv]])
    m = ml_error(y, Xl, Wq)
    out['sem_built_up_level'][lv] = {nm: dict(B=float(m['coef'][i]), SE=float(m['se'][i]), p=float(m['p'][i]))
                                     for i, nm in enumerate(names + [lv])}

# ---- 6) 격자 모형 OLS 잔차의 LM 검정(희소 행렬 계산; 수정본 2.5·3.2절) ------------------------------
from scipy import sparse
from spatial_models import queen_grid, ols as ols_


def lm_sparse(y, X, W):
    """spatial_models.lm_tests와 같은 식을 희소 행렬로 계산한다(집계구 모형에서 값이 일치함을 확인)."""
    W = sparse.csr_matrix(W)
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b; s2 = e @ e / len(y)
    XtXi = np.linalg.inv(X.T @ X); Mv = lambda v: v - X @ (XtXi @ (X.T @ v))
    T = W.multiply(W).sum() + W.multiply(W.T).sum()
    WXb = W @ (X @ b); Dd = (WXb @ Mv(WXb)) / s2 + T
    eWe, eWy = e @ (W @ e) / s2, e @ (W @ y) / s2
    r = {'LM-error': eWe ** 2 / T, 'LM-lag': eWy ** 2 / Dd,
         'Robust LM-error': (eWe - T / Dd * eWy) ** 2 / (T - T ** 2 / Dd), 'Robust LM-lag': (eWy - eWe) ** 2 / (Dd - T)}
    return {k: dict(stat=float(v), p=float(stats.chi2.sf(v, 1))) for k, v in r.items()}


g = pd.read_csv(D / 'Bukgu_Grid_Master_v3.csv', dtype={'TOT_OA_CD': str})
Xg = np.column_stack([np.ones(len(g)), g.RLST2020, g.dSAVI, g.SAVI2020, g.dNDBI, g.DEM])
out['grid_lm_tests'] = lm_sparse(g.dRLST.values, Xg, queen_grid(g.col_index.values, g.row_index.values))
out['oa_lm_tests_check'] = lm_sparse(y, Xo, Wq)

# ---- 7) 주택 비공개 셀(1~4호)을 2.5 대신 0으로 대체했을 때의 집계구 SEM(수정본 2.4절) ----------------------
h = pd.read_csv(D / 'sgis_2024_housing_by_year.csv', header=None, names=['yr', 'oa', 'code', 'cnt'], dtype=str)
h['n'] = pd.to_numeric(h.cnt, errors='coerce').fillna(0)
old0 = h[h.code.isin(['ho_yr_001', 'ho_yr_002', 'ho_yr_003'])].groupby('oa').n.sum()
tot0 = h.groupby('oa').n.sum()
ratio0 = (100 * old0.reindex(d.index).fillna(0) / tot0.reindex(d.index)).fillna(0)
X0 = np.column_stack([np.ones(len(d)), d.dNB_mean, d.Elderly_Ratio, ratio0, d.SAVI, d.DEM])
m0 = ml_error(y, X0, Wq)
out['housing_na_as_zero_sem'] = {nm: dict(B=float(m0['coef'][i]), p=float(m0['p'][i])) for i, nm in enumerate(names)}

# ---- 8) 고령인구 연령대별 비공개 셀(0으로 표시)을 2.5명으로 대체한 집계구 SEM(수정본 2.4절) ----------------
# SGIS 성·연령별 인구표에는 1~4명이 나타나지 않고 0으로 표시되므로(비공개), 65세 이상 연령대(in_age_014~021)의 0을 2.5로 바꾼다.
s1 = pd.read_excel(D / '2024 고령인구비율.xlsx', sheet_name=0, header=3, dtype={'행 레이블': str})
s1 = s1[s1['행 레이블'].str.match(r'^\d{14}$', na=False)].set_index('행 레이블').reindex(d.index)
age = s1[[f'in_age_{i:03d}' for i in range(14, 22)]]
eld25 = 100 * age.replace(0, 2.5).fillna(0).sum(axis=1) / d.to_in_001
X25 = np.column_stack([np.ones(len(d)), d.dNB_mean, eld25, d.Old_housing_Ratio, d.SAVI, d.DEM])
m25 = ml_error(y, X25, Wq)
out['elderly_na_as_2_5_sem'] = {'r_with_main': float(np.corrcoef(eld25, d.Elderly_Ratio)[0, 1]),
                                **{nm: dict(B=float(m25['coef'][i]), p=float(m25['p'][i])) for i, nm in enumerate(names)}}

# ---- 9) 격자 SEM(GM)에 집계구 군집 강건 표준오차 적용(수정본 Table 5 주) -------------------------------------
# 06_ndbi_scale_check.py의 OLS와 같은 CR1 보정(G/(G-1)·(n-1)/(n-k), t(G-1))을 공간 필터링한 회귀에 적용한다.
from spatial_models import _optim
Wg = queen_grid(g.col_index.values, g.row_index.values); yg = g.dRLST.values; ng = len(yg)
WtW = (Wg.T @ Wg).tocsr(); A1 = WtW - sparse.diags(WtW.diagonal())
u = yg - Xg @ np.linalg.lstsq(Xg, yg, rcond=None)[0]; A1u, wu = A1 @ u, Wg @ u
lam = _optim(np.array([[2 * (wu @ A1u), -(wu @ (A1 @ wu))], [wu @ ((Wg + Wg.T) @ u), -(wu @ (Wg @ wu))]]) / ng,
             np.array([u @ A1u, u @ wu]) / ng)
xs, ys = Xg - lam * (Wg @ Xg), yg - lam * (Wg @ yg)
XtXi = np.linalg.inv(xs.T @ xs); bg = XtXi @ xs.T @ ys; ef = ys - xs @ bg
cl = g.TOT_OA_CD.fillna('NONE').replace('', 'NONE').values; Gc = len(np.unique(cl)); kg = Xg.shape[1]
meat = np.zeros((kg, kg))
for c in np.unique(cl):
    sc = xs[cl == c].T @ ef[cl == c]; meat += np.outer(sc, sc)
se_cl = np.sqrt(np.diag(XtXi @ meat @ XtXi * Gc / (Gc - 1) * (ng - 1) / (ng - kg)))
out['grid_sem_cluster_se'] = {'lambda': float(lam), 'clusters': int(Gc),
                              **{nm: dict(B=float(bg[i]), SE_cluster=float(se_cl[i]),
                                          p=float(2 * stats.t.sf(abs(bg[i] / se_cl[i]), Gc - 1)))
                                 for i, nm in enumerate(['Intercept', 'RLST2020', 'dSAVI', 'SAVI2020', 'dNDBI', 'DEM'])}}

(ROOT / 'results').mkdir(exist_ok=True)
(ROOT / 'results' / 'revision_checks.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))

print(f"r(LST2025, 고령인구 비율) = {r:.3f} (p = {p:.2g});  인구가중 고령인구 비율 = "
      f"{out['elderly_ratio']['pop_weighted']:.1f}% (집계구 평균 {out['elderly_ratio']['oa_mean']:.1f}%)")
print(f"평가 미실시 {len(miss)}개 (거주 {miss['pop'].sum():,.0f}명) vs 분석 대상 {len(d)}개")
for v, c in cmp_.items():
    print('  ', v, {kk: round(vv, 4) for kk, vv in c.items()})
print('공간가중행렬 민감도 (SEM 고령인구 비율 / ΔNDBI 계수)')
for key, m in out['W_sensitivity'].items():
    e, g = m['Elderly_Ratio'], m['dNB_mean']
    print(f"  {key:15s} λ = {m['lambda']:.3f}  elderly B = {e['B']:.4f} (SE {e['SE']:.4f}, p = {e['p']:.2g})  "
          f"ΔNDBI B = {g['B']:.3f} (p = {g['p']:.2g})")
sv = out['savi_may_sep_mean']
print(f"SAVI 5~9월 평균 합성: 최댓값 합성과 r = {sv['r_with_max_composite']:.3f};  SEM 고령인구 B = "
      f"{sv['sem']['Elderly_Ratio']['B']:.4f} (p = {sv['sem']['Elderly_Ratio']['p']:.2g}), ΔNDBI B = "
      f"{sv['sem']['dNB_mean']['B']:.3f} (p = {sv['sem']['dNB_mean']['p']:.2g}), SAVI B = {sv['sem']['SAVI2025']['B']:.3f}")
for lv, m in out['sem_built_up_level'].items():
    print(f"SEM + {lv}: ΔNDBI B = {m['dNB_mean']['B']:.3f} (p = {m['dNB_mean']['p']:.2g}), 고령인구 B = "
          f"{m['Elderly_Ratio']['B']:.4f} (p = {m['Elderly_Ratio']['p']:.2g}), {lv} B = {m[lv]['B']:.3f}")
print('격자 LM 검정:', {k: round(v['stat'], 1) for k, v in out['grid_lm_tests'].items()})
print('집계구 LM 검정(희소 계산 확인):', {k: round(v['stat'], 2) for k, v in out['oa_lm_tests_check'].items()})
z0 = out['housing_na_as_zero_sem']
print(f"비공개 셀 0 대체 SEM: 고령인구 B = {z0['Elderly_Ratio']['B']:.4f} (p = {z0['Elderly_Ratio']['p']:.3f}), "
      f"노후주택 B = {z0['Old_housing_Ratio']['B']:.4f} (p = {z0['Old_housing_Ratio']['p']:.3f})")
e25 = out['elderly_na_as_2_5_sem']
print(f"고령인구 비공개 셀 2.5 대체: r = {e25['r_with_main']:.3f}, SEM 고령인구 B = {e25['Elderly_Ratio']['B']:.4f} "
      f"(p = {e25['Elderly_Ratio']['p']:.2g})")
print('격자 SEM 군집 강건 SE(CR1):', {k: (round(v['B'], 3), round(v['SE_cluster'], 3), f"{v['p']:.2g}")
                                   for k, v in out['grid_sem_cluster_se'].items() if isinstance(v, dict)})
