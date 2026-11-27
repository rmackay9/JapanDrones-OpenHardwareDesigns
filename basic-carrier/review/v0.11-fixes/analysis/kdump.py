# KiCad python: kdump.py board.kicad_pcb out.json  -- full dump for analysis
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
def poly_pts(sp):
    res = []
    for oi in range(sp.OutlineCount()):
        o = sp.Outline(oi)
        holes = [[[mm(sp.Hole(oi, h).CPoint(i).x), mm(sp.Hole(oi, h).CPoint(i).y)] for i in range(sp.Hole(oi, h).PointCount())] for h in range(sp.HoleCount(oi))]
        res.append({'o': [[mm(o.CPoint(i).x), mm(o.CPoint(i).y)] for i in range(o.PointCount())], 'h': holes})
    return res
out = {'tracks': [], 'vias': [], 'pads': [], 'zones': [], 'edges': []}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        out['vias'].append({'x': mm(p.x), 'y': mm(p.y), 'd': mm(t.GetWidth(pcbnew.F_Cu)), 'drill': mm(t.GetDrillValue()),
                            'net': t.GetNetname(), 'top': b.GetLayerName(t.TopLayer()), 'bot': b.GetLayerName(t.BottomLayer()),
                            'id': str(t.m_Uuid.AsString())})
    elif t.GetClass() == 'PCB_TRACK':
        s, e = t.GetStart(), t.GetEnd()
        out['tracks'].append({'x0': mm(s.x), 'y0': mm(s.y), 'x1': mm(e.x), 'y1': mm(e.y), 'w': mm(t.GetWidth()),
                              'layer': t.GetLayerName(), 'net': t.GetNetname(), 'id': str(t.m_Uuid.AsString())})
    else:
        s, e = t.GetStart(), t.GetEnd()
        out['tracks'].append({'x0': mm(s.x), 'y0': mm(s.y), 'x1': mm(e.x), 'y1': mm(e.y), 'w': mm(t.GetWidth()),
                              'layer': t.GetLayerName(), 'net': t.GetNetname(), 'id': str(t.m_Uuid.AsString()), 'arc': 1})
for fp in b.GetFootprints():
    for pad in fp.Pads():
        q = pad.GetPosition()
        layers = {}
        for l in pad.GetLayerSet().CuStack():
            layers[b.GetLayerName(l)] = poly_pts(pad.GetEffectivePolygon(l))
        out['pads'].append({'ref': fp.GetReference(), 'num': pad.GetNumber(), 'net': pad.GetNetname(), 'x': mm(q.x), 'y': mm(q.y),
                            'sx': mm(pad.GetSizeX()), 'sy': mm(pad.GetSizeY()), 'drill': mm(pad.GetDrillSizeX()),
                            'attr': int(pad.GetAttribute()), 'side': fp.GetLayerName(), 'layers': layers})
for z in b.Zones():
    zd = {'name': z.GetZoneName(), 'net': z.GetNetname(), 'layers': [b.GetLayerName(l) for l in z.GetLayerSet().CuStack()],
          'rule': bool(z.GetIsRuleArea()), 'prio': z.GetAssignedPriority(), 'outline': poly_pts(z.Outline()), 'fill': {},
          'id': str(z.m_Uuid.AsString())}
    if z.IsFilled() and not z.GetIsRuleArea():
        for l in z.GetLayerSet().CuStack():
            zd['fill'][b.GetLayerName(l)] = poly_pts(z.GetFilledPolysList(l))
    out['zones'].append(zd)
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        out['edges'].append([d.GetShapeStr(), mm(d.GetStart().x), mm(d.GetStart().y), mm(d.GetEnd().x), mm(d.GetEnd().y)])
json.dump(out, open(sys.argv[2], 'w'))
print('ok', {k: len(v) for k, v in out.items()})
