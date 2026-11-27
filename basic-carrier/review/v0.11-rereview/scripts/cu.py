# Independent copper model for the v0.11 re-review (system python: numpy + cv2).
import json, math, numpy as np, cv2, collections

RHO = 1.72e-8          # ohm m, copper 20 C
T_CU = 35e-6
RS = RHO / T_CU        # ohm/sq, 1 oz
T_PLATE = 20e-6
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']
Z = [0.0, 0.135, 0.705, 0.84, 1.41, 1.545]   # mm, from the board stackup
SHIFT = 6

class Board:
    def __init__(self, path, res=50, pad=0.3):
        self.d = json.load(open(path))
        o = self.d['outline'][0]['o']
        xs = [p[0] for p in o]; ys = [p[1] for p in o]
        self.x0 = min(xs) - pad; self.y0 = min(ys) - pad
        self.res = res
        self.W = int(math.ceil((max(xs) + pad - self.x0) * res)); self.H = int(math.ceil((max(ys) + pad - self.y0) * res))
        self._cache = {}

    # ---- raster helpers
    def px(self, pts):
        a = np.asarray(pts, dtype=np.float64)
        a = (a - [self.x0, self.y0]) * self.res - 0.5
        return np.round(a * (1 << SHIFT)).astype(np.int32)

    def _poly(self, img, outline, holes=()):
        cs = [self.px(outline)] + [self.px(h) for h in holes if len(h) >= 3]
        if not holes:
            cv2.fillPoly(img, cs, 1, lineType=cv2.LINE_8, shift=SHIFT); return
        allp = np.vstack(cs) >> SHIFT
        x0 = max(int(allp[:, 0].min()) - 2, 0); y0 = max(int(allp[:, 1].min()) - 2, 0)
        x1 = min(int(allp[:, 0].max()) + 3, self.W); y1 = min(int(allp[:, 1].max()) + 3, self.H)
        if x1 <= x0 or y1 <= y0: return
        tmp = np.zeros((y1 - y0, x1 - x0), np.uint8)
        off = np.array([x0, y0], np.int32) << SHIFT
        cv2.fillPoly(tmp, [cs[0] - off], 1, lineType=cv2.LINE_8, shift=SHIFT)
        # holes: erase interior only (keep the hole boundary pixel as copper is wrong; erase with fill then
        # the 1 px boundary is erased too, which makes holes ~0.5 px larger. conservative for copper.)
        cv2.fillPoly(tmp, [c - off for c in cs[1:]], 0, lineType=cv2.LINE_8, shift=SHIFT)
        np.maximum(img[y0:y1, x0:x1], tmp, out=img[y0:y1, x0:x1])

    @staticmethod
    def stadium(x0, y0, x1, y1, w, n=12):
        r = w / 2; dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy)
        if L < 1e-9:
            return [[x0 + r * math.cos(2 * math.pi * i / (2 * n)), y0 + r * math.sin(2 * math.pi * i / (2 * n))] for i in range(2 * n)]
        a0 = math.atan2(dy, dx); pts = []
        for i in range(n + 1):
            a = a0 - math.pi / 2 + math.pi * i / n; pts.append([x1 + r * math.cos(a), y1 + r * math.sin(a)])
        for i in range(n + 1):
            a = a0 + math.pi / 2 + math.pi * i / n; pts.append([x0 + r * math.cos(a), y0 + r * math.sin(a)])
        return pts

    @staticmethod
    def circle(x, y, r, n=32):
        return [[x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)] for i in range(n)]

    def mask(self, net, layer, zones=True, tracks=True, pads=True, vias=True, zone_filter=None):
        """Fine raster of every piece of copper of `net` on `layer`. net may be a predicate."""
        key = (net if isinstance(net, str) else id(net), layer, zones, tracks, pads, vias, zone_filter)
        if key in self._cache: return self._cache[key]
        match = (lambda n: n == net) if isinstance(net, str) else net
        img = np.zeros((self.H, self.W), np.uint8)
        d = self.d
        if zones:
            for z in d['zones']:
                if z['rule'] or not match(z['net']) or layer not in z['fill']: continue
                if zone_filter and not zone_filter(z): continue
                for p in z['fill'][layer]:
                    self._poly(img, p['o'], p['h'])
        if tracks:
            for t in d['tracks']:
                if t['layer'] != layer or not match(t['net']): continue
                if 'poly' in t:
                    for p in t['poly']: self._poly(img, p['o'], p['h'])
                else:
                    self._poly(img, self.stadium(t['x0'], t['y0'], t['x1'], t['y1'], t['w']))
        if vias:
            for v in d['vias']:
                if not match(v['net']) or layer not in v['layers'] or not v['layers'][layer]['flashed']: continue
                self._poly(img, self.circle(v['x'], v['y'], v['layers'][layer]['d'] / 2))
        if pads:
            for p in d['pads']:
                if not match(p['net']) or layer not in p['layers']: continue
                for q in p['layers'][layer]: self._poly(img, q['o'], q['h'])
        self._cache[key] = img
        return img

    def rc(self, x, y):
        return int((y - self.y0) * self.res), int((x - self.x0) * self.res)

    def xy(self, r, c):
        return self.x0 + (c + 0.5) / self.res, self.y0 + (r + 0.5) / self.res


