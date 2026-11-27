# KiCad python: move_j6.py in out dx - shift J6 (LED CH2) inboard by dx mm and reconnect its pads to their old vias
import sys, math
sys.path.insert(0, '.')
import pcbnew
from router import connect
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
DX = float(sys.argv[3])
EDGE = (100.11, 191.25, 50.0, 140.0)
HOLES = [(102.61, 52.5, 1.6), (188.75, 52.5, 1.6), (102.61, 137.5, 1.6), (188.75, 137.5, 1.6),
         (130, 80, 0.9), (160, 80, 0.9), (130, 110, 0.9), (160, 110, 0.9)]
J = [f for f in b.GetFootprints() if f.GetReference() == 'J6'][0]
log = []
# 1) pad tracks off; remember the far ends (vias)
ends = {}
for p in J.Pads():
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_TRACK' and t.GetLayer() == pcbnew.F_Cu and t.GetNetCode() == p.GetNetCode() and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())):
            e = t.GetEnd() if p.HitTest(t.GetStart()) else t.GetStart()
            ends[p.GetNumber()] = (mm(e.x), mm(e.y), t.GetLayerName(), mm(t.GetWidth())); b.Delete(t)
for p in J.Pads():
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == p.GetNetCode() and p.HitTest(t.GetPosition()) and p.GetNumber() not in ends:
            ends[p.GetNumber()] = (mm(t.GetPosition().x), mm(t.GetPosition().y), 'via', 0.4)
J.Move(V(DX, 0))
bb = J.GetCourtyard(pcbnew.F_CrtYd).BBox()
log.append(f'J6 courtyard x {mm(bb.GetLeft()):.2f}..{mm(bb.GetRight()):.2f}, side-edge gap {EDGE[1] - mm(bb.GetRight()):.2f}')
def pad_hit(x, y, r, clr=0.2):
    for q in J.Pads():
        pb = q.GetBoundingBox()
        if mm(pb.GetLeft()) - r - clr < x < mm(pb.GetRight()) + r + clr and mm(pb.GetTop()) - r - clr < y < mm(pb.GetBottom()) + r + clr: return q
    return None
def seg_pt(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)
def clear_for_via(x, y, r, netcode, clr=0.2):
    if pad_hit(x, y, r, 0.25): return False
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            if math.hypot(mm(p.x) - x, mm(p.y) - y) < r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + (clr if t.GetNetCode() != netcode else 0.3): return False
        elif t.GetNetCode() != netcode:
            if seg_pt(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), x, y) < r + mm(t.GetWidth()) / 2 + clr: return False
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == netcode and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD: continue
            pb = p.GetBoundingBox()
            if mm(pb.GetLeft()) - r - clr < x < mm(pb.GetRight()) + r + clr and mm(pb.GetTop()) - r - clr < y < mm(pb.GetBottom()) + r + clr: return False
    for hx, hy, hr in HOLES:
        if math.hypot(hx - x, hy - y) < hr + r + 0.3: return False
    return x < EDGE[1] - 0.6
