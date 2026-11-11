# Working on this repository

Guidance for coding agents (Codex, Claude Code, Cursor, Gemini CLI, Copilot, …) and
humans changing this repo. To *use* the skill, see README.md.

## Layout

- `skills/3d-modeling/` is the product: `SKILL.md`, `references/`, `scripts/`,
  `templates/`. It must stay self-contained (no imports from outside the folder),
  because installers copy only this folder.
- `examples/` are runnable demonstrations; `docs/images/` are their previews.
- Manifests, one per ecosystem, all pointing at the same `skills/` folder:
  - `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (Claude Code)
  - `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` (Codex)
  - `gemini-extension.json` (Gemini CLI)
  - `install.sh` copies or links the skill into any agent's skill folder.

## Rules

- Keep `SKILL.md` short and agent-neutral (no product-specific tool names in the core
  workflow); put detail in `references/`.
- Scripts: Python 3.10+, standard library + trimesh/numpy/matplotlib only; every script
  has `--help`, works headless, and exits non-zero on hard failures.
- Anything you claim works must be exercised by `tests/run_examples.sh`; mark untested
  material as untested in the text.
- Bump `version` in all three manifests together (`tests/validate_repo.py` checks this).

## Checks

```bash
pip install -r requirements.txt
python tests/validate_repo.py      # manifests, versions, SKILL.md frontmatter, links
tests/run_examples.sh              # builds and inspects every example
tests/run_examples.sh --with-blender   # when bpy or Blender is available
```
