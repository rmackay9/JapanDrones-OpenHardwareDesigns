# BasicCarrier: bring-up checklist

For the first boards of each release (written for v0.11).

Do these in order on the first board. Stop at the first failure.

## 1. Before power
- [ ] Visual / loupe on the three FD6288 pins over filled vias: **U3.13, U3.15 (ESC1) and U12.9 (ESC2)**, bottom side. Look for a full fillet on each lead; ask PCBWay for the X-ray image if they took one.
- [ ] Check the other QFNs (U2, U16, U1, U9, U13, U17) for bridges, and J1 (DF17) for bridges and coplanarity.
- [ ] Polarised parts as fitted: D1 cathode to VBATT, C112 + to VBATT, D15/D16, LEDs D3/D17/D18.
- [ ] **XT90 polarity:** with a meter, J18 + pin to VBATT (e.g. RSHUNT pad, D1 cathode), − pin to GND. Mate the battery lead once, unpowered, and confirm red goes to +.
- [ ] Resistance VBATT–GND, +10V–GND, +5.2V–GND, +3V3–GND: no shorts (VBATT will read the capacitor charge-up, then high).

## 2. First power: current-limited bench supply
- [ ] Bench supply on the XT90, **12 V, 0.2–0.3 A limit**, no Cube, no motors. Note the idle current; it should be steady (the four ESC MCUs and both bucks start).
- [ ] Rails: +10V (U5), +5.2V (U8), +3V3 (U6). Then raise to 25.2 V (6S full) and check again.
- [ ] **Buck frequency (review M3):** frequency meter or scope on the switch node, the L1 pad (10 V buck, U5) and the L2 pad (5.2 V buck, U8). Expect about **500 kHz**. If it reads about **94 kHz**, R43/R46 (200 kΩ RT) are being used: remove them (RT open = 500 kHz) or fit 31.6 kΩ before loading the rails.
- [ ] Touch / thermal camera after a few minutes: bucks, L1/L2, nothing else warm.

## 3. With the Cube
- [ ] Fit the Cube, battery power only: the Cube boots, `BRICK_VALID` (power brick OK) reads valid, battery voltage reads right.
- [ ] USB only (no battery): `VBUS_VALID` reads valid, the Cube boots from USB through U21; USB enumerates.
- [ ] Both connected: battery wins (U21 priority), unplugging USB does not reset the Cube.
- [ ] CAN: all four ESCs (STM32 + TJA1051) appear on the Cube's CAN2 bus (DroneCAN GUI or MAVLink CAN forward); flash/update each one. CAN1 on J10/J11 if used.
- [ ] RC input, serial ports, LEDs, buzzer, fan output (pack voltage on J14, see M5).

## 4. Motors
- [ ] **One motor at a time**, props off, bench supply limited to 2–3 A. Spin each motor slowly, then all four.
- [ ] Each ESC's current reading (INA180) against the bench supply's meter.
- [ ] Then the battery, props off, short runs at rising throttle. Feel for hot spots: **INA180 area** (U4, U10, U14, U18), shunts, the MVDD corners next to J6/J7, **fan port** (J14 track), XT90.
- [ ] Spin every motor on ESC1 and ESC2 under load before flying: that is the check on the three filled-via FD6288 joints.

## Open items from the v0.11 reviews (not fixed yet)
- **M2:** INA180 common-mode absolute maximum is 26 V; a full 6S pack is 25.2 V. Watch for ESC input ringing; do not use above 6S. A series-resistor/clamp or a 40 V part is the fix for the next revision.
- **M3:** buck RT resistors 200 kΩ, outside the datasheet range: measure as in step 2.
- **M5:** the fan output (J14) is unfused battery voltage on 0.3–0.4 mm tracks, and Q1 (AO3400A) is a 30 V part. Do not short the fan lead; next revision adds a fuse/PTC and a 40–60 V FET.
- Re-review leftovers that need no action now: R4/R5 (MVDD corners and via sharing), R7 (about 10 W in battery copper at 4 × 20 A; give the board airflow), R8, R10.
