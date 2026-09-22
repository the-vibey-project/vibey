<!-- split of #383: child 2 of 6; audit: issue-audit/updates/383.md -->

## Title
feat(qwenloop): catalogue Qwen3.6-27B, Qwen3.6-35B-A3B and Qwen3.8-27B on both backends

## Why
Sub-doctrine 8.d (`src/vibey_tools/gh/docs/doctrines.md:236-257`) requires every gold-standard
free laptop model to be pinned in the catalogue (source, revision, digest), runnable on Ollama and
llama.cpp, with the evidence and date of each choice recorded (10.f, `doctrines.md:419`). The
operator's tier table of 2026-09-22 names Qwen3.6-27B (24–32 GB) and Qwen3.6-35B-A3B (48–64 GB),
and asks for Qwen3.8-27B; under the operator's ruling of the same day they are **opt-in
alternatives** to GPT-OSS 20B, which stays the default wherever it fits (8.d). The catalogue
split-383-1-model-catalogue adds (`src/vibey_runners/qwen/src/qwenloop/domain/catalogue.py`,
`CATALOGUE`) holds only Qwen2.5-Coder-14B and GPT-OSS 20B. This lane adds one entry per model as
data plus tests; the downloads and load tests are operator evidence, never CI.

## Required behaviour
All paths are under `src/vibey_runners/qwen/`.

1. `src/qwenloop/domain/catalogue.py` gains up to three `ModelEntry` constants, appended to the
   `CATALOGUE` tuple after the existing entries, in this order: `qwen3.6-27b`, `qwen3.6-35b-a3b`,
   `qwen3.8-27b`. Every value below is read from its source with the commands under "Conventions"
   (C2, C3) on the day the lane runs; none is typed from memory (10.f).
