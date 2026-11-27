#!/bin/bash
# M1 steps as applied on top of the B2 commit (run from this folder; refill zones between the two steps)
K="/c/Program Files/KiCad/10.0/bin"; BRD="$(cygpath -w ../../..)\JapanDrones_BasicCarrierBoard_v0.10.kicad_pcb"
"$K/python.exe" m1_zone.py "$BRD"
# -> kicad-cli pcb drc --refill-zones --save-board ...
MSYS_NO_PATHCONV=1 "$K/python.exe" add_vias.py "$BRD" VBATT 100.95,125.7,190.4,134.3 1.6 60 F.Cu,In2.Cu,In3.Cu 0.6 0.3 102.61,137.5,3.85 188.75,137.5,3.85 nopad
"$K/python.exe" del_vias.py "$BRD" VBATT 188.15,127.09     # it cut the J6 GND via off In1/In4
