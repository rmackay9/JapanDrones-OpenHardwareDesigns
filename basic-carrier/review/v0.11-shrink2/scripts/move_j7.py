# KiCad python: move_j7.py in out [layers] [box-margin] [box-ymax] - move J7 (LED CH3) under the back-left ESC capacitor block, mirror of J6
import sys, math
sys.path.insert(0, '.')
import pcbnew
from router import connect
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
LAYERS = sys.argv[3].split(',') if len(sys.argv) > 3 else ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu']
EDGE = (100.11, 191.25, 50.0, 140.0)
HOLES = [(102.61, 52.5, 1.6), (188.75, 52.5, 1.6), (102.61, 137.5, 1.6), (188.75, 137.5, 1.6),
         (130, 80, 0.9), (160, 80, 0.9), (130, 110, 0.9), (160, 110, 0.9)]
F = {f.GetReference(): f for f in b.GetFootprints()}
J = F['J7']
TX, TY = 291.36 - 185.5, 122.6          # mirror of J6's courtyard centre about the board centre line
log = []
def P(pt): return (round(mm(pt.x), 4), round(mm(pt.y), 4))
def items_at(pt, net, layer, skip):
    n = 0; via = False
    for o in b.GetTracks():
        if o is skip or o.GetNetCode() != net: continue
        if o.GetClass() == 'PCB_VIA':
            if P(o.GetPosition()) == pt: n += 1; via = True
        elif o.GetLayer() == layer and (P(o.GetStart()) == pt or P(o.GetEnd()) == pt): n += 1
    for f in b.GetFootprints():
        if f is J: continue
        for p in f.Pads():
            if p.GetNetCode() == net and p.IsOnLayer(layer) and p.HitTest(V(*pt)): n += 1
    return n, via

ends = {}
def tracks_at(pt, net):
    return [o for o in b.GetTracks() if o.GetClass() == 'PCB_TRACK' and o.GetNetCode() == net and (P(o.GetStart()) == pt or P(o.GetEnd()) == pt)]
for p in J.Pads():
    net = p.GetNetCode()
    touch = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == net and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()))]
    frontier = []
    for t in touch:
        for e in (t.GetStart(), t.GetEnd()):
            if not p.HitTest(e): frontier.append((P(e), t.GetLayer()))
        b.Delete(t)
    out = []
    while frontier:
        pt, layer = frontier.pop()
        n, via = items_at(pt, net, layer, None)
        nxt = tracks_at(pt, net)
        if n == 1 and not via and len(nxt) == 1:
            t = nxt[0]; o = P(t.GetEnd()) if P(t.GetStart()) == pt else P(t.GetStart()); L = t.GetLayer(); b.Delete(t); frontier.append((o, L)); continue
        out.append((pt, via, b.GetLayerName(layer), n))
    ends[p.GetNumber()] = out[0] if out else None
    log.append(f'pad {p.GetNumber()} {p.GetNetname()}: old route now ends at {out}')

J.Move(V(0, 0))
bb = J.GetCourtyard(pcbnew.F_CrtYd).BBox()
cx, cy = (mm(bb.GetLeft()) + mm(bb.GetRight())) / 2, (mm(bb.GetTop()) + mm(bb.GetBottom())) / 2
J.Move(V(TX - cx, TY - cy))
bb = J.GetCourtyard(pcbnew.F_CrtYd).BBox()
CB = (mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom()))
log.append(f'J7 courtyard now x {CB[0]:.2f}..{CB[1]:.2f} y {CB[2]:.2f}..{CB[3]:.2f}, fp at ({mm(J.GetPosition().x):.2f},{mm(J.GetPosition().y):.2f})')

def seg_pt(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)
def clear_for_via(x, y, r, netcode, clr=0.2):
    if any(mm(q.GetBoundingBox().GetLeft()) - r - 0.25 < x < mm(q.GetBoundingBox().GetRight()) + r + 0.25 and mm(q.GetBoundingBox().GetTop()) - r - 0.25 < y < mm(q.GetBoundingBox().GetBottom()) + r + 0.25 for q in J.Pads()): return False
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            need = r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + (clr if t.GetNetCode() != netcode else 0.3)
            if math.hypot(mm(p.x) - x, mm(p.y) - y) < need: return False
        elif t.GetNetCode() != netcode:
            if seg_pt(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), x, y) < r + mm(t.GetWidth()) / 2 + clr: return False
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == netcode and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD: continue
            pb = p.GetBoundingBox()
            if mm(pb.GetLeft()) - r - clr < x < mm(pb.GetRight()) + r + clr and mm(pb.GetTop()) - r - clr < y < mm(pb.GetBottom()) + r + clr: return False
    for hx, hy, hr in HOLES:
        if math.hypot(hx - x, hy - y) < hr + r + 0.3: return False
    return x > EDGE[0] + 0.6
