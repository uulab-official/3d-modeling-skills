#!/usr/bin/env python3
"""Static checks: manifests parse, versions agree, skill frontmatter is valid,
files referenced from SKILL.md exist, and the skill folder is self-contained."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "3d-modeling"
errors: list[str] = []


def load(rel: str) -> dict:
    try:
        return json.loads((ROOT / rel).read_text())
    except Exception as exc:
        errors.append(f"{rel}: {exc}")
        return {}


claude = load(".claude-plugin/plugin.json")
claude_mkt = load(".claude-plugin/marketplace.json")
codex = load(".codex-plugin/plugin.json")
codex_mkt = load(".agents/plugins/marketplace.json")
gemini = load("gemini-extension.json")

versions = {k: v.get("version") for k, v in
            {"claude": claude, "codex": codex, "gemini": gemini}.items()}
if len(set(versions.values())) != 1:
    errors.append(f"versions differ: {versions}")
names = {claude.get("name"), codex.get("name"), gemini.get("name")}
if names != {"3d-modeling"}:
    errors.append(f"plugin names differ: {names}")
if codex.get("skills") not in ("./skills/", "./skills"):
    errors.append("codex plugin.json must point skills at ./skills/")
for rel in ("composerIcon", "logo"):
    path = codex.get("interface", {}).get(rel)
    if path and not (ROOT / path).exists():
        errors.append(f"codex interface.{rel} missing: {path}")
if not any(p.get("name") == "3d-modeling" for p in claude_mkt.get("plugins", [])):
    errors.append("claude marketplace does not list 3d-modeling")
entry = next((p for p in codex_mkt.get("plugins", []) if p.get("name") == "3d-modeling"), None)
if not entry or entry.get("source", {}).get("source") not in ("local", "git", "npm"):
    errors.append("codex marketplace entry for 3d-modeling missing or invalid source")

skill_md = (SKILL_DIR / "SKILL.md").read_text()
m = re.match(r"^---\n(.*?)\n---\n", skill_md, re.S)
if not m:
    errors.append("SKILL.md has no frontmatter")
else:
    fm = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    name = fm.get("name", "").strip()
    desc = fm.get("description", "").strip()
    if name != SKILL_DIR.name or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        errors.append(f"SKILL.md name {name!r} must match folder and be lowercase-hyphen")
    if not 20 <= len(desc) <= 1024:
        errors.append(f"SKILL.md description length {len(desc)} not in 20..1024")
    if "<" in desc or ">" in desc:
        errors.append("SKILL.md description must not contain angle brackets")

for rel in sorted(set(re.findall(r"`((?:scripts|references|templates)/[\w./-]+)`", skill_md))):
    if not (SKILL_DIR / rel).exists():
        errors.append(f"SKILL.md references missing file: {rel}")
for rel in sorted(set(re.findall(r"`(examples/[\w-]+)`", skill_md))):
    if not (ROOT / rel).exists():
        errors.append(f"SKILL.md references missing example: {rel}")

for py in SKILL_DIR.rglob("*.py"):
    if re.search(r"^\s*(from|import)\s+(examples|tests)\b", py.read_text(), re.M):
        errors.append(f"{py.relative_to(ROOT)} imports from outside the skill folder")

if errors:
    print("\n".join(f"FAIL {e}" for e in errors))
    sys.exit(1)
print(f"OK  version {versions['claude']}, skill '{SKILL_DIR.name}', {len(list(SKILL_DIR.rglob('*')))} files")
