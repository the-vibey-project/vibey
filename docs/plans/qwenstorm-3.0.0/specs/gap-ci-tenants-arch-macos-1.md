## Title
ci: every tenant's floor row also runs on macOS

## Why
8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) binds the whole family, not only
`src/vibey`. The `tools` matrix (`.github/workflows/ci.yml:195-690`) runs every tenant on Ubuntu,
except codexloop, which also has macOS rows for 3.12–3.14 (`:405-440`; `issue-audit/gaps.md` F3).
A row runs on another OS by naming `os` (`runs-on: ${{ matrix.os || 'ubuntu-latest' }}`,
`:200`), and the check name then gains a suffix (`:198`), so existing names are unchanged.

Every tenant publishes at the common 3.12 floor (ADR-0037;
`tests/meta/test_tools_matrix_covers_every_package.py`, `SUPPORTED_PYTHON`). One macOS row per
tenant, at 3.12, proves the OS without tripling the matrix. codexloop keeps its three rows.

## Required behaviour
1. For every tenant that has a `python: "3.12"` Ubuntu row in `tools` and no macOS row yet,
   append a row that copies its 3.12 Ubuntu row exactly, adding `os: macos-latest` and leaving
   out `network_test` and `docs`, which stay once per tenant, on Ubuntu. That means the
   package's `dir`, `install`, `static` and `test` are identical. Add each new row directly
   after that tenant's last row.
2. `tests/meta/test_tools_matrix_covers_every_package.py` gains
   `test_every_gateable_package_has_a_macos_floor_row`. For each package from
   `_gateable_packages()` (`:71`), some row has `os == "macos-latest"`, `python == "3.12"`
   and a `test` key. The static-only `vibey-runners-common` row is exempt by the existing
   suite rule, because it ships no suite. The failure message cites 8.h.
3. Nothing else changes.

## Where to change
- `.github/workflows/ci.yml`, the `tools` matrix only (edit_file; one insertion per tenant).
- `tests/meta/test_tools_matrix_covers_every_package.py` (append one test).

## Acceptance criteria
- [ ] The YAML loads. Existing meta-tests in that file pass unchanged, and the new one passes.
- [ ] Deleting any one added macOS row makes the new test fail and name the package (check by a scratch edit and revert).
- [ ] **Evidence, recorded by the reviewer:** every new `(macos-latest)` row is green on the first run, or its
      failure is filed as an 8.h finding against that tenant.

## Tests to write first (TDD)
Append to `tests/meta/test_tools_matrix_covers_every_package.py`:
- `test_every_gateable_package_has_a_macos_floor_row`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Arch rows (`gap-ci-tenants-arch-macos-2`), required checks, and docs.

Commit as `ci: every tenant's floor row runs on macOS`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
