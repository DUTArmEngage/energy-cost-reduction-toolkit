#!/usr/bin/env python3
"""ECRT STRIPBOARD MOTHERBOARD (low-voltage side only). The copper strips run across the page along the number axis (1..29):
every LETTERED ROW is one strip, 29 holes long (39 strips: A..AM). Parts stand upright so each pin sits on its own strip, the strips
are cut where two different nets would meet, and wire jumpers join what the strips cannot.
Mains parts (QF1, contactors, PZEM mains side, relay contacts) are NOT on this board: see ecrt_schematic_mains.

Board: a 7.5 x 10 cm piece of the 10 x 30 cm board, assumed 2.54 mm pitch = 29 x 39 holes (39 strips of 29 holes).
Writes next to this script: stripboard.png / .pdf (component side + copper side, cut and jumper lists)
and stripboard_1to1.pdf (true size, 2 pages).

How it is built (all checked before anything is drawn):
  * Cuts are placed automatically between any two pins of different nets that share a strip (unused pins count as their own net).
  * Each strip piece then carries one net. Nets that end up on several pieces are joined by insulated jumper wires, routed on the
    hole grid; wires of different nets only cross straight over each other and never touch a foreign pin or a cut.
  * The check proves: no shorts, no opens, unused pins isolated, no jumper over a pin hole.

ASSUMPTIONS to confirm (edit the tables and rerun):
  - Strips run along the numbers (each letter row is one strip). If yours run the other way, tell me.
  - Pro Mini: two 1x12 columns 6 holes apart, upright (FTDI end at the top). A4/A5 are NOT socketed: two flying leads
    go from the A4/A5 pads to the two marked holes. Check the pin order against your board's silkscreen.
  - Module header orders (PZEM, LCD, keypad, relay board) are the usual ones: check each against the real part.
  - AMS1117-3.3 is drawn as a 3-pin module (VIN, GND, VOUT). A bare SOT-223 chip needs a breakout board.
"""
import heapq
import itertools
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
PITCH_MM = 2.54
W, H = 29, 39                  # display: 29 holes across (numbers), 39 rows down (letters A..AM)
NS, SL = H, W                  # strips run along the numbers: 39 strips (one per letter), 29 holes long


def rname(y):
    return chr(65 + y) if y < 26 else "A" + chr(65 + y - 26)


def hname(x, y):
    return f"{rname(y)}{x + 1}"


# ------------------------------------------------------------------ parts
PARTS = []


def add(ref, label, pins, lab_xy=None, body=None, desc=None, leads=None):
    PARTS.append(dict(ref=ref, label=label, pins=pins, lab_xy=lab_xy, body=body, desc=desc or label, leads=leads or []))


X0, Y0 = 11, 14                # Pro Mini upright: left pin column x, first pin row; right column is 6 holes further
LEFT = [("TXO", None), ("RXI", None), ("RST", None), ("GND", "G"), ("D2", "PZEM_TX"), ("D3", "PZEM_RX"), ("D4", "RLY_IN1"),
        ("D5", "RLY_IN2"), ("D6", "RLY_IN3"), ("D7", "RLY_IN4"), ("D8", None), ("D9", None)]
RIGHT = [("RAW", None), ("GND", "G"), ("RST", None), ("VCC", "3V3"), ("A3", "KP_C4"), ("A2", "KP_C3"), ("A1", "KP_C2"),
         ("A0", "KP_C1"), ("D13", "KP_R4"), ("D12", "KP_R3"), ("D11", "KP_R2"), ("D10", "KP_R1")]
add("U1", "Arduino Pro Mini\n3.3 V / 8 MHz",
    [(X0, Y0 + i, n, net, "l") for i, (n, net) in enumerate(LEFT)] + [(X0 + 6, Y0 + i, n, net, "r") for i, (n, net) in enumerate(RIGHT)],
    lab_xy=(X0 + 3, Y0 + 6), body=(X0 - 0.6, Y0 - 0.6, X0 + 6.6, Y0 + 11.6), desc="U1 Arduino Pro Mini (2 x 1x12, upright)")
