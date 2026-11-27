# KiCad python: option A - MOSFET + motor-pad pitch 10 -> 8.5 mm in all four ESCs, board narrower.
import os, sys, math, json
sys.path.insert(0, os.environ.get('SCRATCH', os.path.dirname(os.path.abspath(__file__))))
import pcbnew
from router import connect
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
import os
PITCH = float(os.environ.get('PITCH', '8.5'))
log = []
FPS = {f.GetReference(): f for f in b.GetFootprints()}
MOTOR = ('J2', 'J19', 'J22', 'J25')

def cyd(f):
    c = f.GetCourtyard(pcbnew.F_CrtYd if f.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    return mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom())

def quad_of(x, y):
    return ('F' if y < 95 else 'B') + ('L' if x < 145 else 'R')

# ---------------- 1. FET columns per quadrant ----------------
fets = [f for f in b.GetFootprints() if f.GetValue().startswith('TPHR')]
Q = {}
for q in ('FL', 'FR', 'BL', 'BR'):
    fs = [f for f in fets if quad_of(mm(f.GetPosition().x), mm(f.GetPosition().y)) == q]
    cols = []
    for f in sorted(fs, key=lambda f: mm(f.GetPosition().x)):
        x = mm(f.GetPosition().x)
        for c in cols:
            if abs(c['x'] - x) < 3: c['f'].append(f); break
        else: cols.append({'x': x, 'f': [f]})
    for c in cols: c['x'] = sum(mm(f.GetPosition().x) for f in c['f']) / len(c['f'])
    left = q[1] == 'L'
    cols.sort(key=lambda c: c['x'], reverse=not left)     # outer -> inner
    inner = cols[2]['x']
    for k, c in enumerate(cols):
        c['new'] = inner + (k - 2) * PITCH * (1 if left else -1)
        c['shift'] = c['new'] - c['x']
    Q[q] = cols
    log.append(f"{q}: column x {[round(c['x'], 2) for c in cols]} -> {[round(c['new'], 2) for c in cols]}")

# ---------------- 2. gate resistors in the gaps -> top side ----------------
gap_res = []
for q, cols in Q.items():
    for a, c in ((cols[0], cols[1]), (cols[1], cols[2])):
        xs = [cyd(f)[0:2] for f in a['f'] + c['f']]
        ys = [cyd(f)[2:4] for f in a['f'] + c['f']]
        lo = min(max(x[1] for x in [cyd(f) for f in a['f']]), max(x[1] for x in [cyd(f) for f in c['f']]))
        hi = max(min(x[0] for x in [cyd(f) for f in a['f']]), min(x[0] for x in [cyd(f) for f in c['f']]))
        gx0, gx1 = min(lo, hi), max(lo, hi)
        gy0, gy1 = min(y[0] for y in ys) - 1.0, max(y[1] for y in ys) + 1.0
        for f in b.GetFootprints():
            if not f.GetReference().startswith('R') or f.GetLayer() != pcbnew.B_Cu: continue
            x0, x1, y0, y1 = cyd(f)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if gx0 - 0.2 < cx < gx1 + 0.2 and gy0 < cy < gy1:
                gap_res.append(f.GetReference())
gap_res = sorted(set(gap_res)) if os.environ.get('NOFLIP') != '1' else []
log.append(f'gap resistors -> top: {gap_res}')

def chain_terminal(pad):
    """Walk B.Cu tracks from a pad to the first via / other pad / junction; delete the walked tracks."""
    net = pad.GetNetCode()
    pt = None
    tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == net and pad.IsOnLayer(t.GetLayer())]
    cur = [t for t in tracks if pad.HitTest(t.GetStart()) or pad.HitTest(t.GetEnd())]
    if not cur: return None
    t = cur[0]
    here = t.GetEnd() if pad.HitTest(t.GetStart()) else t.GetStart()
    layer = t.GetLayerName()
    walked = [t]
    for _ in range(50):
        vias = [v for v in b.GetTracks() if v.GetClass() == 'PCB_VIA' and v.GetNetCode() == net and v.GetPosition() == here]
        pads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() == net and p is not pad and p.IsOnLayer(t.GetLayer()) and p.HitTest(here)
                and p.GetParentFootprint().GetReference() != pad.GetParentFootprint().GetReference()]
        nxt = [o for o in tracks if o not in walked and (o.GetStart() == here or o.GetEnd() == here)]
        if vias or pads or len(nxt) != 1:
            for w in walked: b.Delete(w)
            kind = 'via' if vias else ('pad' if pads else 'junction')
            return (mm(here.x), mm(here.y), kind, layer, pads[0] if pads else None)
        t = nxt[0]; walked.append(t)
        here = t.GetEnd() if t.GetStart() == here else t.GetStart()
    return None

