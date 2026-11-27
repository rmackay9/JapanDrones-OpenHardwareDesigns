# KiCad python: compaction slack along scan lines (courtyard bboxes, per side)
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
X0, X1, Y0, Y1 = 99.0, 193.0, 50.0, 140.0
GAP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4   # min courtyard gap assumed after tightening
EDGE = 0.3
parts = {'F': [], 'B': []}
for f in b.GetFootprints():
    side = 'F' if f.GetLayer() == pcbnew.F_Cu else 'B'
    c = f.GetCourtyard(pcbnew.F_CrtYd if side == 'F' else pcbnew.B_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    r = (max(X0, mm(bb.GetLeft())), min(X1, mm(bb.GetRight())), max(Y0, mm(bb.GetTop())), min(Y1, mm(bb.GetBottom())))
    parts[side].append((f.GetReference(), r))
    # THT pads occupy both sides
    if side == 'B' and f.GetReference() == 'J18':
        pass
# fixed features both sides: holes (Cube + corner) as 3 mm / 2 mm squares
holes = [(130, 80, 1.8), (160, 80, 1.8), (130, 110, 1.8), (160, 110, 1.8),
         (101.5, 52.5, 3.2), (190.5, 52.5, 3.2), (101.5, 137.5, 3.2), (190.5, 137.5, 3.2)]
for s in parts:
    for hx, hy, d in holes:
        parts[s].append(('hole', (hx - d / 2 - 0.3, hx + d / 2 + 0.3, hy - d / 2 - 0.3, hy + d / 2 + 0.3)))

def slack(lo, hi, ivs):
    ivs = sorted((max(lo, a), min(hi, b_), n) for a, b_, n in ivs if b_ > lo and a < hi)
    free = 0; cur = lo; gaps = 0; who = []
    for a, b_, n in ivs:
        if a > cur:
            free += a - cur; gaps += 1
        cur = max(cur, b_)
        who.append(n)
    free += max(0, hi - cur)
    return free - GAP * max(0, len(ivs) - 1) - 2 * EDGE, who

def scan(axis):
    res = []
    steps = [round(Y0 + 0.25 * i, 2) for i in range(int((Y1 - Y0) / 0.25) + 1)] if axis == 'x' else \
            [round(X0 + 0.25 * i, 2) for i in range(int((X1 - X0) / 0.25) + 1)]
    for s in steps:
        best = None
        for side in 'FB':
            if axis == 'x':  # horizontal line y=s, slack in x
                ivs = [(r[0], r[1], n) for n, r in parts[side] if r[2] < s < r[3]]
                v, who = slack(X0, X1, ivs)
            else:
                ivs = [(r[2], r[3], n) for n, r in parts[side] if r[0] < s < r[1]]
                v, who = slack(Y0, Y1, ivs)
            if best is None or v < best[0]: best = (v, side, who)
        res.append((s, *best))
    return res
for axis, label in (('x', 'WIDTH (horizontal lines y=const)'), ('y', 'DEPTH (vertical lines x=const)')):
    r = scan(axis)
    r.sort(key=lambda t: t[1])
    print(f'== {label}: min slack {r[0][1]:.2f} mm (gap {GAP})')
    seen = 0
    for s, v, side, who in r[:8]:
        print(f'   at {s:6.2f} side {side}: slack {v:5.2f}  parts {" ".join(w for w in who if w != "hole")[:150]}')
