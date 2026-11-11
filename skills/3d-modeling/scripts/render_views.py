#!/usr/bin/env python3
"""Render a mesh from several angles into one PNG so the model can be checked visually.

Usage:
  python render_views.py model.stl [-o preview.png] [--views iso,front,top,right]
                         [--px 700] [--title "Phone stand"] [--color 5b8cd9]
  python render_views.py box.stl lid.stl          # several files, one colour each
  python render_views.py part.step                # STEP via build123d, if installed
  python render_views.py prop.glb                 # glTF: Y-up handled, file colours used
  python render_views.py enclosure.stl --section y=0      # cut and look inside
  python render_views.py enclosure.stl --section x=12:+   # keep the +X side

--section AXIS=VALUE[:+|-] hides everything on one side of the plane and shows the
cut surface in red (works for closed meshes). Default kept side: +Y for y (front view looks into the cut), -X for x
(right view), -Z for z (top view).

Views: iso, iso_back, front, back, left, right, top, bottom.
Orthographic, Z up, front = looking along +Y. Uses a small numpy z-buffer
rasterizer with feature-edge outlines, so it works headless with no GPU,
OpenGL or Blender. Meshes above --max-faces are decimated for drawing only.

Requires: trimesh, numpy, matplotlib
"""
from __future__ import annotations

import argparse
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

# camera direction (from model toward camera) and screen-up vector, Z-up world
VIEWS = {
    "iso": ((1.0, -1.0, 0.85), (0, 0, 1)),
    "iso_back": ((-1.0, 1.0, 0.85), (0, 0, 1)),
    "front": ((0, -1, 0), (0, 0, 1)),
    "back": ((0, 1, 0), (0, 0, 1)),
    "left": ((-1, 0, 0), (0, 0, 1)),
    "right": ((1, 0, 0), (0, 0, 1)),
    "top": ((0, 0, 1), (0, 1, 0)),
    "bottom": ((0, 0, -1), (0, -1, 0)),
}


def basis(direction, up) -> np.ndarray:
    z = np.asarray(direction, float)
    z /= np.linalg.norm(z)
    x = np.cross(up, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z])


def projected_span(mesh: trimesh.Trimesh, R: np.ndarray) -> float:
    v = mesh.vertices @ R.T
    return float(max(v[:, :2].max(0) - v[:, :2].min(0)))


