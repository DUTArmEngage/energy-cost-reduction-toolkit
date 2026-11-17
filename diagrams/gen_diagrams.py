"""ECRT diagrams: block diagram + two Altium-style schematic sheets (control, mains switching).

Run: python3 gen_diagrams.py -> ecrt_block_diagram, ecrt_schematic_control, ecrt_schematic_mains ({png,svg,pdf})
The old UAV version is kept in gen_diagrams_uav_backup.py.
"""
import os
import random

import matplotlib
import matplotlib.patches
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

C_SENS, C_WIFI, C_VID, C_EMG, C_STAT, C_PWR, C_GND = (
    "#1a8a1a", "#1f3fd0", "#8a1a9a", "#d01010", "#e08a00", "#c03000", "#222222")
C_NA = "#8a8a8a"


def box(ax, x, y, w, h, text, fs=8, na=False, fc="white", bold=False, ls=None):
    ec = C_NA if na else "#222222"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.2",
                                fc="#f0f0f0" if na else fc, ec=ec, lw=1.1,
                                ls=ls or ("--" if na else "-")))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=C_NA if na else "black", fontweight="bold" if bold else "normal",
            linespacing=1.25)


def line(ax, pts, color="black", ls="-", lw=1.3, arrow=False, both=False, z=2):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, ls=ls, lw=lw, zorder=z, solid_capstyle="butt")
    if arrow:
        ax.annotate("", xy=pts[-1], xytext=pts[-2],
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0),
                    zorder=z)
    if both:
        ax.annotate("", xy=pts[0], xytext=pts[1],
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0),
                    zorder=z)


def canvas(w, h, figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def save(fig, name):
    for ext in ("png", "svg", "pdf"):
        fig.savefig(os.path.join(HERE, f"{name}.{ext}"), dpi=170, bbox_inches="tight")
    plt.close(fig)


# ================================================== Altium Designer-style schematic
# Circuit only: symbols, wires, junctions, power ports and net labels (no frame, title block or notes).
# Altium defaults: pale-yellow component bodies with dark-red outlines/pins, blue wires, dark-red power ports.
from matplotlib import font_manager
for _f in ("Times_New_Roman.ttf", "Times_New_Roman_Bold.ttf"):      # Altium's default schematic font, if installed
    _p = os.path.join("/usr/share/fonts/truetype/msttcorefonts", _f)
    if os.path.exists(_p):
        font_manager.fontManager.addfont(_p)
plt.rcParams["font.family"] = ["Times New Roman", "Liberation Serif", "DejaVu Serif"]
BG, WIRE, SYM, NUM, TXT, LBL, FILL, PWR = (
    "#FFFFFF", "#000080", "#800000", "#800000", "#000080", "#000080", "#FFFFB0", "#800000")
STUB, PITCH, FIRST = 4.0, 4.0, 9.0       # pin stub length, pin pitch, first pin offset


def kcanvas(w, y0, y1, figsize):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, w); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def ksave(fig, name):
    for ext in ("png", "svg", "pdf"):
        fig.savefig(os.path.join(HERE, f"{name}.{ext}"), dpi=170, bbox_inches="tight",
                    facecolor=BG)
    plt.close(fig)


def wire(ax, pts):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=WIRE, lw=1.5, zorder=2, solid_capstyle="butt", solid_joinstyle="miter")


def junction(ax, x, y):
    ax.plot(x, y, "o", ms=4.4, color=WIRE, zorder=6)


class Mod:
    """Altium-style symbol: pale-yellow body, dark-red outline and pins, designator and comment in blue."""

    def __init__(self, ax, ref, name, sub, x, y_top, w, pins, side, extra=None, nums=False):
        self.ax, self.side = ax, side
        n = max(len(pins), len(extra or []))
        self.h = FIRST + PITCH * n + 1.5
        self.x, self.y0, self.w, self.top = x, y_top - self.h, w, y_top
        ax.add_patch(Rectangle((x, self.y0), w, self.h, fc=FILL, ec=SYM, lw=1.8, zorder=3))
        ax.text(x, y_top + 1.0, ref, ha="left", va="bottom", fontsize=7, color=TXT, zorder=4)
        ax.text(x + w / 2, y_top - 2.6, name, ha="center", va="center", fontsize=7.5,
                color=TXT, fontweight="bold", zorder=4)
        if sub:
            ax.text(x + w / 2, y_top - 5.4, sub, ha="center", va="center", fontsize=6,
                    color=TXT, zorder=4)
        self.pin, self.xpin = {}, {}
        num = 1
        for edge_pins, main in ((pins, True), (extra or [], False)):
            on_right = (side == "right") == main
            for i, p in enumerate(edge_pins):
                if p is None:
                    continue
                py = y_top - FIRST - i * PITCH
                ex = x + w if on_right else x
                sg = 1 if on_right else -1
                ax.plot([ex, ex + sg * STUB], [py, py], color=SYM, lw=1.7, zorder=2)
                if nums:
                    ax.text(ex + sg * STUB / 2, py + 0.7, str(num), ha="center", va="bottom",
                            fontsize=6.4, color=NUM, zorder=4)
                ax.text(ex - sg * 1, py, p, ha="right" if on_right else "left", va="center",
                        fontsize=7.2, color=TXT, zorder=4)
                (self.pin if main else self.xpin)[p] = (ex + sg * STUB, py)
                num += 1