terms = []   # (resistor ref, pad number, terminal)
for ref in gap_res:
    f = FPS[ref]
    for p in f.Pads():
        if p.GetNetname() in ('GND',):
            terms.append((ref, p.GetNumber(), ('zone', 'GND'))); continue
        t = chain_terminal(p)
        terms.append((ref, p.GetNumber(), t))
    f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

# ---------------- 3. shifts for footprints (push compaction per quadrant) ----------------
G = 0.15
shift = {}
for q, cols in Q.items():
    left = q[1] == 'L'
    sgn = 1 if left else -1
    s_outer = cols[0]['shift']
    items = []
    for f in b.GetFootprints():
        ref = f.GetReference()
        if ref in MOTOR: continue
        x0, x1, y0, y1 = cyd(f)
        if quad_of((x0 + x1) / 2, (y0 + y1) / 2) != q: continue
        tht = any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in f.Pads())
        side = 'F' if f.GetLayer() == pcbnew.F_Cu else 'B'
        if not left: x0, x1 = -x1, -x0
        it = dict(ref=ref, sides='FB' if tht else side, x0=x0, x1=x1, y0=y0, y1=y1)
        for k, c in enumerate(cols):
            if f in c['f']: it['force'] = abs(c['shift']); it['fixed'] = True
        outer_x = (cols[0]['x'] if left else -cols[0]['x']) - 3
        it.setdefault('force', abs(s_outer) if x1 < outer_x + 3.8 and x0 < outer_x else 0.0)
        items.append(it)
    items.sort(key=lambda i: i['x0'])
    for n, i in enumerate(items):
        nl = i['x0'] + i['force']
        if not i.get('fixed'):
            for j in items[:n]:
                if not (set(i['sides']) & set(j['sides'])): continue
                if j['y1'] <= i['y0'] or j['y0'] >= i['y1']: continue
                if j['x1'] > i['x0'] + 0.01: continue
                nl = max(nl, j['x1'] + j['s'] + min(i['x0'] - j['x1'], G))
        i['s'] = nl - i['x0']
        shift[i['ref']] = i['s'] * sgn
    # report pushes beyond the inner column
    inner_x = abs(cols[2]['x'])
    for i in items:
        if not i.get('fixed') and i['s'] > 0.01 and i['x0'] > (inner_x if left else inner_x) + 4 and abs(i['s']) > 0.05:
            pass
    over = [i for i in items if i.get('fixed') and abs(i['s'] - i['force']) > 0.01]
    if over: log.append(f'{q}: FET columns pushed: {[i["ref"] for i in over]}')
    s_edge = abs(s_outer)
    log.append(f'{q}: edge shift {s_outer:+.2f}; pushed non-FET parts: ' +
               ', '.join(f"{i['ref']}{i['s']*sgn:+.2f}" for i in items if not i.get('fixed') and i['s'] > 0.01 and i['force'] == 0))

# ---------------- 4. displacement field for everything else ----------------
anchors = {q: [] for q in Q}
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref in MOTOR or ref not in shift: continue
    x0, x1, y0, y1 = cyd(f)
    anchors[quad_of((x0 + x1) / 2, (y0 + y1) / 2)].append((x0, x1, y0, y1, shift[ref]))
EDGE_SHIFT = {q: Q[q][0]['shift'] for q in Q}
INNER = {q: Q[q][2]['x'] for q in Q}

