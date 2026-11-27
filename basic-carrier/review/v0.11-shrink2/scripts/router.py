# Small grid A* router for KiCad python (pcbnew + numpy). Routes one connection at a time.
import heapq, math
import numpy as np
import pcbnew

mm = pcbnew.ToMM
MM = pcbnew.FromMM
RES = 0.1
CU = {'F.Cu': pcbnew.F_Cu, 'In1.Cu': pcbnew.In1_Cu, 'In2.Cu': pcbnew.In2_Cu, 'In3.Cu': pcbnew.In3_Cu,
      'In4.Cu': pcbnew.In4_Cu, 'B.Cu': pcbnew.B_Cu}


class Router:
    def __init__(self, board, bbox, layers, edge=(None, None, None, None), holes=(), res=None):
        global RES
        if res: RES = res
        else: RES = 0.1
        self.b = board
        self.x0, self.y0, self.x1, self.y1 = bbox
        self.nx = int((self.x1 - self.x0) / RES) + 1
        self.ny = int((self.y1 - self.y0) / RES) + 1
        self.layers = layers                 # names, routing allowed on these
        self.edge = edge                     # board outline x0,x1,y0,y1
        self.holes = holes                   # (x, y, r)
        gx = self.x0 + np.arange(self.nx) * RES
        gy = self.y0 + np.arange(self.ny) * RES
        self.GX, self.GY = np.meshgrid(gx, gy, indexing='ij')

    # ---------------- obstacles ----------------
    def _collect(self, netcode):
        objs = []   # (kind, layers set or None(all), geometry, half_width)
        for t in self.b.GetTracks():
            if t.GetNetCode() == netcode: continue
            if t.GetClass() == 'PCB_VIA':
                p = t.GetPosition()
                objs.append(('c', None, (mm(p.x), mm(p.y)), mm(t.GetWidth(pcbnew.F_Cu)) / 2))
            else:
                s, e = t.GetStart(), t.GetEnd()
                objs.append(('s', {t.GetLayerName()}, (mm(s.x), mm(s.y), mm(e.x), mm(e.y)), mm(t.GetWidth()) / 2))
        for f in self.b.GetFootprints():
            for pad in f.Pads():
                if pad.GetNetCode() == netcode and netcode > 0: continue
                bb = pad.GetBoundingBox()
                L = {self.b.GetLayerName(l) for l in pad.GetLayerSet().CuStack()}
                tht = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
                if tht: L = None
                objs.append(('r', L, (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())), 0))
            for z in f.Zones():          # footprint keepouts
                if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
                    bb = z.Outline().BBox()
                    L = {self.b.GetLayerName(l) for l in z.GetLayerSet().CuStack()}
                    objs.append(('r', L, (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())), 0))
        for z in self.b.Zones():
            if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
                bb = z.Outline().BBox()
                L = {self.b.GetLayerName(l) for l in z.GetLayerSet().CuStack()}
                objs.append(('r', L, (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())), 0))
        return objs

    def _paint(self, grid, kind, geom, R):
        if kind == 'c':
            x, y = geom
            i0, i1 = self._ix(x - R), self._ix(x + R) + 1
            j0, j1 = self._iy(y - R), self._iy(y + R) + 1
            if i1 <= 0 or j1 <= 0 or i0 >= self.nx or j0 >= self.ny: return
            i0, j0 = max(i0, 0), max(j0, 0)
            sub = (self.GX[i0:i1, j0:j1] - x) ** 2 + (self.GY[i0:i1, j0:j1] - y) ** 2 <= R * R
            grid[i0:i1, j0:j1] |= sub
        elif kind == 's':
            ax, ay, bx, by = geom
            i0, i1 = self._ix(min(ax, bx) - R), self._ix(max(ax, bx) + R) + 1
            j0, j1 = self._iy(min(ay, by) - R), self._iy(max(ay, by) + R) + 1
            if i1 <= 0 or j1 <= 0 or i0 >= self.nx or j0 >= self.ny: return
            i0, j0 = max(i0, 0), max(j0, 0)
            X = self.GX[i0:i1, j0:j1]; Y = self.GY[i0:i1, j0:j1]
            vx, vy = bx - ax, by - ay
            L2 = vx * vx + vy * vy
            if L2 == 0:
                t = 0
            else:
                t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
            d2 = (ax + t * vx - X) ** 2 + (ay + t * vy - Y) ** 2
            grid[i0:i1, j0:j1] |= d2 <= R * R
        else:
            l, t, r, bt = geom
            i0, i1 = self._ix(l - R), self._ix(r + R) + 1
            j0, j1 = self._iy(t - R), self._iy(bt + R) + 1
            if i1 <= 0 or j1 <= 0 or i0 >= self.nx or j0 >= self.ny: return
            grid[max(i0, 0):i1, max(j0, 0):j1] = True

    def _ix(self, x): return int(round((x - self.x0) / RES))
    def _iy(self, y): return int(round((y - self.y0) / RES))

    def build(self, netcode, w, clr, via_d):
        objs = self._collect(netcode)
        self.block = {}
        for L in self.layers:
            g = np.zeros((self.nx, self.ny), bool)
            for kind, Ls, geom, hw in objs:
                if Ls is not None and L not in Ls: continue
                self._paint(g, kind, geom, hw + w / 2 + clr)
            self._edges(g, w / 2 + 0.3)
            self.block[L] = g
        v = np.zeros((self.nx, self.ny), bool)
        for kind, Ls, geom, hw in objs:       # a through via touches every copper layer
            self._paint(v, kind, geom, hw + via_d / 2 + clr)
        for t in self.b.GetTracks():          # keep hole spacing to same-net vias too
            if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == netcode:
                p = t.GetPosition()
                self._paint(v, 'c', (mm(p.x), mm(p.y)), mm(t.GetWidth(pcbnew.F_Cu)) / 2 + via_d / 2 + 0.15)
        self._edges(v, via_d / 2 + 0.3)
        self.viablock = v

    def _edges(self, g, R):
        ex0, ex1, ey0, ey1 = self.edge
        if ex0 is not None:
            g |= (self.GX < ex0 + R) | (self.GX > ex1 - R) | (self.GY < ey0 + R) | (self.GY > ey1 - R)
        for hx, hy, hr in self.holes:
            self._paint(g, 'c', (hx, hy), hr + R)

    # ---------------- search ----------------
    def route(self, start, goal, via_cost=12.0, start_layers=None, goal_layers=None):
        """start/goal: (x, y). layers: lists of allowed layer names at the ends."""
        Ls = self.layers
        sl = start_layers or Ls
        gl = set(goal_layers or Ls)
        si, sj = self._ix(start[0]), self._iy(start[1])
        gi, gj = self._ix(goal[0]), self._iy(goal[1])
        # free the end cells (they sit on same-net copper)
        fr = max(1, int(round(0.2 / RES)))
        for L in Ls:
            for (ci, cj) in ((si, sj), (gi, gj)):
                self.block[L][max(ci - fr, 0):ci + fr + 1, max(cj - fr, 0):cj + fr + 1] = False
        h = lambda i, j: math.hypot(i - gi, j - gj)
        openh = []
        g = {}
        came = {}
        for L in sl:
            k = (si, sj, Ls.index(L))
            g[k] = 0
            heapq.heappush(openh, (h(si, sj), 0, k))
        dirs = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
        n = 0
        while openh:
            f, gc, k = heapq.heappop(openh)
            if gc > g.get(k, 1e18): continue
            i, j, li = k
            if i == gi and j == gj and Ls[li] in gl:
                path = [k]
                while k in came:
                    k = came[k]; path.append(k)
                return path[::-1]
            n += 1
            if n > 6_000_000: return None
            blk = self.block[Ls[li]]
            for di, dj, c in dirs:
                a, bb = i + di, j + dj
                if a < 0 or bb < 0 or a >= self.nx or bb >= self.ny or blk[a, bb]: continue
                nk = (a, bb, li); ng = gc + c
                if ng < g.get(nk, 1e18):
                    g[nk] = ng; came[nk] = k
                    heapq.heappush(openh, (ng + h(a, bb), ng, nk))
            if not self.viablock[i, j]:
                for l2 in range(len(Ls)):
                    if l2 == li: continue
                    nk = (i, j, l2); ng = gc + via_cost
                    if ng < g.get(nk, 1e18):
                        g[nk] = ng; came[nk] = k
                        heapq.heappush(openh, (ng + h(i, j), ng, nk))
        return None

    def _clear_line(self, L, a, b_):
        (i0, j0), (i1, j1) = a, b_
        n = max(abs(i1 - i0), abs(j1 - j0))
        blk = self.block[L]
        for s in range(n + 1):
            i = int(round(i0 + (i1 - i0) * s / max(n, 1))); j = int(round(j0 + (j1 - j0) * s / max(n, 1)))
            if blk[i, j]: return False
        return True

    def commit(self, path, net, w, via_d, via_drill, start_xy=None, goal_xy=None):
        """Turn a grid path into tracks + vias on the board (string-pulled per layer run)."""
        Ls = self.layers
        runs = []
        cur = [path[0]]
        for k in path[1:]:
            if k[2] != cur[-1][2]:
                runs.append(cur); cur = [k]
            else:
                cur.append(k)
        runs.append(cur)
        added = []
        for ri, run in enumerate(runs):
            L = Ls[run[0][2]]
            pts = [(k[0], k[1]) for k in run]
            # string pull
            out = [pts[0]]; a = 0
            while a < len(pts) - 1:
                bnext = a + 1
                for c in range(len(pts) - 1, a, -1):
                    if self._clear_line(L, pts[a], pts[c]):
                        bnext = c; break
                out.append(pts[bnext]); a = bnext
            xy = [(self.x0 + i * RES, self.y0 + j * RES) for i, j in out]
            if ri == 0 and start_xy: xy[0] = start_xy
            if ri == len(runs) - 1 and goal_xy: xy[-1] = goal_xy
            for (xa, ya), (xb, yb) in zip(xy, xy[1:]):
                if abs(xa - xb) < 1e-6 and abs(ya - yb) < 1e-6: continue
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(pcbnew.VECTOR2I(MM(xa), MM(ya))); t.SetEnd(pcbnew.VECTOR2I(MM(xb), MM(yb)))
                t.SetWidth(MM(w)); t.SetLayer(CU[L]); t.SetNet(net); self.b.Add(t); added.append(t)
            if ri < len(runs) - 1:
                v = pcbnew.PCB_VIA(self.b)
                v.SetPosition(pcbnew.VECTOR2I(MM(xy[-1][0]), MM(xy[-1][1])))
                v.SetWidth(MM(via_d)); v.SetDrill(MM(via_drill)); v.SetNet(net)
                v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                self.b.Add(v); added.append(v)
        return added


def connect(board, net_name, start, goal, w, layers, bbox, edge, holes=(), clr=0.2, via_d=0.45, via_drill=0.25,
            start_layers=None, goal_layers=None, via_cost=12.0):
    net = board.FindNet(net_name)
    r = Router(board, bbox, layers, edge, holes)
    r.build(net.GetNetCode(), w, clr, via_d)
    p = r.route(start, goal, via_cost, start_layers, goal_layers)
    if p is None: return None
    return r.commit(p, net, w, via_d, via_drill, start, goal)
