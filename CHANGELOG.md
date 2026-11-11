# Changelog

## 0.2.0

- Gallery: two-part table lamp (Bezier dome, trumpet base, ring + spokes, light pocket and cable path; optional `printable=1`).
- References: turned shapes (revolve + Bezier + offset), joining thin features to curved walls.
- SKILL.md: model what was asked; manufacturing constraints only when the purpose needs them, as options.

- Works across agents: Agent Skills layout for `npx skills`, Codex plugin
  (`.codex-plugin/`, `.agents/plugins/marketplace.json`), Gemini CLI extension,
  universal `install.sh`, agent-neutral SKILL.md, `AGENTS.md` for contributors.
- `render_views.py`: `--section AXIS=VALUE[:±]`, several input files, STEP and GLB input,
  file material colours, glTF Y-up.
- `inspect_mesh.py`: `--overhang DEG`; welds duplicated vertices before checks.
- Templates: int/bool `--set` parameters.
- References: profile-and-extrude pattern, wall openings, snap fits, feature verification,
  game-prop notes.
- Gallery: cable organiser, snap-fit enclosure, low-poly game tree (built by dogfooding
  the skill) and `tests/validate_repo.py`.

## 0.1.0

- First version: SKILL.md, references (code CAD, Blender, Fusion, AI generation, formats
  and QA), scripts (check_env, inspect_mesh, render_views, convert), templates, examples.
