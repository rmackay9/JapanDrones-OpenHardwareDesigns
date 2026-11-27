"""Write a STEP (AP214) solid box next to each placeholder box VRML in 3dmodels/.

The placeholder .wrl files are single axis-aligned boxes in KiCad VRML units
(0.1 inch). KiCad's STEP export cannot use VRML, but with --subst-models it
uses a .step file with the same base name instead. This script writes those.

usage: python tools/wrl_box_to_step.py 3dmodels/*.wrl
"""
import re
import sys
from pathlib import Path

UNIT = 2.54  # mm per VRML unit used by KiCad


def box_from_wrl(path):
    txt = Path(path).read_text()
    nums = [float(v) for v in re.search(r'point \[([^\]]*)\]', txt).group(1).replace(',', ' ').split()]
    pts = [tuple(nums[i:i + 3]) for i in range(0, len(nums), 3)]
    xs, ys, zs = zip(*pts)
    return [v * UNIT for v in (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))]


def step_box(name, x0, x1, y0, y1, z0, z1):
    ents = []

    def add(s):
        ents.append(s)
        return len(ents)

    def pt(p):
        return add("CARTESIAN_POINT('',(%.6f,%.6f,%.6f))" % p)

    def dirn(d):
        return add("DIRECTION('',(%.1f,%.1f,%.1f))" % d)

    V = {}
    corners = {}
    for i, x in enumerate((x0, x1)):
        for j, y in enumerate((y0, y1)):
            for k, z in enumerate((z0, z1)):
                corners[(i, j, k)] = (x, y, z)
                V[(i, j, k)] = add("VERTEX_POINT('',#%d)" % pt((x, y, z)))

    E = {}

    def edge(a, b):
        key = (a, b) if a < b else (b, a)
        if key not in E:
            pa, pb = corners[key[0]], corners[key[1]]
            d = tuple(pb[n] - pa[n] for n in range(3))
            L = max(abs(c) for c in d)
            u = tuple(c / L for c in d)
            line = add("LINE('',#%d,#%d)" % (pt(pa), add("VECTOR('',#%d,%.6f)" % (dirn(u), L))))
            E[key] = add("EDGE_CURVE('',#%d,#%d,#%d,.T.)" % (V[key[0]], V[key[1]], line))
        return E[key], (a, b) == key

    def face(loop, origin, normal, ref):
        oes = []
        for n in range(4):
            e, fwd = edge(loop[n], loop[(n + 1) % 4])
            oes.append(add("ORIENTED_EDGE('',*,*,#%d,%s)" % (e, '.T.' if fwd else '.F.')))
        el = add("EDGE_LOOP('',(%s))" % ','.join('#%d' % o for o in oes))
        fb = add("FACE_OUTER_BOUND('',#%d,.T.)" % el)
        ax = add("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)" % (pt(origin), dirn(normal), dirn(ref)))
        pl = add("PLANE('',#%d)" % ax)
        return add("ADVANCED_FACE('',(#%d),#%d,.T.)" % (fb, pl))

    # loops ordered counter-clockwise seen from outside (normal points out)
    faces = [
        face([(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)], (x0, y0, z0), (0, 0, -1), (1, 0, 0)),
        face([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], (x0, y0, z1), (0, 0, 1), (1, 0, 0)),
        face([(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], (x0, y0, z0), (0, -1, 0), (1, 0, 0)),
        face([(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)], (x0, y1, z0), (0, 1, 0), (1, 0, 0)),
        face([(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)], (x0, y0, z0), (-1, 0, 0), (0, 1, 0)),
        face([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)], (x1, y0, z0), (1, 0, 0), (0, 1, 0)),
    ]
    shell = add("CLOSED_SHELL('',(%s))" % ','.join('#%d' % f for f in faces))
    solid = add("MANIFOLD_SOLID_BREP('%s',#%d)" % (name, shell))

    ctx_app = add("APPLICATION_CONTEXT('automotive_design')")
    add("APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#%d)" % ctx_app)
    pctx = add("PRODUCT_CONTEXT('',#%d,'mechanical')" % ctx_app)
    prod = add("PRODUCT('%s','%s','',(#%d))" % (name, name, pctx))
    pdf = add("PRODUCT_DEFINITION_FORMATION('','',#%d)" % prod)
    pdctx = add("PRODUCT_DEFINITION_CONTEXT('part definition',#%d,'design')" % ctx_app)
    pd = add("PRODUCT_DEFINITION('design','',#%d,#%d)" % (pdf, pdctx))
    pds = add("PRODUCT_DEFINITION_SHAPE('','',#%d)" % pd)
    mm = add("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))")
    rad = add("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
    sr = add("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())")
    unc = add("UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#%d,'distance_accuracy_value','')" % mm)
    gctx = add("(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#%d))"
               "GLOBAL_UNIT_ASSIGNED_CONTEXT((#%d,#%d,#%d))REPRESENTATION_CONTEXT('',''))" % (unc, mm, rad, sr))
    origin = add("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)" % (pt((0, 0, 0)), dirn((0, 0, 1)), dirn((1, 0, 0))))
    rep = add("ADVANCED_BREP_SHAPE_REPRESENTATION('',(#%d,#%d),#%d)" % (origin, solid, gctx))
    add("SHAPE_DEFINITION_REPRESENTATION(#%d,#%d)" % (pds, rep))

    head = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('placeholder box'),'2;1');\n"
            "FILE_NAME('%s.step','',(''),(''),'wrl_box_to_step.py','','');\n"
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n" % name)
    body = ''.join('#%d=%s;\n' % (i + 1, e) for i, e in enumerate(ents))
    return head + body + "ENDSEC;\nEND-ISO-10303-21;\n"


for f in sys.argv[1:]:
    p = Path(f)
    out = p.with_suffix('.step')
    out.write_bytes(step_box(p.stem, *box_from_wrl(p)).encode('ascii'))
    print(out, ['%.2f' % v for v in box_from_wrl(p)])
