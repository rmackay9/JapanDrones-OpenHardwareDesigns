# KiCad python: localbus.py board out x0,y0,x1,y1 net1,net2,...  - rip the nets inside the box, route all orders, keep best
import sys, math, itertools
sys.path.insert(0, r'SCRATCH')
import pcbnew
from router import Router
mm = pcbnew.ToMM
LAYERS = ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu']
src, out = sys.argv[1], sys.argv[2]
X0, Y0, X1, Y1 = map(float, sys.argv[3].split(','))
names = sys.argv[4].split(',')
inside = lambda x, y: X0 <= x <= X1 and Y0 <= y <= Y1
best = None
for order in itertools.permutations(names):
    b = pcbnew.LoadBoard(src)
    outline = [s for s in b.GetDrawings() if s.GetLayer() == pcbnew.Edge_Cuts and s.GetClass() == 'PCB_SHAPE' and s.GetShape() == pcbnew.SHAPE_T_RECT][0]
    EDGE = (mm(outline.GetStart().x), mm(outline.GetEnd().x), mm(outline.GetStart().y), mm(outline.GetEnd().y))
    for t in list(b.GetTracks()):
        if t.GetNetname() not in names: continue
        if t.GetClass() == 'PCB_VIA':
            if inside(mm(t.GetPosition().x), mm(t.GetPosition().y)): b.Delete(t)
        elif inside(mm(t.GetStart().x), mm(t.GetStart().y)) and inside(mm(t.GetEnd().x), mm(t.GetEnd().y)):
            b.Delete(t)
    fails = 0
    for n in order:
        net = b.FindNet(n); nc = net.GetNetCode()
        terms = []
        for f in b.GetFootprints():
            for p in f.Pads():
                if p.GetNetCode() == nc:
                    q = p.GetPosition(); terms.append((mm(q.x), mm(q.y), [b.GetLayerName(l) for l in p.GetLayerSet().CuStack() if b.GetLayerName(l) in LAYERS]))
        for t in b.GetTracks():
            if t.GetNetCode() != nc: continue
            if t.GetClass() == 'PCB_VIA': terms.append((mm(t.GetPosition().x), mm(t.GetPosition().y), LAYERS))
            else:
                for q in (t.GetStart(), t.GetEnd()): terms.append((mm(q.x), mm(q.y), [t.GetLayerName()]))
        clusters = []
        for p in terms:
            hit = [c for c in clusters if any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.3 for q in c)]
            if hit:
                base = hit[0]
                for c in hit[1:]: base.extend(c); clusters.remove(c)
                base.append(p)
            else: clusters.append([p])
        # only clusters touching the box matter
        if len(clusters) < 2: continue
        tree = clusters[0]; rest = clusters[1:]
        while rest:
            _, ci, p, q = min(((math.hypot(p[0] - q[0], p[1] - q[1]), ci, p, q) for ci, c in enumerate(rest) for p in c for q in tree))
            ok = False
            for res, w, vd in ((0.05, 0.15, 0.45), (0.025, 0.127, 0.4)):
                rb = (min(X0, p[0], q[0]) - 1.5, min(Y0, p[1], q[1]) - 1.5, max(X1, p[0], q[0]) + 1.5, max(Y1, p[1], q[1]) + 1.5)
                r = Router(b, rb, LAYERS, EDGE, [], res=res)
                r.build(nc, w, 0.155, vd)
                path = r.route((p[0], p[1]), (q[0], q[1]), 4.0, p[2], q[2])
                if path:
                    r.commit(path, net, w, vd, 0.25 if vd > 0.42 else 0.2, (p[0], p[1]), (q[0], q[1])); ok = True; break
            if not ok: fails += 1
            tree.extend(rest.pop(ci))
    print('order', order, 'fails', fails)
    if best is None or fails < best:
        best = fails; pcbnew.SaveBoard(out, b)
    if fails == 0: break
print('best', best)