def power(ax, xy, label, direction):
    """Altium power port hung off a pin tip: +V = 'Bar' style, GND = 'Power Ground' (three bars).
    For left/right pins the symbol is rotated so it stays on the pin's own row (pin pitch is 4 units);
    'up'/'down' are for vertical pins."""
    x, y = xy
    if direction in ("left", "right"):
        d = 1 if direction == "right" else -1
        xs = x + d * 2.2
        wire(ax, [(x, y), (xs, y)])
        if label == "GND":
            for k, half in enumerate((1.7, 1.15, 0.6)):
                xx = xs + d * 0.95 * k
                ax.plot([xx, xx], [y - half, y + half], color=SYM, lw=1.5, zorder=5, solid_capstyle="butt")
            tx = xs + d * 3.3
        else:
            ax.plot([xs, xs], [y - 1.7, y + 1.7], color=SYM, lw=1.8, zorder=5, solid_capstyle="butt")
            tx = xs + d * 1.5
        ax.text(tx, y, label, ha="left" if d > 0 else "right", va="center", fontsize=7, color=PWR, zorder=6)
        return
    sg = -1 if direction == "down" else 1
    if label == "GND":
        ax.plot([x, x], [y, y - 1.6], color=SYM, lw=1.5, zorder=5, solid_capstyle="butt")
        for k, half in enumerate((1.9, 1.3, 0.6)):
            yy = y - 1.6 - 0.95 * k
            ax.plot([x - half, x + half], [yy, yy], color=SYM, lw=1.5, zorder=5, solid_capstyle="butt")
        ax.text(x + 2.6, y - 2.4, label, ha="left", va="center", fontsize=7, color=PWR)
    else:
        top = y + 2.4
        ax.plot([x, x], [y, top], color=SYM, lw=1.5, zorder=5, solid_capstyle="butt")
        ax.plot([x - 1.8, x + 1.8], [top, top], color=SYM, lw=1.8, zorder=5, solid_capstyle="butt")
        ax.text(x, top + 1.0, label, ha="center", va="bottom", fontsize=7, color=PWR)


PORT_FILL, NC_RED = "#FFE9A8", "#C00000"


def port(ax, xy, net, direction):
    """Altium port (connector flag) carrying a net name; direction = 'left'/'right' = which way it points away from the pin."""
    x, y = xy
    d = 1 if direction == "right" else -1
    L = 4.0 + 1.15 * len(net)
    ax.add_patch(plt.Polygon([(x, y - 1.4), (x + d * (L - 1.6), y - 1.4), (x + d * L, y),
                              (x + d * (L - 1.6), y + 1.4), (x, y + 1.4)],
                             closed=True, fc=PORT_FILL, ec=SYM, lw=1.1, zorder=5))
    ax.text(x + d * (L - 1.6) / 2, y, net, ha="center", va="center", fontsize=7.2, color=LBL, zorder=6)


def noconnect(ax, xy):
    """Altium 'No ERC' cross on an unused pin."""
    x, y = xy
    for dx in ((-1.1, 1.1), (-1.1, 1.1)):
        pass
    ax.plot([x - 1.1, x + 1.1], [y - 1.1, y + 1.1], color=NC_RED, lw=1.4, zorder=6, solid_capstyle="butt")
    ax.plot([x - 1.1, x + 1.1], [y + 1.1, y - 1.1], color=NC_RED, lw=1.4, zorder=6, solid_capstyle="butt")


def attach(ax, tip, spec, direction):
    """spec: ('p', '+3V3'|'+5V'|'GND') power port | ('n', 'NET') port with net name | None = unused pin (no-connect)."""
    if spec is None:
        noconnect(ax, tip)
    elif spec[0] == "s":
        return
    elif spec[0] == "p":
        power(ax, tip, spec[1], direction)
    else:
        port(ax, tip, spec[1], direction)


P3, P5, PG = ("p", "+3V3"), ("p", "+5V"), ("p", "GND")


def N(net):
    return ("n", net)


SKIP = ("s",)


