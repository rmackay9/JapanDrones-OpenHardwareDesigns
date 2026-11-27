#!/bin/bash
# M4 third pass, applied on top of commit 0d4c442 (run from this folder)
K="/c/Program Files/KiCad/10.0/bin/python.exe"; BRD="$(cygpath -w ../../..)\JapanDrones_BasicCarrierBoard_v0.10.kicad_pcb"
export MSYS_NO_PATHCONV=1
# U2.19 (ESC4 HO1): bootstrap cap C21 and diode D2 up 0.25 mm; HO1 via above the pin; VB1 and HO2 re-routed round it
"$K" nudge.py "$BRD" C21 0 -0.25 D2 0 -0.25
"$K" reroute.py "$BRD" m4n_u2.json
"$K" del_items.py "$BRD" +10V trk:112.502,71.645,109.485,74.895
"$K" add_tracks.py "$BRD" +10V B.Cu 0.3 112.502,71.645,112.502,71.895 112.502,71.895,109.485,74.895
# U16.1 (ESC3 LIN1, logic input): via moved by the router; one GND stitching via re-joins the B.Cu GND piece it split off
"$K" reroute.py "$BRD" m4n_u16.json
"$K" add_via1.py "$BRD" GND 119.2 107.3
