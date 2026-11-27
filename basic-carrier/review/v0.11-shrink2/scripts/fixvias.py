# KiCad python: fixvias.py board drc.json out  - delete stitching vias named in DRC violations
import pcbnew, sys, json, math
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
d = json.load(open(sys.argv[2]))
def stitch(net):
    return net in ('GND', 'VBATT') or net.endswith('MVDD') or net.endswith('_VS1') or net.endswith('_VS2') or net.endswith('_VS3') \
        or net in ('+5.2V',) and False
vias = {}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        vias[(round(mm(t.GetPosition().x), 2), round(mm(t.GetPosition().y), 2), t.GetNetname())] = t
# how many tracks end on each via (a via with a track on it is a real connection, keep it if possible)
ends = {}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_TRACK':
        for p in (t.GetStart(), t.GetEnd()):
            k = (round(mm(p.x), 2), round(mm(p.y), 2))
            ends[k] = ends.get(k, 0) + 1
kill = set()
import re
for v in d['violations']:
    if v['severity'] != 'error' and v['type'] not in ('hole_to_hole',): continue
    cand = []
    for it in v['items']:
        m = re.match(r'Via \[([^\]]*)\]', it['description'])
        if m:
            key = (round(it['pos']['x'], 2), round(it['pos']['y'], 2), m.group(1))
            if key in vias and stitch(m.group(1)) and ends.get(key[:2], 0) == 0:
                cand.append(key)
    if cand:
        kill.add(cand[0])
for k in kill:
    b.Delete(vias[k])
pcbnew.SaveBoard(sys.argv[3], b)
print(f'deleted {len(kill)} stitching vias')
