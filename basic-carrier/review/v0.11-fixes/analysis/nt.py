# nt.py dump net [x0,y0,x1,y1] : list tracks/vias/pads of net (in box)
import sys
from cu import *
d = load(sys.argv[1]); net = sys.argv[2]
bb = tuple(map(float, sys.argv[3].split(','))) if len(sys.argv) > 3 else (0, 0, 999, 999)
ins = lambda x, y: bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]
for t in d['tracks']:
    if t['net'].endswith(net) and (ins(t['x0'], t['y0']) or ins(t['x1'], t['y1'])):
        print(f"T {t['layer']:7s} ({t['x0']:.2f},{t['y0']:.2f})-({t['x1']:.2f},{t['y1']:.2f}) w{t['w']} {t['id'][:8]}")
for v in d['vias']:
    if v['net'].endswith(net) and ins(v['x'], v['y']): print(f"V ({v['x']:.2f},{v['y']:.2f}) {v['d']}/{v['drill']} {v['top']}-{v['bot']}")
for p in d['pads']:
    if p['net'].endswith(net) and ins(p['x'], p['y']): print(f"P {p['ref']}.{p['num']} ({p['x']:.2f},{p['y']:.2f}) {p['sx']}x{p['sy']} {p['side']}")
