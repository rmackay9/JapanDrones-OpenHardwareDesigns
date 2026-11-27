# KiCad python: netcomp.py board NET - connected components of a net's copper (fills, tracks, vias, pads)
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
net = b.FindNet(sys.argv[2]); nc = net.GetNetCode()
nodes = []   # (kind, layer, obj/poly, label)
for z in b.Zones():
    if z.GetNetCode() != nc or z.GetIsRuleArea(): continue
    for l in z.GetLayerSet().CuStack():
        fp = z.GetFilledPolysList(l)
        for i in range(fp.OutlineCount()):
            o = fp.Outline(i); bb = o.BBox()
            nodes.append(('fill', l, o, f'{z.GetZoneName()}/{b.GetLayerName(l)} x{mm(bb.GetLeft()):.0f}-{mm(bb.GetRight()):.0f} y{mm(bb.GetTop()):.0f}-{mm(bb.GetBottom()):.0f}'))
pts = []   # connectors: (position, set of layers, label)
for t in b.GetTracks():
    if t.GetNetCode() != nc: continue
    if t.GetClass() == 'PCB_VIA': pts.append(([t.GetPosition()], None, 'via'))
    else: pts.append(([t.GetStart(), t.GetEnd()], {t.GetLayer()}, 'trk'))
for p in b.GetPads():
    if p.GetNetCode() == nc:
        tht = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        pts.append(([p.GetPosition()], None if tht else set(p.GetLayerSet().CuStack()), 'pad ' + p.GetParentFootprint().GetReference()))
parent = list(range(len(nodes)))
def find(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
def union(a, c): parent[find(a)] = find(c)
for ps, layers, lab in pts:
    hit = [i for i, n in enumerate(nodes) if (layers is None or n[1] in layers) and any(n[2].PointInside(q) for q in ps)]
    for i in hit[1:]: union(hit[0], i)
comps = {}
for i, n in enumerate(nodes): comps.setdefault(find(i), []).append(n[3])
for k, v in sorted(comps.items(), key=lambda kv: -len(kv[1])):
    print(len(v), 'pieces:', '; '.join(v[:8]))
