# mvdd.py dump.json [png-prefix]: per-ESC MVDD islands, shunt->FET vias, drop at 20 A shunt -> middle HS FET
import sys, numpy as np
from solve import *
from comps import comps
d = load(sys.argv[1])
ESC = [('ESC1', 'mod1', 'RSHUNT3', 'Q11', (158, 62, 191.5, 92)), ('ESC2', 'mod2', 'RSHUNT4', 'Q17', (158, 98, 191.5, 128)),
       ('ESC3', 'mod3', 'RSHUNT5', 'Q23', (100, 98, 133, 128)), ('ESC4', 'mod', 'RSHUNT2', 'Q5', (100, 62, 133, 92))]
for name, mod, sh, q, bb in ESC:
    net = f'/VimDrones_{mod}/MVDD'
    R = Raster(bb, 0.05); A = 0.05 * 0.05
    isl = {}
    for L in ('F.Cu', 'B.Cu'):
        lab, k = label(net_mask(d, R, net, L))
        areas = np.bincount(lab.ravel())[1:] * A
        isl[L] = (lab, areas)
    # shunt island (F) and drain island(s) (B)
    def pad_lab(L, ref, num):
        lab = isl[L][0]
        p = [p for p in d['pads'] if p['ref'] == ref and p['num'] == num][0]
        im = R.new(); from PIL import ImageDraw; R.polyset(ImageDraw.Draw(im), p['layers'][L]); m = np.array(im) > 0
        v = lab[m]; v = v[v > 0]; return int(np.bincount(v).argmax()) if len(v) else 0
    fs = pad_lab('F.Cu', sh, '1')
    hs = [r for r in {p['ref'] for p in d['pads'] if p['net'] == net and p['ref'].startswith('Q')}]
    bdr = {r: pad_lab('B.Cu', r, '9') for r in hs}
    nvia = {r: 0 for r in hs}; drills = []
    for v in d['vias']:
        if v['net'] != net: continue
        cx, cy = R.px(v['x'], v['y']); cx, cy = int(cx), int(cy)
        if not (0 <= cy < R.H and 0 <= cx < R.W): continue
        if isl['F.Cu'][0][cy, cx] == fs:
            for r in hs:
                if isl['B.Cu'][0][cy, cx] == bdr[r]: nvia[r] += 1
    big = {L: int((isl[L][1] >= 1.0).sum()) for L in isl}
    small = {L: int(((isl[L][1] > 0) & (isl[L][1] < 1.0)).sum()) for L in isl}
    shA = isl['F.Cu'][1][fs - 1]
    groups = {}
    for r in hs: groups.setdefault(bdr[r], []).append(r)
    via_s = ', '.join(f"{'+'.join(sorted(rs))}: {nvia[rs[0]]}" for g, rs in groups.items())
    # solver
    n = Net(d, net, bb, 0.1)
    fixed = n.pad_nodes(sh, '1')
    sink = np.concatenate([n.pad_nodes(q, k) for k in ('5', '6', '7', '8', '9')])
    n.solve(fixed, [(sink, 20.0)])
    drop = -n.x[sink].mean() * 1000
    vc = n.via_currents()
    print(f'{name}: islands >=1mm2 F {big["F.Cu"]} B {big["B.Cu"]} (tiny F {small["F.Cu"]} B {small["B.Cu"]}) | shunt top island {shA:.0f} mm2 | '
          f'vias shunt-top -> drain-bottom [{via_s}] | MVDD vias {len(n.vias)} | drop 20A->{q} {drop:.0f} mV, max via {vc[0][0]:.1f} A')
