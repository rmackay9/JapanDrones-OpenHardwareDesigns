import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B=Board(sys.argv[1]); z=B.zone('MVDD_ESC2')[0]; pts=B.outline_pts(z); new=[]
for p in pts:
    if abs(p[0]-181.01)<0.02 and abs(p[1]-119.5)<0.02: new += [(179.2,119.5),(179.2,117.7),(181.01,117.7)]
    else: new.append(p)
B.set_outline(z,new); B.save(); print(B.outline_pts(z))
