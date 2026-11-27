import numpy as np
from cu import *
b=Board('now.json',res=100)
for e,net,sh,q,necks in (('ESC2','/VimDrones_mod2/MVDD','RSHUNT4','Q17',[('F.Cu',182.0,118.6),('B.Cu',182.1,118.5)]),
                         ('ESC3','/VimDrones_mod3/MVDD','RSHUNT5','Q23',[('F.Cu',108.2,118.4),('B.Cu',104.8,120.0)]),
                         ('ESC1','/VimDrones_mod1/MVDD','RSHUNT3','Q11',[('F.Cu',181.4,66.7),('B.Cu',179.4,66.8)])):
    N=Net3D(b,net,k=4); src=N.pad_nodes(sh,'1'); dn=np.concatenate([N.pad_nodes(q,n) for n in '56789'])
    v=N.solve(dn,[(src,20.0)],tol=1e-9)
    X=np.zeros(N.n);Y=np.zeros(N.n)
    for L in LAYERS:
        ids,x,y=N.node_xy(L); X[ids]=x; Y[ids]=y
    pw=N.eg*(v[N.ei]-v[N.ej])**2; la=N.layer_of[N.ei]; lb=N.layer_of[N.ej]; ic=N.edge_current(v)
    print('%s (cells %.2f mm, %d nodes): 20 A shunt->%s drop %.1f mV, total loss %.2f W'%(e,N.h,N.n,q,v[src].mean()*1e3,N.power(v)))
    for L,x,y in necks:
        li=LAYERS.index(L)
        for rad in (0.5,1.0,1.5):
            s=(la==li)&(lb==li)&(np.hypot(X[N.ei]-x,Y[N.ei]-y)<rad)
            print('    %s neck (%.1f,%.1f): loss within %.1f mm radius %.0f mW'%(L,x,y,rad,pw[s].sum()*1e3),end='')
            ids=N.idx[L]; m=(ids>=0); nn=ids[m]; sel=nn[np.hypot(X[nn]-x,Y[nn]-y)<rad]
            print(', voltage span %.1f mV'%((v[sel].max()-v[sel].min())*1e3))
        V,J=N.field(L,v); r0=int((y-b.y0)/N.h); c0=int((x-b.x0)/N.h); w=int(0.6/N.h)
        print('    %s peak sheet current near neck %.1f A/mm'%(L,J[r0-w:r0+w,c0-w:c0+w].max()))
    # how much of the 20 A goes through each neck: current crossing a circle of r=0.45 about neck ~ sum |I| of edges crossing / 2
    for L,x,y in necks:
        li=LAYERS.index(L); rin=np.hypot(X[N.ei]-x,Y[N.ei]-y)<0.6; rout=np.hypot(X[N.ej]-x,Y[N.ej]-y)<0.6
        s=(la==li)&(lb==li)&(rin!=rout); print('    %s through-current estimate %.1f A'%(L,np.abs(ic[s]).sum()/2))