LEAD_A4, LEAD_A5 = (21, 14), (21, 15)
add("U1X", "A4/A5 leads", [(LEAD_A4[0], LEAD_A4[1], "A4", "SDA", "l"), (LEAD_A5[0], LEAD_A5[1], "A5", "SCL", "l")],
    leads=[((X0 + 5, Y0 + 4), LEAD_A4), ((X0 + 5, Y0 + 5), LEAD_A5)], desc="U1 A4/A5: flying leads from the pads to these holes")

# rails: horizontal strips at the top (rows B..F): 12 V, GND, 5 V, GND, 3.3 V; regulator and capacitor pins sit on them
add("J2", "J2 12 V in", [(2, 1, "+12V", "12V", "r"), (2, 2, "GND", "G", "r")], lab_xy=(1, -0.2), desc="J2 12 V in (2-pin 2.54 mm header)")
add("U6", "U6 K7805", [(6, 1, "VIN", "12V", "r"), (6, 2, "GND", "G", "r"), (6, 3, "VOUT", "5V", "r")], lab_xy=(5, -0.2),
    desc="U6 K7805-2000R3 5 V SMPS (SIP-3)")
add("U7", "U7 AMS1117", [(11, 3, "VIN", "5V", "r"), (11, 4, "GND", "G", "r"), (11, 5, "VOUT", "3V3", "r")], lab_xy=(10, 1.8),
    desc="U7 AMS1117-3.3 (module, SIP-3)")
add("C1", "C1 10uF", [(17, 3, "+", "5V", "r"), (17, 4, "-", "G", "r")], lab_xy=(16, 1.8), desc="C1 10 uF (5 V)")
add("C2", "C2 10uF", [(21, 4, "-", "G", "r"), (21, 5, "+", "3V3", "r")], lab_xy=(20, 2.8), desc="C2 10 uF (3.3 V)")
add("C4", "C4 100nF", [(25, 4, "-", "G", "r"), (25, 5, "", "3V3", "r")], lab_xy=(24, 2.8), desc="C4 100 nF (3.3 V, near the Pro Mini)")
add("J6", "J6 LCD", [(27, 12, "GND", "G", "l"), (27, 13, "VCC", "5V", "l"), (27, 14, "SDA", "SDA", "l"), (27, 15, "SCL", "SCL", "l")],
    lab_xy=(24, 10.2), desc="J6 LCD 1602 I2C (1x4)")
# left side: relay module with IN1..IN4 on the same rows as D4..D7, PZEM with GND/TX/RX on the rows of GND/D2/D3
add("J4", "J4 relay", [(2, 18, "12V", "12V", "l"), (2, 19, "GND", "G", "l"), (2, 20, "IN1", "RLY_IN1", "l"), (2, 21, "IN2", "RLY_IN2", "l"),
                       (2, 22, "IN3", "RLY_IN3", "l"), (2, 23, "IN4", "RLY_IN4", "l")], lab_xy=(0.2, 16.2), desc="J4 relay module (1x6)")
add("J3", "J3 PZEM", [(6, 17, "GND", "G", "r"), (6, 18, "TX", "PZEM_TX", "r"), (6, 19, "RX", "PZEM_RX", "r"), (6, 20, "5V", "5V", "r")],
    lab_xy=(5, 15.2), desc="J3 PZEM TTL (1x4, pin 1 at the bottom)")
# right side: keypad pins on the same rows as A3..D10
add("J5", "J5 keypad",
    [(25, 18 + i, n, "KP_" + n, "r") for i, n in enumerate(["C4", "C3", "C2", "C1", "R4", "R3", "R2", "R1"])], lab_xy=(22, 16.4),
    desc="J5 keypad 4x4 (1x8, pin 1 at the bottom)")

