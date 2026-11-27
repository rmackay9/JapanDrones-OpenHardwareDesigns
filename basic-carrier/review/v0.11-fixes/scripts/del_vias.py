# KiCad python: del_vias.py board net x,y [x,y ...] : delete vias of net at those points (0.02 mm tolerance)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); net = sys.argv[2]; n = 0
for a in sys.argv[3:]:
    x, y = map(float, a.split(','))
    for v in B.vias():
        p = v.GetPosition()
        if v.GetNetname() == net and abs(mm(p.x) - x) < 0.02 and abs(mm(p.y) - y) < 0.02: B.b.Delete(v); n += 1
B.save(); print('deleted', n)
