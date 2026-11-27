# KiCad python: move_via.py board net x y nx ny -- move a via and drag the track ends that sat on it
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); net = sys.argv[2]; x, y, nx, ny = map(float, sys.argv[3:7]); n = 0
for t in B.b.GetTracks():
    if t.GetNetname() != net: continue
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        if abs(mm(p.x) - x) < 0.02 and abs(mm(p.y) - y) < 0.02: t.SetPosition(V(nx, ny)); n += 1
    else:
        for g, s in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            e = g()
            if abs(mm(e.x) - x) < 0.02 and abs(mm(e.y) - y) < 0.02: s(V(nx, ny)); n += 1
B.save(); print('moved', n)
