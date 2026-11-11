"""Name tag / keychain: raised text on a rounded base that follows the letter outline.

  python name_tag.py --set text=Andrea
  python name_tag.py --set text=GiGAS font_size=14 ring=False

Units: mm. Outputs STEP, STL and 3MF next to this file (or --out DIR).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from build123d import (
    Align,
    BuildPart,
    BuildSketch,
    Plane,
    Sketch,
    Circle,
    Pos,
    RectangleRounded,
    Part,
    Text,
    export_step,
    export_stl,
    extrude,
    offset,
    Kind,
)

PARAMS = {
    "text": "Andrea",
    "font": "Arial",          # any installed font name; falls back to the OCCT default if missing
    "font_size": 16.0,        # cap height-ish, mm
    "letter_height": 2.5,     # how far the letters rise above the base
    "base_height": 3.0,
    "outline": 2.5,           # base margin around the letters
    "ring": True,             # add a keyring loop on the left
    "ring_outer_d": 9.0,
    "ring_hole_d": 4.5,
}


def grow(face, amount: float):
    """Offset one glyph outline outward; retry smaller if OCCT's 2D offset fails."""
    for k in (1.0, 0.75, 0.5, 0.25):
        try:
            faces = offset(face, amount=amount * k, kind=Kind.ARC).faces()
        except Exception:
            continue
        if faces and all(f.is_valid for f in faces):  # OCCT can return self-intersecting outlines
            return faces
    return [face]


def build(p: dict) -> Part:
    """Base (grown glyphs + connecting bar + optional ring) with letters raised on top."""
    with BuildSketch() as letters_sk:
        Text(p["text"], font_size=p["font_size"], font=p["font"], align=(Align.CENTER, Align.CENTER))
    letters: Sketch = letters_sk.sketch
    bb = letters.bounding_box()
    h = p["base_height"]

    pieces = [extrude(f, amount=h) for glyph in letters.faces() for f in grow(glyph, p["outline"])]
    # a bar along the text keeps letters that do not touch in one piece
    bar_h = max(bb.size.Y * 0.45, 2 * p["outline"])
    pieces.append(extrude(Pos(bb.center().X, bb.center().Y) *
                          RectangleRounded(bb.size.X, bar_h, bar_h / 2 - 0.01), amount=h))
    ring_x = bb.min.X - p["outline"] - p["ring_outer_d"] / 2 + p["outline"]
    if p["ring"]:
        pieces.append(extrude(Pos(ring_x, bb.center().Y) * Circle(p["ring_outer_d"] / 2), amount=h))

    base = pieces[0]
    for piece in pieces[1:]:
        base = base + piece
    if p["ring"]:
        base = base - extrude(Pos(ring_x, bb.center().Y) * Circle(p["ring_hole_d"] / 2), amount=h)
    raised = extrude(Plane.XY.offset(h) * letters, amount=p["letter_height"])
    result = (base + raised).clean()
    if len(result.solids()) != 1:
        raise RuntimeError(f"tag came out as {len(result.solids())} bodies; try a larger outline or bolder font")
    return result


def export_all(part: Part, out_dir: Path, name: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [out_dir / f"{name}.step", out_dir / f"{name}.stl"]
    export_step(part, str(files[0]))
    export_stl(part, str(files[1]), tolerance=0.01, angular_tolerance=0.1)
    try:
        from build123d import Mesher

        m = Mesher()
        m.add_shape(part, linear_deflection=0.01, angular_deflection=0.1)
        m.write(str(out_dir / f"{name}.3mf"))
        files.append(out_dir / f"{name}.3mf")
    except Exception as exc:
        print(f"3MF skipped: {exc}")
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent))
    ap.add_argument("--name", default=None)
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    params = dict(PARAMS)
    for item in a.set:
        k, _, v = item.partition("=")
        if k not in PARAMS:
            raise SystemExit(f"unknown parameter {k!r}; known: {', '.join(PARAMS)}")
        params[k] = (v.lower() in ("1", "true", "yes")) if isinstance(PARAMS[k], bool) else type(PARAMS[k])(v)
    part = build(params)
    bb = part.bounding_box()
    print(f"size {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
    for f in export_all(part, Path(a.out), a.name or f"name_tag_{params['text']}"):
        print(f)
