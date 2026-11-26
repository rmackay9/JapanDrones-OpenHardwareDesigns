#!/usr/bin/env python3
"""Netlist sanity checker for the JapanDrones BasicCarrier board.

Catches the class of mistake that ERC/DRC cannot: nets that are "connected"
but join pins whose *functions* disagree (e.g. CAN_H to CANL, TX to TX), plus
a few electrical smells. Also prints per-connector pin tables and compares the
Cube DF17 connector (J1) against the pin-mapping spreadsheet.

Usage:
    python tools/check_netlist.py [--sch FILE.kicad_sch | --netlist FILE.xml]
                                  [--pinmap ../cubeorange-df17-pinmapping.ods]
                                  [--out report.md]

With --sch (the default is the project's root schematic) the netlist is
exported with kicad-cli first. Only the Python standard library is used.

Findings are heuristics: each one is a prompt for a human to look, and some
will be false positives. Keep the review notes (review/*.md) as the record of
which ones were checked and why they are OK.
"""
import argparse
import collections
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(HERE)
DEFAULT_SCH = os.path.join(PROJECT_DIR, "JapanDrones_BasicCarrierBoard_v0.10.kicad_sch")
DEFAULT_PINMAP = os.path.join(PROJECT_DIR, "..", "cubeorange-df17-pinmapping.ods")
CUBE_REF = "J1"

# Alternate functions of MCU pins used on this board (the symbols only carry
# the GPIO name). STM32L431KC: PA11=CAN1_RX, PA12=CAN1_TX (AF9), PB6=USART1_TX,
# PB7=USART1_RX, PA9=USART1_TX, PA10=USART1_RX, PA2=USART2_TX, PA3=USART2_RX.
PIN_HINTS = {
    "STM32L431": {"PA11": "CAN_RX", "PA12": "CAN_TX", "PB6": "USART1_TX",
                  "PB7": "USART1_RX", "PA9": "USART1_TX", "PA10": "USART1_RX",
                  "PA2": "USART2_TX", "PA3": "USART2_RX"},
}

DRIVER_TYPES = {"output", "tri_state", "power_out"}


