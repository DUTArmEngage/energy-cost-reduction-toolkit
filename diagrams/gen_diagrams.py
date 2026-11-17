"""ECRT diagrams: block diagram + two Altium-style schematic sheets (control, mains switching).

Run: python3 gen_diagrams.py -> ecrt_block_diagram, ecrt_schematic_control, ecrt_schematic_mains ({png,svg,pdf})
The old UAV version is kept in gen_diagrams_uav_backup.py.
"""
import itertools
import os
import re

import matplotlib
import matplotlib.patches
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- registry for the interactive index.html: every drawn part, pin, net symbol and block carries an id (SVG gid) of the form
# kind--name[--sub]--n, and what was drawn is recorded here so gen_index.py can build the page from the generator itself.
_GID = itertools.count()
REG = {"sheet": None, "parts": {}, "pins": [], "ctx": None}
SHEETS = {}                       # sheet id -> {"parts": {...}, "pins": [...]} (filled by the schematic_* functions)
BLOCKS = {}                       # block key -> label text (filled by block_diagram)


def key(text):
    return re.sub(r"[^A-Za-z0-9+_.]", "_", str(text))


def tag(artist, kind, *names):
    """Give an artist an SVG id: kind--name--...--n (unique)."""
    artist.set_gid("--".join([kind] + [key(n) for n in names] + [str(next(_GID))]))
    return artist


def _snap(ax):
    return len(ax.lines), len(ax.texts), len(ax.patches)


def _tag_new(ax, snap, kind, *names):
    for a in list(ax.lines)[snap[0]:] + list(ax.texts)[snap[1]:] + list(ax.patches)[snap[2]:]:
        tag(a, kind, *names)


def new_registry(sheet):
    REG.update(sheet=sheet, parts={}, pins=[], ctx=None)


def store_registry():
    SHEETS[REG["sheet"]] = {"parts": dict(REG["parts"]), "pins": list(REG["pins"])}

C_SENS, C_WIFI, C_VID, C_EMG, C_STAT, C_PWR, C_GND = (
    "#1a8a1a", "#1f3fd0", "#8a1a9a", "#d01010", "#e08a00", "#c03000", "#222222")
C_NA = "#8a8a8a"


