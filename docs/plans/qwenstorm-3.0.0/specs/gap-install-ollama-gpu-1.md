## Title
feat(domain): which Arch Ollama package fits the machine's GPU, with a declared override

## Why
8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) makes Arch Linux the default sovereign OS,
and 8.d makes GPT-OSS 20B the default model. On Arch, the plain `ollama` package runs on the
CPU. Arch ships GPU builds, `ollama-cuda` (NVIDIA) and `ollama-rocm` (AMD), and `ollama-vulkan`
where the repository carries it. The installer's catalogue pins `ollama` alone
(`specs/installer-catalogue.md:65-68`), and `specs/installer-ollama.md:117` names the GPU
variants "a follow-up" (`issue-audit/gaps.md` H1, lines 429-434). 10's "read both sides of the
fit" asks for the build that matches the hardware.

This lane is the pure rule. `-2` detects the GPU, and `-3` wires both into the installer's composition.

## Required behaviour
1. New pure module `src/vibey/domain/ollama_variant.py` (provenance header; stdlib and
   `vibey.domain` only):
   - `class GpuVendor(StrEnum)`: `NVIDIA = "nvidia"`, `AMD = "amd"`, `INTEL = "intel"`,
     `NONE = "none"`, `UNKNOWN = "unknown"`.
   - `ARCH_OLLAMA_PACKAGES: Final[tuple[str, ...]] = ("ollama", "ollama-cuda", "ollama-rocm", "ollama-vulkan")`.
   - `class OllamaVariantPolicy` with
     `arch_package(self, vendors: tuple[GpuVendor, ...], override: str | None = None) -> str`:
     - A non-empty `override` must be in `ARCH_OLLAMA_PACKAGES`. It is returned as given, or
       raises `ValueError(f"ollama variant {override!r} is not one of {', '.join(ARCH_OLLAMA_PACKAGES)}")`.
     - Otherwise NVIDIA present gives `ollama-cuda`; else AMD gives `ollama-rocm`; else INTEL
       gives `ollama-vulkan`; else `ollama`. NVIDIA wins over AMD on a mixed machine, because
       CUDA is Ollama's most mature backend. Write that reason in the docstring.
     - `reason(self, vendors, override) -> str` returns one line for the installer's report:
       `"override VIBEY_OLLAMA_VARIANT=<p>"`, `"detected <vendor> GPU"`, or
       `"no supported GPU detected; CPU build"`.
   - `OLLAMA_VARIANTS: Final[OllamaVariantPolicyInterface] = OllamaVariantPolicy()`.
2. New interface `src/vibey/domain/interfaces/ollama_variant_interface.py`: a
   `@runtime_checkable` Protocol `OllamaVariantPolicyInterface` with `arch_package` and `reason`.
   Export it from `src/vibey/domain/interfaces/__init__.py`.
3. The macOS recipe is untouched. Homebrew's `ollama` uses Metal on Apple silicon.

## Where to change
- New: `src/vibey/domain/ollama_variant.py`, `src/vibey/domain/interfaces/ollama_variant_interface.py`.
- `src/vibey/domain/interfaces/__init__.py` (edit_file, the export).
- New test `tests/domain/test_ollama_variant.py`.

## Acceptance criteria
- [ ] `(NVIDIA,)` gives `ollama-cuda`; `(AMD,)` `ollama-rocm`; `(INTEL,)` `ollama-vulkan`;
      `(NONE,)`, `()` and `(UNKNOWN,)` give `ollama`; `(AMD, NVIDIA)` gives `ollama-cuda`.
- [ ] The override `"ollama"` wins over a detected NVIDIA. `"ollama-metal"` raises the exact `ValueError`.
- [ ] `reason` gives the three exact forms.
- [ ] Domain purity passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_ollama_variant.py`:
- `test_vendor_to_package` (parametrized)
- `test_nvidia_wins_on_a_mixed_machine`
- `test_override_wins_and_is_validated`
- `test_reason_lines`
- `test_policy_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- GPU detection (`-2`), wiring (`-3`), whether `ollama-vulkan` exists in Arch's repositories today
  (`-3` checks it at install time), and docs.

Commit as `feat(domain): the Arch Ollama package follows the GPU`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
