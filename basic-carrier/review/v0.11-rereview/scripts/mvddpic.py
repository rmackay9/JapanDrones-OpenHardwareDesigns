import sys, numpy as np
from cu import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
b=Board('now.json',res=50)
ESC={'ESC1':('/VimDrones_mod1/MVDD','RSHUNT3','Q13',(160,64,190,84)),'ESC2':('/VimDrones_mod2/MVDD','RSHUNT4','Q19',(160,106,188,127)),
     'ESC3':('/VimDrones_mod3/MVDD','RSHUNT5','Q25',(100,105,131,127)),'ESC4':('/VimDrones_mod/MVDD','RSHUNT2','Q7',(102,64,131,84))}
fig,axs=plt.subplots(4,2,figsize=(22,30))
for row,(e,(net,sh,q,box)) in enumerate(ESC.items()):
    N=Net3D(b,net,k=5); src=N.pad_nodes(sh,'1'); dn=np.concatenate([N.pad_nodes(q,n) for n in '56789'])
    v=N.solve(dn,[(src,20.0)],tol=1e-8)
    ext=[b.x0,b.x0+N.Wc*N.h,b.y0+N.Hc*N.h,b.y0]
    for col,L in enumerate(('F.Cu','B.Cu')):
        V,J=N.field(L,v); ax=axs[row,col]
        im=ax.imshow(np.ma.masked_where(np.isnan(V),J),extent=ext,cmap='turbo',vmin=0,vmax=6,interpolation='nearest'); ax.set_xlim(box[0],box[2]); ax.set_ylim(box[3],box[1]); ax.set_facecolor('#dddddd')
        ax.set_title('%s MVDD %s, 20 A shunt -> %s, A/mm'%(e,L,q)); plt.colorbar(im,ax=ax,fraction=0.03)
        for via,segs in N.via_currents(v):
            if segs:
                a=max(abs(s[2]) for s in segs); ax.plot(via['x'],via['y'],'o',ms=2+2.5*a,mfc='none',mec='w' if a<2 else 'k',mew=1)
        Jc=J.copy(); s=''
        for i in range(4):
            r,c=np.unravel_index(np.argmax(Jc),Jc.shape); s+='%.1f@(%.1f,%.1f) '%(Jc[r,c],b.x0+(c+.5)*N.h,b.y0+(r+.5)*N.h); Jc[max(r-15,0):r+15,max(c-15,0):c+15]=0
        print(e,L,'hot:',s,' area J>4: %.1f mm2'%((J>4).sum()*N.h**2))
    # cross-section F+B between shunt and FET row: min total width across cuts
plt.tight_layout(); plt.savefig('mvdd_now.png',dpi=70)
