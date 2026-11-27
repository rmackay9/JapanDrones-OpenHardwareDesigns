# KiCad python: shrink.py in.kicad_pcb out.kicad_pcb
import pcbnew, sys, math
b = pcbnew.LoadBoard(sys.argv[1])
MM = pcbnew.FromMM
mm = pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
log = []

def fp(ref):
    for f in b.GetFootprints():
        if f.GetReference() == ref:
            return f
def pads(f):
    return [p for p in b.GetPads() if p.GetParentFootprint().GetReference() == f.GetReference()] if False else list(f.Pads())

def drag_move(ref, dx, dy):
    """Move footprint and drag the ends of tracks/vias that sit on its pads."""
    f = fp(ref)
    d = V(dx, dy)
    for pad in f.Pads():
        for t in b.GetTracks():
            if t.GetNetCode() != pad.GetNetCode() or pad.GetNetCode() <= 0:
                continue
            if t.GetClass() == 'PCB_VIA':
                if pad.HitTest(t.GetPosition()):
                    t.SetPosition(t.GetPosition() + d)
                continue
            if not pad.IsOnLayer(t.GetLayer()):
                continue
            if pad.HitTest(t.GetStart()):
                t.SetStart(t.GetStart() + d)
            if pad.HitTest(t.GetEnd()):
                t.SetEnd(t.GetEnd() + d)
    f.Move(d)
    log.append(f'moved {ref} by ({dx},{dy})')

# ---------------- W: width 100 -> 94 ----------------
NEWX0, NEWX1 = 99.0, 193.0
hole_map = {(99.0, 53.0): (101.5, 52.5), (193.0, 53.0): (190.5, 52.5),
            (99.0, 137.0): (101.5, 137.5), (193.0, 137.0): (190.5, 137.5)}
for d in list(b.GetDrawings()):
    L = d.GetLayer()
    cls = d.GetClass()
    if cls == 'PCB_SHAPE' and d.GetShape() == pcbnew.SHAPE_T_CIRCLE and L in (pcbnew.Edge_Cuts, pcbnew.Dwgs_User):
        c = (round(mm(d.GetCenter().x), 2), round(mm(d.GetCenter().y), 2))
        if c in hole_map:
            n = hole_map[c]
            d.Move(V(n[0] - c[0], n[1] - c[1]))
            log.append(f'hole {b.GetLayerName(L)} {c}->{n}')
    elif cls == 'PCB_SHAPE' and L == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_RECT:
        s, e = d.GetStart(), d.GetEnd()
        d.SetStart(V(NEWX0, mm(s.y)))
        d.SetEnd(V(NEWX1, mm(e.y)))
        log.append('outline rect -> x 99..193')
    elif cls == 'PCB_SHAPE' and L == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        for get, setf in ((d.GetStart, d.SetStart), (d.GetEnd, d.SetEnd)):
            p = get()
            x = mm(p.x)
            if abs(x - 96) < 0.1: setf(V(NEWX0, mm(p.y)))
            if abs(x - 196) < 0.1: setf(V(NEWX1, mm(p.y)))
        log.append('outline segment adjusted')
    elif cls == 'PCB_SHAPE' and L == pcbnew.Dwgs_User and d.GetShape() == pcbnew.SHAPE_T_RECT:
        s, e = d.GetStart(), d.GetEnd()
        for get, setf in ((d.GetStart, d.SetStart), (d.GetEnd, d.SetEnd)):
            p = get(); x = mm(p.x)
            if abs(x - 96) < 0.1: setf(V(NEWX0, mm(p.y)))
            if abs(x - 196) < 0.1: setf(V(NEWX1, mm(p.y)))
    elif cls == 'PCB_TEXT' and L == pcbnew.Cmts_User and d.GetText().startswith('VIM_MOD'):
        x = mm(d.GetPosition().x)
        d.Move(V(3 if x < 145 else -3, 0))
    elif cls == 'PCB_TEXT' and L == pcbnew.Cmts_User and d.GetText().startswith('Check Altium'):
        d.Move(V(-4, 0))
    elif cls.startswith('PCB_DIM') and abs(mm(d.GetStart().x) - 96) < 0.1 and abs(mm(d.GetEnd().x) - 196) < 0.1:
        d.SetStart(V(NEWX0, mm(d.GetStart().y))); d.SetEnd(V(NEWX1, mm(d.GetEnd().y))); d.Update()
        log.append('width dimension updated')
    elif cls.startswith('PCB_DIM') and abs(mm(d.GetStart().x) - 196) < 0.1:
        d.SetStart(V(NEWX1, mm(d.GetStart().y))); d.SetEnd(V(NEWX1, mm(d.GetEnd().y))); d.Update()
        log.append('depth dimension moved')

