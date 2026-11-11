#!/usr/bin/env python3
"""Inspect a mesh file and report whether it is a clean, solid model.

Usage:
  python inspect_mesh.py model.stl [--units mm] [--thickness] [--min-wall 1.2]
                         [--overhang 45] [--expect 80x25x6] [--tol 0.5]
                         [--repair out.stl] [--json]

Reports bounding box, volume, triangle count, watertightness, winding,
disconnected bodies and degenerate faces. --thickness samples local wall
thickness by ray casting (slower). --overhang reports downward-facing area steeper
than the given angle from vertical (needs support when 3D printed, as oriented).
--expect compares the bounding box with the
intended size. --repair writes a cleaned copy (merged vertices, fixed normals,
filled small holes). Exit code is 1 when a hard problem is found.

Requires: trimesh, numpy (pip install trimesh numpy)
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import trimesh


def load(path: str) -> trimesh.Trimesh:
    obj = trimesh.load(path, force="mesh")
    if not isinstance(obj, trimesh.Trimesh) or len(obj.faces) == 0:
        raise SystemExit(f"Could not read any triangles from {path}")
    # Flat-shaded and glTF exports duplicate vertices per face; weld them so that
    # watertightness and body counts describe the shape, not the shading.
    obj.merge_vertices(merge_tex=True, merge_norm=True)
    return obj


def sample_thickness(mesh: trimesh.Trimesh, samples: int = 1500) -> dict:
    points, face_idx = trimesh.sample.sample_surface(mesh, samples, seed=0)
    normals = mesh.face_normals[face_idx]
    origins = points - normals * 1e-4
    locations, ray_idx, _ = mesh.ray.intersects_location(origins, -normals, multiple_hits=False)
    if len(ray_idx) == 0:
        return {"samples": 0}
    dists = np.linalg.norm(locations - origins[ray_idx], axis=1)
    dists = dists[dists > 1e-6]
    if len(dists) == 0:
        return {"samples": 0}
    return {
        "samples": int(len(dists)),
        "min": float(dists.min()),
        "p05": float(np.percentile(dists, 5)),
        "median": float(np.median(dists)),
    }


def overhangs(mesh: trimesh.Trimesh, angle_deg: float) -> dict:
    """Downward faces whose angle from vertical exceeds angle_deg, ignoring the bed layer."""
    limit = -np.cos(np.radians(90 - angle_deg))       # e.g. 45 deg -> normal_z < -0.707
    z0 = mesh.bounds[0][2]
    centers = mesh.triangles_center[:, 2]
    bad = (mesh.face_normals[:, 2] < limit) & (centers > z0 + 0.2)
    area = float(mesh.area_faces[bad].sum())
    return {
        "angle": angle_deg,
        "area": round(area, 3),
        "percent_of_surface": round(100 * area / mesh.area, 2) if mesh.area else 0.0,
        "highest_z": round(float(centers[bad].max()), 3) if bad.any() else None,
    }


def parse_size(text: str) -> list[float]:
    parts = [float(p) for p in text.lower().replace("*", "x").split("x")]
    if len(parts) != 3:
        raise SystemExit("--expect needs three numbers, e.g. 80x25x6")
    return parts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--units", default="mm", help="label for lengths in the report (files carry no units)")
    ap.add_argument("--thickness", action="store_true", help="sample wall thickness by ray casting")
    ap.add_argument("--min-wall", type=float, default=None, help="warn when sampled thickness is below this")
    ap.add_argument("--overhang", type=float, default=None, metavar="DEG",
                    help="report overhangs steeper than DEG from vertical (FDM: 45)")
    ap.add_argument("--expect", default=None, help="intended size LxWxH, compared order-independently")
    ap.add_argument("--tol", type=float, default=0.5, help="tolerance for --expect, in file units")
    ap.add_argument("--repair", default=None, help="write a cleaned copy to this path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    mesh = load(args.path)
    u = args.units
    extents = [float(x) for x in mesh.extents]
    bodies = mesh.split(only_watertight=False)
    degenerate = int((mesh.area_faces < 1e-12).sum())

    report = {
        "file": args.path,
        "units": u,
        "triangles": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "bbox_size": [round(e, 4) for e in extents],
        "bbox_min": [round(float(v), 4) for v in mesh.bounds[0]],
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "volume": round(float(mesh.volume), 4) if mesh.is_watertight else None,
        "surface_area": round(float(mesh.area), 4),
        "bodies": len(bodies),
        "degenerate_faces": degenerate,
        "euler_number": int(mesh.euler_number),
        "problems": [],
        "warnings": [],
    }

    if not mesh.is_watertight:
        report["problems"].append("not watertight (holes or non-manifold edges): not a closed solid")
    if not mesh.is_winding_consistent:
        report["problems"].append("inconsistent face winding (flipped normals)")
    if mesh.is_watertight and mesh.volume < 0:
        report["problems"].append("negative volume: normals point inward")
    if degenerate:
        report["warnings"].append(f"{degenerate} zero-area faces")
    if len(bodies) > 1:
        report["warnings"].append(f"{len(bodies)} separate bodies (fine for multi-part output, otherwise unintended)")
    if max(extents) < 1.0:
        report["warnings"].append("model is under 1 unit across: probably exported in metres, not millimetres")
    if max(extents) > 5000:
        report["warnings"].append("model is over 5000 units across: check the export scale")

    if args.expect:
        want = sorted(parse_size(args.expect))
        got = sorted(extents)
        off = [abs(a - b) for a, b in zip(want, got)]
        report["expected_size"] = want
        if max(off) > args.tol:
            report["problems"].append(f"size {sorted(round(g, 2) for g in got)} differs from expected {want} by up to {max(off):.2f} {u}")

    if args.thickness:
        try:
            th = sample_thickness(mesh)
        except ImportError as exc:
            raise SystemExit(f"--thickness needs an extra package ({exc.name}): pip install rtree")
        report["thickness"] = th
        if args.min_wall and th.get("samples") and th["p05"] < args.min_wall:
            report["warnings"].append(
                f"thin walls: 5th percentile thickness {th['p05']:.2f} {u} < {args.min_wall} {u}")

    if args.overhang is not None:
        oh = overhangs(mesh, args.overhang)
        report["overhang"] = oh
        if oh["area"] > 0:
            report["warnings"].append(
                f"{oh['area']:.1f} {u}^2 ({oh['percent_of_surface']}% of surface) overhangs more than "
                f"{args.overhang:g} deg (highest at z={oh['highest_z']}): "
                + ("small areas such as hole roofs usually bridge; check them in a section view"
                   if oh["percent_of_surface"] < 1 else "needs support or a different orientation"))

    if args.repair:
        fixed = mesh.copy()
        fixed.merge_vertices()
        fixed.update_faces(fixed.nondegenerate_faces())
        fixed.update_faces(fixed.unique_faces())
        fixed.remove_unreferenced_vertices()
        trimesh.repair.fix_normals(fixed)
        trimesh.repair.fill_holes(fixed)
        fixed.export(args.repair)
        report["repaired"] = {"path": args.repair, "watertight": bool(fixed.is_watertight)}

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        sx, sy, sz = report["bbox_size"]
        print(f"{args.path}")
        print(f"  size      {sx:g} x {sy:g} x {sz:g} {u}")
        print(f"  triangles {report['triangles']:,}   bodies {report['bodies']}")
        print(f"  watertight {report['watertight']}   winding ok {report['winding_consistent']}")
        if report["volume"] is not None:
            print(f"  volume    {report['volume']:g} {u}^3")
        if "thickness" in report and report["thickness"].get("samples"):
            t = report["thickness"]
            print(f"  wall      min {t['min']:.2f}  p05 {t['p05']:.2f}  median {t['median']:.2f} {u}")
        if "overhang" in report:
            o = report["overhang"]
            print(f"  overhang  >{o['angle']:g} deg: {o['area']:g} {u}^2 ({o['percent_of_surface']}%)")
        if "repaired" in report:
            print(f"  repaired  -> {report['repaired']['path']} (watertight {report['repaired']['watertight']})")
        for p in report["problems"]:
            print(f"  PROBLEM: {p}")
        for w in report["warnings"]:
            print(f"  warning: {w}")
        if not report["problems"] and not report["warnings"]:
            print("  OK: clean closed solid")
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
