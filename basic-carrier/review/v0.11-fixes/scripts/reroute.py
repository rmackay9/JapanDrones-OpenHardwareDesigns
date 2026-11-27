# KiCad python: reroute.py board jobs.json [only-job-name...]
# Each job deletes some tracks/vias of one net and re-routes the connection with the grid router, keeping
# out of the given zones' outlines on the given layers (e.g. MVDD pours on F/B, VBATT strips on In2/In3).
#   {"name": "...", "net": "...", "w": 0.25, "del_tracks": [[x0,y0,x1,y1],...], "del_vias": [[x,y],...],
#    "a": [x,y,"F.Cu"], "a_stub": [x,y] | null, "b": [x,y,"B.Cu"], "b_stub": [x,y] | null,
#    "layers": ["In2.Cu","In3.Cu"], "block": {"F.Cu": ["MVDD_ESC1"], ...}, "bbox": [x0,y0,x1,y1], "via": [0.45,0.25]}
# a/b are the fixed ends (pad centre or remaining track end); a stub is a short track on that end's layer to a
# point off the pad, where the via is placed when the route continues on another layer.
import sys, json, math
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else __file__.rsplit('/', 1)[0])
import numpy as np
import pcbnew
from kutil import *
import router as RT

def near(a, b, tol=0.02): return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol

def poly_block(r, L, pts, margin):
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    X, Y = r.GX, r.GY
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        x1, y1, x2, y2 = xs[i], ys[i], xs[(i + 1) % n], ys[(i + 1) % n]
        cond = (y1 > Y) != (y2 > Y)
        with np.errstate(divide='ignore', invalid='ignore'):
            xc = (x2 - x1) * (Y - y1) / (y2 - y1) + x1
        inside ^= cond & (X < xc)
    if margin > 0:   # grow by margin (cheap: shift-or)
        k = int(round(margin / RT.RES)); g = inside.copy()
        for di in range(-k, k + 1):
            for dj in range(-k, k + 1):
                if di * di + dj * dj > k * k: continue
                g |= np.roll(np.roll(inside, di, 0), dj, 1)
        inside = g
    r.block[L] |= inside

