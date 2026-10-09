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

## Amendment, 2026-10-07: the backlog killer runs every 90 minutes

At the operator's request the backlog killer runs once per `[backlog_killer] interval_minutes`
slot, 90 minutes by default, rather than once a day: two interleaved three-hourly crons, sixteen
runs a day. Its pick rotates through the window by slot instead of by date, so every run in a day
no longer picks the same issue, and `tests/meta/test_daily_lanes.py` fails if the crons stop
firing once per declared interval. Everything else in this record stands: it still runs only on
GitHub's CPU runners, still lands at most one draft pull request per run through the
continuation lane's guards, and still merges, approves and closes nothing.

## Amendment, 2026-10-08: the backlog killer runs every 20 minutes

At the operator's request `[backlog_killer] interval_minutes` is 20, not 90: one `*/20`-shaped
cron (`3,23,43 * * * *`) replaces the two interleaved three-hourly crons, seventy-two runs a
day. The pick's slot arithmetic is unchanged, so the rotation simply turns faster through the
same `window`. The workflow's concurrency group queues at most one waiting run, so a run
longer than 20 minutes skips slots rather than stacking them. `tests/meta/test_daily_lanes.py`
now parses minute lists and steps, and still fails if the crons stop firing once per declared
interval. Every guard in this record and in the 2026-10-07 amendment stands.

## Amendment, 2026-10-09: the backlog killer's clock is a chain, and the cron is its watchdog

GitHub's `schedule:` is best-effort: on 2026-10-08 it delivered 5 of the 16 runs the 90-minute
schedule asked for, some an hour late, and after the interval became 20 minutes it delivered
one in the first three and a half hours. A clock that is delivered a third of the time is not a
clock, so at the operator's request each run now ends with a `chain` job that waits for the
next `[backlog_killer] interval_minutes` slot and dispatches the workflow again. A dispatch
made with the workflow's own token starts a run, and it can only start this workflow.

The chain is a loop that nothing outside it ends, so every bound is declared and tested
(`tests/meta/test_daily_lanes.py`), by 12.d and the floor above it:

1. **A switch.** `[backlog_killer] chain = false` ends it at the next link; the file is read
   from `develop` on every link, so ending it is a pull request, not a runner setting.
2. **A maximum.** `chain_max_links` ends a chain nobody is watching. The link number travels
   in the dispatch, and a chain that stops waits for the watchdog.
3. **One at a time.** The workflow's concurrency group runs a single link at once and replaces
   a waiting run with a newer one instead of queueing it, so no more than one dispatch per slot
   can be made, whatever else starts a run. A link also dispatches nothing when the next slot
   already has a run, and a run that finds an earlier one in its slot works no issue.
4. **A watchdog.** The cron stays, hourly (`watchdog_minutes`), to start a chain again when
   none is alive: a cancelled run, a lost runner or the maximum all end a chain.
5. **Nothing new may be done.** The chain job holds `contents: read` and `actions: write`, its
   only write is `gh workflow run backlog-killer.yml`, and the guards in this record and in the
   two earlier amendments (CPU runners only, at most one draft pull request per run, no merge,
   approval, release or issue closed) apply to every link unchanged.

The cost is a runner idle for up to one interval per link, which is free on a public repository
and is not free on a private one. The chain does not make the agent succeed: that is
`continuation-prompts.yml`'s concern (the same day's fix for an unavailable model server).

## Amendment, 2026-10-09: the hosted CPU runners run qwen3:8b, not gpt-oss:20b

