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
     6. `unbump` undoes exactly what the push or bump moved: the lane, plus each dependency
        it pulled forward that no other prioritised lane needs. A lane pushed or bumped by
        name keeps its place. Un-bumping a lane another prioritised lane depends on is
        refused, naming the dependents.
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
     - Replay refuses a malformed entry, which checks shape, not who wrote it. A log that is
       gone after it existed is an unknown order: the storm waits and says so.
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
   - `storm_trust.py` contains forge text where it enters (sub-doctrine 12.j, ADR-0053).
     A lane starts only when every account that opened, edited or renamed its issue is in
     `[unattended_approval] authors`. That list is read from the integration branch's
     reviewed history, never the working tree. The issue then reaches the model only
     inside a fenced block that states its provenance. `lane-verify.py` refuses a lane that
     touches any `forbidden_paths` entry from the same grant. The classes are declared in
     `interfaces/storm_trust_interface.py`.
   - `file-suite.py` files the suite as issues. It is resumable and paced.
   - `lint-specs.py` is the check run before filing.
7. `bench/`: the 2026-09-22 benchmark. gpt-oss:20b on Ollama finished a 10-turn session in
   86 s, against 215 s for Qwen2.5-Coder-14B on llama.cpp.

The paths inside these files point at the machine that ran the storm
(`/private/tmp/claude-501/storm/qwenstorm-3.0.0/`). Read them as relative to this folder.