POWER_ORDER = ["12V", "5V", "3V3", "G"]
PALETTE = ["#1f5fbf", "#e07b00", "#7b3fbf", "#c2409b", "#0f9db0", "#2f8f2f", "#2b3a8f", "#9a7d00", "#b5179e", "#00897b",
           "#3949ab", "#16a085", "#c0392b", "#5d4037", "#8c564b"]
COLORS = {"G": "#1b1b1b", "3V3": "#d62728", "5V": "#e65100", "12V": "#7b3f00"}
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ------------------------------------------------------------------ model
# Internal coordinates are (u, v): u = strip index = display row (y), v = position along the strip = display column (x).
def to_int(x, y):
    return (y, x)


def hn(u, v):
    return hname(v, u)


def key_of(u, v, net):
    return net if net else ("NC", u, v)


def build():
    pin_at, body_cells = {}, set()
    for p in PARTS:
        for (x, y, pn, net, _s) in p["pins"]:
            c = to_int(x, y)
            if c in pin_at:
                sys.exit(f"two pins on one hole {hname(x, y)}")
            if not (0 <= x < W and 0 <= y < H):
                sys.exit(f"{p['ref']}.{pn} outside the board")
            pin_at[c] = (p["ref"], pn, net)
        if p["body"]:
            bx0, by0, bx1, by1 = p["body"]
            body_cells |= {to_int(x, y) for x in range(W) for y in range(H) if bx0 <= x <= bx1 and by0 <= y <= by1}
    # cuts: between consecutive pins of one strip that carry different nets
    cuts, strips = set(), {}
    for (u, v), (_r, _p, net) in pin_at.items():
        strips.setdefault(u, []).append((v, key_of(u, v, net)))
    for u, lst in strips.items():
        lst.sort()
        for (va, na), (vb, nb) in zip(lst, lst[1:]):
            if na != nb:
                cand = [v for v in range(va + 1, vb) if (u, v) not in pin_at]
                if not cand:
                    sys.exit(f"strip {rname(u)}: pins at {va + 1} and {vb + 1} are different nets with no hole between to cut")
                mid = (va + vb) / 2
                cuts.add((u, min(cand, key=lambda t: (abs(t - mid), t))))
    return pin_at, body_cells, cuts


def seg_of(cbs, u, v):
    return (u, sum(1 for c in cbs.get(u, []) if c < v))


def seg_holes(cbs, seg):
    u, k = seg
    cs = sorted(cbs.get(u, []))
    lo = cs[k - 1] + 1 if k > 0 else 0
    hi = cs[k] - 1 if k < len(cs) else SL - 1
    return [(u, v) for v in range(lo, hi + 1)]


def segments(pin_at, cuts):
    cbs = {}
    for u, v in cuts:
        cbs.setdefault(u, []).append(v)
    seg_net, net_segs = {}, {}
    for (u, v), (r, pn, net) in pin_at.items():
        sg = seg_of(cbs, u, v)
        k = key_of(u, v, net)
        if sg in seg_net and seg_net[sg] != k:
            sys.exit(f"strip piece {hn(u, v)} joins {seg_net[sg]} and {k}")
        seg_net[sg] = k
    for sg, k in seg_net.items():
        net_segs.setdefault(k, set()).add(sg)
    return cbs, seg_net, net_segs


# ------------------------------------------------------------------ jumper router
def axis_of(d):
    return "h" if d in (0, 1) else "v"


def needed(din, dout):
    return [axis_of(din)] if din == dout else ["h", "v"]


def mark(path, net, slots):
    for i in range(1, len(path) - 1):
        a, b, c = path[i - 1], path[i], path[i + 1]
        din = DIRS.index((b[0] - a[0], b[1] - a[1]))
        dout = DIRS.index((c[0] - b[0], c[1] - b[1]))
        for ax_ in needed(din, dout):
            slots[(b, ax_)] = net


