# system python: plot.py dump.json out.png x0,y0,x1,y1 [layers] [highlight boxes "x0,y0,x1,y1;..."]
import json, sys, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle
d = json.load(open(sys.argv[1]))
x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
layers = sys.argv[4].split(',') if len(sys.argv) > 4 else ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu']
boxes = [list(map(float, b.split(','))) for b in sys.argv[5].split(';')] if len(sys.argv) > 5 and sys.argv[5] else []
def col(net):
    if net == 'GND': return '#2a7f2a'
    if net == 'VBATT': return '#c03030'
    h = int(hashlib.md5(net.encode()).hexdigest()[:6], 16)
    return '#%02x%02x%02x' % (60 + (h >> 16) % 150, 60 + (h >> 8) % 150, 60 + h % 150)
n = len(layers)
fig, axs = plt.subplots(1, n, figsize=(7 * n, 7 * (y1 - y0) / (x1 - x0) + 0.6))
if n == 1: axs = [axs]
for ax, L in zip(axs, layers):
    for net, l, polys in d['fills']:
        if l != L: continue
        for p in polys:
            ax.add_patch(Polygon(p, closed=True, fc=col(net), alpha=0.18, ec='none'))
    for net, l, polys, ra in d['zones']:
        if l != L: continue
        for p in polys:
            ax.add_patch(Polygon(p, closed=True, fill=False, ec=col(net) if not ra else 'k', lw=0.8, ls='--'))
    for sx, sy, ex, ey, w, l, net in d['tracks']:
        if l == L:
            ax.plot([sx, ex], [sy, ey], color=col(net), lw=w * 72 / 25.4 * 7 * n / (x1 - x0) * 0.9, solid_capstyle='round', alpha=0.9)
    for ref, num, net, l, polys in d['pads']:
        if l != L: continue
        for p in polys:
            ax.add_patch(Polygon(p, closed=True, fc=col(net), ec='k', lw=0.3, alpha=0.95))
    for x, y, s, net in d['vias']:
        ax.add_patch(Circle((x, y), s / 2, fc=col(net), ec='k', lw=0.3))
    side = 'B.Cu' if L == 'B.Cu' else ('F.Cu' if L == 'F.Cu' else None)
    for ref, fl, x, y, pts in d['fps']:
        if side and fl != side: continue
        for p in pts:
            ax.add_patch(Polygon(p, closed=True, fill=False, ec='#999999' if not side else '#5050ff', lw=0.6))
        if x0 <= x <= x1 and y0 <= y <= y1 and (side or len(pts)):
            ax.text(x, y, ref, fontsize=6, ha='center', va='center', color='#000080' if fl == 'F.Cu' else '#800080')
    for s, sx, sy, ex, ey in d['edges']:
        if s == 'Circle':
            import math
            ax.add_patch(Circle((sx, sy), math.hypot(ex - sx, ey - sy), fill=False, ec='orange', lw=1))
        else:
            ax.plot([sx, ex], [sy, ey], color='orange', lw=1)
    for bx in boxes:
        ax.add_patch(Rectangle((bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1], fill=False, ec='magenta', lw=1.2))
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect('equal'); ax.set_title(L)
    ax.grid(True, lw=0.2); ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=110)
