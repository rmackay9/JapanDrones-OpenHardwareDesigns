import sys, pickle, numpy as np
from cu import *
tag=sys.argv[1]
b=Board(tag+'.json',res=50); N=Net3D(b,'VBATT',k=5); v=pickle.load(open('vbatt_%s_k5.pkl'%tag,'rb'))['v']
m=b.mask('VBATT','F.Cu'); n,lab,st,ce=islands(m)
vc=N.via_currents(v)
shunts={'ESC1':('RSHUNT3','2'),'ESC2':('RSHUNT4','2'),'ESC3':('RSHUNT5','2'),'ESC4':('RSHUNT2','2')}
pads={(p['ref'],p['num']):p for p in b.d['pads']}
for e,k in shunts.items():
    p=pads[k]; r,c=b.rc(p['x'],p['y']); l=lab[r,c]
    cur=[]
    for via,segs in vc:
        rr,cc=b.rc(via['x'],via['y'])
        if lab[rr,cc]==l:
            f=[a for la,lb,a in segs if la=='F.Cu']; cur.append((abs(f[0]) if f else 0,via['x'],via['y'],via['drill']))
    cur.sort(reverse=True)
    print('%s F.Cu island %.1f mm2: %d vias, sum %.1f A, max %.2f A, >2A: %d ; top: %s'%(e,st[l,cv2.CC_STAT_AREA]/b.res**2,len(cur),sum(c[0] for c in cur),cur[0][0],sum(c[0]>2 for c in cur),' '.join('%.1f'%c[0] for c in cur[:12])))
# F.Cu islands and their via ties
for l in range(1,n+1):
    a=st[l,cv2.CC_STAT_AREA]/b.res**2
    if a<0.4: continue
    nv=sum(1 for via,segs in vc if lab[b.rc(via['x'],via['y'])]==l)
    print('F island %.1f mm2 bbox x %.1f..%.1f y %.1f..%.1f vias %d'%(a,b.x0+st[l,0]/b.res,b.x0+(st[l,0]+st[l,2])/b.res,b.y0+st[l,1]/b.res,b.y0+(st[l,1]+st[l,3])/b.res,nv))
# vias joining F.Cu rear pours to inner planes by region
def reg(x0,y0,x1,y1,name):
    c=[(max(abs(a) for _,_,a in segs),via) for via,segs in vc if x0<=via['x']<=x1 and y0<=via['y']<=y1 and segs]
    if c: print('%s: %d VBATT vias, max %.2f A, sum|F>In| %.1f A'%(name,len(c),max(x[0] for x in c),sum(abs(s[0][2]) for via,s in [(vv,ss) for vv,ss in vc if x0<=vv['x']<=x1 and y0<=vv['y']<=y1 and ss])))
reg(100,124.5,110,140,'rear-left corner'); reg(180,119,191.3,140,'rear-right corner'); reg(100,104.5,110,124.5,'left strip y104.5-124.5'); reg(144,110,157,140,'XT90 area'); reg(110,124.5,144,140,'rear band left'); reg(157,124.5,180,140,'rear band right')
