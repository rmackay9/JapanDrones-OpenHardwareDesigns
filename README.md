# JapanDrones Open Hardware Designs

Open hardware designs from [JapanDrones](https://japandrones.com) for ArduPilot based multicopters.

## Designs

| Design | Description | Status |
|---|---|---|
| [leds](leds/) | Round arm LEDs (under each motor) and a rectangular rear status LED, both 2x SK6812 RGB | Built (PCBWay, 2026) |
| [basic-carrier](basic-carrier/) | Carrier board for a CubePilot Cube with four AM32 ESCs, battery input and connectors (6 layers, 91 x 90 mm) | v0.11 pre-fab (v0.10 built by PCBWay, 2026) |

More designs (such as the smart battery case) will be added over time.

## Repository layout

Each design has its own folder containing (the BasicCarrier, a KiCad 10 design with its own review history, uses a slightly different layout described in its README):

- **KiCad source files** (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`), made with KiCad 9
- **`fab/`** manufacturing files: a zip of Gerbers + drill files, the BOM and the positions (pick and place) file
- **`3d/`** STEP model for mechanical CAD and an STL that GitHub can show in its 3D viewer
- **`docs/`** renders and photos
- **`README.md`** describing the design and how to order it

The STEP files and renders are generated from the KiCad files with [tools/export-3d.ps1](tools/export-3d.ps1) (run from the repo root on Windows with KiCad installed). STL files are converted from the STEP files.

## Licences

Each folder is under the licence below. A subfolder with its own `LICENSE` file is covered by that file, which overrides the top-level [LICENSE.txt](LICENSE.txt).

| Folder | Licence |
|---|---|
| [basic-carrier/](basic-carrier/) | GNU General Public License v3.0 ([basic-carrier/LICENSE](basic-carrier/LICENSE)), because its ESC section is derived from the [VimDrones AM32 ESC development board](https://github.com/VimDrones/AM32_esc_development_board) (GPL-3.0) |
| everything else (e.g. [leds/](leds/)) | [CERN Open Hardware Licence Version 2 - Strongly Reciprocal](LICENSE.txt) (`CERN-OHL-S-2.0`) |
| software (scripts and tools) | GNU General Public License v3, unless otherwise noted |

Copyright (c) 2026 JapanDrones