def box(ax, x, y, w, h, text, fs=8, na=False, fc="white", bold=False, ls=None, blk=None):
    ec = C_NA if na else "#222222"
    patch = ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.2",
                                fc="#f0f0f0" if na else fc, ec=ec, lw=1.1,
                                ls=ls or ("--" if na else "-")))
    label = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                    color=C_NA if na else "black", fontweight="bold" if bold else "normal",
                    linespacing=1.25)
    if blk:
        BLOCKS[blk] = text.replace("\n", " ")
        tag(patch, "blk", blk)
        tag(label, "blk", blk)


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
        tag(ax.add_patch(Rectangle((x, self.y0), w, self.h, fc=FILL, ec=SYM, lw=1.8, zorder=3)), "part", ref)
        tag(ax.text(x, y_top + 1.0, ref, ha="left", va="bottom", fontsize=7, color=TXT, zorder=4), "part", ref)
        tag(ax.text(x + w / 2, y_top - 2.6, name, ha="center", va="center", fontsize=7.5,
                    color=TXT, fontweight="bold", zorder=4), "part", ref)
        if sub:
            tag(ax.text(x + w / 2, y_top - 5.4, sub, ha="center", va="center", fontsize=6,
                        color=TXT, zorder=4), "part", ref)
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
                tag(ax.plot([ex, ex + sg * STUB], [py, py], color=SYM, lw=1.7, zorder=2)[0], "pin", ref, p)
                if nums:
                    tag(ax.text(ex + sg * STUB / 2, py + 0.7, str(num), ha="center", va="bottom",
                                fontsize=6.4, color=NUM, zorder=4), "pin", ref, p)
                tag(ax.text(ex - sg * 1, py, p, ha="right" if on_right else "left", va="center",
                            fontsize=7.2, color=TXT, zorder=4), "pin", ref, p)
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
    ref, pin = REG["ctx"] or (None, None)
    snap, net, kind = _snap(ax), None, "nc"
    if spec is None:
        noconnect(ax, tip)
    elif spec[0] == "s":
        return
    elif spec[0] == "p":
        power(ax, tip, spec[1], direction)
        net, kind = spec[1], "power"
    else:
        port(ax, tip, spec[1], direction)
        net, kind = spec[1], "signal"
    if net:
        _tag_new(ax, snap, "net", net)
    if ref:
        REG["pins"].append({"ref": ref, "pin": pin, "pinkey": key(pin), "net": net, "netkey": key(net) if net else None, "kind": kind})


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
    REG["parts"][ref] = {"name": name, "sub": ""}
    tag(ax.add_patch(Rectangle((x, y_top - h), w, h, fc=FILL, ec=SYM, lw=1.5, zorder=3)), "part", ref)
    tag(ax.text(x, y_top + 1.0, ref, ha="left", va="bottom", fontsize=7, color=TXT), "part", ref)
    tag(ax.text(x, y_top - h - 1.0, name, ha="left", va="top", fontsize=6.6, color=TXT), "part", ref)
    if jack:
        tag(ax.add_patch(plt.Circle((x + w / 2, y_top - h / 2), 2.2, fc="none", ec=SYM, lw=1.3, zorder=4)), "part", ref)
        tag(ax.add_patch(plt.Circle((x + w / 2, y_top - h / 2), 0.8, fc=SYM, ec=SYM, zorder=4)), "part", ref)
    tips = []
    for i, spec in enumerate(specs):
        y = y_top - 2.0 - 4.0 * i
        ex = x + w if side == "right" else x
        sg = 1 if side == "right" else -1
        tag(ax.plot([ex, ex + sg * STUB], [y, y], color=SYM, lw=1.7, zorder=2)[0], "pin", ref, str(i + 1))
        if not jack:
            tag(ax.add_patch(plt.Circle((x + w / 2, y), 0.7, fc=SYM, ec=SYM, zorder=4)), "pin", ref, str(i + 1))
        tag(ax.text(ex + sg * STUB / 2, y + 0.7, str(i + 1), ha="center", va="bottom", fontsize=6.4, color=NUM, zorder=4),
            "pin", ref, str(i + 1))
        tip = (ex + sg * STUB, y)
        tips.append(tip)
        REG["ctx"] = (ref, str(i + 1))
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
    REG["parts"][ref] = {"name": name, "sub": sub or ""}
    for p, s in main:
        REG["ctx"] = (ref, p)
        attach(ax, m.pin[p], s, side)
    opp = "left" if side == "right" else "right"
    for p, s in extra:
        REG["ctx"] = (ref, p)
        attach(ax, m.xpin[p], s, opp)
    return m




# =============================================================== BLOCK DIAGRAM
def block_diagram():
    fig, ax = canvas(204, 112, (16.5, 9.2))
    C_MAINS = C_EMG

    # mains path (left column, top to bottom)
    box(ax, 3, 92, 30, 12, "230 V AC supply", blk="supply")
    box(ax, 3, 74, 30, 12, "QF1 2P 63 A\nbreaker", blk="qf1")
    box(ax, 3, 52, 30, 16, "PZEM-004T V4\n+ 100 A split-core CT\n(aggregate meter)", blk="pzem")
    box(ax, 3, 26, 30, 16, "KM1-KM4\ncontactors 25 A, 2xNO", blk="contactors")
    box(ax, 3, 4, 30, 12, "4 appliance channels", blk="loads")
    for ya, yb in ((92, 86), (74, 68), (52, 42), (26, 16)):
        line(ax, [(18, ya), (18, yb)], C_MAINS, arrow=True)

    # controller column
    box(ax, 70, 52, 36, 36, "Arduino Uno R3\nATmega328P, 5 V / 16 MHz\n\nSoftwareSerial (PZEM)\nUSB serial (Pi)\nI2C, GPIO", fs=8, blk="uno")
    box(ax, 70, 94, 36, 12, "1602 I2C LCD +\n4x4 keypad", blk="hmi")
    box(ax, 70, 22, 36, 16, "12 V 4-channel relay module\n(IN1-IN4)", blk="relay")

    # Raspberry Pi side
    box(ax, 125, 78, 38, 24, "Raspberry Pi 3B+\nPython: tariff, cost,\nscheduling, web dashboard,\nSQLite", blk="pi")
    box(ax, 172, 84, 28, 16, "Dashboard\n(browser over Wi-Fi)", blk="dashboard")

    # power chain
    box(ax, 108, 4, 28, 14, "12 V DC supply\n(Uno VIN, relays;\nnot on quote)", blk="psu12")
    box(ax, 142, 4, 28, 14, "K7805 SMPS\n5 V 2 A (Pi)", blk="k7805")
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


