# KiCad python: labels.py in out - enlarge JST-GH connector labels ~2x, add LED CHn labels and the version text
import pcbnew, sys, math
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; MM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
log = []
outline = [s for s in b.GetDrawings() if s.GetLayer() == pcbnew.Edge_Cuts and s.GetClass() == 'PCB_SHAPE' and s.GetShape() == pcbnew.SHAPE_T_RECT][0]
EX0, EX1, EY0, EY1 = mm(outline.GetStart().x), mm(outline.GetEnd().x), mm(outline.GetStart().y), mm(outline.GetEnd().y)
CUBE = (125.875, 164.125, 75.875, 114.125)
GH = [f for f in b.GetFootprints() if 'GHS' in f.GetValue()]
LEDS = {'J4': 'CH1', 'J6': 'CH2', 'J7': 'CH3', 'J15': 'CH4', 'J16': 'CH5'}

def bbox(item):
    bb = item.BBox() if hasattr(item, 'BBox') else item.GetBoundingBox()
    return (mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom()))
def overlap(a, c, m=0.0):
    return a[0] < c[1] + m and a[1] > c[0] - m and a[2] < c[3] + m and a[3] > c[2] - m

# obstacles on the top side: pads (with solder mask margin), footprint silk graphics, edge
pad_boxes = []
for f in b.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask):
            pad_boxes.append(bbox(p))
fp_silk = []
for f in b.GetFootprints():
    for g in f.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE':
            fp_silk.append(bbox(g))
    for fld in (f.Reference(),):
        if fld.IsVisible() and fld.GetLayer() == pcbnew.F_SilkS: fp_silk.append(bbox(fld))
def texts_except(me):
    out = []
    for d in b.GetDrawings():
        if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS and d.m_Uuid.AsString() != me:
            out.append(bbox(d))
    return out
def fits(box, me, cube_ok=True):
    if box[0] < EX0 + 0.3 or box[1] > EX1 - 0.3 or box[2] < EY0 + 0.3 or box[3] > EY1 - 0.3: return False
    if not cube_ok and overlap(box, CUBE): return False
    if any(overlap(box, p, 0.15) for p in pad_boxes): return False
    if any(overlap(box, s, 0.1) for s in fp_silk): return False
    if any(overlap(box, t, 0.15) for t in texts_except(me)): return False
    return True

CAND = [f for f in b.GetFootprints() if f.GetLayer() == pcbnew.F_Cu and (f.GetReference().startswith('J') or f.GetReference().startswith('D'))]
GHREFS = {f.GetReference() for f in GH}
def near_gh(x, y, m=4.0):
    """the nearest connector/LED owns the label; only JST-GH owners get bigger labels"""
    best = None
    for f in CAND:
        c = f.GetCourtyard(pcbnew.F_CrtYd)
        bb = bbox(c) if c.OutlineCount() else bbox(f)
        dx = max(bb[0] - x, 0, x - bb[1]); dy = max(bb[2] - y, 0, y - bb[3])
        dd = math.hypot(dx, dy)
        if best is None or dd < best[0]: best = (dd, f.GetReference())
    for f in b.GetFootprints():                       # labels hugging a JST-SH (ESC_DBG) stay as they are
        if 'SRSS' in f.GetValue():
            bb = bbox(f.GetCourtyard(pcbnew.F_CrtYd))
            if bb[0] - 1.2 < x < bb[1] + 1.2 and bb[2] - 1.2 < y < bb[3] + 1.2: return None
    if best and best[0] <= m and best[1] in GHREFS: return best[1]
    return None

# 1) enlarge existing labels next to JST-GH connectors
for d in list(b.GetDrawings()):
    if d.GetClass() != 'PCB_TEXT' or d.GetLayer() != pcbnew.F_SilkS: continue
    x, y = mm(d.GetPosition().x), mm(d.GetPosition().y)
    owner = near_gh(x, y)
    if not owner: continue
    h0, w0, t0 = d.GetTextHeight(), d.GetTextWidth(), d.GetTextThickness()
    me = d.m_Uuid.AsString()
    done = None
    for scale in (2.0, 1.75, 1.5, 1.25):
        d.SetTextHeight(int(h0 * scale)); d.SetTextWidth(int(w0 * scale)); d.SetTextThickness(int(max(t0 * scale, MM(0.15))))
        p0 = d.GetPosition()
        for dx, dy in [(0, 0)] + [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for r in (0.3, 0.6, 0.9, 1.2, 1.6) for a in range(0, 360, 30)]:
            d.SetPosition(p0 + V(dx, dy))
            if fits(bbox(d), me):
                done = (scale, dx, dy); break
            d.SetPosition(p0)
        if done: break
    if not done:
        d.SetTextHeight(h0); d.SetTextWidth(w0); d.SetTextThickness(t0)
        log.append(f'  {d.GetText()!r} at ({x:.1f},{y:.1f}) near {owner}: kept original size (no room)')
    else:
        log.append(f'  {d.GetText()!r} near {owner}: x{done[0]}' + (f', moved ({done[1]:+.1f},{done[2]:+.1f})' if done[1] or done[2] else ''))

# 2) "CHn" next to each LED connector
def add_text(txt, h, cands, me='new', cube_ok=True, thick=None):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextHeight(MM(h)); t.SetTextWidth(MM(h)); t.SetTextThickness(MM(thick or h * 0.15))
    b.Add(t)
    for (x, y) in cands:
        t.SetPosition(V(x, y))
        if fits(bbox(t), t.m_Uuid.AsString(), cube_ok): return t, (x, y)
    b.Delete(t); return None, None
F = {f.GetReference(): f for f in b.GetFootprints()}
for ref, ch in LEDS.items():
    bb = bbox(F[ref].GetCourtyard(pcbnew.F_CrtYd))
    cx, cy = (bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2
    cands = []
    for off in (1.3, 1.8, 2.4):
        cands += [(cx, bb[2] - off), (cx, bb[3] + off), (bb[0] - off - 1.6, cy), (bb[1] + off + 1.6, cy)]
    t, pos = add_text(ch, 1.5, cands, cube_ok=False)
    log.append(f'  {ch} for {ref}: ' + (f'at ({pos[0]:.1f},{pos[1]:.1f})' if t else 'NO ROOM'))

# 3) version text on the top silkscreen, outside the Cube outline
cands = []
for yy in [EY0 + 2 + 0.5 * i for i in range(int((EY1 - EY0 - 4) / 0.5))]:
    for xx in [EX0 + 8 + 0.5 * i for i in range(int((EX1 - EX0 - 16) / 0.5))]:
        cands.append((xx, yy))
cands.sort(key=lambda p: (abs(p[1] - 95), abs(p[0] - 175)))   # prefer the right middle (clear of the SD-card note)
t, pos = add_text('BasicCarrier ${REVISION}', 1.5, cands, cube_ok=False, thick=0.25)
log.append('version text: ' + (f'at ({pos[0]:.1f},{pos[1]:.1f}), renders as {t.GetShownText(False)!r}' if t else 'NO ROOM'))

pcbnew.SaveBoard(sys.argv[2], b)
print('\n'.join(log))
