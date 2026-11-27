import json, math, heapq, collections, numpy as np, cv2
RS=1.72e-8/35e-6
def run(tag,net='+5.2V'):
    d=json.load(open(tag+'.json'))
    key=lambda x,y:(round(x,2),round(y,2))
    g=collections.defaultdict(list)
    for t in d['tracks']:
        if t['net']!=net: continue
        a=key(t['x0'],t['y0']); c=key(t['x1'],t['y1']); r=RS*t['len']/t['w']
        g[a].append((c,r,t['len'],t['w'],t['layer'])); g[c].append((a,r,t['len'],t['w'],t['layer']))
    nodes=list(g)
    # zone fills: all nodes inside a +5.2V fill polygon are shorted to node 'Z'
    for z in d['zones']:
        if z['net']!=net or z['rule']: continue
        for L,f in z['fill'].items():
            for q in f:
                poly=np.array(q['o'],np.float32)
                for n in nodes:
                    if cv2.pointPolygonTest(poly,(float(n[0]),float(n[1])),False)>=0:
                        g['Z'].append((n,0,0,9,L)); g[n].append(('Z',0,0,9,L))
    # T-junctions: endpoints lying on another segment's interior
    for t in d['tracks']:
        if t['net']!=net: continue
        a=key(t['x0'],t['y0']); c=key(t['x1'],t['y1'])
        for n in nodes:
            if n in (a,c): continue
            dx=t['x1']-t['x0']; dy=t['y1']-t['y0']; L2=dx*dx+dy*dy
            if L2==0: continue
            u=((n[0]-t['x0'])*dx+(n[1]-t['y0'])*dy)/L2
            if 0<u<1 and math.hypot(n[0]-t['x0']-u*dx,n[1]-t['y0']-u*dy)<0.02:
                # same layer or via present
                l1=u*t['len']; l2=(1-u)*t['len']
                g[n].append((a,RS*l1/t['w'],l1,t['w'],t['layer'])); g[a].append((n,RS*l1/t['w'],l1,t['w'],t['layer']))
                g[n].append((c,RS*l2/t['w'],l2,t['w'],t['layer'])); g[c].append((n,RS*l2/t['w'],l2,t['w'],t['layer']))
    dist={'Z':(0,0,9,0)}; pq=[(0,0,'Z',9.0,0)]; seen={}
    while pq:
        r,l,n,wm,nl=heapq.heappop(pq)
        if n in seen: continue
        seen[n]=(r,l,wm)
        for (o,rr,ll,w,L) in g[n]:
            if o not in seen: heapq.heappush(pq,(r+rr,l+ll,o,min(wm,w),0))
    out={}
    for p in d['pads']:
        if p['net']==net and p['ref'].startswith('J'):
            L=list(p['layers'])[0]; poly=np.array(p['layers'][L][0]['o'],np.float32)
            c=[seen[n] for n in seen if n!='Z' and cv2.pointPolygonTest(poly,(float(n[0]),float(n[1])),True)>-0.05]
            out[p['ref']+'.'+p['num']]=min(c) if c else None
    return out
a=run('pre'); b=run('now')
print('+5.2V from the buck output pour to each connector pin: resistance mOhm, length mm, min width; pre -> now')
for k in sorted(b):
    f=lambda v:'   n/a   ' if v is None else '%5.0f mOhm %5.1f mm w%.2f'%(v[0]*1e3,v[1],v[2])
    print('  %-7s %s -> %s %s'%(k,f(a.get(k)),f(b[k]),'<-- changed' if a.get(k) and b[k] and abs(a[k][0]-b[k][0])>1e-3 else ''))
