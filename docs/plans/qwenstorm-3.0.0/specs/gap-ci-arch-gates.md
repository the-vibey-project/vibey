## Title
ci: the seven-gate sweep runs on Arch Linux on every change

## Why
Sub-doctrine 8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) makes Arch Linux the default
sovereign operating system: "every feature works on Arch Linux … every change is proven on
it". Every job in `.github/workflows/ci.yml` runs on `ubuntu-latest` (`:20`, `:32`, `:107`,
`:144`, `:200`), apart from three codexloop rows on macOS (`:405-440`). No `archlinux`
appears in `.github/` (`issue-audit/gaps.md` F1, lines 342-347).

GitHub has no Arch-hosted runner, so the job runs in the official `archlinux:base-devel`
container. `fakes-ci-no-services` removes PostgreSQL from the default tier, so the sweep needs
no service. The real-service integration tier stays on Ubuntu (`postgres-compatibility`).
`ci.yml` is repository-local; vibey-gh does not render it (`src/vibey_tools/gh/README.md:974`).

## Required behaviour
1. `.github/workflows/ci.yml` gains a job `gates-arch`, placed right after `gates` (`:30-102`):
   ```yaml
     gates-arch:
       name: gates (Arch Linux)
       needs: [uv-lock]
       runs-on: ubuntu-latest
       container: archlinux:base-devel
       steps:
         # 8.h: Arch Linux is the default sovereign OS, and every change is proven on it.
         # git before checkout, so actions/checkout makes a real clone rather than a tarball.
         - name: Arch toolchain
           run: pacman -Syu --noconfirm --needed git uv
         - uses: actions/checkout@v4
         - name: Trust the checkout
           run: git config --global --add safe.directory "$GITHUB_WORKSPACE"
         - name: Set up Python
           run: uv python install 3.12
         - name: Install dependencies
           run: uv sync --extra dev
   ```
   After those steps come the **same** steps as `gates`, from `Gate 1 - ruff check` through
   `Gate 7 - pip-audit`, with names and `run` commands copied byte for byte from `gates` as it
   stands when this lane runs (after `fakes-ci-no-services`). The job has no `services:` and no
   `VIBEY_TEST_DATABASE_URL`.
2. A new meta-test file, `tests/meta/test_ci_default_os.py`, with the provenance header and a
   module docstring citing 8.h:
   - `_gate_runs(job) -> list[str]` returns the `run` of every step whose `name` starts with
     `Gate ` or equals `Run test suite with coverage`, in order.
   - `test_the_arch_gates_mirror_the_ubuntu_gates` asserts
     `_gate_runs(jobs["gates-arch"]) == _gate_runs(jobs["gates"])`, and that the list is non-empty.
   - `test_the_arch_gates_run_in_the_arch_container` asserts
     `jobs["gates-arch"]["container"] == "archlinux:base-devel"` and `"services" not in jobs["gates-arch"]`.
   - YAML is loaded with `yaml.safe_load` from `REPO / ".github/workflows/ci.yml"`, in the
     style of `tests/meta/test_tools_matrix_covers_every_package.py:43-60`.
3. Nothing else in `ci.yml` changes.

## Where to change
- `.github/workflows/ci.yml` (1033 lines; edit_file only, one insertion after the `gates` job).
- New `tests/meta/test_ci_default_os.py`.

## Acceptance criteria
- [ ] `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` passes.
- [ ] Both meta-tests pass. The mirror test fails if a gate step is dropped from `gates-arch`
      (check by a scratch edit and revert).
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes.
- [ ] **Evidence, recorded by the reviewer:** the first PR run shows `gates (Arch Linux)` green,
      with its run URL. A red run is a real 8.h finding to fix, never a reason to relax the job.

## Tests to write first (TDD)
`tests/meta/test_ci_default_os.py`:
- `test_the_arch_gates_mirror_the_ubuntu_gates`
- `test_the_arch_gates_run_in_the_arch_container`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- macOS (`gap-ci-macos-gates`), tenants (`gap-ci-tenants-arch-macos-*`), required checks
  (`gap-ci-os-required-checks`), the integration tier on Arch (a follow-up), and docs.

Commit as `ci: the gates run on Arch Linux`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
