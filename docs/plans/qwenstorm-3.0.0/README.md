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
   - `lane-setup.sh` and `qwenlane.py` set up and drive a lane.
   - `lane_watchdog.py` bounds each lane attempt. It enforces a per-attempt and a per-lane
     wall clock and a stall watchdog, declared in `storm.toml` `[lane]`. A hung attempt
     cannot hold up the one-at-a-time queue.
   - `file-suite.py` files the suite as issues. It is resumable and paced.
   - `lint-specs.py` is the check run before filing.
7. `bench/`: the 2026-09-22 benchmark. gpt-oss:20b on Ollama finished a 10-turn session in
   86 s, against 215 s for Qwen2.5-Coder-14B on llama.cpp.

The paths inside these files point at the machine that ran the storm
(`/private/tmp/claude-501/storm/qwenstorm-3.0.0/`). Read them as relative to this folder.
