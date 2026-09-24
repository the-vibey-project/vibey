# Operations

`ANTHROPIC_API_KEY` is required for the issue, documentation and release-repair AI jobs, and
for PR review, repair and conflict resolution only where `[pr_automation] paid_review`,
`paid_repair` or `paid_conflict_resolution` declares that use (by default none is: the
sovereign lane reviews, and failing scans or conflicts are left to a person). Add `AUTOMERGE_TOKEN` only when the default
`GITHUB_TOKEN` cannot satisfy branch rulesets or repository-settings writes; PyPI/TestPyPI
use trusted publishing environments.

## What `AUTOMERGE_TOKEN` must be able to do

The token appears in a minority of the workflows' `GH_TOKEN` assignments — reading the
pull request, commenting, labelling, merging, and pushing the promotion's version bump.
For a fine-grained personal access token that means exactly:

| Permission | Level |
|---|---|
| Contents | Read and write |
| Pull requests | Read and write |
| Workflows | Read and write |
| Actions | Read |
| Metadata | Read (mandatory) |

**Workflows is not optional.** GitHub refuses any push that creates or updates a file
under `.github/workflows/` from a token without it — `! [remote rejected] ... (refusing
to allow a Personal Access Token to create or update workflow ... without workflow
scope)` — and an automated repair is *more* likely than a human to touch a workflow,
because workflow drift is exactly what reviews flag on tooling pull requests. Without
this permission the repair commits cleanly, the push is rejected, and the pull request
silently stops advancing (#172).

**Checks is deliberately absent, and the fine-grained token UI offers no such permission.**
Check runs can only be created by a GitHub App, so the gate is published with
`GITHUB_TOKEN` — which is one — and no PAT permission exists or is needed for it. The
workflows' own `permissions:` blocks govern `GITHUB_TOKEN`, not this PAT; do not read
`checks: read` there as a token requirement.

Three failure modes worth knowing before they cost an afternoon, because each presented as
something else in production:

- **A fine-grained token expires** (a year at most) and returns as `HTTP 401: Bad
  credentials` inside a step whose name says nothing about credentials. A classic token
  with the single `repo` scope covers everything above and supports no expiration — the
  trade is that it reaches every repository the account can.
- **A fine-grained token only reaches the repositories in its own grant list.** The secret
  being set on a repository proves nothing: two repositories out of a token's list behaved
  identically to two inside it for reads, then failed every privileged write. The merge
  train reported each failure as *"the ruleset refused it"* until it learned to print the
  API's own error.
- **The account behind the token is what bypasses rulesets.** The merge train's `--admin`
  fallback works only if that account holds a bypass role on the ruleset; the token's
  permissions cannot add standing its owner does not have.

## `DISCORD_WEBHOOK_URL` (optional)

`Release surfaces` ends its documentation deploy by announcing what changed and what it
published. `vibey-gh announce` posts a concise changelog: one line per merged change,
grouped **Breaking** / **Added** / **Fixed** / **Other**, capped at `[announce] max_changes`
with the rest counted as `…and N more` and linked. Merge and release chores are hidden but
counted (`+N maintenance commits`). The links to each surface the deploy actually produced
come last. It posts through a Discord webhook held in the repository secret named by
`[announce] webhook_secret`, `DISCORD_WEBHOOK_URL` by default (see
[configuration](configuration.md#announce)).

The secret is optional. With none set, the step prints `announce: no DISCORD_WEBHOOK_URL
secret is set; nothing posted` and passes, so a missing announcement is visible in the log
rather than silent. A webhook that fails is a `::warning::`, never a failed deploy. The
webhook URL is a credential (whoever holds it can post as the project). It lives only in
the secret, it is redacted from every log line the announcer prints, and a tree-wide check
refuses any tracked file that carries one.

What a develop deploy posts, from `test/golden/announce-develop.txt`:

```text
**the-vibey-project/vibey** published `develop` from `600f3db2883d` · changes since `b16ba7b590ab`:
**Breaking**
- Feature · storm: lanes run one at a time ([#1102](<https://github.com/the-vibey-project/vibey/pull/1102>))
**Added**
- Feature · gh: announce a concise changelog with every docs deploy ([#1106](<https://github.com/the-vibey-project/vibey/pull/1106>))
**Fixed**
- Fix · paper: draw the release cadence from the tags the repository holds ([#1104](<https://github.com/the-vibey-project/vibey/pull/1104>))
- Fix · gh: quote the paper's author fields for the shell ([#1101](<https://github.com/the-vibey-project/vibey/pull/1101>))
**Other**
- Docs · canon: ratify sub-doctrine 12.f, unattended approval ([#1103](<https://github.com/the-vibey-project/vibey/pull/1103>))
- Performance · queue: claim a job in one round trip ([#1099](<https://github.com/the-vibey-project/vibey/pull/1099>))
+2 maintenance commits · [compare b16ba7b…600f3db](<https://github.com/the-vibey-project/vibey/compare/b16ba7b590ab...600f3db2883d>)
Read: [site](<https://the-vibey-project.github.io/vibey/develop/>) · [paper PDF](<https://the-vibey-project.github.io/vibey/develop/paper.pdf>) · [paper HTML](<https://the-vibey-project.github.io/vibey/develop/paper/>) · [book PDF](<https://the-vibey-project.github.io/vibey/develop/book.pdf>) · [book EPUB](<https://the-vibey-project.github.io/vibey/develop/book.epub>) · [book print](<https://the-vibey-project.github.io/vibey/develop/book-print.html>)
```

**Where "since" starts.** The range is a position, never a time (sub-doctrine 10.g). Every
`Release surfaces` run is titled `<name> · <branch> · <release commit>`. The next develop
announcement reads the Actions API for the newest successful run on its branch whose
`Record the announced position` step succeeded, and announces the commits from that run's
release commit to this one. The announce step writes `posted=` and `position=` for that
marker, and the marker runs only on `posted == 'true' && position != 'unknown'`. The
position is one of three things, and the message says which:

- **known**: the previous position was read and compared. `changes since <commit>:`. Recorded.
- **unknown**: the history could not be READ. The Actions API errored or answered something
  malformed, a run's jobs or the compare could not be listed, or a dispatched run named no
  commit. The message says `changes since: unknown (<why>) — this commit only; the next
  announcement covers the span again:`, and it is **not recorded**: the watermark stays
  where it was, so the next announcement starts from the last recorded commit and covers
  everything since, this commit included. An API outage delays an announcement; it never
  loses one.
- **re-anchored**: the history was read and holds no usable position. That covers the
  first announcement ever; a last-announced commit that is no longer an ancestor (a
  force-push); nothing accepted within the API's window (a status-filtered run listing stops
  at its 1000th result, which is why `max_history_pages` stops at 10); and more than
  `max_history_candidates` runs for the branch in a row whose announcement was not accepted.
  Reading again would find the same thing, so the message says `re-anchored here (<why>) —
  this commit only:` and **is recorded**, and the next announcement starts here. The commits
  between the old position and this one are not listed, and the message says so rather than
  claiming a range.

A release on the release branch announces its own notes instead: the version's section of
`CHANGELOG.md`, with the commit count and compare link from the previous version's tag when
that tag resolves. A branch or tag prefix may contain `/` (`release/next`, `v/`); refs are
URL-encoded wherever they enter an API path.

**At least once, not exactly once.** A run that posted but whose marker step never ran (the
runner died between the two, or the marker was skipped because the position was unknown) is
not a recorded position. The next announcement covers its commits again, so a reader can see
a change twice; that is the direction 10.g chooses, since a re-read repeats and a skip loses.
Two things are de-duplicated by identity. A run for a commit that is already the recorded
position (a re-run, or a replayed deploy of the same release) posts nothing and prints
`announce: <commit> was already announced for <branch>; nothing posted`. Within one
message, a commit is listed once. Docs jobs for one repository queue behind a single
concurrency group and never overlap, so each announcement reads the position the previous
one recorded. A pending docs job that GitHub cancels in favour of a newer one records
nothing, and its commits are covered by the newer one's range.

To preview a message without posting, run it from the repository root:

```bash
vibey-gh announce --channel develop --branch develop --sha "$(git rev-parse origin/develop)" \
  --repository OWNER/NAME --dry-run
```

## Recovering from a review with no verdict

With no paid review declared (`[pr_automation] paid_review = false`, the default), the
sovereign lane is the only reviewer, and a gate that could not get its verdict says so:
`PR review: review incomplete (needs a human review)` when the runner was down or the local
model gave none — the summary names the reason, and the recovery sweep re-probes once the
runner beats again — and `PR review: needs a human review` for an outside author or a fork,
which only a person can clear. See
[the paid-review declaration](configuration.md#the-paid-review-declaration-paid_review).

With a paid review declared: `PR review: review incomplete` (behind a green `PR evaluate / gate` scan gate) means the primary exact-head review returned no verdict
at all — check API credit balance, the `ANTHROPIC_API_KEY` secret, and model availability,
then rerun the review; this is never a defect in the pull request. When the API refused
the call the summary says so in the API's own words:
`the paid review was refused by the API: Credit balance is too low`. If
`[pr_automation.fallback].enabled` is set and a self-hosted runner carrying the
`[pr_automation.fallback] runner_label` label (default `vibey-local`) is registered, the
same no-verdict condition instead dispatches a local Ollama model against
the diff; a clean local verdict passes the gate as `PR review: gate (local fallback)`
rather than blocking it. That title always names the weaker reviewer — treat it as a
signal to still fix the primary path's root cause, not as a fully reviewed pass.

## The sovereign heartbeat — honest, declared, and through the gate

The PR-review gate schedules the sovereign review only while
`[pr_automation.fallback] heartbeat_ref` is younger than `heartbeat_max_age_minutes`
(default 15); otherwise it asks a human. The heartbeat is published by a timer on the
machine that serves the lane (vibey ADR-0059).

**Stand it up** from the repository's main checkout, with a `vibey-gh` installed outside any
checkout and outside any temporary directory (for example `uv tool install vibey`):

```bash
vibey-gh heartbeat install          # writes the unit, loads nothing, prints the next commands
vibey-gh heartbeat install --load   # also (re)loads it
vibey-gh heartbeat status           # installed, current, loaded, last beat's age and result
vibey-gh heartbeat uninstall        # dry run; --apply unloads it and moves the units aside
```

`vibey-gh runner install` and `runner uninstall` do the same for the heartbeat alongside the
runner. On macOS the timer is a launchd agent; on Linux (Ubuntu LTS included) it is a systemd
user service and timer, and `loginctl enable-linger "$USER"` keeps it running without a login
session. It beats every `[runners] heartbeat_interval_minutes` — by default half the trust
window, and never more — so one missed beat does not stale the lane. Install refuses an
interpreter, a `vibey_gh` or a log directory under a temporary directory or inside a git work
tree, and a checkout that is a linked worktree, and says which.

**Each beat is honest.** `vibey-gh sovereign --beat` publishes only when a runner carrying
`runner_label` is registered with the repository and online (read from GitHub with the
runner's own login in `[runners] gh_config_dir`), and the model endpoint `base_url` answers
with `model`. Otherwise it pushes nothing and says why — `heartbeat withheld: no runner
labelled … is online …` — so the heartbeat goes stale on its own and the gate falls back
honestly. A check that could not be read withholds the beat too. The timer's `--record` file
is what `heartbeat status` reads.

**Each beat goes through the pre-push gate.** There is no `--no-verify`. The hook
`vibey-gh install` renders reads every ref git is pushing and ends before the heavy stage only
when every ref is outside `refs/heads/` and `refs/tags/` and every commit is the empty tree with
no parents (`vibey-gh push-scope`); anything else — a branch, a tag, a file, a parent, a
heartbeat riding beside a branch — runs the whole gate. The heartbeat replaces the previous one
by compare-and-swap (`--force-with-lease` on the exact value read, which must itself be a
heartbeat), never a bare force. The hook needs `vibey-gh` (or, where the repository carries its
own copy, a `python3` that can import it) on the timer's `[runners] path`.

**`vibey-local-authority` is retired.** The hand-written LaunchAgent that used to publish the
heartbeat, from one operator's home directory and recorded nowhere, said "up" whenever its
supervisor had a live process and pushed with `--no-verify`. Unload it
(`launchctl bootout gui/$(id -u)/<its label>`) and install the declared timer above in its
place. The `vibey-gh local-authority` command below is a different thing and is unchanged.

## Local-authority mode — when the paid lane is capped

When API credits are exhausted, evaluations fail rather than review, and the operator's
machine becomes the source of truth (#206). `vibey-gh local-authority` keeps remotes
tracking green local state: each pass pushes any clean, check-passing local branch that
is ahead of its upstream, with an explicit pre-fetch `--force-with-lease` so remote work
this machine has not integrated always refuses the push. Run it as a login daemon
(launchd/systemd) pointing at `vibey-gh local-authority` with no `--once`; reviews meanwhile
come from `vibey-gh local-review` verdicts recorded on the pull request.

Recovery is automatic by design: every evaluation tries the paid lane first, so the
human's only act is adding credits — the next evaluation simply succeeds, and this loop
idles (nothing-ahead is a no-op).

## Everything else

Enable Actions write permissions, PR creation,
GitHub Pages via Actions, Packages, Releases, and Deployments. Use workflow dispatch for
recovery. Inspect exact run and head SHA before retrying. Never solve a blocked release by
deleting, force-pushing, weakening a gate, or switching production to TestPyPI.

To retry one issue, dispatch `Issue automation` with its number; `vibey-gh
issue-automation list-eligible` shows what the scheduled sweep would pick up. A redispatch
of unchanged issue text is a no-op, so retrying is safe. An issue labelled
`vibey-gh:solve-blocked` is waiting on a human decision named in the issue's state comment,
and one labelled `vibey-gh:solve-exhausted` has spent its budget; editing the issue body
restates the request and starts a new lineage. To stop the feature without uninstalling it,
set `[issue_automation].enabled = false` in reviewed configuration.

When a bug in privileged workflow code itself blocks a repair PR from repairing its own
gate, dispatch `Automation bootstrap` (see [Workflows](workflows.md)) with the exact PR
number, exact head SHA, and explicit authorization. It requires administrator permission
and every independent gate already passing on that SHA, and it is the only path that
squash-merges to `develop` without an ordinary PR automation review.

To preview what `Branch sync` would rebase, close, update, or leave without mutating
anything, dispatch it manually with `dry_run = true`; the decisions are printed to the run
summary. The nightly schedule run of its `heal` job refills the repair budget of every pull
request labeled `vibey-gh:repair-exhausted`, up to `branch_sync.max_self_heals` times per
lineage, and re-dispatches `pr-evaluate.yml` against each healed PR's exact head SHA. Once
that budget is spent for a lineage, the label stays and only a human — typically by pushing
a new commit or editing the PR — starts a fresh lineage. See [Workflows](workflows.md) and
`[branch_sync]` in [Configuration](configuration.md).

When Conventional Commits rewrites a topic branch, synchronize the local checkout before
new work. Preserve unpushed work first, then use `git fetch origin` and rebase it onto the
new remote head; if there is no unpushed work, reset the local topic branch to its explicit
`origin/<branch>` ref. Never run either operation against `develop` or `main`. The workflow
has no per-run bypass: correct the commit locally when a fork or merge-containing branch
cannot be repaired automatically. Disable the managed workflow only through reviewed
`[install].workflows` configuration, which makes the policy change visible to CI.
