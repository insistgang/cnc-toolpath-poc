# -*- coding: utf-8 -*-
"""
================================================================================
阶梯轴 车削刀路（Toolpath）仿真脚本
--------------------------------------------------------------------------------
做两件事：
  1. 解析 02_stepped_shaft.nc —— 真正读 G 代码，不另写一份坐标；
  2. 用 matplotlib 绘出「工件截面 + 刀心编程轨迹」，按刀具分色、区分快移与切削。
     G 代码改一个数字，图就跟着变 —— 这正是 PoC 要演示的闭环：代码即模型。

运行：python 03_toolpath.py
输出：toolpath.png (300dpi) + toolpath.svg
================================================================================
"""
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from matplotlib.lines import Line2D

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

NC_FILE = "02_stepped_shaft.nc"

# ============================ 1. 零件几何（与图纸一致） ============================
Z_END, Z_S1, Z_S2, Z_S3, Z_G2_L = -110.0, -30.0, -60.0, -87.0, -90.0
Z_G1_R, Z_G1_L = -18.0, -21.0
D1, D2, D3, D4, D_G1, D_G2, CH = 20.0, 30.0, 40.0, 45.0, 16.0, 36.0, 3.0
R = lambda d: d / 2.0

UP = [
    (0.0, 0.0), (0.0, R(D1) - CH), (-CH, R(D1)),
    (Z_G1_R, R(D1)), (Z_G1_R, R(D_G1)), (Z_G1_L, R(D_G1)), (Z_G1_L, R(D1)),
    (Z_S1, R(D1)), (Z_S1, R(D2) - CH), (Z_S1 - CH, R(D2)),
    (Z_S2, R(D2)), (Z_S2, R(D3) - CH), (Z_S2 - CH, R(D3)),
    (Z_S3, R(D3)), (Z_S3, R(D_G2)), (Z_G2_L, R(D_G2)), (Z_G2_L, R(D4)),
    (Z_END, R(D4)),
]
OUTLINE = UP + [(z, -y) for (z, y) in reversed(UP[1:])]

# ============================ 2. G 代码解析器 ============================
TOK = re.compile(r"([A-Za-z])\s*([-+]?\d*\.?\d+)")


def parse_nc(path):
    """把 .nc 解析成刀心轨迹段列表；X 按直径编程换算为半径"""
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r"\([^)]*\)", "\n", txt, flags=re.S)   # 去掉全部 (中文注释)
    segs, pos, modal, tool = [], (280.0, 130.0), None, None
    for raw in txt.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"[Nn](\d+)", line)
        nline = int(m.group(1)) if m else -1
        body = line[m.end():] if m else line
        pairs = [(k.upper(), float(v)) for k, v in TOK.findall(body)]
        if not pairs:
            continue
        gs = [v for k, v in pairs if k == "G"]
        ts = [v for k, v in pairs if k == "T"]
        xs = [v for k, v in pairs if k == "X"]
        zs = [v for k, v in pairs if k == "Z"]

        if ts:
            tool = int(ts[0])
        if 50 in gs and (xs or zs):                  # G50 X_ Z_ = 坐标系设定
            pos = (zs[0] if zs else pos[0], xs[0] / 2 if xs else pos[1])
            continue
        if 4 in gs:                                  # G04 X_ = 暂停，X 是秒
            continue
        for g in gs:
            if g in (0.0, 1.0, 2.0, 3.0):
                modal = g
        if modal is None or not (xs or zs):
            continue
        nx = xs[0] / 2 if xs else pos[1]
        nz = zs[0] if zs else pos[0]
        segs.append(dict(z0=pos[0], r0=pos[1], z1=nz, r1=nx,
                         rapid=(modal == 0.0), tool=tool, n=nline))
        pos = (nz, nx)
    return segs


SEGS = parse_nc(NC_FILE)
VIS = [s for s in SEGS if max(abs(s["z0"]), abs(s["z1"])) <= 125
       and max(s["r0"], s["r1"]) <= 30]
SKIP = len(SEGS) - len(VIS)

# ============================ 3. 画风 ============================
INK, EDGE, STEEL = "#1B2A33", "#24445C", "#E4ECF1"
C_ROUGH, C_FIN, C_GROOVE = "#C77B26", "#B03A2E", "#2E6F8E"
C_RAPID, GRID = "#AFC0CA", "#CBD9E1"

