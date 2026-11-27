import sys, numpy as np, pickle
from cu import *
tag=sys.argv[1]
b=Board(tag+'.json',res=80)   # 0.0125 mm fine raster
ESC={'ESC1':('/VimDrones_mod1/MVDD','RSHUNT3',['Q9','Q11','Q13']),'ESC2':('/VimDrones_mod2/MVDD','RSHUNT4',['Q15','Q17','Q19']),
     'ESC3':('/VimDrones_mod3/MVDD','RSHUNT5',['Q21','Q23','Q25']),'ESC4':('/VimDrones_mod/MVDD','RSHUNT2',['Q3','Q5','Q7'])}
pads={}
for p in b.d['pads']: pads.setdefault((p['ref'],p['num']),[]).append(p)
res={}
for e,(net,sh,qs) in ESC.items():
    print('=====',e,net,tag)
    lab={}
    for L in ('F.Cu','B.Cu','In2.Cu','In3.Cu'):
        m=b.mask(net,L); n,lb,st,ce=islands(m); lab[L]=(lb,st)
        ar=sorted([st[i,cv2.CC_STAT_AREA]/b.res**2 for i in range(1,n+1)],reverse=True)
        print(' %s: %.1f mm2 in %d islands; >=1mm2: %s ; small: %d'%(L,m.sum()/b.res**2,n,['%.1f'%a for a in ar if a>=1],sum(a<1 for a in ar)))
    # which island holds what
    sp=pads[(sh,'1')][0]; r,c=b.rc(sp['x'],sp['y']); lsh=lab['F.Cu'][0][r,c]
    print(' shunt pad F island area %.1f mm2'%(lab['F.Cu'][1][lsh,cv2.CC_STAT_AREA]/b.res**2))
    lq={}
    for q in qs:
        s=set()
        for num in '56789':
            for p in pads[(q,num)]:
                r,c=b.rc(p['x'],p['y']); s.add(int(lab['B.Cu'][0][r,c]))
        lq[q]=s
    print(' drain pads B islands:',lq,' areas',{l:round(lab['B.Cu'][1][l,cv2.CC_STAT_AREA]/b.res**2,1) for s in lq.values() for l in s})
    vs=[v for v in b.d['vias'] if v['net']==net]
    def li(L,v):
        r,c=b.rc(v['x'],v['y']); return int(lab[L][0][r,c])
    allq=set().union(*lq.values())
    direct=[v for v in vs if li('F.Cu',v)==lsh and li('B.Cu',v) in allq]
    print(' vias total %d; joining shunt-side F island to FET-drain B island(s): %d (drill %s)'%(len(vs),len(direct),dict(__import__('collections').Counter(v['drill'] for v in direct))))
    # solver, 0.1 mm cells (8 fine px)
    N=Net3D(b,net,k=8)
    comp=N.components(); src=N.pad_nodes(sh,'1'); root=comp[src[0]]
    print(' network nodes %d; not connected to shunt: %.2f mm2'%(N.n,(comp!=root).sum()*N.h**2))
    out=[]
    for q in qs:
        dn=np.concatenate([N.pad_nodes(q,num) for num in '56789'])
        # hold drain pad at 0 V (FET drain tab is a solid copper slug), inject at shunt pad
        v=N.solve(dn,[(src,20.0)],tol=1e-8)
        vc=N.via_currents(v)
        cur=sorted([(max(abs(a) for _,_,a in segs),via['x'],via['y'],via['drill']) for via,segs in vc if segs],reverse=True)
        # net current F->B through vias
        fb=sum(abs(segs[0][2]) for via,segs in vc if segs)
        print(' 20A shunt->%s: drop %.1f mV (pad mean), loss %.2f W; vias carrying >0.5A: %d, >1A: %d, >2A: %d, >3A: %d; max %.2f A at (%.2f,%.2f) d%.2f; top5 %s'%(q,v[src].mean()*1e3,N.power(v),sum(c[0]>.5 for c in cur),sum(c[0]>1 for c in cur),sum(c[0]>2 for c in cur),sum(c[0]>3 for c in cur),cur[0][0],cur[0][1],cur[0][2],cur[0][3],' '.join('%.1f'%c[0] for c in cur[:6])))
        out.append((q,v[src].mean()*1e3,cur[0][0]))
    res[e]=out
    b._cache.clear()
pickle.dump(res,open('mvdd_%s.pkl'%tag,'wb'))
