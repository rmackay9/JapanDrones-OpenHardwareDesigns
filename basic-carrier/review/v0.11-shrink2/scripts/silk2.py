# KiCad python: silk2.py in out - label case/size tweaks (Serial1/2, Fan, Buzzer) after the second render review
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
def try_label(d, texts_, scales, rad=(0.0, 0.3, 0.6, 0.9, 1.2, 1.6, 2.0)):
    h0, w0, t0 = d.GetTextHeight(), d.GetTextWidth(), d.GetTextThickness(); p0 = d.GetPosition(); me = d.m_Uuid.AsString()
    for txt in texts_:
        d.SetText(txt)
        for sc in scales:
            d.SetTextHeight(MM(sc)); d.SetTextWidth(MM(sc)); d.SetTextThickness(MM(max(0.15, sc * 0.15)))
            for r in rad:
                for a in (range(0, 360, 30) if r else [0]):
                    d.SetPosition(p0 + V(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))))
                    if fits(d, me): return f'{txt!r} {sc} mm at ({mm(d.GetPosition().x):.2f},{mm(d.GetPosition().y):.2f})'
            d.SetPosition(p0)
    d.SetText(texts_[-1]); d.SetTextHeight(h0); d.SetTextWidth(w0); d.SetTextThickness(t0); d.SetPosition(p0)
    return None
def grid(d, txt, sizes, region, anchor, rot=None):
    """try sizes (largest first) on a 0.25 mm grid in region, nearest to anchor first"""
    me = d.m_Uuid.AsString(); h0, w0, t0, p0, a0 = d.GetTextHeight(), d.GetTextWidth(), d.GetTextThickness(), d.GetPosition(), d.GetTextAngleDegrees()
    d.SetText(txt)
    if rot is not None: d.SetTextAngleDegrees(rot)
    d.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); d.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    pts = sorted([(region[0] + 0.25 * i, region[2] + 0.25 * j) for i in range(int((region[1] - region[0]) / 0.25) + 1) for j in range(int((region[3] - region[2]) / 0.25) + 1)],
                 key=lambda p: math.hypot(p[0] - anchor[0], p[1] - anchor[1]))
    for sc in sizes:
        d.SetTextHeight(MM(sc)); d.SetTextWidth(MM(sc)); d.SetTextThickness(MM(max(0.15, sc * 0.15)))
        for x, y in pts:
            d.SetPosition(V(x, y))
            if fits(d, me): return f'{txt!r} {sc} mm at ({x:.2f},{y:.2f}) rot {d.GetTextAngleDegrees():.0f}'
    d.SetTextHeight(h0); d.SetTextWidth(w0); d.SetTextThickness(t0); d.SetPosition(p0); d.SetTextAngleDegrees(a0)
    return None
for d in T:
    t = d.GetText()
    if t == 'SERIAL1':
        d.SetText('Serial1'); log.append(f'SERIAL1 -> Serial1 (size {mm(d.GetTextHeight())} mm), fits: {fits(d, d.m_Uuid.AsString())}')
    elif t == 'SERIAL2':
        # no room for 2 mm beside J13 (pad array on its left): put it above J13, horizontal like Serial1 over J12
        jb = bbox(F['J13'].GetCourtyard(pcbnew.F_CrtYd))
        r = grid(d, 'Serial2', (2.0,), (jb[0] - 4, jb[1] + 4, jb[2] - 4, jb[2] - 0.8), ((jb[0] + jb[1]) / 2, jb[2] - 1.6), rot=0)
        log.append(f'SERIAL2 -> {r}' if r else 'SERIAL2 -> Serial2: no room to enlarge, kept 1.0 mm')
        if not r: d.SetText('Serial2')
    elif t == 'FAN':
        jb = bbox(F['J14'].GetCourtyard(pcbnew.F_CrtYd))
        r = grid(d, 'Fan', (2.0, 1.75, 1.5), (jb[0] - 6, jb[1] + 6, jb[2] - 1, jb[3] + 1.5), ((jb[0] + jb[1]) / 2, (jb[2] + jb[3]) / 2), rot=0)
        if not r: d.SetText('Fan')
        log.append(f'FAN -> {r}')
    elif t == 'BUZ':
        r = try_label(d, ['Buzzer', 'Buzz'], (mm(d.GetTextHeight()),))
        log.append(f'BUZ -> {r}')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