# ---------------- A: XT90 flush with back edge ----------------
drag_move('J18', 0, -7)   # XT90 face 5 mm past the back edge (frame wall 3 mm)

# C112 -> top side, behind the XT90 pads (N/GND left, P/VBATT right)
c = fp('C112')
for t in list(b.GetTracks()):  # nothing should be attached; report if so
    pass
try:
    c.Flip(c.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
except Exception:
    c.Flip(c.GetPosition(), False)
c.SetPosition(V(145, 132.9))
padN = [p for p in c.Pads() if p.GetNumber() == 'N'][0]
if mm(padN.GetPosition().x) > 145:
    c.SetOrientationDegrees(c.GetOrientationDegrees() + 180)
log.append(f'C112 -> F.Cu at (145,132.9) N pad x={mm(padN.GetPosition().x):.2f}')

# D1 -> vertical between the XT90 pads, A (GND) towards the Cube
d1 = fp('D1')
d1.SetPosition(V(145, 122.5))
for rot in (90, -90, 270, 0):
    d1.SetOrientationDegrees(rot)
    pa = [p for p in d1.Pads() if p.GetNumber() == 'A'][0]
    if mm(pa.GetPosition().y) < 122.5 - 1:
        break
log.append(f'D1 rot {d1.GetOrientationDegrees()} A pad at ({mm(pa.GetPosition().x):.2f},{mm(pa.GetPosition().y):.2f})')

# F1 -> bottom, into the space C112 left (pad1 VBATT right, pad2 to C111 left)
f1 = fp('F1')
f1.SetPosition(V(146.5, 111.9))
p1 = [p for p in f1.Pads() if p.GetNumber() == '1'][0]
if mm(p1.GetPosition().x) < 146.5:
    f1.SetOrientationDegrees(f1.GetOrientationDegrees() + 180)
p2 = [p for p in f1.Pads() if p.GetNumber() == '2'][0]
p2x, p2y = mm(p2.GetPosition().x), mm(p2.GetPosition().y)
log.append(f'F1 pad1 {mm(p1.GetPosition().x):.2f} pad2 ({p2x:.2f},{p2y:.2f})')
# re-route the 2.25 mm F1 -> C111 track
keep = {((142.3, 102.95), (142.3, 106.3)), ((143.95, 101.3), (142.3, 102.95)), ((143.95, 101.3), (146.03, 101.3))}
for t in list(b.GetTracks()):
    if t.GetNetname() == 'Net-(C111-Pad1)' and t.GetClass() == 'PCB_TRACK' and abs(mm(t.GetWidth()) - 2.25) < 0.01:
        k = ((round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)), (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2)))
        if k not in keep and (k[1], k[0]) not in keep:
            b.Delete(t)
net = b.FindNet('Net-(C111-Pad1)')
def seg(x0, y0, x1, y1, w, layer, net):
    s = pcbnew.PCB_TRACK(b)
    s.SetStart(V(x0, y0)); s.SetEnd(V(x1, y1)); s.SetWidth(MM(w)); s.SetLayer(layer); s.SetNet(net)
    b.Add(s)
