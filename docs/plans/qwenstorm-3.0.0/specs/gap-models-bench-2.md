## Title
feat(qwenloop): `qwenloop model bench <entry>` runs the bench and appends dated evidence to the tree

## Why
8.d's catalogue must name "the evidence behind [each choice] and the date"
(`src/vibey_tools/gh/docs/doctrines.md:236-269`), and 10.f and 12.c require that evidence to be
reproducible from the repository. The measurement behind the GPT-OSS 20B default (85.6 s for
ten turns at 17,122 context tokens on Ollama, against 212–220 s for Qwen2.5-Coder-14B on
llama.cpp, measured 2026-09-22) exists only in
`STORM/bench/results.jsonl` (`issue-audit/gaps.md` D3).

`gap-models-bench-1` added `ModelBench`. This lane adds:
- the command;
- a script built from the repository itself, so the bench is reproducible at a named commit;
- an in-tree evidence file that the command appends to, seeded with the 2026-09-22 rows.

Paths are qwenloop's. If `loops-rename` landed first, use the renamed tenant.

## Required behaviour
1. `src/vibey_runners/qwen/src/qwenloop/cli/app.py` gains `@model_app.command("bench")`
   `model_bench(...)`, beside `model_list` (`:476-481`). Use edit_file only; the file is 761
   lines. Its arguments:
   - `entry: str`, a catalogue entry name such as `gpt-oss-20b`;
   - `turns: int = typer.Option(10, "--turns", min=1)`;
   - `repo: Path = typer.Option(Path("."), "--repo")`;
   - `evidence_file: Path | None = typer.Option(None, "--evidence-file")`.
2. Behaviour:
   - It resolves `ModelCatalogue().get(entry)` (from `split-383-1-model-catalogue`). An
     unknown entry exits 2 and prints the `KeyError` message.
   - The model comes from the catalogue entry's Ollama tag. It loads the config with
     `_load_config(model=<tag>)` (`:167`) and attaches with `_attach(config)` (`:204-212`).
     If the entry has no Ollama artifact it exits 2 with
     `"entry <name> has no Ollama tag; the bench attaches to a served endpoint"`.
   - It checks the endpoint first with `server.check()`. A failure exits 1, printing the
     check's message.
   - It builds the `BenchScript` with a new small class `BenchScriptLoader` in
     `src/vibey_runners/qwen/src/qwenloop/infrastructure/bench_script.py`, with interface
     `infrastructure/interfaces/bench_script_interface.py`. `load(repo: Path) -> BenchScript`
     reads, relative to `repo`:
     - `system` = `"You are a careful software engineer working in a git worktree."`;
     - `opening`: the first 6,000 characters of `docs/plans/implementation-plan.md`, followed by
       `"\n\nStart by stating which file you will read first."`;
     - `tool_results`: the constant `BENCH_FILES`, each file's first 7,000 characters. The
       list is `bench.py:18-29`'s ten paths: `src/vibey/infrastructure/engines/local_engines.py`,
       `src/vibey/infrastructure/engines/descriptors.py`,
       `src/vibey/infrastructure/config_loader.py`,
       `src/vibey/infrastructure/cluster_preflight.py`,
       `tests/infrastructure/engines/test_local_engines.py`, `src/vibey/domain/config.py`,
       `src/vibey/bootstrap.py`, `src/vibey/cli/main.py`, `tests/test_bootstrap.py` and
       `tests/cli/test_operational_commands.py`.
     - A missing file raises `FileNotFoundError` naming it, and the command exits 2 with the message.
   - It runs `ModelBench(server=server, clock=SystemClock()).run(info, script, turns=turns)`,
     using the tenant's existing clock (`infrastructure/clock.py`). It prints one JSON line per
     turn and then the summary.
   - With `--evidence-file`, it appends one JSON line: the summary plus `"entry"`, `"recorded"`
     (today, `YYYY-MM-DD`, from the clock), `"machine"`
     (`{"os": platform.system(), "arch": platform.machine()}`) and `"repo_head"`. The repo head
     is the stripped output of `git -C <repo> rev-parse HEAD`, run through the tenant's
     subprocess seam if one exists. Otherwise it goes through a `HeadReader` class beside
     `BenchScriptLoader` whose runner is injected. Never patch `subprocess`.
