"""3D layout of the toolkit: every module as a plain box at its real size (mm) on a base board, with the wires between pins.

The parts and pins come from the schematic registry (gen_diagrams.SHEETS), so the wiring drawn here is the schematic's netlist:
build_model() refuses to run if a schematic part has no box or a pin has no terminal. Positions are a suggested layout.

Run: python3 gen_3d.py  -> ecrt_layout_3d.png (static picture); gen_index.py embeds build_model() in the interactive viewer.
"""
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARD = (520.0, 320.0, 4.0)          # base board length (x), depth (y), thickness (z), mm; low-voltage left, 230 V right

# ref: name, size (L along x, W along y, H) in mm, position of the corner (y counts from the back, the layout is mirrored below so
# the tall parts sit at the back), colour, how the size was found, link.
# 'src': "listing" = taken from a seller / datasheet page, "typical" = common size for this kind of part, not checked on your unit.
PARTS = {
    "U8": dict(name="Raspberry Pi 3B+", size=(85, 56, 17), at=(20, 10), color="#c51a4a", src="typical"),
    "J2": dict(name="DC barrel jack (12 V input)", size=(15, 9, 11), at=(150, 10), color="#222222", src="typical"),
    "U6": dict(name="Mornsun K7805-2000R3 (5 V, 2 A)", size=(11.5, 9, 17.5), at=(150, 40), color="#4a4a4a", src="listing",
               url="https://www.mornsun-power.com/html/products-detail/K78xx-2000R3.html"),
    "U1": dict(name="Arduino Uno R3", size=(68.6, 53.4, 15), at=(20, 100), color="#00979d", src="typical"),
    "U3": dict(name="LCD 1602 with I2C backpack", size=(80, 36, 13), at=(20, 245), color="#2f9e44", src="typical"),
    "KP1": dict(name="4x4 membrane keypad", size=(69, 77, 2), at=(130, 215), color="#6c757d", src="typical"),
    "U5": dict(name="4-channel relay module, 12 V", size=(77, 55, 17), at=(205, 100), color="#1d5fb4", src="listing",
               url="https://www.jaycar.co.nz/p/XC4418"),
    "U2": dict(name="PZEM-004T V4 module", size=(110, 70, 35), at=(330, 175), color="#e8e8e8", src="listing",
               url="https://zbotic.in/product/peacefair-pzem-004t-ac-multi-function-electric-energy-metering-power-monitor/"),
    "CT1": dict(name="100 A split-core current transformer", size=(55, 30, 28), at=(455, 195), color="#333333", src="typical"),
    "J1": dict(name="230 V AC supply terminal", size=(20, 10, 15), at=(300, 150), color="#2d6a4f", src="typical"),
    **{f"KM{i}": dict(name="Contactor 25 A, 2 NO, 230 V coil, 2 modules", size=(36, 66, 90), at=(300 + (i - 1) * 45, 40),
                      color="#d9a441", src="typical") for i in range(1, 5)},
    **{f"J{i + 2}": dict(name=f"Load {i} terminal (appliance)", size=(20, 10, 15), at=(308 + (i - 1) * 45, 12), color="#2d6a4f",
                         src="typical") for i in range(1, 5)},
}
SHORT = {"U8": "Raspberry Pi", "J2": "12 V jack", "U6": "K7805", "U1": "Arduino Uno", "U3": "LCD", "KP1": "Keypad",
         "U5": "Relay module", "U2": "PZEM", "CT1": "CT", "J1": "230 V in",
         **{f"KM{i}": f"Contactor {i}" for i in range(1, 5)}, **{f"J{i + 2}": f"Load {i}" for i in range(1, 5)}}