def rasterize(mesh: trimesh.Trimesh, R: np.ndarray, px: int, face_rgb: np.ndarray, span: float,
              clip: tuple[int, float, float] | None = None, margin=0.06) -> np.ndarray:
    """face_rgb: (F, 3) colours. span: model length that fills the view (share it across views).
    clip: (axis, value, sign) keeps points where sign * (coord - value) >= 0; back faces that
    become visible through the cut are painted as the cut surface."""
    v = mesh.vertices @ R.T
    n = mesh.face_normals @ R.T
    lo, hi = v[:, :2].min(0), v[:, :2].max(0)
    span = span or 1.0
    scale = px * (1 - 2 * margin) / span
    offset = (np.array([px, px]) - (hi - lo) * scale) / 2
    sx = (v[:, 0] - lo[0]) * scale + offset[0]
    sy = px - ((v[:, 1] - lo[1]) * scale + offset[1])
    depth = v[:, 2]

    zbuf = np.full((px, px), -np.inf)
    fid = np.full((px, px), -1, dtype=np.int64)
    tri = mesh.faces
    X, Y, Z = sx[tri], sy[tri], depth[tri]
    W = mesh.vertices[:, clip[0]][tri] if clip else None
    for i in np.argsort(-Z.mean(1)):  # front-to-back lets the depth test reject early
        xs, ys, zs = X[i], Y[i], Z[i]
        x0, x1 = max(int(xs.min()), 0), min(int(np.ceil(xs.max())), px - 1)
        y0, y1 = max(int(ys.min()), 0), min(int(np.ceil(ys.max())), px - 1)
        if x1 < x0 or y1 < y0:
            continue
        den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
        b = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
        c = 1 - a - b
        inside = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not inside.any():
            continue
        z = a * zs[0] + b * zs[1] + c * zs[2]
        if clip:
            w = a * W[i][0] + b * W[i][1] + c * W[i][2]
            inside &= clip[2] * (w - clip[1]) >= 0
        region = zbuf[y0:y1 + 1, x0:x1 + 1]
        win = inside & (z > region)
        region[win] = z[win]
        fid[y0:y1 + 1, x0:x1 + 1][win] = i

    mask = fid >= 0
    img = np.ones((px, px, 3))
    if not mask.any():
        return img
    nrm = n[fid[mask]]
    light = np.array([-0.35, 0.55, 1.0])
    light /= np.linalg.norm(light)
    lambert = np.abs(nrm @ light)  # abs: open meshes still shade both sides
    rim = 1 - np.abs(nrm[:, 2])
    k = 0.30 + 0.62 * lambert + 0.10 * rim
    img[mask] = np.clip(face_rgb[fid[mask]] * k[:, None] + 0.06, 0, 1)
    if clip:  # back faces seen through the cut = inside of the solid = section surface
        back = np.zeros((px, px), bool)
        back[mask] = nrm[:, 2] < 0
        img[back] = CAP_RGB
        nrm[back[mask]] = (0, 0, 1)

    # outlines: silhouette + creases (normal change > ~35°) + depth jumps
    full_n = np.zeros((px, px, 3))
    full_n[mask] = nrm
    zbuf = np.where(mask, zbuf, 0.0)
    edge = np.zeros((px, px), bool)
    dz_tol = span * 0.02
    for dy, dx in ((0, 1), (1, 0)):
        a_m, b_m = mask[: px - dy, : px - dx], mask[dy:, dx:]
        sil = a_m != b_m
        both = a_m & b_m
        crease = both & ((full_n[: px - dy, : px - dx] * full_n[dy:, dx:]).sum(-1) < 0.82)
        jump = both & (np.abs(zbuf[: px - dy, : px - dx] - zbuf[dy:, dx:]) > dz_tol)
        e = sil | crease | jump
        edge[: px - dy, : px - dx] |= e
    img[edge] = img[edge] * 0.25
    return img


def reduce(mesh: trimesh.Trimesh, max_faces: int) -> trimesh.Trimesh:
    if len(mesh.faces) <= max_faces:
        return mesh
    try:
        return mesh.simplify_quadric_decimation(face_count=max_faces)
    except Exception:
        print(f"note: drawing {len(mesh.faces):,} faces (pip install fast-simplification to decimate)",
              file=sys.stderr)
        return mesh


PALETTE = ["5b8cd9", "e0a040", "5fb36b", "c46ad1", "d95b5b", "4fb3c4"]
CAP_RGB = np.array([0.86, 0.30, 0.30])


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def load_any(path: str) -> tuple[trimesh.Trimesh, np.ndarray | None]:
    """Load a mesh as Z-up; also return per-face colours from the file when it has them."""
    low = path.lower()
    if low.endswith((".step", ".stp")):
        try:
            from build123d import import_step, export_stl
        except ImportError:
            raise SystemExit("STEP input needs build123d (pip install build123d)")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            stl = f"{tmp}/x.stl"
            export_stl(import_step(path), stl, tolerance=0.02, angular_tolerance=0.15)
            return trimesh.load(stl, force="mesh"), None
    loaded = trimesh.load(path)
    geoms = list(loaded.dump()) if isinstance(loaded, trimesh.Scene) else [loaded]
    meshes, colours = [], []
    for g in geoms:
        if not isinstance(g, trimesh.Trimesh) or not len(g.faces):
            continue
        rgb = None
        try:
            mat = g.visual.material
            f = getattr(mat, "baseColorFactor", None)
            if f is None and getattr(mat, "diffuse", None) is not None:
                f = mat.diffuse
            if f is not None:
                rgb = np.asarray(f, float)[:3] / (255.0 if np.max(f) > 1 else 1.0)
        except AttributeError:
            pass
        if rgb is None and getattr(g.visual, "kind", None) == "face":
            fc = np.asarray(g.visual.face_colors, float)[:, :3] / 255.0
            colours.append(fc)
        else:
            colours.append(None if rgb is None else np.tile(rgb, (len(g.faces), 1)))
        meshes.append(g)
    mesh = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
    face_rgb = None
    if any(c is not None for c in colours):
        face_rgb = np.vstack([c if c is not None else np.tile(hex_rgb(PALETTE[0]), (len(m.faces), 1))
                              for c, m in zip(colours, meshes)])
    if low.endswith((".glb", ".gltf")):  # glTF is Y-up by specification
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    return mesh, face_rgb


