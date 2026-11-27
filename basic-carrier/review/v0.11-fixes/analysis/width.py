# width.py dump net x0,x1 y0,y1 : min/mean width of net copper (connected run touching the edge side) per layer
import sys, numpy as np
from cu import *
d = load(sys.argv[1]); net = sys.argv[2]; x0, x1 = map(float, sys.argv[3].split(',')); y0, y1 = map(float, sys.argv[4].split(','))
R = Raster((x0, y0, x1, y1), 0.02)
for L in sys.argv[5].split(','):
    m = net_mask(d, R, net, L, vias=False)
    w = m.sum(1) * 0.02
    i = int(w.argmin())
    print(f'{L}: min {w.min():.2f} mm at y {y0 + i * 0.02:.2f}, mean {w.mean():.2f}')
