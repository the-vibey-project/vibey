# 0083 — A daily self-healer, backlog killer and documentation updater, scripted first, on GitHub's CPU runners only

**Status:** accepted · **Date:** 2026-10-06 · **Cites:** sub-doctrines 9.c, 10.f, 10.g, 10.l, 12.c, 12.d and 12.e · **Related:** ADR-0046, ADR-0047, ADR-0080, ADR-0081 · **Evidence:** the 245 runs on the remote between 2026-10-05T09:57Z and 2026-10-06T09:57Z, 30 of them failed; pull request #1426

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; `properdocs.yml` nav entries for this record and for
`docs/continuation/backlog.md` and `docs/continuation/docs.md`; `docs/llms.txt` regenerated
from that nav. All are in the
change that carries this record.

## Context

The operator asked for every error on the remote in the last day to be fixed, and for two
daily jobs: a self-healer, and a backlog killer that handles backlog items, both running on
GitHub's CPU runners only. Then for a third: a job that once a day updates all the
documentation, the research paper and the book included.

The day's 30 failures came from six causes (#1426), and four of them were mechanical. A
release commit left a generated page stale. Two advisories were published with fixed
releases (`source-map-js`, `multidict`). A PostgreSQL test raced. Each had one right answer
that a careful person would give the same way twice, which 12.e says is toil and is
automated. The other failures were the gates refusing correctly, and cascades.

The weekly continuation lane (ADR-0080) already runs open-weights prompts on GitHub-hosted
CPU runners, including `keep-green` and `triage`, behind a split that matters. The agent
job holds no write permission and no secret. A fresh runner checks its patch against a
shared guard and opens at most one draft pull request. Its transcripts from 2026-10-05 also
show what gpt-oss:20b does on a CPU runner with a broad brief: it invented issues that do
not exist. The model is the last resort, not the first.

## Decision

1. **`.github/workflows/self-healer.yml` runs daily** and does the scripted part itself. It
   surveys `develop` (the newest run per workflow over the declared window, from push and
   schedule events only; the PR gate's dispatches on `develop` are about pull requests). It
   re-runs each failed run on a declared allowlist once, failed jobs only. It runs the
   declared repairs: re-render the generated pages, `npm audit fix --package-lock-only`, and
   re-lock the fixed release of each pip-audit finding. Then it opens one pull request with
   what they changed. The repairs run in a job that cannot write. A fresh job applies their
   patch only after a guard refuses any path outside `[self_healer.guard] allowed_paths`.
   Whatever is still red is handed to the `keep-green` prompt.
2. **`.github/workflows/backlog-killer.yml` runs daily**, picks one workable issue
   (`scripts/backlog_killer.py`), and runs the new `backlog` prompt on it. The prompt lands
   the issue's smallest shippable, tested slice, says `Refs #N` and never "Closes", and
   states what is still open. The pick skips operator holds, issues an open pull request
   names, machine-filed issues, self-closing trackers and declared labels. It ranks by the
   operator's priority label, then age, and rotates through the first `window` candidates
   by date. Nothing is stored between runs, so the dispatcher and the agent compute the
   same issue.
3. **`.github/workflows/docs-updater.yml` runs daily.** It is the self-healer's runner and
   guard with a table of its own (`scripts/self_healer.py repair --lane docs_updater`):
   every generator re-runs, with the paper's figures re-pinned to the day's `develop`, every
   measured table re-rendered from its record, the continuation prompts and the book's
   `llms.txt`. What moved lands as one pull request, and the guard refuses any path outside
   the documentation. The book, the site and the paper PDF are published per channel by
   `release-surfaces.yml` after each successful release. So the lane checks that the
   develop channel was rebuilt after the newest successful develop release. If it was not,
   the lane rebuilds it from that release (`republish_book`; it never cuts a release). If
   the branch's tip has no successful release, it says so. Then the `docs` prompt corrects
   one written statement the repository now contradicts, starting from the paper's
   recomputed evidence. Generated indexes the documentation deep scan already keeps stay
   its own, so the two lanes never open the same change.
4. **The model runs through the continuation lane, not beside it.** The lane gains a
   `prompts` dispatch input that narrows a run to named prompts, and a per-prompt `cadence`.
   `keep-green`, `backlog` and `docs` are `daily`: they leave the weekly matrix and run only when
   their lane names them. So no second set of agent jobs, guards or permissions exists to
   drift from the first.
5. **GitHub's CPU runners only is a checked claim.** `scripts/continuation_prompts.py
   check` fails on every pull request in three cases: a lane in `[lane] hosted_cpu_only`
   runs a job on a runner `[lane] cpu_runners` does not name (a matrix expression is
   resolved to the declared `[run] runs_on`; any other expression is refused); a lane in
   `[lane] daily` loses its every-day schedule; or it loses its manual dispatch.
6. **No lane merges, approves, cuts a release, deletes, closes an issue, or touches a
   ruleset or a secret** (12.d). Their forge writes are capped re-runs of failed jobs on an
   allowlist, workflow dispatches (a prompt, or a rebuild of an already-successful
   release's surfaces), and pull requests that land through the merge train or not at all.

## Consequences

- A stale generated page or a published advisory fix turns into a pull request within a
  day, with nobody remembering to do it. A flake gets one re-run before anyone reads its log.
- The daily model runs cost GitHub-hosted runner time, not money: the repository is public,
  and both lanes refuse any runner that is not a declared GitHub CPU label.
- Most backlog items are larger than one run of a 20B model on CPU. The backlog prompt is
  written for that. It moves one issue forward one slice at a time, honestly, and it never
  claims to have finished an issue.
- The paper's history figures now move with `develop` every day instead of staying at a
  hand-chosen pin. The pin guard (`tests/meta/test_paper_figures_pin.py`) keeps every pin on
  the integration branch, and a re-pin to that day's `develop` passed every paper test
  (2026-10-06). The hourly delivery estimate also rewrites the forecast block, so on a day
  both land, the later pull request is rebuilt on top of the earlier one by its next run.
- A develop book that lags its branch is said out loud every day, with the release run that
  failed. On 2026-10-06 that was a TestPyPI outage, which it reports but does not repair.
- What the self-healer cannot repair is still reported, in its run summary, and through
  `keep-green`'s report, never as fixed (10.f).