def resistor_h(ax, x, y, ref, value):
    """Altium-style resistor (horizontal): hollow rectangle body, pin leads. Returns (left tip, right tip)."""
    ax.add_patch(Rectangle((x - 3.2, y - 1.2), 6.4, 2.4, fc=FILL, ec=SYM, lw=1.5, zorder=3))
    ax.plot([x - 6.0, x - 3.2], [y, y], color=SYM, lw=1.7, zorder=2, solid_capstyle="butt")
    ax.plot([x + 3.2, x + 6.0], [y, y], color=SYM, lw=1.7, zorder=2, solid_capstyle="butt")
    ax.text(x, y + 1.8, ref, ha="center", va="bottom", fontsize=7, color=TXT)
    ax.text(x, y - 1.8, value, ha="center", va="top", fontsize=6.6, color=TXT)
    return (x - 6.0, y), (x + 6.0, y)


def led_h(ax, x, y, ref, name):
    """Altium-style LED (horizontal): triangle + cathode bar + two emission arrows. Anode left, cathode right."""
    ax.add_patch(plt.Polygon([(x - 1.8, y + 1.8), (x - 1.8, y - 1.8), (x + 1.8, y)], closed=True,
                             fc=FILL, ec=SYM, lw=1.5, zorder=3))
    ax.plot([x + 1.8, x + 1.8], [y - 1.8, y + 1.8], color=SYM, lw=1.7, zorder=3, solid_capstyle="butt")
    ax.plot([x - 4.6, x - 1.8], [y, y], color=SYM, lw=1.7, zorder=2, solid_capstyle="butt")
    ax.plot([x + 1.8, x + 4.6], [y, y], color=SYM, lw=1.7, zorder=2, solid_capstyle="butt")
    for dx in (-0.6, 1.2):
        ax.annotate("", xy=(x + dx + 2.0, y + 4.4), xytext=(x + dx, y + 2.4),
                    arrowprops=dict(arrowstyle="-|>", color=SYM, lw=1.0, shrinkA=0, shrinkB=0, mutation_scale=6), zorder=4)
    ax.text(x, y + 5.6, ref, ha="center", va="bottom", fontsize=7, color=TXT)
    ax.text(x, y - 2.4, name, ha="center", va="top", fontsize=6.6, color=TXT)
    return (x - 4.6, y), (x + 4.6, y)


def header(ax, x, y_top, ref, name, specs, side, jack=False):
    """Altium-style connector/header: thin body with a socket dot per pin, numbered pin leads. specs = one per pin
    (power / net-port / None for unused / SKIP for hand-wired). Returns the pin tips."""
    n, w = len(specs), (6.0 if jack else 3.0)
    h = 4.0 * n
    ax.add_patch(Rectangle((x, y_top - h), w, h, fc=FILL, ec=SYM, lw=1.5, zorder=3))
    ax.text(x, y_top + 1.0, ref, ha="left", va="bottom", fontsize=7, color=TXT)
    ax.text(x, y_top - h - 1.0, name, ha="left", va="top", fontsize=6.6, color=TXT)
    if jack:
        ax.add_patch(plt.Circle((x + w / 2, y_top - h / 2), 2.2, fc="none", ec=SYM, lw=1.3, zorder=4))
        ax.add_patch(plt.Circle((x + w / 2, y_top - h / 2), 0.8, fc=SYM, ec=SYM, zorder=4))
    tips = []
    for i, spec in enumerate(specs):
        y = y_top - 2.0 - 4.0 * i
        ex = x + w if side == "right" else x
        sg = 1 if side == "right" else -1
        ax.plot([ex, ex + sg * STUB], [y, y], color=SYM, lw=1.7, zorder=2)
        if not jack:
            ax.add_patch(plt.Circle((x + w / 2, y), 0.7, fc=SYM, ec=SYM, zorder=4))
        ax.text(ex + sg * STUB / 2, y + 0.7, str(i + 1), ha="center", va="bottom", fontsize=6.4, color=NUM, zorder=4)
        tip = (ex + sg * STUB, y)
        tips.append(tip)
        attach(ax, tip, spec, side)
    return tips


def cap_pol_h(ax, x, y, ref, value):
    """Altium-style polarised capacitor (horizontal): straight + plate on the left, curved plate on the right. Returns tips."""
    ax.plot([x - 4.6, x - 1.1], [y, y], color=SYM, lw=1.7, zorder=2, solid_capstyle="butt")
    ax.plot([x + 1.1, x + 4.6], [y, y], color=SYM, lw=1.7, zorder=2, solid_capstyle="butt")
    ax.plot([x - 1.1, x - 1.1], [y - 2.6, y + 2.6], color=SYM, lw=2.0, zorder=3, solid_capstyle="butt")
    ax.add_patch(matplotlib.patches.Arc((x + 4.0, y), 5.8, 5.8, theta1=145, theta2=215, ec=SYM, lw=2.0, zorder=3))
    ax.text(x - 3.0, y + 2.6, "+", ha="center", va="center", fontsize=7, color=TXT, zorder=4)
    ax.text(x, y + 4.2, ref, ha="center", va="bottom", fontsize=7, color=TXT)
    ax.text(x, y - 3.4, value, ha="center", va="top", fontsize=6.6, color=TXT)
    return (x - 4.6, y), (x + 4.6, y)


