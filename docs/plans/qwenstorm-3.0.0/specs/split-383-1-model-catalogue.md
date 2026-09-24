<!-- split of #383: child 1 of 6; audit: issue-audit/updates/383.md -->

## Title
feat(qwenloop): a model catalogue as data — each entry pins its GGUF, its Ollama tag, its licence and the evidence for choosing it

## Why
Sub-doctrine 8.d (`src/vibey_tools/gh/docs/doctrines.md:236-269`) says vibey supports every
gold-standard free model that runs on a Linux or macOS laptop: its weights pinned in the model
catalogue (source, revision and digest), runnable on both Ollama and llama.cpp, with the evidence
and date of each choice recorded (10.f, `doctrines.md:419`). This era's designated default is
**GPT-OSS 20B on Ollama** (`gpt-oss:20b`, `doctrines.md:259-269`), already qwenloop's
`DEFAULT_ENDPOINT_MODEL` (`src/vibey_runners/qwen/src/qwenloop/domain/config.py:16`, integrated
by #387 at `ddf2bf05`). Today there is no catalogue: one pinned llama.cpp profile
(Qwen2.5-Coder-14B-Instruct Q5_K_M) and one vLLM profile live in
`src/vibey_runners/qwen/src/qwenloop/infrastructure/profiles.py:6-31` (`PROFILES` at `:31`), in the
shape `ModelProfile` (`src/qwenloop/domain/model.py:36-46`), and nothing records an Ollama tag, a
licence, a RAM floor or why a model was chosen. The operator measured on 2026-09-22 (M5 24 GB,
llama-server build 10566) that Ollama's GPT-OSS 20B file does not load in llama.cpp
(`unknown model architecture: 'gptoss'`), so the llama.cpp side pins its own GGUF and never shares
blobs with Ollama. This lane adds the catalogue as data (12.c) with its first two entries; it
changes no default and no selection.

## Required behaviour
All paths are under `src/vibey_runners/qwen/`.

1. New `src/qwenloop/domain/catalogue.py` (pure: stdlib and `qwenloop.domain.model` only; no I/O,
   no clock, no network). In this order it declares:
   - `@dataclass(frozen=True, slots=True) class OllamaArtifact` with one field `tag: str`.
   - `@dataclass(frozen=True, slots=True) class ModelEntry` with exactly these fields, in this
     order:
     - `name: str` — a slug such as `"gpt-oss-20b"`;
     - `family: str`;
     - `total_params_b: float` and `active_params_b: float`;
     - `license_spdx: str` — for example `"Apache-2.0"`;
     - `license_osi: bool`;
     - `min_ram_gib: int` and `context_window: int`;
     - `ollama: OllamaArtifact | None`;
     - `gguf: ModelProfile | None` — the llama.cpp pin, a `ModelProfile` with
       `backend=Backend.LLAMA_CPP`;
     - `evidence: str` and `recorded: str` — an ISO date, `YYYY-MM-DD`;
     - `unverified: tuple[str, ...] = ()` — the backends (`"llama.cpp"`, `"ollama"`) named here
       were never test-loaded (10.f).
   - `QWEN25_CODER_14B_Q5_K_M: ModelProfile`, the existing portable pin **moved down from
     infrastructure** (see behaviour 3 for why), with exactly today's values from
     `profiles.py:7-18`:
     ```python
     QWEN25_CODER_14B_Q5_K_M = ModelProfile(
         name="qwen2.5-coder-14b-q5-k-m",
         backend=Backend.LLAMA_CPP,
         repository="Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
         revision="d0a692ef765eefbf2fabb130b3cb2e8917e3d225",
         filename="qwen2.5-coder-14b-instruct-q5_k_m.gguf",
         sha256="98ab25e0132e3f1e6d3554e1b64de2b5021908819b740d9c208430117e49a775",
         size=10_508_873_152,
         quantization="Q5_K_M",
     )
     ```
   - the two entries (behaviour 2), then `CATALOGUE: tuple[ModelEntry, ...]` holding them, then
   - `class ModelCatalogue` with `__init__(self, entries: tuple[ModelEntry, ...] = CATALOGUE) -> None`
     (the default argument needs `CATALOGUE` defined above the class). `__init__` raises
     `ValueError` with exactly these messages, checked entry by entry in order:
     - a second entry with a name already seen: `f"duplicate catalogue entry name: {name}"`;
     - a second entry with an Ollama tag already seen: `f"duplicate Ollama tag in the catalogue: {tag}"`;
     - an entry with `ollama is None and gguf is None`:
       `f"catalogue entry {name} pins neither an Ollama tag nor a GGUF"`.

     Methods:
     - `entries(self) -> tuple[ModelEntry, ...]` — the entries, in the order given;
     - `get(self, name: str) -> ModelEntry` — raises
       `KeyError(f"unknown catalogue entry {name!r}; known: {', '.join(sorted(<all names>))}")`;
     - `by_ollama_tag(self, tag: str) -> ModelEntry | None`.
2. After this lane `CATALOGUE` holds exactly these two entries, in this order:
   - **qwen2.5-coder-14b**: `family="qwen2.5-coder"`, `total_params_b=14.7`, `active_params_b=14.7`,
     `license_spdx="Apache-2.0"`, `license_osi=True`, `min_ram_gib=16`, `context_window=32_768`,
     `ollama=OllamaArtifact("qwen2.5-coder:14b")`, `gguf=QWEN25_CODER_14B_Q5_K_M`,
     `evidence="previous default; 215 s for a ten-turn session at 32,768 tokens on an M5 24 GB (llama.cpp); loaded on Ollama as qwen2.5-coder:14b at 9.7 GB resident on a 24 GB machine (vibey_gh/fit.py:15)"`,
     `recorded="2026-09-22"`, `unverified=()` (both backends carry load evidence in that text).
   - **gpt-oss-20b**: `family="gpt-oss"`, `total_params_b=20.9`, `active_params_b=3.6`,
     `license_spdx="Apache-2.0"`, `license_osi=True`, `min_ram_gib=16`, `context_window=131_072`,
     `ollama=OllamaArtifact("gpt-oss:20b")`,
     `evidence="the 8.d designated default: 86 s for a ten-turn session at 131,072 tokens in 13.1 GB resident on an M5 24 GB (Ollama); its llama.cpp GGUF is pinned from ggml-org/gpt-oss-20b-GGUF but never load-tested"`,
     `recorded="2026-09-22"`, `unverified=("llama.cpp",)`. Its `gguf` is pinned from
     `ggml-org/gpt-oss-20b-GGUF` **only with values read from the source** (commands under
     "Conventions", C2):
     - `name="gpt-oss-20b-mxfp4"`, `backend=Backend.LLAMA_CPP`,
       `repository="ggml-org/gpt-oss-20b-GGUF"`, `quantization="MXFP4"`, `context_window` left at
       the `ModelProfile` default (the run's `context_window` setting replaces it at run time,
       `cli/app.py:235-238`);
     - `revision` = the API's `sha`; `filename`, `size`, `sha256` = that file's `path`, `size` and
       `lfs.oid` from the tree listed at that `sha`;
     - the file is `gpt-oss-20b-MXFP4.gguf`. The repository also holds `eagle3-gpt-oss-20b-*.gguf`
       draft-model files: never pin one of those.
     - If the lane host cannot reach huggingface.co, set `gguf=None`, keep
       `unverified=("llama.cpp",)`, and name the missing pin as a follow-up in the commit body.
       Never type a revision, digest or size from memory.
3. `src/qwenloop/infrastructure/profiles.py` keeps `QWEN_REVISION`, `QWEN_GGUF_REVISION`,
   `PORTABLE`, `NVIDIA_BF16` and `PROFILES` with exactly today's values, so every existing caller
   works unchanged. Because the domain may not import infrastructure (the "Onion layering" contract,
   `src/vibey_runners/qwen/pyproject.toml:78-81`), the portable pin's single definition moves to
   the domain and `profiles.py` points at it:
   - line 7 becomes `QWEN_GGUF_REVISION = QWEN25_CODER_14B_Q5_K_M.revision`;
   - lines 9-18 (`PORTABLE = ModelProfile(...)`) become `PORTABLE = QWEN25_CODER_14B_Q5_K_M`;
   - a new import `from qwenloop.domain.catalogue import CATALOGUE, QWEN25_CODER_14B_Q5_K_M`
     goes directly above line 4 (`from qwenloop.domain.model import Backend, ModelProfile`, which
     stays: `NVIDIA_BF16` still uses both names);
   - appended at the end:
     ```python
     #: Every catalogue entry's llama.cpp pin, by profile name, so a GGUF can be chosen by name.
     CATALOGUE_PROFILES: dict[str, ModelProfile] = {
         entry.gguf.name: entry.gguf for entry in CATALOGUE if entry.gguf is not None
     }
     ```
4. New `src/qwenloop/domain/interfaces/catalogue_interface.py` declares
   `@runtime_checkable class ModelCatalogueInterface(Protocol)` with the three methods of behaviour 1
   (same signatures, a one-line docstring each, `...` bodies). It imports `ModelEntry` directly
   (`from qwenloop.domain.catalogue import ModelEntry`), the way `config_interface.py:7` imports
   `QwenConfig`; `catalogue.py` never imports the interfaces package, so there is no cycle.
   `src/qwenloop/domain/interfaces/__init__.py` imports it and lists `"ModelCatalogueInterface"`
   in `__all__` (between `"HardwareInterface"` and `"QwenConfigInterface"`).
5. A test asserts `ModelCatalogue().get("gpt-oss-20b").ollama.tag == DEFAULT_ENDPOINT_MODEL`
   (`domain/config.py:16`), so the default and the catalogue can never drift.

## Where to change
All paths are under `src/vibey_runners/qwen/`:
- new `src/qwenloop/domain/catalogue.py`;
- new `src/qwenloop/domain/interfaces/catalogue_interface.py`, plus its import and `__all__` entry
  in `src/qwenloop/domain/interfaces/__init__.py` (20 lines today; use `edit_file`);
- `src/qwenloop/infrastructure/profiles.py` (31 lines today): the three `edit_file` replacements
  and the append of behaviour 3;
- new `tests/test_catalogue.py`.

Line 1 of every new file is the provenance comment copied byte for byte from line 1 of
`src/qwenloop/infrastructure/profiles.py`. Line 2 is a one-line module docstring. Fix import order
with `UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check --select I --fix <file>` from the repository
root. `ModelCatalogue` gets the interface of behaviour 4 beside it (ADR-0016); the data classes are
frozen records, as `ModelProfile` is.

## Acceptance criteria
- [ ] Every entry is complete: `license_spdx` is non-empty; `recorded` matches
      `^\d{4}-\d{2}-\d{2}$`; every pinned `gguf.sha256` is 64 lowercase hex characters, its `size`
      is positive, its `revision` is 40 lowercase hex characters and its `filename` ends `.gguf`.
- [ ] `ModelCatalogue().get("nope")` raises `KeyError` whose text lists `gpt-oss-20b` and
      `qwen2.5-coder-14b`. A duplicate name, a duplicate Ollama tag, or an entry with no artifact
      raises `ValueError` with the messages of behaviour 1.
- [ ] `ModelCatalogue().by_ollama_tag("gpt-oss:20b").name == "gpt-oss-20b"`; an unknown tag gives
      `None`.
- [ ] `PROFILES` is unchanged; `PORTABLE` has today's values; `CATALOGUE_PROFILES[PORTABLE.name] is PORTABLE`.
- [ ] `test_the_endpoint_default_is_a_catalogued_ollama_tag` passes.
- [ ] The qwen tenant's whole suite passes at its 100% floor, and mypy, lint-imports and bandit
      are clean (block below).
- [ ] `git diff --stat` lists only the five files named under "Where to change".

## Tests to write first (TDD)
New `tests/test_catalogue.py` (no network, no Ollama, nothing patched — the catalogue is pure data
and `ModelCatalogue(entries=...)` is its own in-memory double):
- `test_every_entry_is_complete_and_dated` — for every entry in `CATALOGUE`: the four checks of the
  first acceptance item that apply without a GGUF (`license_spdx`, `recorded`, `min_ram_gib > 0`,
  `context_window > 0`), and `set(entry.unverified) <= {"llama.cpp", "ollama"}`. Also
  `{"qwen2.5-coder-14b", "gpt-oss-20b"} <= {e.name for e in CATALOGUE}` (a subset, not an exact
  count: later lanes append entries).
- `test_pinned_ggufs_carry_a_sha256_and_size` — for every entry whose `gguf` is not `None`:
  `re.fullmatch(r"[0-9a-f]{64}", gguf.sha256)`, `gguf.size > 0`,
  `re.fullmatch(r"[0-9a-f]{40}", gguf.revision)`, `gguf.filename.endswith(".gguf")`,
  `gguf.backend is Backend.LLAMA_CPP`, and no filename starts with `eagle3-`.
- `test_catalogue_rejects_duplicates_and_empty_entries` — build small `ModelEntry` values in the
  test and assert each `ValueError` message of behaviour 1 with `pytest.raises(..., match=...)`.
- `test_lookup_by_name_and_ollama_tag` — `get("gpt-oss-20b").family == "gpt-oss"`;
  `by_ollama_tag("gpt-oss:20b").name == "gpt-oss-20b"`; `by_ollama_tag("nope:1b") is None`;
  `get("nope")` raises under `pytest.raises(KeyError, match="known: .*gpt-oss-20b")` (a pattern
  later entries cannot break); `ModelCatalogue().entries() == CATALOGUE`.
- `test_the_endpoint_default_is_a_catalogued_ollama_tag` — behaviour 5.
- `test_existing_profiles_are_unchanged` — `set(PROFILES) == {"qwen2.5-coder-14b-q5-k-m", "qwen2.5-coder-14b-bf16"}`;
  every field of `PORTABLE` equals the literal of behaviour 1 (compare against a
  `ModelProfile(...)` written out in the test); `QWEN_GGUF_REVISION == "d0a692ef765eefbf2fabb130b3cb2e8917e3d225"`;
  `ModelCatalogue().get("qwen2.5-coder-14b").gguf is PORTABLE`;
  `CATALOGUE_PROFILES[PORTABLE.name] is PORTABLE`; `NVIDIA_BF16.name not in CATALOGUE_PROFILES`.
- `test_catalogue_satisfies_its_interface` — `isinstance(ModelCatalogue(), ModelCatalogueInterface)`,
  importing the interface from `qwenloop.domain.interfaces`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_runners/qwen
python -c "import qwenloop" || python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider --no-cov tests/test_catalogue.py tests/test_model_cache.py tests/test_inference.py
python -m pytest -q -p no:cacheprovider          # whole suite, 100% branch floor from addopts
python -m mypy --strict src/qwenloop
lint-imports
python -m bandit -q -r src/qwenloop
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the five files named under "Where to change"
```

## Out of scope
- The other models (split-383-2-qwen-entries), the family memory probe
  (split-383-3-memory-probe), RAM-tier selection (split-383-4-ram-tier-selection), the reasoning
  parsers (split-383-5-reasoning-channels), and `model verify` and doctor
  (split-383-6-model-verify-doctor).
- Loading or downloading any model. This lane loads nothing.
- `cli/app.py`: `model list`, `inspect`, `verify` and `install` keep reading `PROFILES`.
- vibey's own `DEFAULT_OLLAMA_MODEL` (`src/vibey/infrastructure/engines/ollama_chat.py`), which the
  installer wave ties to `DEFAULT_LOCAL_MODEL` (`specs/installer-ollama.md`), and the chart.
- `tests/conftest.py` and `tests/fakes.py`: do not edit them.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees: the docs wave owns
  those.
- Do not push, open PRs, or change git remotes. Commit locally as this spec's title.

## Conventions this lane relies on (everything needed is here)
**C1, tests.** The qwen tenant's floor is `--cov=qwenloop --cov-branch --cov-fail-under=100` in its
`pyproject.toml` addopts, so a focused run needs `--no-cov` and the whole-suite run must reach
100%. Substitute only at declared seams: never `monkeypatch.setattr` an import or a module/class
attribute, never `mock.patch`, `MagicMock` or `AsyncMock`. No test reaches the network or a live
Ollama; the tenant's `tests/conftest.py` autouse fixtures (`isolated_settings`, `no_local_ollama`)
already keep a developer's configuration and running Ollama out of every test.

**C2, reading a pin from its source (10.f).** Run from the lane shell, never from a test:
```bash
REPO=ggml-org/gpt-oss-20b-GGUF
SHA=$(curl -fsS "https://huggingface.co/api/models/$REPO" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"])')
echo "$SHA"
curl -fsS "https://huggingface.co/api/models/$REPO/tree/$SHA" | python3 -c '
import json, sys
for f in json.load(sys.stdin):
    if f["path"].endswith(".gguf"):
        print(f["path"], f["size"], (f.get("lfs") or {}).get("oid"))'
```
Use the line whose path is `gpt-oss-20b-MXFP4.gguf`: `size` is the second field and the `lfs.oid`
(the file's sha256) the third. On 2026-09-22 the spec writer saw that path with size
12,109,566,624 beside two `eagle3-` files; if the API now says otherwise, the API wins. A `curl`
failure (no network) means `gguf=None`, as behaviour 2 says.

**C3, the data classes.** `ModelProfile` is
`ModelProfile(name, backend, repository, revision, filename, sha256, size, quantization, context_window=32_768)`
(`src/qwenloop/domain/model.py:36-46`); `Backend.LLAMA_CPP` is `"llama.cpp"`.

**Depends on:** default-model-p1
- default-model-p1: `DEFAULT_ENDPOINT_MODEL == "gpt-oss:20b"` in `domain/config.py:16` (integrated as #387 at `ddf2bf05`), which behaviour 5's test ties the catalogue to.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
