import json, math, numpy as np, cv2, sys
from cu import Board, LAYERS
from collections import deque
d=json.load(open('now.json'))
RES=50; CL=0.1524
def run(ref,num,vdrill,vland,w_stub,win=4.0,own_gap=0.15):
    pad=[p for p in d['pads'] if p['ref']==ref and p['num']==num][0]; net=pad['net']; L0=list(pad['layers'])[0]
    ppoly=np.array(pad['layers'][L0][0]['o'],np.float32)
    old=[v for v in d['vias'] if v['net']==net and cv2.pointPolygonTest(ppoly,(v['x'],v['y']),True)>-v['drill']/2][0]
    ends=[t for t in d['tracks'] if t['net']==net and t['layer']!=L0 and (math.hypot(t['x0']-old['x'],t['y0']-old['y'])<0.01 or math.hypot(t['x1']-old['x'],t['y1']-old['y'])<0.01)]
    x0=pad['x']-win; y0=pad['y']-win; N=int(2*win*RES)
    def P(pts): return np.round((np.asarray(pts,float)-[x0,y0])*RES*16-8).astype(np.int32)
    def obst(L,grow,same_net_pads=False):
        """other-net copper on layer L (tracks, pads, via lands), dilated by grow (mm)"""
        m=np.zeros((N,N),np.uint8)
        for t in d['tracks']:
            if t['layer']==L and t['net']!=net: cv2.fillPoly(m,[P(Board.stadium(t['x0'],t['y0'],t['x1'],t['y1'],t['w']))],1,shift=4)
        for p in d['pads']:
            if L in p['layers'] and (p['net']!=net or (same_net_pads and p is not pad and p['attr']==1)):
                for q in p['layers'][L]: cv2.fillPoly(m,[P(q['o'])],1,shift=4)
        for v in d['vias']:
            if v is old or v['net']==net or L not in v['layers']: continue
            c=P([[v['x'],v['y']]])[0]; cv2.circle(m,(int(c[0]),int(c[1])),int(v['layers'][L]['d']/2*RES*16),1,-1,shift=4)
        k=int(round(grow*RES)); 
        if k>0: m=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*k+1,2*k+1)))
        return m
    # via feasibility
    vf=np.zeros((N,N),np.uint8)
    for L in LAYERS: vf|=obst(L,CL+vland/2)
    # SMD pad openings on outer layers (any net): keep land off them; own pad: hole wall >= own_gap
    for L in ('F.Cu','B.Cu'):
        m=np.zeros((N,N),np.uint8)
        for p in d['pads']:
            if L in p['layers'] and p['attr']==1 and p is not pad:
                for q in p['layers'][L]: cv2.fillPoly(m,[P(q['o'])],1,shift=4)
        k=int(round((vland/2+0.05)*RES)); vf|=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*k+1,2*k+1)))
    m=np.zeros((N,N),np.uint8); cv2.fillPoly(m,[P(ppoly)],1,shift=4); k=int(round((vdrill/2+own_gap)*RES)); vf|=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*k+1,2*k+1)))
    hh=np.zeros((N,N),np.uint8)
    for v in d['vias']:
        if v is old: continue
        c=P([[v['x'],v['y']]])[0]; cv2.circle(hh,(int(c[0]),int(c[1])),int((v['drill']/2+vdrill/2+0.25)*RES*16),1,-1,shift=4)
    vf|=hh
    def bfs(block,seeds):
        dist=np.full((N,N),-1,np.int32); dq=deque()
        for r,c in seeds:
            if 0<=r<N and 0<=c<N: dist[r,c]=0; dq.append((r,c))
        while dq:
            r,c=dq.popleft()
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                rr,cc=r+dr,c+dc
                if 0<=rr<N and 0<=cc<N and dist[rr,cc]<0 and not block[rr,cc]: dist[rr,cc]=dist[r,c]+1; dq.append((rr,cc))
        return dist
    rc=lambda x,y:(int((y-y0)*RES),int((x-x0)*RES))
    # stub on pad layer: seeds = pad interior cells
    pm=np.zeros((N,N),np.uint8); cv2.fillPoly(pm,[P(ppoly)],1,shift=4)
    blk0=obst(L0,CL+w_stub/2); d0=bfs(blk0&~pm if False else (blk0*(1-pm)),list(zip(*np.nonzero(pm))))
    best=None
    tot=np.where((d0>=0)&(vf==0),d0,10**7).astype(np.int64)
    info=''
    for t in ends:
        blk=obst(t['layer'],CL+t['w']/2); dj=bfs(blk,[rc(old['x'],old['y'])])
        tot=np.where(dj>=0,tot+dj,10**7)
    i=np.unravel_index(np.argmin(tot),tot.shape)
    nfeas=int((tot<10**7).sum())
    print('==',ref+'.'+num,net.split('/')[-1],'old via (%.3f,%.3f) %s/%s; other-layer ends: %s'%(old['x'],old['y'],old['drill'],old['layers'][L0]['d'],[(t['layer'],t['w']) for t in ends]))
    print('   via-feasible cells in window: %.2f mm2; reachable by a %s stub (w %.3f): %.2f mm2; also joinable on other layers: %.2f mm2'%((vf==0).sum()/RES**2,L0,w_stub,((d0>=0)&(vf==0)).sum()/RES**2,nfeas/RES**2))
    if nfeas:
        x=x0+(i[1]+.5)/RES; y=y0+(i[0]+.5)/RES
        print('   best: via at (%.3f,%.3f), %s stub ~%.2f mm (manhattan), other-layer jog ~%.2f mm; via is %.2f mm from old via'%(x,y,L0,d0[i]/RES,(tot[i]-d0[i])/RES,math.hypot(x-old['x'],y-old['y'])))
        # what zones does new via pierce
        for z in d['zones']:
            if z['rule']: continue
            for L,f in z['fill'].items():
                for q in f:
                    if cv2.pointPolygonTest(np.array(q['o'],np.float32),(x,y),False)>0 and z['net']!=net: print('     passes through zone fill',z['name'],z['net'].split('/')[-1],L)
    return
for a in (('U12','9',0.2,0.4,0.127),('U3','13',0.2,0.4,0.15),('U3','15',0.2,0.4,0.127),('U20','2',0.25,0.45,0.2),('C42','2',0.25,0.45,0.25),('C43','1',0.25,0.45,0.25)): run(*a)
