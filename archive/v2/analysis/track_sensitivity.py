"""Track 1/2 민감도: 상한처리, MAD, winsorizing, dNB 제외. 입력: 집계구 단위 5개 지표 CSV"""
import pandas as pd, numpy as np
from scipy.stats import spearmanr, mstats
oa=pd.read_csv("oa.csv")
z=lambda s:(s-s.mean())/s.std(ddof=1)
zmad=lambda s:(s-s.median())/(1.4826*(s-s.median()).abs().median())
wins=lambda s:pd.Series(mstats.winsorize(s.values,limits=[.05,.05]),index=s.index)
T={}
T['T1']=z(oa.Abs_mean)+z(oa.Elderly_Ratio)
T['T1_cap']=z(oa.Abs_mean)+z(oa.Elderly_Ratio.clip(upper=100))
T['T1_mad']=zmad(oa.Abs_mean)+zmad(oa.Elderly_Ratio)
T['T1_win']=z(wins(oa.Abs_mean))+z(wins(oa.Elderly_Ratio))
T['T2']=z(oa.dNB_mean)+z(oa.Old_housing_Ratio)+z(oa.dRL_mean)
T['T2_nodNB']=z(oa.Old_housing_Ratio)+z(oa.dRL_mean)
T['T2_mad']=zmad(oa.dNB_mean)+zmad(oa.Old_housing_Ratio)+zmad(oa.dRL_mean)
T['T2_win']=z(wins(oa.dNB_mean))+z(wins(oa.Old_housing_Ratio))+z(wins(oa.dRL_mean))
top=int(round(len(oa)*.1))
for base,alts in [('T1',['T1_cap','T1_mad','T1_win']),('T2',['T2_nodNB','T2_mad','T2_win'])]:
    b=set(T[base].nlargest(top).index)
    for a in alts:
        ov=len(b&set(T[a].nlargest(top).index)); rho=spearmanr(T[base],T[a])[0]
        print(f"{base} vs {a:10s} rho={rho:.3f} top10% overlap={ov}/{top} ({ov/top*100:.1f}%)")
