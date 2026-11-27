# KiCad python. dump.py board.kicad_pcb out.json   (read-only: never saves)
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
CU = [l for l in b.GetEnabledLayers().CuStack()]
LN = {l: b.GetLayerName(l) for l in CU}

def polyset(sp):
    res = []
    for oi in range(sp.OutlineCount()):
        o = sp.Outline(oi)
        holes = []
        for h in range(sp.HoleCount(oi)):
            hh = sp.Hole(oi, h)
            holes.append([[mm(hh.CPoint(i).x), mm(hh.CPoint(i).y)] for i in range(hh.PointCount())])
        res.append({'o': [[mm(o.CPoint(i).x), mm(o.CPoint(i).y)] for i in range(o.PointCount())], 'h': holes})
    return res

out = {'layers': [LN[l] for l in CU], 'tracks': [], 'vias': [], 'pads': [], 'zones': [], 'outline': None, 'fps': [], 'drawings': []}
for t in b.GetTracks():
    c = t.GetClass()
    if c == 'PCB_VIA':
        p = t.GetPosition()
        lay = {}
        for l in CU:
            if t.IsOnLayer(l):
                lay[LN[l]] = {'d': mm(t.GetWidth(l)), 'flashed': bool(t.FlashLayer(l))}
        out['vias'].append({'x': mm(p.x), 'y': mm(p.y), 'drill': mm(t.GetDrillValue()), 'net': t.GetNetname(),
                            'layers': lay, 'type': int(t.GetViaType()), 'id': t.m_Uuid.AsString()})
    else:
        s, e = t.GetStart(), t.GetEnd()
        d = {'x0': mm(s.x), 'y0': mm(s.y), 'x1': mm(e.x), 'y1': mm(e.y), 'w': mm(t.GetWidth()),
             'layer': t.GetLayerName(), 'net': t.GetNetname(), 'id': t.m_Uuid.AsString(), 'len': mm(t.GetLength())}
        if c == 'PCB_ARC':
            m = t.GetMid(); d['arc'] = [mm(m.x), mm(m.y)]
            sp = pcbnew.SHAPE_POLY_SET()
            t.TransformShapeToPolygon(sp, t.GetLayer(), 0, 2000, pcbnew.ERROR_INSIDE)
            d['poly'] = polyset(sp)
        out['tracks'].append(d)
for fp in b.GetFootprints():
    p = fp.GetPosition()
    cy = fp.GetCourtyard(fp.GetLayer())
    bb = fp.GetBoundingBox(False)
    out['fps'].append({'ref': fp.GetReference(), 'val': fp.GetValue(), 'fpid': fp.GetFPID().GetUniStringLibItemName(),
                       'x': mm(p.x), 'y': mm(p.y), 'rot': fp.GetOrientationDegrees(), 'side': fp.GetLayerName(),
                       'court': polyset(cy), 'bbox': [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]})
    for pad in fp.Pads():
        q = pad.GetPosition()
        layers = {}
        for l in [x for x in pad.GetLayerSet().CuStack() if x in LN]:
            layers[LN[l]] = polyset(pad.GetEffectivePolygon(l, pcbnew.ERROR_INSIDE))
        out['pads'].append({'ref': fp.GetReference(), 'num': pad.GetNumber(), 'net': pad.GetNetname(), 'x': mm(q.x), 'y': mm(q.y),
                            'sx': mm(pad.GetSizeX()), 'sy': mm(pad.GetSizeY()), 'drill': mm(pad.GetDrillSizeX()), 'drilly': mm(pad.GetDrillSizeY()),
                            'attr': int(pad.GetAttribute()), 'side': fp.GetLayerName(), 'layers': layers,
                            'pinfn': pad.GetPinFunction(), 'rot': pad.GetOrientationDegrees()})
for z in b.Zones():
    zd = {'name': z.GetZoneName(), 'net': z.GetNetname(), 'layers': [LN[l] for l in z.GetLayerSet().CuStack() if l in LN],
          'rule': bool(z.GetIsRuleArea()), 'prio': z.GetAssignedPriority(), 'outline': polyset(z.Outline()), 'fill': {},
          'id': z.m_Uuid.AsString(), 'clear': mm(z.GetLocalClearance() or 0) if not z.GetIsRuleArea() else None,
          'minw': mm(z.GetMinThickness()), 'padconn': int(z.GetPadConnection()), 'island': int(z.GetIslandRemovalMode()),
          'thgap': mm(z.GetThermalReliefGap()), 'thspoke': mm(z.GetThermalReliefSpokeWidth())}
    if z.GetIsRuleArea():
        zd['ko'] = {'tracks': z.GetDoNotAllowTracks(), 'vias': z.GetDoNotAllowVias(), 'pads': z.GetDoNotAllowPads(),
                    'fill': z.GetDoNotAllowZoneFills(), 'fp': z.GetDoNotAllowFootprints()}
    elif z.IsFilled():
        for l in [x for x in z.GetLayerSet().CuStack() if x in LN]:
            zd['fill'][LN[l]] = polyset(z.GetFilledPolysList(l))
    out['zones'].append(zd)
op = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(op, True)
out['outline'] = polyset(op)
for d in b.GetDrawings():
    try:
        s, e = d.GetStart(), d.GetEnd()
        out['drawings'].append({'layer': d.GetLayerName(), 'cls': d.GetClass(), 'shape': d.GetShapeStr() if hasattr(d, 'GetShapeStr') else '',
                                's': [mm(s.x), mm(s.y)], 'e': [mm(e.x), mm(e.y)]})
    except Exception:
        pass
ds = b.GetDesignSettings()
out['ds'] = {'min_clear': mm(ds.m_MinClearance), 'min_track': mm(ds.m_TrackMinWidth), 'min_annular': mm(ds.m_ViasMinAnnularWidth),
             'min_via': mm(ds.m_ViasMinSize), 'min_drill': mm(ds.m_MinThroughDrill), 'hole2hole': mm(ds.m_HoleToHoleMin),
             'edge': mm(ds.m_CopperEdgeClearance), 'hole_clear': mm(ds.m_HoleClearance), 'thick': mm(ds.GetBoardThickness())}
json.dump(out, open(sys.argv[2], 'w'))
print('ok', {k: (len(v) if hasattr(v, '__len__') else v) for k, v in out.items()})
