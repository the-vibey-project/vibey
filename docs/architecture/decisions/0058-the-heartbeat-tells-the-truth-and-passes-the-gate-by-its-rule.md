# 0058 — The heartbeat tells the truth, and passes the gate by the gate's own rule

**Status:** proposed · **Date:** 2026-09-24 · **Cites:** the CLAUDE.md non-negotiables "Unattended authority is bounded by a gate, never by judgement" (12.d), "Everything-as-code" (12.c), "Toil that can be fully automated is" (12.e), "Status is evidence-bounded" (10.f) and "Code lives in classes" (9.b); doctrine 8.a · **Related:** ADR-0016, ADR-0018, ADR-0042, ADR-0046, ADR-0047, ADR-0050 · **Evidence:** `develop` at `e89818ce`, read 2026-09-24; pre-commit 4.6.2 `commands/hook_impl.py::_pre_push_ns`; git's pre-push stdin as observed against a local bare remote

**Owes:**

- the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
  `docs/index.md`, and a nav entry in `properdocs.yml` (done in the change that carries this);
- **a sub-doctrine.** Two rules here bind future decisions and are conduct, so under ADR-0020
  they belong in the canon. This record applies them; it does not ratify them. Proposed text,
  for the operator to file under 10 or 12: *"A signal that something is up is published only
  after what it claims has been read true, and a read that fails withholds it. A gate that
  exempts anything does so by its own rule over the objects it judges, never on a caller's
  flag."*

## Context

The PR-review gate schedules the sovereign (local Ollama) review only while
`refs/vibey-gh/sovereign-heartbeat` is fresh (`[pr_automation.fallback]
heartbeat_max_age_minutes`, default 15); otherwise it falls back to "needs a human". The ref
was published by `vibey-local-authority`, a LaunchAgent in one operator's home directory that
ran `vibey-gh sovereign --beat` on a timer. Two things were wrong with it.

**It skipped the gate.** `beat()` pushed with `git push --force --no-verify`, and its docstring
called `--no-verify` load-bearing: the pre-push stage runs the suite, a coverage pass and a
network audit, measured at more than two minutes against 1.2 seconds skipped, on a push that
carries an empty tree with no parents. The measurement was right and the remedy was not. 12.d
forbids `--no-verify` and "any means whose purpose is to make a check stop applying", with no
exceptions, and a caller-side skip applies to whatever the push happens to carry, not only to
the empty commit it was written for.

**It was not honest.** The agent decided when to beat from its supervisor having a live
process. While runner registration was failing, that process lived for about thirty seconds
of every restart cycle, so a heartbeat went out at 2026-09-22T01:38Z with no runner able to
take a job. A fresh heartbeat with no runner makes the sovereign job queue forever, and the
required gate `needs` it.

And it was hand-made: nothing in the tree declared it, could restore it, or could say it had
stopped. At the operator's request it has been retired.

## Decision

### 1. The gate decides its own scope

The pre-push stage judges code on its way off the machine, so it now recognises, by its own
rule, a push that carries none: **every ref being pushed is outside `refs/heads/` and
`refs/tags/`, and every commit it sends is the empty tree with no parents.** Such a push ends
the hook before the heavy stage; every other push runs the gate in full.

- The rule lives in one class, `vibey_gh.push_scope.PushScope`, with
  `interfaces/push_scope_interface.py` beside it, and one command, `vibey-gh push-scope`.
- **It reads git's pre-push stdin, all of it, once**, in the hook `vibey-gh install` renders
  (`templates/githooks/pre-push`, and its rendered copy `.githooks/pre-push`), before anything
  else can consume it, and hands every line on to the chained `pre-push.local`. It is not a
  wrapper around each hook in `.pre-commit-config.yaml`, and that is deliberate: pre-commit
  reads only the **first** line of pre-push stdin and exports only that ref
  (`PRE_COMMIT_REMOTE_BRANCH`, `PRE_COMMIT_FROM_REF`/`TO_REF`), so a per-hook check reading
  those variables would pass `git push origin <heartbeat>:refs/x main`, whose first ref is a
  heartbeat and whose second is a branch. One check at the point where the list is complete,
  in front of every heavy hook, is the single scope check they all sit behind.
- **It asks git about the objects**: `cat-file -t` must say `commit` (so an annotated tag is
  never peeled into the commit it points at), the commit must have no `parent`, and its tree
  must be the empty tree as `git hash-object -t tree /dev/null` computes it in this repository,
  so a SHA-256 repository is judged in its own format.
- **It fails closed.** A branch, a tag, a non-empty tree, a commit with a parent, a deletion,
  an object that is not a commit, an object git cannot read, a line git would never write, or
  no refs at all — each carries code. The hook ends early only on the exact token
  `carries-no-code` on stdout; an older `vibey-gh` without the command, a crash, or a stub that
  exits 0 for everything prints no token, and the full gate runs.
- There is no flag, variable or file that asks for the exemption. **This is the gate applying
  its own rule, not a caller skipping it**: a heartbeat that carried one file, or rode beside a
  branch, is judged in full. Each refused case is a test (`test/test_push_scope.py`, and end to
  end through a real push in `test/test_push_scope_hook.py`).

