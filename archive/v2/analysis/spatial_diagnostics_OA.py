"""
집계구(N=691) 절대온도 모형: 잔차 Moran's I, LM 검정, 공간오차/공간시차모형
실행: uv run --with pandas,openpyxl,statsmodels,libpysal,esda,spreg,scipy python spatial_diagnostics_OA.py
입력: 저장소의 Bukgu_100m_Master_Data(repro).xlsx (격자 시트: 집계구 중심점 산출)
      OA 단위 변수 파일(oa.csv): TOT_OA_CD, Abs_mean, dNB_mean, Elderly_Ratio, Old_housing_Ratio, SAVI, DEM
※ 최종본은 SGIS 집계구 폴리곤(Queen 인접)으로 가중행렬을 만들어 재실행할 것 (libpysal.weights.Queen.from_dataframe)
"""
import pandas as pd, numpy as np, statsmodels.api as sm, warnings
from libpysal.weights import KNN
from esda.moran import Moran
import spreg
warnings.filterwarnings('ignore')

g = pd.read_excel("Bukgu_100m_Master_Data(repro).xlsx", sheet_name="Bukgu_100m_Master_Data")
g['cx']=(g.left+g.right)/2; g['cy']=(g.top+g.bottom)/2
g['TOT_OA_CD']=g['TOT_OA_CD'].astype('int64').astype(str)
cent = g.groupby('TOT_OA_CD')[['cx','cy']].mean().reset_index()

oa = pd.read_csv("oa.csv"); oa['TOT_OA_CD']=oa['TOT_OA_CD'].astype('int64').astype(str)
oa = oa.merge(cent, on='TOT_OA_CD', how='inner')
names=['dNB_mean','Elderly_Ratio','Old_housing_Ratio','SAVI','DEM']
X=oa[names].values; y=oa['Abs_mean'].values.reshape(-1,1)

w = KNN.from_array(oa[['cx','cy']].values, k=8); w.transform='r'
ols = spreg.OLS(y, X, w=w, spat_diag=True, moran=True, name_x=names, name_y='Abs_mean')
print(ols.summary)
sem = spreg.ML_Error(y, X, w=w, name_x=names, name_y='Abs_mean'); print(sem.summary)
slm = spreg.ML_Lag(y, X, w=w, name_x=names, name_y='Abs_mean');   print(slm.summary)
print("Moran I (OLS resid):", Moran(ols.u.flatten(), w, permutations=999).I)
print("Moran I (SEM resid):", Moran(sem.e_filtered.flatten(), w, permutations=999).I)
