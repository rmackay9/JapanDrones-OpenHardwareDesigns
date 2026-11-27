# v0.11 review fixes (B1, B2, M1, M4, M6)

Layout-only fixes for `review/v0.11-final-review.md`. No schematic or component change.
One commit per item on master: B1 `0da7e29`, B2 `f8e97fe`, M1 `0d2038e`, M4 `32b3a7c`, M6 `b0043e3`.

## Results (DC model, 1 oz all layers, 20 A per ESC; `analysis/vbatt.py`, `analysis/mvdd.py`)

VBATT drop, XT90 + pin to each shunt, and total VBATT copper loss:

| | ESC1 | ESC2 | ESC3 | ESC4 | loss |
|---|---|---|---|---|---|
| v0.11 as reviewed | 234 mV | 236 mV | 887 mV | 904 mV | 45 W |
| after B1 | 234 | 236 | 374 | 390 | 25 W |
| after B2 | 198 | 200 | 375 | 387 | 23 W |
| after M1 | 100 | 101 | 125 | 137 | 9.3 W |
| final (after M6 clip) | 102 | 103 | 130 | 143 | 9.6 W |
| v0.10 | 146 | 145 | 534 | 179 | 20 W |

MVDD, shunt to middle high-side FET at 20 A (islands = F.Cu/B.Cu pieces of at least 1 mm²):

| | islands before → after | shunt-side top copper | vias into FET-drain copper | drop |
|---|---|---|---|---|
| ESC1 | 3/2 → 1/1 | 59 → 166 mm² | 1 → 35 | 100 → 37 mV |
| ESC2 | 3/2 → 1/1 | 69 → 168 mm² | 4 → 30 | 113 → 46 mV |
| ESC3 | 4/1 → 1/1 | 58 → 172 mm² | 5 → 38 | 67 → 46 mV |
| ESC4 | 5/1 → 1/1 | 71 → 180 mm² | 8 → 37 | 52 → 36 mV |
| v0.10 | 1/1 | ~200 mm² | 22–27 | 29–31 mV |

M6 (pads excluded): VBATT/MVDD/phase copper to outline 0.20 → 0.50 mm; non-GND outer copper to corner-hole centre 1.70 → 3.50 mm.
The project now has a `.kicad_dru` that keeps both enforced in DRC.

## Open
- **B1:** the F.Cu left-edge strip is not 2.5 mm wide. The ESC3 capacitor GND pads (x 101.5–102.7) and RSHUNT5 set its width, not the MVDD_ESC3 zone.
  Widening it means moving the ESC3 capacitor block about 2 mm inboard. The model gives 6 mV for it once the inner strips are tied in, so it was left.
- **B2:** ESC2 got 8 new MVDD vias (others 9–15); its strip is full of capacitor pads. HO1 of ESC3 crosses the In3 left VBATT strip for about 4 mm.
  The ESC3 and ESC4 J16/J15 +5.2V re-routes take detours; tidy them by hand if wanted.
- **M4:** 6 vias still touch their pads.
  - Moved in the third pass (`scripts/m4_nudge_run.sh`):
    - U2.19 (ESC4 HO1): bootstrap cap C21 and diode D2 moved 0.25 mm away from the driver, and the HO1 via now sits 0.32 mm above the pin.
      Track length change: HO1 +0.08 mm, VB1 +0.18 mm, VS1 +0.18 mm, HO2 +0.05 mm, +10V +0.25 mm.
    - U16.1 (ESC3 LIN1, logic input): the via was moved and LIN1 is 7.3 mm longer. One GND stitching via was added at (119.2, 107.3) to re-join the B.Cu GND piece the new route split off.
  - U12.9 (ESC2 LO3): a via 0.3 mm off the pin collides with C75.2 on F.Cu. Moving C75 0.15–0.3 mm hits the LO1 via between C75's pads, the +10V track and C73's courtyard. Moving the LO2 and In3 VS2 tracks alone doesn't free it.
  - U3.13 (HO3), U3.15 (VS2): boxed in by the HO2/VB3 escapes on B.Cu, C54.2 on F.Cu, and the VS3/GND tracks on In2/In3. Freeing them means moving C54 and C59 by more than 0.5 mm and re-routing HO2, VB3 and HO3 together.
  - C42.2, C43.1, C46.1, U20.2: GND pads, left as agreed. C42.2's via also carries the In3/F.Cu GND links to C54.2.
  - What's left: a larger re-place in those two corners, or filled and capped vias.
- **M3** (buck RT): left as is by request. Measure the switch-node frequency on v0.10 under load.

## Files
- `scripts/`: the KiCad-python edits (reroute.py uses the grid router from `../v0.11-shrink2/scripts/router.py`).
- `analysis/`: board dump (`kdump.py`, KiCad python), DC solver and island counter (system python with numpy and PIL), via-in-pad and M6 checks. `check.sh` runs refill, DRC with parity, dump and both solvers.
