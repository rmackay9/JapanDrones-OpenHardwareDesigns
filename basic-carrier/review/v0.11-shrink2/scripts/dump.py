# run with KiCad python: dump.py board.kicad_pcb out.json x0,y0,x1,y1
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
mm = pcbnew.ToMM
def inb(x, y, m=3): return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m
out = {'tracks': [], 'vias': [], 'pads': [], 'fps': [], 'zones': [], 'fills': [], 'edges': []}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        if inb(mm(p.x), mm(p.y)):
            out['vias'].append([mm(p.x), mm(p.y), mm(t.GetWidth(pcbnew.F_Cu)), t.GetNetname()])
    else:
        s, e = t.GetStart(), t.GetEnd()
        if inb(mm(s.x), mm(s.y)) or inb(mm(e.x), mm(e.y)):
            out['tracks'].append([mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth()), t.GetLayerName(), t.GetNetname()])
def poly_pts(sp):
    res = []
    for oi in range(sp.OutlineCount()):
        o = sp.Outline(oi)
        res.append([[mm(o.CPoint(i).x), mm(o.CPoint(i).y)] for i in range(o.PointCount())])
    return res
for fp in b.GetFootprints():
    p = fp.GetPosition()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
    pts = poly_pts(cy) if cy.OutlineCount() else []
    if inb(mm(p.x), mm(p.y), 15):
        out['fps'].append([fp.GetReference(), fp.GetLayerName(), mm(p.x), mm(p.y), pts])
    for pad in fp.Pads():
        q = pad.GetPosition()
        if not inb(mm(q.x), mm(q.y)): continue
        for l in pad.GetLayerSet().CuStack():
            sp = pad.GetEffectivePolygon(l)
            out['pads'].append([fp.GetReference(), pad.GetNumber(), pad.GetNetname(), b.GetLayerName(l), poly_pts(sp)])
for z in b.Zones():
    for l in z.GetLayerSet().CuStack():
        ln = b.GetLayerName(l)
        out['zones'].append([z.GetNetname(), ln, poly_pts(z.Outline()), z.GetIsRuleArea()])
        if z.IsFilled() and not z.GetIsRuleArea():
            f = z.GetFilledPolysList(l)
            out['fills'].append([z.GetNetname(), ln, poly_pts(f)])
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        out['edges'].append([d.GetShapeStr(), mm(d.GetStart().x), mm(d.GetStart().y), mm(d.GetEnd().x), mm(d.GetEnd().y)])
json.dump(out, open(sys.argv[2], 'w'))
print('ok', {k: len(v) for k, v in out.items()})