ymid = p2y - (p2x - 142.3)  # 45 degree jog to the x=142.3 run
seg(p2x, p2y, 142.3, ymid, 2.25, pcbnew.B_Cu, net)
seg(142.3, ymid, 142.3, 106.3, 2.25, pcbnew.B_Cu, net)

# bottom parts under the new XT90 body
def rigid_move(ref, dx, dy, box):
    """Move footprint plus all tracks/vias inside box; stretch tracks crossing the box edge."""
    bx0, by0, bx1, by1 = box
    inside = lambda p: bx0 <= mm(p.x) <= bx1 and by0 <= mm(p.y) <= by1
    d = V(dx, dy)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            if inside(t.GetPosition()): t.SetPosition(t.GetPosition() + d)
            continue
        s_in, e_in = inside(t.GetStart()), inside(t.GetEnd())
        if s_in: t.SetStart(t.GetStart() + d)
        if e_in: t.SetEnd(t.GetEnd() + d)
    fp(ref).Move(d)
    log.append(f'rigid-moved {ref} with its fan-out by ({dx},{dy})')

# --- U15 (CAN2 transceiver) area: shift U15 +1.4 mm and re-route its local B.Cu fan-out by hand ---
def find_seg(net, layer, a, b_, tol=0.02):
    for t in b.GetTracks():
        if t.GetClass() != 'PCB_TRACK' or t.GetNetname() != net or t.GetLayer() != layer: continue
        s = (mm(t.GetStart().x), mm(t.GetStart().y)); e = (mm(t.GetEnd().x), mm(t.GetEnd().y))
        for p, q in ((s, e), (e, s)):
            if math.dist(p, a) < tol and math.dist(q, b_) < tol: return t
    raise RuntimeError(f'segment not found {net} {a} {b_}')
def find_via(net, p, tol=0.02):
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net and math.dist((mm(t.GetPosition().x), mm(t.GetPosition().y)), p) < tol: return t
    raise RuntimeError(f'via not found {net} {p}')
B = pcbnew.B_Cu; I2 = pcbnew.In2_Cu
rip = [
    ('+3V3', B, (157.28, 117.54), (157.88, 118.15)), ('+3V3', B, (157.28, 116.65), (157.28, 117.54)),
    ('+3V3', B, (157.99, 118.05), (157.88, 118.15)), ('+3V3', B, (158.8, 118.05), (157.99, 118.05)),
    ('GND', B, (155.97, 113.75), (155.97, 114.88)), ('GND', B, (155.97, 114.88), (156.3, 115.2)),
    ('GND', B, (154.84, 119.7), (154.79, 119.75)), ('GND', B, (157.88, 119.7), (154.84, 119.7)),
    ('GND', B, (157.78, 115.2), (158.53, 115.95)), ('GND', B, (156.3, 115.2), (157.78, 115.2)),
    ('+5.2V', B, (156.62, 112.37), (156.5, 112.25)), ('+5.2V', B, (156.62, 113.75), (156.62, 112.37)),
    ('/Connectors/CAN_L_2', B, (159.38, 118.29), (159.38, 115.73)), ('/Connectors/CAN_L_2', B, (156.62, 116.65), (156.62, 118.09)),
    ('/Connectors/CAN_L_2', B, (158.79, 118.88), (159.38, 118.29)), ('/Connectors/CAN_L_2', B, (159.38, 115.73), (158.32, 114.67)),
    ('/Connectors/CAN_L_2', B, (157.42, 118.88), (158.79, 118.88)), ('/Connectors/CAN_L_2', B, (156.62, 118.09), (157.42, 118.88)),
    ('/Connectors/CAN_L_2', I2, (158.0, 114.33), (158.32, 114.65)), ('/Connectors/CAN_L_2', I2, (158.32, 114.65), (158.32, 114.67)),
    ('/Connectors/CAN_H_2', B, (155.27, 118.78), (154.31, 118.78)), ('/Connectors/CAN_H_2', B, (155.97, 118.07), (155.27, 118.78)),
    ('/Connectors/CAN_H_2', B, (154.04, 115.59), (154.47, 115.15)), ('/Connectors/CAN_H_2', B, (155.97, 116.65), (155.97, 118.07)),
    ('/Connectors/CAN_H_2', B, (154.04, 118.51), (154.04, 115.59)), ('/Connectors/CAN_H_2', B, (154.31, 118.78), (154.04, 118.51)),
    ('/VimDrones_mod2/CAN_TX', B, (155.32, 113.75), (154.82, 113.25)), ('/VimDrones_mod2/CAN_TX', B, (154.82, 113.25), (154.82, 112.91)),
    ('/VimDrones_mod2/CAN_RX', B, (160.95, 113.75), (157.28, 113.75)),
    ('Net-(U15-S)', B, (154.79, 118.1), (154.79, 117.18)), ('Net-(U15-S)', B, (154.79, 117.18), (155.32, 116.65)),
]
for net_, L, a, b_ in rip:
    b.Delete(find_seg(net_, L, a, b_))
