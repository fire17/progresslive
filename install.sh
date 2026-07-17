#!/bin/sh
# ProgressLive installer: skills into ~/.claude/skills (+aliases) and optional MCP registration.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.claude/skills"
for s in progresslive progresslive-runner dev-progress; do
  rm -rf "$HOME/.claude/skills/$s"; cp -R "$HERE/skills/$s" "$HOME/.claude/skills/$s"
done
for pair in plv:progresslive plr:progresslive-runner dvp:dev-progress; do
  a="${pair%%:*}"; t="${pair##*:}"
  mkdir -p "$HOME/.claude/skills/$a"; ln -sf "../$t/SKILL.md" "$HOME/.claude/skills/$a/SKILL.md"
done
echo "skills installed: /progresslive (/plv) · /progresslive-runner (/plr) · /dev-progress (/dvp)"
echo "optional global auto-track MCP:"
echo "  claude mcp add --scope user progresslive -- python3 $HERE/mcp_server.py"
echo "serve: python3 $HERE/progress.py serve --port 8177"
