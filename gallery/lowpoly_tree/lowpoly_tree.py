"""Low-poly stylised tree for a web or game scene (Blender / bpy).

Prompt: "A low-poly tree prop for a three.js scene, under 1,500 triangles, as GLB."
Assumptions: real-world scale in metres (about 3 m tall), Y-up GLB (the glTF exporter
converts from Blender's Z-up), origin at the trunk base, flat shading, two materials
(bark, leaves) so the engine can recolour them, deterministic shape from a seed.

  blender -b -P lowpoly_tree.py -- --out ./out --set seed=7 height=4
  python lowpoly_tree.py --out ./out                      # with `pip install bpy`
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import bpy  # before bmesh when running as the bpy module
import bmesh  # noqa: E402

PARAMS = {
    "seed": 3,
    "height": 3.0,          # m, trunk base to top of the crown
    "trunk_r": 0.14,
    "trunk_sides": 7,
    "crown_blobs": 5,
    "crown_r": 0.85,
    "crown_detail": 2,      # icosphere subdivisions: 1 = bare icosahedron (20 faces), 2 = 80
    "jitter": 0.12,         # random vertex displacement, fraction of blob radius
    "max_tris": 1500,
}
BARK = (0.36, 0.23, 0.14, 1.0)
LEAVES = (0.30, 0.58, 0.27, 1.0)


def material(name, rgba):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def build(p: dict) -> bpy.types.Object:
    rng = random.Random(int(p["seed"]))
    bm = bmesh.new()
    trunk_h = p["height"] * 0.45

    # trunk: tapered prism with a slight lean
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=int(p["trunk_sides"]),
                                radius1=p["trunk_r"], radius2=p["trunk_r"] * 0.6, depth=trunk_h)
    trunk_verts = ret["verts"]
    bmesh.ops.translate(bm, verts=trunk_verts, vec=(0, 0, trunk_h / 2))
    for v in trunk_verts:
        v.co.x += 0.08 * (v.co.z / trunk_h) ** 2
    trunk_faces = {f for v in trunk_verts for f in v.link_faces}

    # crown: overlapping jittered icospheres
    crown_faces = set()
    cz = trunk_h + p["crown_r"] * 0.55
    for i in range(int(p["crown_blobs"])):
        a = 2 * math.pi * i / max(int(p["crown_blobs"]) - 1, 1)
        r = p["crown_r"] * (1.0 if i == 0 else rng.uniform(0.55, 0.75))
        off = (0, 0, 0) if i == 0 else (math.cos(a) * p["crown_r"] * 0.55,
                                       math.sin(a) * p["crown_r"] * 0.55,
                                       rng.uniform(-0.15, 0.45) * p["crown_r"])
        ret = bmesh.ops.create_icosphere(bm, subdivisions=int(p["crown_detail"]), radius=r)
        for v in ret["verts"]:
            v.co.x += off[0] + rng.uniform(-1, 1) * p["jitter"] * r
            v.co.y += off[1] + rng.uniform(-1, 1) * p["jitter"] * r
            v.co.z += cz + off[2] + rng.uniform(-1, 1) * p["jitter"] * r * 0.6
        crown_faces |= {f for v in ret["verts"] for f in v.link_faces}

    # scale the whole crown so the top lands at the requested height
    top = max(v.co.z for f in crown_faces for v in f.verts)
    k = (p["height"] - trunk_h) / (top - trunk_h)
    for v in {v for f in crown_faces for v in f.verts}:
        v.co.z = trunk_h + (v.co.z - trunk_h) * k

    mesh = bpy.data.meshes.new("LowPolyTree")
    for f in trunk_faces:
        f.material_index = 0
    for f in crown_faces:
        f.material_index = 1
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material("Bark", BARK))
    mesh.materials.append(material("Leaves", LEAVES))
    for poly in mesh.polygons:
        poly.use_smooth = False                     # flat shading = low-poly look
    obj = bpy.data.objects.new("LowPolyTree", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out, sets = Path("out"), []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out = Path(argv[i + 1]); i += 2
        elif argv[i] == "--set":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                sets.append(argv[i]); i += 1
        else:
            i += 1
    p = dict(PARAMS)
    for item in sets:
        k, _, v = item.partition("=")
        if k not in PARAMS:
            raise SystemExit(f"unknown parameter {k!r}; known: {', '.join(PARAMS)}")
        p[k] = type(PARAMS[k])(float(v))

    bpy.ops.wm.read_factory_settings(use_empty=True)   # metres: game/web scale
    obj = build(p)
    tris = len(obj.data.polygons)
    d = obj.dimensions
    print(f"[tree] {d.x:.2f} x {d.y:.2f} x {d.z:.2f} m, {tris} triangles")
    if tris > p["max_tris"]:
        raise SystemExit(f"{tris} triangles exceeds the {int(p['max_tris'])} budget")

    out.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out / "lowpoly_tree.glb"), export_format="GLB",
                              use_selection=True, export_yup=True)
    bpy.ops.wm.stl_export(filepath=str(out / "lowpoly_tree_preview.stl"), export_selected_objects=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "lowpoly_tree.blend"))
    print(f"[tree] wrote {out / 'lowpoly_tree.glb'}")


if __name__ == "__main__":
    main()