def parse_section(spec: str) -> tuple[int, float, float]:
    axis_txt, _, rest = spec.partition("=")
    value_txt, _, side = rest.partition(":")
    axis = "xyz".index(axis_txt.strip().lower())
    side = side or {0: "-", 1: "+", 2: "-"}[axis]
    return axis, float(value_txt), 1.0 if side == "+" else -1.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", metavar="path")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--views", default="iso,front,top,right")
    ap.add_argument("--px", type=int, default=700, help="pixels per view (square)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--color", default=None, help="hex RGB for a single file (default palette)")
    ap.add_argument("--section", default=None, metavar="AXIS=VALUE[:+|-]", help="cut away one side")
    ap.add_argument("--max-faces", type=int, default=80000)
    args = ap.parse_args()

    views = [v.strip() for v in args.views.split(",") if v.strip()]
    bad = [v for v in views if v not in VIEWS]
    if bad:
        raise SystemExit(f"unknown view(s) {bad}; choose from {list(VIEWS)}")
    loaded = [load_any(path) for path in args.paths]
    parts = [m for m, _ in loaded]
    mesh = trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0]
    full_extents = mesh.extents.copy()

    budget = max(args.max_faces // len(parts), 2000)
    drawn, colours = [], []
    for i, (part, file_rgb) in enumerate(loaded):
        rgb = hex_rgb(args.color if (args.color and len(parts) == 1) else PALETTE[i % len(PALETTE)])
        if file_rgb is not None and not args.color and len(part.faces) <= budget:
            drawn.append(part)
            colours.append(file_rgb)          # keep the model's own colours
        else:
            part = reduce(part, budget)
            drawn.append(part)
            colours.append(np.tile(rgb, (len(part.faces), 1)))
    face_rgb = np.vstack(colours)
    draw = trimesh.util.concatenate(drawn) if len(drawn) > 1 else drawn[0]
    clip = parse_section(args.section) if args.section else None

    cols = min(len(views), 2)
    rows = int(np.ceil(len(views) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * args.px / 100, rows * args.px / 100 + 0.5), dpi=100,
                             squeeze=False)
    for ax in axes.flat:
        ax.set_axis_off()
    span = max(projected_span(draw, basis(*VIEWS[name])) for name in views)
    for ax, name in zip(axes.flat, views):
        ax.imshow(rasterize(draw, basis(*VIEWS[name]), args.px, face_rgb, span, clip), interpolation="lanczos")
        ax.set_title(name, fontsize=11, color="#444")

    sx, sy, sz = full_extents
    cut = f"  ·  section {args.section}" if args.section else ""
    label = (f"{args.title + '  ·  ' if args.title else ''}X {sx:.1f} × Y {sy:.1f} × Z {sz:.1f}"
             f"  ·  {len(mesh.faces):,} tris{cut}")
    fig.suptitle(label, fontsize=12)
    fig.tight_layout()
    out = args.out or args.paths[0].rsplit(".", 1)[0] + "_preview.png"
    fig.savefig(out, facecolor="white")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
