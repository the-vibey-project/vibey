# 0057 — Storm work lives on durable storage, is committed and pushed often, and a tool refuses volatile paths

**Status:** proposed · **Date:** 2026-09-24 · **Cites:** sub-doctrine 10.h, which this record implements, and 10.f, 12.c, 12.d, 12.e, 12.h · **Related:** ADR-0048, ADR-0051 · **Evidence:** the reboot of the operator's Mac at about 09:09 EDT on 2026-09-24, which emptied `/private/tmp` in the middle of the QwenStorm run

**Owes:** 10.h is the conduct, and it is drafted in the same pull request for the operator's
ratifying merge (ADR-0020: the record argues, the canon states). This record also owes the
advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and `docs/index.md`
(`tests/meta/test_adr_counts.py`), and a nav entry in `properdocs.yml`.

## Context

The storm put everything it had under `/private/tmp/claude-501/storm/`:

- every lane worktree, whether a person's, an agent's or the local model's;
- the storm root: `storm.toml`, the queue, the ledgers, `lanes/`, `integration/` and
  `scratch/`;
- the shared push lock and its state;
- the benchmark evidence and the scratch probe scripts;
- the pre-commit cache.

That place was chosen because it was writable and at hand. No tool or document said it
was durable, and none checked.

macOS empties `/private/tmp` at boot. At about 09:09 EDT on 2026-09-24 the Mac rebooted, and
everything not yet committed was lost:

- about 1.5 hours of concurrency-sweep measurements. The sweep held its rows in memory and
  printed them once, at the end;
- a paper draft;
- three lanes of uncommitted fixes.

Committed work survived only because it lived in the main repository's refs.

Three separate failures combined. Work was placed on storage the operating system discards.
Nothing refused to place it there. And a long measurement kept everything until the end, so
one interruption cost the whole run. The llama-server benchmark had the same defect in
another form: it truncated its results file every time it started.

## Decision

**One declared durable home.** All storm work on a machine lives under the storm home. It is
declared (12.c, 12.h), and the first of these that is set wins:

1. `VIBEY_STORM_HOME`;
2. `[paths] home` in the storm root's `storm.toml`, which extends the `[paths]` section that
   already declares `repo`, `python` and `slug`;
3. the platform's default.

Worktrees are `<home>/<name>`. The shared push lock is `<home>/.push-lock`, and it is now
`push_gate.py`'s default. A storm root is `<home>/<storm>`. The name is "home" because "storm
root" already means the directory holding `storm.toml` in every tool, and a second meaning
for the same words would be a trap.

**The platform decides the default, in one class.** `PlatformStorage` in
`tools/storm_durability.py`, with an interface beside it, is the only place that knows which
operating system it is on:

- **macOS** defaults to `~/git/vibey-storm`. That is where the storm moved after the reboot,
  and where the operator's worktrees already are. It sits beside the main clone.
