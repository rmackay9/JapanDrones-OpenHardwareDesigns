# JapanDrones Open Hardware Designs

Open hardware designs from [JapanDrones](https://japandrones.com) for ArduPilot based multicopters.

## Designs

| Design | Description | Status |
|---|---|---|
| [leds](leds/) | Round arm LEDs (under each motor) and a rectangular rear status LED, both 2x SK6812 RGB | Built (PCBWay, 2026) |

More designs (such as the smart battery case) will be added over time.

## Repository layout

Each design has its own folder containing:

- **KiCad source files** (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`), made with KiCad 9
- **`fab/`** manufacturing files: a zip of Gerbers + drill files, the BOM and the positions (pick and place) file
- **`3d/`** STEP model for mechanical CAD and an STL that GitHub can show in its 3D viewer
- **`docs/`** renders and photos
- **`README.md`** describing the design and how to order it

The STEP files and renders are generated from the KiCad files with [tools/export-3d.ps1](tools/export-3d.ps1) (run from the repo root on Windows with KiCad installed). STL files are converted from the STEP files.

## Licence

Hardware designs are licensed under the [CERN Open Hardware Licence Version 2 - Strongly Reciprocal](LICENSE.txt) (`CERN-OHL-S-2.0`).
Any software in this repository is licensed under the GNU General Public License v3 unless otherwise noted.

Copyright (c) 2026 JapanDrones
