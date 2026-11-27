# KiCad python: repair.py board drc.json out  - local rip-up & re-route of the copper DRC complains about
import os, sys, math, json, re
sys.path.insert(0, os.environ.get('SCRATCH', os.path.dirname(os.path.abspath(__file__))))
import pcbnew
from router import Router
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
d = json.load(open(sys.argv[2]))
LAYERS = ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu']
POUR = lambda n: n in ('GND', 'VBATT') or n.endswith('MVDD')
outline = [s for s in b.GetDrawings() if s.GetLayer() == pcbnew.Edge_Cuts and s.GetClass() == 'PCB_SHAPE' and s.GetShape() == pcbnew.SHAPE_T_RECT][0]
EDGE = (mm(outline.GetStart().x), mm(outline.GetEnd().x), mm(outline.GetStart().y), mm(outline.GetEnd().y))
HOLES = [(mm(s.GetCenter().x), mm(s.GetCenter().y), mm(s.GetRadius())) for s in b.GetDrawings()
         if s.GetLayer() == pcbnew.Edge_Cuts and s.GetClass() == 'PCB_SHAPE' and s.GetShape() == pcbnew.SHAPE_T_CIRCLE]
byuuid = {}
for t in b.GetTracks(): byuuid[t.m_Uuid.AsString()] = t
padbyuuid = {}
for f in b.GetFootprints():
    for p in f.Pads(): padbyuuid[p.m_Uuid.AsString()] = p
bad = []
for v in d['violations']:
    if v['severity'] != 'error': continue
    for it in v['items']:
        o = byuuid.get(it.get('uuid', ''))
        if o is not None and all(o.m_Uuid.AsString() != x.m_Uuid.AsString() for x in bad): bad.append(o)
log = []
gaps = []     # list of terminal lists to reconnect: each terminal (x, y, layers, netcode, width)
killed = set()

def at(pt, o):
    return abs(pt.x - o.x) < 2000 and abs(pt.y - o.y) < 2000   # 2 um

def stop_at(pt, layer, nc, exclude):
    vias = [v for v in b.GetTracks() if v.GetClass() == 'PCB_VIA' and v.GetNetCode() == nc and at(v.GetPosition(), pt) and v.m_Uuid.AsString() not in exclude]
    pads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() == nc and p.IsOnLayer(layer) and p.HitTest(pt)]
    nxt = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == nc and t.GetLayer() == layer and t.m_Uuid.AsString() not in exclude
           and (at(t.GetStart(), pt) or at(t.GetEnd(), pt))]
    return vias, pads, nxt

def walk(t, from_pt):
    """from track t, walk away from from_pt; return (terminal_point, layers) and list of walked tracks"""
    walked = [t]
    here = t.GetEnd() if at(t.GetStart(), from_pt) else t.GetStart()
    layer = t.GetLayer(); nc = t.GetNetCode()
    for _ in range(200):
        vias, pads, nxt = stop_at(here, layer, nc, {w.m_Uuid.AsString() for w in walked})
        if vias or pads or len(nxt) != 1:
            return (mm(here.x), mm(here.y), LAYERS if vias or (pads and pads[0].GetAttribute() == pcbnew.PAD_ATTRIB_PTH) else [b.GetLayerName(layer)]), walked
        t2 = nxt[0]; walked.append(t2)
        here = t2.GetEnd() if at(t2.GetStart(), here) else t2.GetStart()
    return None, walked

for o in bad:
    if o.m_Uuid.AsString() in killed: continue
    nc = o.GetNetCode(); n = o.GetNetname()
    if nc <= 0 or (POUR(n) and o.GetClass() == 'PCB_VIA'):
        continue
    terms = []
    width = 0.2
    if o.GetClass() == 'PCB_TRACK':
        width = mm(o.GetWidth())
        ta, wa = walk(o, o.GetEnd())       # towards start
        tb, wb = walk(o, o.GetStart())     # towards end
        for w in {x.m_Uuid.AsString(): x for x in wa + wb}.values():
            u = w.m_Uuid.AsString()
            if u not in killed: killed.add(u); b.Delete(w)
        terms = [x for x in (ta, tb) if x]
    else:   # signal via: remove it and the chains hanging off it
        p = o.GetPosition()
        att = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == nc and (at(t.GetStart(), p) or at(t.GetEnd(), p))]
        killed.add(o.m_Uuid.AsString()); b.Delete(o)
        for t in att:
            if t.m_Uuid.AsString() in killed: continue
            width = max(width, mm(t.GetWidth()))
            tt, ww = walk(t, p)
            for w in ww:
                u = w.m_Uuid.AsString()
                if u not in killed: killed.add(u); b.Delete(w)
            if tt: terms.append(tt)
    if len(terms) >= 2:
        gaps.append((nc, width, terms))

# DRC 'unconnected' pairs on signal nets
for u in d['unconnected_items']:
    pts = []
    nc = None
    for it in u['items']:
        m = re.search(r'\[([^\]]*)\]', it['description'])
        if not m or POUR(m.group(1)): pts = []; break
        net = b.FindNet(m.group(1)); nc = net.GetNetCode()
        lay = re.search(r' on (\S+\.Cu)', it['description'])
        L = LAYERS if ('Via' in it['description'] or 'PTH' in it['description'] or lay is None) else [lay.group(1)]
        pts.append((it['pos']['x'], it['pos']['y'], L))
    if len(pts) == 2 and nc:
        gaps.append((nc, 0.2, pts))

fails = 0
for nc, w, terms in gaps:
    net = [n for n in [b.FindNet(b.GetNetsByNetcode()[nc].GetNetname())]][0]
    tree = [terms[0]]
    for t in terms[1:]:
        q = min(tree, key=lambda q: math.hypot(q[0] - t[0], q[1] - t[1]))
        ok = False
        for grow, res, ww in ((3, 0.1, max(w, 0.15)), (8, 0.1, max(w, 0.15)), (3, 0.05, 0.15), (8, 0.05, 0.15), (16, 0.1, 0.15), (2, 0.025, 0.127), (5, 0.025, 0.127)):
            box = (min(t[0], q[0]) - grow, min(t[1], q[1]) - grow, max(t[0], q[0]) + grow, max(t[1], q[1]) + grow)
            r = Router(b, box, LAYERS, EDGE, HOLES, res=res)
            vd = 0.45 if ww > 0.13 else 0.4
            r.build(nc, ww, 0.155, vd)
            path = r.route((t[0], t[1]), (q[0], q[1]), 8.0, [l for l in t[2] if l in LAYERS], [l for l in q[2] if l in LAYERS])
            if path:
                r.commit(path, net, ww, vd, 0.25 if vd > 0.42 else 0.2, (t[0], t[1]), (q[0], q[1])); ok = True; break
        if not ok:
            fails += 1; log.append(f'  {net.GetNetname()}: no route ({t[0]:.2f},{t[1]:.2f}) -> ({q[0]:.2f},{q[1]:.2f})')
        tree.append(t)
log.append(f'repaired {len(gaps)} gaps, {fails} failed')
pcbnew.SaveBoard(sys.argv[3], b)
print('\n'.join(log))
