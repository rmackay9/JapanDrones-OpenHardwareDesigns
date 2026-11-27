# copper analysis helpers (system python: numpy + PIL)
import json, math, numpy as np
from PIL import Image, ImageDraw

LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']

def load(p): return json.load(open(p))

class Raster:
    def __init__(self, bbox, res):
        self.x0, self.y0, self.x1, self.y1 = bbox
        self.res = res
        self.W = int(math.ceil((self.x1 - self.x0) / res)); self.H = int(math.ceil((self.y1 - self.y0) / res))
    def px(self, x, y): return ((x - self.x0) / self.res, (y - self.y0) / self.res)
    def new(self): return Image.new('L', (self.W, self.H), 0)
    def poly(self, dr, pts, v=1):
        if len(pts) >= 3: dr.polygon([self.px(*p) for p in pts], fill=v)
    def polyset(self, dr, ps, v=1):
        for o in ps:
            self.poly(dr, o['o'], v)
            for h in o['h']: self.poly(dr, h, 0)
    def seg(self, dr, x0, y0, x1, y1, w, v=1):
        a, b = self.px(x0, y0), self.px(x1, y1); r = w / 2 / self.res
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        if L > 1e-9:
            nx, ny = -dy / L * r, dx / L * r
            dr.polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], fill=v)
        for c in (a, b): dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=v)
    def circ(self, dr, x, y, r, v=1):
        c = self.px(x, y); r = r / self.res
        dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=v)

def via_layers(v):
    i0, i1 = LAYERS.index(v['top']), LAYERS.index(v['bot'])
    return LAYERS[i0:i1 + 1]

def net_mask(d, R, net, layer, fills=True, tracks=True, pads=True, vias=True):
    im = R.new(); dr = ImageDraw.Draw(im)
    if fills:
        for z in d['zones']:
            if z['net'] == net and layer in z['fill']: R.polyset(dr, z['fill'][layer])
    if tracks:
        for t in d['tracks']:
            if t['net'] == net and t['layer'] == layer: R.seg(dr, t['x0'], t['y0'], t['x1'], t['y1'], t['w'])
    if pads:
        for p in d['pads']:
            if p['net'] == net and layer in p['layers']: R.polyset(dr, p['layers'][layer])
    if vias:
        for v in d['vias']:
            if v['net'] == net and layer in via_layers(v): R.circ(dr, v['x'], v['y'], v['d'] / 2)
    return np.array(im) > 0

def label(mask):
    """connected components (4-conn) by min-label propagation with pointer jumping"""
    H, W = mask.shape
    lab = np.where(mask, np.arange(H * W).reshape(H, W), H * W).astype(np.int64)
    big = H * W
    while True:
        old = lab
        m = lab.copy()
        m[1:, :] = np.minimum(m[1:, :], lab[:-1, :]); m[:-1, :] = np.minimum(m[:-1, :], lab[1:, :])
        m[:, 1:] = np.minimum(m[:, 1:], lab[:, :-1]); m[:, :-1] = np.minimum(m[:, :-1], lab[:, 1:])
        m = np.where(mask, m, big)
        flat = m.ravel()
        # pointer jumping
        for _ in range(4):
            idx = np.where(flat < big, flat, 0)
            j = flat[idx]
            flat = np.where((flat < big) & (j < flat), j, flat)
        lab = flat.reshape(H, W)
        if np.array_equal(lab, old): break
    u, inv = np.unique(lab, return_inverse=True)
    inv = inv.reshape(H, W)
    if u[-1] == big: inv = np.where(mask, inv + 1, 0); n = len(u) - 1
    else: inv = inv + 1; n = len(u)
    return inv, n