def run(B, job):
    b = B.b; net = B.net(job['net']); w = job.get('w', 0.25); vd, vdr = job.get('via', [0.45, 0.25])
    nd = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() != job['net']: continue
        if t.GetClass() == 'PCB_TRACK':
            s, e = (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))
            for x0, y0, x1, y1 in job.get('del_tracks', []):
                if (near(s, (x0, y0)) and near(e, (x1, y1))) or (near(e, (x0, y0)) and near(s, (x1, y1))):
                    b.Delete(t); nd += 1; break
        elif t.GetClass() == 'PCB_VIA':
            p = (mm(t.GetPosition().x), mm(t.GetPosition().y))
            if any(near(p, q) for q in job.get('del_vias', [])): b.Delete(t); nd += 1
    want = len(job.get('del_tracks', [])) + len(job.get('del_vias', []))
    if nd != want: return f"{job['name']}: deleted {nd} of {want} items - ABORT"
    for x0, y0, x1, y1, tw, tl in job.get('pre_tracks', []): B.add_track(x0, y0, x1, y1, tw, tl, job['net'])
    if job.get('route') is False: return f"{job['name']}: deleted {nd} (rip-up only)"
    ax, ay, aL = job['a']; bx, by, bL = job['b']
    A = tuple(job['a_stub']) if job.get('a_stub') else (ax, ay)
    Bp = tuple(job['b_stub']) if job.get('b_stub') else (bx, by)
    layers = job['layers']
    r = RT.Router(b, tuple(job['bbox']), layers, EDGE, HOLES)
    r.build(net.GetNetCode(), w, job.get('clr', 0.2), vd)
    for rx, ry, rd in job.get('reserve', []):    # spots kept free for vias placed later
        for L in layers: r._paint(r.block[L], 'c', (rx, ry), rd / 2 + w / 2 + 0.25)
        r._paint(r.viablock, 'c', (rx, ry), rd / 2 + vd / 2 + 0.25)
    for L, names in job.get('block', {}).items():
        if L not in layers: continue
        for z in b.Zones():
            if z.GetZoneName() in names and z.IsOnLayer(lid(b, L)):
                for i in range(z.Outline().OutlineCount()):
                    poly_block(r, L, Board.outline_pts(z, i), job.get('block_margin', 0.0))
    if job.get('pad_via_gap') is not None:   # review M4: new vias keep this much copper gap to every pad
        gap = job['pad_via_gap']
        for f in b.GetFootprints():
            for p in f.Pads():
                bb = p.GetBoundingBox()
                r._paint(r.viablock, 'r', (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())), vd / 2 + gap)
    for z in b.Zones():                       # no new vias inside these pours (MVDD, phase)
        if z.GetZoneName() in job.get('via_block', []):
            for i in range(z.Outline().OutlineCount()):
                saved = r.block[layers[0]].copy(); r.block[layers[0]][:] = False
                poly_block(r, layers[0], Board.outline_pts(z, i), 0.35)
                r.viablock |= r.block[layers[0]]; r.block[layers[0]] = saved
    for (cx, cy) in job.get('free', []):      # small cleared spots (e.g. around a stub end)
        i, j = r._ix(cx), r._iy(cy); k = int(round(0.4 / RT.RES))
        for L in layers: r.block[L][max(i - k, 0):i + k + 1, max(j - k, 0):j + k + 1] = False
    sl = job.get('a_layers') or ([aL] if (not job.get('a_stub') and aL in layers) else layers)
    gl = job.get('b_layers') or ([bL] if (not job.get('b_stub') and bL in layers) else layers)
    p = r.route(A, Bp, job.get('via_cost', 12.0), sl, gl)
    if p is None: return f"{job['name']}: NO ROUTE"
    added = r.commit(p, net, w, vd, vdr, A, Bp)
    def has_via(pt):
        return any(t.GetClass() == 'PCB_VIA' and t.GetNetname() == job['net'] and near((mm(t.GetPosition().x), mm(t.GetPosition().y)), pt) for t in b.GetTracks())
    Ls = layers
    first, last = Ls[p[0][2]], Ls[p[-1][2]]
    extra = []
    if job.get('a_stub'):
        if not near((ax, ay), A): extra.append(B.add_track(ax, ay, A[0], A[1], w, aL, job['net']))
        if first != aL and not has_via(A): extra.append(B.add_via(A[0], A[1], job['net'], vd, vdr))
    elif first != aL and not has_via(A): extra.append(B.add_via(A[0], A[1], job['net'], vd, vdr))
    if job.get('b_stub'):
        if not near((bx, by), Bp): extra.append(B.add_track(Bp[0], Bp[1], bx, by, w, bL, job['net']))
        if last != bL and not has_via(Bp): extra.append(B.add_via(Bp[0], Bp[1], job['net'], vd, vdr))
    elif last != bL and not has_via(Bp): extra.append(B.add_via(Bp[0], Bp[1], job['net'], vd, vdr))
    for o in extra:
        if o.GetClass() == 'PCB_VIA':
            q = o.GetPosition(); why = B.obstacles(mm(q.x), mm(q.y), mm(o.GetWidth(pcbnew.F_Cu)) / 2, job['net'], CU, clr=0.2, edge=0.3, skip=[o] + added + extra)
            if why: print('   WARNING stub via', round(mm(q.x), 2), round(mm(q.y), 2), why)
    for x0, y0, x1, y1, tw, tl in job.get('post_tracks', []): extra.append(B.add_track(x0, y0, x1, y1, tw, tl, job['net']))
    desc = []
    for o in added + extra:
        if o.GetClass() == 'PCB_VIA': desc.append(f"via({mm(o.GetPosition().x):.2f},{mm(o.GetPosition().y):.2f})")
        else: desc.append(f"{o.GetLayerName()}({mm(o.GetStart().x):.2f},{mm(o.GetStart().y):.2f})-({mm(o.GetEnd().x):.2f},{mm(o.GetEnd().y):.2f})")
    return f"{job['name']}: deleted {nd}, added " + ' '.join(desc)

if __name__ == '__main__':
    B = Board(sys.argv[1]); jobs = json.load(open(sys.argv[2]))
    only = set(sys.argv[3:])
    for j in jobs:
        if only and j['name'] not in only: continue
        print(run(B, j))
    B.save()
