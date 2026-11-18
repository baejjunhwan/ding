"""Step 7 - 수정본 그림 (영문, 투고본 그림 양식과 같은 틀).

Fig. 1  연구 흐름도                                  -> figs/rev_Fig1_framework.png
Fig. 3  Track 1 (집계구) + 평가 미실시 67개 집계구     -> figs/rev_Fig3_Track1.jpg
Fig. 4  Track 2 (100 m 격자) + 재건축·신개발 격자 21칸 -> figs/rev_Fig4_Track2_grid.jpg

Fig. 4 는 track2_grid/00~01 실행 후 생성되는 work/t2grid/*.pkl 이 필요합니다.
"""
import sys, os, glob, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch, FancyBboxPatch
from matplotlib.collections import PatchCollection
from scipy.ndimage import map_coordinates, gaussian_filter
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tm5179

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
D = os.path.join(ROOT, 'data')
for f in glob.glob('/usr/share/fonts/opentype/noto/NotoSansCJK-*.ttc'):
    fm.fontManager.addfont(f)
if any('Noto Sans CJK' in f.name for f in fm.fontManager.ttflist):
    plt.rcParams['font.family'] = 'Noto Sans CJK KR'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'custom'; plt.rcParams['mathtext.it'] = 'DejaVu Sans:italic'
INK, INK2, MUTED, HAIR, MAPBG = '#111111', '#333333', '#7a7a76', '#d6d5cf', '#fafaf8'
ORANGE = ["#fbe3d6", "#f7c8ad", "#f2ab83", "#eb6834", "#c9501f", "#9e3b13", "#6e260b"]
BLUE = ["#d3e6fc", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0b2f5e"]
VEIL, SAT = 0.40, 0.55
W, H, DPI = 2525, 2329, 250
os.makedirs(os.path.join(ROOT, 'figs'), exist_ok=True)

oa = pd.read_csv(os.path.join(D, 'Bukgu_OA_Master_v3.csv'), dtype={'TOT_OA_CD': str})
pad = 700
xlim = (oa.cx.min() - pad, oa.cx.max() + pad); ylim = (oa.cy.min() - pad, oa.cy.max() + pad)

# 평가 미실시(유효 LST 없음) 거주 집계구 67개: 03_build_oa_master.py 와 같은 기준
z = pd.read_csv(os.path.join(D, 'Bukgu_OA_zonal_areaweighted.csv'), dtype={'TOT_OA_CD': str}).set_index('TOT_OA_CD')
t = pd.read_csv(os.path.join(D, 'sgis_2024_total_population.csv'), header=None, names=['yr', 'oa', 'item', 'v'], dtype={'oa': str})
pop = pd.to_numeric(t[t.item == 'to_in_001'].set_index('oa').v, errors='coerce')
z['pop'] = pop.reindex(z.index)
unassessed = z[(z['pop'] > 0) & (z.LST25_abs.isna() | z.dRLST.isna())]
assert len(unassessed) == 67, len(unassessed)


def basemap(res=10.0):
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(os.path.join(D, 'basemap', 'Sentinel2_TrueColor_2025_Bukgu.tif'))
    src = np.asarray(im.convert('RGB')).astype(np.float32)
    sx, sy = im.tag_v2[33550][0], im.tag_v2[33550][1]
    lon0, lat0 = im.tag_v2[33922][3], im.tag_v2[33922][4]
    valid = src.sum(2) > 0
    for b in range(3):
        lo, hi = np.percentile(src[..., b][valid], [2, 98])
        src[..., b] = np.clip((src[..., b] - lo) / (hi - lo), 0, 1)
    src = src ** 0.95
    gx = np.arange(xlim[0] + res / 2, xlim[1], res); gy = np.arange(ylim[1] - res / 2, ylim[0], -res)
    LON, LAT = tm5179.inverse(*np.meshgrid(gx, gy))
    col = (LON - lon0) / sx - 0.5; row = (lat0 - LAT) / sy - 0.5
    rgb = np.stack([map_coordinates(src[..., b], [row, col], order=1, cval=0) for b in range(3)], -1)
    alpha = map_coordinates(valid.astype(np.float32), [row, col], order=1, cval=0)
    grey = (rgb @ np.array([0.299, 0.587, 0.114]))[..., None]
    rgb = (1 - VEIL) * (grey + SAT * (rgb - grey)) + VEIL
    rgba = np.dstack([np.clip(rgb, 0, 1), (alpha > 0.5).astype(np.float32)])
    return rgba, (gx[0] - res / 2, gx[-1] + res / 2, gy[-1] - res / 2, gy[0] + res / 2), gx, gy, gaussian_filter(alpha, 1.0)


def map_frame(title, bm):
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor='white')
    fig.add_artist(Rectangle((0.004, 0.004), 0.992, 0.992, transform=fig.transFigure, fill=False, lw=2.2, ec=INK))
    fig.text(0.06, 0.935, title, fontsize=17, color=INK, va='center')
    ax = fig.add_axes([0.055, 0.17, 0.89, 0.72]); ax.set_facecolor(MAPBG)
    rgba, ext, gx, gy, alpha_s = bm
    ax.imshow(rgba, extent=ext, origin='upper', interpolation='bilinear', zorder=0)
    ax.contour(gx, gy, alpha_s, levels=[0.5], colors=['#5c5c58'], linewidths=0.9, zorder=1)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal', adjustable='box')
    for s in ax.spines.values():
        s.set_color(HAIR); s.set_linewidth(1.0)
    ax.set_xticks([]); ax.set_yticks([])
    x0, y0 = xlim[0] + 800, ylim[0] + 700
    ax.plot([x0, x0 + 2000], [y0, y0], color=INK, lw=3.2, solid_capstyle='butt', zorder=5)
    ax.text(x0 + 1000, y0 + 220, '2 km', color=INK2, fontsize=10.5, ha='center', va='bottom')
    nx, ny = xlim[1] - 650, ylim[1] - 2100
    ax.annotate('', xy=(nx, ny + 1250), xytext=(nx, ny),
                arrowprops=dict(arrowstyle='-|>,head_width=0.35,head_length=0.7', color=INK, lw=2.0), zorder=5)
    ax.text(nx, ny + 1450, 'N', color=INK, fontsize=12, ha='center', va='bottom', fontweight='bold')
    return fig, ax


