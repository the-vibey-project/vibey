<!-- split of #331: child 5 of 5; audit: issue-audit/updates/331.md -->

## Title
feat(install): the OpenStack CLI and its Heat plugin are an opt-in dependency on Arch Linux and macOS

## Why
`vibey worker --cloud cli` with `[deploy].target = "openstack"` (the sovereign cloud default,
sub-doctrine 8.b, `src/vibey_tools/gh/docs/doctrines.md:136-137`) drives `openstack stack create|update|show|delete`
(lane `split-331-2-openstack-cli-adapter`), but nothing installs the `openstack` CLI, and
`openstack stack` exists only when the Heat client plugin is installed beside the base client. The
operator's standard (2026-09-22) is that `vibey install` installs everything a developer needs on
the default operating systems, and 8.h (`doctrines.md:326-333`) makes those Arch Linux (sovereign)
and macOS (paid), with every change proven on both. The dependency list is declared data in the
catalogue (`src/vibey/domain/local_stack.py`, lane `installer-catalogue`; 12.c, `doctrines.md:455`),
installed by `HostPackageRunner` from a package manager and never by a piped remote script. The
entry is opt-in because deployment is an opt-in stage set, and the package names are a claim that
must carry its source and date (10.f, `doctrines.md:419`).

## Required behaviour
1. `CATALOGUE_ENTRIES` in `src/vibey/domain/local_stack.py` gains one entry, appended at the end of
   the tuple (after whatever entry is last when you start):
   - key `"openstack-cli"`, title `"OpenStack CLI with the Heat plugin"`, group `"cloud"`,
     default `False`, installer `InstallerKind.PACKAGE`, no `requires`;
   - arch: `HostRecipe(PackageSpec(PackageSource.PACMAN, ("python-openstackclient", "python-heatclient"), ()))`;
   - macos: `HostRecipe(PackageSpec(PackageSource.BREW_FORMULA, ("openstackclient",), ("openstack",)))`;
   - no service, no probe, no post-install step, no hint on either OS;
   - `note`: the dated package evidence of Required behaviour 4.
2. Why the binaries differ. `HostPackageRunner.is_installed` counts a package as installed when any
   declared binary is on `PATH` (lane `installer-host-runner`). On Arch the base client and the Heat
   plugin are separate packages, so an `openstack` already on `PATH` does not prove the plugin is
   there: the Arch recipe declares no binary, and `pacman -Q` must answer for both names. The
   Homebrew formula bundles the Heat plugin, so `openstack` on `PATH` is the binary probe there.
3. Selection: `resolve(host)` includes neither this entry nor the `cloud` group on either OS.
   `resolve(host, extra=("cloud",))` and `resolve(host, extra=("openstack-cli",))` include it on
   both. Once lane `installer-cli` has landed, `vibey install --with cloud` selects it with no change
   here, because `--with` passes names to `LocalStackCatalogue.resolve(extra=...)`.
4. **Package-name evidence, read on the day (10.f).** Before writing the entry, re-read the names and
   record what you read, with the date (`date +%F`), in the entry's `note`. How to read them:
   - Arch official repositories. On an Arch host: `pacman -Si python-openstackclient python-heatclient`.
     On any other host (the storm runs on macOS), read the same data from archlinux.org:
     `curl -fsS "https://archlinux.org/packages/search/json/?name=python-openstackclient"` and the
     same with `name=python-heatclient`. Each must return one result whose `repo` is `extra` or
     `core`; record `pkgver-pkgrel`. Confirm the binary with
     `curl -fsS "https://archlinux.org/packages/extra/any/python-openstackclient/files/json/"`,
     which must list `usr/bin/openstack`.
   - If either name has no official result, check the AUR the way `paru -Si` or `yay -Si` does:
     `curl -fsS "https://aur.archlinux.org/rpc/v5/info?arg[]=<name>"`. If a name exists only in the
     AUR, **stop and report it in your verdict**: one `PackageSpec` has one source, so an entry that
     needs both pacman and the AUR is a different change, not this lane.
   - Homebrew. On macOS: `brew info --json=v2 openstackclient` (or
     `curl -fsS "https://formulae.brew.sh/api/formula/openstackclient.json"`); record
     `versions.stable`. Confirm the formula ships the `stack` commands:
     `brew cat openstackclient | grep -n -E 'python-heatclient|stack list'` (or
     `curl -fsS "https://raw.githubusercontent.com/Homebrew/homebrew-core/HEAD/Formula/o/openstackclient.rb" | grep -n -E 'python-heatclient|stack list'`)
     must show the `resource "python-heatclient"` block and the formula test's `"stack list"`.
   - If a name differs from the table below in any other way (renamed, or no longer shipping
     `openstack`), stop and report it; do not guess a name.
   - If you cannot reach the network at all, keep the spec writer's reading below, say in the note
     that it was "read 2026-09-22 by the spec writer; not re-read by the lane", and say so in your
     verdict. Never write a date you did not read on.

   The spec writer's reading, 2026-09-22, from archlinux.org, aur.archlinux.org and
   formulae.brew.sh / homebrew-core:

   | OS | source | package | version read | what it proves |
   |---|---|---|---|---|
   | Arch | `extra` (official) | `python-openstackclient` | 10.3.0-1 | ships `/usr/bin/openstack` |
   | Arch | `extra` (official) | `python-heatclient` | 5.3.0-1 | the Heat plugin; depends on `python-openstackclient` |
   | Arch | AUR | neither name | (no result) | both are official, so PACMAN, not AUR |
   | macOS | Homebrew formula | `openstackclient` | 10.3.0 (Apache-2.0) | bundles `resource "python-heatclient"` (5.3.0); its test runs `openstack stack list` |

   The note, with your date and versions substituted if they differ, reads:
   ``"opt-in: `vibey worker --cloud cli` drives `openstack stack` for [deploy].target = \"openstack\" (8.b), and `openstack stack` needs the Heat plugin beside the base client. Read 2026-09-22 (archlinux.org, formulae.brew.sh): Arch extra/python-openstackclient 10.3.0-1 (ships /usr/bin/openstack) and extra/python-heatclient 5.3.0-1, both official; Homebrew formula openstackclient 10.3.0 bundles python-heatclient and its test runs `openstack stack list`. Arch declares no binary: an `openstack` on PATH does not prove the Heat plugin is installed."``
   Write it as adjacent string literals inside parentheses, one sentence or clause per line.