def add_via(x, y, net, d, drill):
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v); return v
# ESC2 FD6288_LO1 (F.Cu) runs just left of the new pad 5: re-route it as a straighter line between the MVDD vias and the pad
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname().endswith('FD6288_LO1') and t.GetLayer() == pcbnew.F_Cu and abs(mm(t.GetLength()) - 13.2034) < 0.01:
        a, c = (t.GetStart(), t.GetEnd()) if mm(t.GetStart().y) < mm(t.GetEnd().y) else (t.GetEnd(), t.GetStart())
        ax, ay, cx_, cy_ = mm(a.x), mm(a.y), mm(c.x), mm(c.y); net = t.GetNet(); w = t.GetWidth(); b.Delete(t)
        pts = [(ax, ay), (180.25, 120.25), (180.05, 122.0), (180.05, 126.0), (cx_, cy_)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = pcbnew.PCB_TRACK(b); n.SetStart(V(x0, y0)); n.SetEnd(V(x1, y1)); n.SetWidth(w); n.SetLayer(pcbnew.F_Cu); n.SetNet(net); b.Add(n)
        log.append('LO1 re-routed: ' + ' - '.join(f'({x:.2f},{y:.2f})' for x, y in pts))
# 2) vias that now clash with J6 pads
removed = []
keep = {(round(e[0], 2), round(e[1], 2)) for e in ends.values()}
for t in list(b.GetTracks()):
    if t.GetClass() != 'PCB_VIA': continue
    x, y = mm(t.GetPosition().x), mm(t.GetPosition().y); r = mm(t.GetWidth(pcbnew.F_Cu)) / 2
    q = pad_hit(x, y, r)
    if q is None or q.GetNetCode() == t.GetNetCode() and (round(x, 2), round(y, 2)) in keep: continue
    tracked = any(o.GetClass() == 'PCB_TRACK' and o.GetNetCode() == t.GetNetCode() and (o.GetStart() == t.GetPosition() or o.GetEnd() == t.GetPosition()) for o in b.GetTracks())
    if tracked: raise SystemExit(f'tracked via {t.GetNetname()} at ({x:.2f},{y:.2f}) under J6 pad {q.GetNumber()}')
    removed.append((x, y, t.GetNet(), 2 * r, mm(t.GetDrillValue()))); b.Delete(t)
back = 0
for x, y, net, d, drill in removed:
    for rad in [0.3 * k for k in range(1, 20)]:
        hit = None
        for a in range(0, 360, 15):
            vx, vy = x + rad * math.cos(math.radians(a)), y + rad * math.sin(math.radians(a))
            if clear_for_via(vx, vy, d / 2, net.GetNetCode()): hit = (vx, vy); break
        if hit: add_via(hit[0], hit[1], net, d, drill); back += 1; break
log.append(f'vias clashing with J6 pads: ' + ', '.join(f'{n.GetNetname()}@({x:.2f},{y:.2f})' for x, y, n, d, dr in removed) + f'; re-added {back} nearby')
# 3) reconnect each pad to its old far end
for p in sorted(J.Pads(), key=lambda q: q.GetNumber()):
    if p.GetNumber() not in ends: continue
    ex, ey, lay, w = ends[p.GetNumber()]
    if (round(ex, 2), round(ey, 2)) in {(round(r[0], 2), round(r[1], 2)) for r in removed}:
        # its via had to go: new GND via next to the pad
        q = p.GetPosition(); gx, gy = mm(q.x), mm(q.y); ok = None
        for rad in [0.2 * k for k in range(5, 30)]:
            for a in range(0, 360, 15):
                vx, vy = gx + rad * math.cos(math.radians(a)), gy + rad * math.sin(math.radians(a))
                if clear_for_via(vx, vy, 0.3, p.GetNetCode()):
                    v = add_via(vx, vy, p.GetNet(), 0.6, 0.3)
                    if connect(b, p.GetNetname(), (gx, gy), (vx, vy), 0.4, ['F.Cu'], (min(gx, vx) - 2, min(gy, vy) - 2, max(gx, vx) + 2, max(gy, vy) + 2), EDGE, HOLES) is not None:
                        ok = (round(vx, 2), round(vy, 2)); break
                    b.Delete(v)
            if ok: break
        log.append(f'  pad {p.GetNumber()} {p.GetNetname()}: old via moved away, new via {ok}'); continue
    q = p.GetPosition(); gx, gy = mm(q.x), mm(q.y)
    box = (min(ex, gx) - 2.5, min(ey, gy) - 2.5, min(max(ex, gx) + 2.5, EDGE[1] - 0.2), max(ey, gy) + 2.5)
    res = connect(b, p.GetNetname(), (ex, ey), (gx, gy), w, ['F.Cu'], box, EDGE, HOLES)
    log.append(f'  pad {p.GetNumber()} {p.GetNetname()} from ({ex:.2f},{ey:.2f}) {lay}: ' + ('NO ROUTE' if res is None else f'{sum(1 for o in res if o.GetClass() == "PCB_TRACK")} segs'))
# re-placed VBATT vias cut the B.Cu GND area below J6 off its GND via: stitch it with a new GND via
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
gz = [z for z in b.Zones() if z.GetZoneName() == 'GND_MEGA'][0]
fp = gz.GetFilledPolysList(pcbnew.B_Cu); gv = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND']
for i in range(fp.OutlineCount()):
    o = fp.Outline(i); bb = o.BBox()
    if not (mm(bb.GetLeft()) > 184 and mm(bb.GetTop()) > 118 and mm(bb.GetTop()) < 130): continue
    if any(o.PointInside(a) for a in gv) or o.Area() < MM(1) * MM(1) * 4: continue
    done = None
    for yy in [mm(bb.GetTop()) + 0.6 + 0.2 * k for k in range(40)]:
        for xx in [mm(bb.GetLeft()) + 0.6 + 0.2 * k for k in range(25)]:
            if o.PointInside(V(xx, yy)) and clear_for_via(xx, yy, 0.3, b.FindNet('GND').GetNetCode(), 0.35):
                add_via(xx, yy, b.FindNet('GND'), 0.6, 0.3); done = (round(xx, 2), round(yy, 2)); break
        if done: break
    log.append(f'B.Cu GND area x {mm(bb.GetLeft()):.2f}.. y {mm(bb.GetTop()):.2f}.. had no GND via; added {done}')
# CH2 label follows
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'CH2': d.Move(V(DX, 0))
pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