def finish(fig, ax, norm, cmap, legend, credit, path):
    lg = ax.legend(handles=legend, loc='upper right', bbox_to_anchor=(0.93, 0.985), frameon=True, fontsize=10,
                   labelcolor=INK2, handletextpad=0.5, borderaxespad=0.4, fancybox=False, framealpha=0.88,
                   edgecolor='none', facecolor='white')
    lg.set_zorder(6)
    ax.text(0.99, 0.012, credit, transform=ax.transAxes, ha='right', va='bottom', fontsize=7.5, color=INK2, zorder=6,
            bbox=dict(boxstyle='square,pad=0.25', fc='white', ec='none', alpha=0.8))
    cax = fig.add_axes([0.055, 0.105, 0.89, 0.028])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation='horizontal', extend='both', extendfrac=0.035)
    cb.outline.set_visible(False); cb.ax.tick_params(colors=MUTED, labelsize=10.5, length=0, pad=6)
    fig.text(0.5, 0.035, 'Sum of Z-scores, Color scale: 2nd–98th percentile', fontsize=15, color=INK, ha='center', va='center')
    fig.savefig(path, facecolor='white', dpi=DPI, pil_kwargs={'quality': 92})
    plt.close(fig)
    print('wrote', os.path.relpath(path, ROOT), Image.open(path).size)


bm = basemap()

