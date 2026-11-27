# JapanDrones BasicCarrier

Carrier board for a CubePilot Cube (DF17 connectors) used on the JapanDrones aerial photography copter.

- KiCad 10 project: `JapanDrones_BasicCarrier.kicad_pro` (version-free name; the board revision is the `rev` field in the title block, shown on the silkscreen through `${REVISION}`).
- `fab/<version>/`: the exact Gerbers, BOM, positions and schematic PDF sent to the fab for that release.
- `tools/make_fab.py` makes `fab/<rev>/` for the revision in the title block (Gerbers, drill, zip, BOM, positions, IPC netlist, schematic PDF).
- Releases are git tags (`v0.10` = as built by PCBWay, Sep 2026).

## Known issues in v0.10 (fixed in v0.11 work)
- Battery connector wrong gender / polarity in BOM
- Fan powered from 5V instead of battery voltage
- ESC CAN_H / CAN_L swapped
- Buzzer quiet (piezo driven by low-side FET with no discharge path)

No external libraries are needed: every symbol and footprint is embedded in the schematic and PCB, the project libraries (`JapanDrones.kicad_sym`, `JapanDrones.pretty`) are referenced with `${KIPRJMOD}`, and the 3D models are KiCad 10 stock models (`${KICAD10_3DMODEL_DIR}`) or generated placeholders in `3dmodels/`.