def check_overlaps(fig, ax, label="schematic"):
    """Print any text/text or text/port-flag collisions (bounding boxes in display space)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    texts = [(t.get_text(), t.get_window_extent(r)) for t in ax.texts if t.get_text()]
    flags = [p.get_extents() for p in ax.patches if isinstance(p, plt.Polygon)]
    bad = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if texts[i][1].overlaps(texts[j][1]) and texts[i][1].width > 0 and texts[j][1].width > 0:
                inter_w = min(texts[i][1].x1, texts[j][1].x1) - max(texts[i][1].x0, texts[j][1].x0)
                inter_h = min(texts[i][1].y1, texts[j][1].y1) - max(texts[i][1].y0, texts[j][1].y0)
                if inter_w > 1.5 and inter_h > 1.5:
                    print("TEXT OVERLAP:", repr(texts[i][0]), "<->", repr(texts[j][0])); bad += 1
    for name, bb in texts:
        for fb in flags:
            cx, cy = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
            inside = fb.x0 <= cx <= fb.x1 and fb.y0 <= cy <= fb.y1
            if not inside and bb.overlaps(fb):
                inter_w = min(bb.x1, fb.x1) - max(bb.x0, fb.x0); inter_h = min(bb.y1, fb.y1) - max(bb.y0, fb.y0)
                if inter_w > 1.5 and inter_h > 1.5:
                    print("TEXT ON PORT:", repr(name)); bad += 1
    print(label, "overlap check:", "clean" if not bad else f"{bad} problem(s)")


P12 = ("p", "+12V")


def mod2(ax, ref, name, sub, x, y_top, w, side, main, extra=(), nums=False):
    """Module symbol from (pin, spec) lists. Main pins face `side`, extra pins the other edge. Pin names must be unique per list."""
    m = Mod(ax, ref, name, sub, x, y_top, w, [p for p, _ in main], side, extra=[p for p, _ in extra], nums=nums)
    for p, s in main:
        attach(ax, m.pin[p], s, side)
    opp = "left" if side == "right" else "right"
    for p, s in extra:
        attach(ax, m.xpin[p], s, opp)
    return m


def notes(ax, x, y, lines, step=4.4):
    for i, t in enumerate(lines):
        ax.text(x, y - step * i, t, ha="left", va="center", fontsize=6.8 if i else 7.6, color=TXT,
                fontweight="bold" if i == 0 else "normal")


# =============================================================== BLOCK DIAGRAM
def block_diagram():
    fig, ax = canvas(204, 112, (16.5, 9.2))
    C_MAINS = C_EMG

    # mains path (left column, top to bottom)
    box(ax, 3, 92, 30, 12, "230 V AC supply")
    box(ax, 3, 74, 30, 12, "QF1 2P 63 A\nbreaker")
    box(ax, 3, 52, 30, 16, "PZEM-004T V4\n+ 100 A split-core CT\n(aggregate meter)")
    box(ax, 3, 26, 30, 16, "KM1-KM4\ncontactors 25 A, 2xNO")
    box(ax, 3, 4, 30, 12, "4 appliance channels")
    for ya, yb in ((92, 86), (74, 68), (52, 42), (26, 16)):
        line(ax, [(18, ya), (18, yb)], C_MAINS, arrow=True)

    # controller column
    box(ax, 70, 52, 36, 36, "Arduino Uno R3\nATmega328P, 5 V / 16 MHz\n\nSoftwareSerial (PZEM)\nUSB serial (Pi)\nI2C, GPIO", fs=8)
    box(ax, 70, 94, 36, 12, "1602 I2C LCD +\n4x4 keypad")
    box(ax, 70, 22, 36, 16, "12 V 4-channel relay module\n(IN1-IN4)")

    # Raspberry Pi side
    box(ax, 125, 78, 38, 24, "Raspberry Pi 3B+\nPython: tariff, cost,\nscheduling, web dashboard,\nSQLite")
    box(ax, 172, 84, 28, 16, "Dashboard\n(browser over Wi-Fi)")

    # power chain
    box(ax, 108, 4, 28, 14, "12 V DC supply\n(Uno VIN, relays;\nnot on quote)")
    box(ax, 142, 4, 28, 14, "K7805 SMPS\n5 V 2 A (Pi)")
    line(ax, [(136, 11), (142, 11)], C_PWR, arrow=True)
    line(ax, [(156, 18), (156, 78)], C_PWR, lw=1.2, arrow=True)
    ax.text(158, 48, "5 V to the Pi", fontsize=6.3, color=C_PWR, va="center")
    line(ax, [(116, 18), (116, 58), (106, 58)], C_PWR, lw=1.0, arrow=True)
    line(ax, [(116, 30), (106, 30)], C_PWR, lw=1.0, arrow=True)
    ax.plot(116, 30, "o", ms=3, color=C_PWR)
    ax.text(118, 44, "12 V: Uno VIN,\nrelay coils", fontsize=6.3, color=C_PWR, va="center")

    # data / control
    line(ax, [(33, 60), (70, 60)], C_SENS, arrow=True)
    ax.text(51, 61.5, "TTL serial\n(V, I, P, E)", ha="center", va="bottom", fontsize=6.5, color=C_SENS)
    line(ax, [(88, 52), (88, 38)], C_STAT, arrow=True)
    ax.text(90, 45, "D4-D7", fontsize=6.5, color=C_STAT, va="center")
    line(ax, [(70, 30), (33, 30)], C_STAT, arrow=True)
    ax.text(51, 31.5, "NO contacts switch\n230 V coils", ha="center", va="bottom", fontsize=6.5, color=C_STAT)
    line(ax, [(88, 88), (88, 94)], C_SENS, arrow=True, both=True)
    line(ax, [(106, 70), (144, 70), (144, 78)], C_WIFI, arrow=True, both=True)
    ax.text(125, 71.5, "USB cable (serial)", ha="center", va="bottom", fontsize=6.5, color=C_WIFI)
    line(ax, [(163, 92), (172, 92)], C_WIFI, ls="--", arrow=True, both=True)
    ax.text(167.5, 94, "Wi-Fi", ha="center", fontsize=6.5, color=C_WIFI)

    lx, ly = 125, 109
    items = [(C_MAINS, "-", "230 V mains"), (C_SENS, "-", "data"), (C_STAT, "-", "control"),
             (C_WIFI, "--", "USB / Wi-Fi"), (C_PWR, "-", "DC power")]
    for i, (c, s_, t) in enumerate(items):
        x0 = lx + (i % 3) * 22
        y0 = ly - (i // 3) * 3.6
        ax.plot([x0, x0 + 4], [y0, y0], color=c, ls=s_, lw=1.6)
        ax.text(x0 + 5, y0, t, fontsize=6.5, va="center")
    save(fig, "ecrt_block_diagram")


# ================================================== wiring helpers (real wires instead of net-name ports)
def _seg_pen(a, b, c, d):
    ah, ch = abs(a[1] - b[1]) < 1e-9, abs(c[1] - d[1]) < 1e-9
    if ah and ch:
        if abs(a[1] - c[1]) > 1e-6:
            return 0
        lo, hi = max(min(a[0], b[0]), min(c[0], d[0])), min(max(a[0], b[0]), max(c[0], d[0]))
        return 1000 if hi - lo > 1e-6 else 0
    if (not ah) and (not ch):
        if abs(a[0] - c[0]) > 1e-6:
            return 0
        lo, hi = max(min(a[1], b[1]), min(c[1], d[1])), min(max(a[1], b[1]), max(c[1], d[1]))
        return 1000 if hi - lo > 1e-6 else 0
    h, v = ((a, b), (c, d)) if ah else ((c, d), (a, b))
    hx0, hx1 = sorted((h[0][0], h[1][0]))
    y = h[0][1]
    vx = v[0][0]
    vy0, vy1 = sorted((v[0][1], v[1][1]))
    if hx0 - 1e-6 <= vx <= hx1 + 1e-6 and vy0 - 1e-6 <= y <= vy1 + 1e-6:
        interior = hx0 + 1e-6 < vx < hx1 - 1e-6 and vy0 + 1e-6 < y < vy1 - 1e-6
        return 1 if interior else 1000
    return 0


def wire_penalty(polys):
    segs = [(i, a, b) for i, p in enumerate(polys) for a, b in zip(p, p[1:]) if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1e-6]
    tot = 0
    for k, (i, a, b) in enumerate(segs):
        for (j, c, d) in segs[k + 1:]:
            if i != j:
                tot += _seg_pen(a, b, c, d)
    return tot


def channel_wires(pairs, xs, tries=1500):
    """Route each (A, B) tip pair as A -> vertical channel -> B, picking the channel order with the fewest crossings.
    Returns (polylines, penalty). A penalty of 1000 or more would mean two wires lie on top of each other."""
    n = len(pairs)
    rnd = random.Random(1)

    def build(perm):
        return [[A, (xs[perm[i]], A[1]), (xs[perm[i]], B[1]), B] for i, (A, B) in enumerate(pairs)]

    cands = [list(range(n)), list(range(n))[::-1]]
    by_a = sorted(range(n), key=lambda i: pairs[i][0][1])
    cands += [[by_a.index(i) for i in range(n)], [n - 1 - by_a.index(i) for i in range(n)]]
    bp = min(cands, key=lambda p_: wire_penalty(build(p_)))
    best = wire_penalty(build(bp))
    for _ in range(tries):
        q = bp[:]
        i, j = rnd.sample(range(n), 2)
        q[i], q[j] = q[j], q[i]
        pq_ = wire_penalty(build(q))
        if pq_ <= best:
            best, bp = pq_, q
    return build(bp), best


def draw_wires(ax, polys):
    for p in polys:
        pts = [p[0]]
        for q in p[1:]:
            if abs(q[0] - pts[-1][0]) + abs(q[1] - pts[-1][1]) > 1e-6:
                pts.append(q)
        wire(ax, pts)


# ================================================== SHEET 1: low-voltage control
def schematic_control():
    """Control sheet: Arduino Uno, PZEM TTL side, LCD, keypad, relay module inputs, USB link to the Pi, 12 V supply and the Pi's 5 V.
    Signals are drawn as real wires (no net-name ports); only the power rails and ground use power symbols.
    Pin allocation: D2/D3 SoftwareSerial to PZEM (D0/D1 are the USB serial link), D4-D7 relays, D10-D13 + A0-A3 keypad (4 rows,
    4 columns), A4/A5 I2C LCD. The Uno is 5 V logic, so every module connects directly."""
    fig, ax = kcanvas(394, -8, 172, (25.5, 11.9))
    TOP = 150

    pi = mod2(ax, "U8", "Raspberry Pi 3B+", "Python, web dashboard, Wi-Fi", 36, TOP, 30, "right",
              main=[("USB", SKIP)], extra=[("PWR", ("p", "+5V PI"))])

    u1 = mod2(ax, "U1", "Arduino Uno R3", "ATmega328P, 5 V / 16 MHz", 116, TOP, 34, "right",
              main=[("D2 (SW-RX)", SKIP), ("D3 (SW-TX)", SKIP), ("D4", SKIP), ("D5", SKIP), ("D6", SKIP), ("D7", SKIP),
                    ("D8", None), ("D9", None),
                    ("D10", SKIP), ("D11", SKIP), ("D12", SKIP), ("D13", SKIP),
                    ("A0", SKIP), ("A1", SKIP), ("A2", SKIP), ("A3", SKIP), ("A4 (SDA)", SKIP), ("A5 (SCL)", SKIP)],
              extra=[("USB-B", SKIP), ("VIN", P12), ("5V", P5), ("GND", PG), ("3V3", None), ("IOREF", None),
                     ("RESET", None), ("AREF", None), ("D0 (RX)", None), ("D1 (TX)", None)])
    # USB cable: Pi USB-A port to the Uno USB-B socket (same row, one straight wire)
    draw_wires(ax, [[pi.pin["USB"], u1.xpin["USB-B"]]])
    ax.text((pi.pin["USB"][0] + u1.xpin["USB-B"][0]) / 2, pi.pin["USB"][1] + 1.0, "USB cable (serial + power)", ha="center",
            va="bottom", fontsize=6.5, color=LBL)

    # peripherals, pins face the Uno (shifted by 2 so their rows never line up with the Uno's)
    px, pw, y = 230, 34, TOP - 2
    stack_parts = [
        ("U2", "PZEM-004T V4 (TTL side)", "5 V TTL, 9600 baud",
         [("5V", P5), ("RX", SKIP), ("TX", SKIP), ("GND", PG)]),
        ("U3", "LCD 1602 + I2C", "backpack, 5 V, addr 0x27 (typ.)",
         [("GND", PG), ("VCC", P5), ("SDA", SKIP), ("SCL", SKIP)]),
        ("KP1", "4x4 keypad", "thin-film matrix",
         [("R1", SKIP), ("R2", SKIP), ("R3", SKIP), ("R4", SKIP), ("C1", SKIP), ("C2", SKIP), ("C3", SKIP), ("C4", SKIP)]),
        ("U5", "4-ch relay module", "12 V coils, control side",
         [("VCC", P12), ("GND", PG), ("IN1", SKIP), ("IN2", SKIP), ("IN3", SKIP), ("IN4", SKIP)]),
    ]
    mods = {}
    for ref, name, sub, main in stack_parts:
        m = mod2(ax, ref, name, sub, px, y, pw, "left", main)
        mods[ref] = m
        y = m.y0 - 6
    links = [("D2 (SW-RX)", "U2", "TX"), ("D3 (SW-TX)", "U2", "RX"),
             ("D4", "U5", "IN1"), ("D5", "U5", "IN2"), ("D6", "U5", "IN3"), ("D7", "U5", "IN4"),
             ("D10", "KP1", "R1"), ("D11", "KP1", "R2"), ("D12", "KP1", "R3"), ("D13", "KP1", "R4"),
             ("A0", "KP1", "C1"), ("A1", "KP1", "C2"), ("A2", "KP1", "C3"), ("A3", "KP1", "C4"),
             ("A4 (SDA)", "U3", "SDA"), ("A5 (SCL)", "U3", "SCL")]
    pairs = [(u1.pin[a], mods[r].pin[b]) for a, r, b in links]
    polys, pen = channel_wires(pairs, [166 + 3.4 * i for i in range(len(pairs))])
    assert pen < 1000, "signal wires overlap"
    print("control sheet wire crossings:", pen)
    draw_wires(ax, polys)

    # 12 V jack -> K7805 -> Raspberry Pi 5 V. The same 12 V rail feeds the Uno VIN pin and the relay module.
    jk = header(ax, 292, TOP - 7, "J2", "12 V DC input", [SKIP, PG], "right", jack=True)
    u6 = mod2(ax, "U6", "K7805-2000R3", "Mornsun SMPS 5 V 2 A (Pi supply)", 332, TOP, 34, "right",
              main=[("VOUT", ("p", "+5V PI")), ("GND", PG)], extra=[("VIN", SKIP)])
    draw_wires(ax, [[jk[0], u6.xpin["VIN"]]])
    mx = (jk[0][0] + u6.xpin["VIN"][0]) / 2
    junction(ax, mx, jk[0][1])
    power(ax, (mx, jk[0][1]), "+12V", "up")

    ax.text(8, 168, "ECRT control sheet: Arduino Uno, PZEM TTL side, LCD, keypad, relay inputs, Pi link, DC supply",
            ha="left", va="center", fontsize=9, color=TXT, fontweight="bold")
    notes(ax, 8, 88, [
        "Notes",
        "1. Uno is 5 V logic: the PZEM, LCD and relay module connect directly, with no level shifting.",
        "2. The Uno's USB port is the serial link to the Pi (D0/D1 are reserved for it). A USB A-to-B cable is needed (not on the quote).",
        "3. U2 uses SoftwareSerial on D2/D3 because the hardware UART (D0/D1) is the USB link. Check the PZEM TX level on the bench.",
        "4. The Uno is powered at VIN from the 12 V supply (7 to 12 V). Its 5 V pin feeds U2 and U3 only (about 100 mA).",
        "   Do not feed the 5 V pin from another source. Alternatively plug the 12 V adapter into the Uno's barrel jack.",
        "5. U5 (MD0010) is active-low per its datasheet: drive IN LOW to switch on. A 5 V HIGH switches it off.",
        "6. U6 (K7805, 2 A) powers the Pi only. A Pi 3B+ is rated for 2.5 A, so avoid heavy USB loads.",
        "7. A 12 V DC adapter is needed for J2 and is not on the quote. D8 and D9 are spare.",
        "8. Wires that cross without a dot are not connected. Power rails and GND use power symbols.",
        "9. The quote's Pro Mini, ESP8266 and AMS1117 are not used in this version.",
    ])
    check_overlaps(fig, ax, "schematic_control")
    ksave(fig, "ecrt_schematic_control")


# ================================================== SHEET 2: mains switching (draft)
def schematic_mains():
    """Mains sheet: supply -> QF1 -> L bus / N bus (drawn as wires with junction dots). PZEM voltage terminals and CT on the L conductor
    measure the aggregate. The relay module's NO contacts switch the 230 V coils of KM1-KM4, and each contactor switches one appliance."""
    fig, ax = kcanvas(330, -52, 160, (22, 14.2))
    TOP = 130
    LTOP, NTOP = 138, 141                       # top feed lines of the L and N buses
    XL, XN = 160, 168                           # vertical L and N buses between the relay module and the contactors
    XLL, XNL = 84, 80                           # vertical L and N taps on the left (breaker / PZEM)

    ax.text(8, 154, "ECRT mains and switching sheet (DRAFT: design and install by a qualified electrician)",
            ha="left", va="center", fontsize=9, color=TXT, fontweight="bold")

    j1 = header(ax, 24, TOP, "J1", "230 V AC supply", [SKIP, SKIP], "left")
    q1 = mod2(ax, "QF1", "2P 63 A C-curve", "6 kA breaker", 24, TOP - 20, 30, "right",
              main=[("L OUT", SKIP), ("N OUT", SKIP)], extra=[("L IN", SKIP), ("N IN", SKIP)])
    u2 = mod2(ax, "U2", "PZEM-004T V4", "mains side: L/N sense + CT", 24, q1.y0 - 12, 30, "right",
              main=[("L", SKIP), ("N", SKIP), ("CT A", SKIP), ("CT B", SKIP)])
    ct = header(ax, 24, u2.y0 - 12, "CT1", "100 A split-core CT, clamped on the L conductor", [SKIP, SKIP], "right")

    rel = []
    for i in range(1, 5):
        rel += [(f"COM{i}", SKIP), (f"NO{i}", SKIP), (f"NC{i}", None)]
    u5 = mod2(ax, "U5", "4-ch relay module", "contact side (coil inputs on control sheet)", 110, TOP, 34, "right", rel)

    # contactor stack: pick a gap so no contactor pin row lines up with a relay pin row (keeps the wires apart)
    relay_rows = [p[1] for p in list(u5.pin.values())]
    gap = 6.0
    while True:
        ytops = [TOP - 2 - (26.5 + gap) * k for k in range(4)]
        rows = [yt - 9 - 4 * j for yt in ytops for j in range(4)]
        if all(abs(r - rr) >= 1.0 for r in rows for rr in relay_rows):
            break
        gap += 0.25
    kms = []
    for i in range(1, 5):
        m = mod2(ax, f"KM{i}", "Contactor 25 A, 2xNO", f"channel {i}, 230 V coil", 200, ytops[i - 1], 34, "left",
                 main=[("A1", SKIP), ("A2", SKIP), ("1 (L in)", SKIP), ("3 (N in)", SKIP)],
                 extra=[("2 (L out)", SKIP), ("4 (N out)", SKIP)])
        kms.append(m)
        ld = header(ax, 290, m.top - 7, f"J{i + 2}", f"Load {i} (appliance)", [SKIP, SKIP], "left")
        for k, name in enumerate(("2 (L out)", "4 (N out)")):
            draw_wires(ax, [[m.xpin[name], ld[k]]])

    # supply -> breaker inputs
    yLi, yNi = q1.xpin["L IN"][1], q1.xpin["N IN"][1]
    draw_wires(ax, [[j1[0], (14, j1[0][1]), (14, yLi), q1.xpin["L IN"]]])
    draw_wires(ax, [[j1[1], (10, j1[1][1]), (10, yNi), q1.xpin["N IN"]]])

    # left taps: breaker outputs and PZEM voltage terminals onto the L and N feed lines
    yLo, yNo = q1.pin["L OUT"][1], q1.pin["N OUT"][1]
    yLu, yNu = u2.pin["L"][1], u2.pin["N"][1]
    draw_wires(ax, [[q1.pin["L OUT"], (XLL, yLo)], [u2.pin["L"], (XLL, yLu)], [(XLL, yLu), (XLL, LTOP), (XL, LTOP)]])
    draw_wires(ax, [[q1.pin["N OUT"], (XNL, yNo)], [u2.pin["N"], (XNL, yNu)], [(XNL, yNu), (XNL, NTOP), (XN, NTOP)]])
    for p in ((XLL, yLo), (XLL, yLu), (XNL, yNo), (XNL, yNu)):
        junction(ax, *p)

    # CT leads
    ya, yb = ct[0][1], ct[1][1]
    draw_wires(ax, [[u2.pin["CT A"], (70, u2.pin["CT A"][1]), (70, ya), ct[0]]])
    draw_wires(ax, [[u2.pin["CT B"], (66, u2.pin["CT B"][1]), (66, yb), ct[1]]])

    # right buses: L at XL (relay COM pins and contactor pin 1), N at XN (contactor A2 and pin 3)
    l_pts, n_pts = [], []
    for i in range(1, 5):
        c = u5.pin[f"COM{i}"]
        draw_wires(ax, [[c, (XL, c[1])]])
        l_pts.append(c[1])
        junction(ax, XL, c[1])
        m = kms[i - 1]
        for name, bus, lst in (("1 (L in)", XL, l_pts), ("A2", XN, n_pts), ("3 (N in)", XN, n_pts)):
            t = m.pin[name]
            draw_wires(ax, [[t, (bus, t[1])]])
            lst.append(t[1])
            junction(ax, bus, t[1])
        # relay NO contact -> contactor coil A1 through its own channel
        no, a1 = u5.pin[f"NO{i}"], m.pin["A1"]
        xc = 176 + 4 * (i - 1)
        draw_wires(ax, [[no, (xc, no[1]), (xc, a1[1]), a1]])
    draw_wires(ax, [[(XL, LTOP), (XL, min(l_pts))], [(XN, NTOP), (XN, min(n_pts))]])
    ax.text(XL - 1.5, LTOP + 1.2, "L", ha="right", va="bottom", fontsize=7.5, color=TXT, fontweight="bold")
    ax.text(XN + 1.5, NTOP + 1.2, "N", ha="left", va="bottom", fontsize=7.5, color=TXT, fontweight="bold")

    notes(ax, 24, -12, [
        "Notes",
        "1. DRAFT. Mains wiring, earthing and enclosure: qualified electrician only.",
        "2. The quote lists one contactor. KM2 to KM4 are still needed, one per channel.",
        "3. U5's contacts switch only the 230 V contactor coils. Appliance current never passes through U5.",
        "4. CT1 clamps the live conductor after QF1, so U2 measures all four channels together (aggregate).",
        "5. QF1 (63 A) does not protect 25 A contactors or the loads: add an MCB per channel. Earth bar not drawn.",
        "6. Test the control side first with low-voltage loads (see brief, section 7).",
        "7. Wires that cross without a dot are not connected.",
    ])
    check_overlaps(fig, ax, "schematic_mains")
    ksave(fig, "ecrt_schematic_mains")


if __name__ == "__main__":
    block_diagram()
    schematic_control()
    schematic_mains()
    print("done")
