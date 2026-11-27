#!/usr/bin/env python3
"""Make the fab outputs for the current board revision.

The revision comes from the PCB title block (rev "vX.Y"), which is also what the
silkscreen ${REVISION} text and the schematic title blocks show. Outputs go to
fab/<rev>/ and every file name carries the revision:

  fab/<rev>/gerbers/JapanDrones_BasicCarrier_<rev>-<layer>.gbr, -PTH.drl, -NPTH.drl, drill maps, -job.gbrjob
  fab/<rev>/JapanDrones_BasicCarrier_<rev>_gerbers.zip
  fab/<rev>/JapanDrones_BasicCarrier_<rev>_schematic.pdf
  fab/<rev>/PCBWay_bom.csv, PCBWay_positions.csv  (tools/make_pcbway_fab.py, run with KiCad's python)
  fab/<rev>/PCBWay_netlist.ipc

Usage (from the board folder, KiCad closed, zones filled):
  python tools/make_fab.py [--kicad-bin "C:/Program Files/KiCad/10.0/bin"]
"""
import argparse, os, re, shutil, subprocess, sys, zipfile

NAME = "JapanDrones_BasicCarrier"
LAYERS = "F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def revision(pcb):
    with open(pcb, encoding="utf-8") as f:
        head = f.read(200000)
    m = re.search(r'\(title_block.*?\(rev "([^"]+)"\)', head, re.S)
    if not m:
        sys.exit("no (rev ...) in the PCB title block")
    return m.group(1)


def run(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kicad-bin", default=r"C:\Program Files\KiCad\10.0\bin")
    a = ap.parse_args()
    cli = shutil.which("kicad-cli") or os.path.join(a.kicad_bin, "kicad-cli.exe")
    kpy = os.path.join(a.kicad_bin, "python.exe")
    pcb, sch = os.path.join(HERE, NAME + ".kicad_pcb"), os.path.join(HERE, NAME + ".kicad_sch")
    rev = revision(pcb)
    base = f"{NAME}_{rev}"
    out = os.path.join(HERE, "fab", rev)
    gdir = os.path.join(out, "gerbers")
    if os.path.isdir(gdir):
        shutil.rmtree(gdir)
    os.makedirs(gdir)

    run([cli, "pcb", "export", "gerbers", "-o", gdir, "-l", LAYERS, "--no-protel-ext", "--subtract-soldermask", pcb])
    run([cli, "pcb", "export", "drill", "-o", gdir + os.sep, "--format", "excellon", "-u", "mm",
         "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", pcb])
    # put the revision in every file name (KiCad names them after the project) and in the job file
    for fn in sorted(os.listdir(gdir)):
        if fn.startswith(NAME + "-"):
            os.replace(os.path.join(gdir, fn), os.path.join(gdir, base + fn[len(NAME):]))
    job = os.path.join(gdir, base + "-job.gbrjob")
    if os.path.exists(job):
        with open(job, encoding="utf-8") as f:
            t = f.read()
        with open(job, "w", encoding="utf-8", newline="\n") as f:
            f.write(t.replace(f'"{NAME}-', f'"{base}-'))
    zpath = os.path.join(out, base + "_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, fn), fn)

    run([cli, "pcb", "export", "ipcd356", "-o", os.path.join(out, "PCBWay_netlist.ipc"), pcb])
    run([cli, "sch", "export", "pdf", "-o", os.path.join(out, base + "_schematic.pdf"), sch])
    run([kpy, os.path.join(HERE, "tools", "make_pcbway_fab.py"), pcb, out])
    print("revision", rev, "->", os.path.relpath(out, HERE))


if __name__ == "__main__":
    main()
