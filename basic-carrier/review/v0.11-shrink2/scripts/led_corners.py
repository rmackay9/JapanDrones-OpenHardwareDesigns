# KiCad python: B1 - move the 5 LED/FMU JST-GH connectors out of the mid band to the bottom outer edges.
import os, sys, math
sys.path.insert(0, os.environ.get('SCRATCH', os.path.dirname(os.path.abspath(__file__))))
import pcbnew
from router import connect
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
EDGE = (100.11, 191.25, 50.0, 140.0)
HOLES = [(102.61, 52.5, 1.6), (188.75, 52.5, 1.6), (102.61, 137.5, 1.6), (188.75, 137.5, 1.6),
         (130, 80, 0.9), (160, 80, 0.9), (130, 110, 0.9), (160, 110, 0.9)]
LAYERS = ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu']
# target regions (x0, x1, y0, y1) for the connector centres, in order of preference
REGIONS = {'J4': (176, 192, 68, 90.5), 'J6': (176, 192, 68, 90.5), 'J7': (176, 192, 99.5, 120), 'J15': (176, 192, 99.5, 120),
           'J16': (99, 126, 68, 90.5)}
FPS = {f.GetReference(): f for f in b.GetFootprints()}

def rect_hits(x0, x1, y0, y1, skip_refs, margin=0.2):
    """True if the rectangle touches bottom copper/courtyards we must not cover."""
    for f in b.GetFootprints():
        if f.GetReference() in skip_refs: continue
        if f.GetLayer() == pcbnew.B_Cu:
            c = f.GetCourtyard(pcbnew.B_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
            if mm(bb.GetLeft()) < x1 + margin and mm(bb.GetRight()) > x0 - margin and mm(bb.GetTop()) < y1 + margin and mm(bb.GetBottom()) > y0 - margin: return True
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.B_Cu):
                bb = p.GetBoundingBox()
                if mm(bb.GetLeft()) < x1 + 0.3 and mm(bb.GetRight()) > x0 - 0.3 and mm(bb.GetTop()) < y1 + 0.3 and mm(bb.GetBottom()) > y0 - 0.3: return True
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            if t.GetNetname() == 'GND': continue      # GND stitching may be removed
            p = t.GetPosition(); r = mm(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.25
            if x0 - r < mm(p.x) < x1 + r and y0 - r < mm(p.y) < y1 + r: return True
        elif t.GetLayer() == pcbnew.B_Cu:
            ax, ay, bx, by = mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y)
            r = mm(t.GetWidth()) / 2 + 0.25
            # sample the segment
            n = max(2, int(math.hypot(bx - ax, by - ay) / 0.1))
            for k in range(n + 1):
                px, py = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
                if x0 - r < px < x1 + r and y0 - r < py < y1 + r: return True
    for hx, hy, hr in HOLES:
        if x0 - hr - 0.5 < hx < x1 + hr + 0.5 and y0 - hr - 0.5 < hy < y1 + hr + 0.5: return True
    if x0 < EDGE[0] + 0.5 or x1 > EDGE[1] - 0.5: return True
    return False

def find_spot(ref, region, taken):
    f = FPS[ref]
    best = None
    for rot in (0, 90):
        w, h = (7.79, 6.19) if rot == 0 else (6.19, 7.79)
        x0r, x1r, y0r, y1r = region
        cx = x0r + w / 2
        while cx + w / 2 <= x1r:
            cy = y0r + h / 2
            while cy + h / 2 <= y1r:
                r = (cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
                if not any(r[0] < t[1] + 0.3 and r[1] > t[0] - 0.3 and r[2] < t[3] + 0.3 and r[3] > t[2] - 0.3 for t in taken) \
                        and not rect_hits(*r, skip_refs=set(REGIONS)):
                    # prefer close to the outer edge
                    score = min(abs(r[0] - EDGE[0]), abs(EDGE[1] - r[1]))
                    if best is None or score < best[0] - 1e-6:
                        best = (score, cx, cy, rot, r)
                cy += 0.25
            cx += 0.25
    return best

NEW = {'J4': (183.5, 67.3, 0), 'J6': (185.5, 122.6, 0), 'J7': (117.0, 122.8, 0), 'J15': (105.0, 67.4, 0), 'J16': (131.5, 125.3, 0)}
log = []

def seg_pt(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)

def clear_for_via(x, y, r, netcode, clr=0.2):
    for t in b.GetTracks():
        if t.GetNetCode() == netcode: continue
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            if math.hypot(mm(p.x) - x, mm(p.y) - y) < r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + clr: return False
        else:
            if seg_pt(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), x, y) < r + mm(t.GetWidth()) / 2 + clr: return False
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == netcode: continue
            bb = p.GetBoundingBox()
            if mm(bb.GetLeft()) - r - clr < x < mm(bb.GetRight()) + r + clr and mm(bb.GetTop()) - r - clr < y < mm(bb.GetBottom()) + r + clr: return False
    return True

