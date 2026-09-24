## Title
feat(install): the local stack includes a container runtime: Docker Desktop on macOS, the Docker engine from pacman on Arch

## Why
vibey runs gates and builds in OCI containers (`src/vibey/infrastructure/container/runtime.py:11-30`
looks for `docker`, then `podman`). The cluster path and the image contract build images. The
operator requires Docker Desktop on macOS, and requires the installer to wait until `docker
info` answers (2026-09-22).

**Arch Linux: the pacman `docker` engine, not Docker Desktop for Linux.**
- `extra/docker` 29.8.1 and `extra/docker-buildx` 0.37.1 are in Arch's official, signed
  repositories. Moby is Apache-2.0. It runs natively under systemd (`docker.service`), with
  no VM and no account.
- Docker Desktop for Linux exists on Arch only in the AUR (`docker-desktop` 4.92.0, 30 votes,
  read 2026-09-22). It is proprietary under the Docker Subscription Service Agreement, which
  requires a paid subscription for larger companies. It runs a QEMU VM.
- Sub-doctrine 8.a (doctrines.md:88-107) settles comparable options for the freer and more
  sovereign one, so the engine wins on Arch.

**macOS** has no native engine, so it uses the operator's choice: the `docker-desktop` cask.

## Required behaviour
1. Add this entry to `CATALOGUE_ENTRIES` in `src/vibey/domain/local_stack.py`, immediately after
   the `model` entry:
   - key "docker", title "Docker", group "services", default True, installer `PACKAGE`.
   - arch:
     `HostRecipe(PackageSpec(PACMAN, ("docker", "docker-buildx"), ("docker",)), ServiceSpec(SYSTEMD, "docker"), ProbeSpec(("docker", "info"), privileged=True, timeout_seconds=60.0), post_install=(("usermod", "-aG", "docker", "{user}"),), hint="log out and back in once so your user can reach Docker without sudo")`.
   - macos:
     `HostRecipe(PackageSpec(BREW_CASK, ("docker-desktop",), ("docker",)), ServiceSpec(MACOS_APP, "Docker"), ProbeSpec(("docker", "info"), timeout_seconds=180.0, timeout_hint="Docker Desktop opens a window on its first start: accept its service agreement there, then re-run `vibey install --only docker`"))`.
   - note: "Arch: the pacman engine (Apache-2.0, official repositories) over the AUR-only,
     proprietary Docker Desktop for Linux (8.a). macOS: Docker Desktop, the operator's choice,
     2026-09-22."
2. The installer never accepts Docker's agreement on the user's behalf. On macOS it opens the
   app, waits up to 180 s, and otherwise reports the timeout hint.
3. The `docker` group grants root-equivalent access. The post-install step is declared data,
   printed in the report's commands, and runs only through `sudo`.

## Where to change
- `src/vibey/domain/local_stack.py`: insert the entry. Use edit_file.
- `tests/domain/test_local_stack.py`: append tests.
- `tests/infrastructure/test_package_dependency.py`: append one end-to-end test per OS. Each
  uses the real docker entry, `CataloguePackageInstaller`, `HostPackageRunner` and
  `HostServiceRunner` over `FakeCommandExecutor` and `FakeTime`.
- No other file changes.

## Acceptance criteria
- [ ] `resolve(ARCH)` and `resolve(MACOS)` include docker after model.
- [ ] Arch, as user `alice` with sudo: the install, step and start commands, in order, are
      `sudo pacman -S --needed --noconfirm docker docker-buildx`,
      `sudo usermod -aG docker alice`, then `sudo systemctl enable --now docker`. The probe
      is `sudo docker info`, polled until it answers; queries and probes may sit between
      those commands. The result is READY, and the relogin hint is on the recipe.
- [ ] macOS: `brew install --cask docker-desktop`, then `open -g -a Docker`, with `docker info`
      polled using `FakeTime`. When it never answers within 180 s, the result is FAILED and its
      detail contains the agreement hint.
- [ ] A host where `docker info` already answers runs no install command.
- [ ] The existing guard tests (no curl or shell in any recipe) still pass.

## Tests to write first (TDD)
- `tests/domain/test_local_stack.py`:
  - `test_docker_is_a_default_service_on_both_oses`
  - `test_arch_docker_adds_the_user_to_the_docker_group_through_a_declared_step`
- `tests/infrastructure/test_package_dependency.py`:
  - `test_docker_on_arch_installs_the_engine_and_waits_for_docker_info`
  - `test_docker_on_macos_opens_docker_desktop_and_waits`
  - `test_docker_desktop_timeout_names_the_agreement_window`
  - `test_ready_docker_is_left_alone`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure/test_package_dependency.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Podman.
- Rootless Docker.
- Colima, a FOSS macOS alternative recorded in the ADR as considered.
- Changing `OciContainerExecutor`.
- The CLI.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
