# KiCad python: finalfix.py board drc.json out - connect orphan GND pads, stitch VBATT ESC pours, route leftover gaps wide
import sys, math, json, re
sys.path.insert(0, r'SCRATCH')
import pcbnew
from router import Router
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
d = json.load(open(sys.argv[2]))
LAYERS = ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu']
outline = [s for s in b.GetDrawings() if s.GetLayer() == pcbnew.Edge_Cuts and s.GetClass() == 'PCB_SHAPE' and s.GetShape() == pcbnew.SHAPE_T_RECT][0]
EDGE = (mm(outline.GetStart().x), mm(outline.GetEnd().x), mm(outline.GetStart().y), mm(outline.GetEnd().y))
HOLES = [(mm(s.GetCenter().x), mm(s.GetCenter().y), mm(s.GetRadius())) for s in b.GetDrawings()
         if s.GetLayer() == pcbnew.Edge_Cuts and s.GetClass() == 'PCB_SHAPE' and s.GetShape() == pcbnew.SHAPE_T_CIRCLE]
log = []
gnd = b.FindNet('GND'); vb = b.FindNet('VBATT')

def route(nc, net, p, q, pl, ql, w=0.2):
    for grow, res, ww, vd in ((3, 0.1, w, 0.45), (10, 0.1, w, 0.45), (25, 0.1, w, 0.45), (3, 0.05, 0.15, 0.45), (2, 0.025, 0.127, 0.4), (6, 0.025, 0.127, 0.4)):
        box = (min(p[0], q[0]) - grow, min(p[1], q[1]) - grow, max(p[0], q[0]) + grow, max(p[1], q[1]) + grow)
        r = Router(b, box, LAYERS, EDGE, HOLES, res=res)
        r.build(nc, ww, 0.155, vd)
        path = r.route(p, q, 6.0, pl, ql)
        if path:
            r.commit(path, net, ww, vd, 0.25 if vd > 0.42 else 0.2, p, q); return True
    return False

# 1) GND / VBATT pads sitting in a fill island without via, THT pad or track: route them to the nearest via of their net
for nc_net in (gnd, vb):
    nc = nc_net.GetNetCode()
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == nc]
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetCode() != nc: continue
        for l in z.GetLayerSet().CuStack():
            if l not in (pcbnew.F_Cu, pcbnew.B_Cu): continue
            fp = z.GetFilledPolysList(l)
            for i in range(fp.OutlineCount()):
                o = fp.Outline(i)
                if any(o.PointInside(v.GetPosition()) for v in vias): continue
                if any(o.PointInside(p.GetPosition()) for p in b.GetPads() if p.GetNetCode() == nc and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH): continue
                pads = [p for p in b.GetPads() if p.GetNetCode() == nc and p.IsOnLayer(l) and o.PointInside(p.GetPosition())]
                pads = [p for p in pads if not any(t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == nc and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())) for t in b.GetTracks())]
                for p in pads[:1]:
                    q = p.GetPosition(); px, py = mm(q.x), mm(q.y)
                    near = sorted(vias, key=lambda v: math.hypot(mm(v.GetPosition().x) - px, mm(v.GetPosition().y) - py))[:4]
                    ok = False
                    for v in near:
                        vx, vy = mm(v.GetPosition().x), mm(v.GetPosition().y)
                        if route(nc, nc_net, (px, py), (vx, vy), [b.GetLayerName(l)], LAYERS, 0.3): ok = True; break
                    log.append(f'{nc_net.GetNetname()} pad {p.GetParentFootprint().GetReference()}.{p.GetNumber()} -> via: {"ok" if ok else "FAILED"}')

# 2) leftover unconnected signal pairs from DRC, with a wide search
for u in d['unconnected_items']:
    its = u['items']
    m = [re.search(r'\[([^\]]*)\]', i['description']) for i in its]
    if not all(m) or m[0].group(1) in ('GND', 'VBATT'): continue
    net = b.FindNet(m[0].group(1)); nc = net.GetNetCode()
    ends = []
    for i in its:
        lay = re.search(r' on (\S+\.Cu)', i['description'])
        L = LAYERS if ('Via' in i['description'] or lay is None) else [lay.group(1)]
        ends.append(((i['pos']['x'], i['pos']['y']), L))
    ok = route(nc, net, ends[0][0], ends[1][0], ends[0][1], ends[1][1], 0.2)
    log.append(f'{net.GetNetname()}: {"ok" if ok else "FAILED"}')
pcbnew.SaveBoard(sys.argv[3], b)
print('\n'.join(log))
