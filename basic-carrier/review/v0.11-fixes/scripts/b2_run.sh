#!/bin/bash
# Re-applies all B2 steps on the B1 board (commit 0da7e29). Run from this folder with that board checked out;
# the git checkout line below restores the board from HEAD, so only use it while HEAD is the B1 commit.
set -e
export MSYS_NO_PATHCONV=1; K="/c/Program Files/KiCad/10.0/bin"; BRD="$(cygpath -w ../../..)\JapanDrones_BasicCarrier.kicad_pcb"
PY() { "$K/python.exe" "$@"; }
git checkout -q ../../../JapanDrones_BasicCarrier.kicad_pcb
PY reroute.py "$BRD" b2_esc1.json
PY add_vias.py "$BRD" /VimDrones_mod1/MVDD 181.8,70.9,185.6,80.5 1.0 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod1/MVDD 162.2,65.5,185.5,70.4 1.0 14 F.Cu,B.Cu 0.6 0.3 nopad
PY reroute.py "$BRD" b2_esc2.json
for f in $EXTRA; do PY $f "$BRD"; done
PY reroute.py "$BRD" b2_esc3.json
PY reroute.py "$BRD" b2_esc4.json
# MVDD stitching blocks (0.6/0.3, kept 0.3 mm off every pad)
PY add_vias.py "$BRD" /VimDrones_mod2/MVDD 181.1,108.2,185.7,119.3 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod2/MVDD 161.9,119.6,185.7,124.9 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod3/MVDD 101.2,106.6,108.5,119.4 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod3/MVDD 103.7,119.6,129.5,124.9 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod/MVDD 103.7,70.7,108.0,82.1 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod/MVDD 103.7,65.3,128.8,70.5 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod1/MVDD 162,65.3,185.6,70.5 0.9 14 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod2/MVDD 161.9,119.6,185.7,124.9 0.8 6 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod1/MVDD 162,65.3,185.6,70.5 0.8 6 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod2/MVDD 161.9,119.6,185.7,124.9 0.75 6 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod3/MVDD 103.7,119.6,129.5,124.9 0.75 6 F.Cu,B.Cu 0.6 0.3 nopad
PY add_vias.py "$BRD" /VimDrones_mod/MVDD 103.7,65.3,128.8,70.5 0.75 6 F.Cu,B.Cu 0.6 0.3 nopad