for net_, p in (('GND', (158.53, 115.95)), ('/Connectors/CAN_L_2', (158.32, 114.67))):
    b.Delete(find_via(net_, p))
fp('U15').Move(V(1.4, 0))                     # centre 157.7,115.2
fp('R90').SetPosition(V(156.55, 118.875))     # S pad 118.05, GND pad 119.7
fp('C83').SetPosition(V(159.4, 118.925))      # 3V3 pad 118.15, GND pad 119.7
N = lambda n: b.FindNet(n)
def via(x, y, net_, d=0.45, drill=0.25):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(N(net_))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v)
def path(net_, w, L, pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg(x0, y0, x1, y1, w, L, N(net_))
path('/VimDrones_mod2/CAN_TX', 0.2032, B, [(156.72, 113.75), (156.22, 113.25), (154.82, 113.25), (154.82, 112.91)])
path('GND', 0.3, B, [(157.37, 113.75), (157.37, 114.6)])
path('+5.2V', 0.3, B, [(158.02, 113.75), (158.02, 112.25), (157.49, 112.25)])
path('/VimDrones_mod2/CAN_RX', 0.2032, B, [(158.68, 113.75), (160.95, 113.75)])
path('+3V3', 0.3, B, [(158.68, 116.65), (158.8, 118.05), (159.4, 118.15)])
path('Net-(U15-S)', 0.2032, B, [(156.72, 116.65), (156.72, 118.05)])
path('/Connectors/CAN_H_2', 0.254, B, [(157.37, 116.65), (157.37, 118.82), (154.3, 118.82), (154.3, 115.6), (154.47, 115.15)])
path('/Connectors/CAN_L_2', 0.254, B, [(158.02, 116.65), (158.02, 118.9), (160.5, 118.9), (160.5, 115.11), (159.72, 114.33)])
path('/Connectors/CAN_L_2', 0.254, I2, [(158.0, 114.33), (159.72, 114.33)])
via(159.72, 114.33, '/Connectors/CAN_L_2')
path('GND', 0.3, B, [(156.55, 119.7), (159.4, 119.7)])
path('GND', 0.3, B, [(156.55, 119.7), (153.55, 119.78)])
path('GND', 0.3, B, [(156.5, 115.2), (155.9, 115.2)])
via(155.9, 115.2, 'GND', 0.6, 0.3)
log.append('U15 area re-routed by hand (U15 +1.4 mm, R90/C83 re-placed)')

drag_move('D15', -0.25, 0)

# ---------------- simple clearance checker for new routing ----------------
def seg_pt_dist(ax, ay, bx_, by_, px, py):
    vx, vy = bx_ - ax, by_ - ay
    L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)
def seg_seg_dist(a, b_):
    return min(seg_pt_dist(*a[:2], *a[2:], *b_[:2]), seg_pt_dist(*a[:2], *a[2:], *b_[2:]),
               seg_pt_dist(*b_[:2], *b_[2:], *a[:2]), seg_pt_dist(*b_[:2], *b_[2:], *a[2:]))
