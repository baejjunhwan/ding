"""정본(v2) Track 1/2 점수 지도 생성. 출력: figs/Track12_v2.png

집계구 경계 폴리곤이 저장소에 포함되어 있지 않으므로, 마스터 데이터의
집계구 중심좌표(cx, cy; EPSG:5179)를 점으로 표시한다.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

SRC = "data/Bukgu_TOT_Master_Data_v2_zonal.csv"
OUT = "figs/Track12_v2.png"

SURFACE, INK, INK2, MUTED, HAIRLINE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
ORANGE = ["#fbe3d6", "#f7c8ad", "#f2ab83", "#eb6834", "#c9501f", "#9e3b13", "#75290c"]
BLUE   = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

for fam in ("Malgun Gothic", "NanumGothic", "AppleGothic"):
    if any(f.name == fam for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break
plt.rcParams["axes.unicode_minus"] = False

d = pd.read_csv(SRC, encoding="utf-8-sig")
n_top = int(round(len(d) * 0.10))
t1 = set(d.nlargest(n_top, "Track1_Score").index)
t2 = set(d.nlargest(n_top, "Track2_Score").index)

pad = 600
xlim = (d.cx.min() - pad, d.cx.max() + pad)
ylim = (d.cy.min() - pad, d.cy.max() + pad)

fig, axes = plt.subplots(1, 2, figsize=(15.4, 7.4), dpi=180, facecolor=SURFACE)
fig.subplots_adjust(left=.025, right=.975, top=.855, bottom=.115, wspace=.09)

panels = [
    ("Track1_Score", t1, ORANGE, "Track 1  단기 인명 구호형",
     "Z(절대 표면온도) + Z(고령 인구 비율)"),
    ("Track2_Score", t2, BLUE, "Track 2  중장기 공간 개조형",
     "Z(ΔNDBI) + Z(노후 주택 비율) + Z(ΔRLST)"),
]

for ax, (col, top_idx, ramp, title, sub) in zip(axes, panels):
    cmap = LinearSegmentedColormap.from_list(col, ramp)
    ax.set_facecolor(SURFACE)
    order = d[col].argsort()          # 높은 점수를 위로
    sub_d = d.iloc[order]
    is_top = sub_d.index.isin(top_idx)

    # 상·하위 2% 극단값이 색 범위를 잠식하지 않도록 로버스트 클리핑
    vmin, vmax = d[col].quantile([.02, .98])
    norm = plt.Normalize(vmin, vmax)
    ax.scatter(sub_d.cx, sub_d.cy, c=sub_d[col], cmap=cmap, norm=norm, s=66,
               linewidths=.6, edgecolors=SURFACE, zorder=2)
    ax.scatter(sub_d.cx[is_top], sub_d.cy[is_top], s=150, facecolors="none",
               edgecolors=SURFACE, linewidths=3.0, zorder=3)
    ax.scatter(sub_d.cx[is_top], sub_d.cy[is_top], s=150, facecolors="none",
               edgecolors=INK, linewidths=1.4, zorder=4)

    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal")
    for s in ax.spines.values():
        s.set_color(HAIRLINE); s.set_linewidth(.8)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, color=INK, fontsize=15, fontweight="bold", pad=16, loc="left")
    ax.text(0, 1.012, sub, transform=ax.transAxes, color=INK2, fontsize=10.5, va="bottom")

    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                      orientation="horizontal", fraction=.038, pad=.028,
                      aspect=34, extend="both")
    cb.set_label(f"{col} (Z-score 합산, 색 범위 = 2~98 백분위)",
                 color=INK2, fontsize=10)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=MUTED, labelsize=9, length=0)

    # 축척 막대 2 km
    x0, y0 = xlim[0] + 700, ylim[0] + 620
    ax.plot([x0, x0 + 2000], [y0, y0], color=INK, lw=2.6, solid_capstyle="butt", zorder=5)
    ax.text(x0 + 1000, y0 + 200, "2 km", color=INK2, fontsize=9.5, ha="center")
    # 방위표
    nx, ny = xlim[1] - 900, ylim[1] - 1750
    ax.annotate("", xy=(nx, ny + 1000), xytext=(nx, ny),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.8), zorder=5)
    ax.text(nx, ny + 1120, "N", color=INK, fontsize=10, ha="center", fontweight="bold")

legend = [
    Line2D([], [], marker="o", color="none", markerfacecolor="none",
           markeredgecolor=INK, markeredgewidth=1.4, markersize=13,
           label=f"상위 10% 우선 타겟 집계구 (n={n_top})"),
    Line2D([], [], marker="o", color="none", markerfacecolor="#c9c8c2",
           markeredgecolor=SURFACE, markersize=8, label=f"집계구 중심점 (N={len(d)})"),
]
fig.legend(handles=legend, loc="upper right", bbox_to_anchor=(.975, .988),
           frameon=False, ncol=2, fontsize=10.5, labelcolor=INK2,
           handletextpad=.6, columnspacing=1.6)
fig.text(.025, .966, "광주광역시 북구 집계구 단위 기후 취약성 투트랙 타겟팅 (정본 v2)",
         color=INK, fontsize=17, fontweight="bold", va="center")
fig.text(.025, .026,
         f"자료: Bukgu_TOT_Master_Data_v2_zonal.csv (N={len(d)}, 구역평균 기준) · "
         f"좌표계 EPSG:5179 · Track 1·2 상위 10% 중첩 {len(t1 & t2)}/{n_top} "
         f"({len(t1 & t2)/n_top*100:.1f}%) · r(T1,T2)=.388 · "
         "집계구 경계 폴리곤이 아닌 중심점 표시",
         color=MUTED, fontsize=9.5, va="center")

fig.savefig(OUT, facecolor=SURFACE)
print(f"저장: {OUT}  (상위 10% n={n_top}, 중첩 {len(t1 & t2)})")
