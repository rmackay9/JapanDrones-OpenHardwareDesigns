# BasicCarrier: PCBWay order notes

What to enter on PCBWay's order form for the release being ordered (written for v0.11; update it when the design changes).
Make the files on the release branch with `tools/make_fab.py`: it takes the revision `<rev>` from the PCB title block and writes `fab/<rev>/`.
Upload from that folder.

## Files to upload

| File | What |
|---|---|
| `JapanDrones_BasicCarrier_<rev>_gerbers.zip` | 13 Gerber layers, Excellon drill (PTH and NPTH separate, mm), drill maps, Gerber job file |
| `PCBWay_bom.csv` | BOM, 59 lines, 352 placed parts (same columns idea as v0.10 plus Item/Side/Notes) |
| `PCBWay_positions.csv` | Centroids for both sides, mm, same format as v0.10 (y negated, rotation as in KiCad) |
| `PCBWay_netlist.ipc` | IPC-D-356 netlist for the electrical test |
| `JapanDrones_BasicCarrier_<rev>_schematic.pdf` | Schematic, for their engineers |

Gerber layers: F.Cu, In1.Cu, In2.Cu, In3.Cu, In4.Cu, B.Cu, F/B.Mask, F/B.Paste, F/B.Silkscreen, Edge.Cuts.

## PCB parameters (order form)

| Field | Value |
|---|---|
| Layers | **6** |
| Size | **91.14 × 90.00 mm** (single board, no panel from us) |
| Thickness | **1.6 mm** |
| Material | FR-4, TG150 or better if offered at no big cost (40 A per side of the board) |
| Copper | **1 oz (35 µm) outer, 1 oz (35 µm) inner minimum**. In2/In3 carry the battery current; do not accept 0.5 oz inner. |
| Stackup | As in the board file: F / 0.1 prepreg / In1 / 0.535 core / In2 / 0.1 prepreg / In3 / 0.535 core / In4 / 0.1 prepreg / B. No impedance control; PCBWay's standard 6-layer 1.6 mm stackup is fine. In1 and In4 are GND planes. |
| Min track / space | **0.127 mm** track (17 short segments; most are 0.2–0.25 mm), **0.152 mm (6 mil)** clearance rule |
| Min hole / via | **0.2 mm** finished hole (vias 0.40/0.20 and 0.45/0.20), 0.10 mm annular ring. Other vias 0.45/0.25, 0.6/0.3, 0.7/0.35, 0.8/0.4. Same minimums as v0.10, which PCBWay built. |
| Vias | **Via-in-pad: filled and capped (POFV, resin filled + copper capped, IPC-4761 type VII) required**, whole board. See the list below. |
| Surface finish | **ENIG recommended** (four FD6288 and four STM32 QFNs, a DF17 0.5 mm connector, capped vias need a flat finish). v0.10's photos show a silver finish (HASL); check the v0.10 order if you want to match it instead. |
| Solder mask | **Green** (as v0.10) |
| Silkscreen | **White** (as v0.10) |
| Holes in the outline | 4 × Ø3.0 mm corner holes and 4 × Ø1.8 mm Cube mounting holes are circles on Edge.Cuts: non-plated, routed or drilled by the fab |
| Electrical test | Yes (flying probe, use the IPC netlist) |

### Via-in-pad list (why POFV is needed)

Vias whose hole sits in an SMD pad. Filling and capping makes all of them flat and solder-tight.

| Pad | Net | Via (x, y mm, KiCad page) | Drill / land |
|---|---|---|---|
| **U3.13** (FD6288, ESC1) | FD6288_HO3 | 177.725, 75.800 | 0.25 / 0.45 |
| **U3.15** (FD6288, ESC1) | FD6288_VS2 | 177.500, 76.900 | 0.20 / 0.40 |
| **U12.9** (FD6288, ESC2) | FD6288_LO3 | 177.643, 112.700 | 0.20 / 0.40 |
| U20.2 (USBLC6) | GND | 160.338, 69.638 | 0.30 / 0.60 |
| C42.2 (edge of pad) | GND | 170.275, 74.750 | 0.25 / 0.45 |
| J16.4 (JST-GH tab) | GND | 134.750, 126.301 and 134.750, 128.076 | 0.30 / 0.60 |
| J16.5 (JST-GH tab) | GND | 128.900, 127.566 | 0.30 / 0.60 |
| J9.S2 (JST-GH tab) | GND | 160.750, 63.200 | 0.25 / 0.45 |