# ================================================== SHEET 1: low-voltage control
def schematic_control():
    """Control sheet: Arduino Uno, PZEM TTL side, LCD, keypad, relay module inputs, USB link to the Pi, 12 V supply and the Pi's 5 V.
    Signals between blocks are net-name ports (ports with the same name are connected); the rails and ground use power symbols.
    Pin allocation: D2/D3 SoftwareSerial to PZEM (D0/D1 are the USB serial link), D4-D7 relays, D10-D13 + A0-A3 keypad (4 rows,
    4 columns; the last two columns are crossed, see note 10), A4/A5 I2C LCD. The Uno is 5 V logic, so every module connects directly."""
    fig, ax = kcanvas(372, -8, 172, (24, 11.9))
    new_registry("control")
    TOP = 150

    mod2(ax, "U8", "Raspberry Pi 3B+", "Python, web dashboard, Wi-Fi", 36, TOP, 30, "right",
         main=[("USB", N("USB_SER"))], extra=[("PWR", ("p", "+5V PI"))])

    mod2(ax, "U1", "Arduino Uno R3", "ATmega328P, 5 V / 16 MHz", 116, TOP, 34, "right",
         main=[("D2 (SW-RX)", N("PZEM_TX")), ("D3 (SW-TX)", N("PZEM_RX")),
               ("D4", N("RLY_IN1")), ("D5", N("RLY_IN2")), ("D6", N("RLY_IN3")), ("D7", N("RLY_IN4")),
               ("D8", None), ("D9", None),
               ("D10", N("KP_R1")), ("D11", N("KP_R2")), ("D12", N("KP_R3")), ("D13", N("KP_R4")),
               ("A0", N("KP_C1")), ("A1", N("KP_C2")), ("A2", N("KP_C4")), ("A3", N("KP_C3")),
               ("A4 (SDA)", N("SDA")), ("A5 (SCL)", N("SCL"))],
         extra=[("USB-B", N("USB_SER")), ("VIN", P12), ("5V", P5), ("GND", PG), ("3V3", None), ("IOREF", None),
                ("RESET", None), ("AREF", None), ("D0 (RX)", None), ("D1 (TX)", None)])

    # peripherals, pins face the Uno
    px, pw, y = 210, 34, TOP
    stack_parts = [
        ("U2", "PZEM-004T V4 (TTL side)", "5 V TTL, 9600 baud",
         [("5V", P5), ("RX", N("PZEM_RX")), ("TX", N("PZEM_TX")), ("GND", PG)]),
        ("U3", "LCD 1602 + I2C", "backpack, 5 V, addr 0x27 (typ.)",
         [("GND", PG), ("VCC", P5), ("SDA", N("SDA")), ("SCL", N("SCL"))]),
        ("KP1", "4x4 keypad", "thin-film matrix",
         [("R1", N("KP_R1")), ("R2", N("KP_R2")), ("R3", N("KP_R3")), ("R4", N("KP_R4")),
          ("C1", N("KP_C1")), ("C2", N("KP_C2")), ("C4", N("KP_C4")), ("C3", N("KP_C3"))]),
        ("U5", "4-ch relay module", "12 V coils, control side",
         [("VCC", P12), ("GND", PG), ("IN1", N("RLY_IN1")), ("IN2", N("RLY_IN2")),
          ("IN3", N("RLY_IN3")), ("IN4", N("RLY_IN4"))]),
    ]
    for ref, name, sub, main in stack_parts:
        m = mod2(ax, ref, name, sub, px, y, pw, "left", main)
        y = m.y0 - 6

    # 12 V jack -> K7805 -> Raspberry Pi 5 V. The same 12 V rail feeds the Uno VIN pin and the relay module.
    header(ax, 272, TOP - 7, "J2", "12 V DC input", [P12, PG], "right", jack=True)
    mod2(ax, "U6", "K7805-2000R3", "Mornsun SMPS 5 V 2 A (Pi supply)", 312, TOP, 34, "right",
         main=[("VOUT", ("p", "+5V PI")), ("GND", PG)], extra=[("VIN", P12)])

    ax.text(8, 168, "ECRT control sheet: Arduino Uno, PZEM TTL side, LCD, keypad, relay inputs, Pi link, DC supply",
            ha="left", va="center", fontsize=9, color=TXT, fontweight="bold")
    check_overlaps(fig, ax, "schematic_control")
    store_registry()
    ksave(fig, "ecrt_schematic_control")