def seg_ok(x0, y0, x1, y1, w, layer, netcode, clr=0.2, ignore=()):
    for t in b.GetTracks():
        if t.GetNetCode() == netcode or t in ignore: continue
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            if seg_pt_dist(x0, y0, x1, y1, mm(p.x), mm(p.y)) < w / 2 + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + clr: return False
        elif t.GetLayer() == layer:
            o = (mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y))
            if seg_seg_dist((x0, y0, x1, y1), o) < w / 2 + mm(t.GetWidth()) / 2 + clr: return False
    for f in b.GetFootprints():
        for pad in f.Pads():
            if pad.GetNetCode() == netcode or not pad.IsOnLayer(layer): continue
            q = pad.GetPosition(); r = max(mm(pad.GetSize().x), mm(pad.GetSize().y)) / 2
            if seg_pt_dist(x0, y0, x1, y1, mm(q.x), mm(q.y)) < w / 2 + r + clr: return False
    return True

# CAN_H_2 on In2 ran straight under the new XT90 pads: drop below them
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == '/Connectors/CAN_H_2' and t.GetLayer() == pcbnew.In2_Cu \
            and abs(mm(t.GetStart().y) - 115.15) < 0.05 and abs(mm(t.GetEnd().y) - 115.15) < 0.05 and abs(mm(t.GetLength()) - 19.05) < 0.1:
        xa, xb = sorted((mm(t.GetStart().x), mm(t.GetEnd().x)))
        w = mm(t.GetWidth()); nc = t.GetNetCode(); netobj = t.GetNet()
        done = False
        if seg_ok(xa, 115.15, xb, 115.15, w, pcbnew.In2_Cu, nc, clr=0.17, ignore=(t,)):
            log.append('CAN_H_2 In2 clear of the XT90 pads, kept'); break
        for yy in [round(119.75 + 0.05 * i, 2) for i in range(110)]:
            pth = [(xa, 115.15, xa, yy), (xa, yy, xb, yy), (xb, yy, xb, 115.15)]
            if all(seg_ok(*p, w, pcbnew.In2_Cu, nc, clr=0.17, ignore=(t,)) for p in pth):
                b.Delete(t)
                for p in pth: seg(*p, w, pcbnew.In2_Cu, netobj)
                log.append(f'CAN_H_2 In2 rerouted at y={yy}')
                done = True
                break
        if not done: log.append('CAN_H_2 reroute: NO PATH FOUND')
        break

# ---------------- zones around the connector ----------------
def set_outline(z, pts):
    o = z.Outline()
    o.RemoveAllContours()
    o.NewOutline()
    for x, y in pts:
        o.Append(MM(x), MM(y))
for z in b.Zones():
    ls = [b.GetLayerName(l) for l in z.GetLayerSet().CuStack()]
    if ls == ['F.Cu', 'B.Cu'] and z.GetNetname() == 'GND':
        set_outline(z, [(137, 110), (147.3, 110), (147.3, 121.2), (144.72, 121.2), (144.72, 134.5), (134, 134.5), (134, 122), (137, 122)])
        log.append('GND connector zone reshaped')
    if ls == ['F.Cu', 'B.Cu'] and z.GetNetname() == 'VBATT':
        set_outline(z, [(147.8, 110), (152.5, 110), (152.5, 122), (155.75, 122), (155.75, 135), (145, 135), (145, 121.7), (147.8, 121.7)])
        log.append('VBATT connector zone reshaped')

# ---------------- vias that now clash ----------------
def items_clear(x, y, r):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            if math.hypot(mm(p.x) - x, mm(p.y) - y) < r + mm(t.GetWidth(pcbnew.F_Cu)) / 2:
                b.Delete(t); n += 1
    return n
