# KiCad python: m4_vias.py board REF.PAD [REF.PAD ...]
# Review M4: every via that sits in (or overlaps) one of the listed pads is moved so its copper is at least
# 0.3 mm clear of every pad, and joined back with short tracks: pad -> new via on the pad's layer, and
# old via point -> new via on every other layer where a track ended at the old via.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); b = B.b
targets = [a.split('.', 1) for a in sys.argv[2:]]
PADGAP = 0.3

def pad_dist(p, L, x, y):
    """distance from point to pad copper on layer L (0 if inside)"""
    poly = p.GetEffectivePolygon(lid(b, L)); P = V(x, y)
    if poly.Contains(P): return 0.0
    lo, hi = 0.0, 5.0
    if not poly.Collide(P, MM(hi)): return hi
    for _ in range(20):
        mid = (lo + hi) / 2
        if poly.Collide(P, MM(mid)): hi = mid
        else: lo = mid
    return hi

def near_pads(x, y, r):
    out = []
    for f in b.GetFootprints():
        fb = f.GetBoundingBox()
        if not (mm(fb.GetLeft()) - 3 < x < mm(fb.GetRight()) + 3 and mm(fb.GetTop()) - 3 < y < mm(fb.GetBottom()) + 3): continue
        for p in f.Pads():
            q = p.GetPosition()
            if math.hypot(mm(q.x) - x, mm(q.y) - y) < r: out.append((f, p))
    return out

def seg_clear(x0, y0, x1, y1, w, L, net, skip):
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05) + 1)
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n; y = y0 + (y1 - y0) * k / n
        why = B.obstacles(x, y, w / 2, net, [L], clr=0.2, edge=0.25, skip=skip, zones=False)
        why = [s for s in why if not s.startswith('hole') and not s.startswith('via-same') and not s.startswith('pth')]
        if why: return why
    return []

log = []
for ref, num in targets:
    f = B.F[ref]; pad = [p for p in f.Pads() if p.GetNumber() == num][0]
    L = 'F.Cu' if pad.IsOnLayer(pcbnew.F_Cu) else 'B.Cu'
    for v in list(B.vias()):
        vx, vy = mm(v.GetPosition().x), mm(v.GetPosition().y); vr = mm(v.GetWidth(pcbnew.F_Cu)) / 2
        if math.hypot(vx - mm(pad.GetPosition().x), vy - mm(pad.GetPosition().y)) > 4: continue
        if pad_dist(pad, L, vx, vy) >= vr: continue          # via copper does not touch this pad
        net = v.GetNetname(); vd, vdr = mm(v.GetWidth(pcbnew.F_Cu)), mm(v.GetDrillValue())
        if os.environ.get('M4_SMALL') and vd > 0.4: vd, vdr = 0.4, 0.2   # QFN fan-out: smallest via already used there
        vr_new = vd / 2
        # tracks ending at the via, per layer
        ends = {}
        for t in B.tracks():
            if t.GetNetname() != net: continue
            for e in (t.GetStart(), t.GetEnd()):
                if abs(mm(e.x) - vx) < 0.01 and abs(mm(e.y) - vy) < 0.01: ends.setdefault(t.GetLayerName(), []).append(t)
        padnet = pad.GetNetname() == net
        best = None
        for dist in [x / 100 for x in range(30, 210, 5)]:
            for k in range(24):
                a = 2 * math.pi * k / 24; nx, ny = vx + dist * math.cos(a), vy + dist * math.sin(a)
                if B.obstacles(nx, ny, vr_new, net, CU, clr=0.2, edge=0.3, skip=[v], zones=False): continue
                # 0.3 mm off the target pad and off every pad of the via's own net; other nets: normal clearance (obstacles)
                if any(pad_dist(p, Lp, nx, ny) < vr_new + (PADGAP if p == pad else float(os.environ.get('M4_SAMEGAP', PADGAP))) for fp, p in near_pads(nx, ny, 4)
                       for Lp in ('F.Cu', 'B.Cu') if p.IsOnLayer(lid(b, Lp)) and (p.GetNetname() == net or p == pad)):
                    if os.environ.get('M4_DEBUG'): print('   padgap', round(nx, 2), round(ny, 2))
                    continue
                if any(math.hypot(hx - nx, hy - ny) < 3.6 + vr_new for hx, hy in CORNER_HOLES) and net != 'GND': continue
                ok = True; plan = []
                layers = set(ends) | ({L} if padnet else set())
                for Ln in layers:
                    w = max([mm(t.GetWidth()) for t in ends.get(Ln, [])] or [0.25])
                    w = min(w, 0.3)
                    sc = seg_clear(vx, vy, nx, ny, w, Ln, net, [v])
                    if sc:
                        ok = False
                        if os.environ.get('M4_DEBUG'): print('   seg', Ln, round(nx, 2), round(ny, 2), sc[:2])
                        break
                    plan.append((Ln, w))
                if ok: best = (nx, ny, plan); break
            if best: break
        if not best:
            log.append(f'{ref}.{num}: via {net} ({vx:.2f},{vy:.2f}) - NO SPOT, left'); continue
        nx, ny, plan = best
        b.Delete(v)
        B.add_via(nx, ny, net, vd, vdr)
        for Ln, w in plan: B.add_track(vx, vy, nx, ny, w, Ln, net)
        log.append(f'{ref}.{num}: via {net} ({vx:.2f},{vy:.2f}) -> ({nx:.2f},{ny:.2f}), tracks on {",".join(l for l, _ in plan) or "-"}')
B.save()
print('\n'.join(log))