3. A new data file `src/vibey_runners/qwen/model-evidence.jsonl` (at the tenant root, not in the
   package) is seeded with five lines, one per recorded 2026-09-22 summary. Each line has:
   - `"method": "bench.py-replay-v1"`;
   - `"recorded": "2026-09-22"`;
   - `"machine": {"os": "Darwin", "arch": "arm64", "note": "M5, 24 GB"}`;
   - `"source": "QwenStorm 3.0.0 bench, results.jsonl"`;
   - the recorded values, exactly:
     - `{"label": "A-baseline", "entry": "qwen2.5-coder-14b", "backend": "llama.cpp", "total_wall_s": 215.0, "mean_gen_tps": 9.3, "final_ctx_tokens": 17658}`
     - `{"label": "D-1slot-f16-32k", "entry": "qwen2.5-coder-14b", "backend": "llama.cpp", "total_wall_s": 212.2, "mean_gen_tps": 9.3, "final_ctx_tokens": 17658}`
     - `{"label": "B-1slot-q8-48k", "entry": "qwen2.5-coder-14b", "backend": "llama.cpp", "total_wall_s": 220.5, "mean_gen_tps": 8.8, "final_ctx_tokens": 17658}`
     - `{"label": "C-1slot-q8-48k-draft", "entry": "qwen2.5-coder-14b", "backend": "llama.cpp", "total_wall_s": 215.6, "mean_gen_tps": 8.9, "final_ctx_tokens": 17658}`
     - `{"label": "E-gptoss-20b-ollama", "entry": "gpt-oss-20b", "backend": "ollama", "total_wall_s": 85.6, "mean_gen_tps": null, "final_ctx_tokens": 17122}`

     The Ollama run reported no server timings, so its throughput is `null`, never `0.0`.
4. A test ties the evidence to the catalogue. Every `entry` in `model-evidence.jsonl` is a
   `ModelCatalogue()` name, and every line has `recorded` matching `^\d{4}-\d{2}-\d{2}$` and a
   `method`.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/cli/app.py`: edit_file only.
- New: `src/vibey_runners/qwen/src/qwenloop/infrastructure/bench_script.py` and
  `src/vibey_runners/qwen/src/qwenloop/infrastructure/interfaces/bench_script_interface.py`
  (export it from `infrastructure/interfaces/__init__.py`).
- New: `src/vibey_runners/qwen/model-evidence.jsonl`.
- Tests: append to `src/vibey_runners/qwen/tests/test_cli.py` for the command, using its
  existing `CliRunner` pattern and a scripted endpoint through the command's declared seams.
  If the command cannot be reached without patching, add a module-level
  `BENCH_FACTORY` seam object that the command reads, and document it. Put the loader,
  head-reader and evidence-file tests in the new file `src/vibey_runners/qwen/tests/test_bench_script.py`.

## Acceptance criteria
- [ ] `qwenloop model bench nope` exits 2 and lists the known entry names.
- [ ] Against a scripted endpoint, `qwenloop model bench gpt-oss-20b --turns 2 --repo <tmp repo with the 11 files>`
      prints 2 turn lines and 1 summary line with `method == "qwenloop-turn-v1"`.
- [ ] With `--evidence-file F` it appends exactly one valid JSON line holding
      `entry`, `recorded`, `machine` and `repo_head`, and it never rewrites earlier lines.
- [ ] A repo missing `src/vibey/bootstrap.py` exits 2 and names the file.
- [ ] `model-evidence.jsonl` holds the five seeded lines exactly, and the catalogue-tie test passes.
- [ ] The qwen tenant's gates pass at its 100% floor.

## Tests to write first (TDD)
- `tests/test_bench_script.py`: `test_loader_reads_the_declared_files_truncated`,
  `test_loader_names_a_missing_file`, `test_head_reader_uses_the_injected_runner`,
  `test_seeded_evidence_names_catalogue_entries_and_dates`.
- Append to `tests/test_cli.py`: `test_model_bench_unknown_entry_exits_2`,
  `test_model_bench_prints_turns_and_summary`, `test_model_bench_appends_one_evidence_line`,
  `test_model_bench_entry_without_ollama_tag_exits_2`.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider && python -m mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
- Running the bench in CI. It needs a served model, so it is operator evidence.
- The llama.cpp managed-server path. The command attaches to a served endpoint; a
  `--managed` flag is a follow-up.
- vibey's ledger (`gap-measure-models`) and docs.

Commit as `feat(qwenloop): model bench command and in-tree model evidence`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
