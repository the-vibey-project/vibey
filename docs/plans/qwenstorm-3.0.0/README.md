# QwenStorm 3.0.0: working material

Working material for vibey 3.0.0. It is not reference documentation: `docs/plans/**` is left
out of the site build on purpose. This folder is the planning record of the QwenStorm that
brings the code up to the canon ratified in #325, #384, #385, #390 and #392, and to the
operator's standards of 2026-09-22:

- the installer installs everything a developer needs on Arch Linux and macOS;
- persistence goes through an ORM, always behind interfaces;
- every interface has a comprehensive in-memory fake, so tests need no outside service.

A local sovereign loop implements each lane: gpt-oss:20b on Ollama, one instance per model
under sub-doctrine 8.c. Every lane is then reviewed against its spec and its diff before it
becomes a pull request. The first verified wave is `feat/qwenstorm-3.0.0-wave-1`.

## Reading order

1. `STORM-CONTEXT.md`: the settled law, the standards and the operator's rulings. It overrides
   everything older.
2. `SPEC-TEMPLATE.md` and `EDITING-RULES.md`: what a lane spec contains, and the editing rules
   every lane is given.
3. `specs/ADR-*.md`: the draft ADRs.
   - `ADR-rabbitmq-queue.md` is ADR-0044, already merged.
   - `ADR-test-harness-queue.md` is ADR-0045, amended by `ADR-test-harness-fakes-amendment.md`.
   - `ADR-two-loops.md` is ADR-0046.
   - `ADR-surface-lanes.md` is ADR-0047.
   - `ADR-installer.md` and `ADR-orm.md` are not numbered yet.
4. `specs/<wave>-*.md`: one spec per lane, with each wave's dependency order in
   `specs/<wave>-queue.txt`. The waves are installer, orm, fakes, harness, loops, surfaces,
   split (the children of oversized issues), gap and roadmap.
5. `issue-audit/`: the audit of the issue suite on 2026-09-22.
   - `storm-audit.md`, `roadmap-audit.md` and `gaps.md` hold the findings.
   - `updates/<N>.md` holds the rewritten issue bodies.
   - `storm-disposition.tsv` records what happens to each open issue.
   - `review-followups.md` lists the reconciliations made between waves.
