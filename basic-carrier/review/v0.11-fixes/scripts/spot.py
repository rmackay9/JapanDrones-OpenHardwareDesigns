# spot.py board net d drill x0,y0,x1,y1 step [need_layer...] : candidate via spots clear of other nets (0.2), not touching any pad (+0.1), inside net fill on need layers
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B=Board(sys.argv[1]); net=sys.argv[2]; d=float(sys.argv[3]); dr=float(sys.argv[4])
x0,y0,x1,y1=map(float,sys.argv[5].split(',')); st=float(sys.argv[6]); need=sys.argv[7:]
pads=[(f.GetReference()+'.'+p.GetNumber(),p) for f in B.b.GetFootprints() for p in f.Pads()]
y=y0; out=[]
while y<=y1+1e-9:
    x=x0
    while x<=x1+1e-9:
        P=V(x,y); ok=not B.obstacles(x,y,d/2,net,CU,clr=0.2)
        if ok:
            for n,p in pads:
                q=p.GetPosition()
                if abs(mm(q.x)-x)>4 or abs(mm(q.y)-y)>4: continue
                if any(p.IsOnLayer(lid(B.b,L)) and p.GetEffectivePolygon(lid(B.b,L)).Collide(P,MM(d/2+0.1)) for L in ('F.Cu','B.Cu')): ok=False; break
        if ok and need: ok=all(B.in_fill(x,y,net,L) for L in need)
        if ok: out.append((x,y))
        x+=st
    y+=st
print(len(out)); print(' '.join('(%.2f,%.2f)'%p for p in out[:80]))