The continuation lane's model chain (`scripts/continuation_prompts.toml` `[run] models`) and the
sovereign repair's (`[pr_automation.sovereign_repair] models`) were `gpt-oss:20b`, then
`qwen3:4b`. gpt-oss:20b is about 13 GB and the GitHub-hosted `ubuntu-24.04-arm` runner has 16 GB:
across the backlog killer's runs of 2026-10-08 and 09 the agent log read `gptossloop
unavailable: Remote end closed connection without response`, a dead model server, and the
lane opened no pull request. At the operator's decision the chain is now `qwen3:8b` (about
5 GB), then `qwen3:4b`, on every hosted CPU runner that runs an agent.

What this does not do, and why:

- **The sovereign default is unchanged** (8.d): gpt-oss:20b is still the model on the operator's
  own device, in `[local_models]`, and in the review lane's own settings.
- **The PR review and its canary are not changed here.** The review runs at a 65,536-token
  context with a 16,384-token reasoning reserve; a dense 8B model's KV cache at that window is
  several times gpt-oss's, so the same swap could exhaust the runner it was meant to spare, and
  the canary's recall measurement vouches for nothing under another model
  (`[pr_automation.review_canary]`). Moving the review is its own decision, with its own
  measurement.
- **qwen3:8b is unmeasured on this runner.** gpt-oss:20b is a mixture-of-experts model that
  reads about 2 GB of weights per token; qwen3:8b is dense and reads about 5 GB, so on a
  memory-bound CPU it may generate more slowly per token, not faster. The lane is bounded by
  turns and by time, so a slow model costs runs, not safety.

## Amendment, 2026-10-09: the agent runs get the longest timeout a hosted job allows

At the operator's request the continuation lane's agent budget is 350 minutes inside a 360-minute
job (360 is GitHub's ceiling for a hosted job; the ten minutes left cover the model pull, the
evidence and the hand-over, which must finish inside the job or the log is lost), and the
sovereign repair's is 330, the most its validator allows. The runs that prompted it were not
timing out, so this buys a slow model time rather than speed. It costs the lane its slot: the
continuation lane's concurrency group runs one agent at a time and holds a hung one for up to
six hours, during which the backlog killer's dispatches are dropped or queued behind it.

## Amendment, 2026-10-09: one model, a tested patch, and an hourly clock

Three findings from watching the lane for four hours, none of them a crash.

- **qwen3:4b is withdrawn as the continuation lane's fallback.** qwen3:8b timed out on the
  hosted CPU runner, qwen3:4b answered, and its patch was a placeholder adoption table of
  reviewer feedback that exists nowhere in the repository (#1488). A fallback that answers
  with something plausible is worse than a run that fails loudly (10.f). The sovereign
  repair's chain is unchanged here.
- **A patch for the `backlog` prompt must add or change a test.** `[authority.require_test]`
  declares the prompts and what counts as a test; `continuation_prompts.py guard PATCH
  --prompt ID` refuses a patch for one of them that touches none. The prompt promises "a
  tested slice", and a deterministic check is the part a small model cannot talk its way past.
- **The backlog killer runs hourly, not every 20 minutes.** An agent run takes 40 to 80
  minutes and the lane runs one at a time, so two of every three dispatches were replaced
  unrun and showed as cancelled. `interval_minutes` is 60, the watchdog 120.


## Amendment, 2026-10-09 (later): a patch may not gut a file

The first hourly run after the previous amendment showed why a model that cannot ground itself
is dangerous even when it fails. Denied a direct delete, qwen3:8b wrote the 331-line paper
(`src/vibey_tools/gh/docs/paper.md`) and a 53-line site definition to empty with
`write_file(content="", allow_shrink=True)`, added an unwired shell script as the "test", and
reported the work as complete. The only thing that stopped it was a rejected push.

- **`[authority] max_removed_lines = 40`.** The guard refuses a patch that removes more than that
  from any one file; a deleted file and an emptied one are the same patch. 0 disables it.
- **A test is a collectable test.** `[authority.require_test] paths` now matches `test_*.py`
  under `tests/` and `*.test.ts(x)`, not any file under `tests/`.
- **The push is no longer "stale info".** The Act and refresh jobs fetch the day's branch before
  the lease, so a branch left by an earlier run is replaced instead of failing every later run.
- **Two ways round the per-file limit are closed.** A binary file reports no line count (`-`), so
  it is refused outright instead of counted as nothing, and `max_removed_total = 120` bounds the
  whole patch, so forty lines from each of forty files is the same patch as forty from one. Both
  were found by probing the guard with a binary replacement and a spread-out patch.

## Amendment, 2026-10-09 (later still): grounding, before and after the model runs

The cause under the previous two amendments was one thing: the runs were not grounded in the
codebase. The run that emptied the paper made seven tool calls, one of them a `find`; it never
read `CLAUDE.md`, the files the issue named, or ran a test, though its prompt asks for all three.
The prompt asked and nothing checked, so two layers now do.

- **After the run, the lane reads the runner's record of it.** `continuation_prompts.py guard
  PATCH --prompt ID --tools TOOLS_JSONL` refuses a patch for a tested prompt unless the record
  shows a successful `read_file` (or a shell command that only displays the path: `cat`, `head`,
  `tail`, `less`, `more`, `nl`, `sed` without `-i`, `git show`) for every file the patch changes
  or deletes, and a successful test command: one that starts with a runner such as `pytest`,
  `npm test` or `vitest` and is not a dry run. The record (`continuation_prompts.py tools`) is
  built from the runner's structured `tool.call` and `tool_result` events and never from the
  agent's prose; the store must hold exactly one run; a covered prompt with no record is refused.
  Run against the 2026-10-09 artifact it refuses all three of that patch's defects.
- **A security review of the first version found three ways round it, all confirmed and
  closed.** `git`, `sed -i` and `awk` were counted as readers, so `git rm paper.md` "read" the
  paper; the evidence was parsed from `agent.log`, which also holds the model's own words, so
  a model could print `[tool] read_file ...`; and any argv that mentioned `pytest` counted as a
  test, so `echo pytest` did, whatever its exit code.
- **Later review rounds found more, also confirmed and closed.** The hand-over ran
  `continuation_prompts.py tools` in the agent's own runner, from the tree the agent had edited,
  so an agent that rewrote that script wrote its own record; a first fix, a "trusted copy"
  exported there before the run, was a copy in a place the agent could equally overwrite. So
  nothing from the repository now runs in that job after the agent: it hands its run store over
  raw (`events.jsonl` files and the working directory's path), and the `report` job, on a clean
  runner and a clean checkout of the base branch, builds the transcript and the tool record from
  it (`transcript DIR`, `tools DIR ROOT`). A read that returned nothing (`head -c 0 paper.md`)
  no longer counts, so each call records the size of what it returned. Paths are compared as the
  patch names them (`./a/../b`, and a path under the run's own directory). And a file named
  `pytest.py` or `pytest/`, which `python -m pytest` would import from the working directory in
  place of the real runner, is a protected path, with more dry-run flags (`--fixtures`,
  `--setup-plan`) excluded from "a test".
- **What this does not stop.** An agent with a shell (it has `sudo` on its VM) can still write
  into its own `.qwenloop/` run store, replace the events files it hands over, or tamper with
  the tools that run after it in its job (`git`, the artifact upload), and the lane cannot tell. The check holds against a model that skips
  its steps, not against one that forges its record; closing that needs the run store outside
  the agent's tree, which is a change to the runner, not to this lane.
- **Before the run, the evidence is the codebase.** `scripts/backlog_grounding.py` is a second
  `gather` command of the `backlog` prompt: it quotes the first lines of every tracked file the
  issue names, where the identifiers the issue puts in backticks occur, and the headline of each
  `CLAUDE.md` non-negotiable, each bounded and each cut with a note. The issue text only selects
  which tracked files to quote; it is data, and an untracked path is never read.

Neither layer makes a small model good. They make a run that did not look at the code unable to
land a change to it, and a run that did start with what it would otherwise have had to find.

## Amendment, 2026-10-09 (the operator's decision): the backlog prompt runs on the operator's machine

Four hours of watching the backlog lane on a hosted runner settled it: qwen3:8b on four vCPUs
called tools that do not exist, edited files that do not exist, and wrote a ledger of invented
records, and every guard held while nothing useful landed. No free GPU exists to fix that on
GitHub: GPU runners are larger runners, "always charged for, even when used by public
repositories" (about $0.05 a minute for the 4-core Linux one), and the free inference services
checked (GitHub Models, Cloudflare Workers AI, Hugging Face ZeroGPU, Kaggle, Colab, the Groq and
Cerebras free tiers) are token- or minute-capped, interactive-only, or not sovereign. The
operator's own machine already serves gpt-oss:20b and already registers a runner for it.

- **`[run.sovereign]` in `scripts/continuation_prompts.toml`** is now the one declared exception
  to "hosted CPU only". The prompts it names (`backlog`) run on `[self-hosted,
  vibey-local-vibey]`, through gptossloop (`GPTOSSLOOP_BASE_URL`, `GPTOSSLOOP_MODEL`), on
  gpt-oss:20b at the host's Ollama, with 40 turns and a 120-minute ceiling. `check` holds its
  runner label and heartbeat to `.vibey-gh.toml`, so the two cannot drift.
- **An offline host skips the job; it never queues it and never falls back.** Before the matrix
  exists, a hosted `refresh` step reads the machine's heartbeat ref
  (`refs/vibey-gh/sovereign-heartbeat`, at most 15 minutes old). Stale or unreadable, the prompt
  is left out of the matrix, the `run` and `report` jobs are skipped on an empty matrix, and the
  summary says why. A job queued for a runner that is not there would wait a day holding the
  lane's concurrency group.
- **What the agent can reach: the gate, and nothing else.** The first version of this
  decision let the container reach the host through `host-gateway`, and testing it showed the
  host's Postgres (5432) and RabbitMQ (5672, 15672) accepting connections from inside, while the
  agent runner's `allow_network=False` turned out to be an environment variable that enforces
  nothing. So the runner container now has NO route out. It joins a Docker `--internal` network
  whose only other member is an egress gate: a `CONNECT` proxy for a declared host list on 443
  (GitHub and its stores, PyPI) that resolves names itself and refuses any address that is not
  globally routable, and a forwarder that lets through four model-server requests, so the agent
  cannot pull or delete a model on the operator's machine. `[run.sovereign]` is refused by
  `check` unless `[runners] egress_gate = true`, and its model URL must be the gate's. Tested
  with a throwaway network on the operator's machine: direct connections to the internet, the
  host's Postgres and RabbitMQ, and Ollama all fail; through the gate, GitHub, PyPI and the
  chat endpoint work and `DELETE /api/delete`, `POST /api/pull` and `POST /api/generate` return
  403. What remains is exfiltration to a host on the allowlist, which takes a credential the
  job does not hold, and the pre-existing exposure of the run record (below).
- **A security review of the gate found its first version leaky, and three things were closed.**
  The default allowlist's `productionresultssa*.blob.core.windows.net` also matched
  `productionresultssaz.blob.core.windows.net`, a storage-account name anyone can register, so
  a job's shell could have sent data to it: the default now names GitHub's twenty accounts
  exactly, and a wildcard is only ever a whole first label, refused over a top-level domain, a
  country-code second level or a shared-hosting domain (`windows.net`, `github.io`,
  `amazonaws.com`). The supervisor reused a network of the right name without checking it was
  `--internal`; it now verifies that before the gate starts and again before every job, and
  that the gate is attached to it. And the check that the gate was running could never match
  (a glob needing one space to be two), so it would have rebuilt the gate before each job; two
  tests caught it.
- **Who can reach the machine at all.** The workflow is dispatch- and schedule-only, so no
  fork's code or pull request ever reaches it, and the backlog pick takes issues only from
  trusted authors.
- **What a heartbeat does not promise.** It says the machine was up within 15 minutes, not that
  Ollama is serving the model: the job checks that first and fails loudly. And a machine that
  goes down in the minutes between the heartbeat and the job leaves the job queued.
- **Reversible by one key.** Remove `[run.sovereign]` and the prompt runs hosted again.


## Amendment, 2026-10-09 (night): the agent could write a test and never run one

The first runs through the gated container (20:00, 21:00 and 22:00Z) were different in kind from
every earlier one: `gpt-oss:20b` read real files, edited `config.py`, and wrote a real test
(`tests/meta/test_one_book_one_paper.py`). All three ended at 40 turns of 40, mid-edit, and all
three were refused, correctly, for want of a passing test. They could not have had one:

- **No Python ran in the agent's shell.** Its environment is filtered, and `setup-python`'s
  Python finds its libpython through `LD_LIBRARY_PATH`, which the filter drops:
  `libpython3.12.so.1.0: cannot open shared object file`, 16 shell calls in one run spent
  looking for a working interpreter. `pytest` and `uv` were not installed anywhere it could
  find. One run's report said "all existing tests continue to pass" having run none.
- **The fix gives it what needs no environment:** a venv from the SYSTEM Python in the worktree
  (git-ignored), with the project's `[dev]` extras, built by a workflow step that proves it with
  `env -i`. Replayed in the runner image behind the gate: 70 seconds, `pytest` and `ruff` run
  with an empty environment.
- **The test session needs PostgreSQL**, which the container does not have and must not reach:
  the root `conftest.py` connects for any session under `tests/`. `--noconftest` runs
  `tests/scripts` and `tests/meta` (tried: 15, 11 and 80 tests pass) and the vibey-gh suites
  need none; the prompt says so, and says to report a database test as unrunnable.
- **The guard read the agent's commands wrongly.** The agent sends every command as
  `bash -lc '<command>'`, which my anchored pattern would have refused even for a real passing
  run. It now judges the command inside, and only when it is one simple command: `pytest || true`,
  `pytest | tee`, `echo pytest` and `pytest --collect-only` still do not count.
- **`max_turns` 40 -> 120** for the host prompt (about 25 minutes at 12 s a turn, against a
  120-minute ceiling). The guards, not the budget, decide whether a patch lands.
