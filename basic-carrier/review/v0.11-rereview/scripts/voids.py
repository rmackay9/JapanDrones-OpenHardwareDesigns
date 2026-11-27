import sys, numpy as np, cv2
from cu import *
def voids(tag,L):
    b=Board(tag+'.json',res=40); m=b.mask('GND',L)
    o=b.d['outline'][0]; inside=np.zeros((b.H,b.W),np.uint8); cv2.fillPoly(inside,[b.px(o['o'])],1,shift=SHIFT)
    for h in o['h']: cv2.fillPoly(inside,[b.px(h)],0,shift=SHIFT)
    v=(inside&(1-m)).astype(np.uint8)
    n,lab,st,ce=cv2.connectedComponentsWithStats(v,connectivity=8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]; 
        if x<=int(0.6*b.res) or y<=int(0.6*b.res) or x+w>=b.W-int(0.6*b.res) or y+h>=b.H-int(0.6*b.res): continue   # edge margin ring
        out.append((max(w,h)/b.res,a/b.res**2,b.x0+x/b.res,b.y0+y/b.res,b.x0+(x+w)/b.res,b.y0+(y+h)/b.res))
    return sorted(out,reverse=True)
for L in ('In1.Cu','In4.Cu'):
    a=voids('now',L); p=voids('pre',L)
    print(L,'voids in GND plane: now %d (>=3 mm long: %d, total area %.0f mm2) ; pre %d (>=3 mm: %d, area %.0f)'%(len(a),sum(v[0]>=3 for v in a),sum(v[1] for v in a),len(p),sum(v[0]>=3 for v in p),sum(v[1] for v in p)))
    pk={(round(v[2],1),round(v[3],1),round(v[4],1),round(v[5],1)) for v in p}
    for v in a[:40]:
        if v[0]<3: break
        new='' if (round(v[2],1),round(v[3],1),round(v[4],1),round(v[5],1)) in pk else 'NEW/changed'
        print('   %.1f mm long, %.1f mm2, x %.1f..%.1f y %.1f..%.1f %s'%(v[0],v[1],v[2],v[4],v[3],v[5],new))