_END2 = {"1": (.3, 1), "2": (.7, 1)}
# pin -> (fx, fy): where the pin is on the module as a fraction of the footprint (x from the left, y from the back)
TERMS = {
    "U8": {"USB": (.8, 1), "PWR": (1, .8)},
    "J2": _END2,
    "U6": {"VIN": (.2, 1), "GND": (.5, 1), "VOUT": (.8, 1)},
    "U1": {"USB-B": (0, .3), "VIN": (.62, 1), "5V": (.47, 1), "GND": (.52, 1), "A0": (.68, 1), "A1": (.72, 1), "A2": (.77, 1),
           "A3": (.81, 1), "A4 (SDA)": (.87, 1), "A5 (SCL)": (.92, 1), "D2 (SW-RX)": (.55, 0), "D3 (SW-TX)": (.6, 0),
           "D4": (.66, 0), "D5": (.7, 0), "D6": (.75, 0), "D7": (.79, 0), "D10": (.88, 0), "D11": (.92, 0), "D12": (.96, 0),
           "D13": (.99, 0)},
    "U3": {"GND": (0, .2), "VCC": (0, .4), "SDA": (0, .6), "SCL": (0, .8)},
    "KP1": {"R1": (.2, 0), "R2": (.3, 0), "R3": (.4, 0), "R4": (.5, 0), "C1": (.6, 0), "C2": (.7, 0), "C3": (.8, 0), "C4": (.9, 0)},
    "U5": {"VCC": (0, .1), "GND": (0, .25), "IN1": (0, .4), "IN2": (0, .55), "IN3": (0, .7), "IN4": (0, .85),
           **{f"COM{i}": (1, .08 + (i - 1) * .24) for i in range(1, 5)}, **{f"NO{i}": (1, .2 + (i - 1) * .24) for i in range(1, 5)}},
    "U2": {"5V": (0, .2), "RX": (0, .4), "TX": (0, .6), "GND": (0, .8), "L": (.3, 0), "N": (.5, 0), "CT A": (1, .3), "CT B": (1, .6)},
    "CT1": {"1": (0, .3), "2": (0, .7)},
    "J1": _END2,
    **{f"KM{i}": {"1 (L in)": (.15, 1), "A1": (.4, 1), "A2": (.6, 1), "3 (N in)": (.85, 1), "2 (L out)": (.15, 0),
                  "4 (N out)": (.85, 0)} for i in range(1, 5)},
    **{f"J{i + 2}": _END2 for i in range(1, 5)},
}


# Mirror the layout front to back so the tall battery sits at the back and does not hide the modules from the default camera.
for _ref, _p in PARTS.items():
    _p["at"] = (_p["at"][0], BOARD[1] - _p["at"][1] - _p["size"][1])
    TERMS[_ref] = {k: (fx, 1 - fy) for k, (fx, fy) in TERMS[_ref].items()}


def _terminal(ref, pin):
    """Pin position on the board: the point on the footprint edge nearest to where the pin is on the module, and the outward
    direction. Every wire starts here, on the board, so nothing is routed through the air."""
    p = PARTS[ref]
    (l, w, _h), (x, y) = p["size"], p["at"]
    fx, fy = TERMS[ref][pin]
    d = {"W": fx * l, "E": (1 - fx) * l, "S": fy * w, "N": (1 - fy) * w}
    side = min(d, key=lambda k: (d[k], "WESN".index(k)))
    px, py = {"W": (x, y + fy * w), "E": (x + l, y + fy * w), "S": (x + fx * l, y), "N": (x + fx * l, y + w)}[side]
    return [round(px, 2), round(py, 2), 0.0], side


CELL = 1.5                                   # routing grid, mm
_STEP = {"W": (-1, 0), "E": (1, 0), "S": (0, -1), "N": (0, 1)}


