#!/bin/bash
# lane-setup.sh SLUG BASE_REF
# An isolated lane: a full clone of the main repository at BASE_REF, on branch storm/SLUG,
# with NO remote and no credential helper, so nothing a local model runs can push anywhere
# or move the operator's own branches. Hooks match the main checkout (Made-With trailer).
set -euo pipefail
SLUG="$1"; BASE="${2:-origin/develop}"
MAIN=/Users/adam/git/vibey
ROOT=/private/tmp/claude-501/storm/qwenstorm-3.0.0/lanes
LANE="$ROOT/$SLUG"
mkdir -p "$ROOT"
[ -e "$LANE" ] && { echo "exists: $LANE" >&2; exit 1; }
# BASE "lane:<slug>" stacks this lane on another lane's branch (its Part 1, say);
# anything else is a ref in the main checkout.
if [ "$BASE" = "integration" ]; then
  SRC="$ROOT/../integration"; SHA=$(git -C "$SRC" rev-parse storm/integration)
elif [[ "$BASE" == lane:* ]]; then
  SRC="$ROOT/${BASE#lane:}"; SHA=$(git -C "$SRC" rev-parse "storm/${BASE#lane:}")
else
  SRC="$MAIN"; git -C "$MAIN" fetch -q origin develop; SHA=$(git -C "$MAIN" rev-parse "$BASE")
fi
git clone -q --no-checkout "$MAIN" "$LANE"
git -C "$LANE" fetch -q "$SRC" "$SHA"
git -C "$LANE" checkout -q -b "storm/$SLUG" "$SHA"
git -C "$LANE" remote remove origin
git -C "$LANE" config credential.helper ""
git -C "$LANE" config core.hooksPath .githooks
printf '.qwenstorm/\n.venv/\n' >> "$LANE/.git/info/exclude"
(cd "$LANE" && uv sync -q --extra dev >/dev/null 2>&1) || echo "warn: uv sync failed in $LANE" >&2
echo "$LANE @ $(git -C "$LANE" rev-parse --short HEAD) on storm/$SLUG"