2. The fields of each entry:
   | field | qwen3.6-27b | qwen3.6-35b-a3b | qwen3.8-27b |
   |---|---|---|---|
   | `name` | `"qwen3.6-27b"` | `"qwen3.6-35b-a3b"` | `"qwen3.8-27b"` |
   | `family` | `"qwen3.6"` | `"qwen3.6"` | `"qwen3.8"` |
   | base model (C3) | `Qwen/Qwen3.6-27B` | `Qwen/Qwen3.6-35B-A3B` | `Qwen/Qwen3.8-27B` |
   | GGUF repository (C2) | `unsloth/Qwen3.6-27B-GGUF` | `unsloth/Qwen3.6-35B-A3B-GGUF` | `unsloth/Qwen3.8-27B-GGUF` |
   | Ollama library (C4) | `qwen3.6` | `qwen3.6` | `qwen3.8` |
   | `min_ram_gib` | `24` | `48` | `24` |
   - `total_params_b`: the base model's `safetensors.total` divided by 1e9, rounded to one decimal.
   - `active_params_b`: equal to `total_params_b` for the two dense 27B models. For
     `qwen3.6-35b-a3b`, the activated-parameter count its model card states (C3), in billions to one
     decimal; if the card states none, `3.0` from the `A3B` in its name, and `evidence` says so.
   - `license_spdx` and `license_osi`: from the base model's `license:` tag (C3). `apache-2.0` →
     `"Apache-2.0"`, `True`; `mit` → `"MIT"`, `True`; any other value → that value verbatim,
     `False`, and the commit body names it.
   - `min_ram_gib`: the operator's tier where the operator named the model (Qwen3.6-27B: 24;
     Qwen3.6-35B-A3B: 48). Qwen3.8-27B is not in the operator's table; it takes its sibling
     Qwen3.6-27B's tier (24: the same parameter count and quantization) and `evidence` says so.
   - `context_window`: the base model's `config.json` `text_config.max_position_embeddings`, or the
     top-level `max_position_embeddings` when there is no `text_config` (C3).
   - `ollama`: `OllamaArtifact(tag)` for the library's plain size tag (`27b`, `35b-a3b`), confirmed
     by the registry manifest answering HTTP 200 (C4); `None` if the library lists no such tag.
   - `gguf`: a `ModelProfile` with `backend=Backend.LLAMA_CPP`, `repository` = the GGUF repository,
     `revision` = the API's `sha`, and `filename`, `size`, `sha256` = that file's `path`, `size`,
     `lfs.oid` from the tree listed at that `sha` (C2). The file is chosen by this rule:
     `<Model>-Q4_K_M.gguf` at the repository root if the tree lists it, else
     `<Model>-UD-Q4_K_M.gguf`, else no GGUF (`gguf=None`). `quantization` is the file name between
     `<Model>-` and `.gguf` (`"Q4_K_M"` or `"UD-Q4_K_M"`). `name` is the entry name, `-`, and the
     quantization lower-cased with `_` turned into `-` (for example `"qwen3.6-27b-q4-k-m"`,
     `"qwen3.8-27b-ud-q4-k-m"`). `context_window` stays at the `ModelProfile` default. Never pin an
     `mmproj-*` file, an `imatrix*` file, a split `-0000N-of-0000M` file, or a file under a
     subdirectory (`BF16/`, `MTP/`).
   - `evidence`: one sentence naming the operator's tier table of 2026-09-22 (or, for Qwen3.8-27B,
     its sibling's tier), `opt-in alternative to gpt-oss-20b under the operator's ruling of 2026-09-22`,
     the GGUF as `<repository>@<first 12 characters of sha> <filename>`, and `not load-tested`.
   - `recorded`: the date the lane read the pins, `date -u +%F`.
   - `unverified=("llama.cpp", "ollama")` for every new entry. The lane host loads none of these
     models (a 24 GB lane host already holds gpt-oss:20b resident, and ADR-0046 §4 keeps one model
     resident per machine). The operator's load evidence is recorded in a follow-up commit (C5).
3. An entry is added only if at least one artifact (`ollama` or `gguf`) was read from source. A
   model with neither is left out and named in the commit body as a follow-up. If both
   huggingface.co and ollama.com are unreachable from the lane host, change nothing, and report the
   lane blocked (10.f).
4. `CATALOGUE_PROFILES` (`src/qwenloop/infrastructure/profiles.py`, from split-383-1) picks up each
   new GGUF automatically; `PROFILES`, `PORTABLE`, `NVIDIA_BF16` and every default stay exactly as
   they are. No selection changes.

## Where to change
All paths are under `src/vibey_runners/qwen/`:
- `src/qwenloop/domain/catalogue.py`: add the new `ModelEntry` constants directly above the
  `CATALOGUE = (` line, and add their names inside that tuple after the existing entries. Use
  `edit_file` with the `CATALOGUE = (` block as `old_string`; never rewrite the module.
- `tests/test_catalogue.py`: append the tests below (open it in append mode; never rewrite it).

Nothing else. No new class, so no new interface.

## Acceptance criteria
- [ ] `python -m pytest -q -p no:cacheprovider --no-cov tests/test_catalogue.py` passes, including
      the existing split-383-1 tests (every GGUF sha256 is 64 hex characters, every entry dated).
- [ ] `test_the_new_qwen_entries_follow_the_pinning_rules` and
      `test_the_new_qwen_entries_are_never_claimed_as_loaded` pass.
- [ ] Every new `gguf` appears in `CATALOGUE_PROFILES`.
- [ ] The commit body lists, per entry, the revision `sha` read and the date, plus every model or
      artifact left out and why.
- [ ] The qwen tenant's whole suite passes at its 100% floor; mypy, lint-imports, bandit, ruff are
      clean (block below).
- [ ] `git diff --stat` lists only `src/qwenloop/domain/catalogue.py` and `tests/test_catalogue.py`.

## Tests to write first (TDD)
Append to `tests/test_catalogue.py` (pure data; nothing patched, no network). The names used here
(`ModelCatalogue`, `CATALOGUE_PROFILES`) are already imported at the top of that file by
split-383-1; if one is missing, add it to the top import block with `edit_file` — never put an
import below code (ruff E402).
- A module constant `NEW_QWEN = ("qwen3.6-27b", "qwen3.6-35b-a3b", "qwen3.8-27b")`, reduced to the
  names this lane actually added (behaviour 3).
- `test_the_new_qwen_entries_follow_the_pinning_rules` — for each name in `NEW_QWEN`, `entry =
  ModelCatalogue().get(name)`:
  - `entry.min_ram_gib == {"qwen3.6-27b": 24, "qwen3.6-35b-a3b": 48, "qwen3.8-27b": 24}[name]`;
  - `entry.ollama is not None or entry.gguf is not None`;
  - if `entry.gguf`: `entry.gguf.repository.startswith("unsloth/")`,
    `entry.gguf.quantization in {"Q4_K_M", "UD-Q4_K_M"}`,
    `entry.gguf.filename.endswith(f"-{entry.gguf.quantization}.gguf")`,
    `"/" not in entry.gguf.filename`, `not entry.gguf.filename.startswith("mmproj")`,
    `entry.gguf.name == f"{name}-{entry.gguf.quantization.lower().replace('_', '-')}"`, and
    `CATALOGUE_PROFILES[entry.gguf.name] is entry.gguf`;
  - if `entry.ollama`: `entry.ollama.tag.startswith(entry.family + ":")`;
  - `entry.total_params_b >= entry.active_params_b > 0`.
- `test_the_new_qwen_entries_are_never_claimed_as_loaded` — for each name in `NEW_QWEN`:
  `set(entry.unverified) == {"llama.cpp", "ollama"}`, `"not load-tested" in entry.evidence`,
  `"opt-in alternative" in entry.evidence`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_runners/qwen
python -c "import qwenloop" || python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider --no-cov tests/test_catalogue.py
python -m pytest -q -p no:cacheprovider          # whole suite, 100% branch floor from addopts
python -m mypy --strict src/qwenloop
lint-imports
python -m bandit -q -r src/qwenloop
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only catalogue.py and tests/test_catalogue.py
```

## Out of scope
- Downloading or loading any model on the lane host, and any test that reaches the network or a
  live Ollama. The loads are operator evidence (C5), recorded by a follow-up commit.
- Making any of these models a default, and the RAM tiers (split-383-4-ram-tier-selection). They
  are opt-in alternatives: an operator chooses one with `model` / `QWENLOOP_MODEL` / `--model`.
- The sub-8.d-floor models (Gemma 4 E2B, Qwen 3.5 4B) and the models the operator named that are
  not on this list (Llama 3.x, DeepSeek V4 Flash, Qwen3 235B-A22B, Qwen 3.5 9B).
- `qwenloop model install` for these GGUFs (it installs the portable profile only), `model verify`
  and doctor (split-383-6-model-verify-doctor).
- `infrastructure/profiles.py`, `tests/conftest.py`, `tests/fakes.py`: do not edit them.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs, or change git remotes. Commit locally as this spec's title.

## Conventions this lane relies on (everything needed is here)
**C1, the shapes.** From split-383-1 (`src/qwenloop/domain/catalogue.py`):
`OllamaArtifact(tag: str)` and
`ModelEntry(name, family, total_params_b, active_params_b, license_spdx, license_osi, min_ram_gib, context_window, ollama, gguf, evidence, recorded, unverified=())`,
both frozen; `ModelProfile(name, backend, repository, revision, filename, sha256, size, quantization, context_window=32_768)`
(`src/qwenloop/domain/model.py:36-46`); `Backend.LLAMA_CPP` is `"llama.cpp"`.
`ModelCatalogue()` refuses a duplicate name or Ollama tag and an entry with no artifact.

**C2, a GGUF pin (Hugging Face API).** Run in the lane shell, never in a test:
```bash
REPO=unsloth/Qwen3.6-27B-GGUF      # then unsloth/Qwen3.6-35B-A3B-GGUF, unsloth/Qwen3.8-27B-GGUF
SHA=$(curl -fsS "https://huggingface.co/api/models/$REPO" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"])')
echo "$REPO $SHA"
curl -fsS "https://huggingface.co/api/models/$REPO/tree/$SHA" | python3 -c '
import json, sys
for f in json.load(sys.stdin):
    if f["type"] == "file" and f["path"].endswith(".gguf"):
        print(f["path"], f["size"], (f.get("lfs") or {}).get("oid"))'
```
The listing's third column is the sha256. On 2026-09-22 the spec writer saw
`Qwen3.6-27B-Q4_K_M.gguf` (16,817,244,384 bytes), `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`
(22,134,528,992) and `Qwen3.8-27B-UD-Q4_K_M.gguf` (16,464,440,224), and no plain `Q4_K_M` file in
the last two; if the API now says otherwise, the API wins.

**C3, the base model's facts.**
```bash
BASE=Qwen/Qwen3.6-27B              # then Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-27B
curl -fsS "https://huggingface.co/api/models/$BASE" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("license tags:", [t for t in d.get("tags", []) if t.startswith("license:")])
print("safetensors total:", (d.get("safetensors") or {}).get("total"))'
curl -fsSL "https://huggingface.co/$BASE/raw/main/config.json" | python3 -c '
import json, sys
c = json.load(sys.stdin)
print("context:", (c.get("text_config") or {}).get("max_position_embeddings") or c.get("max_position_embeddings"))'
curl -fsSL "https://huggingface.co/$BASE/raw/main/README.md" | grep -i -m3 "activated"
```
On 2026-09-22 the Hugging Face API tagged all three GGUF repositories `license:apache-2.0`.

**C4, an Ollama tag (ollama.com/library).**
```bash
curl -fsS https://ollama.com/library/qwen3.6/tags | grep -oE 'qwen3\.6:[A-Za-z0-9._-]+' | sort -u
curl -fsS https://ollama.com/library/qwen3.8/tags | grep -oE 'qwen3\.8:[A-Za-z0-9._-]+' | sort -u
# confirm the one chosen: 200 means it exists
curl -s -o /dev/null -w '%{http_code}\n' \
  -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
  https://registry.ollama.ai/v2/library/qwen3.6/manifests/27b
```

**C5, the operator's load evidence (not CI, not this lane).** On a machine with the tier's RAM
(macOS and Arch Linux, 8.h), per entry and backend:
```bash
# llama.cpp: download the pinned file at the pinned revision, check it, load it, ask once
curl -fL -o model.gguf "https://huggingface.co/$REPO/resolve/$SHA/$FILENAME"
shasum -a 256 model.gguf        # macOS; `sha256sum model.gguf` on Arch Linux
llama-server --model model.gguf --jinja --ctx-size 32768 --port 8089 &
curl -s http://127.0.0.1:8089/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Reply with OK"}],"max_tokens":16}'
# Ollama: pull the tag, ask once, read what is resident
ollama pull "$TAG" && ollama run "$TAG" "Reply with OK" && ollama ps
# the machine: `sysctl -n machdep.cpu.brand_string; sysctl -n hw.memsize` (macOS),
# `uname -a; grep MemTotal /proc/meminfo` (Arch Linux)
```
The follow-up commit writes the machine, the date and a one-line result into the entry's
`evidence` and removes that backend from `unverified`. A backend that did not load stays in
`unverified` and is never claimed. The GGUF is never taken from Ollama's blob store.

**C6, tests.** Focused runs need `--no-cov` (the tenant's addopts carry a 100% floor). Never
`monkeypatch.setattr` an import or a module/class attribute, `mock.patch`, `MagicMock` or
`AsyncMock`. No test reaches the network or a live Ollama.

**Depends on:** split-383-1-model-catalogue
- split-383-1-model-catalogue: `ModelEntry`, `OllamaArtifact`, `CATALOGUE`, `ModelCatalogue` in `domain/catalogue.py`, `CATALOGUE_PROFILES` in `infrastructure/profiles.py`, and `tests/test_catalogue.py` to append to.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
