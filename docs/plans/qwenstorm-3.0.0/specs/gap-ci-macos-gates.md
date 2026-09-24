## Title
ci: the seven-gate sweep runs on macOS on every change

## Why
Sub-doctrine 8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) makes macOS the default paid
operating system "with the same standing, so a change that works on one but not the other is
not done". vibey's gates never run on macOS. Only codexloop's tenant rows do
(`.github/workflows/ci.yml:405-440`; `issue-audit/gaps.md` F2, lines 349-354). GitHub's macOS
runners cannot run service containers, so this depends on `fakes-ci-no-services`, which leaves
the default tier with no service.

## Required behaviour
1. `ci.yml` gains a job `gates-macos`, placed after `gates-arch`:
   ```yaml
     gates-macos:
       name: gates (macOS)
       needs: [uv-lock]
       runs-on: macos-latest
       steps:
         # 8.h: macOS is the default paid OS, with the same standing as Arch Linux.
         - uses: actions/checkout@v4
         - name: Install uv
           uses: astral-sh/setup-uv@v7
           with:
             enable-cache: true
         - name: Set up Python
           run: uv python install 3.12
         - name: Install dependencies
           run: uv sync --extra dev
   ```
   Then come the same gate steps as `gates`, byte for byte, as in `gap-ci-arch-gates`.
2. Append to `tests/meta/test_ci_default_os.py`:
   - `test_the_macos_gates_mirror_the_ubuntu_gates`: the same `_gate_runs` equality, for `gates-macos`;
   - `test_the_macos_gates_run_on_macos`: `runs-on == "macos-latest"` and no `services`.

## Where to change
- `.github/workflows/ci.yml` (edit_file, one insertion after `gates-arch`).
- `tests/meta/test_ci_default_os.py` (append).

## Acceptance criteria
- [ ] The YAML loads, and every test in `tests/meta/test_ci_default_os.py` passes.
- [ ] **Evidence, recorded by the reviewer:** the first PR run shows `gates (macOS)` green, with
      its URL. A macOS-only failure is a real finding to fix in code, never by skipping the job.

## Tests to write first (TDD)
Append to `tests/meta/test_ci_default_os.py`:
- `test_the_macos_gates_mirror_the_ubuntu_gates`
- `test_the_macos_gates_run_on_macos`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Tenants, required checks and docs.

Commit as `ci: the gates run on macOS`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