def field(x, y):
    q = quad_of(x, y)
    left = q[1] == 'L'
    band = [a for a in anchors[q] if a[2] - 1.0 <= y <= a[3] + 1.0]
    for a in band:
        if a[0] <= x <= a[1]: return a[4]
    lefts = [a for a in band if a[1] < x]; rights = [a for a in band if a[0] > x]
    L = max(lefts, key=lambda a: a[1]) if lefts else None
    R = min(rights, key=lambda a: a[0]) if rights else None
    # outer side boundary condition: edge shift; inner side (towards the centre): 0 beyond the inner column
    if left:
        sL = L[4] if L else EDGE_SHIFT[q]; xL = L[1] if L else 99.0
        sR = R[4] if R else 0.0; xR = R[0] if R else 145.0
    else:
        sL = L[4] if L else 0.0; xL = L[1] if L else 145.0
        sR = R[4] if R else EDGE_SHIFT[q]; xR = R[0] if R else 193.0
    if xR - xL < 1e-6: return (sL + sR) / 2
    t = min(1, max(0, (x - xL) / (xR - xL)))
    return sL + (sR - sL) * t

# ---------------- 5. apply ----------------
pad_shift = []   # (pad, shift) for track-end lookup, computed before moving
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref in MOTOR:
        q = quad_of(mm(f.GetPosition().x), mm(f.GetPosition().y)); cols = Q[q]
        for p in f.Pads():
            px = mm(p.GetPosition().x)
            c = min(cols, key=lambda c: abs(c['x'] - px))
            pad_shift.append((p, c['shift']))
    elif ref in shift:
        for p in f.Pads(): pad_shift.append((p, shift[ref]))
def end_shift(pt, layer, netcode):
    for p, s in pad_shift:
        if p.GetNetCode() == netcode and p.IsOnLayer(layer) and p.HitTest(pt): return s
    return field(mm(pt.x), mm(pt.y))
moves = []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        s = None
        for pd, sh in pad_shift:
            if pd.GetNetCode() == t.GetNetCode() and pd.HitTest(p): s = sh; break
        moves.append((t, 'v', s if s is not None else field(mm(p.x), mm(p.y))))
    else:
        moves.append((t, 's', end_shift(t.GetStart(), t.GetLayer(), t.GetNetCode())))
        moves.append((t, 'e', end_shift(t.GetEnd(), t.GetLayer(), t.GetNetCode())))
zone_moves = []
for z in b.Zones():
    o = z.Outline()
    pts = []
    for ci in range(o.OutlineCount()):
        ol = o.Outline(ci)
        pts.append([(mm(ol.CPoint(i).x), mm(ol.CPoint(i).y)) for i in range(ol.PointCount())])
    zone_moves.append((z, pts))
draw_moves = []
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_SHAPE' and d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_RECT:
        draw_moves.append((d, 'rect'))
    elif d.GetClass() in ('PCB_SHAPE', 'PCB_TEXT'):
        p = d.GetCenter() if d.GetClass() == 'PCB_SHAPE' and d.GetShape() == pcbnew.SHAPE_T_CIRCLE else d.GetPosition()
        x, y = mm(p.x), mm(p.y)
        if 99 <= x <= 193 and 50 <= y <= 140:
            # corner holes / their drawings travel with the edge
            if (abs(x - 101.5) < 0.2 or abs(x - 190.5) < 0.2) and (abs(y - 52.5) < 0.2 or abs(y - 137.5) < 0.2):
                draw_moves.append((d, EDGE_SHIFT[quad_of(x, y)]))
            elif d.GetLayer() != pcbnew.Edge_Cuts:
                draw_moves.append((d, field(x, y)))

