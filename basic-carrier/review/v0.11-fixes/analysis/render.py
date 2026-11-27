# render.py dump.json layer x0,y0,x1,y1 out.png [res] [labels]
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from cu import *
d = load(sys.argv[1]); layer = sys.argv[2]
bbox = tuple(map(float, sys.argv[3].split(','))); out = sys.argv[4]
res = float(sys.argv[5]) if len(sys.argv) > 5 else 0.05
R = Raster(bbox, res)
def col(net):
    if net == 'VBATT': return (230, 40, 40)
    if net == 'GND': return (70, 70, 70)
    if net.endswith('/MVDD'): return (230, 200, 0)
    if '/FD6288_VS' in net or 'PH' in net: return (40, 120, 230)
    if net == '+5.2V': return (230, 0, 230)
    if net == '': return (120, 60, 0)
    return (40, 180, 60)
img = Image.new('RGB', (R.W, R.H), (255, 255, 255)); dr = ImageDraw.Draw(img)
def poly(pts, c):
    if len(pts) >= 3: dr.polygon([R.px(*p) for p in pts], fill=c)
for z in sorted(d['zones'], key=lambda z: z['prio']):
    if layer in z['fill']:
        c = col(z['net'])
        for o in z['fill'][layer]:
            poly(o['o'], c)
            for h in o['h']: poly(h, (255, 255, 255))
    if z['rule'] and layer in z['layers']:
        for o in z['outline']: dr.line([R.px(*p) for p in o['o'] + o['o'][:1]], fill=(0, 200, 200), width=2)
for t in d['tracks']:
    if t['layer'] == layer:
        c = tuple(int(v * 0.7) for v in col(t['net']))
        R.seg(dr, t['x0'], t['y0'], t['x1'], t['y1'], t['w'], c)
for p in d['pads']:
    if layer in p['layers']:
        c = tuple(int(v * 0.85) for v in col(p['net']))
        for o in p['layers'][layer]: poly(o['o'], c)
for v in d['vias']:
    if layer in via_layers(v):
        cx, cy = R.px(v['x'], v['y']); r = v['d'] / 2 / res; r2 = v['drill'] / 2 / res
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col(v['net']), outline=(0, 0, 0))
        dr.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 255, 255))
for e in d['edges']:
    if e[0] == 'Rect': dr.rectangle([R.px(e[1], e[2]), R.px(e[3], e[4])], outline=(0, 0, 0), width=2)
    else:
        cx, cy = R.px(e[1], e[2]); r = (e[3] - e[1]) / res
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 0, 0), width=2)
# grid ticks every 1mm, labels every 5
import math
for gx in range(math.ceil(bbox[0]), int(bbox[2]) + 1):
    x, _ = R.px(gx, 0); L = 12 if gx % 5 == 0 else 5
    dr.line([(x, 0), (x, L)], fill=(0, 0, 0))
    if gx % 5 == 0: dr.text((x + 2, 2), str(gx), fill=(0, 0, 0))
for gy in range(math.ceil(bbox[1]), int(bbox[3]) + 1):
    _, y = R.px(0, gy); L = 12 if gy % 5 == 0 else 5
    dr.line([(0, y), (L, y)], fill=(0, 0, 0))
    if gy % 5 == 0: dr.text((14, y - 5), str(gy), fill=(0, 0, 0))
img.save(out); print(out, img.size)
