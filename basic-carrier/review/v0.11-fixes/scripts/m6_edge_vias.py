# KiCad python: m6_edge_vias.py board -- review M6: VBATT/MVDD/phase vias whose copper is within 0.5 mm of the
# board outline are pushed inward just far enough (+0.03 mm), or deleted if that spot is not clear.
# Tracks ending at a moved via are dragged with it.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); b = B.b
def power(net): return net == 'VBATT' or (net.startswith('/VimDrones') and ('/MVDD' in net or '/FD6288_VS' in net))
log = []
for v in list(B.vias()):
    net = v.GetNetname()
    if not power(net): continue
    x, y = mm(v.GetPosition().x), mm(v.GetPosition().y); r = mm(v.GetWidth(pcbnew.F_Cu)) / 2
    lim = 0.5 + r + 0.03
    nx = min(max(x, EDGE[0] + lim), EDGE[1] - lim); ny = min(max(y, EDGE[2] + lim), EDGE[3] - lim)
    if (nx, ny) == (x, y): continue
    ends = [t for t in B.tracks() if t.GetNetname() == net and any(abs(mm(e.x) - x) < 0.01 and abs(mm(e.y) - y) < 0.01 for e in (t.GetStart(), t.GetEnd()))]
    why = B.obstacles(nx, ny, r, net, CU, clr=0.2, edge=0.5, skip=[v] + ends, zones=False)
    why = [w for w in why if not w.startswith('via-same')]
    if why and not ends:
        b.Delete(v); log.append(f'{net} ({x:.2f},{y:.2f}) deleted ({why[0]})'); continue
    v.SetPosition(V(nx, ny))
    for t in ends:
        if abs(mm(t.GetStart().x) - x) < 0.01 and abs(mm(t.GetStart().y) - y) < 0.01: t.SetStart(V(nx, ny))
        else: t.SetEnd(V(nx, ny))
    log.append(f'{net} ({x:.2f},{y:.2f}) -> ({nx:.2f},{ny:.2f})' + (f' [check: {why[0]}]' if why else ''))
B.save(); print('\n'.join(log))