Plus (large pads, carried over from v0.10, harmless when filled): thermal vias in the exposed pads of the QFNs and HVSONs, D1 (3), RSHUNT2–5 VBATT pads, and the via groups in the four motor wire pads J2/J19/J22/J25.
The three FD6288 pins are the ones that matter: ask PCBWay to confirm they will be capped flush and to X-ray or inspect U3 and U12 after reflow.

The Gerber coordinates are KiCad page coordinates with Y negated (same as the drill files and `PCBWay_positions.csv`).

### Things PCBWay's CAM may ask about

- **Five pairs of close holes** (0.115–0.21 mm wall to wall), known since the first v0.11 review (m8, re-review R10): (125.46, 54.10)/(125.90, 54.10), (182.55, 136.00)/(182.10, 136.03), (182.55, 139.17)/(182.10, 139.12), (112.87, 124.25)/(112.84, 124.66), (125.37, 50.90)/(125.90, 50.90). If they object, allow them to merge each pair into one via.
- Battery copper is 0.5 mm from the board edge; GND only within 3.5 mm of the corner holes. That is intentional.
- 0.127 mm tracks and 0.10 mm annular rings, as above.

## Assembly (PCBA)

| Field | Value |
|---|---|
| Sides | **Double-sided**: top 100 parts, bottom 252 parts (all MOSFETs, FD6288 drivers, MCUs, bucks and the XT90 are on the bottom) |
| SMT pads | 351 SMT parts, smallest 0402 (R137, R138), finest pitch 0.5 mm (DF17, QFN-24, QFN-32) |
| Through-hole | **1 part: J18 XT90PW-M on the bottom side** (pins soldered from the top). Hand or selective solder; the + pin is tied to four copper layers and needs as much heat as the − pin. |
| Not fitted | J2, J19, J22, J25 are bare motor-wire pads (marked DNP, not in the BOM or positions) |
| Supplied by us | Nothing, unless PCBWay cannot source a line below |

Notes for the assembler:
- **XT90 (J18):** XT90PW-M30.G.Y (male). It overhangs the rear board edge (y = 140) by about **6.5 mm** (the -M body is 27.1 mm long). Do not put a V-score or break-off rail on that edge without allowing for it. Polarity: VBATT (+, the flat side of the housing) on pad P. The footprint is named `AMASS_XT90PW-F` but its pads match the -M part (review m2: only the body outline differs).
- **JST-GH** (BM02B/03B/04B/06B-GHS-TBT) and **JST-SH** (BM06B-SRSS-TB): SMT side-entry, all on the top side, with two mounting tabs each. Tabs are GND and must be soldered. JLCPCB cannot source the GH parts; PCBWay built them on v0.10.
- **J1 DF17(1.0H)-80DP-0.5V(57)**: top side, 0.5 mm pitch, two locating pegs (NPTH Ø0.65).
- **J3** RC header is an SMD 1×3 2.54 mm pin header (pin 1 on the right).
- Polarised parts to check against the silkscreen: D1 (SMCJ33A, cathode to VBATT), D2/D4–D14 (1N5819WS bootstrap diodes), D15/D16 (SS14), LEDs D3/D17/D18, C112 (electrolytic, + to VBATT), all ICs (pin 1), Y5–Y8 oscillators, 28 MOSFETs.

### BOM lines to confirm

Every placed part has an MPN. Three lines have no LCSC number, so PCBWay must source them by MPN:

| Ref | Value | MPN | Manufacturer | Note |
|---|---|---|---|---|
| R131 | 23.2 kΩ 0603 1 % | 0603WAF2322T5E | UNI-ROYAL | Any 23.2 kΩ 1 % 0603 is fine |
| C116 | 47 µF 0805 10 V X5R | GRM21BR61A476ME15L | Murata | Equivalent 47 µF ≥ 10 V 0805 X5R is fine |
| U22 | TCM809J, 4.00 V reset | TCM809JENB713 | Microchip | Must be the 4.00 V push-pull (J) version, SOT-23 |

Also check with PCBWay: J1 DF17(1.0H) (C354837), L1 MSY1040-100M-V and L2 APS1040M4R7H (recent LCSC numbers), TPHR8504PL (24 pcs), JSM6288Q (FD6288Q equivalent, 4 pcs).
`DNP` and value-only parts: none besides the motor pads.

## After ordering

Follow `BRINGUP.md` with the first boards.
