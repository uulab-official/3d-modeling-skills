# Code CAD (build123d, CadQuery, OpenSCAD)

Exact, parametric solids (B-rep). Exports STEP for CAD hand-off and STL/3MF meshes.
Default library: **build123d** (`pip install build123d`, Python 3.10+, ships OCCT, no GUI).
CadQuery uses the same kernel; OpenSCAD is fine when the user already uses it.

## build123d essentials

Two styles; both are fine, do not mix them in one function.

**Builder mode** (context managers, good for step-by-step features):

```python
from build123d import *

with BuildPart() as part:
    Box(60, 40, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))     # sits on Z=0
    fillet(part.edges().filter_by(Axis.Z), radius=3)                  # round vertical edges
    with Locations(part.faces().sort_by(Axis.Z).last):                 # work on the top face
        with GridLocations(40, 20, 2, 2):
            Hole(radius=1.6)                                           # through holes
result = part.part
```

**Algebra mode** (plain objects and operators, good for combining parts):

```python
base = Box(60, 40, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
peg = Pos(0, 0, 10) * Cylinder(5, 15, align=(Align.CENTER, Align.CENTER, Align.MIN))
result = base + peg - Pos(0, 0, 5) * Box(70, 4, 4)       # union, then cut a slot
```

Placement: `Pos(x, y, z) * shape`, `Rot(rx, ry, rz) * shape`, `Plane.XY.offset(z) * sketch`,
`shape.moved(Location((x, y, z)))`, `shape.rotate(Axis.Z, deg)`.

### Common operations

| Need | build123d |
|---|---|
| 2D profile → solid | `extrude(sketch, amount=h)`; `revolve(sketch, Axis.Z)`; `loft([s1, s2])`; `sweep(profile, path=line)` |
| Hollow out (shell) | `offset(solid, amount=-wall, openings=solid.faces().sort_by(Axis.Z).last)` |
| Grow / shrink an outline | `offset(sketch, amount=2, kind=Kind.ARC)` |
| Rounds / bevels | `fillet(edges, radius)`, `chamfer(edges, length)` |
| Patterns | `GridLocations`, `PolarLocations(r, count)`, `HexLocations` |
| Holes | `Hole`, `CounterBoreHole`, `CounterSinkHole` (builder mode, on a face location) |
| Text | `Text("Hi", font_size=12, font="Arial")` in a `BuildSketch`, then extrude |
| Mirror | `mirror(about=Plane.YZ)` |
| Cut in half (section view, split print) | `split(bisect_by=Plane.XZ)` |
| Lines/arcs | `BuildLine` with `Line`, `Polyline`, `ThreePointArc`, `RadiusArc`, `Spline`, then `make_face()` |

**Constant cross-sections** (channels, rails, keyholes, gaskets, extrusions): sketch the
profile once on the plane it lives in and extrude it through, instead of stacking
boxes. On `Plane.XZ` the sketch's (x, y) are world (x, z); on `Plane.YZ` they are
world (y, z). `extrude(..., both=True)` goes both ways from the plane.

```python
with BuildSketch(Plane.XZ) as profile:              # keyhole: round seat + throat + 45° lead-in
    with Locations((x, cz)):
        Circle(seat_r)
    Polygon((x - t, cz), (x + t, cz), (x + t, H - lead), (x + t + lead, H + 0.01),
            (x - t - lead, H + 0.01), (x - t, H - lead), align=None)
part -= extrude(profile.sketch, amount=depth / 2 + 1, both=True)
```

**Turned shapes** (lamp shades, vases, knobs, bottles): draw one (r, z) outline on
`Plane.XZ` and `revolve(axis=Axis.Z)`. Prefer a cubic `Bezier(p0, c1, c2, p3)` over a
`Spline` through many points: its two handles set the start and end angles exactly and
it cannot wiggle. Hollow it with the kernel, not a hand-made inner curve, which tends to
overshoot and leave slivers:

```python
outer = revolve(profile_face, axis=Axis.Z)
shell = offset(outer, amount=-wall, openings=outer.faces().sort_by(Axis.Z)[0])  # open bottom
```