def _route_all(nets, term):
    """Route every net on a grid over the board with Dijkstra: wires keep out of the module footprints, two nets never run side by
    side on the same cell, and may only cross at right angles (a jumper or a bridged crossing on the real board)."""
    import heapq
    nx, ny = int(BOARD[0] / CELL), int(BOARD[1] / CELL)
    blocked = set()
    for ref, p in PARTS.items():
        (l, w, _h), (x, y) = p["size"], p["at"]
        for i in range(nx):
            for j in range(ny):
                if x <= (i + .5) * CELL <= x + l and y <= (j + .5) * CELL <= y + w:
                    blocked.add((i, j))
    cell = lambda x, y: (int(x / CELL), int(y / CELL))                            # noqa: E731
    centre = lambda c: [round((c[0] + .5) * CELL, 2), round((c[1] + .5) * CELL, 2)]  # noqa: E731
    occ = {}                                  # cell -> {net: set of axes 'h'/'v'}
    start = {}                                # (ref, pin) -> start cell
    for ref, pin in term:
        pt, side = term[(ref, pin)]
        dx, dy = _STEP[side]
        k = 0.6
        c = cell(pt[0] + dx * CELL * k, pt[1] + dy * CELL * k)
        while c in blocked:
            k += 0.5
            c = cell(pt[0] + dx * CELL * k, pt[1] + dy * CELL * k)
        assert 0 <= c[0] < nx and 0 <= c[1] < ny
        assert c not in blocked, f"pin {ref}.{pin} start cell is inside a module"
        start[(ref, pin)] = c
    pin_net = {pn: key for key, n in nets.items() for pn in n["pins"]}
    for pn, c in start.items():
        occ.setdefault(c, {}).setdefault(pin_net.get(pn), set()).update("hv")

    def free_for(c, key, axis):
        o = occ.get(c)
        if not o:
            return 0.0
        mine = key in o
        others = [(k, a) for k, a in o.items() if k != key]
        if not others:
            return 0.1 if mine else 0.0
        if any(axis in a and len(a) == 1 or len(a) == 2 for _k, a in others):
            return None
        return 30.0                                                              # perpendicular crossing

    paths = {}
    order = sorted(nets.items(), key=lambda kv: (kv[1]["name"] == "GND", kv[1]["kind"] == "power", len(kv[1]["pins"]), kv[1]["name"]))
    for key, n in order:
        pins = sorted(n["pins"])
        tree = {start[pins[0]]: pins[0]}
        occ.setdefault(start[pins[0]], {}).setdefault(key, set()).update("hv")
        todo = sorted(pins[1:], key=lambda pn: math.dist(centre(start[pn]), centre(start[pins[0]])))
        for pn in todo:
            s = start[pn]
            heap, best, prev = [(0.0, 0, s, "")], {(s, ""): 0.0}, {}
            goal = None
            while heap:
                cost, _i, c, d = heapq.heappop(heap)
                if cost > best.get((c, d), 1e18):
                    continue
                if c in tree and c != s:
                    goal = (c, d)
                    break
                for nd, (dx, dy) in _STEP.items():
                    q = (c[0] + dx, c[1] + dy)
                    if not (0 <= q[0] < nx and 0 <= q[1] < ny) or q in blocked:
                        continue
                    axis = "h" if nd in "WE" else "v"
                    f = free_for(q, key, axis)
                    if f is None:
                        continue
                    if f >= 30 and d and d != nd:                                       # cross only while going straight
                        continue
                    cc = cost + 1 + f + (2.5 if d and d != nd else 0) + (0.6 if any((q[0] + a, q[1] + b) in blocked for a, b in _STEP.values()) else 0)
                    if cc < best.get((q, nd), 1e18):
                        best[(q, nd)] = cc
                        prev[(q, nd)] = (c, d)
                        heapq.heappush(heap, (cc, len(best), q, nd))
            assert goal, f"no route for net {n['name']} to {pn[0]}.{pn[1]}"
            seq, cur = [], goal
            while cur[0] != s or cur[1] != "":
                seq.append(cur[0])
                cur = prev[cur]
            seq.append(s)
            seq.reverse()
            for a, b in zip(seq, seq[1:]):
                axis = "h" if a[1] == b[1] else "v"
                for c in (a, b):
                    occ.setdefault(c, {}).setdefault(key, set()).add(axis)
            for c in seq:
                tree.setdefault(c, pn)
            paths.setdefault(key, []).append((pn, tree[seq[-1]] if seq[-1] in tree else pins[0], seq))
    return paths, centre


