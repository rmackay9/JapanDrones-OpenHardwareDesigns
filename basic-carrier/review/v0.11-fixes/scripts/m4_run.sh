#!/bin/bash
# M4 as applied on top of the M1 commit (4 passes; later passes relaxed the search, see m4_vias.py)
K="/c/Program Files/KiCad/10.0/bin"; BRD="$(cygpath -w ../../..)\JapanDrones_BasicCarrierBoard_v0.10.kicad_pcb"
"$K/python.exe" m4_vias.py "$BRD" $(cat m4_pads.txt)
M4_SMALL=1 "$K/python.exe" m4_vias.py "$BRD" U2.19 U16.1 U3.13 U3.15 U12.9 D11.1 R105.1 R112.1 C64.1 U11.3 U20.2 C93.2 R97.1 R130.2 C43.1 C46.1 C42.2 F1.1
"$K/python.exe" del_items.py "$BRD" VBATT via:147.80,109.55 trk:148.75,110.50,147.80,109.55   # F1.1 sits in the B.Cu VBATT pour already
