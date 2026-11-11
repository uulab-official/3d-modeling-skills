#!/usr/bin/env python3
"""Report which 3D modeling backends are usable on this machine.

Usage: python check_env.py [--json]

Checks Python CAD/mesh libraries, the Blender executable, OpenSCAD, and uv/uvx
(used to run MCP servers). It never installs anything; it prints the install
command for each missing piece so the caller can decide.
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys

BLENDER_CANDIDATES = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
    r"C:\Program Files\Blender Foundation\Blender\blender.exe",
    "/usr/bin/blender",
    "/snap/bin/blender",
]

PY_LIBS = {
    "build123d": "pip install build123d",
    "cadquery": "pip install cadquery",
    "trimesh": "pip install trimesh",
    "manifold3d": "pip install manifold3d",
    "rtree": "pip install rtree  (only for inspect_mesh.py --thickness)",
    "numpy": "pip install numpy",
    "matplotlib": "pip install matplotlib",
}


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def find_exe(name: str, extra: list[str] | None = None) -> str | None:
    env_override = os.environ.get(f"{name.upper()}_PATH")
    if env_override and os.path.exists(env_override):
        return env_override
    found = shutil.which(name)
    if found:
        return found
    for path in extra or []:
        if os.path.exists(path):
            return path
    return None


def version_of(exe: str, args: list[str]) -> str | None:
    try:
        out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=30)
        text = (out.stdout or out.stderr).strip().splitlines()
        return text[0] if text else None
    except Exception:
        return None


def main() -> int:
    report: dict = {
        "platform": f"{platform.system()} {platform.machine()}",
        "python": sys.version.split()[0],
        "python_libs": {},
        "executables": {},
        "backends": {},
        "install_hints": [],
    }

    for mod, hint in PY_LIBS.items():
        ok = has_module(mod)
        report["python_libs"][mod] = ok
        if not ok:
            report["install_hints"].append(f"{mod}: {hint}")

    blender = find_exe("blender", BLENDER_CANDIDATES)
    openscad = find_exe("openscad", ["/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"])
    uvx = find_exe("uvx")
    report["executables"] = {
        "blender": {"path": blender, "version": version_of(blender, ["--version"]) if blender else None},
        "openscad": {"path": openscad, "version": version_of(openscad, ["--version"]) if openscad else None},
        "uvx": {"path": uvx},
    }

    libs = report["python_libs"]
    report["backends"] = {
        "code_cad_build123d": libs["build123d"],
        "code_cad_cadquery": libs["cadquery"],
        "openscad": bool(openscad),
        "blender_headless": bool(blender),
        "mesh_tools": libs["trimesh"],
        "preview_render": libs["trimesh"] and libs["matplotlib"],
        "mcp_for_blender_runnable": bool(uvx),
    }
    if not blender:
        report["install_hints"].append("blender: https://www.blender.org/download/ (or set BLENDER_PATH)")
    if not uvx:
        report["install_hints"].append("uv/uvx (for MCP servers): https://docs.astral.sh/uv/")

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Platform: {report['platform']}  Python {report['python']}")
    print("\nBackends:")
    for key, ok in report["backends"].items():
        print(f"  [{'x' if ok else ' '}] {key}")
    print("\nExecutables:")
    for key, info in report["executables"].items():
        print(f"  {key}: {info.get('path') or '-'} {info.get('version') or ''}".rstrip())
    if report["install_hints"]:
        print("\nMissing (install only if the task needs it):")
        for hint in report["install_hints"]:
            print(f"  - {hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
