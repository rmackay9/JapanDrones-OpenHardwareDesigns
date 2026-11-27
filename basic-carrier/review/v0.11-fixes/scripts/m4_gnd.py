# KiCad python: m4_gnd.py board REF.PAD ... -- review M4 for GND pads that sit in the GND pour:
# the GND via in the pad is removed and a new GND via is placed at the nearest clear spot (within 1.6 mm) that is
# inside the GND fill on the pad's layer and at least 0.3 mm from every pad. The pour connects pad and via,
# so no track is added; the pad keeps its pour connection.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); b = B.b
def pad_gap_ok(x, y, r):
    P = V(x, y)
    for f in b.GetFootprints():
        fb = f.GetBoundingBox()
        if not (mm(fb.GetLeft()) - 3 < x < mm(fb.GetRight()) + 3 and mm(fb.GetTop()) - 3 < y < mm(fb.GetBottom()) + 3): continue
        for p in f.Pads():
            for L in ('F.Cu', 'B.Cu'):
                if p.IsOnLayer(lid(b, L)) and p.GetEffectivePolygon(lid(b, L)).Collide(P, MM(r + 0.3)): return False
    return True
for a in sys.argv[2:]:
    ref, num = a.split('.'); pad = [p for p in B.F[ref].Pads() if p.GetNumber() == num][0]
    L = 'F.Cu' if pad.IsOnLayer(pcbnew.F_Cu) else 'B.Cu'
    for v in list(B.vias()):
        if v.GetNetname() != 'GND': continue
        vx, vy = mm(v.GetPosition().x), mm(v.GetPosition().y)
        if not pad.GetEffectivePolygon(lid(b, L)).Collide(v.GetPosition(), v.GetWidth(pcbnew.F_Cu) // 2): continue
        tr = [t for t in B.tracks() if t.GetNetname() == 'GND' and any(abs(mm(e.x) - vx) < 0.01 and abs(mm(e.y) - vy) < 0.01 for e in (t.GetStart(), t.GetEnd()))]
        best = None
        for dist in [x / 20 for x in range(6, 33)]:
            for k in range(36):
                t = 2 * math.pi * k / 36; nx, ny = vx + dist * math.cos(t), vy + dist * math.sin(t)
                if B.obstacles(nx, ny, 0.225, 'GND', CU, clr=0.2, edge=0.3, skip=[v] + tr, zones=False): continue
                if not B.in_fill(nx, ny, 'GND', L, 0.3) or not pad_gap_ok(nx, ny, 0.225): continue
                best = (nx, ny); break
            if best: break
        if not best: print(f'{a}: no spot'); continue
        for t in tr: b.Delete(t)
        b.Delete(v); B.add_via(best[0], best[1], 'GND', 0.45, 0.25)
        print(f'{a}: GND via ({vx:.2f},{vy:.2f}) -> ({best[0]:.2f},{best[1]:.2f}) in the {L} GND pour, stub removed: {len(tr)}')
B.save()