for f in b.GetFootprints():
    ref = f.GetReference()
    if ref in MOTOR:
        q = quad_of(mm(f.GetPosition().x), mm(f.GetPosition().y)); cols = Q[q]
        old = sorted((mm(p.GetPosition().x), min(cols, key=lambda c: abs(c['x'] - mm(p.GetPosition().x)))['shift']) for p in f.Pads())
        def mapx(x):
            if x <= old[0][0]: return x + old[0][1]
            if x >= old[-1][0]: return x + old[-1][1]
            for (xa, sa), (xb, sb) in zip(old, old[1:]):
                if xa <= x <= xb: return x + sa + (sb - sa) * (x - xa) / (xb - xa)
        for p in f.Pads():
            px = mm(p.GetPosition().x)
            p.SetPosition(V(mapx(px), mm(p.GetPosition().y)))
        for g in f.GraphicalItems():
            if g.GetClass() == 'PCB_SHAPE' and g.GetShape() in (pcbnew.SHAPE_T_SEGMENT, pcbnew.SHAPE_T_RECT):
                s, e = g.GetStart(), g.GetEnd()
                g.SetStart(V(mapx(mm(s.x)), mm(s.y))); g.SetEnd(V(mapx(mm(e.x)), mm(e.y)))
            elif g.GetClass() in ('PCB_SHAPE', 'PCB_TEXT', 'PCB_FIELD'):
                p = g.GetPosition(); g.SetPosition(V(mapx(mm(p.x)), mm(p.y)))
        for fld in (f.Reference(), f.Value()):
            p = fld.GetPosition(); fld.SetPosition(V(mapx(mm(p.x)), mm(p.y)))
    elif ref in shift and abs(shift[ref]) > 1e-6:
        f.Move(V(shift[ref], 0))
for t, which, s in moves:
    if which == 'v': t.SetPosition(t.GetPosition() + V(s, 0))
    elif which == 's': t.SetStart(t.GetStart() + V(s, 0))
    else: t.SetEnd(t.GetEnd() + V(s, 0))
for z, pts in zone_moves:
    o = z.Outline(); o.RemoveAllContours()
    for ci, ring in enumerate(pts):
        o.NewOutline()
        for x, y in ring:
            o.Append(MM(x + field(x, y)), MM(y))
for d, s in draw_moves:
    if s == 'rect':
        st, en = d.GetStart(), d.GetEnd()
        d.SetStart(V(mm(st.x) + EDGE_SHIFT['FL'], mm(st.y))); d.SetEnd(V(mm(en.x) + EDGE_SHIFT['FR'], mm(en.y)))
    else:
        d.Move(V(s, 0))
log.append(f"outline now x {99 + EDGE_SHIFT['FL']:.2f} .. {193 + EDGE_SHIFT['FR']:.2f}  (width {94 - EDGE_SHIFT['FL'] + EDGE_SHIFT['FR']:.2f})")

# ---------------- 6. route the flipped gate resistors back to their terminals ----------------
EDGE = (99 + EDGE_SHIFT['FL'], 193 + EDGE_SHIFT['FR'], 50.0, 140.0)
HOLES = [(101.5 + EDGE_SHIFT['FL'], 52.5, 1.6), (190.5 + EDGE_SHIFT['FR'], 52.5, 1.6), (101.5 + EDGE_SHIFT['BL'], 137.5, 1.6),
         (190.5 + EDGE_SHIFT['BR'], 137.5, 1.6), (130, 80, 0.9), (160, 80, 0.9), (130, 110, 0.9), (160, 110, 0.9)]
nok = 0
for ref, num, term in terms:
    if term is None or term[0] == 'zone': continue
    x, y, kind, layer, tpad = term
    s = field(x, y)
    if tpad is not None:
        tp = tpad.GetPosition(); gx, gy = mm(tp.x), mm(tp.y)   # pads already moved
        gl = [b.GetLayerName(l) for l in tpad.GetLayerSet().CuStack()]
        gl = [l for l in gl if l in ('F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu')]
    else:
        gx, gy = x + s, y
        gl = ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu'] if kind == 'via' else [layer]
    p = [pp for pp in FPS[ref].Pads() if pp.GetNumber() == num][0]
    sp = p.GetPosition(); sx, sy = mm(sp.x), mm(sp.y)
    net = p.GetNetname()
    w = 0.25
    res = connect(b, net, (sx, sy), (gx, gy), w, ['F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu'],
                  (min(sx, gx) - 4, min(sy, gy) - 4, max(sx, gx) + 4, max(sy, gy) + 4), EDGE, HOLES,
                  start_layers=['F.Cu'], goal_layers=gl, via_cost=6.0)
    if res is None:
        log.append(f'  {ref}.{num} ({net}) -> NO ROUTE to {kind} at ({gx:.2f},{gy:.2f})'); nok += 1
log.append(f'gate resistor connections: {len([t for t in terms if t[2] and t[2][0] != "zone"])} routed, {nok} failed')
json.dump({'edge': EDGE_SHIFT, 'shift': shift}, open(sys.argv[2] + '.json', 'w'))
pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
