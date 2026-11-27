import sys, json, math, numpy as np, cv2
tag=sys.argv[1]; d=json.load(open(tag+'.json'))
fp={f['ref']:f for f in d['fps']}
def pip(x,y,poly):
    return cv2.pointPolygonTest(np.array(poly,np.float32),(float(x),float(y)),True)   # +inside distance
out=[]
for v in d['vias']:
    for p in d['pads']:
        if p['attr']!=1: continue   # SMD pads only
        if abs(p['x']-v['x'])>max(p['sx'],p['sy'])/2+1 or abs(p['y']-v['y'])>max(p['sx'],p['sy'])/2+1: continue
        for L,polys in p['layers'].items():
            if L not in v['layers']: continue
            for q in polys:
                dist=pip(v['x'],v['y'],q['o'])     # >0 centre inside pad
                rpad=v['layers'][L]['d']/2; rdr=v['drill']/2
                if dist>-rpad:   # via land overlaps pad copper
                    kind='HOLE IN PAD (centre inside)' if dist>=0 else ('hole edge overlaps pad' if dist>-rdr else 'via land overlaps pad')
                    out.append((kind,p['ref'],p['num'],p['net'],fp[p['ref']]['val'],fp[p['ref']]['fpid'],L,round(v['x'],3),round(v['y'],3),v['drill'],v['layers'][L]['d'],round(dist,3),round(min(p['sx'],p['sy']),2),round(max(p['sx'],p['sy']),2),v['net']==p['net']))
out.sort(key=lambda r:(r[0],r[1],r[2]))
import collections
print(tag,collections.Counter(r[0] for r in out))
for r in out:
    if r[0]!='via land overlaps pad': print('  %-28s %s.%s %-28s %-14s %-34s %s via(%.3f,%.3f) drill %.2f land %.2f centre-in %.3f pad %sx%s same-net %s'%r)
print(' land-only overlaps:')
for r in out:
    if r[0]=='via land overlaps pad': print('    %s.%s %s %s via(%.2f,%.2f) d%.2f/%.2f overlap %.2f pad %sx%s'%(r[1],r[2],r[3][-22:],r[4],r[7],r[8],r[9],r[10],r[10]/2+r[11],r[12],r[13]))
