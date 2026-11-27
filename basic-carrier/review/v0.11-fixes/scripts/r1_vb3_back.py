import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); N='/VimDrones_mod2/FD6288_VB3'; n=0
for t in list(B.b.GetTracks()):
    if t.GetNetname()!=N: continue
    if t.GetClass()=='PCB_VIA':
        p=t.GetPosition()
        if abs(mm(p.x)-181.3825)<0.01 and abs(mm(p.y)-117.905)<0.01:
            t.SetPosition(V(181.3825,116.255)); t.SetWidth(MM(0.45)); t.SetDrill(MM(0.25)); n+=1
    else:
        s,e=t.GetStart(),t.GetEnd()
        ends={(round(mm(s.x),3),round(mm(s.y),3)),(round(mm(e.x),3),round(mm(e.y),3))}
        if ends=={(181.383,116.255),(181.383,117.905)} or ends=={(181.382,116.255),(181.382,117.905)}: B.b.Delete(t); n+=1
B.save(); print('changed',n)
