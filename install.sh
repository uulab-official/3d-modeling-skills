#!/usr/bin/env bash
# Install the 3d-modeling skill into one or more coding agents.
#
#   ./install.sh                     # every agent found on this machine
#   ./install.sh claude codex        # only these
#   ./install.sh --project codex     # into ./.agents/skills of the current project
#   ./install.sh --link all          # symlink instead of copy (tracks this checkout)
#   ./install.sh --uninstall all
#   ./install.sh --list
#
# Remote one-liner (no clone needed):
#   curl -fsSL https://raw.githubusercontent.com/uulab-official/3d-modeling-skills/main/install.sh | bash -s -- claude codex
#
# Agents and their skill folders follow the Agent Skills convention (SKILL.md folders).
set -eo pipefail   # no -u: macOS bash 3.2 treats empty arrays as unset

SKILL="3d-modeling"
REPO="https://github.com/uulab-official/3d-modeling-skills"

# name|global dir|project dir
AGENTS="
claude|$HOME/.claude/skills|.claude/skills
codex|$HOME/.agents/skills|.agents/skills
cursor|$HOME/.cursor/skills|.agents/skills
gemini|$HOME/.gemini/skills|.agents/skills
copilot|$HOME/.copilot/skills|.agents/skills
opencode|$HOME/.config/opencode/skills|.agents/skills
windsurf|$HOME/.codeium/windsurf/skills|.windsurf/skills
agents|$HOME/.agents/skills|.agents/skills
"
# how to tell an agent is installed (dir or command)
detect() {
  case "$1" in
    claude) [ -d "$HOME/.claude" ] || command -v claude >/dev/null ;;
    codex) [ -d "$HOME/.codex" ] || command -v codex >/dev/null ;;
    cursor) [ -d "$HOME/.cursor" ] || command -v cursor >/dev/null ;;
    gemini) [ -d "$HOME/.gemini" ] || command -v gemini >/dev/null ;;
    copilot) [ -d "$HOME/.copilot" ] ;;
    opencode) [ -d "$HOME/.config/opencode" ] || command -v opencode >/dev/null ;;
    windsurf) [ -d "$HOME/.codeium/windsurf" ] ;;
    agents) [ -d "$HOME/.agents" ] ;;
    *) return 1 ;;
  esac
}

MODE=copy; SCOPE=global; ACTION=install; TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --link) MODE=link ;;
    --project) SCOPE=project ;;
    --uninstall) ACTION=uninstall ;;
    --list) ACTION=list ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) TARGETS+=("$arg") ;;
  esac
done

# locate the skill: this checkout, or a temporary clone when piped through curl
SRC=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "$(dirname "${BASH_SOURCE[0]}")/skills/$SKILL/SKILL.md" ]; then
  SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills/$SKILL"
fi
if [ -z "$SRC" ] && [ "$ACTION" = install ]; then
  [ "$MODE" = link ] && { echo "--link needs a local clone" >&2; exit 1; }
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  git clone --depth 1 -q "$REPO" "$TMP/repo"
  SRC="$TMP/repo/skills/$SKILL"
fi

row() { echo "$AGENTS" | grep "^$1|" || true; }

if [ "$ACTION" = list ]; then
  echo "$AGENTS" | while IFS='|' read -r name gdir pdir; do
    [ -z "$name" ] && continue
    state="not found"; detect "$name" && state="found"
    inst=""; [ -e "$gdir/$SKILL" ] && inst=" (installed)"
    printf "  %-9s %-10s %s%s\n" "$name" "$state" "$gdir" "$inst"
  done
  exit 0
fi

WANT_ALL=0
if [ ${#TARGETS[@]} -gt 0 ] && [ "${TARGETS[0]}" = all ]; then WANT_ALL=1; fi
if [ ${#TARGETS[@]} -eq 0 ] || [ "$WANT_ALL" = 1 ]; then
  TARGETS=()
  while IFS='|' read -r name _ _; do
    [ -z "$name" ] && continue
    if [ "$WANT_ALL" = 1 ] || detect "$name"; then TARGETS+=("$name"); fi
  done <<< "$AGENTS"
fi
[ ${#TARGETS[@]} -gt 0 ] || { echo "No supported agent found. Name one: claude codex cursor gemini copilot opencode windsurf agents" >&2; exit 1; }

done_dirs=" "
for t in "${TARGETS[@]}"; do
  r="$(row "$t")"; [ -n "$r" ] || { echo "unknown agent: $t" >&2; continue; }
  IFS='|' read -r name gdir pdir <<< "$r"
  dir="$gdir"; [ "$SCOPE" = project ] && dir="$PWD/$pdir"
  dest="$dir/$SKILL"
  case "$done_dirs" in *" $dest "*) echo "  $name: shares $dest"; continue ;; esac
  done_dirs="$done_dirs$dest "
  if [ "$ACTION" = uninstall ]; then
    if [ -e "$dest" ] || [ -L "$dest" ]; then rm -rf "$dest"; echo "  $name: removed $dest"; fi
    continue
  fi
  mkdir -p "$dir"
  rm -rf "$dest"
  if [ "$MODE" = link ]; then ln -s "$SRC" "$dest"; else cp -R "$SRC" "$dest"; fi
  echo "  $name: $MODE -> $dest"
done

if [ "$ACTION" = install ]; then
  echo
  echo "Done. Python tools the skill uses (installed on demand, or now):"
  echo "  pip install build123d trimesh numpy matplotlib rtree"
fi
