# KiCad python: stitchpour.py board out ZONENAME[,..] - add VBATT vias where an F.Cu pour overlaps the In2+In3 VBATT fill
import pcbnew, sys, math
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
names = sys.argv[3].split(',')
vb = b.FindNet('VBATT'); nc = vb.GetNetCode()
def seg_pt(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)
def ok(x, y, r=0.3, clr=0.2):
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            if math.hypot(mm(p.x) - x, mm(p.y) - y) < r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + (clr if t.GetNetCode() != nc else 0.3): return False
        elif t.GetNetCode() != nc and seg_pt(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), x, y) < r + mm(t.GetWidth()) / 2 + clr:
            return False
    for p in b.GetPads():
        bb = p.GetBoundingBox()
        m = r + (0.05 if p.GetNetCode() == nc else clr)
        if mm(bb.GetLeft()) - m < x < mm(bb.GetRight()) + m and mm(bb.GetTop()) - m < y < mm(bb.GetBottom()) + m: return False
    return True
inner = {}
for z in b.Zones():
    if z.GetNetCode() == nc and not z.GetIsRuleArea():
        for l in (pcbnew.In2_Cu, pcbnew.In3_Cu):
            if z.GetLayerSet().Contains(l): inner.setdefault(l, []).append(z.GetFilledPolysList(l))
def in_inner(x, y):
    return all(any(fp.Contains(V(x, y)) for fp in inner.get(l, [])) for l in (pcbnew.In2_Cu, pcbnew.In3_Cu))
for z in b.Zones():
    if z.GetZoneName() not in names: continue
    fp = z.GetFilledPolysList(pcbnew.F_Cu); bb = z.Outline().BBox(); added = 0
    y = mm(bb.GetTop()) + 0.4
    while y < mm(bb.GetBottom()) - 0.4 and added < 6:
        x = mm(bb.GetLeft()) + 0.4
        while x < mm(bb.GetRight()) - 0.4 and added < 6:
            if fp.Contains(V(x, y)) and in_inner(x, y) and ok(x, y):
                v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(vb)
                v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v); added += 1
            x += 0.2
        y += 0.2
    print(z.GetZoneName(), 'added', added, 'VBATT vias')
# general: tie F + In2 + In3 VBATT fills together inside a region
if len(sys.argv) > 4:
    rx0, ry0, rx1, ry1 = map(float, sys.argv[4].split(','))
    fF = [z.GetFilledPolysList(pcbnew.F_Cu) for z in b.Zones() if z.GetNetCode() == nc and not z.GetIsRuleArea() and z.GetLayerSet().Contains(pcbnew.F_Cu)]
    added = 0; placed = []
    y = ry0
    while y < ry1 and added < 24:
        x = rx0
        while x < rx1 and added < 24:
            if any(f.Contains(V(x, y)) for f in fF) and in_inner(x, y) and all(math.hypot(x - a, y - c) > 1.5 for a, c in placed) and ok(x, y):
                v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(vb)
                v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v); added += 1; placed.append((x, y))
            x += 0.25
        y += 0.25
    print('region', sys.argv[4], 'added', added, 'VBATT vias')
pcbnew.SaveBoard(sys.argv[2], b)
