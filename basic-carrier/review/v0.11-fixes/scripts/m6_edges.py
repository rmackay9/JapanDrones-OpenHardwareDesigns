# KiCad python: m6_edges.py board  -- review M6
#  1. Every non-GND copper zone is clipped to the board outline inset by 0.5 mm, and the 3.5 mm-radius circles
#     around the four corner holes are cut out of it (all its layers).
#  2. Non-GND vias whose copper reaches into a corner circle are moved out to the nearest clear spot that is
#     still inside their own net's fill on F.Cu and B.Cu (phase stitching vias), or deleted if there is none.
#  3. Four rule areas named CORNER_KO (F.Cu + B.Cu, no restrictions of their own) mark the circles; the project
#     .kicad_dru uses them so DRC flags any non-GND track/via/zone there.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); b = B.b
INSET = 0.5; KR = 3.5
x0, x1, y0, y1 = EDGE[0] + INSET, EDGE[1] - INSET, EDGE[2] + INSET, EDGE[3] - INSET

def circle(cx, cy, r, n=48):
    sp = pcbnew.SHAPE_POLY_SET(); sp.NewOutline()
    for k in range(n):
        a = 2 * math.pi * k / n; sp.Append(MM(cx + r / math.cos(math.pi / n) * math.cos(a)), MM(cy + r / math.cos(math.pi / n) * math.sin(a)))
    return sp

rect = pcbnew.SHAPE_POLY_SET(); rect.NewOutline()
for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)): rect.Append(MM(x), MM(y))
holes = pcbnew.SHAPE_POLY_SET()
for hx, hy in CORNER_HOLES: holes.Append(circle(hx, hy, KR))
holes.Simplify()

def boolean(a, b_, op):
    try: getattr(a, op)(b_)
    except TypeError: getattr(a, op)(b_, pcbnew.SHAPE_POLY_SET.PM_FAST)

changed = []
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() == 'GND': continue
    o = z.Outline()
    before = o.Area()
    boolean(o, rect, 'BooleanIntersection')
    boolean(o, holes, 'BooleanSubtract')
    if o.OutlineCount() == 0: changed.append(f'{z.GetZoneName()}: EMPTY'); continue
    if abs(o.Area() - before) > 1: changed.append(f'{z.GetZoneName()} ({z.GetNetname()}): {before / 1e12:.1f} -> {o.Area() / 1e12:.1f} mm2')
    z.SetNeedRefill(True)
print('zones clipped:\n  ' + '\n  '.join(changed))

# vias
moved = []
for v in list(B.vias()):
    if v.GetNetname() == 'GND': continue
    vx, vy = mm(v.GetPosition().x), mm(v.GetPosition().y); vr = mm(v.GetWidth(pcbnew.F_Cu)) / 2
    hit = [(hx, hy) for hx, hy in CORNER_HOLES if math.hypot(vx - hx, vy - hy) < KR + vr]
    if not hit: continue
    hx, hy = hit[0]; net = v.GetNetname()
    has_tracks = any(t.GetNetname() == net and (abs(mm(t.GetStart().x) - vx) < 0.01 and abs(mm(t.GetStart().y) - vy) < 0.01 or
                                               abs(mm(t.GetEnd().x) - vx) < 0.01 and abs(mm(t.GetEnd().y) - vy) < 0.01) for t in B.tracks())
    best = None
    for dist in [x / 20 for x in range(1, 50)]:
        for k in range(32):
            a = 2 * math.pi * k / 32; nx, ny = vx + dist * math.cos(a), vy + dist * math.sin(a)
            if math.hypot(nx - hx, ny - hy) < KR + vr + 0.05: continue
            if not (B.in_fill(nx, ny, net, 'F.Cu', vr) and B.in_fill(nx, ny, net, 'B.Cu', vr)): continue
            if B.obstacles(nx, ny, vr, net, CU, clr=0.2, edge=0.5, skip=[v]): continue
            best = (nx, ny); break
        if best: break
    if has_tracks or not best:
        b.Delete(v); moved.append(f'{net} ({vx:.2f},{vy:.2f}) deleted' + (' (had tracks!)' if has_tracks else ''))
        continue
    v.SetPosition(V(*best)); moved.append(f'{net} ({vx:.2f},{vy:.2f}) -> ({best[0]:.2f},{best[1]:.2f})')
print('vias:\n  ' + '\n  '.join(moved))

# marker rule areas
for hx, hy in CORNER_HOLES:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True); z.SetZoneName('CORNER_KO')
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
    for f in ('SetDoNotAllowTracks', 'SetDoNotAllowVias', 'SetDoNotAllowPads', 'SetDoNotAllowFootprints'):
        getattr(z, f)(False)
    if hasattr(z, 'SetDoNotAllowZoneFills'): z.SetDoNotAllowZoneFills(False)
    elif hasattr(z, 'SetDoNotAllowCopperPour'): z.SetDoNotAllowCopperPour(False)
    c = circle(hx, hy, KR - 0.05, 36); o = c.Outline(0)   # a hair inside the cut-outs so zone edges don't graze it
    z.Outline().NewOutline()
    for k in range(o.PointCount()): z.Outline().Append(o.CPoint(k).x, o.CPoint(k).y)
    b.Add(z)
B.save()