TOOL_STYLE = {
    101: ("T0101  外圆粗车", C_ROUGH, "-", 1.5),
    202: ("T0202  外圆精车", C_FIN, "-", 1.7),
    303: ("T0303  切槽刀", C_GROOVE, "-", 1.7),
}


def style_of(tool):
    return TOOL_STYLE.get(tool, ("T%s  其他" % tool, "#888888", "-", 1.2))


def draw_blank(ax):
    """毛坯 φ45 参考轮廓"""
    for y in (R(D4), -R(D4)):
        ax.plot([2.5, Z_END - 4], [y, y], color="#B9C7D0", lw=0.8,
                linestyle=(0, (5, 3)), zorder=1)


def draw_part(ax):
    ax.add_patch(Polygon(OUTLINE, closed=True, facecolor=STEEL, edgecolor=EDGE,
                         lw=1.5, joinstyle="miter", zorder=2))
    ax.plot([Z_END - 6, 12], [0, 0], color="#7C8F9A", lw=0.75,
            linestyle=(0, (12, 3, 2, 3)), zorder=3)


def draw_path(ax, segs, lw=1.0):
    for s in segs:
        if s["rapid"]:
            ax.plot([s["z0"], s["z1"]], [s["r0"], s["r1"]], color=C_RAPID,
                    lw=0.65 * lw, linestyle=(0, (4, 2.4)),
                    solid_capstyle="round", zorder=4)
        else:
            _, c, _, w = style_of(s["tool"])
            ax.plot([s["z0"], s["z1"]], [s["r0"], s["r1"]], color=c,
                    lw=w * lw, solid_capstyle="round", zorder=5)


def fmt(ax, title):
    ax.set_aspect("equal")
    ax.set_facecolor("white")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors="#5A6E79", labelsize=7.8, length=3, width=0.7)
    ax.grid(True, color=GRID, lw=0.55, alpha=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=10.2, color=EDGE, loc="left", pad=7,
                 fontweight="bold")
    ax.set_xlabel("Z 轴向（mm）", fontsize=8.6, color="#5A6E79", labelpad=3)


# ============================ 4. 版面计算（按数据比自动定尺寸） ============================
FIG_W = 14.4
M_L, M_R, GAP, TOP, BOT = 0.78, 0.28, 1.32, 1.10, 1.06
A_W, A_H = 140.0, 72.0        # (a) xlim −124..16, ylim −42..30
B_W, B_H = 40.0, 34.0         # (b) xlim −24..16,  ylim −16..18

k = A_W / A_H + B_W / B_H
H = (FIG_W - M_L - M_R - GAP) / k
W1, W2 = A_W / A_H * H, B_W / B_H * H
FIG_H = H + TOP + BOT

fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=300)
fig.patch.set_facecolor("white")
ax1 = fig.add_axes([M_L / FIG_W, BOT / FIG_H, W1 / FIG_W, H / FIG_H])
ax2 = fig.add_axes([(M_L + W1 + GAP) / FIG_W, BOT / FIG_H, W2 / FIG_W, H / FIG_H])

# --- (a) 全图 ---
draw_blank(ax1)
draw_part(ax1)
draw_path(ax1, VIS, lw=1.0)
ax1.set_xlim(-124, 16)
ax1.set_ylim(-42, 30)
fmt(ax1, "（a）全程序刀心轨迹 —— 3 把刀 / 4 道工序")
ax1.set_yticks([-20, -10, 0, 10, 20])
ax1.set_ylabel("X 半径（mm）", fontsize=8.6, color="#5A6E79", labelpad=4)

ax1.plot(6, 25, marker="o", ms=4.2, mfc="white", mec=INK, mew=1.2, zorder=9)
ax1.annotate("安全起始点 X50 Z6", xy=(6.3, 24.7), xytext=(15.0, 28.6),
             fontsize=7.2, color=INK, ha="right", va="center",
             arrowprops=dict(arrowstyle="-", color="#8FA3AE", lw=0.7,
                             shrinkA=2, shrinkB=3))
ax1.plot([-121.5, -118.5], [27.4, 27.4], color="#B9C7D0", lw=0.9,
         linestyle=(0, (5, 3)))
ax1.text(-117.4, 27.4, "毛坯 φ45 参考线", fontsize=7.2, color="#8FA3AE",
         ha="left", va="center")

