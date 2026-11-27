# Left VBATT strip: copper width per layer (F.Cu, In2, In3) along y. Usage: python strip.py TAG [TAG...]
import sys, numpy as np
from cu import *
for tag in sys.argv[1:]:
    b=Board(tag+'.json',res=50); M={L:b.mask('VBATT',L) for L in ('F.Cu','In2.Cu','In3.Cu')}
    rows=[]
    for y in np.arange(106.0,125.01,0.1):
        w=[]
        for L in M:
            r,c0=b.rc(100.0,y); _,c1=b.rc(112.0,y); w.append(M[L][r,c0:c1].sum()/b.res)
        rows.append((sum(w),y,w))
    rows.sort()
    for t,y,w in rows[:4]: print(tag,'y=%.1f total %.2f mm  F %.2f In2 %.2f In3 %.2f'%(y,t,*w))
    for yy in (118.8,124.3):
        t,y,w=min(rows,key=lambda r:abs(r[1]-yy)); print(tag,'  at y=%.1f total %.2f  F %.2f In2 %.2f In3 %.2f'%(y,t,*w))
