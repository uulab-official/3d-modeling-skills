"""Desk cable organiser: cables click into round channels through a narrower throat.

Prompt: "Make a desk cable organiser: 120 mm long, five slots for 6 mm cables,
         screw holes for M3."
Assumptions: cables run front-to-back (Y); 0.5 mm clearance on the cable; throat
0.8 mm narrower than the cable so it snaps in; countersunk M3 holes at both ends
for screwing onto the desk top; flat bottom prints without supports.

  python cable_organizer.py [--out DIR] [--set cable_d=5 slots=4]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Locations,
    Plane,
    Polygon,
    extrude,
    Cylinder,
    Part,
    Pos,
    Cone,
    export_step,
    export_stl,
    fillet,
)

PARAMS = {
    "length": 120.0,
    "depth": 22.0,
    "height": 16.0,
    "slots": 5,
    "cable_d": 6.0,
    "clearance": 0.5,        # added to the cable diameter for the channel
    "throat_squeeze": 0.8,   # throat is this much narrower than the cable
    "channel_z": 9.0,        # channel centre height
    "end_margin": 14.0,      # space at each end for the screws
    "screw_d": 3.4,          # M3 clearance
    "screw_head_d": 6.5,     # countersink top diameter (90°)
    "edge_r": 2.0,
    "lead_in": 1.5,          # 45° chamfer at the throat entry
}

CB = (Align.CENTER, Align.CENTER, Align.MIN)


def build(p: dict) -> Part:
    L, D, H = p["length"], p["depth"], p["height"]
    with BuildPart() as body:
        Box(L, D, H, align=CB)
        fillet(body.edges().filter_by(Axis.Z), radius=p["edge_r"])
        fillet(body.edges().group_by(Axis.Z)[-1], radius=1.0)   # soften the top edges
    part = body.part

    # One cutter: the keyhole cross-section (round seat + throat + V lead-in),
    # sketched once on the XZ plane and extruded through the whole depth.
    ch_r = (p["cable_d"] + p["clearance"]) / 2
    t = (p["cable_d"] - p["throat_squeeze"]) / 2           # half throat width
    lead = p["lead_in"]
    cz = p["channel_z"]
    usable = L - 2 * p["end_margin"]
    pitch = usable / p["slots"]
    for i in range(int(p["slots"])):
        x = -usable / 2 + pitch * (i + 0.5)
        with BuildSketch(Plane.XZ) as profile:
            with Locations((x, cz)):
                Circle(ch_r)
            Polygon((x - t, cz), (x + t, cz), (x + t, H - lead), (x + t + lead, H + 0.01),
                    (x - t - lead, H + 0.01), (x - t, H - lead), align=None)
        part = part - extrude(profile.sketch, amount=D / 2 + 1, both=True)

    for sx in (-1, 1):
        x = sx * (L / 2 - p["end_margin"] / 2)
        hole = Pos(x, 0, 0) * Cylinder(p["screw_d"] / 2, H, align=CB)
        sink_h = (p["screw_head_d"] - p["screw_d"]) / 2           # 90° countersink
        sink = Pos(x, 0, H - sink_h) * Cone(p["screw_d"] / 2, p["screw_head_d"] / 2, sink_h, align=CB)
        part = part - hole - sink
    return part


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
    part = build(p)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    export_step(part, str(out / "cable_organizer.step"))
    export_stl(part, str(out / "cable_organizer.stl"), tolerance=0.01, angular_tolerance=0.1)
    bb = part.bounding_box().size
    print(f"cable_organizer: {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f} mm, volume {part.volume:.0f} mm^3")


if __name__ == "__main__":
    main()
