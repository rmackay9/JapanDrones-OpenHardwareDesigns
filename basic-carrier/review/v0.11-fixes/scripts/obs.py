# obs.py board net layers r x0,y0 x1,y1 ...  : sample polyline, print obstacles
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B=Board(sys.argv[1]); net=sys.argv[2]; L=sys.argv[3].split(','); r=float(sys.argv[4])
pts=[tuple(map(float,a.split(','))) for a in sys.argv[5:]]
seen=set()
for (ax,ay),(bx,by) in zip(pts,pts[1:]):
    n=max(2,int(math.hypot(bx-ax,by-ay)/0.05))
    for i in range(n+1):
        x=ax+(bx-ax)*i/n; y=ay+(by-ay)*i/n
        for w in B.obstacles(x,y,r,net,L,clr=0.2):
            if w not in seen: seen.add(w); print('%.2f,%.2f'%(x,y),w)
print('done', len(seen))
