#!/usr/bin/env bash
# Build every example and check the meshes. Usage: tests/run_examples.sh [--with-blender]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/skills/3d-modeling/scripts"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
PY="${PYTHON:-python}"

"$PY" "$S/check_env.py"

"$PY" "$ROOT/skills/3d-modeling/templates/build123d_part.py" --out "$OUT" --name template --set width=90
"$PY" "$S/inspect_mesh.py" "$OUT/template.stl" --expect 90x40x12

"$PY" "$ROOT/examples/name_tag/name_tag.py" --out "$OUT" --name tag --set text=Claude
"$PY" "$S/inspect_mesh.py" "$OUT/tag.stl" --thickness --min-wall 1.2

"$PY" "$ROOT/examples/box_with_lid/box_with_lid.py" --out "$OUT"
"$PY" "$S/inspect_mesh.py" "$OUT/box.stl" --expect 64x44x27
"$PY" "$S/inspect_mesh.py" "$OUT/lid.stl" --expect 64x44x7

"$PY" "$S/convert.py" "$OUT/box.stl" "$OUT/lid.stl" --merge-into "$OUT/both.3mf"
"$PY" "$S/render_views.py" "$OUT/tag.stl" -o "$OUT/tag.png"
test -s "$OUT/tag.png"

"$PY" "$ROOT/gallery/cable_organizer/cable_organizer.py" --out "$OUT" --set slots=4
"$PY" "$S/inspect_mesh.py" "$OUT/cable_organizer.stl" --expect 120x22x16 --overhang 45

"$PY" "$ROOT/gallery/enclosure/enclosure.py" --out "$OUT"
"$PY" "$S/inspect_mesh.py" "$OUT/enclosure_base.stl" --expect 56x36x21
"$PY" "$S/inspect_mesh.py" "$OUT/enclosure_lid.stl" --expect 56x36x6
"$PY" "$S/render_views.py" "$OUT/enclosure_base.stl" "$OUT/enclosure_lid_seated.stl" --section x=0 -o "$OUT/sec.png"
"$PY" "$S/render_views.py" "$OUT/enclosure_assembly.step" --views iso -o "$OUT/step.png"
test -s "$OUT/sec.png" && test -s "$OUT/step.png"

"$PY" "$ROOT/gallery/table_lamp/table_lamp.py" --out "$OUT"
"$PY" "$S/inspect_mesh.py" "$OUT/table_lamp_shade.stl" --expect 110x110x60
"$PY" "$S/inspect_mesh.py" "$OUT/table_lamp_base.stl" --expect 74x74x84
"$PY" "$ROOT/gallery/table_lamp/table_lamp.py" --out "$OUT/printable" --set printable=1
"$PY" "$S/inspect_mesh.py" "$OUT/printable/table_lamp_shade.stl" --overhang 60
if "$PY" "$ROOT/gallery/table_lamp/table_lamp.py" --out "$OUT/bad" --set printable=1 dome_fullness=0.8 2>/dev/null; then
  echo "expected the lamp profile check to reject printable=1 dome_fullness=0.8" >&2; exit 1
fi

if [[ "${1:-}" == "--with-blender" ]]; then
  "$PY" "$ROOT/examples/blender_vase/vase.py" --out "$OUT" --name vase
  "$PY" "$S/inspect_mesh.py" "$OUT/vase.stl" --thickness --min-wall 1.2
  "$PY" "$ROOT/gallery/lowpoly_tree/lowpoly_tree.py" --out "$OUT"
  "$PY" "$S/render_views.py" "$OUT/lowpoly_tree.glb" -o "$OUT/tree.png"
fi
echo "all examples passed"
