# KiCad python: add_vias.py board net x0,y0,x1,y1 pitch maxn layers-that-must-be-filled [d drill] [avoid cx,cy,r]
# Adds through vias of `net` on a staggered grid inside the box where every listed layer has `net` fill and
# nothing of another net (except GND zone fill) is within 0.2 mm.
import sys, math
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else __file__.rsplit('/', 1)[0])
from kutil import *
path, net = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
pitch, maxn = float(sys.argv[4]), int(sys.argv[5])
need = sys.argv[6].split(',')
d, drill = (float(sys.argv[7]), float(sys.argv[8])) if len(sys.argv) > 8 else (0.6, 0.3)
avoid = [tuple(map(float, a.split(','))) for a in sys.argv[9:] if a != 'nopad']
NOPAD = 'nopad' in sys.argv[9:]
B = Board(path)
added = []
row = 0
y = y0
while y <= y1 + 1e-9 and len(added) < maxn:
    x = x0 + (pitch / 2 if row % 2 else 0)
    while x <= x1 + 1e-9 and len(added) < maxn:
        ok = all(math.hypot(x - ax, y - ay) >= ar for ax, ay, ar in avoid)
        ok = ok and all(B.in_fill(x, y, net, L, margin=d / 2) for L in need)
        if ok and all(math.hypot(x - ax, y - ay) >= pitch * 0.85 for ax, ay in added):
            why = B.obstacles(x, y, d / 2, net, CU, clr=0.2)
            if not why and NOPAD:   # no via in or within 0.3 mm of any pad, same net included (review M4)
                P = V(x, y)
                for f in B.b.GetFootprints():
                    fb = f.GetBoundingBox()
                    if not (mm(fb.GetLeft()) - 2 < x < mm(fb.GetRight()) + 2 and mm(fb.GetTop()) - 2 < y < mm(fb.GetBottom()) + 2): continue
                    for p in f.Pads():
                        if any(p.IsOnLayer(lid(B.b, L)) and p.GetEffectivePolygon(lid(B.b, L)).Collide(P, MM(d / 2 + 0.3)) for L in ('F.Cu', 'B.Cu')):
                            why.append('pad'); break
                    if why: break
            if not why:
                B.add_via(x, y, net, d, drill); added.append((x, y))
        x += pitch
    y += pitch * 0.866; row += 1
B.save()
print(f'{net}: added {len(added)} vias', ' '.join(f'({x:.2f},{y:.2f})' for x, y in added))
