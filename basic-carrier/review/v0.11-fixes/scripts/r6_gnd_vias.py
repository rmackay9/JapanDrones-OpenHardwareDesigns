import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B=Board(sys.argv[1]); add='add' in sys.argv
S=[(121.96,77.25,.6,.3),(114.36,64.65,.45,.25),(186.26,137.15,.6,.3),(109.86,106.85,.6,.3),(105.06,137.05,.6,.3),
   (156.66,88.55,.6,.3),(154.26,82.75,.45,.25),(159.86,123.15,.6,.3),(159.26,105.25,.45,.25),(119.56,117.35,.45,.25)]
pads=[(f.GetReference()+'.'+p.GetNumber(),p) for f in B.b.GetFootprints() for p in f.Pads()]
for x,y,d,dr in S:
    why=B.obstacles(x,y,d/2,'GND',CU,clr=0.2,zones=False)
    P=V(x,y)
    for n,p in pads:
        q=p.GetPosition()
        if abs(mm(q.x)-x)<4 and abs(mm(q.y)-y)<4 and any(p.IsOnLayer(lid(B.b,L)) and p.GetEffectivePolygon(lid(B.b,L)).Collide(P,MM(d/2+0.1)) for L in ('F.Cu','B.Cu')): why.append('pad '+n)
    print(x,y,d,why)
    if add and not why: B.add_via(x,y,'GND',d,dr)
if add: B.save()
