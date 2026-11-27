import json, math, numpy as np, cv2, sys
d=json.load(open('now.json'))
CL=0.1524
def segdist(px,py,x0,y0,x1,y1):
    dx=x1-x0; dy=y1-y0; L2=dx*dx+dy*dy
    u=0 if L2==0 else max(0,min(1,((px-x0)*dx+(py-y0)*dy)/L2)); return math.hypot(px-x0-u*dx,py-y0-u*dy)
def seg_seg(a,b):
    # min distance between two segments (sampled)
    n=max(int(math.hypot(a[2]-a[0],a[3]-a[1])/0.02),1); m=1e9
    for i in range(n+1):
        f=i/n; m=min(m,segdist(a[0]+(a[2]-a[0])*f,a[1]+(a[3]-a[1])*f,*b))
    return m
def search(ref,num,vdrill,vland,stubw,R=1.6,own_gap=0.15,ignore_tracks_of_net=True):
    pad=[p for p in d['pads'] if p['ref']==ref and p['num']==num][0]; net=pad['net']; L0=list(pad['layers'])[0]
    ppoly=np.array(pad['layers'][L0][0]['o'],np.float32)
    old=[v for v in d['vias'] if v['net']==net and cv2.pointPolygonTest(ppoly,(v['x'],v['y']),True)>-v['drill']/2][0]
    # track(s) ending at old via on other layers
    ends=[t for t in d['tracks'] if t['net']==net and t['layer']!=L0 and (math.hypot(t['x0']-old['x'],t['y0']-old['y'])<0.01 or math.hypot(t['x1']-old['x'],t['y1']-old['y'])<0.01)]
    box=lambda x,y,m:(pad['x']-R-m<=x<=pad['x']+R+m and pad['y']-R-m<=y<=pad['y']+R+m)
    tr=[t for t in d['tracks'] if t['net']!=net and (box(t['x0'],t['y0'],3) or box(t['x1'],t['y1'],3))]
    vs=[v for v in d['vias'] if v is not old and box(v['x'],v['y'],2)]
    pds=[p for p in d['pads'] if box(p['x'],p['y'],4)]
    print('==',ref,num,net,'pad centre (%.3f,%.3f) on %s; old via (%.3f,%.3f) %s/%s; other-layer tracks ending there: %s'%(pad['x'],pad['y'],L0,old['x'],old['y'],old['drill'],old['layers'][L0]['d'],[(t['layer'],t['w']) for t in ends]))
    def ok_via(x,y,why=False):
        # own pad: hole wall >= own_gap outside pad
        dp=-cv2.pointPolygonTest(ppoly,(x,y),True)
        if dp-vdrill/2<own_gap: return 'own pad'
        for p in pds:
            for L,polys in p['layers'].items():
                for q in polys:
                    dist=-cv2.pointPolygonTest(np.array(q['o'],np.float32),(x,y),True)
                    if p is pad: continue
                    if p['net']!=net and dist-vland/2<CL: return 'pad %s.%s %s'%(p['ref'],p['num'],L)
                    if p['net']==net and p['attr']==1 and dist-vdrill/2<own_gap: return 'same-net pad %s.%s'%(p['ref'],p['num'])
                    if p['attr']==1 and L in('F.Cu','B.Cu') and dist-vland/2<0.0 and p['net']!=net: return 'pad'
        for v in vs:
            dd=math.hypot(x-v['x'],y-v['y'])
            if dd-vdrill/2-v['drill']/2<0.25: return 'hole-hole via %s'%v['net'][-14:]
            if v['net']!=net and dd-vland/2-max(l['d'] for l in v['layers'].values())/2<CL: return 'via land %s'%v['net'][-14:]
        for t in tr:
            if segdist(x,y,t['x0'],t['y0'],t['x1'],t['y1'])-t['w']/2-vland/2<CL: return 'track %s %s'%(t['net'][-14:],t['layer'])
        return None
    def ok_seg(L,x0,y0,x1,y1,w):
        for t in tr:
            if t['layer']!=L: continue
            if seg_seg((x0,y0,x1,y1),(t['x0'],t['y0'],t['x1'],t['y1']))-t['w']/2-w/2<CL: return 'track %s'%t['net'][-14:]
        for v in vs:
            if v['net']==net or L not in v['layers']: continue
            if segdist(v['x'],v['y'],x0,y0,x1,y1)-v['layers'][L]['d']/2-w/2<CL: return 'via %s'%v['net'][-14:]
        for p in pds:
            if p['net']==net or L not in p['layers']: continue
            for q in p['layers'][L]:
                poly=np.array(q['o'],np.float32); n=max(int(math.hypot(x1-x0,y1-y0)/0.02),1)
                for i in range(n+1):
                    f=i/n
                    if -cv2.pointPolygonTest(poly,(x0+(x1-x0)*f,y0+(y1-y0)*f),True)-w/2<CL: return 'pad %s.%s'%(p['ref'],p['num'])
        return None
    cands=[]; reasons={}
    g=0.025; n=int(R/g)
    for i in range(-n,n+1):
        for j in range(-n,n+1):
            x=pad['x']+i*g; y=pad['y']+j*g
            if math.hypot(i*g,j*g)>R: continue
            r=ok_via(x,y)
            if r: reasons[r.split(' ')[0]+' '+(r.split(' ')[1] if ' ' in r else '')]=reasons.get(r.split(' ')[0]+' '+(r.split(' ')[1] if ' ' in r else ''),0)+1; continue
            # stub on pad layer: from nearest point of pad (clamped to pad bbox) to via
            xs=ppoly[:,0]; ys=ppoly[:,1]; sx=min(max(x,xs.min()+stubw/2),xs.max()-stubw/2); sy=min(max(y,ys.min()+stubw/2),ys.max()-stubw/2)
            r1=ok_seg(L0,sx,sy,x,y,stubw)
            if r1: reasons['stub '+r1]=reasons.get('stub '+r1,0)+1; continue
            bad=None
            for t in ends:
                r2=ok_seg(t['layer'],x,y,old['x'],old['y'],t['w'])
                if r2: bad='%s jog %s'%(t['layer'],r2); break
            if bad: reasons[bad]=reasons.get(bad,0)+1; continue
            cands.append((math.hypot(x-sx,y-sy),x,y))
    cands.sort()
    print('   feasible via positions: %d'%len(cands), '; nearest:', ['(%.3f,%.3f) stub %.2f mm'%(x,y,l) for l,x,y in cands[:5]])
    if cands:
        xs=[c[1] for c in cands]; ys=[c[2] for c in cands]; print('   feasible region bbox x %.2f..%.2f y %.2f..%.2f'%(min(xs),max(xs),min(ys),max(ys)))
    print('   rejection reasons (grid points):',sorted(reasons.items(),key=lambda t:-t[1])[:10])
    return cands
for ref,num,dr,ld,w in (('U12','9',0.2,0.4,0.127),('U3','13',0.2,0.4,0.15),('U3','15',0.2,0.4,0.127),('C43','1',0.25,0.45,0.25),('C42','2',0.25,0.45,0.25),('U20','2',0.25,0.45,0.25)):
    search(ref,num,dr,ld,w)
