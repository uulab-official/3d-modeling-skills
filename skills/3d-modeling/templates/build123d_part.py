"""<Part name> — parametric model (build123d).

Edit PARAMS, then run:
  python build123d_part.py                 # writes STEP + STL + 3MF next to this file
  python build123d_part.py --out out/ --set width=90 height=40

Units: millimetres. Z is up; the part sits on Z=0.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from build123d import (
    Align,
    Box,
    BuildPart,
    Cylinder,
    Locations,
    Mode,
    Part,
    export_step,
    export_stl,
    fillet,
    Axis,
)

# ---- Parameters (all mm) ---------------------------------------------------
PARAMS = {
    "width": 60.0,
    "depth": 40.0,
    "height": 12.0,
    "hole_d": 5.0,
    "edge_fillet": 2.0,
}


def build(p: dict) -> Part:
    with BuildPart() as part:
        Box(p["width"], p["depth"], p["height"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        # Round the vertical edges. Fillet before cutting features to keep edge selection simple.
        fillet(part.edges().filter_by(Axis.Z), radius=p["edge_fillet"])
        with Locations((p["width"] / 2 - 8, 0, 0), (-p["width"] / 2 + 8, 0, 0)):
            Cylinder(p["hole_d"] / 2, p["height"], align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
    return part.part


def export_all(part: Part, out_dir: Path, name: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    step, stl = out_dir / f"{name}.step", out_dir / f"{name}.stl"
    export_step(part, str(step))
    export_stl(part, str(stl), tolerance=0.01, angular_tolerance=0.1)
    files = [step, stl]
    try:  # 3MF via build123d's Mesher (needs lib3mf, bundled with build123d)
        from build123d import Mesher

        m = Mesher()
        m.add_shape(part, linear_deflection=0.01, angular_deflection=0.1)
        m.write(str(out_dir / f"{name}.3mf"))
        files.append(out_dir / f"{name}.3mf")
    except Exception as exc:  # 3MF is optional
        print(f"3MF skipped: {exc}")
    return files


def parse_overrides(items: list[str]) -> dict:
    out = {}
    for item in items:
        key, _, value = item.partition("=")
        if key not in PARAMS:
            raise SystemExit(f"unknown parameter {key!r}; known: {', '.join(PARAMS)}")
        default = PARAMS[key]
        if isinstance(default, bool):
            out[key] = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(default, int):
            out[key] = int(float(value))
        else:
            out[key] = type(default)(value)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent))
    ap.add_argument("--name", default=Path(__file__).stem)
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    params = {**PARAMS, **parse_overrides(a.set)}
    result = build(params)
    bb = result.bounding_box()
    print(f"size {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm, volume {result.volume:.1f} mm^3")
    for f in export_all(result, Path(a.out), a.name):
        print(f)
