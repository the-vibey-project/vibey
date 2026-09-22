## Title
ops: restore at least one PR-review lane (fund the paid key, or re-register the sovereign runners)

## Why
Constitution III.3 says the two review lanes back each other. Sub-doctrine 8.a says the
sovereign path is the preference. Today neither lane can produce `PR review / gate`
(`issue-audit/gaps.md` L2, lines 534-542):
- **Paid lane.** Every run's "Say why the model call failed" step prints
  "Credit balance is too low". Read it in the full job log (`gh run view <id> --log`, not
  `--log-failed`); the step passes, so `--log-failed` omits it.
- **Sovereign lane.** Every `~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner-*.plist`
  sets `VIBEY_REPO_URL=https://github.com/adammatthewsteinberger/<repo>`. The repository moved
  to `the-vibey-project/vibey`, so registration has returned 404 since 2026-08-31. The
  supervisor stops after five failures and relaunches every 120 s.
- The latest `pr-review.yml` run failed at 2026-09-22T15:06Z.

Without a gate, nothing merges. `gap-chain-dispatch` then has nothing to hand on.

Implementer: the operator. Path B is a security decision, item 10 of `gap-ops-canon-rulings`.
The storm runner skips `gap-ops-*` lanes.

## Required behaviour
At least one lane produces a successful `PR review / gate` on a real PR head, and the evidence
is recorded.

## Where to change
Nothing in the tree. Path B's durable fix, runners declared as code, is
`gap-runners-declared-1..3` and `gap-heartbeat-registered`.

## Operator checklist (human — not code; the storm runner must skip gap-ops-* lanes)
Choose A, B, or both.

**A. The paid lane.**
1. [ ] Add credit to the Anthropic account behind the repository secret `ANTHROPIC_API_KEY`
   (`.github/workflows/pr-review.yml:450`).
2. [ ] Re-run one review:
   `gh workflow run pr-review.yml -R the-vibey-project/vibey --ref develop -f pr=<N>`.
3. [ ] Confirm the model step no longer prints "Credit balance is too low", and that
   `gh api repos/the-vibey-project/vibey/commits/<head>/check-runs --jq '.check_runs[]|select(.name=="PR review / gate")|.conclusion'`
   is `success`.

**B. The sovereign lane (runs PR review on this Mac; rule on it first, `gap-ops-canon-rulings` item 10).**
1. [ ] Record the ruling and the isolation you accept. Today the runner runs in Docker, per
   `~/.local/share/vibey-runner/Dockerfile`.
2. [ ] In each `~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner-*.plist`
   that serves this repository, set `VIBEY_REPO_URL` to `https://github.com/the-vibey-project/vibey`.
   The siblings were absorbed, so every per-repository plist except `-vibey` serves a
   repository that no longer exists: `launchctl bootout gui/$(id -u) <plist>` those and move
   them aside rather than deleting them.
3. [ ] `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner-vibey.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner-vibey.plist`.
4. [ ] `gh api repos/the-vibey-project/vibey/actions/runners --jq '.runners[]|{name,status,busy,labels:[.labels[].name]}'`
   shows a runner labelled `vibey-local-vibey` with `status: online`.
5. [ ] Watch `~/Library/Logs/vibey-runner-vibey.log` for a successful registration. Then
   dispatch a review as in A.2 and confirm the "Sovereign diff review" job ran on the self-hosted runner.

**Both.**
1. [ ] Paste the successful gate's run URL into this issue.
2. [ ] Mark `gap-ops-review-lane` integrated (append it to `STORM/integrated.txt`).

## Acceptance criteria
- [ ] One `PR review / gate` with conclusion `success` on a real PR head after 2026-09-22, with its run URL recorded.
- [ ] If B was taken: the ruling is recorded in `gap-ops-canon-rulings`, and a runner labelled `vibey-local-vibey` is online.

## Tests to write first (TDD)
None. This is a human checklist.

## Checks the lane must run (all must pass)
None in code.

## Out of scope
- Declaring the runners and heartbeat as code (`gap-runners-declared-*`, `gap-heartbeat-registered`).
- Changing review logic.

Commit nothing. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
