# KiCad python: tidy.py board drc.json out - delete dangling vias/tracks reported by DRC
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
d = json.load(open(sys.argv[2]))
ids = set()
for v in d['violations']:
    if v['type'] in ('via_dangling', 'track_dangling'):
        for it in v['items']: ids.add(it.get('uuid'))
n = 0
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in ids:
        b.Delete(t); n += 1
pcbnew.SaveBoard(sys.argv[3], b)
print('deleted', n, 'dangling items')
