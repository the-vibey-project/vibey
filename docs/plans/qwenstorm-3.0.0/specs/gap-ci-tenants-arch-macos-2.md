## Title
ci: every tenant's floor row also runs on Arch Linux

## Why
8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) makes Arch Linux the default sovereign OS,
and every change must be proven on it. The `tools` job (`.github/workflows/ci.yml:195-690`)
cannot simply gain Arch rows. Arch needs a container, and it cannot use
`actions/setup-python` (`:568-570`), whose prebuilt interpreters target Ubuntu. So a sibling job
`tools-arch` runs each tenant's 3.12 floor row inside `archlinux:base-devel`, with Python from
`uv python install` (`issue-audit/gaps.md` F3).

## Required behaviour
1. `ci.yml` gains a job `tools-arch`, placed after `tools`:
   - `name: ${{ matrix.package }} on ${{ matrix.python }} (Arch Linux)`,
     `needs: [uv-lock]`, `runs-on: ubuntu-latest`, `container: archlinux:base-devel`,
     `strategy: { fail-fast: false, matrix: { include: [...] } }`.
   - The matrix rows copy, for every tenant, its `python: "3.12"` Ubuntu row from `tools`:
     `package`, `dir`, `python`, `install`, `static` and `test` exactly. Leave out
     `network_test` and `docs`.
   - Steps, in order:
     1. `pacman -Syu --noconfirm --needed git uv`;
     2. `actions/checkout@v4` with `fetch-depth: 0`;
     3. `git config --global --add safe.directory "$GITHUB_WORKSPACE"`;
     4. `uv python install ${{ matrix.python }} && uv venv --python ${{ matrix.python }} /opt/venv && echo "/opt/venv/bin" >> "$GITHUB_PATH" && echo "VIRTUAL_ENV=/opt/venv" >> "$GITHUB_ENV"`;
     5. `python -m ensurepip --upgrade`, so `pip install -e …` in `install` works in the venv;
     6. then the same steps as `tools`, `Install` through `Its own suite, unchanged`: the
        family-provenance script (`:586-640`) byte for byte, plus the `static` and `test`
        steps with their `if:` conditions.
   - A comment at the job head cites 8.h and explains why the job is separate (container, no setup-python).
2. `tests/meta/test_tools_matrix_covers_every_package.py` gains
   `test_every_gateable_package_has_an_arch_floor_row`. It reads
   `jobs["tools-arch"]["strategy"]["matrix"]["include"]` and asserts:
   - each gateable package has a 3.12 row with `test`;
   - each row's `install`, `static` and `test` equal the same package's 3.12 Ubuntu row in `tools`;
   - the job's `container` is `archlinux:base-devel`.

## Where to change
- `.github/workflows/ci.yml` (edit_file; one insertion after the `tools` job, before `tools-lint` at about `:691`).
- `tests/meta/test_tools_matrix_covers_every_package.py` (append).

## Acceptance criteria
- [ ] The YAML loads, and every meta-test in that file passes.
- [ ] Changing one Arch row's `test` string makes the new test fail with the package named.
- [ ] **Evidence, recorded by the reviewer:** the `(Arch Linux)` rows go green on the first run, or each
      failure is filed as an 8.h finding against its tenant (never fixed by dropping the row).

## Tests to write first (TDD)
Append to `tests/meta/test_tools_matrix_covers_every_package.py`:
- `test_every_gateable_package_has_an_arch_floor_row`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Required checks (`gap-ci-os-required-checks`); every Python version on Arch (the floor proves the OS); docs.

Commit as `ci: every tenant's floor row runs on Arch Linux`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
