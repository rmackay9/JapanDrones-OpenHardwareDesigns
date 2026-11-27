import sys, numpy as np
from solve import *
def comps(n):
    par = np.arange(n.N)
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    # vectorised union by repeated min propagation over edges
    lab = np.arange(n.N)
    while True:
        m = np.minimum(lab[n.ei], lab[n.ej])
        new = lab.copy(); np.minimum.at(new, n.ei, m); np.minimum.at(new, n.ej, m)
        new = new[new]; new = new[new]
        if np.array_equal(new, lab): break
        lab = new
    return lab
if __name__ == '__main__':
    d = load(sys.argv[1]); n = Net(d, sys.argv[2], (99.5, 49.5, 192, 140.5), float(sys.argv[3]))
    lab = comps(n)
    for r, num in [x.split('.') for x in sys.argv[4:]]:
        nodes = n.pad_nodes(r, num); print(r, num, set(lab[nodes].tolist()))
    u, c = np.unique(lab, return_counts=True); print('components', len(u), sorted(c)[-6:])