def find_kicad_cli():
    for c in ("kicad-cli", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
              r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe"):
        if shutil.which(c) or os.path.exists(c):
            return c
    sys.exit("kicad-cli not found; pass --netlist instead")


def export_netlist(sch):
    out = os.path.join(tempfile.mkdtemp(), "netlist.xml")
    subprocess.run([find_kicad_cli(), "sch", "export", "netlist", "--format",
                    "kicadxml", "-o", out, sch], check=True, capture_output=True)
    return out


def base(net):
    return net.rsplit("/", 1)[-1]


def fn_name(pinfunction, pin):
    """KiCad writes pinfunction as NAME_PINNUMBER; strip the suffix."""
    if not pinfunction:
        return ""
    s = pinfunction
    if s.endswith("_" + pin):
        s = s[: -len(pin) - 1]
    return "" if s == pin else s


def has(rx, s):
    return bool(s) and re.search(rx, s.upper()) is not None


CAN_H = r"CAN_?H(?![A-Z])"
CAN_L = r"CAN_?L(?![A-Z])"
TX = r"(^|[^A-Z])(TXD?|U?S?ART\d*_TX)(\d*)([^A-Z]|$)"
RX = r"(^|[^A-Z])(RXD?|U?S?ART\d*_RX)(\d*)([^A-Z]|$)"
GND_NET = r"(^|[^A-Z])(GND|VSS|AGND|PGND)([^A-Z]|$)"
RAIL_NET = r"^[+-]|VBATT|VCC|VDD|VBUS|^\+?\d+V\d*$|3V3|5V2|^POW(ER)?_SEL$"
GND_PIN = r"^(GND|VSS|AGND|PGND|DGND)\d*$"


def read_ods(path):
    """Return list of rows (lists of strings) of the first sheet."""
    ns_t = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    ns_x = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    root = ET.fromstring(zipfile.ZipFile(path).read("content.xml"))
    table = next(root.iter("{%s}table" % ns_t))
    rows = []
    for row in table.iter("{%s}table-row" % ns_t):
        cells = []
        for c in row.findall("{%s}table-cell" % ns_t):
            rep = min(int(c.get("{%s}number-columns-repeated" % ns_t, "1")), 30)
            txt = " ".join("".join(p.itertext()) for p in c.findall("{%s}p" % ns_x))
            cells += [txt] * rep
        while cells and not cells[-1]:
            cells.pop()
        rows.append(cells)
    return rows


class Design:
    def __init__(self, netlist):
        root = ET.parse(netlist).getroot()
        self.comps = {}
        for c in root.find("components"):
            self.comps[c.get("ref")] = c.findtext("value") or ""
        self.nets = {}          # net name -> list of node dicts
        self.pin_net = {}       # (ref, pin) -> net name
        for n in root.find("nets"):
            nodes = []
            for nd in n:
                d = dict(ref=nd.get("ref"), pin=nd.get("pin"),
                         type=(nd.get("pintype") or "").split("+")[0],
                         nc="no_connect" in (nd.get("pintype") or ""))
                d["func"] = fn_name(nd.get("pinfunction"), d["pin"])
                d["role"] = self.role_name(d)
                nodes.append(d)
                self.pin_net[(d["ref"], d["pin"])] = n.get("name")
            self.nets[n.get("name")] = nodes
        self.pinmap = {}

    def role_name(self, d):
        """Best available description of what a pin *is*."""
        val = self.comps.get(d["ref"], "")
        for prefix, hints in PIN_HINTS.items():
            if val.startswith(prefix) and d["func"] in hints:
                return hints[d["func"]]
        return d["func"]

    def label(self, d):
        r = d["role"] or d["func"]
        if d["ref"] == CUBE_REF and d["pin"] in self.pinmap:
            r = self.pinmap[d["pin"]][0]
        return f"{d['ref']}.{d['pin']}" + (f"({r})" if r else "")

    def roles(self, d):
        r = [d["role"], d["func"]]
        if d["ref"] == CUBE_REF and d["pin"] in self.pinmap:
            r.append(self.pinmap[d["pin"]][0])
        return [x for x in r if x]


def check(des):
    F = []  # (severity, rule, net, message)

    def add(sev, rule, net, msg):
        F.append((sev, rule, net, msg))

    for net, nodes in sorted(des.nets.items()):
        b = base(net)
        real = [d for d in nodes if not d["ref"].startswith("#")]
        unconnected = b.startswith("unconnected-")

        # 1. CAN polarity: every name on the net (net label, pin functions,
        #    Cube pin names) must agree on H vs L.
        hs = [x for d in real for x in des.roles(d) if has(CAN_H, x)]
        ls = [x for d in real for x in des.roles(d) if has(CAN_L, x)]
        if has(CAN_H, b):
            hs.append("net " + b)
        if has(CAN_L, b):
            ls.append("net " + b)
        if hs and ls:
            add("ERROR", "can-polarity", net,
                f"mixes CAN-H names {sorted(set(hs))} with CAN-L names {sorted(set(ls))}")

        # 2. TX/RX direction (UART and CAN logic side).
        tx = [d for d in real if any(has(TX, x) for x in des.roles(d))]
        rx = [d for d in real if any(has(RX, x) for x in des.roles(d))]
        tx_drv = [d for d in tx if d["type"] in DRIVER_TYPES | {"bidirectional"}]
        tx_in = [d for d in tx if d["type"] == "input"]
        rx_out = [d for d in rx if d["type"] in DRIVER_TYPES]
        if len(tx) >= 2 and not rx and not tx_in and len({d["ref"] for d in tx}) >= 2:
            add("ERROR", "tx-to-tx", net, "TX joined to TX: " + ", ".join(des.label(d) for d in tx))
        if len(rx) >= 2 and not tx and not rx_out and len({d["ref"] for d in rx}) >= 2:
            add("ERROR", "rx-to-rx", net, "RX joined to RX: " + ", ".join(des.label(d) for d in rx))
        if tx_in and rx and not tx_drv:
            add("ERROR", "txd-from-rx", net, "transceiver TXD fed from an RX pin: "
                + ", ".join(des.label(d) for d in tx_in + rx))
        if rx_out and tx_drv and not rx:
            add("ERROR", "rxd-into-tx", net, "transceiver RXD drives a TX pin: "
                + ", ".join(des.label(d) for d in rx_out + tx_drv))

        # 3. Power/ground pins on the wrong kind of net.
        is_gnd = has(GND_NET, b)
        is_rail = has(RAIL_NET, b) and not is_gnd
        for d in real:
            if has(GND_PIN, d["func"]) and not is_gnd:
                add("ERROR", "gnd-pin-off-gnd", net, f"{des.label(d)} is a ground pin on net {b}")
            if d["type"] == "power_in" and not (is_gnd or is_rail) and not unconnected:
                add("WARN", "power-pin-on-signal", net,
                    f"{des.label(d)} [{des.comps.get(d['ref'],'')}] is a power input on non-rail net {b}")
            if d["type"] == "power_in" and unconnected:
                add("ERROR", "power-pin-floating", net, f"{des.label(d)} power input is unconnected")

        # 4. Outputs tied straight to a rail; several drivers on one net.
        drivers = [d for d in real if d["type"] in DRIVER_TYPES]
        if is_gnd or is_rail:
            for d in drivers:
                # A regulator/mux output pin driving its own rail is expected.
                if d["type"] != "power_out" and (is_gnd or d["func"].upper() not in
                                                 ("OUT", "VOUT", "VO", "SW", "OUTPUT")):
                    add("WARN", "output-on-rail", net,
                        f"{des.label(d)} [{des.comps.get(d['ref'],'')}] output tied directly to {b}")
        elif len({d["ref"] for d in drivers}) >= 2:
            add("ERROR", "multiple-drivers", net, "several outputs drive this net: "
                + ", ".join(des.label(d) for d in drivers))

        # 5. Single-pin nets and floating inputs.
        if not unconnected and len(real) == 1:
            add("WARN", "single-pin-net", net, f"only {des.label(real[0])} is on this net")
        if unconnected:
            for d in real:
                if d["type"] == "input" and not d["nc"]:
                    add("WARN", "floating-input", net,
                        f"{des.label(d)} [{des.comps.get(d['ref'],'')}] input is unconnected")
    return F


def connector_tables(des):
    out = []
    refs = sorted((r for r in des.comps if r.startswith("J")),
                  key=lambda r: (len(r), r))
    for ref in refs:
        pins = sorted([(p, n) for (r, p), n in des.pin_net.items() if r == ref],
                      key=lambda x: (len(x[0]), x[0]))
        out.append(f"\n### {ref} — {des.comps[ref]}\n")
        out.append("| Pin | Net | Far end (active pins first) |")
        out.append("|---|---|---|")
        for p, n in pins:
            if base(n).startswith("unconnected-"):
                out.append(f"| {p} | — (NC) | |")
                continue
            others = [d for d in des.nets[n] if not (d["ref"] == ref and d["pin"] == p)
                      and not d["ref"].startswith("#")]
            active = [des.label(d) for d in others if d["type"] != "passive" or d["ref"].startswith(("J", "U"))]
            passive = [d["ref"] for d in others if not (d["type"] != "passive" or d["ref"].startswith(("J", "U")))]
            far = ", ".join(active[:8]) + (f" (+{len(active)-8} more)" if len(active) > 8 else "")
            if passive:
                far += ("; " if far else "") + "passives: " + ", ".join(sorted(set(passive))[:6]) + \
                    (" …" if len(set(passive)) > 6 else "")
            out.append(f"| {p} | {base(n)} | {far} |")
    return out


def compare_cube(des, rows):
    """Compare J1 against the DF17 pin-mapping spreadsheet."""
    out, issues = [], []
    sheet = {}
    for r in rows:
        if r and r[0].strip().isdigit():
            pin = r[0].strip()
            sheet[pin] = (r[1].strip() if len(r) > 1 else "",
                          r[2].strip() if len(r) > 2 else "",
                          r[4].strip() if len(r) > 4 else "")
    des.pinmap = {p: (v[0], v[2]) for p, v in sheet.items()}
    out.append("| J1 pin | Cube signal (sheet) | Dir | Sheet says | Board net | Far end | Check |")
    out.append("|---|---|---|---|---|---|---|")
    for pin in sorted(sheet, key=int):
        name, direction, note = sheet[pin]
        net = des.pin_net.get((CUBE_REF, pin), "")
        b = base(net)
        nc_board = (not net) or b.startswith("unconnected-")
        nc_sheet = note.upper().startswith("NC")
        far = []
        if not nc_board:
            far = [des.label(d) for d in des.nets[net] if not (d["ref"] == CUBE_REF and d["pin"] == pin)
                   and not d["ref"].startswith("#") and (d["type"] != "passive" or d["ref"].startswith(("J", "U")))]
        flag = "ok"
        if nc_sheet and not nc_board:
            flag = "BOARD CONNECTS, SHEET SAYS NC"
        elif not nc_sheet and note and nc_board:
            flag = "SHEET EXPECTS USE, BOARD NC"
        elif not nc_board:
            n1 = re.sub(r"[^A-Z0-9]", "", name.upper())
            n2 = re.sub(r"[^A-Z0-9]", "", b.upper())
            if name.upper() == "GND":
                flag = "ok" if b.upper() == "GND" else "GND PIN NOT ON GND"
            elif n1 and n2 and n1 not in n2 and n2 not in n1:
                flag = "name differs (check)"
        if flag != "ok":
            issues.append((pin, name, note, b, flag))
        out.append(f"| {pin} | {name} | {direction} | {note or '—'} | {'—' if nc_board else b} | "
                   f"{', '.join(far[:5])}{' …' if len(far) > 5 else ''} | {flag} |")
    return out, issues


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sch", default=DEFAULT_SCH)
    ap.add_argument("--netlist")
    ap.add_argument("--pinmap", default=DEFAULT_PINMAP)
    ap.add_argument("--out")
    a = ap.parse_args()
    netlist = a.netlist or export_netlist(a.sch)
    des = Design(netlist)

    rep = ["# BasicCarrier netlist check", "",
           f"Netlist: {len(des.nets)} nets, {len(des.comps)} components.", ""]
    cube_rows, cube_issues = [], []
    if a.pinmap and os.path.exists(a.pinmap):
        cube_rows, cube_issues = compare_cube(des, read_ods(a.pinmap))
    else:
        rep.append(f"(Pin-mapping sheet not found at {a.pinmap}; J1 comparison skipped.)\n")

    findings = check(des)
    rep.append("## Findings\n")
    if not findings:
        rep.append("No findings.\n")
    else:
        rep.append("| Severity | Rule | Net | Detail |")
        rep.append("|---|---|---|---|")
        for sev, rule, net, msg in sorted(findings, key=lambda f: (f[0] != "ERROR", f[1], f[2])):
            rep.append(f"| {sev} | {rule} | {base(net)} | {msg} |")
    if cube_rows:
        rep += ["", "## J1 (Cube DF17) vs cubeorange-df17-pinmapping.ods", ""]
        rep.append(f"{len(cube_issues)} pin(s) need a look.\n")
        rep += cube_rows
    rep += ["", "## Connector pin tables"] + connector_tables(des)
    text = "\n".join(rep) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    n_err = sum(1 for f in findings if f[0] == "ERROR")
    print(f"{n_err} error(s), {len(findings) - n_err} warning(s), "
          f"{len(cube_issues)} J1 pin(s) to check", file=sys.stderr)
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
