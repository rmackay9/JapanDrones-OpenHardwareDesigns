# KiCad python: add_tracks.py board net layer width x0,y0,x1,y1 [...]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); net, L, w = sys.argv[2], sys.argv[3], float(sys.argv[4])
for a in sys.argv[5:]:
    x0, y0, x1, y1 = map(float, a.split(',')); B.add_track(x0, y0, x1, y1, w, L, net)
B.save(); print('added', len(sys.argv) - 5)