old_texts = []
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS and d.GetText() in ('LED', 'V', 'G'):
        x, y = mm(d.GetPosition().x), mm(d.GetPosition().y)
        if 89.5 < y < 100.5 and (x < 108 or x > 163):
            old_texts.append(d)
for d in old_texts:
    b.Delete(d)
log.append(f'removed {len(old_texts)} old LED/V/G silk texts in the band')

starts = {}
removed_vias = []
CONN = set(NEW)
for ref, (nx, ny, nrot) in NEW.items():
    f = FPS[ref]
    for p in f.Pads():
        q = p.GetPosition()
        starts[(ref, p.GetNumber())] = (mm(q.x), mm(q.y), p.GetNetname())
        if p.GetNetname() == 'GND':      # F stubs from the old GND pads to stitching
            for t in list(b.GetTracks()):
                if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == p.GetNetCode() and t.GetLayer() == pcbnew.F_Cu \
                        and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd())):
                    b.Delete(t)
    f.SetOrientationDegrees(nrot)
    f.SetPosition(V(nx, ny))
    bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()          # centre the courtyard on the target
    cx, cy = (mm(bb.GetLeft()) + mm(bb.GetRight())) / 2, (mm(bb.GetTop()) + mm(bb.GetBottom())) / 2
    f.Move(V(nx - cx, ny - cy))
    bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_VIA' and (t.GetNetname() in ('GND', 'VBATT') or t.GetNetname().endswith('MVDD')):
            p = t.GetPosition()
            if mm(bb.GetLeft()) - 0.4 < mm(p.x) < mm(bb.GetRight()) + 0.4 and mm(bb.GetTop()) - 0.4 < mm(p.y) < mm(bb.GetBottom()) + 0.4:
                removed_vias.append((mm(p.x), mm(p.y), t.GetNet(), mm(t.GetWidth(pcbnew.F_Cu)), mm(t.GetDrillValue())))
                b.Delete(t)
    log.append(f'{ref} -> F.Cu courtyard x {mm(bb.GetLeft()):.2f}..{mm(bb.GetRight()):.2f} y {mm(bb.GetTop()):.2f}..{mm(bb.GetBottom()):.2f}')

def in_conn(x, y, m=0.5):
    for r in CONN:
        bb = FPS[r].GetCourtyard(pcbnew.F_CrtYd).BBox()
        if mm(bb.GetLeft()) - m < x < mm(bb.GetRight()) + m and mm(bb.GetTop()) - m < y < mm(bb.GetBottom()) + m: return True
    return False

ADDED = set()
def add_via(x, y, net, d=0.6, drill=0.3):
    ADDED.add((round(x, 3), round(y, 3)))
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(v)

