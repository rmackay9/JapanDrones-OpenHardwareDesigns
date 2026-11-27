import json, math, collections
d=json.load(open('now.json')); df=json.load(open('diff.json'))
newv={(k[1],k[2]) for k in df['va']}
isnew=lambda v:(round(v['x'],3),round(v['y'],3)) in newv
V=d['vias']
print('vias',len(V),'new',sum(isnew(v) for v in V), 'sizes',collections.Counter((v['drill'],v['layers']['F.Cu']['d']) for v in V))
print('new via sizes',collections.Counter((v['drill'],v['layers']['F.Cu']['d']) for v in V if isnew(v)))
# hole to hole
rows=[]
for i,a in enumerate(V):
    for b in V[i+1:]:
        dx=a['x']-b['x']; dy=a['y']-b['y']
        if abs(dx)>1.2 or abs(dy)>1.2: continue
        w=math.hypot(dx,dy)-a['drill']/2-b['drill']/2
        if w<0.25: rows.append((w,a,b))
rows.sort(key=lambda r:r[0])
print('hole wall-to-wall < 0.25 mm: %d pairs (%d involve a new via)'%(len(rows),sum(isnew(a) or isnew(b) for w,a,b in rows)))
for w,a,b in rows: print('  %.3f mm  %s (%.3f,%.3f) d%.2f %s | %s (%.3f,%.3f) d%.2f %s'%(w,a['net'][-18:],a['x'],a['y'],a['drill'],'NEW' if isnew(a) else '',b['net'][-18:],b['x'],b['y'],b['drill'],'NEW' if isnew(b) else ''))
# via hole to PTH/NPTH pad holes
for v in V:
    for p in d['pads']:
        if p['drill']>0:
            w=math.hypot(v['x']-p['x'],v['y']-p['y'])-v['drill']/2-p['drill']/2
            if w<0.3: print('  via-hole to pad-hole %.3f'%w,v['net'],v['x'],v['y'],p['ref'],p['num'])
# via hole wall to other-net tracks (any layer the via passes = all)
def segdist(px,py,t):
    x0,y0,x1,y1=t['x0'],t['y0'],t['x1'],t['y1']; dx=x1-x0; dy=y1-y0; L2=dx*dx+dy*dy
    u=0 if L2==0 else max(0,min(1,((px-x0)*dx+(py-y0)*dy)/L2)); return math.hypot(px-x0-u*dx,py-y0-u*dy)
rows=[]
for v in V:
    for t in d['tracks']:
        if t['net']==v['net']: continue
        if min(t['x0'],t['x1'])-1>v['x'] or max(t['x0'],t['x1'])+1<v['x'] or min(t['y0'],t['y1'])-1>v['y'] or max(t['y0'],t['y1'])+1<v['y']: continue
        w=segdist(v['x'],v['y'],t)-t['w']/2-v['drill']/2
        if w<0.25: rows.append((w,v,t))
rows.sort(key=lambda r:r[0])
print('via hole wall to other-net track copper < 0.25 mm: %d (new via involved: %d); <0.2: %d (new %d)'%(len(rows),sum(isnew(v) for w,v,t in rows),sum(w<0.2 for w,v,t in rows),sum(w<0.2 and isnew(v) for w,v,t in rows)))
for w,v,t in rows[:25]: print('  %.3f  via %s (%.3f,%.3f) d%.2f %s  track %s %s'%(w,v['net'][-20:],v['x'],v['y'],v['drill'],'NEW' if isnew(v) else '',t['net'][-20:],t['layer']))
# track-track same layer min spacing stats for added tracks
addk={tuple(k) for k in df['add']}
def tk(t):
    k=(t['layer'],t['net'],round(t['x0'],3),round(t['y0'],3),round(t['x1'],3),round(t['y1'],3),round(t['w'],3)); k2=(k[0],k[1],k[4],k[5],k[2],k[3],k[6]); return k in addk or k2 in addk
newt=[t for t in d['tracks'] if tk(t)]
print('new tracks',len(newt),'widths',collections.Counter(round(t['w'],3) for t in newt))
# via annular ring check
print('annular rings',collections.Counter(round((v['layers']['F.Cu']['d']-v['drill'])/2,3) for v in V))
# via to edge
ox=[p[0] for p in d['outline'][0]['o']]; oy=[p[1] for p in d['outline'][0]['o']]
x0,x1,y0,y1=min(ox),max(ox),min(oy),max(oy)
e=sorted((min(v['x']-x0,x1-v['x'],v['y']-y0,y1-v['y'])-v['drill']/2,v['net'],v['x'],v['y'],isnew(v)) for v in V)[:8]
print('via hole wall to board edge, smallest:',[(round(a,2),n[-12:],round(x,2),round(y,2),nw) for a,n,x,y,nw in e])
