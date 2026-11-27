# KiCad python: 1-D push compaction in x for one quadrant; reports blocking parts.
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
quad = sys.argv[2]            # FL, BL, FR, BR
SKIP = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else set()
G = 0.15
CUBE = (125.875, 164.125, 75.875, 114.125)
front = quad[0] == 'F'
left = quad[1] == 'L'
ylo, yhi = (49, 95) if front else (95, 141)
items = []
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref in ('J2', 'J19', 'J22', 'J25') or ref in SKIP: continue
    side = 'F' if f.GetLayer() == pcbnew.F_Cu else 'B'
    c = f.GetCourtyard(pcbnew.F_CrtYd if side == 'F' else pcbnew.B_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    x0, x1, y0, y1 = mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom())
    if y1 < ylo or y0 > yhi: continue
    if ((x0 + x1) / 2 < 145) != left: continue
    tht = any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in f.Pads())
    sides = 'FB' if tht else side
    if not left:   # mirror x so the algorithm always pushes towards +x
        x0, x1 = -x1, -x0
    items.append(dict(ref=ref, val=f.GetValue(), sides=sides, x0=x0, x1=x1, y0=y0, y1=y1, side=side))
# Cube holes as fixed items
for hx in (130, 160):
    for hy in (80, 110):
        if ylo <= hy <= yhi:
            x0, x1 = hx - 1.2, hx + 1.2
            if not left: x0, x1 = -x1, -x0
            items.append(dict(ref='HOLE', val='', sides='FB', x0=x0, x1=x1, y0=hy - 1.2, y1=hy + 1.2, side='B'))
# FET phase columns -> forced shifts
fets = sorted([i for i in items if i['val'].startswith('TPHR')], key=lambda i: i['x0'])
cols = []
for i in fets:
    for c in cols:
        if abs(c[0]['x0'] - i['x0']) < 3 or abs((c[0]['x0'] + c[0]['x1']) / 2 - (i['x0'] + i['x1']) / 2) < 3: c.append(i); break
    else: cols.append([i])
cols.sort(key=lambda c: min(i['x0'] for i in c))
centres = [sum((i['x0'] + i['x1']) / 2 for i in c) / len(c) for c in cols]
pitch = [centres[1] - centres[0], centres[2] - centres[1]]
P = float(__import__('os').environ.get('PITCH', '8.5'))
s_outer = (pitch[0] - P) + (pitch[1] - P); s_mid = pitch[1] - P
EDGE_SHIFT = s_outer
for k, c in enumerate(cols):
    for i in c: i['force'] = (s_outer, s_mid, 0.0)[k]; i['fixed'] = True
inner_limit = max(i['x1'] for i in cols[2])    # right side of the innermost phase column
for i in items:
    i.setdefault('force', EDGE_SHIFT if i['x0'] < centres[0] - 3 else 0.0)
    i['ub'] = 0.0 if i['ref'] == 'HOLE' or i['x0'] > inner_limit + 0.5 else 99
    if 'fixed' in i: i['ub'] = i['force']
    # top-side parts must not enter the Cube outline
    cx0 = CUBE[0] if left else -CUBE[1]
    if i['side'] == 'F' and 'F' in i['sides'] and i['y1'] > CUBE[2] and i['y0'] < CUBE[3] and i['x1'] <= cx0 + 0.01:
        i['ub'] = min(i['ub'], cx0 - i['x1'])
items.sort(key=lambda i: i['x0'])
for n, i in enumerate(items):
    nl = i['x0'] + i['force']
    i['by'] = 'force'
    for j in items[:n]:
        if not (set(i['sides']) & set(j['sides'])): continue
        if j['y1'] <= i['y0'] or j['y0'] >= i['y1']: continue
        if j['x1'] > i['x0'] + 0.01: continue     # already overlapping / not left of i
        gap = i['x0'] - j['x1']
        cand = j['x1'] + j['shift'] + min(gap, G)
        if cand > nl: nl, i['by'] = cand, j['ref']
    i['shift'] = nl - i['x0']
bad = [i for i in items if i['shift'] > i['ub'] + 0.01]
print(f'{quad}: pitches {pitch[0]:.2f} {pitch[1]:.2f} -> outer shift {s_outer:.2f}, mid {s_mid:.2f}')
for i in bad:
    print(f"   BLOCK {i['ref']:8} {i['val'][:12]:12} side {i['side']} shift {i['shift']:.2f} > limit {i['ub']:.2f}  pushed by {i['by']}")
json.dump({i['ref']: round(i['shift'], 3) * (1 if left else -1) for i in items if i['ref'] != 'HOLE'}, open(sys.argv[3], 'w'))
