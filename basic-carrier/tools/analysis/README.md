# Copper analysis tools

A DC copper model of the board, used for the v0.11 reviews (`../../reviews/`).
It rasterises the filled copper of each net and layer, follows vias between layers, and solves the current flow on a resistor grid.
Use it to check power paths after layout changes: battery (VBATT) drop to each ESC, motor-supply (MVDD) pours, narrow passages, floating GND copper.

Assumptions: 1 oz (35 µm) copper on every layer, 20 µm via plating, copper at 20 °C, DC only, no thermal model. Treat the numbers as ±20 %.

## Use

1. Dump the board with KiCad's Python (read-only, never saves the board). The tag is any name for this snapshot:

   ```
   "C:\Program Files\KiCad\10.0\bin\python.exe" tools/analysis/dump.py JapanDrones_BasicCarrier.kicad_pcb <work dir>/now.json
   ```

2. Run the scripts with a normal Python 3 that has `numpy`, `opencv-python` and `matplotlib`, from the work directory (they read `<tag>.json` and write their results next to it):

   ```
   cd <work dir>
   python <board>/tools/analysis/vbatt.py now      # VBATT drop XT90 -> each shunt at 20 A per ESC, copper loss, busiest vias
   python <board>/tools/analysis/mvdd.py now       # per ESC: MVDD islands, shunt -> high-side FET drop, via sharing
   ```

| Script | What it reports |
|---|---|
| `dump.py` | KiCad Python: tracks, vias, pads and filled zones to JSON |
| `cu.py` | Shared copper rasteriser and 3D resistor network (imported by the others) |
| `vbatt.py` | VBATT drop to each ESC shunt, total loss per layer, via currents (run before `cuts.py`/`shuntvias.py`) |
| `mvdd.py` | Each ESC's MVDD pour: islands per layer, drop to each FET, via currents |
| `gnd.py` | Ground rise and loss with current returning from each ESC |
| `neck.py` | Narrowest passage from each ESC's capacitor strip to its FETs, per layer |
| `strip.py` | Width of the left VBATT strip per layer along y |
| `cuts.py`, `shuntvias.py` | Cross-sections of the battery band, and vias at the shunt pads (use `vbatt.py`'s results) |
| `gfloat.py`, `gndvia.py` | Floating GND copper, and a spot for a via to ground each piece |
| `m6.py` | Battery and phase copper distance to the board edge and the corner holes |
| `vip.py` | Vias inside or touching SMD pads |
| `zoom.py` | Picture of one net's copper in a box, with labels |

ESC positions, shunts and FETs are hard-coded for this board in `mvdd.py`, `neck.py` and `gnd.py`.

Results for v0.11-dev (`now`): VBATT drop 107/107/133/145 mV to ESC1–4, 9.8 W loss at 4 × 20 A;
ESC2 MVDD neck 1.09 mm (F.Cu) / 1.56 mm (B.Cu); floating GND 63.6 mm² in 4 pieces; left strip 10.3 mm at y = 124.3.
