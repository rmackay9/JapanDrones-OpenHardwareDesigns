import sys, numpy as np, time, pickle
from cu import *
tag = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
amps = [float(a) for a in sys.argv[3].split(',')] if len(sys.argv) > 3 else [20, 20, 20, 20]
b = Board(tag + '.json', res=50)
print('grid', b.W, b.H, 'fine px; coarse h =', k / b.res)
# islands per layer
for L in LAYERS:
    m = b.mask('VBATT', L)
    n, lab, st, ce = islands(m)
    big = sorted([(st[i, cv2.CC_STAT_AREA] / b.res ** 2, i) for i in range(1, n + 1)], reverse=True)
    print(L, 'VBATT area %.0f mm2, islands %d:' % (m.sum() / b.res ** 2, n), ['%.1f' % a for a, i in big[:12]])
t = time.time()
N = Net3D(b, 'VBATT', k=k)
print('nodes', N.n, 'edges', len(N.ei), 'vias', len(N.vias), 'build %.1fs' % (time.time() - t))
comp = N.components()
src = N.pad_nodes('J18', 'P')
root = comp[src[0]]
print('XT90+ nodes', len(src), 'same comp', (comp[src] == root).all(), '; nodes not connected to XT90+: %d (%.1f mm2)' % ((comp != root).sum(), (comp != root).sum() * N.h ** 2))
shunts = {'ESC1': ('RSHUNT3', '2'), 'ESC2': ('RSHUNT4', '2'), 'ESC3': ('RSHUNT5', '2'), 'ESC4': ('RSHUNT2', '2')}
inj = []; sn = {}
for (e, (ref, num)), a in zip(shunts.items(), amps):
    ids = N.pad_nodes(ref, num); sn[e] = ids
    print(e, ref, 'pad nodes', len(ids), 'connected', (comp[ids] == root).all())
    if a: inj.append((ids, -a))
t = time.time()
v = N.solve(src, inj, tol=1e-8, verbose=False)
print('solve %.0fs, %d iters' % (time.time() - t, N.iters))
for e, ids in sn.items():
    print('%s drop: mean %.1f mV, min %.1f max %.1f' % (e, -v[ids].mean() * 1e3, -v[ids].max() * 1e3, -v[ids].min() * 1e3))
P = N.power(v)
print('total VBATT copper loss %.2f W' % P, ' check sum(I*V)= %.2f' % sum(-a * v[ids].mean() for ids, a in inj))
# per layer power
pw = N.eg * (v[N.ei] - v[N.ej]) ** 2
la = N.layer_of[N.ei]; lb = N.layer_of[N.ej]
for li, L in enumerate(LAYERS):
    print('  loss in', L, '%.2f W' % pw[(la == li) & (lb == li)].sum())
print('  loss in via barrels %.2f W' % pw[la != lb].sum())
vc = N.via_currents(v)
rows = []
for via, segs in vc:
    mx = max((abs(a) for _, _, a in segs), default=0)
    rows.append((mx, via['x'], via['y'], via['drill'], segs))
rows.sort(reverse=True, key=lambda r: r[0])
print('vias: n=%d, top currents:' % len(rows))
for r in rows[:25]:
    print('  (%.2f,%.2f) d%.2f  max %.2f A  ' % (r[1], r[2], r[3], r[0]) + ' '.join('%s>%s %.2f' % (a[:3], bb[:3], c) for a, bb, c in r[4]))
print('vias >3A: %d, >2A: %d, >1A: %d' % (sum(r[0] > 3 for r in rows), sum(r[0] > 2 for r in rows), sum(r[0] > 1 for r in rows)))
pickle.dump({'v': v, 'tag': tag, 'k': k}, open('vbatt_%s_k%d.pkl' % (tag, k), 'wb'))
# fields for pictures
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, axs = plt.subplots(2, 3, figsize=(27, 18))
ext = [b.x0, b.x0 + N.Wc * N.h, b.y0 + N.Hc * N.h, b.y0]
for ax, L in zip(axs.flat, ['F.Cu', 'In2.Cu', 'In3.Cu']):
    V, J = N.field(L, v)
    Jm = np.ma.masked_where(np.isnan(V), J)
    im = ax.imshow(Jm, extent=ext, cmap='turbo', vmin=0, vmax=8, interpolation='nearest'); ax.set_title('%s VBATT sheet current A/mm (%s)' % (L, tag)); plt.colorbar(im, ax=ax, fraction=0.04)
    ax.set_facecolor('#dddddd')
for ax, L in zip(axs.flat[3:], ['F.Cu', 'In2.Cu', 'In3.Cu']):
    V, J = N.field(L, v)
    im = ax.imshow(-V * 1e3, extent=ext, cmap='viridis', interpolation='nearest'); ax.set_title('%s VBATT drop mV' % L); plt.colorbar(im, ax=ax, fraction=0.04)
    ax.set_facecolor('#dddddd')
    for via, segs in vc: ax.plot(via['x'], via['y'], 'w.', ms=2)
plt.tight_layout(); plt.savefig('vbatt_%s.png' % tag, dpi=90)