J = fp('J18')
for pad in J.Pads():
    p = pad.GetPosition()
    r = max(mm(pad.GetSize().x), mm(pad.GetSize().y)) / 2 + 0.3
    log.append(f'J18 pad {pad.GetNumber()} at ({mm(p.x):.2f},{mm(p.y):.2f}): removed {items_clear(mm(p.x), mm(p.y), r)} vias')
for pad in list(d1.Pads()) + list(f1.Pads()) + list(c.Pads()):
    bb = pad.GetBoundingBox()
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_VIA':
            q = t.GetPosition(); rr = mm(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.3
            if mm(bb.GetLeft()) - rr < mm(q.x) < mm(bb.GetRight()) + rr and mm(bb.GetTop()) - rr < mm(q.y) < mm(bb.GetBottom()) + rr and t.GetNetCode() != pad.GetNetCode():
                b.Delete(t); n += 1
    if n: log.append(f'{pad.GetParentFootprint().GetReference()} pad {pad.GetNumber()}: removed {n} other-net vias')
# new holes and new edges
for (hx, hy) in hole_map.values():
    log.append(f'hole ({hx},{hy}) removed {items_clear(hx, hy, 1.5 + 0.35)} vias')
n = 0
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        x = mm(t.GetPosition().x); r = mm(t.GetWidth(pcbnew.F_Cu)) / 2
        if x - r < NEWX0 + 0.3 or x + r > NEWX1 - 0.3:
            b.Delete(t); n += 1
log.append(f'removed {n} edge vias')

# stitching vias where the old XT90 pads were
gnd = b.FindNet('GND'); vb = b.FindNet('VBATT')
for net_, cx in ((gnd, 139.55), (vb, 150.45)):
    for dx in (-1.6, 0, 1.6):
        for dy in (-1.6, 0, 1.6):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(V(cx + dx, 129.1 + dy)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(net_)
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            b.Add(v)

# VBATT stitching vias left inside the reshaped GND area, and vias hitting the new F1->C111 track
n = 0
for t in list(b.GetTracks()):
    if t.GetClass() != 'PCB_VIA': continue
    x, y = mm(t.GetPosition().x), mm(t.GetPosition().y)
    if t.GetNetname() == 'VBATT' and 137 <= x <= 147.3 + 0.5 and 109.5 <= y <= 121.2 + 0.5:
        b.Delete(t); n += 1; continue
    if t.GetNetname() != 'Net-(C111-Pad1)':
        for sx0, sy0, sx1, sy1 in ((p2x, p2y, 142.3, ymid), (142.3, ymid, 142.3, 106.3)):
            if seg_pt_dist(sx0, sy0, sx1, sy1, x, y) < 2.25 / 2 + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.2:
                b.Delete(t); n += 1; break
log.append(f'removed {n} more clashing vias')

# left ESC3 VBATT pour lost its edge vias: stitch it under the RSHUNT5 body
for vx, vy in ((101.3, 103.6), (102.5, 103.6), (103.7, 103.6), (101.3, 104.8), (102.5, 104.8), (103.7, 104.8)):
    if seg_ok(vx, vy, vx, vy, 0.6, pcbnew.F_Cu, vb.GetNetCode()) and seg_ok(vx, vy, vx, vy, 0.6, pcbnew.In2_Cu, vb.GetNetCode()) \
            and seg_ok(vx, vy, vx, vy, 0.6, pcbnew.In3_Cu, vb.GetNetCode()) and seg_ok(vx, vy, vx, vy, 0.6, pcbnew.B_Cu, vb.GetNetCode()):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(V(vx, vy)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(vb)
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        b.Add(v); log.append(f'ESC3 VBATT via at ({vx},{vy})')
    else:
        log.append(f'ESC3 via at ({vx},{vy}) skipped (clearance)')

# the side VBATT strips (F/In2/In3) lost 3 mm to the narrower outline: widen them inwards on In2/In3
for xa, xb in ((105, 108), (182, 185)):
    z = pcbnew.ZONE(b)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.In2_Cu); ls.AddLayer(pcbnew.In3_Cu)
    z.SetLayerSet(ls); z.SetNet(vb); z.SetAssignedPriority(6)
    z.SetLocalClearance(MM(0.5)); z.SetMinThickness(MM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline(); o.NewOutline()
    for x, y in ((xa - 0.5, 83), (xb, 83), (xb, 135), (xa - 0.5, 135)):
        o.Append(MM(x), MM(y))
    z.SetZoneName('VBATT_STRIP_WIDEN')
    b.Add(z)
    log.append(f'added In2/In3 VBATT strip widening x {xa}..{xb}')

# --- R117 (U19 S-pin pulldown) clashed with the XT90 body: stand it up between U19 and the body ---
F = pcbnew.F_Cu
for net_, L, a, b_ in (('/Connectors/CAN_H_2', B, (131.07, 113.85), (134.12, 113.85)),):
    b.Delete(find_seg(net_, L, a, b_))
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'Net-(U19-S)' and t.GetLayer() == B:
        b.Delete(t)
cv = find_via('/Connectors/CAN_H_2', (134.125, 113.85))
cv.SetPosition(V(132.2, 113.85))
fseg = find_seg('/Connectors/CAN_H_2', F, (134.12, 113.85), (134.12, 92.03))
iseg = find_seg('/Connectors/CAN_H_2', I2, (134.12, 113.85), (135.43, 115.15))
iseg.SetStart(V(132.2, 113.85)) if math.dist((mm(iseg.GetStart().x), mm(iseg.GetStart().y)), (134.12, 113.85)) < 0.05 else iseg.SetEnd(V(132.2, 113.85))
path('/Connectors/CAN_H_2', 0.254, F, [(132.2, 113.85), (134.12, 113.85)])
path('/Connectors/CAN_H_2', 0.254, B, [(131.07, 113.85), (132.2, 113.85)])
lv = find_via('/Connectors/CAN_L_2', (133.12, 113.2), tol=0.05)
old = lv.GetPosition()
best = None
for gx in [round(131.9 + 0.05 * i, 2) for i in range(14)]:
    for gy in [round(112.9 + 0.05 * j, 2) for j in range(10)]:
        if math.dist((gx, gy), (132.2, 113.85)) < 0.45 + 0.2: continue
        if all(seg_ok(gx, gy, gx, gy, 0.45, L, lv.GetNetCode(), clr=0.17, ignore=(lv,)) for L in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu)) \
                and math.dist((gx, gy), (133.6, 113.56)) > 0.9:
            if best is None or math.dist((gx, gy), (132.2, 113.2)) < math.dist(best, (132.2, 113.2)): best = (gx, gy)
log.append(f'CAN_L_2 via candidate {best}')
new = V(*best)
for t in b.GetTracks():
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == '/Connectors/CAN_L_2':
        if math.dist((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(old.x), mm(old.y))) < 0.05: t.SetStart(new)
        if math.dist((mm(t.GetEnd().x), mm(t.GetEnd().y)), (mm(old.x), mm(old.y))) < 0.05: t.SetEnd(new)
lv.SetPosition(new)
log.append(f'CAN_L_2 via moved to {best}')
r = fp('R117')
r.SetPosition(V(133.6, 114.39))
for rot in (90, -90):
    r.SetOrientationDegrees(rot)
    ps = [p for p in r.Pads() if p.GetNetname() == 'Net-(U19-S)'][0]
    if mm(ps.GetPosition().y) > 114.39: break
psx, psy = mm(ps.GetPosition().x), mm(ps.GetPosition().y)
path('Net-(U19-S)', 0.2032, B, [(131.07, 114.5), (131.9, 114.5), (132.6, psy), (psx, psy)])
log.append(f'R117 stood up at (133.6,114.39) rot {r.GetOrientationDegrees()}, CAN_H_2 via moved to (132.2,113.85)')

# 'LED' label of J16 now hangs over the left edge: nudge it onto the board
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'LED' and d.GetLayer() == pcbnew.F_SilkS and mm(d.GetPosition().x) < 100.5:
        d.Move(V(0, 0)); bb = d.GetBoundingBox()
        d.Move(V(99.3 - mm(bb.GetLeft()), 0)); log.append('J16 LED label moved inside the edge')

# In3 VBATT feed to the FAN connector (J14 pin 1) ran under the new XT90 GND pad: go round above it
I3 = pcbnew.In3_Cu
for a_, b2 in (((132.47, 120.8), (144.58, 120.8)), ((144.58, 120.8), (145.75, 119.63))):
    b.Delete(find_seg('VBATT', I3, a_, b2))
pth = [(132.47, 120.8), (136.0, 120.8), (136.0, 118.5), (146.2, 118.5), (146.2, 128.4)]
segs_ = list(zip(pth, pth[1:]))
nd = 0
for t in list(b.GetTracks()):   # GND stitching vias in the way (GND pour keeps plenty)
    if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND':
        x, y = mm(t.GetPosition().x), mm(t.GetPosition().y)
        if any(seg_pt_dist(*p, *q, x, y) < 0.2 + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.2 for p, q in segs_):
            b.Delete(t); nd += 1
bad = [(p, q) for p, q in segs_ if not seg_ok(*p, *q, 0.4, I3, vb.GetNetCode(), clr=0.17)]
for p, q in segs_: seg(*p, *q, 0.4, I3, vb)
v = pcbnew.PCB_VIA(b); v.SetPosition(V(146.2, 128.4)); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(vb)
v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v)
log.append(f'In3 VBATT fan feed re-routed round the XT90 GND pad (removed {nd} GND vias); checker issues: {bad}')
fp('C112').Reference().SetPosition(V(145, 139.1))

# XT90 placeholder: real body measured 21 mm wide
for m in fp('J18').Models():
    if 'xt90pw_' in m.m_Filename:
        m.m_Filename = m.m_Filename.replace('xt90pw_24.50x25.40x10.20', 'xt90pw_21.00x25.40x10.20')
# CubeOrange body outline on User.Drawings for future clearance checks:
# 38.25 mm square centred on the Cube 30x30 holes (145,95); rear edge y 114.125 is ~1 mm ahead of the
# FAN connector J14 (courtyard front y 115.0), matching Randy's measurement on the real board.
CX0, CY0, CX1, CY1 = 145 - 19.125, 95 - 19.125, 145 + 19.125, 95 + 19.125
rect = pcbnew.PCB_SHAPE(b); rect.SetShape(pcbnew.SHAPE_T_RECT); rect.SetLayer(pcbnew.Dwgs_User)
rect.SetStart(V(CX0, CY0)); rect.SetEnd(V(CX1, CY1)); rect.SetWidth(MM(0.15)); b.Add(rect)
txt = pcbnew.PCB_TEXT(b); txt.SetText('CubeOrange body (assumed 38.25 sq) - top parts inside must be low'); txt.SetLayer(pcbnew.Dwgs_User)
txt.SetPosition(V(145, CY1 - 1.2)); txt.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); txt.SetTextThickness(MM(0.12)); b.Add(txt)
inside = []
for f in b.GetFootprints():
    if f.GetLayer() != pcbnew.F_Cu: continue
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
    if mm(bb.GetRight()) > CX0 and mm(bb.GetLeft()) < CX1 and mm(bb.GetBottom()) > CY0 and mm(bb.GetTop()) < CY1:
        inside.append(f'{f.GetReference()}(y {mm(bb.GetTop()):.1f}..{mm(bb.GetBottom()):.1f})')
log.append('top parts overlapping the Cube outline: ' + ', '.join(inside))
log.append('J14 courtyard front y=%.2f, D1 top y=%.2f, C112 top y=%.2f' % tuple(mm(fp(r).GetCourtyard(pcbnew.F_CrtYd).BBox().GetTop()) for r in ('J14', 'D1', 'C112')))

pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