def dijkstra(srcs, targets, net, solid, ends, slots):
    pq, best, prev = [], {}, {}
    for s in srcs:
        best[(s[0], s[1], 4)] = 0
        heapq.heappush(pq, (0, s[0], s[1], 4))
    while pq:
        c, x, y, d = heapq.heappop(pq)
        if best.get((x, y, d), 1e18) < c:
            continue
        if d != 4 and (x, y) in targets:
            path, st = [], (x, y, d)
            while True:
                path.append((st[0], st[1]))
                if st not in prev:
                    break
                st = prev[st]
            return path[::-1]
        for nd, (dx, dy) in enumerate(DIRS):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < NS and 0 <= ny < SL):
                continue
            if d != 4:
                if any(slots.get(((x, y), ax_), net) != net for ax_ in needed(d, nd)):
                    continue
            if (nx, ny) not in targets:
                if (nx, ny) in solid or ends.get((nx, ny), net) != net:
                    continue
            cross = 6 if any(slots.get(((nx, ny), a_), net) != net for a_ in ("h", "v")) else 0
            nc = c + 1 + (0 if d in (4, nd) else 3) + cross
            if nc < best.get((nx, ny, nd), 1e18):
                best[(nx, ny, nd)] = nc
                prev[(nx, ny, nd)] = (x, y, d)
                heapq.heappush(pq, (nc, nx, ny, nd))
    return None


def attempt(pin_at, body_cells, cuts, cbs, seg_net, net_segs, order):
    solid = set(pin_at) | body_cells | cuts
    ends, slots, wires = {}, {}, []

    def free_holes(sg, net):
        return {h for h in seg_holes(cbs, sg) if h not in solid and ends.get(h, net) == net
                and all(slots.get((h, a_), net) == net for a_ in ("h", "v"))}

    for net in order:
        sgs = sorted(net_segs[net])
        conn, rest = {sgs[0]}, set(sgs[1:])
        while rest:
            srcs = set().union(*(free_holes(sg, net) for sg in conn))
            tg = set().union(*(free_holes(sg, net) for sg in rest))
            path = dijkstra(srcs, tg, net, solid, ends, slots)
            if path is None:
                return None, net
            ends[path[0]] = ends[path[-1]] = net
            mark(path, net, slots)
            wires.append(dict(id=f"W{len(wires) + 1:02d}", net=net, path=path))
            end_seg = seg_of(cbs, *path[-1])
            conn.add(end_seg)
            rest.discard(end_seg)
    return wires, None


def route(pin_at, body_cells, cuts, cbs, seg_net, net_segs):
    def spread(n):
        sgs = sorted(net_segs[n])
        return min(abs(a[0] - b[0]) for a in sgs for b in sgs if a != b)

    nets = [n for n in net_segs if not isinstance(n, tuple) and len(net_segs[n]) > 1]
    signals = sorted([n for n in nets if n not in POWER_ORDER], key=spread)
    power = [n for n in POWER_ORDER if n in nets]
    stuck = set()
    for perm in itertools.permutations(power):
        for order in (signals + list(perm), list(perm) + signals):
            wires, bad = attempt(pin_at, body_cells, cuts, cbs, seg_net, net_segs, order)
            if wires is not None:
                return wires
            stuck.add(bad)
    sys.exit(f"router: no net order worked (stuck on {sorted(stuck)}). Move parts and rerun.")


