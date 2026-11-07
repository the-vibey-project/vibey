#!/usr/bin/env bash
set -euo pipefail

# Eve and PromptScript adapters in `npx skills` do not support --global installation.
# Using `--all` with `--global` triggers 2 failures per skill (1,640 errors across 820 skills).
# This script installs all repository and plugin skills globally to supported agent targets.

AGENTS=("claude-code" "continue" "cursor" "codex" "windsurf" "github-copilot")
AGENT_FLAGS=()
for agent in "${AGENTS[@]}"; do
  AGENT_FLAGS+=("-a" "$agent")
done

echo "Installing all vibey skills globally to supported agents (${AGENTS[*]})..."
npx -y skills add "${1:-.}" --skill '*' --global "${AGENT_FLAGS[@]}" -y
