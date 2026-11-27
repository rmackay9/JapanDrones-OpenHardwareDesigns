# KiCad python: del_items.py board net via:x,y | trk:x0,y0,x1,y1 ...  (0.02 mm tolerance)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); net = sys.argv[2]; n = 0
near = lambda a, b: abs(a[0] - b[0]) < 0.02 and abs(a[1] - b[1]) < 0.02
for a in sys.argv[3:]:
    kind, xy = a.split(':'); c = list(map(float, xy.split(',')))
    for t in list(B.b.GetTracks()):
        if t.GetNetname() != net: continue
        if kind == 'via' and t.GetClass() == 'PCB_VIA' and near((mm(t.GetPosition().x), mm(t.GetPosition().y)), c): B.b.Delete(t); n += 1
        if kind == 'trk' and t.GetClass() == 'PCB_TRACK':
            s, e = (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))
            if (near(s, c[:2]) and near(e, c[2:])) or (near(e, c[:2]) and near(s, c[2:])): B.b.Delete(t); n += 1
B.save(); print('deleted', n)
