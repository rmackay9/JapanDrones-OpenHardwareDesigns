import sys, numpy as np
from cu import *
tag=sys.argv[1]; b=Board(tag+'.json',res=50); N=Net3D(b,'GND',k=5)
comp=N.components(); root=comp[N.pad_nodes('J18','N','F.Cu')[0]]
bad=comp!=root; u,cnt=np.unique(comp[bad],return_counts=True)
X=np.zeros(N.n);Y=np.zeros(N.n)
for L in LAYERS:
    ids,x,y=N.node_xy(L); X[ids]=x; Y[ids]=y
print(tag,'floating GND total %.1f mm2 in %d pieces; pieces >=0.5 mm2:'%(bad.sum()*N.h**2,len(u)))
for uu,c in sorted(zip(u,cnt),key=lambda t:-t[1]):
    if c*N.h**2<0.5: break
    s=comp==uu; print('   %6.2f mm2 %s x %.1f..%.1f y %.1f..%.1f'%(c*N.h**2,','.join(sorted(set(np.array(LAYERS)[np.unique(N.layer_of[s])]))),X[s].min(),X[s].max(),Y[s].min(),Y[s].max()))
