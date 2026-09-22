<!-- split of #383: child 4 of 6; audit: issue-audit/updates/383.md -->

## Title
feat(qwenloop)!: with no model configured, the sovereign loop picks the 8.d default wherever it fits, and a RAM-tier default only where it does not

## Why
Sub-doctrine 8.d (`src/vibey_tools/gh/docs/doctrines.md:236-269`) has vibey choose among its
supported models "by the machine it finds itself on", designates GPT-OSS 20B on Ollama as this
era's default, and says "on a machine it does not fit, the catalogue's default for that machine's
tier applies"; where two models are otherwise comparable, the OSI-licensed one wins. The operator
ruled on 2026-09-22 that gpt-oss:20b is the default **wherever it fits**, that every other model is
an opt-in alternative except in tiers where gpt-oss does not fit, and that within a tier an OSI
licence wins a tie — so the tier table's 48–64 GB Qwen3.6-35B-A3B and 128 GB DeepSeek V4 Flash
rows are opt-in alternatives, not defaults. Today qwenloop's model is the constant
`DEFAULT_ENDPOINT_MODEL` (`src/vibey_runners/qwen/src/qwenloop/domain/config.py:16`, used at `:32`)
on every machine, whatever its memory, and a run's `meta.json`
(`src/qwenloop/application/runner.py:233-247`) does not say why its model was chosen (8.g,
`doctrines.md:316-324`). This lane adds a pure selector, injected with the family memory probe
(split-383-3), whose RAM-tier table is catalogue data with evidence and a date (10.f, 12.c).

## Required behaviour
All paths are under `src/vibey_runners/qwen/` unless they start with `.github/`.

1. **Configuration** (`src/qwenloop/domain/config.py`). `QwenConfig` gains three fields after
   `endpoint_timeout_seconds` (`:34`), with these comments:
   ```python
       # Whether an unconfigured model is chosen by this machine's memory (#383). Off, the model
       # is this era's default (sub-doctrine 8.d) on every machine.
       model_by_memory: bool = True
       # Derived, never read from a file or the environment: whether `model` was set by the
       # config file, QWENLOOP_MODEL or --model, and why the model is the one it is.
       model_configured: bool = False
       model_reason: str = ""
   ```
   - `_KEYS` (`:47`) becomes
     `_KEYS = frozenset(item.name for item in fields(QwenConfig)) - _DERIVED_KEYS`, with
     `_DERIVED_KEYS = frozenset({"model_configured", "model_reason"})` declared directly above it,
     so a file naming either is refused as an unknown key.
   - `QwenConfigParser.parse` passes two more arguments to `QwenConfig(...)`:
     `model_by_memory=self._bool("model_by_memory", data.get("model_by_memory", defaults.model_by_memory)),`
     and `model_configured="model" in data,`.
   - A new static method on `QwenConfigParser`:
     ```python
         @staticmethod
         def _bool(key: str, value: object) -> bool:
             """An on/off setting: a TOML bool, or the words an environment variable uses."""
             if isinstance(value, bool):
                 return value
             text = str(value).strip().lower()
             if text in {"1", "true", "yes", "on"}:
                 return True
             if text in {"0", "false", "no", "off"}:
                 return False
             raise ValueError(f"{key} must be true or false (1/0, yes/no, on/off), got {value!r}")
     ```
2. **Environment** (`src/qwenloop/infrastructure/settings.py`). Below `ENV_API_KEY` (`:22`) add
   `#: Whether an unconfigured model is chosen by this machine's memory (\`model_by_memory\`).`
   and `ENV_MODEL_BY_MEMORY = "QWENLOOP_MODEL_BY_MEMORY"`. `ENVIRONMENT_KEYS` (`:33`) becomes
   ```python
       ENVIRONMENT_KEYS: ClassVar[Mapping[str, str]] = {
           ENV_BASE_URL: "base_url",
           ENV_MODEL: "model",
           ENV_MODEL_BY_MEMORY: "model_by_memory",
       }
   ```