def islands(img, conn=4):
    n, lab, stats, cent = cv2.connectedComponentsWithStats(img, connectivity=conn)
    return n - 1, lab, stats, cent


def via_g(drill_mm, dz_mm, plate=T_PLATE):
    """Conductance (S) of a plated barrel segment."""
    a = math.pi * plate * (drill_mm * 1e-3 + plate)
    return a / (RHO * dz_mm * 1e-3)


class Net3D:
    """Resistor network of one net over all six layers. Coarse cell = k x k fine pixels."""
    def __init__(self, board, net, k=5, layers=LAYERS, mask_fn=None):
        self.b = board; self.net = net; self.k = k; self.h = k / board.res
        H = board.H // k; W = board.W // k
        self.Hc, self.Wc = H, W
        self.idx = {}; ei = []; ej = []; eg = []
        n = 0
        self.fine = {}
        self.layer_of = []
        for li, L in enumerate(layers):
            m = (mask_fn(L) if mask_fn else board.mask(net, L))[:H * k, :W * k]
            self.fine[L] = m
            blk = m.reshape(H, k, W, k)
            cov = blk.sum(axis=(1, 3))
            # face links
            right = (blk[:, :, :-1, k - 1] & blk[:, :, 1:, 0]).sum(axis=1) / k      # (H, W-1)
            down = (blk[:-1, k - 1, :, :] & blk[1:, 0, :, :]).sum(axis=2) / k        # (H-1, W)
            node = cov > 0
            ids = np.full((H, W), -1, np.int64)
            ids[node] = n + np.arange(node.sum())
            n += int(node.sum())
            self.idx[L] = ids
            r, c = np.nonzero(right > 0)
            ei.append(ids[r, c]); ej.append(ids[r, c + 1]); eg.append(right[r, c] / RS)
            r, c = np.nonzero(down > 0)
            ei.append(ids[r, c]); ej.append(ids[r + 1, c]); eg.append(down[r, c] / RS)
            self.layer_of.append(np.full(int(node.sum()), li))
        self.n = n
        self.layer_of = np.concatenate(self.layer_of)
        self.layers = layers
        # vias / through-hole pads
        self.via_edges = []   # (via index, segment, slice into edge arrays)
        self.vias = []
        ne = sum(len(a) for a in ei)
        for v in board.d['vias']:
            if v['net'] != net and not (callable(net) and net(v['net'])): continue
            ls = [L for L in layers if L in v['layers']]
            cells = self._disc_cells(v['x'], v['y'], v['drill'] / 2 + 0.05)
            segs = []
            for a, bL in zip(ls[:-1], ls[1:]):
                dz = Z[LAYERS.index(bL)] - Z[LAYERS.index(a)]
                g = via_g(v['drill'], dz)
                ia = [self.idx[a][r, c] for r, c in cells]; ib = [self.idx[bL][r, c] for r, c in cells]
                pr = [(x, y) for x, y in zip(ia, ib) if x >= 0 and y >= 0]
                if not pr: continue
                ei.append(np.array([p[0] for p in pr])); ej.append(np.array([p[1] for p in pr])); eg.append(np.full(len(pr), g / len(pr)))
                segs.append((a, bL, ne, ne + len(pr))); ne += len(pr)
            self.vias.append((v, segs))
        # plated through-hole pads: tie the layers with a low-resistance link at the pad centre ring
        for p in board.d['pads']:
            if p['drill'] <= 0 or p['attr'] != 0: continue
            if p['net'] != net and not (callable(net) and net(p['net'])): continue
            ls = [L for L in layers if L in p['layers']]
            cells = self._disc_cells(p['x'], p['y'], max(p['sx'], p['sy']) / 2)
            for a, bL in zip(ls[:-1], ls[1:]):
                dz = Z[LAYERS.index(bL)] - Z[LAYERS.index(a)]
                g = via_g(p['drill'], dz)
                pr = [(self.idx[a][r, c], self.idx[bL][r, c]) for r, c in cells]
                pr = [(x, y) for x, y in pr if x >= 0 and y >= 0]
                if not pr: continue
                ei.append(np.array([q[0] for q in pr])); ej.append(np.array([q[1] for q in pr])); eg.append(np.full(len(pr), g / len(pr)))
                ne += len(pr)
        self.ei = np.concatenate(ei); self.ej = np.concatenate(ej); self.eg = np.concatenate(eg).astype(np.float64)
        self.diag = np.bincount(self.ei, self.eg, n) + np.bincount(self.ej, self.eg, n)

    def _disc_cells(self, x, y, r):
        b = self.b; h = self.h
        c0 = int((x - r - b.x0) / h); c1 = int((x + r - b.x0) / h) + 1
        r0 = int((y - r - b.y0) / h); r1 = int((y + r - b.y0) / h) + 1
        out = []
        for rr in range(r0, r1 + 1):
            for cc in range(c0, c1 + 1):
                if 0 <= rr < self.Hc and 0 <= cc < self.Wc:
                    cx = b.x0 + (cc + 0.5) * h; cy = b.y0 + (rr + 0.5) * h
                    if (cx - x) ** 2 + (cy - y) ** 2 <= r * r: out.append((rr, cc))
        return out

    def cells_in_poly(self, layer, polys):
        """node ids of coarse cells whose centre lies in pad polygon(s) (list of {'o','h'})"""
        b = self.b
        img = np.zeros((b.H, b.W), np.uint8)
        for p in polys: b._poly(img, p['o'], p['h'])
        k = self.k
        cov = img[:self.Hc * k, :self.Wc * k].reshape(self.Hc, k, self.Wc, k).sum(axis=(1, 3))
        ids = self.idx[layer][(cov * 2 >= k * k)]
        return ids[ids >= 0]

    def pad_nodes(self, ref, num, layer=None):
        out = []
        for p in self.b.d['pads']:
            if p['ref'] == ref and p['num'] == num:
                for L, polys in p['layers'].items():
                    if (layer is None or L == layer) and L in self.idx:
                        out.append(self.cells_in_poly(L, polys))
        return np.concatenate(out) if out else np.array([], np.int64)

    def components(self):
        """connected components of the network (union-find by label propagation)"""
        lab = np.arange(self.n)
        while True:
            m = np.minimum(lab[self.ei], lab[self.ej])
            new = lab.copy()
            np.minimum.at(new, self.ei, m); np.minimum.at(new, self.ej, m)
            new = new[new]  # pointer jump
            if np.array_equal(new, lab): break
            lab = new
        return lab

    def solve(self, fixed, inject, tol=1e-9, maxit=60000, x0=None, verbose=False):
        """fixed: node ids held at 0 V. inject: {node ids array: total amps injected (negative = drawn)}.
        Returns node voltages."""
        n = self.n
        free = np.ones(n, bool); free[fixed] = False
        b = np.zeros(n)
        for ids, amps in inject:
            b[ids] += amps / len(ids)
        b[~free] = 0
        dg = self.diag.copy(); dg[dg == 0] = 1.0
        ei, ej, eg = self.ei, self.ej, self.eg
        def A(x):
            y = dg * x - np.bincount(ei, eg * x[ej], n) - np.bincount(ej, eg * x[ei], n)
            y[~free] = 0
            return y
        x = np.zeros(n) if x0 is None else x0.copy(); x[~free] = 0
        r = b - A(x); r[~free] = 0
        z = r / dg; p = z.copy(); rz = r @ z; bn = np.linalg.norm(b)
        for it in range(maxit):
            Ap = A(p); a = rz / (p @ Ap)
            x += a * p; r -= a * Ap
            if it % 50 == 0:
                rn = np.linalg.norm(r)
                if verbose and it % 500 == 0: print('  it', it, 'res', rn / bn)
                if rn < tol * bn: break
            z = r / dg; rz2 = r @ z; p = z + (rz2 / rz) * p; rz = rz2
        self.iters = it
        return x

    def edge_current(self, v):
        return self.eg * (v[self.ei] - v[self.ej])

    def via_currents(self, v):
        """per via: list of (layerA, layerB, amps flowing A->B)"""
        ic = self.edge_current(v); out = []
        for via, segs in self.vias:
            out.append((via, [(a, bL, float(ic[s:e].sum())) for a, bL, s, e in segs]))
        return out

    def power(self, v):
        return float((self.eg * (v[self.ei] - v[self.ej]) ** 2).sum())

    def node_xy(self, layer):
        ids = self.idx[layer]; r, c = np.nonzero(ids >= 0)
        return ids[r, c], self.b.x0 + (c + 0.5) * self.h, self.b.y0 + (r + 0.5) * self.h

    def field(self, layer, v):
        """2-D arrays: voltage (nan where no copper) and sheet current density magnitude in A/mm"""
        ids = self.idx[layer]; V = np.full(ids.shape, np.nan); m = ids >= 0; V[m] = v[ids[m]]
        ic = self.edge_current(v)
        lo = ids[m].min() if m.any() else 0; hi = ids[m].max() if m.any() else -1
        jx = np.zeros(self.n); jy = np.zeros(self.n)
        # in-plane edges: ej == ei+1 is not guaranteed; classify by row/col lookup
        pos = {}
        r, c = np.nonzero(m); rowof = np.zeros(self.n, np.int64); colof = np.zeros(self.n, np.int64)
        rowof[ids[r, c]] = r; colof[ids[r, c]] = c
        sel = (self.ei >= lo) & (self.ei <= hi) & (self.ej >= lo) & (self.ej <= hi)
        e_i = self.ei[sel]; e_j = self.ej[sel]; cur = np.abs(ic[sel])
        horiz = rowof[e_i] == rowof[e_j]
        np.maximum.at(jx, e_i[horiz], cur[horiz]); np.maximum.at(jx, e_j[horiz], cur[horiz])
        np.maximum.at(jy, e_i[~horiz], cur[~horiz]); np.maximum.at(jy, e_j[~horiz], cur[~horiz])
        J = np.zeros(ids.shape); J[m] = np.hypot(jx[ids[m]], jy[ids[m]]) / self.h
        return V, J
