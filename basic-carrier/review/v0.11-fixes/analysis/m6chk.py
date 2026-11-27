import sys, json, math
d = json.load(open(sys.argv[1]))
E = (100.109881, 191.25, 50.0, 140.0); H = [(102.609881,52.5),(188.75,52.5),(102.609881,137.5),(188.75,137.5)]
def pw(n): return n == 'VBATT' or (n.startswith('/VimDrones') and ('/MVDD' in n or 'FD6288_VS' in n))
def ed(x, y): return min(x - E[0], E[1] - x, y - E[2], E[3] - y)
res = {}
def upd(k, v, w):
    if k not in res or v < res[k][0]: res[k] = (v, w)
for z in d['zones']:
    for L, ps in z['fill'].items():
        for o in ps:
            for p in o['o']:
                if pw(z['net']): upd(('edge', L), ed(*p), z['name'])
                if z['net'] != 'GND' and L in ('F.Cu', 'B.Cu'): upd(('hole', L), min(math.hypot(p[0]-hx, p[1]-hy) for hx, hy in H), z['name'] + ' ' + z['net'])
for v in d['vias']:
    for L in ('F.Cu', 'B.Cu'):
        if pw(v['net']): upd(('edge', 'via'), ed(v['x'], v['y']) - v['d'] / 2, v['net'])
        if v['net'] != 'GND': upd(('hole', 'via'), min(math.hypot(v['x']-hx, v['y']-hy) for hx, hy in H) - v['d'] / 2, v['net'])
for t in d['tracks']:
    for x, y in ((t['x0'], t['y0']), (t['x1'], t['y1'])):
        if pw(t['net']): upd(('edge', 'trk'), ed(x, y) - t['w'] / 2, t['net'])
        if t['net'] != 'GND' and t['layer'] in ('F.Cu','B.Cu'): upd(('hole', 'trk'), min(math.hypot(x-hx, y-hy) for hx, hy in H) - t['w']/2, t['net'])
for k in sorted(res): print(k, round(res[k][0], 3), res[k][1])
