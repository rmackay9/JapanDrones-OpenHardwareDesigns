# KiCad python: findvia.py board net x0,y0,x1,y1 [d] [ignore-zones-of-these-nets...] : list clear through-via spots
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); net = sys.argv[2]; x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
d = float(sys.argv[4]) if len(sys.argv) > 4 else 0.45
ok = []
y = y0
while y <= y1:
    x = x0
    while x <= x1:
        why = B.obstacles(x, y, d / 2, net, CU, clr=0.2, edge=0.3)
        why = [w for w in why if not any(w.startswith('zone ' + z) for z in sys.argv[5:])]
        if not why: ok.append((round(x, 2), round(y, 2)))
        x += 0.1
    y += 0.1
print(len(ok), ok[:400])
