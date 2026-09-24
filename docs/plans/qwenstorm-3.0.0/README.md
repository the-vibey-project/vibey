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
     prioritises a queued lane; `unbump SLUG` returns it to its `queue.txt` place; `list`
     prints the order the storm will run, with blocked and settled lanes marked.
     - A prioritised lane runs next after the lane running now. It never interrupts it.
     - Prioritised lanes run first pushed first, ahead of every other `queue.txt` line.
     - A push also prioritises every dependency that is not yet integrated, transitively and
       in dependency order, and says what it moved. A lane still starts only once all its
       dependencies are in `integrated.txt`.
     - Only the operator may change the lane: the account that owns the storm, running the
       CLI locally. Automation may too if it passes `--source NAME` and `storm.toml` lists
       NAME under `[priority] sources`. Anything else is refused, recorded and reported
       (sub-doctrine 12.j). Nothing reads a label or an issue to decide priority.
     - Admission still applies: `storm_trust.py` judges a pushed lane's issue when it
       starts, and `lane-verify.py` still refuses forbidden paths.
     - Every push, bump, un-bump and refusal is one JSON line appended to the priority log
       (`[priority] log` in `storm.toml`, else `priority.log` beside the ledgers) and a
       plain line in `progress.log`. The order is always the log's replay; nothing is edited
       in place. `storm-evidence.py` consumes the log by byte offset with the other ledgers.
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