3. **Catalogue data** (`src/qwenloop/domain/catalogue.py`, appended at the end):
   ```python
   @dataclass(frozen=True, slots=True)
   class RamTier:
       """One row of the operator's RAM-tier table, held as catalogue data (#383, 8.d)."""

       min_ram_gib: int
       #: Catalogue entry names, in the operator's order.
       candidates: tuple[str, ...]
       evidence: str
       recorded: str


   @dataclass(frozen=True, slots=True)
   class ModelChoice:
       """The model a run uses, and why (#383)."""

       model: str
       reason: str
       entry_name: str | None = None
   ```
   and `RAM_TIERS: tuple[RamTier, ...]`, ascending by `min_ram_gib`, every row with
   `recorded="2026-09-22"` and exactly these candidates and evidence (ASCII hyphens):
   - `RamTier(8, ("gemma-4-e2b", "qwen3.5-4b"), ...)` with evidence
     `"Operator's tier table (2026-09-22), 8 GB (base M1-M4): Gemma 4 E2B, then Qwen 3.5 4B, 25-45 tok/s for chat and summarization (operator guidance, not a vibey measurement). gpt-oss-20b does not fit, so the tier's own default applies, and an OSI licence wins a tie (operator ruling 2026-09-22)."`
     — this row lists only the names behaviour 4 actually catalogued; with neither, the row is
     left out.
   - `RamTier(16, ("gpt-oss-20b", "qwen2.5-coder-14b"), ...)`:
     `"Operator's tier table (2026-09-22), 16 GB (M2-M4 Pro/Max): Qwen 3.5 9B Q4 and Llama 3.1 8B Q4, ~25-40 tok/s (guidance; not yet catalogued). gpt-oss-20b fits at its 16 GiB floor, so it is the default (8.d); the rest are opt-in alternatives."`
   - `RamTier(24, ("gpt-oss-20b",), ...)`:
     `"Operator's tier table (2026-09-22), 24-32 GB (M4 Pro / M5 Pro): GPT-OSS 20B, then Qwen3.6-27B (an opt-in alternative). 8.d's measurement: 86 s for a ten-turn session at 131,072 tokens in 13.1 GB on an M5 24 GB."`
   - `RamTier(48, ("gpt-oss-20b",), ...)`:
     `"Operator's tier table (2026-09-22), 48-64 GB (M4 Max / M5 Max) named Qwen3.6-35B-A3B and Llama 3.3 70B Q4; under the operator's ruling of 2026-09-22 gpt-oss-20b stays the default wherever it fits (8.d) and those are opt-in alternatives."`
   - `RamTier(128, ("gpt-oss-20b",), ...)`:
     `"Operator's tier table (2026-09-22), 128 GB (M5 Max / Studio) named DeepSeek V4 Flash (284B) and Qwen3 235B-A22B; under the operator's ruling of 2026-09-22 they are opt-in alternatives and gpt-oss-20b is the default (8.d)."`

   Only catalogued names appear in `candidates`; the models the operator named that are not
   catalogued live in `evidence`, never in `candidates`.
4. **The sub-floor tier's models** (appended to `CATALOGUE`, after whatever entries are already
   there). Two Ollama-only entries, read from source with the commands in C3 on the day the lane
   runs; never typed from memory:
   - `gemma-4-e2b`: `family="gemma4"`, base model `google/gemma-4-E2B-it`, Ollama library `gemma4`;
   - `qwen3.5-4b`: `family="qwen3.5"`, base model `Qwen/Qwen3.5-4B`, Ollama library `qwen3.5`.

   For each: `total_params_b` = the base model's `safetensors.total` / 1e9 to one decimal;
   `active_params_b` = the effective or activated parameter count its model card states, else
   `total_params_b`; `license_spdx`/`license_osi` from its `license:` tag (`apache-2.0` →
   `"Apache-2.0"`, `True`; `mit` → `"MIT"`, `True`; anything else verbatim, `False`);
   `min_ram_gib=8`; `context_window` from `config.json` (`text_config.max_position_embeddings`, else
   `max_position_embeddings`); `ollama=OllamaArtifact(<the library's plain size tag, e2b / 4b,
   confirmed by its registry manifest answering 200>)`; `gguf=None`;
   `unverified=("llama.cpp", "ollama")`; `recorded` = `date -u +%F`; `evidence` =
   `"Operator's tier table (2026-09-22), 8 GB tier; licence read from the Hugging Face API; Ollama tag read from ollama.com; not load-tested; its llama.cpp GGUF is not pinned yet"`.
   A model whose Ollama tag cannot be read is left out (it would have no artifact) and named in the
   commit body. On 2026-09-22 the spec writer read `license:apache-2.0` for both base models from
   the Hugging Face API, so both are OSI and the operator's order (Gemma 4 E2B first) decides the
   tie; the lane re-reads and the rule, not this note, decides.
