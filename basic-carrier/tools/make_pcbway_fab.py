# KiCad python: make_pcbway_fab.py board.kicad_pcb outdir
# Writes PCBWay_bom.csv and PCBWay_positions.csv (same columns as fab/v0.10) from the board's footprints.
import pcbnew, sys, csv, re, collections, os
b = pcbnew.LoadBoard(sys.argv[1]); out = sys.argv[2]; mm = pcbnew.ToMM
def fld(f, k): return f.GetFieldText(k).strip() if f.HasField(k) else ''
def natkey(r): m = re.match(r'([A-Z]+)(\d+)', r); return (m.group(1), int(m.group(2))) if m else (r, 0)
POL = {'D': 'polarised: diode/TVS/LED, check cathode mark', 'U': 'pin 1 orientation', 'Q': 'pin orientation', 'Y': 'pin 1 orientation',
       'J': 'connector orientation'}
rows, skipped = [], []
for f in b.GetFootprints():
    a = f.GetAttributes(); ref = f.GetReference()
    if a & (pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_DNP):
        skipped.append((ref, f.GetValue(), 'DNP' if a & pcbnew.FP_DNP else '', 'not in BOM' if a & pcbnew.FP_EXCLUDE_FROM_BOM else '')); continue
    p = f.GetPosition()
    rows.append(dict(ref=ref, val=f.GetValue(), fp=f.GetFPID().GetLibItemName().wx_str(), mpn=fld(f, 'MPN'), lcsc=fld(f, 'LCSC'),
                     mf=fld(f, 'MF') or fld(f, 'MFR_NAME') or fld(f, 'MANUFACTURER'), desc='' if fld(f, 'Description').startswith('http') else fld(f, 'Description'),
                     mount='tht' if a & pcbnew.FP_THROUGH_HOLE else 'smt', x=mm(p.x), y=mm(p.y), rot=f.GetOrientationDegrees(),
                     side='bottom' if f.IsFlipped() else 'top'))
def note(r):
    n = []
    if not r['mpn']: n.append('NO MPN')
    if not r['lcsc']: n.append('no LCSC number')
    pre = re.match(r'[A-Z]+', r['ref']).group(0)
    if pre == 'C' and (r['fp'].startswith('CP') or 'CAPAE' in r['fp']): n.append('polarised: electrolytic, check + mark')
    elif pre in POL and not r['ref'].startswith('RSHUNT'): n.append(POL[pre])
    if r['mount'] == 'tht': n.append('through-hole')
    return '; '.join(n)
g = collections.OrderedDict()
for r in sorted(rows, key=lambda r: (r['mpn'] or '~', r['val'], natkey(r['ref']))):
    g.setdefault((r['mpn'], r['val'], r['fp']), []).append(r)
with open(os.path.join(out, 'PCBWay_bom.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['Item', 'Designator', 'Quantity', 'Value', 'Footprint', 'Manufacturer', 'MPN', 'LCSC', 'Mount_Type', 'Side', 'Description', 'Notes'])
    items = sorted(g.values(), key=lambda rs: natkey(sorted(rs, key=lambda r: natkey(r['ref']))[0]['ref']))
    for i, rs in enumerate(items, 1):
        rs = sorted(rs, key=lambda r: natkey(r['ref'])); r = rs[0]
        sides = sorted(set(x['side'] for x in rs))
        w.writerow([i, ', '.join(x['ref'] for x in rs), len(rs), r['val'], r['fp'], r['mf'], r['mpn'], r['lcsc'], r['mount'], '+'.join(sides), r['desc'], note(r)])
with open(os.path.join(out, 'PCBWay_positions.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['pos_x', 'pos_y', 'rotation', 'side', 'designator', 'mpn', 'pack', 'footprint', 'value', 'mount_type'])
    for r in sorted(rows, key=lambda r: natkey(r['ref'])):
        w.writerow([round(r['x'], 6), round(-r['y'], 6), round(r['rot'], 3), r['side'], r['ref'], r['mpn'], '', r['fp'], r['val'], r['mount']])
print('placed parts', len(rows), 'BOM lines', len(g), 'top', sum(r['side'] == 'top' for r in rows), 'bottom', sum(r['side'] == 'bottom' for r in rows))
print('not placed:', skipped)
for rs in g.values():
    n = note(rs[0])
    if 'MPN' in n or 'LCSC' in n: print('GAP', ', '.join(x['ref'] for x in rs), rs[0]['val'], rs[0]['mpn'], '|', n)
