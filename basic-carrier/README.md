# JapanDrones BasicCarrier

![BasicCarrier v0.11-dev](review/v0.11-shrink2/iso.png)

Carrier board for a CubePilot Cube (CubeOrange / CubeOrange+, DF17 80-pin connector) used on the JapanDrones aerial photography copter.
It carries the Cube and four ESCs (one per corner), so a quadcopter needs no separate ESCs or power board.

- 91.14 × 90 mm, 6 layers, 1.6 mm, parts on both sides (MOSFETs, drivers and regulators on the bottom for cooling)
- Battery in through an XT90 (bottom side, overhanging the rear edge), up to 6S
- Four AM32 ESCs on the board: STM32L431 + FD6288 gate driver + 6 × TPHR8504PL MOSFETs each, 1 mΩ shunt with INA180 current sense, DroneCAN on the Cube's CAN2 bus
- 10 V and 5.2 V buck converters, USB/battery power changeover (TPS2121) with VBUS and brick-valid flags to the Cube
- JST-GH connectors: CAN1, two serial ports, five FMU PWM outputs for LEDs, RC input, buzzer and fan (fan on battery voltage)

Designed by Swapnil Marathe for JapanDrones.

## Status

**v0.11-dev: in review, not manufactured yet.** The layout was reviewed twice by AI (`review/`) and is now with human reviewers.
The order notes and bring-up checklist for the coming release are in `docs/ORDER-NOTES.md` and `docs/BRINGUP.md`.
v0.10 was built by PCBWay in September 2026. Its known problems (battery connector gender, CAN_H/CAN_L swap, fan on 5 V, quiet buzzer) are fixed in v0.11-dev.
Open items are listed at the end of `docs/BRINGUP.md`.

## Folder map

| Path | What |
|---|---|
| `JapanDrones_BasicCarrier.kicad_pro/.kicad_sch/.kicad_pcb` | KiCad 10 project, top-level schematic and PCB |
| `Connectors.kicad_sch`, `PowerSheet.kicad_sch`, `USBSheet.kicad_sch` | Schematic sub-sheets |
| `VimDrones_mod.kicad_sch` | One ESC (used four times), derived from the VimDrones AM32 ESC development board |
| `JapanDrones_BasicCarrier.kicad_dru` | Custom DRC rules (battery copper away from the edge and the corner screws) |
| `JapanDrones.kicad_sym`, `JapanDrones.pretty/` | Project symbol and footprint libraries |
| `3dmodels/` | Generated placeholder 3D models for parts without a KiCad stock model |
| `fab/<rev>/` | Exactly what was sent to the fab for a release: Gerbers + drill zip, BOM, positions, IPC netlist, schematic PDF (`fab/v0.10/` here; later releases on their release branches) |
| `fab/v0.11-wip/` | STEP of the assembled board for mechanical CAD |
| `docs/` | PCBWay order notes, the bring-up checklist, and `cube-df17-pinmap.csv`: the Cube's 80-pin DF17 pinout (pin, name, direction and description from CubePilot's public [interface specification](https://docs.cubepilot.org/autopilot/the-cube/introduction/interface-specifications#the-cube-80-pin-df17-connector-long-term-standard)) plus how this board uses each pin |
| `tools/` | `make_fab.py` (fab outputs), `make_pcbway_fab.py` (BOM and positions), `check_netlist.py` (netlist sanity checks and the Cube DF17 pin check against `docs/cube-df17-pinmap.csv`), STEP and 3D-model helpers |
| `review/` | Design reviews of v0.11, the fixes made for them, and the scripts and renders they used |

No external libraries are needed: every symbol and footprint is embedded in the schematic and PCB, the project libraries are referenced with `${KIPRJMOD}`, and the 3D models are KiCad 10 stock models (`${KICAD10_3DMODEL_DIR}`) or the placeholders in `3dmodels/`.

## How versions work

- The **revision** lives in one place: the `rev` field of the title block. The PCB silkscreen shows it through `${REVISION}`, and `tools/make_fab.py` names every fab output after it. The KiCad file names carry no version.
- **main is always a development version**, `vX.Y-dev` (currently `v0.11-dev`): X.Y is the next release. Boards made from main say "-dev" on the silkscreen.
- **A release** is made when the board is actually ordered:
  1. Create the release branch `basic-carrier-vX.Y` from main (two numbers, like ArduPilot's release branches).
  2. On that branch, set the title-block rev to `vX.Y` on every sheet and the PCB, run `python tools/make_fab.py` to make `fab/vX.Y/`, and commit both together as the last commit of the branch.
  3. Tag that commit `basic-carrier-vX.Y.0` (annotated, three numbers, so it never clashes with the branch name). That is exactly what the fab built. Fixes for that release (a respin, a BOM change) go on the same branch, set the rev to `vX.Y.1`, and are tagged `basic-carrier-vX.Y.1`, and so on.
  4. On main, bump the rev to the next `-dev` version.
- Changes are cherry-picked between main and release branches, never merged, so history stays linear.
- **Fab files exist only on release branches** (and attached to the GitHub Release for each tag). `fab/v0.10/` and the tag `basic-carrier-v0.10.0` predate this scheme and stay on main (there is no v0.10 branch).

`tools/make_fab.py` refuses a `-dev` revision. To make Gerbers, BOM and positions from main for review, use `--dev`; it writes to a folder outside the repo (the system temp folder by default, or `--out DIR`):

```
cd basic-carrier
python tools/make_fab.py --dev
```

## Licence and attribution

This board is licensed under the **GNU General Public License v3.0** ([LICENSE](LICENSE)), not the CERN-OHL-S v2 that covers the rest of this repository.
The reason is the ESC section: `VimDrones_mod.kicad_sch` (used four times) is derived from the
[VimDrones AM32 ESC development board](https://github.com/VimDrones/AM32_esc_development_board), which VimDrones publish under GPL-3.0.
Thanks to VimDrones for releasing that design.

The [LICENSE](LICENSE) file in this folder overrides the top-level [LICENSE.txt](../LICENSE.txt) for everything under `basic-carrier/`.