# ---------- Fig. 3  Track 1 ----------
col = 'Track1_Score'; top = round(len(oa) * .1)
fig, ax = map_frame('Track 1: Z(LST) + Z(Elderly ratio), output areas', bm)
cmap = LinearSegmentedColormap.from_list('t1', ORANGE)
vmin, vmax = oa[col].quantile([.02, .98]); norm = plt.Normalize(vmin, vmax)
dd = oa.iloc[oa[col].argsort()]; is_top = dd.index.isin(oa[col].nlargest(top).index)
ax.scatter(dd.cx, dd.cy, c=dd[col], cmap=cmap, norm=norm, s=62, linewidths=.7, edgecolors='white', zorder=2)
ax.scatter(dd.cx[is_top], dd.cy[is_top], s=170, facecolors='none', edgecolors='white', linewidths=3.4, zorder=3)
ax.scatter(dd.cx[is_top], dd.cy[is_top], s=170, facecolors='none', edgecolors=INK, linewidths=1.6, zorder=4)
ax.scatter(unassessed.cx, unassessed.cy, marker='X', s=70, c='#6b6a66', edgecolors='white', linewidths=.7, zorder=4)
leg = [Line2D([], [], marker='o', color='none', markerfacecolor='none', markeredgecolor=INK, markeredgewidth=1.8, markersize=12,
              label=f'Top 10% priority review areas ($n$ = {top})'),
       Line2D([], [], marker='o', color='none', markerfacecolor='#8f8f8b', markeredgecolor='white', markersize=10,
              label=f'Output areas analysed ($N$ = {len(oa)})'),
       Line2D([], [], marker='X', color='none', markerfacecolor='#6b6a66', markeredgecolor='white', markersize=10,
              label=f'Unassessed: no valid LST ($n$ = {len(unassessed)})')]
finish(fig, ax, norm, cmap, leg, 'Background: Sentinel-2 true colour (2025), contains modified Copernicus Sentinel data',
       os.path.join(ROOT, 'figs', 'rev_Fig3_Track1.jpg'))

# ---------- Fig. 4  Track 2 (grid) ----------
Dg = pd.read_pickle(os.path.join(ROOT, 'work', 't2grid', 'final.pkl'))
G = pd.read_pickle(os.path.join(ROOT, 'work', 't2grid', 'g.pkl'))
dev = G[(G.dNDBI >= 0.10) & (G.dSAVI <= -0.10) & (G.res_h >= 1000) & (G.known_h > 0)]
fig, ax = map_frame('Track 2: Z(ΔNDBI) + Z(Aged roof area) + Z(ΔRLST), 100 m grid', bm)
cmap = LinearSegmentedColormap.from_list('t2', BLUE)
vmin, vmax = Dg.score.quantile([.02, .98]); norm = plt.Normalize(vmin, vmax)
dd = Dg.sort_values('score'); tt = Dg[Dg.top]
ax.add_collection(PatchCollection([Rectangle((x - 50, y - 50), 100, 100) for x, y in zip(dd.cx, dd.cy)],
                                  facecolor=cmap(norm(dd.score.values)), edgecolor='none', zorder=2))
ax.add_collection(PatchCollection([Rectangle((x - 50, y - 50), 100, 100) for x, y in zip(dev.cx, dev.cy)],
                                  facecolor='#d9d8d2', edgecolor='#6b6a66', linewidth=0.6, hatch='////', zorder=3))
ax.add_collection(PatchCollection([Rectangle((x - 50, y - 50), 100, 100) for x, y in zip(tt.cx, tt.cy)],
                                  facecolor='none', edgecolor=INK, linewidth=0.9, zorder=4))
leg = [Patch(facecolor='none', edgecolor=INK, linewidth=1.4, label=f'Top 10% priority review cells ($n$ = {len(tt)})'),
       Patch(facecolor=BLUE[3], edgecolor='none', label=f'Residential cells, roof ≥ 1,000 m² ($N$ = {len(Dg):,})'),
       Patch(facecolor='#d9d8d2', edgecolor='#6b6a66', hatch='////', label=f'Redevelopment cells, excluded ($n$ = {len(dev)})')]
finish(fig, ax, norm, cmap, leg, 'Background: Sentinel-2 true colour (2025), contains modified Copernicus Sentinel data; buildings: MOLIT GIS building database',
       os.path.join(ROOT, 'figs', 'rev_Fig4_Track2_grid.jpg'))

# ---------- Fig. 1  Research framework ----------
fig = plt.figure(figsize=(7.2, 7.6), dpi=300, facecolor='white')
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 106); ax.axis('off')
EDGE, ACC1, ACC2, FILL = '#555550', '#c9501f', '#256abf', '#f4f3ef'