5. **The selector.** New `src/qwenloop/application/model_selection.py`:
   ```python
   class DefaultModelSelector:
       def __init__(
           self,
           catalogue: ModelCatalogueInterface,
           probe: MemoryProbeInterface,
           *,
           tiers: tuple[RamTier, ...] = RAM_TIERS,
           default_tag: str = DEFAULT_ENDPOINT_MODEL,
       ) -> None: ...
       def select(self, config: QwenConfig) -> ModelChoice: ...
   ```
   `MemoryProbeInterface` is imported from `vibey_runners.common.infrastructure.interfaces`
   (split-383-3); the application layer never constructs the probe (10.e: "behind a port"). With
   `_ERA_DEFAULT = "this era's default (sub-doctrine 8.d)"`, `select` answers, in this order:
   1. `config.model_configured` → `ModelChoice(config.model, "explicitly configured (config \`model\`, QWENLOOP_MODEL or --model)", <the entry whose Ollama tag is config.model, its name, else None>)`.
      The probe is not asked.
   2. `default = catalogue.by_ollama_tag(default_tag)`; `None` raises
      `ValueError(f"this era's default {default_tag} is not in the model catalogue")`.
   3. `not config.model_by_memory` → `ModelChoice(default_tag, f"model_by_memory is off: {_ERA_DEFAULT}", default.name)`.
      The probe is not asked.
   4. `total = probe.total_bytes()`; `None` →
      `ModelChoice(default_tag, f"this machine did not state its memory: {_ERA_DEFAULT}", default.name)`.
   5. `gib = math.ceil(total / 1024**3)` (installed memory in whole GiB: Linux's `MemTotal` omits
      what the kernel reserves, so a 16 GiB machine reads a little under 16; macOS states the exact
      size — write this as the comment above the line). `gib >= default.min_ram_gib` →
      `ModelChoice(default_tag, f"{gib} GiB of memory is at least {default.name}'s {default.min_ram_gib} GiB floor: {_ERA_DEFAULT}", default.name)`.
   6. Otherwise the tier default: of the tiers with `min_ram_gib <= gib`, the one with the largest
      `min_ram_gib`; of its `candidates`, those whose catalogue entry has an Ollama tag and
      `min_ram_gib <= gib`, ordered OSI-licensed first and otherwise in the operator's order
      (`sorted(fitting, key=lambda pair: not pair[0].license_osi)` — `sorted` is stable); the first →
      `ModelChoice(tag, f"{gib} GiB of memory is below {default.name}'s {default.min_ram_gib} GiB floor: the {tier.min_ram_gib} GiB tier's default, {entry.name} ({licence})", entry.name)`
      where `licence` is `f"{entry.license_spdx}, OSI-approved"` when `entry.license_osi`, else
      `entry.license_spdx`. Put this step in a private method
      `_tier_default(self, gib: int) -> tuple[RamTier, ModelEntry, str] | None`.
   7. No tier reached, or no candidate fits →
      `ModelChoice(default_tag, f"{gib} GiB of memory is below {default.name}'s {default.min_ram_gib} GiB floor and no RAM tier names a model that fits: {_ERA_DEFAULT} is used and will not fit", default.name)`.
