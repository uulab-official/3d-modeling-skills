# Blender (bpy)

Use for organic or procedural shapes, modifiers (solidify, subdivision, array, boolean,
remesh), scenes, materials and renders, and for cleaning up meshes from other sources.

## Three ways to run the same script

| Situation | How |
|---|---|
| A Blender MCP server is connected (e.g. **mcp-for-blender**, formerly `blender-mcp`) | Send code with its `execute_blender_code` tool; inspect with `get_scene_info`; see it with `look` (renders views of the live scene). Work in small steps and print what you need. |
| Blender is installed, no MCP | `blender -b -P script.py -- --out ./out` (headless). macOS binary: `/Applications/Blender.app/Contents/MacOS/Blender`. |
| Nothing installed | `pip install bpy` gives Blender as a Python module (the wheel targets one Python version; check `pip index versions bpy`). Import `bpy` before `bmesh`. |

`templates/blender_build.py` works in all three. Keep its structure:
`reset_scene()` → `build(PARAMS)` → `finalize()` (apply modifiers, rest on Z=0) → `export()`.

### Setting up mcp-for-blender (for the user)

`uvx mcp-for-blender setup` configures supported MCP clients and installs the Blender
add-on; then in Blender open the sidebar (N) → BlenderMCP → Connect. It has an opt-in
telemetry prompt; tell the user rather than choosing for them. Its `generate_3d`,
`search_assets` and `import_asset` tools cover AI generation and asset libraries
(see `ai-generation.md`).

## Units and orientation

Set 1 Blender unit = 1 mm when the output is physical:

```python
s = bpy.context.scene
s.unit_settings.system = "METRIC"
s.unit_settings.scale_length = 0.001
s.unit_settings.length_unit = "MILLIMETERS"
```

Then type sizes in mm directly. STL/OBJ exporters write raw units (`global_scale=1`,
`use_scene_unit=False`) so files read as mm. glTF/GLB is metres and Y-up: scale by 0.001
for GLB (the exporter converts the axis). For render-only scenes keep the default metres.

## Patterns

```python
import bpy, bmesh  # bpy first

# primitive with exact size
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 10))
cube = bpy.context.active_object
cube.scale = (60, 40, 20); bpy.ops.object.transform_apply(scale=True)

# modifiers: add, then apply before export
m = cube.modifiers.new("bevel", "BEVEL"); m.width = 2; m.segments = 4
bpy.ops.object.modifier_apply(modifier=m.name)

# boolean (EXACT solver is robust on closed meshes)
b = obj.modifiers.new("cut", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = cutter; b.solver = "EXACT"
bpy.ops.object.modifier_apply(modifier=b.name); bpy.data.objects.remove(cutter)

# open surface -> printable solid
s = obj.modifiers.new("wall", "SOLIDIFY"); s.thickness = 2; s.offset = -1; s.use_even_offset = True

# make any messy mesh watertight (loses sharp detail below voxel size)
r = obj.modifiers.new("remesh", "REMESH"); r.mode = "VOXEL"; r.voxel_size = 0.4

# cleanup
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.01); bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")

# text
bpy.ops.object.text_add(); t = bpy.context.active_object
t.data.body = "Hello"; t.data.size = 12; t.data.extrude = 1.5
bpy.ops.object.convert(target="MESH")
```

Build geometry directly with `bmesh` for procedural shapes (see the vase in the template):
create vertices from a formula, connect faces, `bmesh.ops.recalc_face_normals`, then
`bm.to_mesh(mesh)`.

## Export

```python
bpy.ops.wm.stl_export(filepath="x.stl", export_selected_objects=True)       # Blender 4.2+
bpy.ops.wm.obj_export(filepath="x.obj", export_selected_objects=True)
bpy.ops.export_scene.gltf(filepath="x.glb", export_format="GLB", use_selection=True)
bpy.ops.export_scene.fbx(filepath="x.fbx", use_selection=True)               # game engines
bpy.ops.wm.save_as_mainfile(filepath="x.blend")
```

Blender before 4.2 used `bpy.ops.export_mesh.stl`; check `bpy.app.version` if a call
is missing. Blender has no STEP export; model in code CAD when STEP is required.

## Checking

Print `obj.dimensions` and face count after each step. Export and run
`scripts/inspect_mesh.py` and `scripts/render_views.py`, or call the MCP's `look` tool.
Non-manifold geometry shows up as "not watertight": apply all modifiers, merge by
distance, recalc normals, and as a last resort voxel-remesh.
