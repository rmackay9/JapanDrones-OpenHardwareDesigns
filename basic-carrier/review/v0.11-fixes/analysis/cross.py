import sys, json
from PIL import Image, ImageDraw
import numpy as np
from cu import *
d = load(sys.argv[1])
ZN = {'ESC1': 'MVDD_ESC1', 'ESC2': 'MVDD_ESC2', 'ESC3': 'MVDD_ESC3', 'ESC4': 'MVDD_ESC'}
def inside(pt, poly):
    x, y = pt; c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
for e, zn in ZN.items():
    z = [z for z in d['zones'] if z['name'] == zn][0]; poly = z['outline'][0]['o']; net = z['net']
    print(e, zn)
    for t in d['tracks']:
        if t['net'] == net or t['layer'] not in ('F.Cu', 'B.Cu'): continue
        pts = [(t['x0'] + (t['x1'] - t['x0']) * k / 10, t['y0'] + (t['y1'] - t['y0']) * k / 10) for k in range(11)]
        if any(inside(p, poly) for p in pts):
            print(f"  {t['layer']} {t['net']:32s} ({t['x0']:.2f},{t['y0']:.2f})-({t['x1']:.2f},{t['y1']:.2f}) w{t['w']}")
    for v in d['vias']:
        if v['net'] != net and inside((v['x'], v['y']), poly): print(f"  via {v['net']} ({v['x']:.2f},{v['y']:.2f}) {v['d']}/{v['drill']}")
