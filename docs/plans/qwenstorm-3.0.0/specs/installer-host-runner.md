## Title
feat(install): one host package runner for pacman, the AUR and Homebrew, with sudo handled once

## Why
Each local installer re-implements host detection and package commands.
`PostgresLocalService` has `_package_manager`, `_privileged` and `_run_step`
(src/vibey/infrastructure/postgres.py:304-388), and R33 (#380) would copy them for RabbitMQ.
Neither knows pacman, the package manager of the sovereign default OS. The operator's
standard (2026-09-22) requires `vibey install` to install everything on Arch Linux and macOS.
It must use pacman or an AUR helper on Arch and Homebrew on macOS, and it must never pipe a
remote script into a shell.

This lane adds the one runner that turns a catalogue `PackageSpec` (lane installer-catalogue,
`src/vibey/domain/local_stack.py`) into idempotent package commands. Substitution happens at
the declared seam, `CommandExecutorInterface`, never by patching imports (sub-doctrine 9.b,
doctrines.md:258).

## Required behaviour
1. `src/vibey/infrastructure/host_packages.py` declares the following.
   - `CommandResult(returncode: int, stdout: str = "", stderr: str = "")`, a frozen dataclass.
   - `StepOutcome(ok: bool, changed: bool, detail: str, commands: tuple[tuple[str, ...], ...] = ())`,
     a frozen dataclass.
   - `HOMEBREW_REQUIRED: Final`, set to exactly:
     `"Homebrew is required on macOS and is not on PATH: install it with the signed .pkg from https://github.com/Homebrew/brew/releases/latest (vibey never pipes a remote script into a shell), then re-run `vibey install`"`.
   - `class SubprocessCommandExecutor`:
     - `run(argv, *, timeout: float = 600.0) -> CommandResult` calls
       `subprocess.run(argv, capture_output=True, text=True, check=False, timeout=timeout)`.
       It never uses `shell=True`. `FileNotFoundError` returns returncode 127, another
       `OSError` returns 1, and `TimeoutExpired` returns 124, each with the error text in
       `stderr`. Copy the bandit `# nosec` comments from postgres.py:19 and :118.
     - `which(name) -> str | None` is `shutil.which`.
   - `class HostPackageRunner`:
     - Constructor: `__init__(self, executor, *, platform: str, os_release: str, effective_uid: int, user: str)`.
     - `@classmethod for_this_host(cls, executor, *, os_release_path: Path = Path("/etc/os-release"), environ: Mapping[str, str] | None = None)`.
       It reads the following:
       - `sys.platform`;
       - the os-release text, or `""` when the file is missing;
       - `os.geteuid()`;
       - the user: `environ["SUDO_USER"]` when set, otherwise `getpass.getuser()`. The
         `environ` default is `os.environ`.
     - `host() -> HostOs | None`:
       - `"darwin"` returns MACOS;
       - a platform starting `"linux"` returns ARCH when the os-release `ID`, or any word of
         `ID_LIKE`, is `arch` (with surrounding quotes removed). This also covers EndeavourOS
         and Manjaro;
       - anything else returns None.
     - `host_label() -> str`:
       - "macOS" for MACOS;
       - the os-release `PRETTY_NAME`, or "Arch Linux", for ARCH;
       - otherwise `PRETTY_NAME` or the platform string.
     - `user` is a property that returns the login user.
     - `precondition() -> str | None` returns None when the host can install. Otherwise it
       returns one line saying what is missing:
       - MACOS as root: "run `vibey install` as your own user: Homebrew refuses to run as root";
       - MACOS with no `brew` on PATH: `HOMEBREW_REQUIRED`;
       - ARCH with no `pacman`: "pacman is not on PATH; this does not look like a working
         Arch Linux install";
       - ARCH, not root, and no `sudo`: "vibey install needs sudo on Arch Linux: pacman and
         systemctl run as root";
       - a None host: f"{host_label()} is not a default OS for `vibey install` (Arch Linux, macOS)".
     - `privileged(argv) -> tuple[str, ...] | None` returns:
       - `argv` when the effective uid is 0;
       - `("sudo", *argv)` when `sudo` is on PATH;
       - otherwise None.
     - `is_installed(spec: PackageSpec) -> bool` returns True in these cases:
       - any of `spec.binaries` is on PATH;
       - the source is NONE;
       - PACMAN or AUR, and `("pacman", "-Q", name)` returns 0 for every name;
       - BREW_FORMULA, and `("brew", "list", "--formula", "--versions", name)` returns 0 for
         every name;
       - BREW_CASK, and `("brew", "list", "--cask", "--versions", name)` returns 0 for every
         name.
       Query commands use `timeout=30.0`.
     - `ensure(spec: PackageSpec) -> StepOutcome` is idempotent:
       - Already installed: returns `StepOutcome(True, False, "<names> already installed")`.
       - PACMAN: runs `privileged(("pacman", "-S", "--needed", "--noconfirm", *names))`. With
         no privilege it returns `StepOutcome(False, False, "pacman needs root or sudo to install <names>")`.
       - AUR:
         - it uses the first of `paru` or `yay` on PATH and runs
           `(helper, "-S", "--needed", "--noconfirm", *names)` as the user, never through sudo;
         - with no helper it returns: "installing <names> needs an AUR helper (paru or yay);
           install one, or build https://aur.archlinux.org/packages/<first name> with makepkg";
         - as root it returns: "AUR helpers refuse to run as root; run `vibey install` as your
           own user".
       - BREW_FORMULA: runs `("brew", "install", *names)`. BREW_CASK runs
         `("brew", "install", "--cask", *names)`. With no brew it returns `HOMEBREW_REQUIRED`.
         As root it returns the root line from `precondition`.
       - NONE: returns `StepOutcome(True, False, "nothing to install")`.
       - Exit 0: returns `StepOutcome(True, True, "installed <names> with <tool>", (argv,))`.
       - Any other exit: returns `StepOutcome(False, True, "<tool> could not install <names>: <last non-empty stderr line, or 'exit N'>", (argv,))`.
       - Install commands use `timeout=1800.0`.
2. `src/vibey/infrastructure/interfaces/host_packages_interface.py` declares two
   `@runtime_checkable` Protocols:
   - `CommandExecutorInterface`, with `run` and `which`;
   - `HostPackageRunnerInterface`, with `host`, `host_label`, `user`, `precondition`,
     `privileged`, `is_installed` and `ensure`.

   Import `CommandResult`, `StepOutcome`, `HostOs` and `PackageSpec` under `TYPE_CHECKING`, as
   `src/vibey/infrastructure/interfaces/postgres_interface.py:6-9` does.
3. `tests/fakes/host.py` declares two shared fakes that later lanes import:
   - `FakeCommandExecutor(*, on_path=(), responses=None, default=CommandResult(0))`:
     - `which(name)` returns `f"/usr/bin/{name}"` when the name is in `on_path`, else None;
     - `run(argv, *, timeout=600.0)` appends `argv` to `self.calls`. It answers from
       `responses`, a dict keyed by an argv prefix; the longest matching prefix wins. A value
       is a `CommandResult`, or a list of them consumed one per call, with the last one
       repeating. Anything else gets `default`.
   - `FakeTime`: `monotonic()` returns `self.now`, and `sleep(seconds)` adds to `self.now` and
     appends to `self.sleeps`.

## Where to change
- New files:
  - `src/vibey/infrastructure/host_packages.py`
  - `src/vibey/infrastructure/interfaces/host_packages_interface.py`
  - `tests/fakes/host.py`
  - `tests/infrastructure/test_host_packages.py`
- Copy line 1, the provenance comment, from `src/vibey/infrastructure/postgres.py` into every
  new file.
- Copy the subprocess pattern from postgres.py:115-131.
- Copy the `_privileged` logic from postgres.py:374-379.
- Do not edit `postgres.py`.

## Acceptance criteria
- [ ] Arch detection:
  - `ID=arch` gives ARCH;
  - `ID=endeavouros` with `ID_LIKE=arch` gives ARCH;
  - `ID=ubuntu` gives None;
  - `darwin` gives MACOS.
- [ ] A second `ensure` of an installed package runs no install command. The fake's calls list
      holds only the query.
- [ ] Non-root pacman goes through `sudo`, and root pacman does not.
- [ ] With no sudo, pacman fails with the privilege line and runs nothing.
- [ ] AUR installs run as the user through paru, falling back to yay. With neither helper, or
      as root, the lane fails with the exact lines above.
- [ ] Brew formula and cask argv are exact. With no brew, the result is `HOMEBREW_REQUIRED`.
      Nothing ever runs `curl`, `wget` or a shell.
- [ ] `for_this_host` reads a temporary os-release file, handles a missing path, and prefers
      `SUDO_USER`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/host_packages.py`.

## Tests to write first (TDD)
All tests go in `tests/infrastructure/test_host_packages.py` and use `FakeCommandExecutor`:
- `test_detects_arch_and_its_derivatives_from_os_release`
- `test_detects_macos_and_rejects_other_hosts`
- `test_host_label_prefers_pretty_name`
- `test_precondition_names_what_is_missing` (parametrized over the five lines)
- `test_privileged_uses_sudo_only_when_not_root`
- `test_is_installed_accepts_a_binary_on_path_or_a_package_query`
- `test_ensure_is_idempotent_for_an_installed_package`
- `test_ensure_installs_with_pacman_through_sudo`
- `test_ensure_reports_pacman_without_privilege`
- `test_ensure_installs_aur_packages_as_the_user_with_paru_or_yay`
- `test_ensure_refuses_aur_as_root_and_without_a_helper`
- `test_ensure_installs_brew_formulas_and_casks`
- `test_ensure_requires_homebrew_and_refuses_root_on_macos`
- `test_ensure_reports_a_failed_install_with_the_last_stderr_line`
- `test_subprocess_executor_maps_missing_binary_oserror_and_timeout`: use a real
  `SubprocessCommandExecutor`. Run `("python3", "-c", "print(1)")`, a missing binary, and
  `("python3", "-c", "import time; time.sleep(5)")` with `timeout=0.1`.
- `test_for_this_host_reads_os_release_and_sudo_user` (uses `tmp_path`).
- `test_runner_and_executor_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_host_packages.py tests/application/test_interfaces_convention.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure
    uv run coverage report --include='src/vibey/infrastructure/host_packages.py' --fail-under=100

## Out of scope
- Starting services, readiness probes and post-install steps: that is lane
  installer-service-runner.
- Changing `PostgresLocalService`.
- The CLI.
- Docs and CHANGELOG.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
