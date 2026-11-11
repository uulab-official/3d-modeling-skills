# Formats and quality checks by purpose

## Formats

| Format | Kind | Units / axis | Use for |
|---|---|---|---|
| STEP (.step/.stp) | Exact B-rep solid | mm, Z up | CAD hand-off (Fusion, SolidWorks, Onshape, FreeCAD), machining, further editing |
| STL | Triangles only | unitless (treat as mm), Z up | 3D printing, universal fallback |
| 3MF | Triangles + units, colours, multiple objects | mm, Z up | 3D printing with several parts or colours in one file |
| OBJ (+MTL) | Triangles/quads, UVs, materials | unitless | Rendering, texturing, older tools |
| GLB / glTF | Mesh, PBR materials, scene, animation | **metres, Y up** | Web (three.js, model-viewer), AR, game engines |
| FBX | Mesh, rigs, animation | varies (cm in Unreal) | Unreal, Unity, animation pipelines (export from Blender) |
| .blend | Full Blender scene | — | Source file for anything built in Blender |

Always deliver the **source** (script, .blend or Fusion design) plus the exports.

## 3D printing (any printer)

- Closed solid: `inspect_mesh.py` reports watertight, one body per part.
- Size within the build volume; flat face down; part rests on Z=0.
- Walls ≥ 2 × nozzle width for FDM (≈0.8 mm for a 0.4 mm nozzle; 1.2–2 mm is safer);
  resin ≥ 0.6 mm. Check with `--thickness --min-wall`.
- Overhangs over ~45° from vertical need support (`inspect_mesh.py --overhang 45`
  reports them for the current orientation); prefer chamfers to fillets on
  downward-facing edges; bridge spans under ~20 mm.
- Domes and shades printed rim-down: keep the wall under ~55–60° from vertical and end
  in a flat top of ≤ ~40 mm, which bridges; a fully round top needs supports inside.
  Light-diffusing walls: 0.8–1.2 mm (two perimeters).
- Holes print slightly small: add ~0.2 mm to diameters that must fit a pin or screw.
- Clearance between mating parts (per side): press fit 0.1, snug slide 0.2,
  free/loose 0.3–0.4 mm (FDM). Resin can go tighter.
- Text: raised or engraved ≥ 0.6 mm deep, stroke width ≥ 2 × nozzle; small fonts need
  bold weights.
- Split parts larger than the printer or with heavy overhangs; add pins or dovetails.
- Slicing and printer settings are outside this skill: hand the STL/3MF to the user's
  slicer or a printer integration.

## CAD hand-off

- STEP from code CAD or Fusion (Blender cannot make true STEP).
- Name parts and keep units in mm. Include the parameter list in the note.

## Rendering

- Real-world scale helps lighting and depth of field; bevel hard edges slightly
  (0.2–1 mm) so they catch highlights.
- Shade smooth with auto-smooth or weighted normals; apply materials in Blender.

## Web and games

- GLB, metres, Y up, origin at the base centre (or the pivot the engine expects).
- Polycount guide: hero prop 5–30k triangles, background prop 0.5–5k, mobile/web lower;
  decimate generated meshes.
- One material where possible, textures power-of-two (1024/2048), baked if procedural.
- Apply transforms (scale 1, rotation 0) before export.
- Flat shading duplicates vertices per face; that is normal for low-poly props.
  `inspect_mesh.py` welds them before checking, and several separate bodies (trunk +
  leaf blobs) are fine for a render-only prop.
- Use materials (or vertex colours) the engine can recolour rather than baked textures
  for simple props; `render_views.py` shows the file's material colours.

## Final review checklist

1. Preview PNG looked at, from more than one side.
2. Size matches the spec (`--expect`), units stated.
3. Watertight and single-body where expected; clearance verified for assemblies.
4. Source file and every promised export present, named after the object.
5. Note to the user: assumptions, editable parameters, anything not verified.