def add_via(x, y, net, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v); return v

# stitching vias under the new spot -> next to it
removed = []
for t in list(b.GetTracks()):
    if t.GetClass() != 'PCB_VIA': continue
    x, y = mm(t.GetPosition().x), mm(t.GetPosition().y)
    r = mm(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.25
    if any(mm(q.GetBoundingBox().GetLeft()) - r < x < mm(q.GetBoundingBox().GetRight()) + r and mm(q.GetBoundingBox().GetTop()) - r < y < mm(q.GetBoundingBox().GetBottom()) + r for q in J.Pads()):
        tracked = any(o.GetClass() == 'PCB_TRACK' and o.GetNetCode() == t.GetNetCode() and (o.GetStart() == t.GetPosition() or o.GetEnd() == t.GetPosition()) for o in b.GetTracks())
        removed.append((x, y, t.GetNet(), mm(t.GetWidth(pcbnew.F_Cu)), mm(t.GetDrillValue()), tracked)); b.Delete(t)
log.append('vias removed from under J7: ' + ', '.join(f'{n.GetNetname()}@({x:.2f},{y:.2f}){" TRACKED" if tr else ""}' for x, y, n, d, dr, tr in removed))
back = 0
if [r for r in removed if r[5]]: raise SystemExit('tracked via under J7 pads')
add_via(104.62, 122.01, removed[0][2], removed[0][3], removed[0][4]); back = 1   # one MVDD stitch back under the body (the other spot is isolated)
for x, y, net, d, drill, tr in []:
    for rad in [0.3 * k for k in range(1, 30)]:
        hit = None
        for a in range(0, 360, 15):
            vx, vy = x + rad * math.cos(math.radians(a)), y + rad * math.sin(math.radians(a))
            if clear_for_via(vx, vy, d / 2, net.GetNetCode()): hit = (vx, vy); break
        if hit: add_via(hit[0], hit[1], net, d, drill); back += 1; break
log.append(f're-added {back} of {len(removed)} next to J7')

# signal / +5.2V: hand-routed. Both hop under the HO1 gate track on B.Cu; +5.2V then joins the In2 +5.2V track in the GND plane.
def trk(x0, y0, x1, y1, w, layer, net):
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(x0, y0)); t.SetEnd(V(x1, y1)); t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)
CH = '/Connectors/FMU_CH3_PROT'
pd = {p.GetNumber(): (mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in J.Pads()}
# old F.Cu hop 112.4 -> 118.4 is kept; remove the router's B.Cu (112.4,119.1)->(107.9,119.4) etc. if present (fresh run: not present)
x2, y2 = pd['2']
add_via(x2, 119.0, b.FindNet(CH), 0.45, 0.25)
trk(x2, y2, x2, 119.0, 0.25, pcbnew.F_Cu, CH)
trk(x2, 119.0, x2 + 0.45, 119.45, 0.25, pcbnew.B_Cu, CH)
trk(x2 + 0.45, 119.45, 112.05, 119.45, 0.25, pcbnew.B_Cu, CH)
trk(112.05, 119.45, 112.4, 119.1, 0.25, pcbnew.B_Cu, CH)
add_via(112.4, 119.1, b.FindNet(CH), 0.45, 0.25)
trk(112.4, 119.1, 114.9, 118.9, 0.25, pcbnew.F_Cu, CH)
trk(114.9, 118.9, 118.4, 119.4, 0.25, pcbnew.F_Cu, CH)
x1, y1 = pd['1']
P5 = '+5.2V'
add_via(x1, 118.6, b.FindNet(P5), 0.45, 0.25)
trk(x1, y1, x1, 118.6, 0.4, pcbnew.F_Cu, P5)
trk(x1, 118.6, 109.6, 118.6, 0.4, pcbnew.B_Cu, P5)
add_via(109.6, 118.6, b.FindNet(P5), 0.45, 0.25)
res = connect(b, P5, (109.6, 118.6), (113.1, 116.24), 0.4, ['In2.Cu'], (108.5, 114.5, 115, 120), EDGE, HOLES, start_layers=['In2.Cu'], goal_layers=['In2.Cu'])
log.append('  +5.2V In2 tie: ' + ('NO ROUTE' if res is None else f'{len(res)} items'))

# GND pads: own via + short F.Cu track
gnd = b.FindNet('GND')
for p in J.Pads():
    if p.GetNetname() != 'GND': continue
    q = p.GetPosition(); gx, gy = mm(q.x), mm(q.y)
    cands = []
    for rad in [0.2 * k for k in range(5, 40)]:
        for a in range(0, 360, 15):
            vx, vy = gx + rad * math.cos(math.radians(a)), gy + rad * math.sin(math.radians(a))
            if clear_for_via(vx, vy, 0.3, gnd.GetNetCode()): cands.append((rad, vx, vy))
        if len(cands) > 40: break
    ok = False
    for rad, vx, vy in cands:
        v = add_via(vx, vy, gnd)
        if connect(b, 'GND', (gx, gy), (vx, vy), 0.4, ['F.Cu'], (min(gx, vx) - 3, min(gy, vy) - 3, max(gx, vx) + 3, max(gy, vy) + 3), EDGE, HOLES) is not None:
            ok = (round(vx, 2), round(vy, 2)); break
        b.Delete(v)
    if not ok:
        for p2 in J.Pads():
            if p2.GetNetname() == 'GND' and p2.GetNumber() != p.GetNumber() and abs(mm(p2.GetPosition().y) - gy) < 0.1:
                q2 = p2.GetPosition()
                r = connect(b, 'GND', (gx, gy), (mm(q2.x), mm(q2.y)), 0.4, ['F.Cu'], (101, gy - 1.6, 111, gy + 2.2), EDGE, HOLES)
                if r is not None: ok = f'track to pad {p2.GetNumber()} ({len(r)} items)'
    log.append(f'  pad {p.GetNumber()} GND: via {ok}')

# FD6288_VS1 (ESC3) ran straight through the new pad 4 spot: dog-leg it to the right of J7
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname().endswith('FD6288_VS1') and t.GetLayer() == pcbnew.F_Cu and abs(mm(t.GetLength()) - 13.785) < 0.01:
        if mm(t.GetStart().y) > mm(t.GetEnd().y): s0 = t.GetStart(); t.SetStart(t.GetEnd()); t.SetEnd(s0)
        sx0, sy0 = mm(t.GetStart().x), mm(t.GetStart().y)
        ex, ey = mm(t.GetEnd().x), mm(t.GetEnd().y); VS = t.GetNetname(); b.Delete(t)
        k = (sx0 - 110.45) / ((sx0 - ex) / (ey - sy0))
        trk(sx0, sy0, 110.45, sy0 + k, 0.3, pcbnew.F_Cu, VS)
        trk(110.45, sy0 + k, 110.45, 126.0, 0.3, pcbnew.F_Cu, VS)
        trk(110.45, 126.0, ex, ey, 0.3, pcbnew.F_Cu, VS)
        log.append(f'  VS1 re-routed: (113.7,115.67)-(110.45,{115.67 + k:.2f})-(110.45,126.0)-({ex:.2f},{ey:.2f})')
# pad 4 GND: tie to pad 5 under the connector body
if 'pad 4 GND: via False' in chr(10).join(log):
    q4 = [p for p in J.Pads() if p.GetNumber() == '4'][0]; q5 = [p for p in J.Pads() if p.GetNumber() == '5'][0]
    yy = 125.3
    trk(mm(q4.GetPosition().x), yy, mm(q5.GetPosition().x), yy, 0.4, pcbnew.F_Cu, 'GND')
    log.append('  pad 4 GND: F.Cu track to pad 5 at y 125.3')
# the old J7 +5.2V feed from the right (via 123.05,116.25 on In2) is joined to the left In2 +5.2V chain at via (119.7,118.14)
res = connect(b, '+5.2V', (123.05, 116.25), (119.7, 118.14), 0.4, ['F.Cu'], (117.5, 114.0, 125.5, 120.5), EDGE, HOLES)
log.append('  +5.2V right feed joined on F.Cu: ' + ('NO ROUTE' if res is None else f'{len(res)} items'))
# CH3 label below the connector, like CH2 under J6
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'CH3':
        d.SetPosition(V(TX, 126.99 + (TY - 122.6)))
pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
