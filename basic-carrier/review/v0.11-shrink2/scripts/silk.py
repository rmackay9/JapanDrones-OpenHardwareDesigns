# KiCad python: silk.py in out - silkscreen tweaks after the v0.11 render review
import pcbnew, sys, math
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
log = []
EX0, EX1, EY0, EY1 = 100.11, 191.25, 50.0, 140.0
F = {f.GetReference(): f for f in b.GetFootprints()}
def bbox(item):
    bb = item.BBox() if hasattr(item, 'BBox') else item.GetBoundingBox()
    return (mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom()))
def overlap(a, c, m=0.0):
    return a[0] < c[1] + m and a[1] > c[0] - m and a[2] < c[3] + m and a[3] > c[2] - m
pad_boxes = [bbox(p) for f in b.GetFootprints() for p in f.Pads() if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask)]
def fp_silk(skip=None):
    out = []
    for f in b.GetFootprints():
        for g in f.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE': out.append(bbox(g))
        r = f.Reference()
        if r.IsVisible() and r.GetLayer() == pcbnew.F_SilkS and r is not skip and r.m_Uuid.AsString() != getattr(skip, 'uuid', None): out.append(bbox(r))
    return out
def texts(skip):
    return [bbox(d) for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS and d.m_Uuid.AsString() != skip]
def fits(item, skip_uuid, ref_skip=None, mp=0.15):
    bx = bbox(item)
    if bx[0] < EX0 + 0.3 or bx[1] > EX1 - 0.3 or bx[2] < EY0 + 0.3 or bx[3] > EY1 - 0.3: return False
    if any(overlap(bx, p, mp) for p in pad_boxes): return False
    if any(overlap(bx, s, 0.1) for s in fp_silk(ref_skip)): return False
    if any(overlap(bx, t, 0.15) for t in texts(skip_uuid)): return False
    return True
def place(item, cands, skip_uuid, ref_skip=None):
    p0 = item.GetPosition()
    for x, y in cands:
        item.SetPosition(V(x, y))
        if fits(item, skip_uuid, ref_skip): return (x, y)
    item.SetPosition(p0); return None
T = [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS]

# 1) renames
RENAME = {'CAN_1': 'CAN1', 'SERIAL 1': 'SERIAL1', 'SERIAL 2': 'SERIAL2'}
for d in T:
    if d.GetText() in RENAME:
        log.append(f'rename {d.GetText()!r} -> {RENAME[d.GetText()]!r} at ({mm(d.GetPosition().x):.1f},{mm(d.GetPosition().y):.1f})'); d.SetText(RENAME[d.GetText()])
# ESC_DBG: front = low y. ESC1 front-right, ESC2 back-right, ESC3 back-left, ESC4 front-left
for d in T:
    if d.GetText() == 'ESC_DBG':
        x, y = mm(d.GetPosition().x), mm(d.GetPosition().y)
        n = {(True, True): 1, (True, False): 2, (False, False): 3, (False, True): 4}[(x > 145.68, y < 95)]
        was = fits(d, d.m_Uuid.AsString())
        d.SetText(f'ESC{n} DBG')
        log.append(f'  original ESC_DBG fitted: {was}')
        ok = fits(d, d.m_Uuid.AsString())
        if not ok:
            r = place(d, [(x + dx, y + dy) for r_ in (0.2, 0.4, 0.6, 0.8, 1.0) for dx, dy in ((0, -r_), (0, r_), (-r_, 0), (r_, 0))], d.m_Uuid.AsString())
            ok = f'moved to {r}' if r else 'DOES NOT FIT CLEANLY'
        log.append(f'ESC_DBG at ({x:.1f},{y:.1f}) -> {d.GetText()!r} ({ok})')

# 2) version text right of C112
ver = [d for d in T if d.GetText().startswith('BasicCarrier')][0]
cb = bbox(F['C112'].GetCourtyard(pcbnew.F_CrtYd))
w = bbox(ver)[1] - bbox(ver)[0]
cands = sorted([(cb[1] + 2.4 + w / 2 + 0.25 * i, 128 + 0.25 * j) for i in range(40) for j in range(46)],
               key=lambda p: (p[0] - cb[1]) + 0.7 * abs(p[1] - 133.5))
r = place(ver, cands, ver.m_Uuid.AsString())
log.append(f'version text: C112 courtyard x {cb[0]:.2f}..{cb[1]:.2f} y {cb[2]:.2f}..{cb[3]:.2f}; text -> {r}')

# 3) RC label 2x, J3 refdes out of the way
rc = [d for d in T if d.GetText() == 'RC'][0]
j3 = F['J3']; ref = j3.Reference(); jb = bbox(j3.GetCourtyard(pcbnew.F_CrtYd))
rc.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); rc.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
rc.SetTextHeight(MM(2.0)); rc.SetTextWidth(MM(2.0)); rc.SetTextThickness(MM(0.3))
ref.SetVisible(False)
cx = (jb[0] + jb[1]) / 2
r = place(rc, [(cx + dx * 0.25, jb[3] + 1.3 + dy * 0.25) for dy in range(0, 12) for dx in (0, -1, 1, -2, 2, -3, 3, -4, 4)], rc.m_Uuid.AsString())
log.append(f'RC: J3 courtyard x {jb[0]:.2f}..{jb[1]:.2f} y {jb[2]:.2f}..{jb[3]:.2f}; RC 2.0 mm -> {r}')
ref.SetVisible(True)
cy_ = (jb[2] + jb[3]) / 2
c = sorted([(jb[0] - 3 + 0.25 * i, jb[2] - 3 + 0.25 * j) for i in range(int((jb[1] - jb[0] + 6) / 0.25)) for j in range(int((jb[3] - jb[2] + 6) / 0.25))],
           key=lambda p: max(jb[0] - p[0], 0, p[0] - jb[1]) + max(jb[2] - p[1], 0, p[1] - jb[3]))
p0 = ref.GetPosition()
for x, y in c:
    ref.SetPosition(V(x, y))
    bx = bbox(ref)
    if not (any(overlap(bx, p, 0.15) for p in pad_boxes) or any(overlap(bx, t, 0.15) for t in texts('')) or
            any(overlap(bx, s, 0.1) for f in b.GetFootprints() for s in ([bbox(g) for g in f.GraphicalItems() if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE'] + ([bbox(f.Reference())] if f.GetReference() != 'J3' and f.Reference().IsVisible() and f.Reference().GetLayer() == pcbnew.F_SilkS else [])))):
        log.append(f'J3 refdes -> ({x:.2f},{y:.2f})'); break
else:
    ref.SetPosition(p0); log.append('J3 refdes: NO SPOT')

# CH3 label check
ch3 = [d for d in T if d.GetText() == 'CH3'][0]
log.append(f'CH3 at ({mm(ch3.GetPosition().x):.2f},{mm(ch3.GetPosition().y):.2f}) fits: {fits(ch3, ch3.m_Uuid.AsString())}')
pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[2], b)
