## Title
feat(measure): the worker samples which local models are resident and how much memory each holds

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) measures every model's
"resource use", and ADR-0046 §4 chooses model residency from evidence: "vibey never has two
models loaded at once" (`specs/ADR-two-loops.md:193-214`). Nothing records what is resident or
what it costs in memory. Ollama answers `GET /api/ps` with the loaded models
(`{"models": [{"name": …, "model": …, "size": <bytes>, "size_vram": <bytes>, …}]}`); gpt-oss:20b
is 13.1 GB resident (STORM-CONTEXT). This lane samples it as a `MeasurementSource` (lane
`gap-measure-port`) the worker's ticker collects (lane `gap-measure-ticker`), only when a local
engine is on, so a paid-only machine does not record a failure every period.

## Required behaviour
1. New `src/vibey/infrastructure/measure/model_residency_sampler.py`,
   `class OllamaResidencySampler`:
   `__init__(self, base_url: str, *, clock: Clock, opener: Callable[..., Any] =
   urllib.request.urlopen, timeout: int = 5, instance: str = "", ids: Callable[[], UUID] = uuid4)`.
   The base URL is validated exactly as `OllamaChatClient._validated_base_url`
   (`src/vibey/infrastructure/engines/ollama_chat.py:179-188`): an http(s) URL with a host, else
   `ConfigError(OLLAMA_URL_ENV, …)`; trailing `/` stripped. `name` property returns `"ollama.ps"`.
   `async def collect(self) -> tuple[Measurement, ...]`:
   - `body = await asyncio.to_thread(self._get, f"{base}/api/ps")`, where `_get` re-checks the
     scheme (copy `UrllibOllamaTransport._send`, `ollama_chat.py:59-74`, as a `GET`:
     `urllib.request.Request(url)` with `# nosec B310 - scheme checked above`), decodes JSON and
     requires an object;
   - `now = clock.now()`; `models = body.get("models")` must be a list, else
     `ValueError("Ollama /api/ps returned no models list")`;
   - one measurement per entry that is a mapping with a non-empty `str` `name` (else `model`):
     subject `MeasurementSubject(SubjectKind.MODEL, name)`, outcome `SAMPLED`,
     `started_at = ended_at = now`, readings `MEMORY_BYTES = size` and `VRAM_BYTES = size_vram`
     when each is a number (not `bool`), finite and `>= 0`; `instance`;
   - plus, always, one measurement subject `MeasurementSubject(SubjectKind.MODEL,
     "ollama:resident")` with `COUNT` = the number of models measured, so an empty machine
     records 0 rather than nothing.
   Any exception propagates: the ticker records it as a failed source.
2. New `src/vibey/infrastructure/measure/interfaces/model_residency_sampler_interface.py`:
   `OllamaResidencySamplerInterface` (`name`, `collect`).
3. `src/vibey/cli/main.py`, `worker`'s `run_worker`, right after lane `gap-measure-ticker`'s
   `worker_sources` list is created: when `local.enabled_engines` (`local` is bound at `:1643`)
   is non-empty,
   `worker_sources.append(OllamaResidencySampler(os.environ.get(OLLAMA_URL_ENV) or
   DEFAULT_OLLAMA_URL, clock=resources.clock, instance=platform.node()))`
   (`DEFAULT_OLLAMA_URL` is imported with the other names at `:67-72`). The ticker is built after
   this, so it sees the source.

## Where to change
- New `src/vibey/infrastructure/measure/model_residency_sampler.py` and its interface file.
- `src/vibey/cli/main.py` (`edit_file`; imports inside `worker`).
- New `tests/infrastructure/measure/test_model_residency_sampler.py`. The opener is a plain class
  whose `__call__(request, timeout)` returns a context manager with `read()` (copy the opener
  double style of `tests/infrastructure/engines/test_ollama_chat.py`) — never a mock.

## Acceptance criteria
- [ ] A `/api/ps` body with `gpt-oss:20b` (`size 14067000000`, `size_vram 14067000000`) records
      its memory and VRAM and an `ollama:resident` count of 1.
- [ ] `{"models": []}` records only `ollama:resident` with count 0.
- [ ] An entry with no name, or `size: true`, is skipped or read without that reading.
- [ ] `file:///etc/passwd` as the base URL raises `ConfigError` at construction; a body without a
      `models` list raises `ValueError` from `collect`.
- [ ] An AST test finds the `OllamaResidencySampler(` call inside `worker` guarded by
      `local.enabled_engines`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/` and `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_model_residency_sampler.py`:
- `test_each_resident_model_reports_its_memory`
- `test_an_empty_runtime_reports_zero_resident`
- `test_malformed_entries_are_skipped_or_read_partially`
- `test_a_non_http_endpoint_is_refused`
- `test_a_body_without_models_is_an_error`
- `test_the_sampler_asks_ps_with_a_get` (the opener saw `…/api/ps`, method `GET`, the timeout)
- `test_the_sampler_satisfies_its_interfaces`
- `test_the_worker_samples_residency_only_with_a_local_engine` (the AST check)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Choosing or switching the resident model (`loops-residency`); llama.cpp/vLLM servers that do
  not speak `/api/ps` (the qwenloop server log, #382); the benchmark (gap D3).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): the worker samples which local models are resident and how much memory each holds`. Do not push.

## Lane card
- **Depends on:** `gap-measure-ticker`, `gap-measure-models-1` (shares the `cli/main.py` imports).
- **Must keep passing unchanged:** the worker tests in `tests/cli/test_operational_commands.py`
  (where a local engine is on and no Ollama answers, the ticker records the sampler as a failed
  source; the worker is unaffected), `tests/infrastructure/engines/test_ollama_chat.py` (whose
  opener doubles this lane's test copies) and the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
