## Title
feat(install): on Arch Linux, `vibey install` installs the Ollama build that matches the GPU

## Why
`gap-install-ollama-gpu-1` chooses the Arch package, and `-2` reads the GPU vendors. The
installer's composition (`LocalStackComposition.build`, appended to `src/vibey/bootstrap.py` by
`installer-composition`, `specs/installer-composition.md:21-40`) maps each catalogue spec to an
installer. The `ollama` spec's Arch recipe names `("ollama",)` (`specs/installer-catalogue.md:67`).
This lane substitutes the chosen variant before the package installer is built, so the
catalogue stays one declaration (12.c) and the choice is visible in the report (10.f).

## Required behaviour
1. `LocalStackComposition.__init__` gains the keywords
   `gpu_probe: GpuProbeInterface | None = None` (default `SysfsGpuProbe()`) and
   `variants: OllamaVariantPolicyInterface = OLLAMA_VARIANTS`. It reads
   `VIBEY_OLLAMA_VARIANT` from the `environ` mapping it already receives. The environment is
   the declared seam, never `os.environ` directly.
2. In `build(specs, *, model)`, when `self.host()` is Arch and a spec has
   `spec.key == "ollama"`, it computes
   `package = variants.arch_package(gpu_probe.vendors(), override=environ.get("VIBEY_OLLAMA_VARIANT"))`.
   It then builds the package installer from a copy of the spec whose Arch recipe's package
   names are `(package,)`. Everything else is unchanged; `dataclasses.replace` on the frozen
   recipe and spec keeps the catalogue object itself untouched. The service name stays
   `ollama`: every variant provides `ollama.service`.
   - An invalid override raises the policy's `ValueError`. The CLI already reports installer
     errors, and it must surface this one with exit 2. Verify it with the CLI test named below.
3. The report shows the choice. The `ollama` line's detail is prefixed with
   `variants.reason(...)`, for example `"detected nvidia GPU; ollama-cuda"`. Implement this
   through whatever detail or title field `CataloguePackageInstaller` reports. Read
   `installer-host-runner`'s and `installer-composition`'s final code first. If no field can
   carry it without changing another lane's class, add one line to the stack presenter's output
   instead: `f"ollama variant: {package} ({reason})"`.
4. macOS is unchanged, and `gpu_probe.vendors()` is never called there.

## Where to change
- `src/vibey/bootstrap.py`: `LocalStackComposition` only (edit_file; the file is large).
- `src/vibey/bootstrap_interface.py`: only if the constructor signature is part of `LocalStackCompositionInterface`.
- Tests: append to the composition test file that `installer-composition` created
  (`grep -rln "LocalStackComposition" tests`). Use `FixedGpuProbe` from `tests/fakes/`, a fake
  executor, and an Arch os-release file under `tmp_path`.

## Acceptance criteria
- [ ] An Arch host with `FixedGpuProbe((NVIDIA,))` yields a package install command naming
      `ollama-cuda`, as seen by the fake executor. AMD gives `ollama-rocm`, and no GPU gives `ollama`.
- [ ] `VIBEY_OLLAMA_VARIANT=ollama` on an NVIDIA machine installs `ollama`.
      `VIBEY_OLLAMA_VARIANT=bogus` makes `vibey install` exit 2, naming the allowed values.
- [ ] A macOS host never calls the probe (a probe that raises proves it).
- [ ] The installer report names the variant and its reason.
- [ ] Every existing installer test passes unchanged. 100% branch coverage for the layers touched.

## Tests to write first (TDD)
Append to the composition test file:
- `test_arch_nvidia_installs_ollama_cuda`
- `test_arch_amd_installs_ollama_rocm`
- `test_arch_without_gpu_installs_plain_ollama`
- `test_variant_override_wins`
- `test_invalid_variant_exits_2` (through the CLI, with `obj=` the composition)
- `test_macos_never_probes_the_gpu`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Verifying on a real Arch GPU host. That is operator evidence: the reviewer records
  `pacman -Si ollama-cuda ollama-rocm ollama-vulkan` output from an Arch machine, and a missing
  package is reported and never invented.
- macOS and docs.

Commit as `feat(install): Arch installs the Ollama build that matches the GPU`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
