#!/bin/bash
# check.sh TAG : refill+DRC(parity)+save repo board, dump, analyse
TAG=$1; W=SCRATCH
R=BOARD_DIR
K="/c/Program Files/KiCad/10.0/bin"; B=JapanDrones_BasicCarrierBoard_v0.10.kicad_pcb
cd $R
"$K/kicad-cli.exe" pcb drc --schematic-parity --refill-zones --save-board --format json -o $W/$TAG.drc.json $B >/dev/null
python - $W/$TAG.drc.json $B <<'PY'
import json,collections,sys
d=json.load(open(sys.argv[1]))
c=collections.Counter((v['severity'],v['type']) for v in d['violations'])
err=sum(n for (s,t),n in c.items() if s=='error')
print(f"DRC errors {err} unconnected {len(d['unconnected_items'])} parity {len(d['schematic_parity'])} warnings {sum(c.values())-err}")
print('  ', dict((t,n) for (s,t),n in c.items()))
a=open(sys.argv[2],'rb').read(); print('  line endings CRLF', a.count(b'\r\n'), 'bare LF', a.count(b'\n')-a.count(b'\r\n'))
PY
"$K/python.exe" $W/kdump.py "BOARD_DIR" "SCRATCH" >/dev/null
cd $W; python vbatt.py $TAG.json 0.2 | head -2; python mvdd.py $TAG.json
