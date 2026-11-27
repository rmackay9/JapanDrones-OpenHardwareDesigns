import sys, pickle, numpy as np
from cu import *
tag=sys.argv[1]
b=Board(tag+'.json',res=50); N=Net3D(b,'VBATT',k=5); v=pickle.load(open('vbatt_%s_k5.pkl'%tag,'rb'))['v']
res=b.res
def width_v(L,x,y0,y1):   # copper width (mm) along vertical line x, between y0..y1
    m=b.mask('VBATT',L); r0,c=b.rc(x,y0); r1,_=b.rc(x,y1); return m[r0:r1,c].sum()/res
def width_h(L,y,x0,x1):
    m=b.mask('VBATT',L); r,c0=b.rc(x0,y); _,c1=b.rc(x1,y); return m[r,c0:c1].sum()/res
ic=N.edge_current(v)
# node coords
X=np.zeros(N.n);Y=np.zeros(N.n)
for L in LAYERS:
    ids,x,y=N.node_xy(L); X[ids]=x; Y[ids]=y
la=N.layer_of[N.ei]; lb=N.layer_of[N.ej]; inpl=la==lb
def cur_v(x,y0,y1):   # net current crossing vertical line x (in +x), per layer
    out={}
    s=inpl&(X[N.ei]<x)&(X[N.ej]>x)&(Y[N.ei]>=y0)&(Y[N.ei]<y1)
    for li,L in enumerate(LAYERS):
        out[L]=ic[s&(la==li)].sum()
    return out
def cur_h(y,x0,x1):
    out={}
    s=inpl&(Y[N.ei]<y)&(Y[N.ej]>y)&(X[N.ei]>=x0)&(X[N.ei]<x1)
    for li,L in enumerate(LAYERS):
        out[L]=ic[s&(la==li)].sum()
    return out
print('--- rear band, vertical cuts (y 124.5..140.2): width F/In2/In3 mm, current F/In2/In3 A, mean J A/mm')
for x in list(np.arange(104.05,146,1.0))+list(np.arange(155.05,190,1.0)):
    w=[width_v(L,x,124.5,140.2) for L in ('F.Cu','In2.Cu','In3.Cu')]; c=cur_v(x,124.5,140.2)
    cc=[abs(c[L]) for L in ('F.Cu','In2.Cu','In3.Cu')]
    print('x=%6.2f  w %5.2f %5.2f %5.2f = %5.2f | I %5.1f %5.1f %5.1f = %5.1f | J %4.1f %4.1f %4.1f'%(x,*w,sum(w),*cc,sum(cc),*[ci/max(wi,1e-9) if wi>0.05 else 0 for ci,wi in zip(cc,w)]))
for name,(xa,xb) in {'left':(100.0,110.5),'right':(178.5,191.4)}.items():
    print('--- %s strip, horizontal cuts: width F/In2/In3, current'%name)
    for y in np.arange(84.05,126,1.0):
        w=[width_h(L,y,xa,xb) for L in ('F.Cu','In2.Cu','In3.Cu')]; c=cur_h(y,xa,xb)
        cc=[abs(c[L]) for L in ('F.Cu','In2.Cu','In3.Cu')]
        print('y=%6.2f  w %5.2f %5.2f %5.2f = %5.2f | I %5.1f %5.1f %5.1f = %5.1f | J %4.1f %4.1f %4.1f'%(y,*w,sum(w),*cc,sum(cc),*[ci/max(wi,1e-9) if wi>0.05 else 0 for ci,wi in zip(cc,w)]))
# hot spots: top J cells per layer, clustered
for L in ('F.Cu','In2.Cu','In3.Cu','B.Cu'):
    V,J=N.field(L,v); 
    Jc=J.copy(); print(L,'hot spots (A/mm @ x,y):',end=' ')
    for i in range(10):
        r,c=np.unravel_index(np.argmax(Jc),Jc.shape); 
        if Jc[r,c]<4: break
        print('%.1f@(%.1f,%.1f)'%(Jc[r,c],b.x0+(c+.5)*N.h,b.y0+(r+.5)*N.h),end='  ')
        Jc[max(r-20,0):r+20,max(c-20,0):c+20]=0
    print(); print('   area with J>5: %.1f mm2, >8: %.1f mm2, >12: %.1f mm2'%((J>5).sum()*N.h**2,(J>8).sum()*N.h**2,(J>12).sum()*N.h**2))
# unconnected comps
comp=N.components(); root=comp[N.pad_nodes('J18','P')[0]]
bad=comp!=root; u,cnt=np.unique(comp[bad],return_counts=True)
print('components not tied to XT90+:',len(u))
for uu,c in sorted(zip(u,cnt),key=lambda t:-t[1])[:15]:
    s=comp==uu; print('   %.2f mm2 layer %s around (%.2f,%.2f)'%(c*N.h**2,set(np.array(LAYERS)[np.unique(N.layer_of[s])]),X[s].mean(),Y[s].mean()))