6. **Its interface.** New `src/qwenloop/application/interfaces/model_selection_interface.py`:
   `@runtime_checkable class DefaultModelSelectorInterface(Protocol)` with
   `def select(self, config: QwenConfig) -> ModelChoice:` (docstring: `"""The model \`config\` runs and why; an explicit model always wins."""`, body `...`),
   importing `ModelChoice` from `qwenloop.domain.catalogue` and `QwenConfig` from
   `qwenloop.domain.config`. `src/qwenloop/application/interfaces/__init__.py` imports it (after
   the `desktop_notifier_interface` import) and lists `"DefaultModelSelectorInterface"` in `__all__`.
7. **Composition** (`src/qwenloop/cli/app.py`, every helper module-level for the reason the module
   already states at `:170-171`):
   - new `_with_default_model(config: QwenConfig, *, selector: DefaultModelSelectorInterface | None = None) -> QwenConfig`:
     `chosen = (selector or DefaultModelSelector(ModelCatalogue(), MemoryProbe())).select(config)`,
     then `typer.echo(f"qwenloop model: {chosen.model} ({chosen.reason})", err=True)`, then
     `return replace(config, model=chosen.model, model_reason=chosen.reason)`. `MemoryProbe` is
     `vibey_runners.common.infrastructure.memory_probe.MemoryProbe`.
   - `_load_config` (`:167-176`) returns `_with_default_model(config)` for the config the loader
     built (the `try`/`except` stays around the loader call only), so `run`, `run --storm`,
     `doctor`, `server status` and `server start` all use the chosen model.
   - new `_model_selection(config: QwenConfig, profile: ModelProfile) -> dict[str, str]`: when
     `profile.backend is Backend.OPENAI_COMPAT`, `{"model": config.model, "reason": config.model_reason}`;
     otherwise `{"model": profile.name, "reason": f"the managed {profile.backend.value} server loads its pinned profile"}`.
   - `_run_plan` (`:282-313`) gains a keyword `model_selection: Mapping[str, str] | None = None`
     and passes it to `runner.run(...)`. `_run_single` (`:262`) and `_run_storm` (`:427`) pass
     `model_selection=_model_selection(config, profile)`.
8. **The ledger** (`src/qwenloop/application/runner.py`, 7.c and 8.g). `AutonomousRunner.run`
   (`:210-219`) gains a last keyword `model_selection: Mapping[str, str] | None = None`. The dict
   passed to `self._store.create` (`:233-247`) is first bound to
   `metadata: dict[str, object] = {...}` (same keys), then
   `if model_selection is not None: metadata["model_selection"] = dict(model_selection)`
   (comment: `# Which model the run used and why it was chosen (#383, sub-doctrine 8.g).`), then
   `self._store.create(run_id, metadata)`. `AutonomousRunnerInterface.run`
   (`src/qwenloop/application/interfaces/class_contracts.py:14-23`) gains the same keyword.
9. **Test isolation** (`tests/conftest.py`). In `isolated_settings`, directly after
   `monkeypatch.setenv("QWENLOOP_CONFIG", str(config))` (`:19`), add
   `monkeypatch.setenv("QWENLOOP_MODEL_BY_MEMORY", "0")` with the comment
   `# The machine's own memory never picks a test's model (#383); a test that wants it says so.`
   The environment is a declared seam; every existing test keeps `gpt-oss:20b` as its model.
10. **CI** (`.github/workflows/ci.yml:531-545`). Each of the three `qwenloop` rows' `install`
    becomes `'pip install -e ../common && pip install -e ".[dev]"'` — qwenloop now imports
    `vibey_runners.common`, and plain pip installs a family package from the tree first (ADR-0037;
    the family package is never named in `dependencies`).

## Where to change
Why this lane spans more than one source file: the choice must reach configuration (1-2), data
(3-4), a pure selector (5-6), every command (7), the run's recorded settings (8), test isolation
(9) and CI (10); each edit is small and exact.
- `src/qwenloop/domain/config.py` — behaviour 1 (`edit_file`; 106 lines).
- `src/qwenloop/infrastructure/settings.py` — behaviour 2.
- `src/qwenloop/domain/catalogue.py` — behaviours 3-4 (`edit_file`; append the classes and
  `RAM_TIERS` at the end; the new entries go above the `CATALOGUE = (` line and into it).
