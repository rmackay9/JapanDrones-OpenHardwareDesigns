# KiCad python: nudge.py board REF dx dy [REF dx dy ...] -- move footprints (placement only) and drag the
# ends of tracks that sat on their pad centres by the same amount
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kutil import *
B = Board(sys.argv[1]); a = sys.argv[2:]
for i in range(0, len(a), 3):
    ref, dx, dy = a[i], float(a[i + 1]), float(a[i + 2])
    f = B.F[ref]
    centres = [(mm(p.GetPosition().x), mm(p.GetPosition().y), p.GetNetname(), p) for p in f.Pads()]
    n = 0
    for t in B.tracks():
        for getter, setter in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            e = getter()
            for x, y, net, p in centres:
                if t.GetNetname() == net and abs(mm(e.x) - x) < 0.01 and abs(mm(e.y) - y) < 0.01 and p.IsOnLayer(t.GetLayer()):
                    setter(V(x + dx, y + dy)); n += 1
    f.Move(V(dx, dy))
    print(f'{ref}: moved ({dx:+.2f},{dy:+.2f}) mm, {n} track ends dragged')
B.save()
