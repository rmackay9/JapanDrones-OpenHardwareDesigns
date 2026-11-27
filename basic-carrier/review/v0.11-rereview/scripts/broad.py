import sys, json, numpy as np, cv2, collections, re
from cu import *
def run(tag):
    b=Board(tag+'.json',res=20)
    res={}
    def netmasks(L):
        out={}
        for t in b.d['tracks']:
            if t['layer']!=L or t['net'] in('GND',): continue
            m=out.setdefault(t['net'],np.zeros((b.H,b.W),np.uint8))
            if 'poly' in t:
                for p in t['poly']: b._poly(m,p['o'],p['h'])
            else: b._poly(m,Board.stadium(t['x0'],t['y0'],t['x1'],t['y1'],t['w']))
        return out
    A=netmasks('In2.Cu'); B=netmasks('In3.Cu')
    pairs={}
    for na,ma in A.items():
        ys,xs=np.nonzero(ma)
        if len(ys)==0: continue
        sl=(slice(ys.min(),ys.max()+1),slice(xs.min(),xs.max()+1))
        for nb,mb in B.items():
            if na==nb: continue
            ov=(ma[sl]&mb[sl]).sum()/b.res**2
            if ov>0.02: pairs[(na,nb)]=ov
    # what plane is opposite each In2 track (on In3) and each In3 track (on In2): fraction over GND / VBATT / other / nothing
    planes={}
    for L,other,M in (('In2.Cu','In3.Cu',A),('In3.Cu','In2.Cu',B)):
        g=b.mask('GND',other); vb=b.mask('VBATT',other)
        for n,m in M.items():
            tot=m.sum()
            planes[(n,L)]=(tot/b.res**2,(m&g).sum()/tot,(m&vb).sum()/tot)
    return pairs,planes
pn,pln=run('now'); pp,plp=run('pre')
sh=lambda n:n.replace('/VimDrones_','').replace('/Connectors/','')
print('broadside overlap In2 (first) over In3 (second), mm2 (0.1 mm prepreg => ~0.4 pF per mm2). now [pre]')
for k,v in sorted(pn.items(),key=lambda t:-t[1]):
    if v>=0.05: print('  %-34s x %-34s %.2f [%.2f]'%(sh(k[0]),sh(k[1]),v,pp.get(k,0)))
print('pairs in pre that vanished:',[(sh(a),sh(b_),round(v,2)) for (a,b_),v in pp.items() if (a,b_) not in pn and v>0.1])
print('tracks on In2/In3: area mm2, fraction facing GND / VBATT on the other inner layer; now [pre]')
for k,v in sorted(pln.items()):
    o=plp.get(k)
    if o is None or abs(o[1]-v[1])>0.1 or abs(o[2]-v[2])>0.1 or abs(o[0]-v[0])>0.5:
        print('  %-36s %s  %.1f mm2 gnd %.0f%% vbatt %.0f%%   [%s]'%(sh(k[0]),k[1][:3],v[0],v[1]*100,v[2]*100,'-' if o is None else '%.1f mm2 gnd %.0f%% vbatt %.0f%%'%(o[0],o[1]*100,o[2]*100)))
