import sys, numpy as np, re
from cu import *
tag=sys.argv[1]; b=Board(tag+'.json',res=80,pad=1.0)
o=b.d['outline'][0]
inside=np.zeros((b.H,b.W),np.uint8); cv2.fillPoly(inside,[b.px(o['o'])],1,shift=SHIFT)
dist_edge=cv2.distanceTransform(inside,cv2.DIST_L2,5)/b.res            # distance to outer edge
holes=np.ones((b.H,b.W),np.uint8)
hc=[]
for h in o['h']:
    cv2.fillPoly(holes,[b.px(h)],0,shift=SHIFT); xs=[p[0] for p in h]; ys=[p[1] for p in h]; hc.append(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(max(xs)-min(xs))))
dist_hole=cv2.distanceTransform(holes,cv2.DIST_L2,5)/b.res
cats={'VBATT':lambda n:n=='VBATT','MVDD':lambda n:n.endswith('/MVDD'),'PHASE':lambda n:bool(re.search(r'FD6288_VS\d$',n)),
      'OTHER non-GND':lambda n:n not in('GND','VBATT','') and not n.endswith('/MVDD') and not re.search(r'FD6288_VS\d$',n),'GND':lambda n:n=='GND'}
print(tag,'min distance (mm) of non-pad copper [zones+tracks+vias] to outer edge / to any hole wall ; and of pads')
for L in LAYERS:
    for c,f in cats.items():
        m=b.mask(f,L,pads=False); mp=b.mask(f,L,zones=False,tracks=False,vias=False)
        def mn(mm,d):
            if not mm.any(): return None
            v=np.where(mm>0,d,1e9); i=np.unravel_index(np.argmin(v),v.shape); return v[i],b.xy(*i)
        e=mn(m,dist_edge); h=mn(m,dist_hole); pe=mn(mp,dist_edge); ph=mn(mp,dist_hole)
        fmt=lambda t:'  -   ' if t is None else '%.2f@(%.1f,%.1f)'%(t[0],t[1][0],t[1][1])
        print('  %-6s %-14s edge %s  hole %s | pads: edge %s hole %s'%(L,c,fmt(e),fmt(h),fmt(pe),fmt(ph)))
        b._cache.clear()
print('corner holes: nearest non-GND copper to hole centre on outer layers (3.5 mm wanted)')
yy,xx=np.mgrid[0:b.H,0:b.W]
for (cx,cy,dia) in hc:
    if dia<2.5: continue
    r0,c0=b.rc(cx,cy); w=int(6*b.res)
    sl=(slice(max(r0-w,0),r0+w),slice(max(c0-w,0),c0+w))
    dd=np.hypot((xx[sl]+0.5)/b.res+b.x0-cx,(yy[sl]+0.5)/b.res+b.y0-cy)
    for L in LAYERS:
        s='  hole (%.2f,%.2f) %s:'%(cx,cy,L)
        for c in ('VBATT','MVDD','PHASE','OTHER non-GND','GND'):
            f=cats[c]
            m=b.mask(f,L,pads=False)[sl]; mp=b.mask(f,L,zones=False,tracks=False,vias=False)[sl]
            a=dd[m>0].min() if m.any() else 99; p=dd[mp>0].min() if mp.any() else 99
            s+=' %s %.2f (pads %.2f) |'%(c.split()[0],a,p)
            b._cache.clear()
        print(s)
