# vip.py dump : vias that overlap a pad (centre inside, or annulus touching) on F/B
import sys, math, json
from cu import load
d = load(sys.argv[1])
def inside(pt, poly):
    x, y = pt; c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def dist_poly(pt, poly):
    x, y = pt; best = 1e9
    for i in range(len(poly)):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % len(poly)]
        vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
        t = 0 if L2 == 0 else max(0, min(1, ((x - ax) * vx + (y - ay) * vy) / L2))
        best = min(best, math.hypot(ax + t * vx - x, ay + t * vy - y))
    return best
def area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2
out = []
for v in d['vias']:
    for p in d['pads']:
        if abs(p['x'] - v['x']) > 4 or abs(p['y'] - v['y']) > 4: continue
        for L in ('F.Cu', 'B.Cu'):
            if L not in p['layers'] or p['drill'] > 0: continue
            for o in p['layers'][L]:
                poly = o['o']; c = inside((v['x'], v['y']), poly); dd = dist_poly((v['x'], v['y']), poly)
                if c or dd < v['d'] / 2 + 0.3:
                    out.append((p['ref'], p['num'], p['net'], L, round(area(poly), 2), v['x'], v['y'], v['d'], v['net'], 'IN' if c else f'{dd - v["d"]/2:.2f}'))
small = [o for o in out if o[4] < 4.0]
for o in sorted(small): print(*o)
print(len(out), 'total overlaps/near;', len(small), 'with pad < 4 mm2;', sum(1 for o in small if o[9] == 'IN'), 'centre inside')
