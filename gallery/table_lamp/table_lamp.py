"""Mushroom table lamp: thin dome shade on a trumpet base, modelled as two parts.

Prompt: "A small table lamp like the pastel mushroom lamps: dome shade, slim stem,
         wide foot, room for a light module and its cable."
Modelling: the shade is one cubic Bezier profile revolved and hollowed with a
constant wall; the base is a revolved trumpet; a ring with three spokes joins them;
an assembly check guarantees the parts do not collide. Separate parts mean separate
materials or colours in any renderer, CAD tool or slicer.
Assumptions: about 128 mm tall, 1 mm shade wall (translucent), light module in a pocket
at the top of the stem with a cable channel down the centre. The pocket size is a
PLACEHOLDER (led_d, led_h) until the real module is known.

  python table_lamp.py [--out DIR] [--set height=150 shade_d=120 dome_fullness=0.55]
  python table_lamp.py --set printable=1     # flat top + overhang limit for printing rim-down

Writes table_lamp_shade.{step,stl}, table_lamp_base.{step,stl} and
table_lamp_assembly.step.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Bezier,
    BuildLine,
    BuildPart,
    BuildSketch,
    Compound,
    Cylinder,
    Location,
    Part,
    Plane,
    Polyline,
    Pos,
    Rot,
    Spline,
    export_step,
    export_stl,
    make_face,
    offset,
    revolve,
)

PARAMS = {
    # overall proportions (mm)
    "height": 128.0,        # foot bottom to shade top
    "shade_d": 110.0,       # rim diameter
    "shade_h": 60.0,        # rim to dome top
    "shade_wall": 1.0,      # thin enough to glow; ~2 perimeters with a 0.4 nozzle
    "rim_flare": 3.0,       # rim kicks out this much past the dome curve
    "dome_fullness": 0.6,   # shoulder roundness (Bezier handle at the rim, fraction of height)
    "top_handle": 0.45,     # how far the dome eases into the top (fraction of radius)
    "top_flat_d": 0.0,      # 0 = smooth round top (1 mm cap); >0 = flat top of this diameter
    # optional manufacturing constraint (off by default: this is a modelling example)
    "printable": 0,         # 1 = flat top (top_flat_d or 34) and wall slope <= max_overhang
    "max_overhang": 58.0,   # deg from vertical, used only when printable=1
    "foot_d": 74.0,
    "stem_d": 24.0,
    "foot_h": 40.0,         # height of the trumpet curve before the straight stem
    "foot_edge": 3.0,       # vertical edge at the bottom of the foot
    "overlap": 16.0,        # how far the stem top reaches up inside the shade
    # shade mount
    "ring_wall": 2.4, "ring_h": 6.0, "fit": 0.25,
    "spokes": 3, "spoke_w": 2.4, "spoke_h": 2.0,
    "shoulder": 1.0,        # stem steps in by this (radius) where the ring sits
    # LED module and cable (PLACEHOLDER dimensions until the real kit is measured)
    "led_d": 16.0, "led_h": 8.0,
    "cable_d": 5.0, "exit_w": 7.0, "exit_h": 5.0,
}
CB = (Align.CENTER, Align.CENTER, Align.MIN)


def bezier_slopes(ctrl, n: int = 200) -> list[float]:
    """Slope (deg above horizontal) along a cubic Bezier given its 4 control points."""
    def at(t):
        u = 1 - t
        return [u**3 * ctrl[0][i] + 3 * u * u * t * ctrl[1][i] + 3 * u * t * t * ctrl[2][i]
                + t**3 * ctrl[3][i] for i in (0, 1)]
    pts = [at(i / n) for i in range(n + 1)]
    return [math.degrees(math.atan2(b[1] - a[1], a[0] - b[0])) for a, b in zip(pts, pts[1:])]


def check_profile(ctrl, max_overhang: float | None) -> None:
    """Shape quality: the profile must get steadily flatter towards the top (no kink).
    Printing (optional): it must not be steeper than max_overhang from vertical."""
    slopes = bezier_slopes(ctrl)
    if any(s2 > s1 + 1e-6 for s1, s2 in zip(slopes, slopes[1:])):
        raise SystemExit("shade profile kinks below the top: lower dome_fullness or raise top_handle")
    if max_overhang is not None and 90 - min(slopes) > max_overhang + 1:
        raise SystemExit(f"shade overhang reaches {90 - min(slopes):.0f} deg (printable=1)")


def make_shade(p: dict) -> Part:
    """Dome = one cubic Bezier from the rim to the top, revolved and hollowed."""
    R, H = p["shade_d"] / 2, p["shade_h"]
    printable = bool(p["printable"])
    # never end exactly on the axis: a pole tessellates badly; 0.5 mm is invisible
    rt = max(p["top_flat_d"] / 2 or (17.0 if printable else 0.0), 0.5)
    a = math.radians(90 - p["max_overhang"]) if printable else 0.0   # end slope above horizontal
    k1, k2 = H * p["dome_fullness"], (R - rt) * p["top_handle"]
    rim, top = (R, 0.0), (rt, H)
    c1 = (R - p["rim_flare"], k1)                   # leaves the rim almost vertically
    c2 = (rt + k2 * math.cos(a), H - k2 * math.sin(a))
    check_profile([rim, c1, c2, top], p["max_overhang"] if printable else None)
    closing = [top, (0.0, H), (0.0, 0.0), rim] if rt > 0 else [top, (0.0, 0.0), rim]
    with BuildPart() as solid:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Bezier(rim, c1, c2, top)
                Polyline(*closing)
            make_face()
        revolve(axis=Axis.Z)
    outer = solid.part
    # hollow with a constant wall, open at the rim
    dome = offset(outer, amount=-p["shade_wall"], openings=outer.faces().sort_by(Axis.Z)[0])

    # mounting ring + spokes in the rim plane (also lets the shade print rim-down)
    ring_ir = stem_top_r(p) + p["fit"]
    ring_or = ring_ir + p["ring_wall"]
    mount = Cylinder(ring_or, p["ring_h"], align=CB) - Cylinder(ring_ir, p["ring_h"] + 1, align=CB)
    # Spokes run long, then are trimmed to a surface halfway through the wall, so their
    # ends always sit inside the wall whatever the profile (no coincident faces).
    mid_wall = offset(outer, amount=-p["shade_wall"] / 2)
    reach = p["shade_d"] / 2 + 5
    for i in range(int(p["spokes"])):
        spoke = Rot(0, 0, 360 * i / p["spokes"] + 90) * Pos(ring_or - 0.4 + reach / 2, 0, 0) * \
            Box(reach, p["spoke_w"], p["spoke_h"], align=CB)
        mount = mount + (spoke & mid_wall)
    return dome + mount


def stem_top_r(p: dict) -> float:
    return max(p["stem_d"] / 2 - p["shoulder"], p["led_d"] / 2 + 1.6)


def make_base(p: dict) -> Part:
    rim_z = p["height"] - p["shade_h"]          # where the shade rim sits
    top_z = rim_z + p["overlap"]                # stem top, inside the shade
    Rf, Rs = p["foot_d"] / 2, p["stem_d"] / 2
    fh = p["foot_h"]
    # foot flows into the stem with a smooth concave curve
    e = p["foot_edge"]
    trumpet = [(Rf, e), (Rf * 0.80, e + fh * 0.12), (Rf * 0.55, e + fh * 0.32),
               (Rs * 0.5 + Rf * 0.18, e + fh * 0.62), (Rs, e + fh)]
    with BuildPart() as foot:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline((0.0, 0.0), (Rf, 0.0), trumpet[0])
                Spline(*trumpet, tangents=[(-0.25, 1), (0, 1)])
                Polyline(trumpet[-1], (Rs, rim_z), (0.0, rim_z), (0.0, 0.0))
            make_face()
        revolve(axis=Axis.Z)
    base = foot.part
    # narrower top section the shade ring slides over; the step is the shoulder it rests on
    top_r = stem_top_r(p)
    base += Pos(0, 0, rim_z - 0.01) * Cylinder(top_r, top_z - rim_z + 0.01, align=CB)

    # LED pocket at the top, cable channel down the middle, exit slot at the back
    base -= Pos(0, 0, top_z - p["led_h"]) * Cylinder(p["led_d"] / 2, p["led_h"] + 1, align=CB)
    base -= Pos(0, 0, -1) * Cylinder(p["cable_d"] / 2, top_z, align=CB)
    exit_slot = Pos(0, Rf / 2, -0.01) * Box(p["exit_w"], Rf + 2, p["exit_h"], align=CB)
    base -= exit_slot
    return base


def seat_shade(shade: Part, p: dict) -> Part:
    return shade.moved(Location((0, 0, p["height"] - p["shade_h"])))


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

    shade, base = make_shade(p), make_base(p)
    seated = seat_shade(shade, p)
    clash = (base & seated).volume
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("table_lamp_shade", shade), ("table_lamp_base", base)):
        export_step(part, str(out / f"{name}.step"))
        export_stl(part, str(out / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.05)
        s = part.bounding_box().size
        print(f"{name}: {s.X:.1f} x {s.Y:.1f} x {s.Z:.1f} mm, {part.volume / 1000:.1f} cm^3, "
              f"{len(part.solids())} solid(s)")
    export_step(Compound([base, seated]), str(out / "table_lamp_assembly.step"))
    export_stl(seated, str(out / "table_lamp_shade_seated.stl"), tolerance=0.01, angular_tolerance=0.05)
    print(f"shade/base interference: {clash:.4f} mm^3 (must be 0)")
    if clash > 1e-3:
        raise SystemExit("shade collides with the base")


if __name__ == "__main__":
    main()
