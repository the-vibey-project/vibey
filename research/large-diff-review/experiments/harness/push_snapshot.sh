#!/bin/sh
# Snapshot the live results into data/ and push them (sub-doctrine 10.h: every 30-45 min).
# If the current research branch's PR has merged (its remote branch is gone), start the
# next numbered branch from origin/develop, carry research/ over (research/-only commit),
# and open a draft PR. Prints the branch and PR it pushed to.
set -e
cd "$(dirname "$0")/../../../.."
EXP=research/large-diff-review/experiments
"$EXP/harness/snapshot.sh"
git fetch -q origin
branch=$(git branch --show-current)
# A new branch is needed when this one's PR merged (its remote branch is gone), or when
# develop changed research/ since this branch forked from it (a release rewrote develop and
# re-landed earlier research PRs under new SHAs) -- merging would then conflict on every
# research file, and a non-fast-forward push is never made.
base=$(git merge-base HEAD origin/develop)
gone=0; git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1 || gone=1
moved=0; git diff --quiet "$base" origin/develop -- research || moved=1
if [ "$gone" = 1 ] || [ "$moved" = 1 ]; then
  old_branch=$branch
  n=${branch##*-}; next="research/large-diff-review-$((n + 1))"
  git switch -q -c "$next"
  git reset -q --soft origin/develop
  git restore --source=origin/develop --staged --worktree -- . ':!research'
  branch=$next
  new=1
fi
git add -A research/large-diff-review
if ! git diff --cached --quiet; then
  git commit -q -m "docs(review): snapshot the live experiment results

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>" || \
  { git add -A research/large-diff-review; git commit -q -m "docs(review): snapshot the live experiment results

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"; }
fi
git merge -q -m "chore: merge develop into $branch" origin/develop
python3 /Users/adam/git/vibey/docs/plans/qwenstorm-3.0.0/tools/push_gate.py --root ~/git/vibey-storm run -- git push -q -u origin "$branch"
if [ "${new:-0}" = 1 ]; then
  if [ "$moved" = 1 ] && [ "$gone" = 0 ]; then
    old_pr=$(gh pr list --repo the-vibey-project/vibey --head "$old_branch" --state open --json number --jq '.[0].number')
    [ -n "$old_pr" ] && gh pr close "$old_pr" --repo the-vibey-project/vibey \
      --comment "Superseded by $branch: develop was rewritten and re-landed earlier research PRs under new SHAs, so this branch no longer merges. The new branch carries the same research/ tree on the new develop."
  fi
  gh pr create --repo the-vibey-project/vibey --base develop --head "$branch" --draft \
    --title "research(review): large-diff sovereign review — experiments (continued)" \
    --body "Draft — research in progress (EXPERIMENT track), continuing the merged research/large-diff-review-* PRs. research/ only; experiments/results/ stays live and untracked, experiments/data/ is the committed snapshot. Production review code is not changed here.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
fi
echo "pushed $branch $(git log --oneline -1)"
