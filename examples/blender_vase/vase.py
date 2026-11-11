"""Blender build script template (bpy). Runs three ways, unchanged:

  1. Headless:     blender -b -P blender_build.py -- --out ./out --name vase
  2. bpy module:   python blender_build.py --out ./out          (pip install bpy; Python version must match)
  3. Live Blender: paste into the Scripting tab, or send through an MCP tool such as
                   mcp-for-blender's execute_blender_code (set OUT_DIR below first).

Convention: 1 Blender unit = 1 mm (scene unit scale 0.001), Z up, object rests on Z=0.
STL/OBJ/3MF consumers read the numbers as mm. glTF/GLB expects metres: the GLB export below
is scaled by 0.001 so it opens at the right size in web viewers and game engines.

Replace build() with the model. Keep everything parametric in PARAMS.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy  # must come before bmesh when running as the bpy module
import bmesh  # noqa: E402

PARAMS = {
    "height": 120.0,
    "base_r": 30.0,
    "belly_r": 45.0,
    "neck_r": 18.0,
    "lip_r": 24.0,
    "wall": 2.0,
    "segments": 96,
    "twist_lobes": 6,       # decorative ripples around the body
    "ripple": 2.5,          # ripple depth, mm
}
OUT_DIR = None  # set when running inside a live Blender session
NAME = "vase"
FORMATS = ("stl", "obj", "glb", "blend")


# ---------------------------------------------------------------- scene setup
def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 0.001
    s.unit_settings.length_unit = "MILLIMETERS"


def profile_radius(t: float, p: dict) -> float:
    """Radius along the height, t in [0, 1]: smooth base -> belly -> neck -> flared lip."""
    keys = [(0.0, p["base_r"]), (0.35, p["belly_r"]), (0.78, p["neck_r"]), (1.0, p["lip_r"])]
    for (t0, r0), (t1, r1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)  # smoothstep
            return r0 + (r1 - r0) * u
    return keys[-1][1]


# ---------------------------------------------------------------- the model
def build(p: dict) -> bpy.types.Object:
    rings = 64
    seg = int(p["segments"])
    bm = bmesh.new()
    grid = []
    for i in range(rings + 1):
        t = i / rings
        z = t * p["height"]
        r = profile_radius(t, p)
        row = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            rr = r + p["ripple"] * math.sin(p["twist_lobes"] * a + 3.0 * t) * math.sin(math.pi * t)
            row.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        grid.append(row)
    for i in range(rings):
        for j in range(seg):
            k = (j + 1) % seg
            bm.faces.new((grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]))
    bottom = bm.verts.new((0, 0, 0))
    for j in range(seg):  # closed floor
        bm.faces.new((grid[0][(j + 1) % seg], grid[0][j], bottom))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(NAME, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # open shell -> solid wall; thickness grows inward so the outer size stays as specified
    sol = obj.modifiers.new("wall", "SOLIDIFY")
    sol.thickness = p["wall"]
    sol.offset = -1.0
    sol.use_even_offset = True
    sub = obj.modifiers.new("smooth", "SUBSURF")
    sub.levels = sub.render_levels = 1
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


# ---------------------------------------------------------------- finishing
def finalize(obj: bpy.types.Object) -> None:
    """Apply modifiers, rest on Z=0, report size. Exports need real geometry."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    min_z = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    obj.location.z -= min_z
    d = obj.dimensions
    print(f"[build] {obj.name}: {d.x:.2f} x {d.y:.2f} x {d.z:.2f} mm, {len(obj.data.polygons)} faces")


def export(obj: bpy.types.Object, out_dir: Path, name: str, formats=FORMATS) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    written = []
    if "stl" in formats:
        path = out_dir / f"{name}.stl"
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, global_scale=1.0,
                              use_scene_unit=False, ascii_format=False)
        written.append(path)
    if "obj" in formats:
        path = out_dir / f"{name}.obj"
        bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True, global_scale=1.0,
                              forward_axis="Y", up_axis="Z", export_materials=False)
        written.append(path)
    if "glb" in formats:
        path = out_dir / f"{name}.glb"
        obj.scale = (0.001,) * 3  # mm -> m for glTF
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True)
        obj.scale = (1.0,) * 3
        written.append(path)
    if "blend" in formats:
        path = out_dir / f"{name}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        written.append(path)
    return written


def cli_args() -> dict:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    opts = {"out": OUT_DIR, "name": NAME, "set": []}
    i = 0
    while i < len(argv):
        if argv[i] in ("--out", "--name") and i + 1 < len(argv):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        elif argv[i] == "--set":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                opts["set"].append(argv[i])
                i += 1
        else:
            i += 1
    return opts


def main() -> None:
    opts = cli_args()
    params = dict(PARAMS)
    for item in opts["set"]:
        k, _, v = item.partition("=")
        if k not in PARAMS:
            raise SystemExit(f"unknown parameter {k!r}; known: {', '.join(PARAMS)}")
        params[k] = type(PARAMS[k])(v)
    reset_scene()
    obj = build(params)
    finalize(obj)
    out = Path(opts["out"] or Path.cwd() / "out")
    for f in export(obj, out, opts["name"]):
        print(f"[build] wrote {f}")


if __name__ == "__main__":
    main()
