# KiCad python: islands.py board out - stitch GND fill islands that hold pads but no via, and VBATT ESC pours without vias
import pcbnew, sys, math
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
log = []
def seg_pt(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)
def clear_for_via(x, y, r, nc, clr=0.2):
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            lim = r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + (clr if t.GetNetCode() != nc else 0.25)
            if math.hypot(mm(p.x) - x, mm(p.y) - y) < lim: return False
        elif t.GetNetCode() != nc:
            if seg_pt(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), x, y) < r + mm(t.GetWidth()) / 2 + clr: return False
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == nc and p.GetAttribute() not in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                bb = p.GetBoundingBox()
                if mm(bb.GetLeft()) - r < x < mm(bb.GetRight()) + r and mm(bb.GetTop()) - r < y < mm(bb.GetBottom()) + r: return False  # no via in pad
                continue
            bb = p.GetBoundingBox()
            if mm(bb.GetLeft()) - r - clr < x < mm(bb.GetRight()) + r + clr and mm(bb.GetTop()) - r - clr < y < mm(bb.GetBottom()) + r + clr: return False
        for z in f.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowVias() and z.Outline().Contains(V(x, y)): return False
    return True
def add_via(x, y, net):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v)
gnd = b.FindNet('GND'); vb = b.FindNet('VBATT')
vias = lambda nc: [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == nc]
tht = lambda nc: [p for p in b.GetPads() if p.GetNetCode() == nc and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetCode() not in (gnd.GetNetCode(), vb.GetNetCode()): continue
    net = z.GetNet(); nc = net.GetNetCode()
    for l in z.GetLayerSet().CuStack():
        if l not in (pcbnew.F_Cu, pcbnew.B_Cu): continue
        fp = z.GetFilledPolysList(l)
        for i in range(fp.OutlineCount()):
            o = fp.Outline(i)
            if any(o.PointInside(v.GetPosition()) for v in vias(nc)) or any(o.PointInside(p.GetPosition()) for p in tht(nc)): continue
            pads = [p for p in b.GetPads() if p.GetNetCode() == nc and p.IsOnLayer(l) and o.PointInside(p.GetPosition())]
            if not pads and z.GetZoneName() not in ('VBATT_ESC', 'VBATT_ESC1', 'VBATT_ESC2', 'VBATT_ESC3'): continue
            # island with pads but no via: drop a via inside the island
            bb = o.BBox(); added = 0
            y = mm(bb.GetTop()) + 0.35
            while y < mm(bb.GetBottom()) - 0.35 and added < 2:
                x = mm(bb.GetLeft()) + 0.35
                while x < mm(bb.GetRight()) - 0.35 and added < 2:
                    if o.PointInside(V(x, y)) and all(o.PointInside(V(x + dx, y + dy)) for dx, dy in ((0.35, 0), (-0.35, 0), (0, 0.35), (0, -0.35))) \
                            and clear_for_via(x, y, 0.3, nc):
                        add_via(x, y, net); added += 1
                    x += 0.1
                y += 0.1
            log.append(f'{z.GetZoneName()} {b.GetLayerName(l)} island at x {mm(bb.GetLeft()):.1f}..{mm(bb.GetRight()):.1f} y {mm(bb.GetTop()):.1f}..{mm(bb.GetBottom()):.1f} pads {[p.GetParentFootprint().GetReference() for p in pads][:4]}: +{added} vias')
pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
