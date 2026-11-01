# -*- coding: utf-8 -*-
"""
================================================================================
阶梯轴 工程截面图绘制脚本（PoC 演示用）
--------------------------------------------------------------------------------
用途：为「基于图纸 LLM 自动提取加工特征并生成 G 代码」的技术验证
      提供一份带完整尺寸标注的零件工程图，作为 LLM 的输入基线。

零件：阶梯轴   φ20-φ30-φ40   总长 110mm   材料 45 钢
特征：端面 1 / 外圆 3 / 3×45°倒角 3 / φ16 切槽 1 / φ36 退刀槽 1 = 9 个特征
运行：python 01_part_drawing.py
输出：part_drawing.png (300dpi) + part_drawing.svg (矢量源)
================================================================================
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["hatch.linewidth"] = 0.55

# ============================ 1. 零件几何参数 ============================
# 坐标系：右端面中心 = 原点，Z 向左为负；绘图用 y 表示半径
Z_END       = -110.0      # 左端（卡盘夹持侧）
Z_S1        = -30.0       # φ20 段结束
Z_S2        = -60.0       # φ30 段结束
Z_S3        = -87.0       # φ40 段结束（退刀槽右壁）
Z_G2_L      = -90.0       # 退刀槽左壁
Z_G1_R, Z_G1_L = -18.0, -21.0     # φ16 切槽右/左壁

D1, D2, D3, D4 = 20.0, 30.0, 40.0, 45.0
D_G1, D_G2 = 16.0, 36.0
CH = 3.0

R = lambda d: d / 2.0

UP = [
    (0.0, 0.0),
    (0.0, R(D1) - CH),                # 端面倒角起点 φ14
    (-CH, R(D1)),                     # CH1  3×45°
    (Z_G1_R, R(D1)),
    (Z_G1_R, R(D_G1)),                # 切槽右壁
    (Z_G1_L, R(D_G1)),                # φ16 槽底
    (Z_G1_L, R(D1)),                  # 切槽左壁
    (Z_S1, R(D1)),
    (Z_S1, R(D2) - CH),               # 台阶面 → C3 起点 φ26
    (Z_S1 - CH, R(D2)),               # CH2  3×45°
    (Z_S2, R(D2)),
    (Z_S2, R(D3) - CH),               # 台阶面 → C3 起点 φ36
    (Z_S2 - CH, R(D3)),               # CH3  3×45°
    (Z_S3, R(D3)),
    (Z_S3, R(D_G2)),                  # 退刀槽右壁
    (Z_G2_L, R(D_G2)),                # φ36 槽底
    (Z_G2_L, R(D4)),                  # 升至毛坯 φ45
    (Z_END, R(D4)),                   # 夹持段
]
OUTLINE = UP + [(z, -y) for (z, y) in reversed(UP[1:])]

# ============================ 2. 图面风格 ============================
INK   = "#1B2A33"
STEEL = "#E4ECF1"
EDGE  = "#24445C"
DIM   = "#3F6679"
ACC   = "#B5651D"
GRID  = "#BFCED7"

FS_DIM, FS_SMALL, FS_NOTE = 9.0, 7.8, 8.2

X_R, X_L = 96.0, -128.0      # 画布横向范围
Y_T, Y_B = 47.0, -52.0       # 画布纵向范围


# ============================ 3. 标注工具 ============================
def hdim(ax, x1, x2, y, label, fs=FS_DIM, ty=1.3, dx=0.0, ha="center",
         ystart=None, yend=None):
    """水平尺寸：尺寸界线自轮廓引出（留 2mm 间隙），窄段用 45° 斜线代替箭头"""
    for i, x in enumerate((x1, x2)):
        y0 = y - 1.0 if ystart is None else (
            ystart[i] if isinstance(ystart, (tuple, list)) else ystart)
        y1 = y + 2.6 if yend is None else yend
        ax.plot([x, x], [y0, y1], color=DIM, lw=0.6,
                solid_capstyle="butt", zorder=4)
    if abs(x2 - x1) < 5.0:
        for x in (x1, x2):
            ax.plot([x - 1.15, x + 1.15], [y - 1.15, y + 1.15],
                    color=DIM, lw=0.9, solid_capstyle="butt", zorder=4)
    else:
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="<|-|>", color=DIM, lw=0.85,
                                    shrinkA=0, shrinkB=0, mutation_scale=9),
                    zorder=4)
    ax.text((x1 + x2) / 2 + dx, y + ty, label, ha=ha, va="bottom",
            fontsize=fs, color=INK, zorder=5)


def r_at(z):
    """取上半轮廓在给定 Z 处的最大半径，用于确定尺寸界线起点"""
    for i in range(len(UP) - 1):
        (z1, r1), (z2, r2) = UP[i], UP[i + 1]
        if min(z1, z2) - 1e-9 <= z <= max(z1, z2) + 1e-9:
            if abs(z2 - z1) < 1e-9:
                return max(r1, r2)
            return r1 + (z - z1) / (z2 - z1) * (r2 - r1)
    return R(D4)


def vleader(ax, x, y_surf, y_text, label, fs=FS_DIM):
    ax.annotate("", xy=(x, y_surf), xytext=(x, y_text - 3.2),
                arrowprops=dict(arrowstyle="-|>", color=DIM, lw=0.8,
                                shrinkA=0, shrinkB=1.2, mutation_scale=9), zorder=4)
    ax.text(x, y_text, label, ha="center", va="bottom", fontsize=fs,
            color=INK, zorder=5)


def rough(ax, x, y_surf, label="Ra 3.2", fs=FS_SMALL):
    ax.plot([x, x - 1.6, x + 1.9], [y_surf, y_surf + 2.2, y_surf + 4.4],
            color=INK, lw=1.0, solid_capstyle="round", zorder=5)
    ax.plot([x, x + 4.6], [y_surf, y_surf], color=INK, lw=0.9, zorder=5)
    ax.text(x + 3.0, y_surf + 4.0, label, ha="left", va="bottom",
            fontsize=fs, color=INK, zorder=5)


def c3(ax, xy, xytext):
    ax.annotate("C3", xy=xy, xytext=xytext, fontsize=FS_SMALL, color=ACC,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=ACC, lw=0.8,
                                shrinkA=2, shrinkB=2))


# ============================ 4. 绘图 ============================
fig = plt.figure(figsize=(15.0, 6.63), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(X_L, X_R)
ax.set_ylim(Y_B, Y_T)
ax.set_aspect("equal")
ax.axis("off")
fig.patch.set_facecolor("white")

# 4.1 本体（先填充，再叠轮廓线，避免遮住区域注记）
ax.add_patch(Polygon(OUTLINE, closed=True, facecolor=STEEL, edgecolor="none",
                     zorder=3))
ax.text(-104.5, 12.6, "卡盘夹持区", rotation=90, fontsize=7.4,
        color="#6E848F", ha="center", va="center", zorder=3.5)
ax.add_patch(Polygon(OUTLINE, closed=True, facecolor="none", edgecolor=EDGE,
                     lw=1.7, joinstyle="miter", zorder=4))
ax.plot([8, Z_END - 6], [0, 0], color="#7C8F9A", lw=0.8,
        linestyle=(0, (12, 3, 2, 3)), zorder=6)

# 4.3 直径标注
vleader(ax, -9.0,   R(D1), 30.0, "φ20")
vleader(ax, -44.0,  R(D2), 30.0, "φ30")
vleader(ax, -66.0,  R(D3), 30.0, "φ40")
vleader(ax, -98.0, R(D4), 30.0, "φ45")
vleader(ax, (Z_G1_R + Z_G1_L) / 2, R(D_G1), 37.5, "φ16")
vleader(ax, (Z_S3 + Z_G2_L) / 2,  R(D_G2), 37.5, "φ36")

# 4.4 长度尺寸链（尺寸界线自零件底轮廓引出，留 2mm 间隙）
Y_CHAIN, Y_TOTAL = -36.0, -45.5
CHAIN = [(Z_END, Z_G2_L, "20"), (Z_G2_L, Z_S3, "3"), (Z_S3, Z_S2, "27"),
         (Z_S2, Z_S1, "30"), (Z_S1, Z_G1_L, "9"), (Z_G1_L, Z_G1_R, "3"),
         (Z_G1_R, 0.0, "18")]
for x1, x2, t in CHAIN:
    ys = (-r_at(x1) - 2.0, -r_at(x2) - 2.0)
    if abs(x2 - x1) < 5.0:
        hdim(ax, x1, x2, Y_CHAIN, t, fs=FS_SMALL, ty=3.4,
             ystart=ys, yend=Y_CHAIN - 2.2)
    else:
        hdim(ax, x1, x2, Y_CHAIN, t, ystart=ys, yend=Y_CHAIN - 2.2)
hdim(ax, Z_END, 0.0, Y_TOTAL, "110", ystart=Y_CHAIN - 2.2, yend=Y_TOTAL - 2.2)

# 4.5 粗糙度与倒角
rough(ax, -82.0, R(D3), "Ra 3.2")
c3(ax, (-1.6, 8.60), (2.8, 14.6))
c3(ax, (-31.6, 14.07), (-27.6, 18.8))
c3(ax, (-61.6, 19.07), (-57.6, 22.8))

# 4.6 原点
ax.plot(0, 0, marker="+", ms=11, mew=1.8, color=ACC, zorder=7)
ax.text(1.1, 1.2, "O", fontsize=9.5, color=ACC, style="italic",
        ha="left", va="bottom", zorder=7)

# 4.7 图名（置于右侧信息栏顶部，避让零件上方直径标注）
IX, IW = 22.0, 72.0
ax.text(IX, 43.4, "阶梯轴  零件图（工序图）", fontsize=13.5, color=EDGE,
        fontweight="bold", ha="left", va="center")
ax.text(IX, 39.8, "STEPPED SHAFT  ·  TURNING PROCESS DRAWING",
        fontsize=7.4, color="#7C8F9A", ha="left", va="center", style="italic")

# 4.8 技术要求
ax.add_patch(Rectangle((IX, 1.0), IW, 33.0, facecolor="#FBFCFD",
                       edgecolor=GRID, lw=0.9, zorder=1))
ax.text(IX + 2.4, 31.4, "技术要求", fontsize=10.5, color=EDGE,
        fontweight="bold", va="top", ha="left", zorder=2)
TECH = [
    "1. C3 = 3×45° 倒角，全图共 3 处。",
    "2. 未注线性公差按 GB/T 1804-m。",
    "3. 调质 28～32 HRC，无裂纹、磕碰。",
    "4. 未注表面粗糙度 Ra3.2。",
    "5. 毛坯 φ45×130，左端 20 段夹持，",
    "     本工序不加工。",
    "6. 原点 O 在右端面中心（X0 Z0）。",
]
for i, line in enumerate(TECH):
    ax.text(IX + 2.6, 26.6 - i * 3.35, line, fontsize=FS_NOTE, color=INK,
            va="top", ha="left", zorder=2)

# 4.9 标题栏
TB_X, TB_W, TB_TOP, RH = IX, IW, -4.0, 9.5
COLS = [13, 40, 53]
ROWS = [("零件名称", "阶梯轴", "图号", "PoC-001"),
        ("材料", "45 钢", "比例", "1 : 1"),
        ("设计", "待定", "日期", "2026.10.28"),
        ("审核", "工艺高工", "版本", "V1.0")]
for i, (k1, v1, k2, v2) in enumerate(ROWS):
    y = TB_TOP - i * RH
    ax.add_patch(Rectangle((TB_X, y - RH), TB_W, RH, facecolor="white",
                           edgecolor=GRID, lw=0.9, zorder=1))
    for c in COLS:
        ax.plot([TB_X + c, TB_X + c], [y - RH, y], color=GRID, lw=0.8, zorder=2)
    ax.text(TB_X + 1.8, y - RH / 2, k1, fontsize=FS_SMALL, color="#5A6E79",
            va="center", ha="left", zorder=3)
    ax.text(TB_X + 15.0, y - RH / 2, v1, fontsize=FS_SMALL, color=INK,
            va="center", ha="left", zorder=3)
    ax.text(TB_X + 41.5, y - RH / 2, k2, fontsize=FS_SMALL, color="#5A6E79",
            va="center", ha="left", zorder=3)
    ax.text(TB_X + 54.5, y - RH / 2, v2, fontsize=FS_SMALL, color=INK,
            va="center", ha="left", zorder=3)

fig.savefig("part_drawing.png", dpi=300, facecolor="white")
fig.savefig("part_drawing.svg", facecolor="white")

print("总长 %g  最大直径 %g  倒角 %g" % (-Z_END, D4, CH))
print("特征：端面1 外圆3 倒角3 切槽1 退刀槽1 = 9")
print("saved part_drawing.png / part_drawing.svg")
