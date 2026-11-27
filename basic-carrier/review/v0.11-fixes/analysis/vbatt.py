# vbatt.py dump.json [res] [png-prefix] : VBATT drop XT90+ -> each ESC shunt at 20 A each
import sys, time, numpy as np
from solve import *
d = load(sys.argv[1]); res = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
t = time.time()
n = Net(d, 'VBATT', (99.5, 49.5, 192, 140.5), res)
xt = [p for p in d['pads'] if p['ref'] == 'J18' and p['net'] == 'VBATT' and p['drill'] > 0]
fixed = np.concatenate([n.pad_nodes(p['ref'], p['num']) for p in xt])
SH = [('ESC1', 'RSHUNT3'), ('ESC2', 'RSHUNT4'), ('ESC3', 'RSHUNT5'), ('ESC4', 'RSHUNT2')]
sinks = [(n.pad_nodes(r, 2), 20.0) for _, r in SH]
n.solve(fixed, sinks)
out = []
for (e, r), (nodes, I) in zip(SH, sinks):
    out.append(f'{e} {r}: {-n.x[nodes].mean()*1000:.0f} mV')
print(f'VBATT nodes {n.N} it {n.iters} {time.time()-t:.0f}s | ' + ' | '.join(out) + f' | loss {n.loss():.1f} W')
vc = n.via_currents()
print('VBATT vias:', len(n.vias), 'max via currents:', [(round(I, 1), round(v['x'], 2), round(v['y'], 2)) for I, v in vc[:5]])
if len(sys.argv) > 3:
    # current-density pictures per layer
    from PIL import Image
    for L in ('F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu'):
        v = n.vmap(L); gy, gx = np.gradient(np.nan_to_num(v), res * 1e-3)
        J = np.hypot(gx, gy) * GS * res * 1e-3 / (res * 1e-3) * 1e-3  # A per mm width
        J = np.where(np.isnan(v), -1, J)
        img = np.zeros(v.shape + (3,), np.uint8) + 255
        c = np.clip(J / 5.0, 0, 1)
        img[J >= 0] = np.stack([c * 255, 40 + 0 * c, (1 - c) * 160], -1)[J >= 0].astype(np.uint8)
        Image.fromarray(img).save(f'{sys.argv[3]}_{L}.png')
