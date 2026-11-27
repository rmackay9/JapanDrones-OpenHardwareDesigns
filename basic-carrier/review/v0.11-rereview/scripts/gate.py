import json, math, heapq, collections, numpy as np, cv2, re
from cu import *
def analyse(tag):
    b=Board(tag+'.json',res=20); d=b.d
    pads=collections.defaultdict(list)
    for p in d['pads']: pads[p['net']].append(p)
    out={}
    for mod in ('/VimDrones_mod1/','/VimDrones_mod2/','/VimDrones_mod3/','/VimDrones_mod/'):
        for ph in '123':
            vsnet=mod+'FD6288_VS'+ph
            # VS copper on any layer (zones+tracks+pads+vias), distance transform
            vs=np.zeros((b.H,b.W),np.uint8)
            for L in LAYERS: vs|=b.mask(vsnet,L)
            dist=cv2.distanceTransform(1-vs,cv2.DIST_L2,5)/b.res
            for kind in ('HO','LO'):
                net=mod+'FD6288_'+kind+ph
                tr=[t for t in d['tracks'] if t['net']==net]
                # graph
                g=collections.defaultdict(list); key=lambda x,y:(round(x,2),round(y,2))
                for t in tr:
                    a=key(t['x0'],t['y0']); c=key(t['x1'],t['y1']); g[a].append((c,t['len'],t)); g[c].append((a,t['len'],t))
                drv=[p for p in pads[net] if p['ref'].startswith('U')][0]; res=[p for p in pads[net] if p['ref'].startswith('R')]
                def attach(p):
                    L=list(p['layers'])[0]; poly=np.array(p['layers'][L][0]['o'],np.float32)
                    return [n for n in g if cv2.pointPolygonTest(poly,(float(n[0]),float(n[1])),True)>-0.05]
                src=attach(drv); best=None
                for r in res:
                    dst=set(attach(r)); pq=[(0,s,None) for s in src]; seen={}; 
                    while pq:
                        c,n,prev=heapq.heappop(pq)
                        if n in seen: continue
                        seen[n]=(c,prev)
                        if n in dst:
                            if best is None or c<best[0]:
                                path=[]; m=n
                                while m is not None: path.append(m); m=seen[m][1]
                                best=(c,r['ref'],path)
                            break
                        for (o,l,t) in g[n]:
                            if o not in seen: heapq.heappush(pq,(c+l,o,n))
                if best is None: out[(mod,kind+ph)]=None; continue
                length,rref,path=best
                # layer usage along path and separation integral to VS copper
                segs=[]
                for a,c in zip(path[:-1],path[1:]):
                    t=[t for (o,l,t) in g[a] if o==c][0]; segs.append(t)
                lay=collections.Counter(); sep=0; mx=0
                for t in segs:
                    lay[t['layer'][:3].rstrip('.')]+=t['len']
                    n=max(int(t['len']/0.1),1)
                    for i in range(n):
                        f=(i+0.5)/n; x=t['x0']+(t['x1']-t['x0'])*f; y=t['y0']+(t['y1']-t['y0'])*f
                        r_,c_=b.rc(x,y); dd=dist[r_,c_]; sep+=dd*t['len']/n; mx=max(mx,dd)
                nv=sum(1 for a,c in zip(segs[:-1],segs[1:]) if a['layer']!=c['layer'])
                wmin=min(t['w'] for t in segs)
                out[(mod,kind+ph)]=dict(len=length,r=rref,lay=dict(lay),vias=nv,loop=sep,maxsep=mx,wmin=wmin,total=sum(t['len'] for t in tr))
    return out
now=analyse('now'); pre=analyse('pre')
esc={'/VimDrones_mod1/':'ESC1','/VimDrones_mod2/':'ESC2','/VimDrones_mod3/':'ESC3','/VimDrones_mod/':'ESC4'}
print('gate net: driver pin -> gate resistor path. len mm, layer changes, min width, [HO only] area between HO and nearest same-phase VS copper (mm2) and max separation;  pre -> now')
for k in now:
    n=now[k]; p=pre[k]
    if n is None or p is None: print(esc[k[0]],k[1],'path not found',n is None,p is None); continue
    f=lambda r:'%5.1f mm %dv w%.3f %s'%(r['len'],r['vias'],r['wmin'],' '.join('%s %.1f'%(a,b_) for a,b_ in sorted(r['lay'].items())))
    ch='  <-- changed' if abs(n['len']-p['len'])>0.05 or n['lay'].keys()!=p['lay'].keys() else ''
    print('%s %s %-5s  %-44s -> %-44s loop %.0f->%.0f mm2 maxsep %.1f->%.1f%s'%(esc[k[0]],k[1],n['r'],f(p),f(n),p['loop'],n['loop'],p['maxsep'],n['maxsep'],ch))