6. `tools/`: the storm machinery.
   - `storm-queue.sh` runs one lane at a time (unattended mode via an `UNATTENDED` file).
     It asks `storm_queue.py next` what to run, so the runner and the priority CLI share one
     resolver and cannot disagree.
   - `storm-priority.py` is the priority lane (ADR-0054). `push SLUG ISSUE [--deps a,b]`
     prioritises a lane, first appending it to `queue.txt` if it is new; `bump SLUG`
     prioritises a queued lane; `unbump SLUG` undoes that; `list` prints the order the storm
     will run, with blocked and settled lanes and skipped `queue.txt` lines marked.

     The contract, numbered as ADR-0054 numbers it:

     1. Next means next after whatever is running. A running lane is never interrupted.
     2. Prioritised lanes run first pushed first, ahead of every other `queue.txt` line.
        Re-bumping a lane keeps its place.
     3. A push also prioritises every dependency that is not yet integrated, transitively
        and dependencies first, and says what it moved. A dependency that can never finish
        (abandoned, queued nowhere, or in a cycle) refuses the push, naming it. A lane still
        starts only once all its dependencies are in `integrated.txt`.
     4. Every caller must run as the account that owns the storm's `queue.txt`, checked by
        uid; the name recorded comes from the password database, never `$USER`. With no
        `--source` that caller is the operator; automation passes `--source NAME`, and NAME
        must be listed under `[priority] sources` in `storm.toml`. A process carrying
        `VIBEY_STORM_LANE`, which every lane command inherits, is refused. Nothing reads a
        label or an issue to decide priority, and no other gate is bypassed: `storm_trust.py`
        judges a pushed lane's issue when it starts, and `lane-verify.py` still refuses
        forbidden paths.
     5. Every request, whether it moved something, moved nothing or was refused, is one JSON
        line appended to the priority log (`[priority] log` in `storm.toml`, else
        `priority.log` beside the ledgers) and one line in `progress.log`, with outside text
        escaped. Authorisation runs before any lookup. The order is always the log's replay;
        nothing is edited in place.
     6. `unbump` undoes exactly what the push or bump moved, by derivation: the priority lane
        is exactly the lanes pushed or bumped by name and not since un-bumped, plus all their
        unfinished transitive dependencies, first in first. Un-bumping a lane removes it from
        that named set, and every lane nothing named still requires leaves with it, so no
        orphan remains. It is refused, naming them, while another named lane depends on it.
        The `unbump` line records its resulting `removed` list, so replay is exact. A lane
        bumped by name keeps its place.
     7. `push` enqueues a new lane already prioritised, in one step. Pushing or bumping a
        finished lane (settled, or run and awaiting review) is a recorded no-op.

     Beyond the contract:

     - **What the authorisation does not do.** Lanes run as the operator's uid today, so a
       lane's process can unset `VIBEY_STORM_LANE`, claim a declared source, or append to
       the priority log and `queue.txt` directly. The marker catches mistakes; it does not
       contain a hostile lane, and a source name identifies automation without
       authenticating it. The fix is to run lanes as a separate low-privilege OS user:
       `specs/storm-lane-os-user.md`.
     - Slugs, dependencies and source names must match `[A-Za-z0-9][A-Za-z0-9._-]*` with no
       `..`. A `queue.txt` line outside that is skipped, never run, and said in
       `progress.log`.
     - Replay refuses a malformed entry, which checks shape, not who wrote it. After every
       append a witness (`.priority.log.witness`, which a `priority.log*` glob does not
       match) records the log's length; it is fsynced, and so is its directory. The
       witness is read under the same lock as the log, so a read racing an append never
       reports a false truncation. A log that is gone after it existed, shorter than
       recorded, or whose witness is empty is an unknown order: the storm waits and says
       so, and no request, not even a refusal, re-creates it (exit 3).
     - **The way out of "order unknown"** is `storm-priority.py reset --reason TEXT`, and the
       message names it. Only the operator can run it (the storm owner's uid, never a
       `--source`, never from inside a lane), and only while the log is NOT readable: a
       reset never replaces a readable order. It keeps the old file, if any, as
       `priority.log.abandoned-<stamp>`, starts a new log whose first line is a `reset`
       event naming the length it abandons and the reason, rewrites the witness, and says in
       `progress.log` that the prior priority order was abandoned. Every lane then runs in
       `queue.txt` order until pushed again. This also recovers a fresh storm root whose
       tracked evidence watermark still carries an offset from an earlier root: the
       watermark offset is set aside once the log begins with a reset that abandoned it, and
       `storm-evidence.py` re-bases on that line and reports the discontinuity as a gap.
     - Authority is checked before the lock, so a caller without write access to the storm
       is refused (exit 1), not crashed; if the refusal cannot be written it says "could not
       be recorded (no write access)".
       `storm-evidence.py` consumes the log by byte offset with the other ledgers, and
       counts lane starts and ends only from `progress.log`.
     - Exit codes: 0 done, 1 refused (not authorised), 2 refused (cannot be carried out),
       3 order unknown, 4 crashed.
   - `lane-setup.sh` and `qwenlane.py` set up and drive a lane.
   - `lane_environment.py` gives a lane's commands its own `.venv` and nothing that points
     outside it, and refuses a lane whose `python` resolves elsewhere.
   - `lane_watchdog.py` bounds each lane attempt. It enforces a per-attempt and a per-lane
     wall clock and a stall watchdog, declared in `storm.toml` `[lane]`. A hung attempt
     cannot hold up the one-at-a-time queue.
   - `push_gate.py` is the shared push lock as code, and its reaper. Push with
     `python3 tools/push_gate.py run -- git push origin HEAD:<branch>`: it waits for the lock,
     runs the push in a process group of its own, logs its output, and always releases,
     including on a signal. `status` says who holds the lock and what it is doing; `acquire`
     and `release TOKEN` are the shell form, and only the token's owner can release. The
     lock is an atomic `mkdir` with an owner record inside (pid, process group, branch,
     worktree, start time, uid), at `[push_gate] lock` in `storm.toml`, else `.push-lock`
     beside the storm root.

     The reaper (`push_gate.py reap`, `--dry-run` to only report) runs first in every
     `storm-cycle.py` pass. It acts on exactly three measured conditions, each declared in
     `[push_gate]` with a default:
     - the holder is gone and nothing of its push still runs: the lock is released;
     - the push's own process group used under `idle_cpu_seconds` (2) of CPU over
       `idle_window_seconds` (600), sampled with `ps -o time` pass by pass;
     - it has held the lock past `wall_ceiling_seconds` (3600).

     Before a kill it writes evidence: the process tree, the push log's tail, and the suite's
     stacks, from `py-spy dump` or else SIGUSR1, which `tests/conftest.py` arms. It then
     sends SIGTERM to that group, waits `kill_grace_seconds`, and sends SIGKILL. It never
     signals a process outside the group, a group taken by `acquire` (the shell's own), or a
     group holding a `protected` process such as Ollama or the runner. Each reap is one line
     in the append-only reap log, and the push reports `reaped: hang` (exit 124), not a test
     failure. An unreadable process table (the sandbox refuses `ps`) is reported as unknown
     and is never taken for idle. The classes are declared in
     `interfaces/push_gate_interface.py`.

     A lock taken the old way, with a bare `mkdir` and no owner record, is traced to its
     push by process. The push must meet all of these conditions:
     - it is the only `git push` that started within `ownerless_match_seconds` (5) of the
       lock's mtime;
     - it stands in one of `worktree_roots`, or `git -C` points it there (the default root is
       the lock's own directory);
     - its process group holds nothing but that push, its descendants, and the shells above
       it.

     A push that meets them is judged by the same idle and ceiling rules. It is killed with
     evidence first, and the reaper removes the lock that the dead shell's `rmdir` never
     reached. A push that does not meet them is reported as unknown and never killed.

     The reaper also runs on a schedule of its own, whether or not a storm is running. The
     unit files are the tracked templates in `templates/`:
     - `push_gate.py install-schedule` installs a launchd agent on macOS, or a systemd user
       timer on Linux, and runs `reap` every `schedule_seconds` (90);
     - `uninstall-schedule` removes it, and `schedule-status` reports its state;
     - `--target cron` only prints a cron line.

     The storm cycle's own step stays in place. A non-blocking reap lock makes two
     overlapping passes safe: the second one stands aside.
   - **Pushing in this repository.** Every push, by a lane, a tool or a person, uses one
     recipe:
     `python3 <storm>/tools/push_gate.py run -- git push origin HEAD:<branch>`.
     `lane-publish.py` and `storm-snapshot.py` push this way too, and a meta test fails any
     storm tool that builds a bare `["git", "push", ...]`. From a checkout with no storm, set
     `VIBEY_PUSH_LOCK` to the machine's shared lock. Without it the tool refuses rather than
     derive a private lock. See CONTRIBUTING.md.
   - `storm_trust.py` contains forge text where it enters (sub-doctrine 12.j, ADR-0053).
     A lane starts only when every account that opened, edited or renamed its issue is in
     `[unattended_approval] authors`. That list is read from the integration branch's
     reviewed history, never the working tree. The issue then reaches the model only
     inside a fenced block that states its provenance. `lane-verify.py` refuses a lane that
     touches any `forbidden_paths` entry from the same grant. The classes are declared in
     `interfaces/storm_trust_interface.py`.
   - `file-suite.py` files the suite as issues. It is resumable and paced.
   - `lint-specs.py` is the check run before filing.
   - `storm_durability.py` is the durability gate (sub-doctrine 10.h, ADR-0057). It resolves
     the storm home, and `check` refuses with exit 78 when the home, the storm root or a
     named path lies on storage the operating system empties. `status` reports each one,
     `worktree NAME` prints where a worktree goes, and `storm-watch.py` reports it as the
     `durable` check. The classes are declared in `interfaces/storm_durability_interface.py`.
   - `storm_checkpoint.py` holds `StepJournal`, the per-step results file a long measurement
     resumes from. It is declared in `interfaces/storm_checkpoint_interface.py`.
7. `bench/`: the 2026-09-22 benchmark. gpt-oss:20b on Ollama finished a 10-turn session in
   86 s, against 215 s for Qwen2.5-Coder-14B on llama.cpp. Both benchmarks resume:
   `bench-run.sh` skips every label whose session is already in `results.jsonl`, and
   `host-sweep.py` journals each configuration as it finishes and measures only the rest.

## Where storm work lives, and how often it is saved

On 2026-09-24 at about 09:09 EDT the operator's Mac rebooted in the middle of the storm. macOS
empties `/private/tmp` at boot, and the storm root, every lane worktree, the push lock, the
benchmark evidence and the scratch probes were all under `/private/tmp/claude-501/storm/`.
Everything not yet committed was lost: about 1.5 hours of concurrency-sweep measurements, a
paper draft and three lanes of fixes. Only committed work survived. Sub-doctrine 10.h and
ADR-0057 are the rule and the record.

**One declared home.** All storm work on a machine lives under the storm home:
`VIBEY_STORM_HOME`, else `[paths] home` in the storm root's `storm.toml`, else the platform's
default. On macOS that is `~/git/vibey-storm`. On Linux (Ubuntu LTS, Arch) it is
`$XDG_DATA_HOME/vibey/storm`, falling back to `~/.local/share/vibey/storm`. Windows is not
supported yet (#1097): the gate refuses there rather than guess. The worktrees are
`<home>/<name>`. The shared push lock and its state are
`<home>/.push-lock` and `<home>/.push-lock.gate`. A storm root is `<home>/<storm>`, for example
`<home>/qwenstorm-3.0.0`, and holds `storm.toml`, the queue, the ledgers, `lanes/`,
`integration/` and `scratch/`.

```bash
python3 tools/storm_durability.py status          # the home and the storm root: durable or not
git worktree add "$(python3 tools/storm_durability.py worktree fix-x)" -b fix/x origin/develop
```

**A gate, not a judgement.** `storm-queue.sh`, `lane-setup.sh`, `storm-cycle.py --run` and both
benchmarks refuse to start, with exit 78 and the key to change, when anything they would write
resolves under a volatile location. Symlinks are followed, so `/tmp` is caught as
`/private/tmp`. On macOS the volatile locations are `/tmp`, `/var/tmp` and `/var/folders`. On
Linux they are `/tmp`, `/var/tmp` (systemd-tmpfiles), `/dev/shm` and `/run/user/<uid>`. On
both, `$TMPDIR` and `$XDG_RUNTIME_DIR` count too. One class per platform decides both lists
(`PlatformStorage` in `storm_durability.py`). A test's throwaway storm passes only by
declaring itself so in its own `storm.toml`, with a reason: `[durability] disposable = "..."`.

**Moving a storm that is on volatile storage.** Stop it (`storm-stop.py --stop`). Commit and
push what can be pushed. Recreate the storm root under the home, and link `tools/` into it
again. `git worktree prune` in the main clone clears the worktrees a reboot already took. The
durable record, `integrated.txt`, `abandoned.txt` and the priority log, is what matters: copy
it across before starting.

**Commit early, push often.**
- Commit as soon as a change is coherent, not when it is finished.
- Push work in progress to a draft pull request at least every 30–45 minutes.
- A long measurement writes each step to a `StepJournal` as it finishes, and resumes.
- Lanes resume at lane granularity already: a lane without `.qwenstorm/result.json` runs
  again.

A reboot, a crash or a lost disk then costs minutes of work, not hours. CONTRIBUTING.md has
the same rule for every contributor.

Lane clones have no remote by design (lane-setup.sh), so a lane's work reaches a remote only
when `lane-publish.py` publishes it. An automatic "checkpoint" that pushes a lane's
work-in-progress as a `wip:` commit is not built. It would need a remote the lane is
deliberately denied. Each push also runs the full pre-push gate (minutes, one at a time under
the machine's push lock), and a red WIP cannot pass it. Nothing may skip that gate (12.d).
What protects a lane's uncommitted work instead is that it now lives on durable storage.

The specs and audit notes here write the storm root as `STORM/`, as `STORM-CONTEXT.md`
defines it. Older copies named a directory under `/private/tmp`, which the reboot emptied. Read
those paths as relative to this folder.
