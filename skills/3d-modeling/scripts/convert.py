#!/usr/bin/env python3
"""Convert, scale, re-orient or merge mesh files.

Usage:
  python convert.py in.obj out.stl
  python convert.py in.glb out.3mf --scale 1000          # metres -> millimetres
  python convert.py in.stl out.stl --fit 80              # longest side becomes 80
  python convert.py in.stl out.stl --z-up-from-y         # Y-up (glTF, many games) -> Z-up
  python convert.py in.stl out.stl --drop-to-floor --center-xy
  python convert.py a.stl b.stl --merge-into both.3mf    # several inputs, one file

Mesh formats: stl, obj, ply, glb/gltf, 3mf, off. STEP/IGES are CAD (B-rep)
formats: produce those from build123d/CadQuery/Fusion, not from a mesh.

Requires: trimesh, numpy (3MF also needs networkx and lxml: pip install "trimesh[easy]")
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import trimesh


def transform(mesh: trimesh.Trimesh, args) -> trimesh.Trimesh:
    if args.z_up_from_y:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    if args.scale:
        mesh.apply_scale(args.scale)
    if args.fit:
        mesh.apply_scale(args.fit / max(mesh.extents))
    if args.center_xy:
        c = mesh.bounds.mean(axis=0)
        mesh.apply_translation([-c[0], -c[1], 0])
    if args.drop_to_floor:
        mesh.apply_translation([0, 0, -mesh.bounds[0][2]])
    return mesh


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="input file(s); with one input the last positional is the output")
    ap.add_argument("--merge-into", default=None, help="combine all inputs into this output file")
    ap.add_argument("--scale", type=float, default=None)
    ap.add_argument("--fit", type=float, default=None, help="scale so the longest side equals this")
    ap.add_argument("--z-up-from-y", action="store_true")
    ap.add_argument("--center-xy", action="store_true")
    ap.add_argument("--drop-to-floor", action="store_true")
    args = ap.parse_args()

    if args.merge_into:
        sources, out = args.inputs, args.merge_into
    else:
        if len(args.inputs) != 2:
            raise SystemExit("give exactly one input and one output, or use --merge-into")
        sources, out = args.inputs[:1], args.inputs[1]

    meshes = [transform(trimesh.load(p, force="mesh"), args) for p in sources]
    if len(meshes) == 1:
        meshes[0].export(out)
    else:
        scene = trimesh.Scene()
        for path, m in zip(sources, meshes):
            scene.add_geometry(m, node_name=path.rsplit("/", 1)[-1].rsplit(".", 1)[0])
        scene.export(out)
    ext = trimesh.load(out, force="mesh").extents
    print(f"{out}  {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
