## Title
build(image): an Arch Linux variant of the runnable image, contract-tested like the Debian one

## Why
8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`): "Arch Linux is always the default
sovereign operating system vibey supports". The runnable image is Debian bookworm
(`deploy/docker/Dockerfile:27`, `uv:0.9-python3.12-bookworm-slim` build stage; `:157`,
`python:3.12-slim-bookworm` runtime). Whether OCI images are exempt from 8.h is **the
operator's ruling** (`gap-ops-canon-rulings` item 6; `issue-audit/gaps.md` F6). This lane runs
only if the ruling is "an Arch variant". **If the ruling is "images are exempt", stop and
report BLOCKED.** The lane is then closed by the ruling and not implemented.

## Required behaviour
1. New `deploy/docker/Dockerfile.arch`, with the same two stages and the same promises as the
   Debian file. The build stage is `FROM archlinux:base-devel AS build`, installing
   `git ca-certificates curl uv` with `pacman -Syu --noconfirm --needed` and then running the
   same `uv sync --frozen --no-dev --extra operator --extra skills`, with Python 3.12 through
   `uv python install 3.12` and `UV_PYTHON=3.12`. The runtime stage is `FROM archlinux:base`,
   copying the resolved virtual environment and the uv-managed Python.
   - It keeps every claim the Debian file makes, and each claim becomes an `Image contract`
     step: the entrypoint runs, it runs as non-root uid 10001, there is no compiler, uv, pip,
     node or npm in the runtime, migrations ship, `codex` runs at the pinned build, and every
     console script is on PATH.
   - The runtime stage must remove pacman's cache
     (`pacman -Scc --noconfirm && rm -rf /var/cache/pacman/pkg/*`) and must not install
     `base-devel`.
   - Copy the Debian file's comments where the reason is the same (tini as PID 1, the codex
     musl build), and say where Arch differs.
2. `ci.yml`'s `image` job (`:730-854`) gains a second build, `Build amd64 (Arch Linux)`, from
   `deploy/docker/Dockerfile.arch` with tag `vibey:ci-arch`. Its contract steps are duplicated
   with the image tag `vibey:ci-arch` and names suffixed ` (Arch Linux)`. arm64 follows only if
   `archlinux` publishes an arm64 base; record the answer in the Dockerfile's header comment
   either way.
3. Extend the existing image meta-test, if there is one (`grep -rln "Image contract" tests/meta`),
   or create `tests/meta/test_image_arch.py`. For every `Image contract - X` step there must be
   an `Image contract - X (Arch Linux)` step.

## Where to change
- New `deploy/docker/Dockerfile.arch`.
- `.github/workflows/ci.yml`, the `image` job only (edit_file).
- The image meta-test named in *Required behaviour* item 3: the existing one if
  `grep -rln "Image contract" tests/meta` finds it, otherwise a new
  `tests/meta/test_image_arch.py`.

## Acceptance criteria
- [ ] The meta-test passes, and fails when an Arch contract step is removed.
- [ ] Locally, if Docker is available: `docker build -f deploy/docker/Dockerfile.arch -t vibey:arch .`
      builds, and `docker run --rm vibey:arch --version` prints `vibey …`. Otherwise the reviewer
      records the first CI run.
- [ ] The ruling that authorised the lane is quoted in the commit body.

## Tests to write first (TDD)
- `test_every_image_contract_has_an_arch_twin`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Publishing (`gap-release-image-publish`), the chart's image choice, and docs.

Commit as `build(image): an Arch Linux image variant`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