- **Linux** (Ubuntu LTS is first-class, #1116; Arch as before) defaults to
  `$XDG_DATA_HOME/vibey/storm`, else `~/.local/share/vibey/storm`. That is the XDG place for
  user data.
- **Windows** (#1097) refuses rather than guess. Its subclass is still to write:
  `%LOCALAPPDATA%` is durable, and `%TEMP%` and `%TMP%` are volatile.

**A gate, not a judgement (12.d).** `storm-queue.sh`, `lane-setup.sh`, `storm-cycle.py --run`
and both benchmarks consult `DurabilityGate` before they write. It resolves paths through
symlinks, because on macOS `/tmp` is `/private/tmp`. It exits 78 (`EX_CONFIG`) with a message
naming the key that moves the work when the home, the storm root or a named path lies under
one of these:

- on macOS: `/tmp`, `/private/tmp`, `/var/tmp` and `/var/folders`;
- on Linux: `/tmp`, `/var/tmp`, `/dev/shm` and `/run/user/<uid>`;
- on both: `$TMPDIR` and `$XDG_RUNTIME_DIR`.

`storm-watch.py` reports it as the `durable` health check, and a volatile storm is TROUBLE
there: a storm under `/tmp` is healthy right up to the reboot that deletes it.

A throwaway storm, such as a test's, passes only by saying so in its own `storm.toml`, with a
reason (`[durability] disposable = "..."`), and every tool that passes it prints the reason.
The gate never decides for itself that work is disposable. Nothing moves or deletes a storm it
finds on volatile storage. It is reported and refused.

**Long measurements checkpoint per step.** `StepJournal` (`tools/storm_checkpoint.py`)
appends one JSON line per finished step and fsyncs it before the next step starts. On
restart, a measurement asks the journal what is done and runs only the rest. A line torn by a
crash is skipped and counted, never glued to the next record. `host-sweep.py` journals each
configuration. `bench-run.sh` no longer truncates `results.jsonl`, and it skips every label
whose session is already recorded. Lanes already resume at lane granularity: a lane without
`result.json` runs again.

**Commit early, push often.** CONTRIBUTING.md, the storm README and the four agent-skill trees
say it the same way:

- commit as soon as a change is coherent;
- push work in progress to a draft pull request at least every 30–45 minutes;
- let long measurements persist and resume per step.

**The text may not reintroduce it.** `tests/meta/test_no_volatile_work_paths.py` reads every
tracked text file for a literal volatile path. The genuinely ephemeral hits are an explicit
allow-list with the reason beside each entry: a CI runner's scratch, a socket, a throwaway
render, a sentence stating the rule. An entry that stops matching fails too, so the list
shrinks when its reason goes away. 654 lane specs that ended "See
/private/tmp/…/SPEC-TEMPLATE.md." now write the storm root as `STORM/`, as `STORM-CONTEXT.md`
defines it.

## Alternatives not taken

- **An XDG data directory on macOS too.** It is consistent, but it moves the operator's live
  worktrees for no gain. On a Mac, a checkout a person `cd`s into belongs where they look for
  checkouts. The platform class keeps both answers in one place.
- **A reboot-time rescue, copying `/tmp` somewhere safe.** At boot it is already too late, and
  on a crash or a power cut it never runs. The fix is not to be there.
- **An automatic `storm checkpoint` that pushes a lane's work in progress as a `wip:`
  commit.** Not built:
  - lane clones have no remote, by design. `lane-setup.sh` denies a local model any way to
    push, and a checkpoint would need exactly that;
  - every push runs the full pre-push gate, which takes minutes and runs one at a time under
    the machine's push lock;
  - red work in progress cannot pass that gate, and nothing may skip it (12.d).

  What protects a lane's uncommitted work instead is that it now lives on durable storage.
  For people and agents, the rule is the draft pull request. An opt-in helper for their own
  branches, which commits and pushes when the gates pass, is possible next work.
- **Letting an environment variable switch the gate off, for tests.** That would be a means
  whose purpose is to make a check stop applying, and a shell profile would carry it into a
  real storm. The disposable declaration is scoped to one storm root and gives its reason
  where the root is.

## Consequences

A storm set up the old way, under `/private/tmp`, now refuses to start and says how to move.
`push_gate.py`'s default lock is `<home>/.push-lock`, so a shell recipe still taking a bare
`mkdir /private/tmp/claude-501/storm/.push-lock` no longer excludes a push through the gate. The
recipes move with this change, and lanes should be told.

`push_gate.py` takes its default from the home but does not call the gate itself. A lock
declared onto volatile storage is still taken there. The class exists for it to call.

The pre-commit cache set by `.claude/settings.json` (`PRE_COMMIT_HOME=.cache/pre-commit`,
inside each worktree) is a regenerable cache. It is durable now that worktrees are, and it is
left as it is.

The rule outlives the storm tools. 10.h binds any future runner, measurement or agent that
keeps work in progress, whatever it is written in.