ax1.legend(handles=[
    Line2D([], [], color=C_ROUGH, lw=1.6, label="T0101 粗车  ap=2.5"),
    Line2D([], [], color=C_FIN, lw=1.8, label="T0202 精车  G42 补偿"),
    Line2D([], [], color=C_GROOVE, lw=1.8, label="T0303 切槽  φ16 / φ36"),
    Line2D([], [], color=C_RAPID, lw=0.9, ls=(0, (4, 2.4)), label="G00 快速移动"),
    Line2D([], [], color=EDGE, lw=1.5, label="成品轮廓"),
], loc="lower left", bbox_to_anchor=(0.002, -0.005), fontsize=7.3,
    frameon=True, facecolor="white", edgecolor=GRID, framealpha=1.0,
    handlelength=2.1, borderpad=0.55, labelspacing=0.38)

# --- (b) 右端放大 ---
draw_part(ax2)
draw_path(ax2, VIS, lw=1.55)
ax2.set_xlim(-24, 16)
ax2.set_ylim(-16, 18)
fmt(ax2, "（b）右端放大 —— C3 倒角 / G42 引入 / φ16 切槽")
ax2.set_yticks([-15, -10, -5, 0, 5, 10, 15])

for tag, xy, col in (("①", (-19.5, 5.8), C_GROOVE), ("②", (5.4, 8.6), C_FIN)):
    ax2.text(xy[0], xy[1], tag, fontsize=8.4, color=col, ha="center", va="center",
             bbox=dict(boxstyle="circle,pad=0.22", fc="white", ec=col, lw=0.9),
             zorder=10)
ax2.plot(4.0, 4.0, marker="o", ms=3.2, mfc="white", mec=C_FIN, mew=1.1, zorder=9)
ax1.add_patch(Rectangle((-24, -16), B_W, B_H, facecolor="none",
                        edgecolor="#8FA3AE", lw=0.9, linestyle=(0, (3, 2)),
                        zorder=7))

# --- 标题区 ---
fig.text(M_L / FIG_W, 0.963, "阶梯轴车削刀路仿真", fontsize=15.5, color=EDGE,
         fontweight="bold", ha="left", va="center")
fig.text(M_L / FIG_W, 0.921,
         "由 02_stepped_shaft.nc 直接解析生成  ·  X 按直径编程已换算为半径  ·  "
         "毛坯 φ45×130  材料 45 钢  ·  轨迹 %d 段" % len(VIS),
         fontsize=8.1, color="#7C8F9A", ha="left", va="center")
fig.text(M_L / FIG_W, 0.882,
         "工序：① 车端面  →  ② 外圆粗车 5 刀  →  ③ 精车 G42  →  "
         "④ 切槽 2 处  →  ⑤ 返回参考点",
         fontsize=8.1, color=EDGE, ha="left", va="center")
if SKIP:
    fig.text(1 - M_R / FIG_W, 0.882, "参考点往返 %d 段超出图幅未绘制" % SKIP,
             fontsize=7.6, color="#A9BCC6", ha="right", va="center")

fig.text(M_L / FIG_W, 0.052,
         "①  φ16×3 切槽：T0303 于 Z-19.5 一次切入至 φ16，槽底 G04 暂停 0.5 s；"
         "φ36×3 退刀槽同法在 Z-88.5 切出\n"
         "②  G42 右刀补：在 N390 斜向引入段建立，刀尖圆弧 R0.4 与刀尖方位号 T3 "
         "必须与刀补表一致，否则倒角与台阶过切；G40 在 N490 取消",
         fontsize=7.6, color="#5A6E79", ha="left", va="bottom", linespacing=1.7)

fig.savefig("toolpath.png", dpi=300, facecolor="white")
fig.savefig("toolpath.svg", facecolor="white")

feed = [s for s in VIS if not s["rapid"]]
print("轨迹段 %d（切削 %d / 快移 %d），版面 %.2f x %.2f in"
      % (len(VIS), len(feed), len(VIS) - len(feed), FIG_W, FIG_H))
for t in sorted({s["tool"] for s in feed}):
    sub = [s for s in feed if s["tool"] == t]
    L = sum(abs(s["z1"] - s["z0"]) + abs(s["r1"] - s["r0"]) for s in sub)
    print("  T%s  切削段 %2d  刀路长度约 %6.1f mm" % (t, len(sub), L))
print("saved toolpath.png / toolpath.svg")
