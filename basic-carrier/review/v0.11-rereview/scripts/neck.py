import sys, numpy as np, cv2, pickle
from cu import *
tag=sys.argv[1]
b=Board(tag+'.json',res=100)
ESC={'ESC1':('/VimDrones_mod1/MVDD',(183.4,76.0),[('Q9',183.1,66.8),('Q11',173.8,66.7),('Q13',164.4,66.8)]),
     'ESC2':('/VimDrones_mod2/MVDD',(183.4,114.1),[('Q15',183.1,123.5),('Q17',173.8,123.5),('Q19',164.4,123.5)]),
     'ESC3':('/VimDrones_mod3/MVDD',(106.0,113.6),[('Q21',108.4,123.4),('Q23',117.8,123.4),('Q25',127.2,123.4)]),
     'ESC4':('/VimDrones_mod/MVDD',(106.0,76.1),[('Q3',108.4,66.7),('Q5',117.8,66.7),('Q7',127.2,66.7)])}
def neck(m,p,q):
    """largest w such that p and q stay connected after eroding by w/2 (i.e. narrowest passage on the best path)"""
    d=cv2.distanceTransform(m,cv2.DIST_L2,5)   # px to nearest non-copper
    lo,hi=0.0,d.max()
    rp=b.rc(*p); rq=b.rc(*q)
    # snap p,q to local max of d within 1 mm
    def snap(r):
        w=int(1.0*b.res); sl=d[r[0]-w:r[0]+w,r[1]-w:r[1]+w]; i=np.unravel_index(np.argmax(sl),sl.shape); return (r[0]-w+i[0],r[1]-w+i[1])
    rp=snap(rp); rq=snap(rq)
    if d[rp]==0 or d[rq]==0: return 0,None
    for _ in range(18):
        mid=(lo+hi)/2
        n,lab=cv2.connectedComponents((d>=mid).astype(np.uint8),connectivity=8)
        if lab[rp]!=0 and lab[rp]==lab[rq]: lo=mid
        else: hi=mid
    # locate the neck: pixels with d in [lo-1, lo+1] that disconnect: find where components for threshold hi touch
    n,lab=cv2.connectedComponents((d>=hi).astype(np.uint8),connectivity=8)
    a=(lab==lab[rp]).astype(np.uint8); c=(lab==lab[rq]).astype(np.uint8)
    da=cv2.distanceTransform(1-a,cv2.DIST_L2,5); dc=cv2.distanceTransform(1-c,cv2.DIST_L2,5)
    s=np.where(m>0,da+dc,1e9); i=np.unravel_index(np.argmin(s),s.shape)
    return 2*lo/b.res, b.xy(*i)
for e,(net,ps,qs) in ESC.items():
    for L in ('F.Cu','B.Cu'):
        m=b.mask(net,L)
        # shunt-side reference point: in the capacitor strip
        out=[]
        for q,x,y in qs:
            w,loc=neck(m,ps,(x,y))
            out.append('%s %.2f mm%s'%(q,w,'' if loc is None else ' at (%.1f,%.1f)'%loc))
        print(tag,e,L,'narrowest passage from the capacitor strip to the copper over each high-side FET:',' | '.join(out))
    b._cache.clear()