Check the profile numerically: for a dome the slope must get flatter steadily towards
the top, otherwise it kinks (`gallery/table_lamp`, `check_profile`). Do not end a
revolved curve exactly on the axis: the pole meshes badly; stop 0.5 mm short and close
with a tiny flat. Only if the part will be printed rim-down, add an overhang limit and
a flat top (the lamp's `printable=1`).

Joining thin features to a curved wall (spokes, ribs, tabs): make them too long and
intersect them with the wall solid offset inward by half the wall thickness
(`spoke & offset(outer, -wall/2)`). Ends that merely touch a surface leave slivers.

Openings in a wall: `Plane.YZ.offset(x_wall) * Pos(y, z) * SlotOverall(w, h)` then
`extrude(..., amount=wall + 2)` (see `gallery/enclosure`).

Selecting geometry: `part.edges().filter_by(Axis.Z)` (vertical edges),
`part.faces().sort_by(Axis.Z).last` (top face), `.group_by(Axis.Z)[-1]` (all top-most
items), `part.edges().filter_by(GeomType.CIRCLE)`.

### Export

```python
export_step(result, "part.step")
export_stl(result, "part.stl", tolerance=0.01, angular_tolerance=0.1)   # finer = smoother, larger
m = Mesher(); m.add_shape(result); m.write("part.3mf")                   # 3MF
export_gltf(result, "part.glb", binary=True)                            # web / game preview
```

Report `result.bounding_box().size` and `result.volume` after building.

### Pitfalls

- Fillet before cutting features into the edges you fillet, and keep the radius below
  half of the smallest adjacent face. On failure try a smaller radius or `max_fillet()`.
- Inside a nested `BuildPart`, `outer.edges()` still selects the outer builder's edges.
  Build each rounded body as its own part and combine with `+`/`-` instead
  (see `examples/box_with_lid`).
- `Text` uses system fonts; a missing font silently falls back to the default. Name a
  font that exists on the machine or pass `font_path=`.
- 2D `offset` of text or complex outlines can fail or return an invalid
  (self-intersecting) face, and overlapping offset faces are not merged. Offset each
  glyph separately, check `face.is_valid`, retry with a smaller amount, extrude the
  pieces and fuse them in 3D; finally assert `len(result.solids()) == 1`
  (see `examples/name_tag`).
- Coplanar booleans can leave slivers: make cutting tools overshoot by 0.5–1 mm.
- Very small features (<0.05 mm) and huge sizes slow the kernel; work in mm.

## CadQuery equivalent

```python
import cadquery as cq
r = (cq.Workplane("XY").box(60, 40, 10).edges("|Z").fillet(3)
     .faces(">Z").workplane().rarray(40, 20, 2, 2).hole(3.2))
cq.exporters.export(r, "part.step"); cq.exporters.export(r, "part.stl")
```

## OpenSCAD

Write a `.scad` file with parameters at the top, then
`openscad -o part.stl part.scad -D 'width=80'`. Use `$fn=96` for smooth curves,
`minkowski()` sparingly (slow). There is no STEP export.

## Assemblies and fits

- Model each part separately in its printing/working orientation; place copies for an
  assembly only to check: `(part_a & part_b).volume` must be 0 for parts that must not
  collide. Fail the script when it is not (`raise SystemExit`).
- Snap fits: a rod-shaped bump on one part and a slightly larger groove on the other,
  at the same height in the assembled position; engagement = bump protrusion - fit gap
  (0.2–0.4 mm for PLA). See `gallery/enclosure`.
- Export `Compound([a, b])` as STEP for the user to inspect in a CAD viewer, and render
  both parts together with a section: `render_views.py base.stl lid_seated.stl --section x=0`.

## Verifying features

External views hide things (a standoff behind a wall looks "missing"). Before saying a
feature is there or not:
- cut it open: `render_views.py part.stl --section z=4` (top view of a slice),
- or count it in code, e.g. `len(part.faces().filter_by(GeomType.CYLINDER))`, and
  assert the expected number in the script.