# signal and +5.2V routes from the old pad positions
for ref in NEW:
    for p in FPS[ref].Pads():
        net = p.GetNetname()
        if net == 'GND': continue
        q = p.GetPosition(); gx, gy = mm(q.x), mm(q.y)
        sx, sy, _ = starts[(ref, p.GetNumber())]
        w = 0.4 if net == '+5.2V' else 0.25
        bbox = (min(sx, gx) - 8, min(sy, gy) - 8, max(sx, gx) + 8, max(sy, gy) + 8)
        res = connect(b, net, (sx, sy), (gx, gy), w, LAYERS, bbox, EDGE, HOLES, start_layers=['F.Cu'], goal_layers=['F.Cu'])
        if res is None:
            res = connect(b, net, (sx, sy), (gx, gy), w, LAYERS, (bbox[0] - 10, bbox[1] - 10, bbox[2] + 10, bbox[3] + 10), EDGE, HOLES,
                          start_layers=['F.Cu'], goal_layers=['F.Cu'])
        log.append(f'  {ref} pad {p.GetNumber()} {net}: ' + ('NO ROUTE' if res is None else f'{sum(1 for o in res if o.GetClass()=="PCB_TRACK")} segs, {sum(1 for o in res if o.GetClass()=="PCB_VIA")} vias'))

# put back the power stitching vias that were under the connectors, just outside them
back = 0
for x, y, net, d, drill in removed_vias:
    placed = False
    for rad in [0.4 * k for k in range(0, 16)]:
        for a in range(0, 360, 20):
            vx, vy = x + rad * math.cos(math.radians(a)), y + rad * math.sin(math.radians(a))
            if clear_for_via(vx, vy, d / 2, net.GetNetCode()):
                add_via(vx, vy, net, d, drill); placed = True; back += 1; break
        if placed: break
log.append(f'power stitching vias: removed {len(removed_vias)}, re-added {back} next to the connectors')

# GND pads: a GND via close by, joined with a short routed track on B.Cu
gnd = b.FindNet('GND')
for ref in NEW:
    for p in FPS[ref].Pads():
        if p.GetNetname() != 'GND': continue
        q = p.GetPosition(); gx, gy = mm(q.x), mm(q.y)
        cands = []
        for rad in [0.2 * k for k in range(5, 35)]:
            for a in range(0, 360, 15):
                vx, vy = gx + rad * math.cos(math.radians(a)), gy + rad * math.sin(math.radians(a))
                if clear_for_via(vx, vy, 0.3, gnd.GetNetCode()) and all(math.hypot(mm(o.GetPosition().x) - vx, mm(o.GetPosition().y) - vy) > 0.9 for o in b.GetTracks() if o.GetClass() == 'PCB_VIA'):
                    cands.append((rad, vx, vy))
            if len(cands) > 12: break
        ok = False
        for rad, vx, vy in cands:
            add_via(vx, vy, gnd)
            res = connect(b, 'GND', (gx, gy), (vx, vy), 0.4, ['F.Cu'], (min(gx, vx) - 3, min(gy, vy) - 3, max(gx, vx) + 3, max(gy, vy) + 3), EDGE, HOLES)
            if res is not None: ok = True; break
            for t in list(b.GetTracks()):
                if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == gnd.GetNetCode() and abs(mm(t.GetPosition().x) - vx) < 1e-3 and abs(mm(t.GetPosition().y) - vy) < 1e-3:
                    b.Delete(t)
        if not ok:   # tie it to another GND pad of the same connector on B.Cu
            for p2 in FPS[ref].Pads():
                if p2.GetNetname() == 'GND' and p2.GetNumber() != p.GetNumber():
                    q2 = p2.GetPosition()
                    if connect(b, 'GND', (gx, gy), (mm(q2.x), mm(q2.y)), 0.3, ['F.Cu'], (min(gx, mm(q2.x)) - 3, min(gy, mm(q2.y)) - 3, max(gx, mm(q2.x)) + 3, max(gy, mm(q2.y)) + 3), EDGE, HOLES):
                        ok = 'pad-to-pad'; break
        log.append(f'  {ref} pad {p.GetNumber()} GND: ' + ('via + track' if ok is True else (ok or 'NO VIA')))