def check(pin_at, cuts, cbs, seg_net, net_segs, wires):
    parent = {sg: sg for sg in seg_net}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    slots, crossings = {}, set()
    for w in wires:
        pth = w["path"]
        for a, b in zip(pth, pth[1:]):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
                sys.exit(f"check: {w['id']} has a non-adjacent step")
        for end in (pth[0], pth[-1]):
            sg = seg_of(cbs, *end)
            if end in pin_at or end in cuts or seg_net.get(sg) != w["net"]:
                sys.exit(f"check: {w['id']} ends on {hn(*end)}, which is not a free {w['net']} strip hole")
        for c in pth[1:-1]:
            if c in pin_at:
                sys.exit(f"check: {w['id']} runs over pin hole {hn(*c)}")
        for i in range(1, len(pth) - 1):
            a, b, c = pth[i - 1], pth[i], pth[i + 1]
            din = DIRS.index((b[0] - a[0], b[1] - a[1]))
            dout = DIRS.index((c[0] - b[0], c[1] - b[1]))
            for ax_ in needed(din, dout):
                o = slots.setdefault((b, ax_), w["net"])
                if o != w["net"]:
                    sys.exit(f"check: hole {hn(*b)} {ax_}-line shared by {o} and {w['net']}")
        parent[find(seg_of(cbs, *pth[0]))] = find(seg_of(cbs, *pth[-1]))
    for (c, _a), _n in slots.items():
        if (c, "h") in slots and (c, "v") in slots and slots[(c, "h")] != slots[(c, "v")]:
            crossings.add(c)
    roots = {}
    for k, sgs in net_segs.items():
        if len({find(sg) for sg in sgs}) != 1:
            sys.exit(f"check: net {k} is not fully connected")
        roots.setdefault(find(next(iter(sgs))), []).append(k)
    for r, ks in roots.items():
        if len(ks) > 1:
            sys.exit(f"check: nets {ks} are joined (short)")
    print(f"layout check OK: {len([k for k in net_segs if not isinstance(k, tuple)])} nets, {len(cuts)} cuts, {len(wires)} jumpers, "
          f"{len(crossings)} insulated crossings, no shorts, no opens, unused pins isolated")
    return sorted(crossings)


def corners(path):
    pts = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = path[i - 1], path[i], path[i + 1]
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            pts.append(b)
    pts.append(path[-1])
    return pts


# ------------------------------------------------------------------ drawing (display coordinates: x = number, y = letter row)
def add_view(fig, left_in, bottom_in, s, fig_w, fig_h):
    w_in, h_in = (W + 2) * s / 72, (H + 1.1) * s / 72
    ax = fig.add_axes([left_in / fig_w, bottom_in / fig_h, w_in / fig_w, h_in / fig_h])
    ax.set_xlim(-2.0, W)
    ax.set_ylim(H - 0.5, -1.6)
    ax.axis("off")
    return ax