- new `src/qwenloop/application/model_selection.py` and
  `src/qwenloop/application/interfaces/model_selection_interface.py`, plus
  `src/qwenloop/application/interfaces/__init__.py` — behaviours 5-6. Line 1 of each new file is the
  provenance comment copied from line 1 of `src/qwenloop/application/backend_selection.py`.
- `src/qwenloop/cli/app.py` — behaviour 7 (`edit_file` only: 761 lines).
- `src/qwenloop/application/runner.py` and `src/qwenloop/application/interfaces/class_contracts.py`
  — behaviour 8 (`edit_file` only).
- `tests/conftest.py` — behaviour 9; `tests/fakes.py` — the two fakes below (imports go into its
  top import block with `edit_file`; the classes and their `isinstance` asserts are appended).
- `.github/workflows/ci.yml` — behaviour 10.
- Tests: new `tests/test_model_selection.py`; append to `tests/test_domain.py`,
  `tests/test_settings.py`, `tests/test_runner.py`, `tests/test_cli.py`, `tests/test_catalogue.py`.
  New imports go into each file's top import block with `edit_file`, never below code.

Fix import order with `UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check --select I --fix <file>`
from the repository root (`vibey_runners` sorts as third-party, ahead of `qwenloop`).

## Acceptance criteria
- [ ] Every test named below passes; the qwen suite passes at its 100% floor; mypy --strict,
      lint-imports and bandit are clean.
- [ ] `gpt-oss:20b` is chosen at 16, 24, 32, 48, 64 and 128 GiB and at a Linux-style
      `int(15.6 * 1024**3)` bytes (`test_gpt_oss_is_the_default_wherever_it_fits`).
- [ ] Below the floor an OSI licence wins the tier, and equal licences keep the operator's order.
- [ ] An explicit model, and `model_by_memory` off, never ask the probe.
- [ ] `meta.json` carries `model_selection` when one is given, and nothing new when not.
- [ ] `QWENLOOP_MODEL_BY_MEMORY=0` and `model_by_memory = false` both turn selection off; a
      non-boolean is refused naming the key; `model_reason` in a config file is refused as unknown.
- [ ] `tests/meta/test_tools_matrix_covers_every_package.py` passes from the repository root.
- [ ] No new test patches an import or a module/class attribute, or reaches the network.