# ================================================== SHEET 2: mains switching (draft)
def schematic_mains():
    """Mains sheet: supply -> QF1 -> L_BUS / N_BUS. PZEM voltage terminals and CT on L_BUS measure the aggregate. The relay module's
    NO contacts switch the 230 V coils of KM1-KM4, and each contactor switches one appliance channel.
    Connections are net-name ports (ports with the same name are connected)."""
    fig, ax = kcanvas(330, -20, 150, (22, 11.4))
    new_registry("mains")
    TOP = 130

    ax.text(8, 144, "ECRT mains and switching sheet (DRAFT: design and install by a qualified electrician)",
            ha="left", va="center", fontsize=9, color=TXT, fontweight="bold")

    header(ax, 24, TOP, "J1", "230 V AC supply", [N("L_SUP"), N("N_SUP")], "right")
    q1 = mod2(ax, "QF1", "2P 63 A C-curve", "6 kA breaker", 24, TOP - 20, 30, "right",
              main=[("L OUT", N("L_BUS")), ("N OUT", N("N_BUS"))], extra=[("L IN", N("L_SUP")), ("N IN", N("N_SUP"))])
    u2 = mod2(ax, "U2", "PZEM-004T V4", "mains side: L/N sense + CT", 24, q1.y0 - 12, 30, "right",
              main=[("L", N("L_BUS")), ("N", N("N_BUS")), ("CT A", N("CT_A")), ("CT B", N("CT_B"))])
    header(ax, 24, u2.y0 - 12, "CT1", "100 A split-core CT, clamped on L_BUS", [N("CT_A"), N("CT_B")], "right")

    rel = []
    for i in range(1, 5):
        rel += [(f"COM{i}", N("L_BUS")), (f"NO{i}", N(f"KM{i}_A1")), (f"NC{i}", None)]
    mod2(ax, "U5", "4-ch relay module", "contact side (coil inputs on control sheet)", 110, TOP, 34, "right", rel)

    y = TOP
    for i in range(1, 5):
        m = mod2(ax, f"KM{i}", "Contactor 25 A, 2xNO", f"channel {i}, 230 V coil", 200, y, 34, "left",
                 main=[("A1", N(f"KM{i}_A1")), ("A2", N("N_BUS")), ("1 (L in)", N("L_BUS")), ("3 (N in)", N("N_BUS"))],
                 extra=[("2 (L out)", N(f"LOAD{i}_L")), ("4 (N out)", N(f"LOAD{i}_N"))])
        header(ax, 290, m.top - 7, f"J{i + 2}", f"Load {i} (appliance)", [N(f"LOAD{i}_L"), N(f"LOAD{i}_N")], "left")
        y = m.y0 - 6

    check_overlaps(fig, ax, "schematic_mains")
    store_registry()
    ksave(fig, "ecrt_schematic_mains")


if __name__ == "__main__":
    block_diagram()
    schematic_control()
    schematic_mains()
    print("done")