5. The Azure CLI is not added: Azure is a declared-only paid cloud (8.b), and its tool is not this
   lane's.
6. The module stays pure (`dataclasses`, `enum`, `typing` only); `tests/domain/test_domain_purity.py`
   and the catalogue's existing guard tests (no recipe runs `curl`, `wget` or a shell; every entry
   whose source is not NONE names a package) still pass.

## Where to change
Line numbers are not given: lanes `installer-catalogue`, `installer-toolchain` and others write
`local_stack.py` before this lane, so find the end of `CATALOGUE_ENTRIES` by reading the file.
- `src/vibey/domain/local_stack.py`: append the entry with `edit_file` (the file is long; never
  `write_file` it). Write it in the same style (keyword or positional) as the entries before it.
- `tests/domain/test_local_stack.py`: append the four domain tests below.
- `tests/infrastructure/test_package_dependency.py`: append the two end-to-end tests below, which
  prove the entry on both default operating systems (8.h). Copy the shape of the docker tests lane
  `installer-container-runtime` added there (`test_docker_on_arch_installs_the_engine_and_waits_for_docker_info`):
  the real `CataloguePackageInstaller`, `HostPackageRunner` and `HostServiceRunner` over
  `FakeCommandExecutor` and `FakeTime` from `tests/fakes/host.py`.