def box(x, y, w, h, title, lines, ec=EDGE, fc='white', lw=1.0, tsize=8.6, lsize=7.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.2', fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h - 2.6, title, ha='center', va='top', fontsize=tsize, fontweight='bold', color=INK)
    for i, s in enumerate(lines):
        ax.text(x + w / 2, y + h - 7.4 - i * 3.6, s, ha='center', va='top', fontsize=lsize, color=INK2)


def arrow(x1, y1, x2, y2, color=EDGE, text=None, tx=0, ty=0):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle='-|>,head_width=0.3,head_length=0.6', color=color, lw=1.1))
    if text:
        ax.text((x1 + x2) / 2 + tx, (y1 + y2) / 2 + ty, text, ha='center', va='center', fontsize=6.8, color=color, style='italic')


ax.text(52, 104, 'Data (Buk-gu, Gwangju; 2020 and 2025 summers)', ha='center', va='center', fontsize=8.6, fontweight='bold', color=INK)
box(7, 82, 27, 19, 'GIS building database', ['Residential buildings', 'approved before 2000', '→ aged roof area'], fc=FILL)
box(38, 82, 28, 19, 'Satellite (GEE)', ['Landsat 8: LST, NDBI', 'Sentinel-2: SAVI', 'SRTM: DEM'], fc=FILL)
box(70, 82, 28, 19, 'SGIS output areas', ['Elderly ratio (65+)', 'Aged-housing ratio', '919 → 832 analysed'], fc=FILL)

box(7, 46, 42, 30, 'RQ1  Grid model (100 m, N = 11,752)', ['DV: ΔRLST (2020→2025)', 'IV: ΔSAVI, ΔNDBI, SAVI2020,', 'DEM, RLST2020', 'OLS → Moran\'s I → SEM (GM)', 'ΔNDBI scale decomposition'])
box(56, 46, 42, 30, 'RQ2  Output-area model (N = 832)', ['DV: 2025 summer LST', 'IV: elderly ratio, aged housing,', 'ΔNDBI; controls SAVI, DEM', 'OLS → LM tests → SEM / SLM', 'Final: SEM'])

box(7, 9, 42, 31, 'Track 2  Mid- to long-term retrofit', ['100 m residential grid (N = 1,174)', 'Z(ΔNDBI) + Z(aged roof) + Z(ΔRLST)', 'Redevelopment cells (21) separated', 'Top 10%: 117 cells', 'Cool roofs, greening, paving'], ec=ACC2, lw=1.8)
box(56, 9, 42, 31, 'Track 1  Short-term relief', ['Output areas (N = 832)', 'Z(LST) + Z(elderly ratio)', '67 OAs without LST: unassessed', 'Top 10%: 83 output areas', 'Cooling shelters, welfare checks'], ec=ACC1, lw=1.8)
ax.text(52, 4.2, 'RQ3  Sensitivity analysis (MAD, winsorizing, PCA weights, indicator exclusion, residence-based exposure)', ha='center', va='center', fontsize=7.0, color=INK2)
ax.text(52, 1.2, 'IPCC AR6 risk framework: hazard · exposure · vulnerability (sensitivity, adaptive capacity)', ha='center', va='center', fontsize=7.0, color=MUTED)

arrow(46, 82, 34, 76); arrow(58, 82, 70, 76); arrow(84, 82, 84, 76)
# 건물 자료 → Track 2: 왼쪽 여백을 따라 꺾어 내려감
ax.plot([10, 10, 3.5, 3.5], [82, 79, 79, 24.5], color=EDGE, lw=1.1, solid_capstyle='butt')
arrow(3.5, 24.5, 7, 24.5)
ax.annotate('', xy=(28, 40.2), xytext=(28, 46), arrowprops=dict(arrowstyle='-|>,head_width=0.3,head_length=0.6', color=ACC2, lw=1.1))
ax.text(29.5, 43.1, 'basis for ΔNDBI, ΔRLST', ha='left', va='center', fontsize=6.8, color=ACC2, style='italic')
ax.annotate('', xy=(77, 40.2), xytext=(77, 46), arrowprops=dict(arrowstyle='-|>,head_width=0.3,head_length=0.6', color=ACC1, lw=1.1))
ax.text(78.5, 43.1, 'basis for elderly ratio', ha='left', va='center', fontsize=6.8, color=ACC1, style='italic')
out = os.path.join(ROOT, 'figs', 'rev_Fig1_framework.png')
fig.savefig(out, facecolor='white'); plt.close(fig)
print('wrote', os.path.relpath(out, ROOT), Image.open(out).size)
