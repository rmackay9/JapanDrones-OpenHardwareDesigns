import sys, numpy as np, time, pickle
from cu import *
tag=sys.argv[1]; k=int(sys.argv[2]) if len(sys.argv)>2 else 10
b=Board(tag+'.json',res=50)
for L in LAYERS:
    m=b.mask('GND',L); n,lab,st,ce=islands(m)
    ar=sorted([st[i,cv2.CC_STAT_AREA]/b.res**2 for i in range(1,n+1)],reverse=True)
    print(L,'GND %.0f mm2, islands %d, largest %s'%(m.sum()/b.res**2,n,['%.1f'%a for a in ar[:8]]))
t=time.time(); N=Net3D(b,'GND',k=k); print('nodes',N.n,'vias',len(N.vias),'%.0fs'%(time.time()-t))
comp=N.components(); src=N.pad_nodes('J18','N','B.Cu'); src=np.concatenate([N.pad_nodes('J18','N',L) for L in LAYERS]); root=comp[N.pad_nodes('J18','N','F.Cu')[0]]
bad=comp!=root; print('GND nodes not tied to XT90-: %.1f mm2'%(bad.sum()*N.h**2))
u,cnt=np.unique(comp[bad],return_counts=True)
X=np.zeros(N.n);Y=np.zeros(N.n)
for L in LAYERS:
    ids,x,y=N.node_xy(L); X[ids]=x; Y[ids]=y
for uu,c in sorted(zip(u,cnt),key=lambda t:-t[1])[:12]:
    s=comp==uu; print('   floating %.2f mm2 layer %s around (%.2f,%.2f)'%(c*N.h**2,set(np.array(LAYERS)[np.unique(N.layer_of[s])]),X[s].mean(),Y[s].mean()))
LS={'ESC1':['Q10','Q12','Q14'],'ESC2':['Q16','Q18','Q20'],'ESC3':['Q22','Q24','Q26'],'ESC4':['Q4','Q6','Q8']}
inj=[];sn={}
for e,qs in LS.items():
    q=qs[1]; ids=np.concatenate([N.pad_nodes(q,n_) for n_ in '123']); ids=ids[comp[ids]==root]; sn[e]=ids; inj.append((ids,20.0))
t=time.time(); v=N.solve(src,inj,tol=1e-7); print('solve %.0fs %d it'%(time.time()-t,N.iters))
for e,ids in sn.items(): print('%s GND rise at low-side source (mid FET): %.1f mV'%(e,v[ids].mean()*1e3))
print('GND loss %.2f W'%N.power(v))
pw=N.eg*(v[N.ei]-v[N.ej])**2; la=N.layer_of[N.ei]; lb=N.layer_of[N.ej]
for li,L in enumerate(LAYERS): print('  loss in',L,'%.2f W'%pw[(la==li)&(lb==li)].sum())
vc=N.via_currents(v); cur=sorted([(max(abs(a) for _,_,a in segs),via['x'],via['y'],via['drill']) for via,segs in vc if segs],reverse=True)
print('GND via max currents:',' '.join('%.1f@(%.1f,%.1f)d%.2f'%c for c in cur[:10]))
for L in LAYERS:
    V,J=N.field(L,v); Jc=J.copy(); print(L,'hot:',end=' ')
    for i in range(6):
        r,c=np.unravel_index(np.argmax(Jc),Jc.shape)
        if Jc[r,c]<3: break
        print('%.1f@(%.1f,%.1f)'%(Jc[r,c],b.x0+(c+.5)*N.h,b.y0+(r+.5)*N.h),end='  '); Jc[max(r-15,0):r+15,max(c-15,0):c+15]=0
    print()
pickle.dump(v,open('gnd_%s.pkl'%tag,'wb'))
