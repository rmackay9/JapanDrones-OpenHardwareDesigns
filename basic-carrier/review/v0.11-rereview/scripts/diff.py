import json,collections,math
a=json.load(open('pre.json')); b=json.load(open('now.json'))
def tk(t): return (t['layer'],t['net'],round(t['x0'],3),round(t['y0'],3),round(t['x1'],3),round(t['y1'],3),round(t['w'],3))
def tkn(t):
    k=tk(t); 
    return k if (k[2],k[3])<=(k[4],k[5]) else (k[0],k[1],k[4],k[5],k[2],k[3],k[6])
A=collections.Counter(tkn(t) for t in a['tracks']); B=collections.Counter(tkn(t) for t in b['tracks'])
add=B-A; rem=A-B
def L(k): return math.hypot(k[4]-k[2],k[5]-k[3])
print('tracks added',sum(add.values()),'removed',sum(rem.values()))
nets=sorted(set(k[1] for k in add)|set(k[1] for k in rem))
def tot(d,net):
    o=collections.defaultdict(float)
    for t in d['tracks']:
        if t['net']==net: o[t['layer'][:3].rstrip('.')]+=t['len']
    return o
print('%-34s %-44s %-44s'%('net','before: len by layer','after'))
for n in nets:
    ta=tot(a,n); tb=tot(b,n)
    f=lambda o:' '.join('%s %.1f'%(k,v) for k,v in sorted(o.items()))+' = %.1f'%sum(o.values())
    print('%-34s %-44s %-44s'%(n,f(ta),f(tb)))
def vk(v): return (v['net'],round(v['x'],3),round(v['y'],3),v['drill'])
VA=collections.Counter(vk(v) for v in a['vias']); VB=collections.Counter(vk(v) for v in b['vias'])
va=VB-VA; vr=VA-VB
print('vias added',sum(va.values()),collections.Counter(k[0] for k in va)); print('vias removed',sum(vr.values()),collections.Counter(k[0] for k in vr))
# footprints moved
FA={f['ref']:f for f in a['fps']}; 
for f in b['fps']:
    g=FA[f['ref']]
    if abs(f['x']-g['x'])>1e-4 or abs(f['y']-g['y'])>1e-4 or f['rot']!=g['rot']: print('moved',f['ref'],f['val'],(g['x'],g['y'],g['rot']),'->',(f['x'],f['y'],f['rot']))
# zones
za={z['id']:z for z in a['zones']}
for z in b['zones']:
    if z['id'] not in za: print('new zone',z['name'],z['net'],z['layers'],z['rule'])
    elif z['outline']!=za[z['id']]['outline'] or z['layers']!=za[z['id']]['layers']: print('zone outline/layers changed',z['name'],z['net'],za[z['id']]['layers'],'->',z['layers'])
zb={z['id'] for z in b['zones']}
for z in a['zones']:
    if z['id'] not in zb: print('zone removed',z['name'],z['net'],z['layers'])
json.dump({'add':[list(k) for k in add.elements()],'rem':[list(k) for k in rem.elements()],'va':[list(k) for k in va.elements()],'vr':[list(k) for k in vr.elements()]},open('diff.json','w'))
