# AI mesh generation and asset libraries

For characters, animals, statues, food, plants and detailed realistic props: shapes that
are impractical to describe with dimensions. Results are triangle meshes with arbitrary
scale and no exact dimensions, so never use them for parts that must fit something.

## Cost and consent

Generation services charge per call (credits or a subscription). Before the first call:
say which service, roughly what it costs the user, and get a yes. Reuse or duplicate a
result instead of generating it again; resume an unfinished job rather than restarting.

## Routes

| Route | Tools | Notes |
|---|---|---|
| **mcp-for-blender** | `generate_3d(prompt=… or image=…, provider=auto|tripo|hunyuan3d|hyper3d|meshy)`; long jobs return a handle, call again with `job=` | Imports straight into the live Blender scene, ready for cleanup there. Needs the provider enabled/keyed in the Blender add-on. |
| **Meshy MCP** (`@meshy-ai/meshy-mcp-server`, needs `MESHY_API_KEY`) | `meshy_text_to_3d` → `meshy_text_to_3d_refine`, `meshy_image_to_3d`, `meshy_multi_image_to_3d`, `meshy_get_task_status`, `meshy_download_model`, `meshy_remesh`, `meshy_resize`, `meshy_repair_printability`, `meshy_analyze_printability` | Text-to-3D is two stages: preview (shape) then refine (texture). |
| Web app by hand | Tripo, Meshy, Hyper3D Rodin, Hunyuan3D sites | When no MCP is set up: write the prompt for the user, they download GLB/OBJ, you clean it up. |
| **Asset libraries** via mcp-for-blender | `search_assets(source=polyhaven|sketchfab|polypizza, query=…)` then `import_asset` | Poly Haven is CC0; Sketchfab licences vary per model; Poly Pizza is CC0 or CC-BY (credit the author). Record the licence in the delivery note. |

## Writing the prompt

One object per call, English, concrete: subject, style, material, pose, and what to leave
out. "Chibi astronaut cat, standing, hands at sides, smooth stylised surfaces, no base,
no background". For image input use a single subject on a plain background with the
whole silhouette visible; several views of the same object improve the back side.
For a character to be rigged later, ask for an A-pose or T-pose.

## Cleanup (always)

1. **Scale**: set real size, e.g. `python scripts/convert.py in.glb out.stl --fit 80
   --z-up-from-y --drop-to-floor --center-xy` (GLB is metres, Y-up).
2. **Inspect**: `scripts/inspect_mesh.py`; generated meshes are often not watertight,
   have several shells or inverted normals.
3. **Repair**: `inspect_mesh.py --repair` for small holes; in Blender, voxel Remesh
   (0.2–0.5 mm for a figurine) then Decimate; or `meshy_repair_printability`.
4. **Thin parts** (fingers, tails, antennae): thicken or remove them if the model will be
   printed; check with `--thickness --min-wall`.
5. **Polycount**: decimate for web and games (see `formats-and-qa.md`).
6. **Combine with CAD**: export the cleaned mesh and union it with a code-CAD base in
   Blender (Boolean, EXACT), e.g. a generated figure on a parametric pedestal with a
   name plate.