# remove dangling GND track stubs (repeat until stable)
def ends_connected(t, pt):
    for o in b.GetTracks():
        if o is t or o.GetNetCode() != t.GetNetCode(): continue
        if o.GetClass() == 'PCB_VIA':
            if o.GetPosition() == pt: return True
        elif o.GetLayer() == t.GetLayer() and (o.GetStart() == pt or o.GetEnd() == pt): return True
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()) and p.HitTest(pt): return True
    return False
for t in list(b.GetTracks()):
    if False and t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'GND' and t.GetLayer() == pcbnew.F_Cu and 181 < mm(t.GetStart().x) < 187 and 88 < mm(t.GetStart().y) < 91.5 and 181 < mm(t.GetEnd().x) < 187 and 88 < mm(t.GetEnd().y) < 91.5:
        b.Delete(t)
for _ in range(5):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'GND' and t.GetLayer() == pcbnew.F_Cu and 175 < mm(t.GetStart().x) < 193 and 88 < mm(t.GetStart().y) < 101:
            if not ends_connected(t, t.GetStart()) or not ends_connected(t, t.GetEnd()):
                b.Delete(t); n += 1
    if n == 0: break

# dangling GND stubs left from the old connector pads: give their free end a GND via instead
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'GND' and t.GetLayer() == pcbnew.F_Cu and 180 < mm(t.GetStart().x) < 190 and 88.5 < mm(t.GetStart().y) < 90:
        for pt in (t.GetStart(), t.GetEnd()):
            if not ends_connected(t, pt):
                x, y = mm(pt.x), mm(pt.y)
                if clear_for_via(x, y, 0.3, gnd.GetNetCode()): add_via(x, y, gnd); log.append(f'GND via added at stub end ({x:.2f},{y:.2f})')
                else: log.append(f'stub end ({x:.2f},{y:.2f}) could not get a via')

# zones that relied on stitching vias now under a connector: make sure each still has VBATT vias
vb = b.FindNet('VBATT')
for z in b.Zones():
    if z.GetNetname() != 'VBATT' or z.GetZoneName() not in ('VBATT_ESC1', 'VBATT_ESC2', 'VBATT_ESC', 'VBATT_ESC3'): continue
    bb = z.Outline().BBox(); added = 0
    y = mm(bb.GetTop()) + 0.5
    while y < mm(bb.GetBottom()) - 0.5 and added < 4:
        x = mm(bb.GetLeft()) + 0.5
        while x < mm(bb.GetRight()) - 0.5 and added < 4:
            if z.Outline().Contains(V(x, y)) and clear_for_via(x, y, 0.3, vb.GetNetCode()) and \
                    all(math.hypot(mm(o.GetPosition().x) - x, mm(o.GetPosition().y) - y) > 1.2 for o in b.GetTracks() if o.GetClass() == 'PCB_VIA' and o.GetNetCode() == vb.GetNetCode()):
                add_via(x, y, vb); added += 1
            x += 0.3
        y += 0.3
    log.append(f'zone {z.GetZoneName()}: added {added} VBATT vias')

# drop same-net via pairs that ended up too close (keep the one with a track on it)
vs = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and 99 < mm(t.GetPosition().x) < 193]
gone = set()
for i, v1 in enumerate(vs):
    for v2 in vs[i + 1:]:
        if id(v1) in gone or id(v2) in gone: continue
        if math.hypot(mm(v1.GetPosition().x - v2.GetPosition().x), mm(v1.GetPosition().y - v2.GetPosition().y)) < 0.75:
            tracked = lambda v: any(t.GetClass() == 'PCB_TRACK' and (t.GetStart() == v.GetPosition() or t.GetEnd() == v.GetPosition()) for t in b.GetTracks())
            isnew = lambda v: (round(mm(v.GetPosition().x), 3), round(mm(v.GetPosition().y), 3)) in ADDED
            if not (isnew(v1) or isnew(v2)): continue
            victim = v2 if isnew(v2) else v1
            vx_, vy_ = mm(victim.GetPosition().x), mm(victim.GetPosition().y)
            gone.add(id(victim)); b.Delete(victim); log.append(f'removed duplicate GND via at ({vx_:.2f},{vy_:.2f})')

pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))