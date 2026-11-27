# DC copper solver over a net: grid per layer + via barrels. system python (numpy, PIL)
import numpy as np, math
from PIL import Image, ImageDraw
from cu import *

RHO = 1.72e-8; T_CU = 35e-6; T_PLATE = 20e-6
GAP = 1.6e-3 / 5           # layer-to-layer barrel length (6 layers, 1.6 mm)
GS = T_CU / RHO            # sheet conductance per square

def pad_mask(R, pad, layer):
    im = R.new(); dr = ImageDraw.Draw(im); R.polyset(dr, pad['layers'][layer]); return np.array(im) > 0

class Net:
    def __init__(self, d, net, bbox, res, layers=LAYERS):
        self.d, self.net, self.R = d, net, Raster(bbox, res)
        self.layers = [L for L in layers]
        self.masks = {L: net_mask(d, self.R, net, L) for L in self.layers}
        H, W = self.R.H, self.R.W
        self.idx = {}; n = 0
        for L in self.layers:
            m = self.masks[L]; ix = -np.ones((H, W), np.int64)
            k = int(m.sum()); ix[m] = np.arange(n, n + k); n += k; self.idx[L] = ix
        ei, ej, eg = [], [], []
        for L in self.layers:
            ix = self.idx[L]
            for a, b in ((ix[:, :-1], ix[:, 1:]), (ix[:-1, :], ix[1:, :])):
                ok = (a >= 0) & (b >= 0)
                ei.append(a[ok]); ej.append(b[ok]); eg.append(np.full(int(ok.sum()), GS))
        self.extra = n
        self.vias = []
        def barrel(x, y, drill, lays, tag):
            g = 1.0 / (RHO * GAP / (math.pi * drill * 1e-3 * T_PLATE))
            nodes = []
            for L in lays:
                if L not in self.idx: continue
                cx, cy = self.R.px(x, y); cx, cy = int(cx), int(cy)
                if 0 <= cy < H and 0 <= cx < W and self.idx[L][cy, cx] >= 0: nodes.append(int(self.idx[L][cy, cx]))
                else: nodes.append(self.extra); self.extra += 1
            for a, b in zip(nodes[:-1], nodes[1:]):
                ei.append(np.array([a])); ej.append(np.array([b])); eg.append(np.array([g]))
            return nodes
        for v in d['vias']:
            if v['net'] != net: continue
            nodes = barrel(v['x'], v['y'], v['drill'], via_layers(v), 'via')
            self.vias.append((v, nodes))
        self.thpads = []
        for p in d['pads']:
            if p['net'] != net or p['drill'] <= 0 or len(p['layers']) < 2: continue
            # plated hole: tie all layers at every cell of the pad (pin + solder)
            cells = []
            for L in self.layers:
                if L in p['layers']:
                    pm = pad_mask(self.R, p, L) & (self.idx[L] >= 0); cells.append(self.idx[L][pm])
            if len(cells) > 1:
                base = cells[0][: max(1, len(cells[0]))]
                for c in cells[1:]:
                    k = min(len(base), len(c))
                    ei.append(base[:k]); ej.append(c[:k]); eg.append(np.full(k, GS * 100))
            self.thpads.append(p)
        self.N = self.extra
        self.ei = np.concatenate(ei); self.ej = np.concatenate(ej); self.eg = np.concatenate(eg)
        self.deg = np.bincount(self.ei, self.eg, self.N) + np.bincount(self.ej, self.eg, self.N)

    def pad_nodes(self, ref, num, layer=None):
        out = []
        for p in self.d['pads']:
            if p['ref'] == ref and p['num'] == str(num) and p['net'] == self.net:
                for L in p['layers']:
                    if L in self.idx and (layer is None or L == layer):
                        pm = pad_mask(self.R, p, L) & (self.idx[L] >= 0); out.append(self.idx[L][pm])
        return np.concatenate(out) if out else np.array([], np.int64)

    def solve(self, fixed, sinks, tol=1e-9, maxit=20000):
        """fixed: node array held at 0 V. sinks: list of (nodes, amps) drawn from the net (current leaves)."""
        N = self.N; b = np.zeros(N)
        for nodes, I in sinks: b[nodes] -= I / len(nodes)
        free = np.ones(N, bool); free[fixed] = False
        b[~free] = 0
        ei, ej, eg, deg = self.ei, self.ej, self.eg, self.deg
        def A(x):
            x = np.where(free, x, 0)
            y = deg * x - np.bincount(ei, eg * x[ej], N) - np.bincount(ej, eg * x[ei], N)
            return np.where(free, y, 0)
        Minv = np.where(free & (deg > 0), 1 / np.maximum(deg, 1e-30), 0)
        x = np.zeros(N); r = b - A(x); z = Minv * r; p = z.copy(); rz = r @ z; b2 = math.sqrt(b @ b)
        for it in range(maxit):
            Ap = A(p); a = rz / (p @ Ap); x += a * p; r -= a * Ap
            if math.sqrt(r @ r) < tol * b2: break
            z = Minv * r; rz2 = r @ z; p = z + rz2 / rz * p; rz = rz2
        self.x = x; self.iters = it
        return x

    def via_currents(self):
        out = []
        for v, nodes in self.vias:
            g = 1.0 / (RHO * GAP / (math.pi * v['drill'] * 1e-3 * T_PLATE))
            I = max([abs(self.x[a] - self.x[b]) * g for a, b in zip(nodes[:-1], nodes[1:])] or [0])
            out.append((I, v))
        return sorted(out, key=lambda t: -t[0])

    def loss(self):
        dv = self.x[self.ei] - self.x[self.ej]; return float((self.eg * dv * dv).sum())

    def vmap(self, L):
        m = np.full(self.idx[L].shape, np.nan); ok = self.idx[L] >= 0; m[ok] = self.x[self.idx[L][ok]]; return m
