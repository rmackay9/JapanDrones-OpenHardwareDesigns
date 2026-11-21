# JapanDrones BasicCarrier

Carrier board for a CubePilot Cube (DF17 connectors) used on the JapanDrones aerial photography copter.

- KiCad 10 project: `JapanDrones_BasicCarrierBoard_v0.10.kicad_pro` (file names kept from v0.10 because KiCad stores the project name inside each schematic's symbol instances; the board revision is the `rev` field in the title block).
- `fab/<version>/`: the exact Gerbers, BOM, positions and schematic PDF sent to the fab for that release.
- Releases are git tags (`v0.10` = as built by PCBWay, Sep 2026).

## Known issues in v0.10 (fixed in v0.11 work)
- Battery connector wrong gender / polarity in BOM
- Fan powered from 5V instead of battery voltage
- ESC CAN_H / CAN_L swapped
- Buzzer quiet (piezo driven by low-side FET with no discharge path)

Note: custom footprints/3D models come from `${KICAD_CUSTOM}` (outside this repo); footprints are embedded in the .kicad_pcb.
