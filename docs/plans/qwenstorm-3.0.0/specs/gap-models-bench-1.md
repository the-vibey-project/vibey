## Title
feat(qwenloop): a model bench that replays a fixed ten-turn session through the loop's own chat client

## Why
Sub-doctrine 8.d (`src/vibey_tools/gh/docs/doctrines.md:236-269`) makes GPT-OSS 20B the era's
default on measured evidence. Its catalogue "names, for each choice, the evidence behind it
and the date". 8.g (`:316-325`) chooses defaults "from live evidence, never from assumption".
10.f and 12.c require that the evidence be reproducible from the tree.

The measurement that chose the default lives only outside the repository:
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/bench/bench.py` and `results.jsonl`
(`issue-audit/gaps.md` D3, lines 282-287). That script also bypasses the loop, posting raw
requests. This lane moves the method into qwenloop's application layer, driven through the
same `InferenceServer.chat_stream` a run uses (10.e). A bench then measures what a lane
actually experiences. `gap-models-bench-2` adds the command and the evidence file.

Paths are qwenloop's. If ADR-0046's rename (`loops-rename`) has landed first, apply the same
change under `src/vibey_runners/sovereign/src/sovereignloop/`.

## Required behaviour
1. New module `src/vibey_runners/qwen/src/qwenloop/application/bench.py`. It has the provenance
   header, copied from `application/runner.py:1`, and defines:
   - `BENCH_METHOD: Final = "qwenloop-turn-v1"`. It is recorded with every result, because the
     2026-09-22 numbers used a different method (`bench.py`: no tools, `max_tokens=160`) and
     the two are not directly comparable (10.f).
   - `@dataclass(frozen=True, slots=True) class BenchScript` with fields `system: str`,
     `opening: str` and `tool_results: tuple[tuple[str, str], ...]` (each is a path and its
     text). `__post_init__` raises `ValueError("a bench script needs at least one tool result")`
     when `tool_results` is empty.
   - `@dataclass(frozen=True, slots=True) class BenchTurn` with fields `turn: int`,
     `wall_s: float`, `input_tokens: int`, `output_tokens: int`,
     `timings: Mapping[str, float] | None` and `tool_calls: int`.
   - `@dataclass(frozen=True, slots=True) class BenchResult` with fields `model: str`,
     `backend: str`, `method: str` and `turns: tuple[BenchTurn, ...]`, plus a method
     `summary(self) -> dict[str, object]` that returns:
     - `turns`: the count;
     - `total_wall_s`: the sum rounded to 1 decimal;
     - `input_tokens_total` and `output_tokens_total`;
     - `final_ctx_tokens`: the last turn's `input_tokens`;
     - `mean_output_tps`: the mean over turns of `output_tokens / wall_s`, skipping turns with
       `wall_s == 0`, rounded to 1, and `None` when no turn counts;
     - `server_mean_gen_tps`: the mean of `timings["predicted_per_second"]` over turns that
       have it, rounded to 1, `None` otherwise;
     - `model`, `backend` and `method`.
   - `class ModelBench` with `__init__(self, *, server: InferenceServer, clock: ClockInterface) -> None`
     (both from `qwenloop.application.interfaces`) and the method
     `async def run(self, info: ServerInfo, script: BenchScript, *, turns: int = 10) -> BenchResult`.
     - `turns < 1` raises `ValueError("turns must be at least 1")`.
     - Messages start as `[ChatMessage("system", script.system), ChatMessage("user", script.opening)]`.
     - For each turn `n` from 1 to `turns`:
       - `t0 = clock.monotonic()`;
       - consume `server.chat_stream(info, messages)`: concatenate each chunk's `text`, count
         chunks with a `tool_call`, and keep the **last** non-zero `input_tokens` and
         `output_tokens` and the last non-None `timings`;
       - `wall = clock.monotonic() - t0`;
       - record a `BenchTurn`;
       - with `path, text = script.tool_results[(n - 1) % len(script.tool_results)]`, append
         `ChatMessage("assistant", reply)` and
         `ChatMessage("user", f"Tool result (read_file {path}):\n{text}\n\nNext step?")`.
         These are the method's exact strings, from `bench.py:66-68`.
     - It returns `BenchResult(model=info.model or info.profile, backend=info.backend.value, method=BENCH_METHOD, turns=...)`.
     - An exception from `chat_stream` propagates. A partial bench is not evidence.
2. New interface `src/vibey_runners/qwen/src/qwenloop/application/interfaces/bench_interface.py`:
   `class ModelBenchInterface(Protocol)` with `run`, in the style of
   `clock_interface.py`. Export it from `application/interfaces/__init__.py`, in the imports
   and in `__all__`.
3. No infrastructure or CLI change in this lane.

## Where to change
- New: `src/vibey_runners/qwen/src/qwenloop/application/bench.py`,
  `src/vibey_runners/qwen/src/qwenloop/application/interfaces/bench_interface.py`.
- Edit with edit_file: `src/vibey_runners/qwen/src/qwenloop/application/interfaces/__init__.py`.
- New test file `src/vibey_runners/qwen/tests/test_bench.py`. It uses a test class
  `ScriptedServer` implementing `InferenceServer`, whose `chat_stream` yields planned
  `ChatChunk`s per call and records the messages it received, and a `SteppingClock` whose
  `monotonic()` returns 0.0, 2.0, 2.0, 5.0, and so on from a list. Define both in the test
  file, or in `tests/fakes.py` if `fakes-tenant-qwen-1`/`-2` put shared fakes there. Use no
  `monkeypatch.setattr` and no `mock`.

## Acceptance criteria
- [ ] With a script of 3 tool results and `turns=4`, the server receives 4 calls. The 4th call's
      last user message is the tool result for path index 0 again (wrap-around), and each
      call's message list is 2 longer than the previous one.
- [ ] Walls come from the injected clock. The summary's `total_wall_s` equals the sum of the
      planned differences.
- [ ] `final_ctx_tokens` is the last turn's `input_tokens`. `mean_output_tps` skips
      zero-wall turns. `server_mean_gen_tps` is `None` when no chunk carries timings.
- [ ] Tool-call chunks are counted in `BenchTurn.tool_calls`, and their text is not appended.
- [ ] `turns=0` and an empty script raise the stated `ValueError`s.
- [ ] `result.method == "qwenloop-turn-v1"`.
- [ ] `isinstance(ModelBench(server=..., clock=...), ModelBenchInterface)`.
- [ ] The qwen tenant's gates pass at its 100% floor.

## Tests to write first (TDD)
`src/vibey_runners/qwen/tests/test_bench.py`:
- `test_each_turn_appends_the_reply_and_the_next_tool_result`
- `test_tool_results_wrap_around`
- `test_wall_times_come_from_the_injected_clock`
- `test_summary_fields`
- `test_tool_calls_are_counted_not_echoed`
- `test_invalid_turns_and_empty_script_are_refused`
- `test_the_bench_satisfies_its_interface`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && python -m pytest -q -p no:cacheprovider && python -m mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
- The CLI command, the script loader and the evidence file (`gap-models-bench-2`).
- Recording into vibey's ledger (8.g's `gap-measure-models`).
- Memory and load-time sampling (the memory probe is `split-383-3-memory-probe`).
- Docs.

Commit as `feat(qwenloop): a model bench that replays a fixed session through the chat client`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
