---
name: 3d-modeling
description: Create 3D models from a description, sketch or reference image and deliver real files (STEP, STL, 3MF, OBJ, GLB, .blend). Use for any request to model, design, sculpt, generate or modify a 3D object, part, enclosure, prop, character, keychain, product or scene, whether the result is for 3D printing, CAD, rendering, the web or a game engine. Chooses between parametric code CAD (build123d/CadQuery), Blender scripting, Autodesk Fusion and AI mesh generation (Meshy, Tripo, Hyper3D), then validates and previews the result before handing it over.
---

# 3D Modeling

Turn a request into a finished, checked 3D file. The model is code or a recorded
procedure whenever possible, so it can be re-run with new dimensions.

Paths such as `scripts/…` and `references/…` are relative to this skill's folder
(the folder containing this file); resolve them before running. Write the user's
model files in their working directory, not inside the skill folder. These
instructions work in any agent that can run shell commands and Python.

## Workflow

1. **Pin down the spec** (ask only what you cannot reasonably assume):
   - Purpose: 3D print, CAD hand-off, render/animation, web (three.js), game engine.
     Purpose decides formats and quality rules (see `references/formats-and-qa.md`).
   - Size in real units (default mm), key dimensions, fits with other objects.
   - Look: reference image, style (mechanical, organic, low-poly, realistic).
   State the assumptions you made in one or two lines and continue.
2. **Pick the approach** with the table below. Combine them when a model has both
   precise and organic parts (e.g. CAD body + generated figurine, joined in Blender).
3. **Check the environment** once: `python scripts/check_env.py`. Use what is
   installed and what MCP tools you can see. Install a missing Python package only
   when the chosen approach needs it (`pip install build123d trimesh`).
4. **Block out, then refine.** First produce the rough volumes at the right size,
   render a preview, confirm proportions, then add detail (fillets, text, holes,
   textures). Small steps; print sizes after each step.
5. **Validate** every model you deliver; fix and repeat until clean:
   - Numbers: `python scripts/inspect_mesh.py out.stl --expect LxWxH` (watertight,
     size, bodies). Printed parts: add `--thickness --min-wall 1.2 --overhang 45`.
   - Pictures: `python scripts/render_views.py out.stl` and **look at the PNG**.
     Hollow parts: `--section x=0` (or y/z). Assemblies: pass every part file.
   - One view can hide a feature. Confirm with a section, or count it in code, before
     saying something is (or is not) there.
   - If you cannot view images, rely on the numbers, give the user the PNG and say it
     was not checked visually.
6. **Deliver**: source (script / .blend / Fusion design), the exports the purpose
   needs, the preview PNG, and a short note: size, parameters that can be changed,
   anything you assumed or could not verify.

## Choosing the approach

| The object is... | Approach | Read |
|---|---|---|
| Dimensioned: parts, brackets, enclosures, mounts, gears, furniture, architecture blocks, text plates | **Code CAD** with build123d (or CadQuery). Exact, parametric, exports STEP. Default choice. | `references/code-cad.md` |
| Organic or artistic shape you can still describe procedurally: vases, lamps, low-poly props, terrain, lattices, twisted/swept forms, scenes, materials, renders | **Blender** via Python (`bpy`): live through a Blender MCP, or headless `blender -b -P` | `references/blender.md` |
| User works in Fusion, needs an editable timeline / sketches / STEP in Fusion | **Autodesk Fusion** via its MCP or a Fusion API script | `references/fusion.md` |
| Characters, animals, statues, food, detailed realistic props that are not practical to model procedurally | **AI generation** (Meshy, Tripo, Hyper3D Rodin, Hunyuan3D), then clean up | `references/ai-generation.md` |
| Something that already exists as a free asset | Asset library search (Poly Haven, Sketchfab, Poly Pizza via Blender MCP); check the licence | `references/ai-generation.md` |

Rules of thumb:
- Model what was asked. Do not add manufacturing constraints (print orientation,
  overhang limits, supports, slicer settings) unless the stated purpose needs them;
  when it does, keep them as an option (`printable=1`), not baked into the shape.
- Prefer code CAD whenever the user gives numbers. It is the only approach where
  dimensions are exact by construction.
- Do not use AI generation for parts that must fit something; generated meshes have
  arbitrary scale and no exact dimensions.
- AI generation and some asset sources cost the user money or credits: say so and get
  a yes before the first paid call; reuse results instead of regenerating.
- If no backend is installed and the user did not ask for a specific tool, build123d
  is a `pip install` away and needs no GUI.

## Conventions

- Units mm, Z up, model resting on Z=0, centred in XY unless it is an assembly.
  Exception: render, web and game assets use metres (GLB is Y-up; the exporter converts).
- Every script starts with a `PARAMS` dict; derive everything else from it.
- Multi-part designs: one file per part in its own working orientation, plus an
  assembly (STEP or .blend) to check fit. Mating parts need clearance; see
  `references/formats-and-qa.md`.
- Name outputs after the object, not `output.stl`.
- Templates: `templates/build123d_part.py`, `templates/blender_build.py`.
  Worked examples in the repository root: `examples/` (name tag, box with lid, Blender
  vase) and `gallery/` (cable organiser, snap-fit enclosure, low-poly game tree), each
  with the prompt and the assumptions made.

## Scripts

All take `--help`. They need `trimesh numpy matplotlib` (`rtree` for `--thickness`).

| Script | Use |
|---|---|
| `scripts/check_env.py` | Which backends exist here; prints install hints |
| `scripts/inspect_mesh.py` | Size, watertight, winding, bodies, volume, `--thickness`, `--overhang`, `--expect`, `--repair` |
| `scripts/render_views.py` | Headless multi-view PNG; several files at once, `--section`, STEP/GLB input, file colours |
| `scripts/convert.py` | STL/OBJ/PLY/GLB/3MF conversion, `--scale`, `--fit`, `--z-up-from-y`, `--merge-into` |

## When things go wrong

- Boolean or fillet fails in code CAD: lower the radius, fillet before cutting, or
  build the solid from separate bodies and combine (`a + b`, `a - b`).
- Mesh not watertight: in code CAD this means a bad export tolerance or a
  self-intersection; in Blender apply modifiers, merge by distance, recalc normals,
  or use a Remesh (voxel) modifier; `inspect_mesh.py --repair` handles simple holes.
- Size off by 1000: metres vs millimetres. Check the scene unit, then `convert.py --scale`.
- Model looks wrong in the preview: fix it before delivering; describe what changed.
