"""Step 8 - 재심 전 점검 수치 (수정본 2.4·2.5·3.3절).

1) LST와 고령인구 비율의 단순상관(통제 이전), 분석 대상의 인구가중 고령인구 비율
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
