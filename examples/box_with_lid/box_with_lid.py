"""Two-part box with a press-fit lid: shows multi-part output and fit clearance.

  python box_with_lid.py
  python box_with_lid.py --set inner_w=80 inner_d=50 inner_h=30 clearance=0.25

Units: mm. Writes box.step/.stl, lid.step/.stl and assembly.step (lid placed on
the box, for checking) to --out DIR. Each part is exported in its own printable
orientation, lying on Z=0.
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
    Location,
    Part,
    export_step,
    export_stl,
    fillet,
)

PARAMS = {
    "inner_w": 60.0,
    "inner_d": 40.0,
    "inner_h": 25.0,
    "wall": 2.0,
    "floor": 2.0,
    "lid_top": 2.0,
    "lip_h": 5.0,          # depth of the lid lip that slides into the box
    "lip_wall": 1.6,
    "clearance": 0.2,      # gap per side between lip and box wall
    "corner_r": 3.0,
}

CENTER_BOTTOM = (Align.CENTER, Align.CENTER, Align.MIN)


def rounded_block(w: float, d: float, h: float, r: float, z: float = 0.0) -> Part:
    """Box centred in XY, bottom at z, vertical edges rounded with radius r."""
    with BuildPart() as blk:
        Box(w, d, h, align=CENTER_BOTTOM)
        fillet(blk.edges().filter_by(Axis.Z), radius=r)
    return blk.part.moved(Location((0, 0, z)))


def make_box(p: dict) -> Part:
    ow, od = p["inner_w"] + 2 * p["wall"], p["inner_d"] + 2 * p["wall"]
    outer = rounded_block(ow, od, p["inner_h"] + p["floor"], p["corner_r"])
    cavity = rounded_block(p["inner_w"], p["inner_d"], p["inner_h"] + 1,
                           max(p["corner_r"] - p["wall"], 0.5), z=p["floor"])
    return outer - cavity


def make_lid(p: dict) -> Part:
    """Printed top-down: flat lid face on the bed, lip pointing up."""
    ow, od = p["inner_w"] + 2 * p["wall"], p["inner_d"] + 2 * p["wall"]
    lw, ld = p["inner_w"] - 2 * p["clearance"], p["inner_d"] - 2 * p["clearance"]
    lip_r = max(p["corner_r"] - p["wall"] - p["clearance"], 0.5)
    plate = rounded_block(ow, od, p["lid_top"], p["corner_r"])
    lip = rounded_block(lw, ld, p["lip_h"], lip_r, z=p["lid_top"])
    lip_hole = rounded_block(lw - 2 * p["lip_wall"], ld - 2 * p["lip_wall"], p["lip_h"] + 1,
                             max(lip_r - p["lip_wall"], 0.3), z=p["lid_top"])
    return plate + (lip - lip_hole)


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
        p[k] = float(v)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    box, lid = make_box(p), make_lid(p)

    # assembly for visual/fit check: flip the lid and seat it on the box
    top = p["floor"] + p["inner_h"]
    seated = lid.rotate(Axis.X, 180).moved(Location((0, 0, top + p["lid_top"])))
    overlap = (box & seated).volume
    print(f"box-lid interference volume: {overlap:.4f} mm^3 (should be 0)")

    for name, part in (("box", box), ("lid", lid)):
        export_step(part, str(out / f"{name}.step"))
        export_stl(part, str(out / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
    export_step(Compound([box, seated]), str(out / "assembly.step"))
    print(f"wrote box, lid and assembly to {out}")


if __name__ == "__main__":
    main()