def draw_view(ax, s, mirrored, wires_d, cuts_d, strip_segs, colors, detail=True):
    X = (lambda x: W - 1 - x) if mirrored else (lambda x: x)
    swap = {"l": "r", "r": "l", "u": "u", "d": "d"} if mirrored else {"l": "l", "r": "r", "u": "u", "d": "d"}
    ax.add_patch(Rectangle((-0.5, -0.5), W, H, fc="#e3d3a6" if not mirrored else "#cfa36a", ec="#5a4a20", lw=s * 0.1, zorder=0))
    for (y, xa, xb, net) in strip_segs:                      # strip pieces: faint on the component side, bold copper on the copper side
        col = colors[net] if net and not isinstance(net, tuple) else "#8a6a3a"
        x0, x1 = sorted((X(xa) - (0.5 if not mirrored else -0.5) * 0, X(xb)))
        lo, hi = min(X(xa), X(xb)) - 0.5, max(X(xa), X(xb)) + 0.5
        if mirrored:
            ax.plot([lo, hi], [y, y], color="#b87333", lw=s * 0.5, solid_capstyle="butt", zorder=1, alpha=0.9)
            if net and not isinstance(net, tuple):
                ax.plot([lo, hi], [y, y], color=col, lw=s * 0.16, solid_capstyle="butt", zorder=2)
        else:
            ax.plot([lo, hi], [y, y], color=col, lw=s * 0.05, ls=(0, (2, 3)), solid_capstyle="butt", zorder=1, alpha=0.5)
    xs = [X(x) for x in range(W) for _ in range(H)]
    ys = [y for _ in range(W) for y in range(H)]
    ax.scatter(xs, ys, s=(s * 0.26) ** 2, c="#3a2e12", linewidths=0, zorder=3)
    for x in range(W):
        ax.text(X(x), -1.0, str(x + 1), ha="center", va="center", fontsize=s * 0.4, color="#444")
    for y in range(H):
        ax.text(-1.2, y, rname(y), ha="center", va="center", fontsize=s * 0.42, color="#444")
    fs = s * 0.42
    for p in PARTS:
        xs_ = [q[0] for q in p["pins"]]
        ys_ = [q[1] for q in p["pins"]]
        x0, x1, y0, y1 = (p["body"][0], p["body"][2], p["body"][1], p["body"][3]) if p["body"] else \
            (min(xs_) - 0.5, max(xs_) + 0.5, min(ys_) - 0.5, max(ys_) + 0.5)
        if p["ref"] == "U1X":
            for (pad, land) in p["leads"]:
                ax.plot([X(pad[0]), X(land[0])], [pad[1], land[1]], color="#c00000", lw=s * 0.1, ls=(0, (3, 2)), zorder=6)
        else:
            bx0, bx1 = sorted((X(x0), X(x1)))
            ax.add_patch(Rectangle((bx0, y0), bx1 - bx0, y1 - y0, fc="white" if not mirrored else "none", alpha=0.45 if not mirrored else 1,
                                   ec="#1a3a6e", lw=s * 0.08, ls="-" if not mirrored else (0, (3, 2)), zorder=4))
        if p["lab_xy"] and detail:
            lx, ly = p["lab_xy"]
            ax.text(X(lx), ly, p["label"], ha="center" if p["ref"] == "U1" else ("right" if mirrored else "left"),
                    va="center" if p["ref"] == "U1" else "bottom", fontsize=fs * 1.05, color="#10284f", zorder=9, linespacing=1.1)
        for (x, y, pn, net, side) in p["pins"]:
            ax.add_patch(Circle((X(x), y), 0.4, fc=colors[net] if net else "white", ec="black", lw=s * 0.06, zorder=7))
            if not net:
                ax.plot([X(x) - 0.22, X(x) + 0.22], [y - 0.22, y + 0.22], color="#c00000", lw=s * 0.08, zorder=8)
                ax.plot([X(x) - 0.22, X(x) + 0.22], [y + 0.22, y - 0.22], color="#c00000", lw=s * 0.08, zorder=8)
            if detail and pn:
                sd = swap[side]
                if sd == "l":
                    ax.text(X(x) - 0.6, y, pn, ha="right", va="center", fontsize=fs, color="#10284f", zorder=9)
                elif sd == "r":
                    ax.text(X(x) + 0.6, y, pn, ha="left", va="center", fontsize=fs, color="#10284f", zorder=9)
                elif sd == "u":
                    ax.text(X(x), y - 0.6, pn, ha="center", va="bottom", rotation=90, fontsize=fs * 0.9, color="#10284f", zorder=9)
                else:
                    ax.text(X(x), y + 0.6, pn, ha="center", va="top", rotation=90, fontsize=fs * 0.9, color="#10284f", zorder=9)
    for (x, y) in cuts_d:
        if mirrored:
            ax.add_patch(Rectangle((X(x) - 0.34, y - 0.34), 0.68, 0.68, fc="#e3d3a6", ec="#c00000", lw=s * 0.09, zorder=8))
            ax.plot([X(x) - 0.3, X(x) + 0.3], [y - 0.3, y + 0.3], color="#c00000", lw=s * 0.09, zorder=9)
            ax.plot([X(x) - 0.3, X(x) + 0.3], [y + 0.3, y - 0.3], color="#c00000", lw=s * 0.09, zorder=9)
        else:
            ax.plot([X(x)], [y], marker="x", ms=s * 0.3, color="#c00000", mew=s * 0.08, zorder=8)
    for w in wires_d:
        pts = corners(w["path"])
        if not mirrored:
            ax.plot([X(a[0]) for a in pts], [a[1] for a in pts], color=colors[w["net"]], lw=s * 0.2, solid_capstyle="round",
                    solid_joinstyle="round", zorder=5, alpha=0.95)
            mid = w["path"][len(w["path"]) // 2]
            if detail:
                ax.text(X(mid[0]), mid[1], w["id"][1:], ha="center", va="center", fontsize=s * 0.34, color="white", zorder=10,
                        bbox=dict(boxstyle="round,pad=0.08", fc=colors[w["net"]], ec="none"))
        for e in (w["path"][0], w["path"][-1]):
            ax.add_patch(Circle((X(e[0]), e[1]), 0.36, fc="white" if mirrored else colors[w["net"]], ec=colors[w["net"]], lw=s * 0.08, zorder=6))


def main():
    pin_at, body_cells, cuts = build()
    cbs, seg_net, net_segs = segments(pin_at, cuts)
    wires = route(pin_at, body_cells, cuts, cbs, seg_net, net_segs)
    crossings_i = check(pin_at, cuts, cbs, seg_net, net_segs, wires)
    # back to display coordinates (x = v, y = u)
    wires_d = [dict(id=w["id"], net=w["net"], path=[(v, u) for (u, v) in w["path"]]) for w in wires]
    cuts_d = sorted((v, u) for (u, v) in cuts)
    crossings = [(v, u) for (u, v) in crossings_i]
    strip_segs = []
    for sg in sorted({(u, k) for u in range(NS) for k in range(len(cbs.get(u, [])) + 1)}):
        hs = seg_holes(cbs, sg)
        if hs:
            strip_segs.append((sg[0], hs[0][1], hs[-1][1], seg_net.get(sg)))
    nets = sorted({k for k in net_segs if not isinstance(k, tuple)})
    colors, k = dict(COLORS), 0
    for n in nets:
        if n not in colors:
            colors[n] = PALETTE[k % len(PALETTE)]
            k += 1

    by_row = {}
    for x, y in cuts_d:
        by_row.setdefault(y, []).append(str(x + 1))
    cut_lines = [f"{len(cuts)} cuts (copper side, at the hole)", ""] + [f"strip {rname(y):>2}: {', '.join(v)}" for y, v in sorted(by_row.items())]
    wire_lines = [f"{len(wires)} jumpers (insulated wire, component side)", ""]
    total = 0
    for w in wires_d:
        n = len(w["path"]) - 1
        total += n
        wire_lines.append(f"{w['id']} {w['net']:<8} {hname(*w['path'][0]):>4} > {hname(*w['path'][-1]):<4} {n:>3} holes")
    wire_lines += ["", f"total {total} holes = {total * PITCH_MM / 10:.0f} cm of wire", "(add 1 cm per jumper for the ends)"]
    place = ["Parts (component side), first pin hole", ""]
    for p in PARTS:
        c = min(p["pins"], key=lambda q: (q[1], q[0]))
        place.append(f"{p['ref']:<4} {p['desc'][:40]:<40} {hname(c[0], c[1])}")
    notes = [
        "Notes", "",
        "Board: 7.5 x 10 cm piece (a quarter of the 10 x 30 cm).",
        "Strips run ACROSS the page: each LETTER ROW is one strip",
        "(1 to 29). Cuts are at the X marks, on the copper side.",
        "Order: 1 cut the strips (drill or knife at each X),",
        "2 check every cut with a meter, 3 sockets and headers,",
        "4 jumpers, 5 meter every net, 6 power test.",
        f"Use INSULATED wire: {len(crossings)} jumpers cross over others.",
        f"Power rails are strips: {rname(1)} = 12 V, {rname(2)} and {rname(4)} = GND,",
        f"{rname(3)} = 5 V, {rname(5)} = 3.3 V. U6, U7 and the caps sit on them.",
        "Pro Mini stands upright: both pin columns go in sockets,",
        f"and every strip under it is cut between the columns (column {X0 + 4}).",
        f"A4/A5: two flying leads from the pads to {hname(*LEAD_A4)} and {hname(*LEAD_A5)} (red).",
        "USB-UART (3.3 V): plug onto an upward 1x6 male header on",
        "the Pro Mini's FTDI pads: it carries TX, RX, DTR.",
        "J4: relay module MD0010 is active-low. CHECK its header.",
        "Keypad and relay inputs reach the Pro Mini through the strips.",
        "Power test: 12 V at J2, nothing plugged in: check 5 V and",
        "3.3 V first, only then fit the Pro Mini.",
    ]

    s = 26.0
    w_in, h_in = (W + 2) * s / 72, (H + 1.1) * s / 72
    text_h = 5.6
    fig_w, fig_h = 0.3 + w_in + 0.5 + w_in + 0.3, 0.3 + h_in + 0.5 + text_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax1 = add_view(fig, 0.3, text_h + 0.3, s, fig_w, fig_h)
    draw_view(ax1, s, False, wires_d, cuts_d, strip_segs, colors)
    ax1.set_title("Stripboard 7.5 x 10 cm, strips run across (1 to 29): component side", loc="left", fontsize=s * 0.6, pad=2)
    ax2 = add_view(fig, 0.3 + w_in + 0.5, text_h + 0.3, s, fig_w, fig_h)
    draw_view(ax2, s, True, wires_d, cuts_d, strip_segs, colors)
    ax2.set_title("Copper side (flipped left to right): strips, cuts (red X), jumper joints (rings)", loc="left", fontsize=s * 0.6, pad=2)
    cols = [(0.01, cut_lines), (0.17, wire_lines), (0.36, place), (0.70, notes)]
    for x, lines in cols:
        ax = fig.add_axes([x, 0.005, 0.2 if x < 0.3 else 0.32, (text_h - 0.1) / fig_h])
        ax.axis("off")
        ax.text(0, 1, "\n".join(lines), ha="left", va="top", family="DejaVu Sans Mono", fontsize=7.2, linespacing=1.3)
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"stripboard.{ext}", dpi=110)
    plt.close(fig)

    s1 = 72 * PITCH_MM / 25.4
    with PdfPages(HERE / "stripboard_1to1.pdf") as pdf:
        for mirrored in (False, True):
            fw, fh = (W + 2) * 0.1 + 0.6, (H + 1.1) * 0.1 + 1.1
            fig = plt.figure(figsize=(fw, fh))
            ax = add_view(fig, 0.3, 0.7, s1, fw, fh)
            draw_view(ax, s1, mirrored, wires_d, cuts_d, strip_segs, colors, detail=True)
            ax.set_title("copper side (mirrored): cuts and joints" if mirrored else "component side: jumpers", loc="left", fontsize=9)
            bar = fig.add_axes([0.3 / fw, 0.35 / fh, 1.0 / fw, 0.1 / fh])
            bar.axis("off")
            bar.set_xlim(0, 1)
            bar.set_ylim(0, 1)
            bar.add_patch(Rectangle((0, 0), 1, 1, fc="black"))
            fig.text(1.5 / fw, 0.33 / fh, f"bar = 25.4 mm: print at 100 %. Board {W} x {H} holes = "
                     f"{W * PITCH_MM:.0f} x {H * PITCH_MM:.0f} mm", fontsize=8)
            pdf.savefig(fig)
            plt.close(fig)
    print("wrote", HERE / "stripboard.png", HERE / "stripboard_1to1.pdf")


if __name__ == "__main__":
    main()