### 2. `beat()` drops `--no-verify`, and `--force` becomes a compare-and-swap

The heartbeat pushes through the checkout's own gate. The bare `--force` is also gone, because
12.d allows no unattended act that cannot be undone and a bare force replaces whatever the ref
holds, including a value this machine never saw. `beat()` reads the ref's current value with
`ls-remote`, fetches it if absent locally, confirms with `PushScope.is_empty_root` that it is
itself a heartbeat, and pushes with `--force-with-lease=<ref>:<that value>` (an empty lease
when the ref does not exist). Only that exact heartbeat is ever replaced; a concurrent write,
or anything on the ref that is not a heartbeat, is refused and left as it was. Replacing a
commit that carries nothing, and only the one that was read, is not an irreversible act.

### 3. An honest heartbeat

`beat()` now takes a `LaneReadinessInterface` and publishes only when the lane can serve.
`SovereignLaneReadiness` (`vibey_gh/sovereign_lane.py`) reads, never assumes, two things:

- **the runner**: a self-hosted runner carrying `[pr_automation.fallback] runner_label` is
  registered with the repository `[runners]` declares and GitHub reports it `online` (busy
  counts: it takes the next job when it finishes). Read from `repos/<owner>/<name>/actions/runners`
  with the runner's own file-based login (`[runners] gh_config_dir` as `GH_CONFIG_DIR`, every
  ambient token stripped) — the one credential on the machine with the Administration
  permission that API needs — through `SovereignRunner.registered_runners`, which never
  surfaces gh's output;
- **the model**: the endpoint `[pr_automation.fallback] base_url` answers and holds `model`,
  read through the fit's `OllamaModelSampler`.

Anything else — no runner, one offline, a listing that could not be read, a model endpoint
that did not answer — withholds the heartbeat with the reason and pushes nothing, so the ref
goes stale on its own and the gate falls back honestly. `--beat` exits non-zero and, with
`--record <file>`, writes what it did (published or withheld, and why) for `heartbeat status`.

The workflow side is unchanged: it still cannot ask GitHub (`GITHUB_TOKEN` cannot hold
`administration: read`) and still reads only the ref's age. What changed is that the age now
means what it says.

### 4. The timer is declared

`vibey-gh heartbeat install | status | uninstall`, and `vibey-gh runner install` / `runner
uninstall` do the same for the heartbeat alongside the runner. From `[runners]` and
`[pr_automation.fallback]` it renders a **launchd agent on macOS** or a **systemd user service
and timer on Linux** (Ubuntu LTS is first-class, #1116); `[runners] heartbeat_scheduler` picks
one explicitly. It runs `python -m vibey_gh.cli sovereign --beat --record <file>` from the
repository's main checkout every `heartbeat_interval_minutes` — 0 takes half of
`heartbeat_max_age_minutes`, and anything over half is refused, so one missed beat never
stales the lane.

Render refuses an interpreter, a `vibey_gh`, or a log directory under a temporary directory
(a reboot empties it: this machine lost `/private/tmp` the day this was written) or inside a
git work tree (a lane's worktree is deleted when the lane ends; a checkout's virtualenv changes
under every sync), and a checkout that is a linked worktree. The interpreter is the one running
the install unless `[runners] heartbeat_python` names another; the `vibey_gh` location is asked
of that interpreter exactly as the timer will run it. Nothing is loaded unless `--load` is
given; `uninstall` is a dry run until `--apply`, and moves units into
`<install_dir>/retired-units/` rather than deleting them. `status` reports the units present
and current (judged against the interpreter the installed unit runs, not the one running
`status`), whether the timer is loaded, and the last beat's age and result from its record;
it exits non-zero unless the last beat was published inside the trust window.

## Consequences

- The heartbeat reaches the remote through the same gate as everything else and in seconds;
  the gate's exemption is a rule anyone can read in one sentence and check against the objects.
- A fresh heartbeat now means a runner was online and the model answered when it was written.
  A heartbeat that stops is still indistinguishable from a machine that stopped, which is
  still the point.
- `vibey-local-authority` is retired. Its successor is installed by
  `vibey-gh heartbeat install --load` from the main checkout, with a `vibey-gh` installed
  outside any checkout (for example `uv tool install vibey`). `vibey-gh local-authority`, the
  command that pushes green local branches when the paid lane is capped, is unrelated and
  unchanged.
- The hand-written agent could be restored by nobody; the declared timer can be restored by
  anyone with a clone.

## Alternatives rejected

- **Keep `--no-verify`, with a written exception.** 12.d admits none, and the exemption would
  cover whatever the push carried.
- **Push the heartbeat from a separate bare repository with no hooks.** A means whose purpose
  is to make the check stop applying, by another name.
- **Wrap each heavy hook with a check on `PRE_COMMIT_*`.** Passes a heartbeat riding beside a
  branch, as §1 shows.
- **An environment variable the heartbeat sets to say "nothing to judge".** A caller's flag.
- **Keep the bare `--force`.** It replaces a value it never read.
