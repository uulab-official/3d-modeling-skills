"""Two-part electronics enclosure with a snap-fit lid, PCB standoffs and a USB-C opening.

Prompt: "Design a two-part box for a 50 x 30 x 15 mm board, with a snap-fit lid and a
         USB-C cutout."
Assumptions: 50 x 30 mm PCB, 1.6 mm thick, parts up to 15 mm total height; USB-C
receptacle centred on the -X short edge, sitting on the PCB; M2.5 self-tapping
screws into 3 mm standoffs; FDM clearances (0.2 mm per side lid fit).

  python enclosure.py [--out DIR] [--set board_w=60 board_d=40 usb_y=5]

Writes enclosure_base.{step,stl}, enclosure_lid.{step,stl} (each in its printing
orientation) and enclosure_assembly.step; prints the base/lid interference volume.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Compound,
    Cylinder,
    Location,
    Part,
    Plane,
    Pos,
    Rot,
    SlotOverall,
    export_step,
    export_stl,
    extrude,
    fillet,
)

PARAMS = {
    "board_w": 50.0, "board_d": 30.0, "board_h": 15.0,   # board incl. components
    "pcb_t": 1.6,
    "gap": 1.0,             # board to wall, each side
    "wall": 2.0, "floor": 2.0,
    "standoff_h": 3.0, "standoff_d": 5.0, "pilot_d": 2.2, "hole_inset": 3.5,
    "top_gap": 1.0,         # above the tallest component
    "lid_t": 2.0, "lip_h": 4.0, "lip_wall": 1.4, "fit": 0.2,
    "snap_r": 0.5, "snap_len": 20.0, "groove_r": 0.6,
    "usb_w": 10.0, "usb_h": 4.2, "usb_y": 0.0, "usb_above_pcb": 1.6,
    "vent_slots": 5, "vent_w": 2.0, "vent_len": 18.0,
    "corner_r": 3.0,
}
CB = (Align.CENTER, Align.CENTER, Align.MIN)


def rounded_block(w, d, h, r, z=0.0) -> Part:
    with BuildPart() as b:
        Box(w, d, h, align=CB)
        fillet(b.edges().filter_by(Axis.Z), radius=r)
    return b.part.moved(Location((0, 0, z)))


def dims(p: dict) -> dict:
    iw, idp = p["board_w"] + 2 * p["gap"], p["board_d"] + 2 * p["gap"]
    ih = p["standoff_h"] + p["board_h"] + p["top_gap"]
    return {"iw": iw, "id": idp, "ih": ih, "ow": iw + 2 * p["wall"], "od": idp + 2 * p["wall"],
            "top": p["floor"] + ih}


def snap_bars(length, r, y_abs, z) -> Part:
    """Two horizontal rods along X at y = +/- y_abs (used as bumps or grooves)."""
    rod = Rot(0, 90, 0) * Cylinder(r, length)
    return Pos(0, y_abs, z) * rod + Pos(0, -y_abs, z) * rod


def make_base(p: dict) -> Part:
    d = dims(p)
    base = rounded_block(d["ow"], d["od"], d["top"], p["corner_r"])
    base -= rounded_block(d["iw"], d["id"], d["ih"] + 1, max(p["corner_r"] - p["wall"], 0.5), z=p["floor"])

    hx, hy = p["board_w"] / 2 - p["hole_inset"], p["board_d"] / 2 - p["hole_inset"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            post = Pos(sx * hx, sy * hy, p["floor"] - 0.01) * Cylinder(
                p["standoff_d"] / 2, p["standoff_h"] + 0.01, align=CB)
            pilot = Pos(sx * hx, sy * hy, p["floor"] - 1) * Cylinder(
                p["pilot_d"] / 2, p["standoff_h"] + 1.01, align=CB)
            base = base + post - pilot

    # USB-C opening on the -X wall, centred on the receptacle
    usb_z = p["floor"] + p["standoff_h"] + p["pcb_t"] + p["usb_above_pcb"]
    slot = Plane.YZ.offset(-d["ow"] / 2 - 1) * Pos(p["usb_y"], usb_z) * SlotOverall(p["usb_w"], p["usb_h"])
    base -= extrude(slot, amount=p["wall"] + 2)

    # snap grooves in the long inner walls, matching the lid bumps
    base -= snap_bars(p["snap_len"], p["groove_r"], d["id"] / 2, d["top"] - p["lip_h"] / 2)
    return base


def make_lid(p: dict) -> Part:
    """Printed plate-down: lip and snap bumps point up."""
    d = dims(p)
    lw, ld = d["iw"] - 2 * p["fit"], d["id"] - 2 * p["fit"]
    lip_r = max(p["corner_r"] - p["wall"] - p["fit"], 0.5)
    lid = rounded_block(d["ow"], d["od"], p["lid_t"], p["corner_r"])
    lip = rounded_block(lw, ld, p["lip_h"], lip_r, z=p["lid_t"])
    lip -= rounded_block(lw - 2 * p["lip_wall"], ld - 2 * p["lip_wall"], p["lip_h"] + 1,
                         max(lip_r - p["lip_wall"], 0.3), z=p["lid_t"])
    lid += lip
    lid += snap_bars(p["snap_len"], p["snap_r"], ld / 2, p["lid_t"] + p["lip_h"] / 2)

    n = int(p["vent_slots"])
    pitch = p["vent_w"] * 2.5
    for i in range(n):
        y = (i - (n - 1) / 2) * pitch
        vent = Pos(0, y, -1) * SlotOverall(p["vent_len"], p["vent_w"])
        lid -= extrude(vent, amount=p["lid_t"] + 2)
    return lid


def seat(lid: Part, p: dict) -> Part:
    """Lid flipped and placed on the base, for fit checks."""
    return lid.rotate(Axis.X, 180).moved(Location((0, 0, dims(p)["top"] + p["lid_t"])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent))
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    p = dict(PARAMS)
    for item in a.set:
        k, _, v = item.partition("=")
        if k not in PARAMS:
            raise SystemExit(f"unknown parameter {k!r}; known: {', '.join(PARAMS)}")
        p[k] = type(PARAMS[k])(float(v))

    base, lid = make_base(p), make_lid(p)
    seated = seat(lid, p)
    clash = (base & seated).volume
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("enclosure_base", base), ("enclosure_lid", lid)):
        export_step(part, str(out / f"{name}.step"))
        export_stl(part, str(out / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
        s = part.bounding_box().size
        print(f"{name}: {s.X:.1f} x {s.Y:.1f} x {s.Z:.1f} mm, {len(part.solids())} solid(s)")
    export_step(Compound([base, seated]), str(out / "enclosure_assembly.step"))
    export_stl(seated, str(out / "enclosure_lid_seated.stl"), tolerance=0.01, angular_tolerance=0.1)
    print(f"base/lid interference: {clash:.4f} mm^3 (must be 0)")
    if clash > 1e-3:
        raise SystemExit("lid collides with the base")


if __name__ == "__main__":
    main()