## Tests to write first (TDD)
`tests/fakes.py` (the tenant's in-memory fakes, one per new port):
```python
class FakeMemoryProbe:
    """An in-memory stand-in for the family memory probe: states a fixed total, counts asks."""

    def __init__(self, total_bytes: int | None) -> None:
        self.total = total_bytes
        self.asked = 0

    def total_bytes(self) -> int | None:
        self.asked += 1
        return self.total


class FakeModelSelector:
    """An in-memory stand-in for the default-model selector: one answer, records each config."""

    def __init__(self, choice: ModelChoice) -> None:
        self.choice = choice
        self.seen: list[QwenConfig] = []

    def select(self, config: QwenConfig) -> ModelChoice:
        self.seen.append(config)
        return self.choice


assert isinstance(FakeMemoryProbe(None), MemoryProbeInterface)
assert isinstance(FakeModelSelector(ModelChoice("m", "r")), DefaultModelSelectorInterface)
```
New `tests/test_model_selection.py` (`GIB = 1024**3`; `parser = QwenConfigParser()`; injected
catalogues are `ModelCatalogue(entries=(...))` built from small `ModelEntry` values in the test; an
entry with no Ollama tag carries `gguf=QWEN25_CODER_14B_Q5_K_M`):
- `test_an_explicit_model_always_wins_and_never_probes` — `parser.parse({"model": "qwen2.5-coder:14b"})`
  with `FakeMemoryProbe(4 * GIB)` → model `"qwen2.5-coder:14b"`, `entry_name == "qwen2.5-coder-14b"`,
  reason starts `"explicitly configured"`, `probe.asked == 0`.
- `test_an_explicit_uncatalogued_model_is_used_as_given` — model `"llama3.1:8b"` →
  `entry_name is None`.
- `test_model_by_memory_off_is_the_era_default_without_probing` — `parse({"model_by_memory": False})`
  → `"gpt-oss:20b"`, reason `"model_by_memory is off: this era's default (sub-doctrine 8.d)"`,
  `probe.asked == 0`.
- `test_an_unreadable_machine_gets_the_era_default` — `FakeMemoryProbe(None)` → `"gpt-oss:20b"`,
  reason starts `"this machine did not state its memory"`.
- `test_gpt_oss_is_the_default_wherever_it_fits` — parametrised over `16*GIB, 24*GIB, 32*GIB,
  48*GIB, 64*GIB, 128*GIB, int(15.6*GIB)` with the real `ModelCatalogue()` and `RAM_TIERS` →
  `"gpt-oss:20b"`, `entry_name == "gpt-oss-20b"`, reason contains `"GiB floor: this era's default"`.
- `test_below_the_floor_an_osi_licence_wins_the_tier` — injected catalogue: `big` (tag
  `"big:1"`, min 16, OSI), `custom` (tag `"custom:1"`, min 8, `license_osi=False`,
  `license_spdx="LicenseRef-custom"`), `open` (tag `"open:1"`, min 8, OSI); tiers
  `(RamTier(8, ("custom", "open"), "e", "2026-09-22"),)`; `default_tag="big:1"`; 8 GiB →
  `"open:1"`, reason ends `"the 8 GiB tier's default, open (Apache-2.0, OSI-approved)"`.
- `test_equal_licences_keep_the_operators_order` — both 8-GiB candidates OSI → the first listed.
- `test_a_tier_with_nothing_that_fits_falls_back_loudly` — the tier's candidates are one entry
  with no Ollama tag and one with `min_ram_gib=12`; at 8 GiB → `"big:1"`, reason ends
  `"is used and will not fit"`.
- `test_below_every_tier_the_era_default_is_named_as_not_fitting` — 4 GiB with a lowest tier of 8
  → `"big:1"`, reason ends `"is used and will not fit"`.
- `test_an_uncatalogued_era_default_is_refused` — `default_tag="absent:1"` → `ValueError` matching
  `"not in the model catalogue"`.
- `test_the_tier_table_is_consistent` — `RAM_TIERS` strictly ascending by `min_ram_gib`; every
  candidate is `ModelCatalogue().get(...)`-able; each candidate's `min_ram_gib <= tier.min_ram_gib`;
  every tier with `min_ram_gib >= 16` lists `"gpt-oss-20b"` first; every `evidence` non-empty and
  every `recorded` matches `^\d{4}-\d{2}-\d{2}$`; if an 8 GiB tier exists, each of its candidates
  has an Ollama tag and `min_ram_gib == 8`.
- `test_the_selector_satisfies_its_interface` — `isinstance(DefaultModelSelector(ModelCatalogue(), FakeMemoryProbe(None)), DefaultModelSelectorInterface)`.

Appended elsewhere:
- `tests/test_domain.py`: `test_config_model_by_memory_parses_and_refuses_non_bool` (`"0"`, `"off"`,
  `False` → False; `"yes"`, `True` → True; `"maybe"` → `ValueError` matching
  `"model_by_memory must be true or false"`); `test_config_records_whether_the_model_was_configured`
  (`parse({}).model_configured is False`; `parse({"model": "x:1"}).model_configured is True`);
  `test_derived_fields_are_not_config_keys` (`parse({"model_reason": "x"})` raises matching
  `"unknown qwenloop config key\\(s\\): model_reason"`).
- `tests/test_settings.py`: `test_environment_turns_off_choosing_the_model_by_memory` —
  `SettingsLoader({"QWENLOOP_MODEL_BY_MEMORY": "0"}, default_path=tmp_path / "absent.toml").load().model_by_memory is False`,
  and with `{"QWENLOOP_MODEL": "x:1"}` the loaded config has `model_configured is True`.
- `tests/test_runner.py`: `test_meta_records_why_the_model_was_chosen` — a `ScriptedServer` with
  one turn `[ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")]`,
  `run(..., model_selection={"model": "gpt-oss:20b", "reason": "r"})` → `meta.json`'s
  `model_selection == {"model": "gpt-oss:20b", "reason": "r"}`; the same run without the keyword
  has no `model_selection` key.
- `tests/test_cli.py`:
  - `test_the_chosen_model_is_applied_and_logged(capsys)` — `_with_default_model(QwenConfig(), selector=FakeModelSelector(ModelChoice("qwen3.5:4b", "why", "qwen3.5-4b")))`
    returns a config with `model == "qwen3.5:4b"` and `model_reason == "why"`; `capsys.readouterr().err`
    contains `"qwenloop model: qwen3.5:4b (why)"`.
  - `test_the_model_selection_record_names_what_actually_runs` — `_model_selection(replace(QwenConfig(), model_reason="r"), OpenAICompatServer("http://h:1/v1", "gpt-oss:20b").profile) == {"model": "gpt-oss:20b", "reason": "r"}`;
    `_model_selection(QwenConfig(), PORTABLE) == {"model": PORTABLE.name, "reason": "the managed llama.cpp server loads its pinned profile"}`.
  - `test_run_plan_records_why_the_model_was_chosen(tmp_path)` (async) — a small in-test server
    class whose `inspect` returns `ServerInfo(Backend.OPENAI_COMPAT, "gpt-oss:20b", "http://h:1/v1", False, True)`,
    `health` returns True and `chat_stream(self, info, messages)` is an async generator yielding
    `ChatChunk(text="")`; `await _run_plan(server, PORTABLE, tmp_path, "sel", "do it", 1, startup_timeout_seconds=1, desktop_notifications=False, model_selection={"model": "gpt-oss:20b", "reason": "r"})`
    (the run itself fails for want of an answer; only its `meta.json` is asserted);
    then `json.loads((tmp_path / ".qwenloop" / "runs" / "sel" / "meta.json").read_text())["model_selection"] == {"model": "gpt-oss:20b", "reason": "r"}`.
- `tests/test_catalogue.py`: `test_the_sub_floor_entries_are_ollama_only_and_unverified` — for each
  of `"gemma-4-e2b"`, `"qwen3.5-4b"` present in `CATALOGUE`: `ollama is not None`, `gguf is None`,
  `min_ram_gib == 8`, `set(unverified) == {"llama.cpp", "ollama"}`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_runners/qwen
python -c "import qwenloop, vibey_runners.common.infrastructure.memory_probe" || { python -m pip install -e ../common && python -m pip install -e ".[dev]"; }
python -m pytest -q -p no:cacheprovider --no-cov tests/test_model_selection.py tests/test_domain.py tests/test_settings.py tests/test_catalogue.py tests/test_runner.py tests/test_cli.py
python -m pytest -q -p no:cacheprovider          # whole suite, 100% branch floor from addopts
python -m mypy --strict src/qwenloop
lint-imports
python -m bandit -q -r src/qwenloop
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run pytest -q -p no:cacheprovider tests/meta/test_tools_matrix_covers_every_package.py
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
UV_CACHE_DIR=$TMPDIR/uvcache uv lock --check
git diff --stat
```

## Out of scope
- Which GGUF the managed llama.cpp server loads (`_server_for` keeps `PORTABLE`, `cli/app.py:236-238`);
  8.d applies the default there "once its own weights are pinned", which is a follow-up after
  gpt-oss-20b's GGUF is pinned and load-tested.
- The Qwen3.6/3.8 entries (split-383-2) and adding them to any tier's `candidates`; the models the
  operator named that are not catalogued; GGUF pins for the 8 GiB models.
- vibey's own model defaults (`src/vibey/...`), the installer, the chart, ADR-0046 §4's residency.
- `model verify`, `model list` and doctor output (split-383-6-model-verify-doctor).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs, or change git remotes. Commit locally as this spec's title with the
  footer `BREAKING CHANGE: with no model configured, a machine below gpt-oss-20b's 16 GiB floor now asks its RAM tier's default model (the 8 GiB tier's, where catalogued); set QWENLOOP_MODEL=gpt-oss:20b, or QWENLOOP_MODEL_BY_MEMORY=0, to keep the old one.`

## Conventions this lane relies on (everything needed is here)
**C1, the shapes from split-383-1** (`src/qwenloop/domain/catalogue.py`): `OllamaArtifact(tag)`;
`ModelEntry(name, family, total_params_b, active_params_b, license_spdx, license_osi, min_ram_gib, context_window, ollama, gguf, evidence, recorded, unverified=())`;
`QWEN25_CODER_14B_Q5_K_M` (a llama.cpp `ModelProfile`); `CATALOGUE`; `ModelCatalogue(entries=CATALOGUE)`
with `entries()`, `get(name)` (`KeyError` when unknown), `by_ollama_tag(tag)` (`None` when
unknown); `ModelCatalogueInterface` exported from `qwenloop.domain.interfaces`. Both catalogued
defaults, `gpt-oss-20b` (tag `gpt-oss:20b`) and `qwen2.5-coder-14b` (tag `qwen2.5-coder:14b`), have
`min_ram_gib=16`.

**C2, the probe from split-383-3**: `vibey_runners.common.infrastructure.interfaces.MemoryProbeInterface`
with `total_bytes(self) -> int | None`, and
`vibey_runners.common.infrastructure.memory_probe.MemoryProbe()` (no arguments: this machine).

**C3, reading the sub-floor entries (never from a test).**
```bash
for BASE in google/gemma-4-E2B-it Qwen/Qwen3.5-4B; do
  curl -fsS "https://huggingface.co/api/models/$BASE" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["id"], [t for t in d.get("tags", []) if t.startswith("license:")], (d.get("safetensors") or {}).get("total"))'
  curl -fsSL "https://huggingface.co/$BASE/raw/main/config.json" | python3 -c '
import json, sys
c = json.load(sys.stdin)
print("context:", (c.get("text_config") or {}).get("max_position_embeddings") or c.get("max_position_embeddings"))'
  curl -fsSL "https://huggingface.co/$BASE/raw/main/README.md" | grep -i -m3 -E "effective|activated"
done
curl -fsS https://ollama.com/library/gemma4/tags | grep -oE 'gemma4:[A-Za-z0-9._-]+' | sort -u
curl -fsS https://ollama.com/library/qwen3.5/tags | grep -oE 'qwen3\.5:[A-Za-z0-9._-]+' | sort -u
curl -s -o /dev/null -w '%{http_code}\n' -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
  https://registry.ollama.ai/v2/library/gemma4/manifests/e2b
curl -s -o /dev/null -w '%{http_code}\n' -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
  https://registry.ollama.ai/v2/library/qwen3.5/manifests/4b
```

**C4, tests.** Focused runs need `--no-cov`. Substitute only at declared seams: constructor and
keyword injection (`probe=`, `selector=`, `tiers=`, `default_tag=`, `entries=`), the environment
(`QWENLOOP_*` through `SettingsLoader(environ)` or the conftest's `isolated_settings`), and
`tests/fakes.py`. Never `monkeypatch.setattr` an import or a module/class attribute, never
`mock.patch`, `MagicMock` or `AsyncMock`. No test reaches the network or a live Ollama: the conftest
autouse fixtures `isolated_settings` (config file, `QWENLOOP_*` variables, and now
`QWENLOOP_MODEL_BY_MEMORY=0`) and `no_local_ollama` (the CLI's Ollama probe answers "not running")
keep a developer's machine out of every test.

**Depends on:** split-383-1-model-catalogue, split-383-3-memory-probe
- split-383-1-model-catalogue: `ModelEntry`, `OllamaArtifact`, `CATALOGUE`, `ModelCatalogue`, `ModelCatalogueInterface`, `QWEN25_CODER_14B_Q5_K_M`, and `tests/test_catalogue.py`.
- split-383-3-memory-probe: `MemoryProbe` and `MemoryProbeInterface` in `vibey_runners.common.infrastructure`, and the family package's CI rows.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
