# near.py board x0 y0 x1 y1 : list tracks/vias/pads in box
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); x0,y0,x1,y1 = map(float, sys.argv[2:6])
inb = lambda x,y: x0<=x<=x1 and y0<=y<=y1
for t in B.b.GetTracks():
    if t.GetClass()=='PCB_VIA':
        p=t.GetPosition()
        if inb(mm(p.x),mm(p.y)): print('VIA %.4f %.4f d%.2f/%.2f %s'%(mm(p.x),mm(p.y),mm(t.GetWidth(pcbnew.F_Cu)),mm(t.GetDrillValue()),t.GetNetname()))
    else:
        s,e=t.GetStart(),t.GetEnd()
        if inb(mm(s.x),mm(s.y)) or inb(mm(e.x),mm(e.y)): print('TRK %s %.4f,%.4f -> %.4f,%.4f w%.2f %s'%(t.GetLayerName(),mm(s.x),mm(s.y),mm(e.x),mm(e.y),mm(t.GetWidth()),t.GetNetname()))
for f in B.b.GetFootprints():
    for p in f.Pads():
        q=p.GetPosition()
        if inb(mm(q.x),mm(q.y)): print('PAD %s.%s %.3f %.3f %.2fx%.2f %s %s'%(f.GetReference(),p.GetNumber(),mm(q.x),mm(q.y),mm(p.GetSizeX()),mm(p.GetSizeY()),','.join(B.b.GetLayerName(l) for l in p.GetLayerSet().CuStack()),p.GetNetname()))
