# Autodesk Fusion

Use when the user designs in Fusion and wants an editable history (sketches, features,
user parameters) rather than a dead mesh, or needs Fusion-specific output.

## Through an MCP server

Community Fusion MCP servers run an add-in inside Fusion and expose tools to create
sketches and features or to run API code. Tool names differ between servers: list the
tools you have, prefer one that runs a Python script in Fusion (most flexible), and fall
back to the specific create/extrude tools. Fusion must be open with a design active.

## Fusion API script (works without MCP)

The user can run it from **Utilities → Add-Ins → Scripts and Add-Ins → + (Create)**, or an
MCP tool can execute it. **The API's internal length unit is centimetres**; pass strings
with units (`"60 mm"`) through `ValueInput.createByString` to avoid mistakes.

```python
import adsk.core, adsk.fusion

def run(context):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    up = design.userParameters
    for name, expr in (("width", "60 mm"), ("depth", "40 mm"), ("height", "10 mm")):
        up.add(name, adsk.core.ValueInput.createByString(expr), "mm", "")

    w = up.itemByName("width").value          # .value is in cm
    d = up.itemByName("depth").value
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addCenterPointRectangle(
        adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(w / 2, d / 2, 0))

    ext = root.features.extrudeFeatures.addSimple(
        sk.profiles.item(0), adsk.core.ValueInput.createByString("height"),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    body = ext.bodies.item(0)

    em = design.exportManager
    em.execute(em.createSTEPExportOptions("/tmp/part.step"))
    stl = em.createSTLExportOptions(body, "/tmp/part.stl")
    stl.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    em.execute(stl)
```

The extrusion height stays linked to the `height` parameter. To make sketch sizes follow
parameters after the script ends, add sketch dimensions and set their
`parameter.expression` to the parameter name. Fusion is not available in CI, so this
snippet is not machine-tested: run it once and read any error Fusion shows.

Other features follow the same pattern: `filletFeatures`, `chamferFeatures`,
`holeFeatures`, `revolveFeatures`, `loftFeatures`, `shellFeatures`,
`rectangularPatternFeatures`, `combineFeatures`.

## When Fusion is not available

Model the same design in build123d (`code-cad.md`) and export STEP; Fusion imports it
as a base body. Mention that history and parameters do not transfer through STEP.
