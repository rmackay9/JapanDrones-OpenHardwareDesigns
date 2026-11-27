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

## Re-review follow-up (`review/v0.11-rereview.md`)

Layout only, three commits on master: R1 `229011a`, R6/R9/N2 `660e1f5`, R3 `e128125`. R2 (vias under U3.13, U3.15, U12.9) is left for Randy to decide (filled and capped vias or accept the risk).

| | before (`4de16da`) | after |
|---|---|---|
| **R1** ESC2 MVDD strip-to-FET passage, F.Cu / B.Cu | 0.42 / 0.42 mm at (182.0, 118.6) | **1.09 / 1.56 mm** |
| ESC2 drop shunt → Q17 at 20 A (`analysis/mvdd.py`) | 46 mV | **37 mV** |
| **R3** left VBATT strip at y = 124.3, F / In2 / In3 | 0 / 4.26 / 1.32 = 5.58 mm | **1.16 / 6.04 / 3.10 = 10.30 mm** |
| left strip at y = 118.8 | 8.76 mm | 11.26 mm (F.Cu 2.50) |
| VBATT drop to shunts ESC1–4, loss (`analysis/vbatt.py`) | 102 / 103 / 129 / 141 mV, 9.5 W | 101 / 101 / 124 / 137 mV, 9.3 W |
| same, re-review model (`v0.11-rereview/scripts/vbatt.py`, `mvdd.py`) | VBATT 108 / 110 / 137 / 149 mV, 10.1 W; ESC2 Q17 / Q19 47 / 58 mV | VBATT 107 / 107 / 133 / 145 mV, 9.8 W; ESC2 Q17 / Q19 38 / 49 mV |
| **R6** floating GND (re-review `gfloat.py`) | 427.6 mm² in 20 pieces | **63.6 mm² in 4** (v0.10: 232 mm²) |
| **R9** holes in or overlapping pads ≤ 1.3 mm | 11 | 9 (C43.1 and J11.S1 cleared) |
| MVDD islands per layer, ESC1–4 | 1/1 each | 1/1 each |
| M6 VBATT/MVDD/phase to outline, non-GND to corner holes | 0.53 mm, 3.50 mm | unchanged |
| DRC (parity, all severities) | 0 / 0 / 0, 493 warnings | 0 / 0 / 0, 476 warnings (isolated copper 20 → 4, dangling via 1 → 0) |
| `tools/check_netlist.py` | 0 errors, 0 warnings, 5 J1 pins | same |

What changed:
- **R1:** the ESC2 `FD6288_VB3` via is back at (181.38, 116.26), 0.45/0.25, and its two 1.65 mm stubs are gone (only the tented land brushes D11.1, as before M4).
  The J6 pin 3 GND via moved 0.40 mm east to (183.15, 119.25), 0.34 mm hole-to-hole from its neighbour.
  The `MVDD_ESC2` outline gets a pocket (x 179.2–181.0, y 117.7–119.5) so B.Cu fills the free space west of the strip.
  F.Cu is now set by J6.3's pad and the F.Cu `LO1` track at x = 180.4; moving `LO1` to In3 would slot the In3 VBATT strip, so it stays.
- **R6:** 11 GND vias, each at least 0.2 mm from other-net copper on all six layers and 0.1 mm from every pad: rear corners (186.26, 137.15) and (105.06, 137.05); (121.96, 77.25), (109.86, 106.85), (156.66, 88.55), (159.86, 123.15) at 0.6/0.3; (114.36, 64.65), (154.26, 82.75), (159.26, 105.25), (119.56, 117.35), (122.05, 106.7) at 0.45/0.25.
  The 4 pieces left (15–17 mm² each) are between the rear motor pads, where no via fits (0.28 mm free).
- **R9:** C43.1's via moved to (165.43, 91.85) between C43 and C45 (B.Cu stub, In2 track straightened).
  The J11.S1 tab via moved to (114.15, 108.6), still in the B.Cu GND piece it joins; the In2 piece it also grounded has its own via at (122.05, 106.7).
- **R3:** the J7.5 tab GND via at (101.60, 124.31), in line with the MVDD via column and the HO1 track, is removed; J7.4/J7.5 now join the J7.3 GND via (103.74, 121.15) with a 0.3 mm F.Cu track.
  That via also anchored a GND fill down the left edge on F.Cu, so the F.Cu VBATT pour is back there (1.2–2.5 mm wide, y 116–125). The ESC3 capacitor GND pads keep their own vias.
  The ESC3 `HO1` In3 track was not moved: the B.Cu route the re-review suggested runs into Q21's drain pad and the ESC3 MVDD bottom copper, and other inner routes cross the strip again or are longer.
- **N2:** the dangling `+5.2V` via at (124.85, 73.95) is deleted.

Still open from the re-review (not done here):
- **R2** vias under U3.13, U3.15, U12.9: decision pending.
- **R4** other MVDD corners: ESC3 0.70 mm F.Cu / 1.48 mm B.Cu, ESC1 and ESC4 0.52 mm F.Cu (carried by their 3.2–4.2 mm B.Cu). The 0.25 mm MVDD/VBATT zone-clearance option needs its own DRC pass.
- **R5** MVDD current concentrated in a few vias (max 3.7–4.0 A per via in this model): add vias near the shunts if wanted.
- **R7** about 9–10 W of VBATT copper loss at 4 × 20 A: no further change asked for.
- **R8** GND plane openings round the XT90 and the via blocks; **R10** five close drill pairs; **N1** longer gate runs; **N3** LED supply resistance; **N8** the 0.002 mm VBATT zone joint at (183.25, 135.0) on In2 (both zones are joined elsewhere).
- Remaining small-pad vias: U12.9, U3.13, U3.15 (R2), U20.2, C42.2 (edge), J16.4 ×2, J16.5, J9.S2.

Scripts: `scripts/r1_vb3_back.py`, `scripts/r1_mvdd_pocket.py`, `scripts/r6_gnd_vias.py` (check, then `add`), plus `near.py`, `obs.py` and `spot.py` for looking up copper and free via spots; `analysis/strip_rr.py` measures the left strip with the re-review's `cu.py`.
Renders in `review/v0.11-shrink2/` and `fab/v0.11-wip/JapanDrones_BasicCarrier.step` are refreshed.