def _corners(seq, centre):
    out = [centre(seq[0])]
    for a, b, c in zip(seq, seq[1:], seq[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(centre(b))
    out.append(centre(seq[-1]))
    return out


def build_model(sheets, classes):
    """sheets = gen_diagrams.SHEETS, classes = gen_diagrams.CLASSES (wire colours and classes come from the schematic).
    Returns the JSON-able model for the viewer."""
    nets = {}
    drawn = set()
    for reg in sheets.values():
        drawn |= set(reg["parts"])
        for p in reg["pins"]:
            if p["net"]:
                nets.setdefault(p["netkey"], {"name": p["net"], "kind": p["kind"], "cls": p["cls"], "pins": set()})["pins"].add((p["ref"], p["pin"]))
    missing = sorted(drawn - set(PARTS))
    assert not missing, f"schematic parts with no 3D box: {missing}"
    extra = sorted(set(PARTS) - drawn)
    assert not extra, f"3D boxes for parts that are not in the schematic: {extra}"
    term = {}
    for k, n in nets.items():
        for ref, pin in n["pins"]:
            assert pin in TERMS.get(ref, {}), f"no 3D terminal for {ref} pin {pin!r} (net {n['name']})"
            term[(ref, pin)] = _terminal(ref, pin)
    nets = {k: n for k, n in nets.items() if len(n["pins"]) > 1}
    paths, centre = _route_all(nets, term)

    wires = []
    for key, segs in paths.items():
        n = nets[key]
        for pin, owner, seq in segs:
            pa = term[pin][0]
            body = _corners(seq, centre)
            wires.append({"net": n["name"], "netkey": key, "kind": n["kind"], "cls": n["cls"], "ends": [list(pin), list(owner)],
                          "path": [[pa[0], pa[1], 0.0]] + [[x, y, 0.0] for x, y in body]})
    parts = []
    for ref, p in PARTS.items():
        parts.append({"ref": ref, "name": p["name"], "short": SHORT[ref], "size": list(p["size"]), "at": list(p["at"]), "color": p["color"],
                      "src": p["src"], "url": p.get("url", ""), "pins": {k: _terminal(ref, k)[0] for k in TERMS[ref]}})
    return {"board": list(BOARD), "parts": parts, "wires": wires, "classes": {k: list(v) for k, v in classes.items()}}


def model_classes(model):
    used = {w["cls"] for w in model["wires"]}
    return [tuple(v) for k, v in model["classes"].items() if k in used]


def render_png(model, path, yaw=12.0, pitch=42.0):
    """Static picture: orthographic projection and painter's order, plain 2D polygons (the viewer uses the same idea)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def proj(pt):
        x, y, z = pt
        x1, y1 = x * cy - y * sy, x * sy + y * cy
        return (x1, y1 * sp + z * cp), y1 * cp - z * sp         # screen (x, up), depth (bigger = farther)

    def shade(color, k):
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(min(255, int(c * k)) for c in (r, g, b))

    def box_faces(x, y, z, l, w, h, color):
        faces = [((0, 0, 1), [(x, y, z + h), (x + l, y, z + h), (x + l, y + w, z + h), (x, y + w, z + h)], 1.0),
                 ((0, -1, 0), [(x, y, z), (x + l, y, z), (x + l, y, z + h), (x, y, z + h)], 0.8),
                 ((0, 1, 0), [(x, y + w, z), (x + l, y + w, z), (x + l, y + w, z + h), (x, y + w, z + h)], 0.7),
                 ((-1, 0, 0), [(x, y, z), (x, y + w, z), (x, y + w, z + h), (x, y, z + h)], 0.9),
                 ((1, 0, 0), [(x + l, y, z), (x + l, y + w, z), (x + l, y + w, z + h), (x + l, y, z + h)], 0.6)]
        out = []
        for n, quad, k in faces:
            nx1, ny1 = n[0] * cy - n[1] * sy, n[0] * sy + n[1] * cy
            if -ny1 * cp + n[2] * sp > 1e-9:                       # facing the camera
                out.append((quad, shade(color, k)))
        return out

    fig, ax = plt.subplots(figsize=(14, 8.5))
    bl, bw, bt = model["board"]
    items = [(1e6, box_faces(0, 0, -bt, bl, bw, bt, "#c8b98a"))]
    for p in model["parts"]:
        (l, w, h), (x, y) = p["size"], p["at"]
        items.append((proj((x + l / 2, y + w / 2, h / 2))[1], box_faces(x, y, 0, l, w, h, p["color"])))
    for n, (_depth, faces) in enumerate(sorted(items, key=lambda i: -i[0])):
        for quad, col in faces:
            ax.add_patch(Polygon([proj(q)[0] for q in quad], closed=True, fc=col, ec="#222222", lw=0.5))
        if n == 0:                                             # wires lie on the board: after the board, before the modules
            for wr in model["wires"]:
                xs, ys = zip(*[proj(q)[0] for q in wr["path"]])
                col = model["classes"][wr["cls"]][0]
                ax.plot(xs, ys, color=col, lw=2.2, solid_joinstyle="round", solid_capstyle="round")
    for p in model["parts"]:
        (l, w, h), (x, y) = p["size"], p["at"]
        sx, sy_ = proj((x + l / 2, y + w / 2, h + 4))[0]
        ax.text(sx, sy_, p["ref"], ha="center", va="bottom", fontsize=8, fontweight="bold",
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.8))
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0], [0], color=c, lw=3, label=n) for c, n in model_classes(model)], loc="lower left", frameon=False, fontsize=9)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    import gen_diagrams as g
    g.block_diagram()
    g.schematic_power()
    g.schematic_control()
    m = build_model(g.SHEETS, g.CLASSES)
    render_png(m, HERE / "ecrt_layout_3d.png")
    print(f"{len(m['parts'])} parts, {len(m['wires'])} wire runs -> ecrt_layout_3d.png")
