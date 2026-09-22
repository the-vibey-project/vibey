## Title
chore(runners): import the sovereign review runner's supervisor, heartbeat loop and image into the tree

## Why
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) says the test for declared
state is "whether a stranger with a clone and admin rights can restore the state from the
tree". The sovereign review runner exists only on the operator's machine
(`issue-audit/gaps.md` L3, lines 544-554):
- `~/.local/share/vibey-runner/`: `vibey-runner.sh` (156 lines, the supervisor),
  `vibey-local-authority.sh` (132 lines, the heartbeat and branch-sync loop), `Dockerfile`
  (50), `entrypoint.sh` (34) and `README.md` (100);
- ten `~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner*.plist` units.

A lane runs in a clone and cannot read the operator's home directory. So the first step,
bringing the files into the tree as they are, is the operator's. `gap-runners-declared-1..3`
then make the units rendered from configuration, and `gap-heartbeat-registered` fixes the
false-online heartbeat.

Implementer: the operator. The storm runner skips `gap-ops-*` lanes.

## Required behaviour
The five files are in the tree under `deploy/runners/`, byte for byte, except for the edits
listed in the checklist. They contain no secret, and they have a PR of their own.

## Where to change
New directory `deploy/runners/`, holding `vibey-runner.sh`, `vibey-local-authority.sh`,
`Dockerfile`, `entrypoint.sh` and `README.md`.

## Operator checklist (human — not code; the storm runner must skip gap-ops-* lanes)
1. [ ] On a topic branch: `mkdir -p deploy/runners && cp ~/.local/share/vibey-runner/{vibey-runner.sh,vibey-local-authority.sh,Dockerfile,entrypoint.sh,README.md} deploy/runners/`.
2. [ ] Edit `deploy/runners/vibey-runner.sh:21`, the default `REPO_URL`, to
   `https://github.com/the-vibey-project/vibey`. Change nothing else in the file's logic.
3. [ ] `vibey-local-authority.sh` hard-codes the plist glob
   `com.adammatthewsteinberger.vibey-runner*.plist` (`runner_up`, about `:33-44`). Replace the
   prefix with `${VIBEY_RUNNER_UNIT_PREFIX:-com.adammatthewsteinberger.vibey-runner}`, which the
   rendered units will set.
4. [ ] Secret scan, which must print nothing:
   `grep -n -E 'ghp_|github_pat_|gho_|ghs_|sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH) PRIVATE KEY' deploy/runners/*`.
5. [ ] Put the provenance header on line 1 or 2 of each file (after the shebang), copied from any `.sh` in the tree.
6. [ ] `shellcheck deploy/runners/*.sh` where available, recording any warnings in the PR.
   Fixing them is a follow-up, not this import.
7. [ ] Commit as `chore(runners): import the sovereign review runner as declared state`, then
   open the PR to `develop`.
8. [ ] Append `gap-ops-runner-assets-import` to `STORM/integrated.txt` once it has merged.

## Acceptance criteria
- [ ] `deploy/runners/` holds the five files, and the only content changes are items 2, 3 and 5.
- [ ] The secret scan prints nothing.

## Tests to write first (TDD)
None in this lane. `gap-runners-declared-3` adds a meta-test over `deploy/runners/`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Rendering launchd or systemd units (`gap-runners-declared-2`).
- Any behaviour change to the supervisor.

Do not push until the PR is reviewed.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
