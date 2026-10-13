"""
정본(Mean 합성) 기반 전면 재산출 스크립트 — 원고 수치의 재현용
입력(저장소 data/): 전체종합_구역통계-빈셀 제거.csv(N=11,809, 정본 격자),
  z_score 산출.xlsx(고령·노후 비율), git 이력의 Bukgu_100m_Master_Data.csv(격자→집계구 매핑, 커밋 e7da65f)
실행: uv run --with pandas,openpyxl,statsmodels,scipy,libpysal,esda,spreg python rebuild_all.py
산출: Table 3 신규 계수, Moran's I/SEM/SLM, Track 1·2 정본 점수, 3.5절 강건성 수치 일체
※ 격자→집계구 매핑 복원: git show e7da65f:Bukgu_100m_Master_Data.csv > grid_oa_map.csv
"""
import pandas as pd, numpy as np, statsmodels.api as sm, warnings
from scipy.stats import spearmanr, pearsonr, mstats
from libpysal.weights import KNN
from esda.moran import Moran
import spreg
warnings.filterwarnings('ignore')

g = pd.read_csv('grid_oa_map.csv', encoding='utf-8-sig').dropna(subset=['TOT_OA_CD'])
g['TOT_OA_CD'] = g['TOT_OA_CD'].astype('int64').astype(str)
c = pd.read_csv('전체종합_구역통계-빈셀 제거.csv', encoding='utf-8-sig')
m = g[['id','TOT_OA_CD','ADM_CD','Abs_mean']].merge(
    c[['id','dLST_mean','dNDBI_mean','SAVI25_mea','DEM_mean','left','top','right','bottom']], on='id')
zx = pd.read_excel('z_score 산출.xlsx', sheet_name='z_score', header=None, skiprows=3)
zx.columns = ['TOT_OA_CD','Abs_pv','Eld','dNB_pv','Old','dRL_pv','z1','z2','z3','z4','z5','T1_ms','T2_ms']
zx = zx.dropna(subset=['TOT_OA_CD'])
zx['TOT_OA_CD'] = zx.TOT_OA_CD.astype(str).str.replace('.0','',regex=False)
zx = zx[zx.TOT_OA_CD.str.len()==14]
m = m[m.TOT_OA_CD.isin(set(zx.TOT_OA_CD))]
m['cx']=(m.left+m.right)/2; m['cy']=(m.top+m.bottom)/2
oa = m.groupby('TOT_OA_CD').agg(Abs=('Abs_mean','mean'), dRL=('dLST_mean','mean'), dNB=('dNDBI_mean','mean'),
      SAVI=('SAVI25_mea','mean'), DEM=('DEM_mean','mean'), cx=('cx','mean'), cy=('cy','mean')).reset_index()
oa = oa.merge(zx[['TOT_OA_CD','Eld','Old','Abs_pv']], on='TOT_OA_CD', how='right')
# 신규 격자망 미포함 3개 집계구는 저장소 z_score xlsx의 대표격자 시트 값으로 보정할 것(본문 D-2 참조)
oa = oa.dropna(subset=['Abs','cx'])

X = oa[['dNB','Eld','Old','SAVI','DEM']]; y = oa.Abs
ols = sm.OLS(y, sm.add_constant(X)).fit(); print(ols.summary())
w = KNN.from_array(oa[['cx','cy']].values, k=8); w.transform='r'
print('Moran I (OLS resid):', Moran(ols.resid.values, w, permutations=999).I)
sem = spreg.ML_Error(y.values.reshape(-1,1), X.values, w=w, name_x=list(X.columns)); print(sem.summary)
slm = spreg.ML_Lag(y.values.reshape(-1,1), X.values, w=w, name_x=list(X.columns)); print(slm.summary)

z = lambda s:(s-s.mean())/s.std(ddof=1)
zmad = lambda s:(s-s.median())/(1.4826*(s-s.median()).abs().median())
wins = lambda s: pd.Series(mstats.winsorize(s.values, limits=[.05,.05]), index=s.index)
T1 = z(oa.Abs_pv)+z(oa.Eld); T2 = z(oa.dNB)+z(oa.Old)+z(oa.dRL)
print('r(T1,T2)=', pearsonr(T1,T2)[0], '| r(dNB,dRL)=', pearsonr(oa.dNB,oa.dRL)[0],
      '| 무조건부 r(Abs,Eld)=', pearsonr(oa.Abs_pv,oa.Eld)[0])
top = round(len(oa)*.1); b = set(T2.nlargest(top).index)
for lab, alt in [('MAD', zmad(oa.dNB)+zmad(oa.Old)+zmad(oa.dRL)),
                 ('winsor', z(wins(oa.dNB))+z(wins(oa.Old))+z(wins(oa.dRL))),
                 ('no-dNB', z(oa.Old)+z(oa.dRL)),
                 ('T1cap(vsT1)', None)]:
    if alt is None:
        alt = z(oa.Abs_pv)+z(oa.Eld.clip(upper=100)); base = T1
    else:
        base = T2
    ov = len(set(base.nlargest(top).index) & set(alt.nlargest(top).index))
    print(f'{lab}: rho={spearmanr(base,alt)[0]:.3f}, top10% overlap={ov}/{top}')