Only these three files change: one source file (the catalogue is data in one module, whose
interface lane `installer-catalogue` already declared) and two test files, the second because 8.h
requires the install commands proven on Arch and macOS, not only the data.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_local_stack.py tests/infrastructure/test_package_dependency.py tests/domain/test_domain_purity.py`
      passes.
- [ ] `uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/domain/test_local_stack.py tests/infrastructure/test_package_dependency.py`
      passes with PostgreSQL stopped.
- [ ] Neither OS's default resolution contains `openstack-cli`; `extra=("cloud",)` adds it on both.
- [ ] The Arch recipe installs `python-openstackclient` and `python-heatclient` with pacman and
      declares no binary; the macOS recipe installs the `openstackclient` formula and probes
      `openstack`.
- [ ] The entry's `note` names both Arch packages and the formula, says the formula bundles the Heat
      plugin, and carries the date the names were read (`YYYY-MM-DD`).
- [ ] If `tests/cli/test_local_install.py` exists (lane `installer-cli`),
      `uv run pytest -q -p no:cacheprovider tests/cli/test_local_install.py` still passes.
- [ ] `git diff --stat` names only `src/vibey/domain/local_stack.py`, `tests/domain/test_local_stack.py` and `tests/infrastructure/test_package_dependency.py`.
- [ ] `uv run coverage report --include='src/vibey/domain/*' --fail-under=100` passes after the
      coverage run.

## Tests to write first (TDD)
Append to `tests/domain/test_local_stack.py` (never assert the complete list of keys; later lanes
append entries):
- `test_openstack_cli_is_opt_in_in_the_cloud_group`: `spec = LocalStackCatalogue().get("openstack-cli")`
  has `group == "cloud"`, `default is False`, `installer is InstallerKind.PACKAGE`, `requires == ()`;
  for each of `HostOs.ARCH` and `HostOs.MACOS`, `"openstack-cli"` is not among the keys of
  `resolve(host)` and is among the keys of `resolve(host, extra=("cloud",))` and of
  `resolve(host, extra=("openstack-cli",))`.
- `test_openstack_cli_brings_the_heat_plugin_on_both_oses`: `spec.recipe(HostOs.ARCH).package ==
  PackageSpec(PackageSource.PACMAN, ("python-openstackclient", "python-heatclient"), ())`;
  `spec.recipe(HostOs.MACOS).package == PackageSpec(PackageSource.BREW_FORMULA, ("openstackclient",), ("openstack",))`;
  on both recipes `service is None`, `probe is None`, `post_install == ()` and `hint == ""`.
- `test_openstack_cli_note_records_dated_package_evidence`: the note contains
  `"python-openstackclient"`, `"python-heatclient"`, `"openstackclient"` and `"openstack stack"`, and
  `re.search(r"\b20\d\d-\d\d-\d\d\b", spec.note)` matches.
- `test_the_azure_cli_is_not_a_catalogue_entry`: no entry's key is `"azure-cli"` or `"az"`, and no
  recipe on either OS names a package `"azure-cli"` (8.b: Azure is declared-only).

Append to `tests/infrastructure/test_package_dependency.py`:
- `test_openstack_cli_on_arch_installs_the_client_and_the_heat_plugin_with_pacman`: a
  `HostPackageRunner(executor, platform="linux", os_release="ID=arch\n", effective_uid=1000, user="alice")`
  over `FakeCommandExecutor(on_path=("pacman", "sudo"), responses={("pacman", "-Q"): CommandResult(1)})`,
  and `CataloguePackageInstaller(LocalStackCatalogue().get("openstack-cli"), HostOs.ARCH, packages, services)`.
  `install()` returns READY with `changed` True, and `executor.calls` contains
  `("sudo", "pacman", "-S", "--needed", "--noconfirm", "python-openstackclient", "python-heatclient")`.
  No call starts with `curl`, `wget`, `sh`, `bash` or `zsh`.
- `test_openstack_cli_on_macos_installs_the_formula`: `platform="darwin"`, `os_release=""`,
  `on_path=("brew",)`, responses `{("brew", "list", "--formula"): CommandResult(1)}`; `install()`
  returns READY and `executor.calls` contains `("brew", "install", "openstackclient")`.
Build `services` as the docker tests do: `clock = FakeTime()` and
`HostServiceRunner(packages, executor, sleep=clock.sleep, monotonic=clock.monotonic)`.
`CommandResult` here is the one in `vibey.infrastructure.host_packages`, and
`LocalStackCatalogue`/`HostOs` come from `vibey.domain.local_stack`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure/test_package_dependency.py
uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/domain/test_local_stack.py tests/infrastructure/test_package_dependency.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
```
One coverage run at a time. Until lane `fakes-harness-decouple` lands, `tests/conftest.py:146-156`
connects to PostgreSQL at session start, so every run except the `--noconftest` one needs
PostgreSQL 17 reachable. If `ruff check` reports only import order (`I001`), run
`uv run ruff check --select I --fix` on the files you changed, then `uv run ruff format` on them.

## Out of scope
- The Azure CLI, AWS and GCP CLIs (paid, declared-only clouds).
- `HostPackageRunner`, `CataloguePackageInstaller`, the CLI (`installer-cli`) and doctor
  (`installer-doctor`): no code outside the catalogue changes.
- OpenStack credentials (`clouds.yaml`), which the operator provides; the adapter and the worker
  (lanes `split-331-2` to `split-331-4`).
- A `ProbeSpec` that runs `openstack`: the Homebrew formula's own test expects
  `openstack stack list` to exit 1 without credentials even with the plugin installed, so that exit
  code does not prove the plugin; the package queries do.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, README.md or the skill
  trees. Do not push, open PRs, or change git remotes. Commit locally as
  `feat(install): the OpenStack CLI and its Heat plugin are an opt-in dependency on Arch Linux and macOS`;
  the hooks add the `Made-With:` trailer.

## Standing constraints
- 8.h: every recipe has an Arch Linux and a macOS form, and both are proven by a test.
- 10.f: the note states what was read, where, and on which date; a claim not re-read is labelled so.
- 12.c: package names are data in the catalogue, never literals in code elsewhere.
- Never a piped remote script: installation is pacman or Homebrew through `HostPackageRunner`.
- Tests substitute only at declared seams (the `FakeCommandExecutor` handed to the runner's
  constructor); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock` (9.b).
- Change existing files with `edit_file`, append tests, and never rewrite an existing file
  (EDITING-RULES.md).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.

**Depends on:** installer-catalogue, installer-toolchain
- installer-catalogue: `src/vibey/domain/local_stack.py` (`CATALOGUE_ENTRIES`, `DependencySpec`,
  `HostRecipe`, `PackageSpec`, `PackageSource`, `InstallerKind`, `HostOs`, `LocalStackCatalogue`)
  and `tests/domain/test_local_stack.py` with its guard tests.
- installer-toolchain: the toolchain entries this lane appends after, and (through
  `installer-container-runtime`, `installer-package-dependency`, `installer-host-runner` and
  `installer-service-runner`) `CataloguePackageInstaller`, `HostPackageRunner`,
  `HostServiceRunner`, `tests/fakes/host.py` and the docker end-to-end tests to copy.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
