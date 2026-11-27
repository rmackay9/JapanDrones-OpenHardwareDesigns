# KiCad python helpers for the v0.11 review fixes (run with KiCad 10's python.exe)
import math, pcbnew

mm = pcbnew.ToMM
MM = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))
CU = ['F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']
EDGE = (100.11, 191.25, 50.0, 140.0)
CORNER_HOLES = [(102.61, 52.5), (188.75, 52.5), (102.61, 137.5), (188.75, 137.5)]
HOLES = [(x, y, 1.5) for x, y in CORNER_HOLES] + [(130, 80, 0.9), (160, 80, 0.9), (130, 110, 0.9), (160, 110, 0.9)]

def lid(b, name): return b.GetLayerID(name)

def seg_dist(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)

class Board:
    def __init__(self, path):
        self.path = path
        self.b = pcbnew.LoadBoard(path)
        self.F = {f.GetReference(): f for f in self.b.GetFootprints()}
        self.log = []

    def net(self, name): return self.b.FindNet(name)

    def tracks(self): return [t for t in self.b.GetTracks() if t.GetClass() == 'PCB_TRACK']
    def vias(self): return [t for t in self.b.GetTracks() if t.GetClass() == 'PCB_VIA']

    def obstacles(self, x, y, r, net, layers, clr=0.2, hole_wall=0.25, edge=0.5, zones=True, skip=(), gnd_zone_ok=True):
        """list of reasons why copper disc (x,y,r) of `net` on `layers` (plus drilled hole if hole_r) is not clear"""
        why = []
        if not (EDGE[0] + edge + r <= x <= EDGE[1] - edge - r and EDGE[2] + edge + r <= y <= EDGE[3] - edge - r): why.append('edge')
        for hx, hy, hr in HOLES:
            if math.hypot(hx - x, hy - y) < hr + r + 0.3: why.append('hole')
        P = V(x, y)
        for t in self.b.GetTracks():
            if t in skip: continue
            if t.GetClass() == 'PCB_VIA':
                q = t.GetPosition(); dd = math.hypot(mm(q.x) - x, mm(q.y) - y)
                if dd > 3: continue
                if t.GetNetname() == net:
                    if dd < r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + hole_wall - 0.15: why.append(f'via-same {mm(q.x):.2f},{mm(q.y):.2f}')
                elif dd < r + mm(t.GetWidth(pcbnew.F_Cu)) / 2 + max(clr, hole_wall - 0.15): why.append(f'via {t.GetNetname()} {mm(q.x):.2f},{mm(q.y):.2f}')
            elif t.GetClass() == 'PCB_TRACK':
                if t.GetNetname() == net or t.GetLayerName() not in layers: continue
                s, e = t.GetStart(), t.GetEnd()
                if seg_dist(mm(s.x), mm(s.y), mm(e.x), mm(e.y), x, y) < r + mm(t.GetWidth()) / 2 + clr: why.append(f'track {t.GetNetname()} {t.GetLayerName()}')
        for f in self.b.GetFootprints():
            fb = f.GetBoundingBox()
            if not (mm(fb.GetLeft()) - 2 < x < mm(fb.GetRight()) + 2 and mm(fb.GetTop()) - 2 < y < mm(fb.GetBottom()) + 2): continue
            for p in f.Pads():
                for L in layers:
                    if not p.IsOnLayer(lid(self.b, L)): continue
                    same = p.GetNetname() == net
                    if same: continue          # same-net pad: caller decides (via-in-pad check separately)
                    if p.GetEffectivePolygon(lid(self.b, L)).Collide(P, MM(r + clr)): why.append(f'pad {f.GetReference()}.{p.GetNumber()} {L}'); break
                if p.GetDrillSizeX() > 0 and p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                    q = p.GetPosition()
                    if math.hypot(mm(q.x) - x, mm(q.y) - y) < r + mm(p.GetDrillSizeX()) / 2 + 0.3: why.append('pth')
        if zones:
            for z in self.b.Zones():
                if z.GetIsRuleArea() or z.GetNetname() == net or (gnd_zone_ok and z.GetNetname() == 'GND'): continue
                for L in layers:
                    if z.IsOnLayer(lid(self.b, L)) and z.GetFilledPolysList(lid(self.b, L)).Collide(P, MM(r + clr)):
                        why.append(f'zone {z.GetZoneName()} {L}'); break
        return why

    def in_fill(self, x, y, net, layer, margin=0.0):
        P = V(x, y)
        for z in self.b.Zones():
            if z.GetNetname() == net and not z.GetIsRuleArea() and z.IsOnLayer(lid(self.b, layer)):
                fp = z.GetFilledPolysList(lid(self.b, layer))
                if fp.Contains(P) and (margin == 0 or not self._near_edge(fp, P, margin)): return True
        return False

    def _near_edge(self, fp, P, margin):
        # true if P is within margin of the fill boundary
        for dx, dy in ((margin, 0), (-margin, 0), (0, margin), (0, -margin)):
            if not fp.Contains(pcbnew.VECTOR2I(P.x + MM(dx), P.y + MM(dy))): return True
        return False

    def add_via(self, x, y, net, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(V(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(self.net(net)); self.b.Add(v)
        return v

    def add_track(self, x0, y0, x1, y1, w, layer, net):
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(V(x0, y0)); t.SetEnd(V(x1, y1)); t.SetWidth(MM(w)); t.SetLayer(lid(self.b, layer)); t.SetNet(self.net(net)); self.b.Add(t)
        return t

    def zone(self, name, layer=None):
        zs = [z for z in self.b.Zones() if z.GetZoneName() == name and (layer is None or z.IsOnLayer(lid(self.b, layer)))]
        return zs

    @staticmethod
    def outline_pts(z, i=0):
        o = z.Outline().Outline(i); return [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]

    @staticmethod
    def set_outline(z, pts):
        sp = z.Outline(); sp.RemoveAllContours(); sp.NewOutline()
        for x, y in pts: sp.Append(MM(x), MM(y))
        z.SetNeedRefill(True)

    def clone_zone(self, z, name, layers, pts, prio=None, net=None):
        n = z.Duplicate(False)
        n = n.Cast() if hasattr(n, 'Cast') else n
        n.SetZoneName(name)
        ls = pcbnew.LSET()
        for L in layers: ls.AddLayer(lid(self.b, L))
        n.SetLayerSet(ls)
        self.set_outline(n, pts)
        if prio is not None: n.SetAssignedPriority(prio)
        if net is not None: n.SetNet(self.net(net))
        self.b.Add(n)
        return n

    def save(self, path=None):
        pcbnew.SaveBoard(path or self.path, self.b)
