import numpy as np, cv2
from cu import *
import sys
b=Board(sys.argv[1]+'.json',res=40)
# other-net copper on every layer (including zone fills) -> distance map; a through via needs clearance on all 6 layers
other=np.zeros((b.H,b.W),np.uint8)
notgnd=lambda n:n!='GND'
for L in LAYERS: other|=b.mask(notgnd,L)
o=b.d['outline'][0]; inside=np.zeros((b.H,b.W),np.uint8); cv2.fillPoly(inside,[b.px(o['o'])],1,shift=SHIFT)
for h in o['h']: cv2.fillPoly(inside,[b.px(h)],0,shift=SHIFT)
# SMD pads of any net on outer layers (don't put vias in pads)
padm=np.zeros((b.H,b.W),np.uint8)
for p in b.d['pads']:
    for L in ('F.Cu','B.Cu'):
        if L in p['layers']:
            for q in p['layers'][L]: b._poly(padm,q['o'],q['h'])
free=((other==0)&(inside==1)&(padm==0)).astype(np.uint8)
dist=cv2.distanceTransform(free,cv2.DIST_L2,5)/b.res
N=Net3D(b,'GND',k=4); comp=N.components(); root=comp[N.pad_nodes('J18','N','F.Cu')[0]]
X=np.zeros(N.n);Y=np.zeros(N.n)
for L in LAYERS:
    ids,x,y=N.node_xy(L); X[ids]=x; Y[ids]=y
bad=comp!=root; u,cnt=np.unique(comp[bad],return_counts=True)
for uu,c in sorted(zip(u,cnt),key=lambda t:-t[1]):
    if c*N.h**2<1: break
    s=np.nonzero(comp==uu)[0]; L=LAYERS[N.layer_of[s[0]]]
    r=((Y[s]-b.y0)*b.res).astype(int); cc=((X[s]-b.x0)*b.res).astype(int)
    dd=dist[r,cc]; i=np.argmax(dd)
    print('%6.1f mm2 %s x %.1f..%.1f y %.1f..%.1f : best GND via spot (%.2f,%.2f), %.2f mm clear of other nets/pads/edge on all layers'%(c*N.h**2,L,X[s].min(),X[s].max(),Y[s].min(),Y[s].max(),X[s][i],Y[s][i],dd[i]))
