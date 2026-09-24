## Title
feat(gh): render the sovereign runner's launchd and systemd units from `[runners]`, and detect drift

## Why
The runner's units exist only as hand-written launchd plists on the operator's Mac. There is no
systemd unit for Arch Linux, which is 8.h's sovereign default OS
(`src/vibey_tools/gh/docs/doctrines.md:326`), and nothing checks installed units against
anything (`issue-audit/gaps.md` L3). 12.c (`:455`) asks for declared state "reconciled from the
file". `gap-runners-declared-1` added `RunnersConfig`. This lane renders units from it and
compares installed units with a fresh render.

## Required behaviour
1. New templates, which ship inside the package; hatch includes package files:
   - `src/vibey_tools/gh/vibey_gh/templates/runners/launchd-runner.plist`: the shape of the
     operator's `com.adammatthewsteinberger.vibey-runner-vibey.plist`.
     - `Label` is `__UNIT__`.
     - `ProgramArguments` is `[__INSTALL_DIR__/vibey-runner.sh]` and `WorkingDirectory` is `__INSTALL_DIR__`.
     - `EnvironmentVariables` holds `VIBEY_REPO_URL=__REPO_URL__`, `VIBEY_RUNNER_LABEL=__LABEL__`,
       `VIBEY_RUNNER_IMAGE=__IMAGE__`, `VIBEY_OLLAMA_URL=__OLLAMA_URL__`,
       `VIBEY_REQUIRE_AC=__REQUIRE_AC__` (`1` or `0`), `VIBEY_RUNNER_UNIT_PREFIX=__PREFIX__`,
       and `PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`.
     - `RunAtLoad` and `KeepAlive` are true, and `ThrottleInterval` is `__THROTTLE__`.
     - Logs go to `~/Library/Logs/__UNIT__.log`.
     - Keep the operator plist's three explanatory comments (user agent not daemon, KeepAlive,
       ThrottleInterval) in XML comments.
   - `launchd-authority.plist`: the same shape for `__INSTALL_DIR__/vibey-local-authority.sh`,
     `Label` `__PREFIX__.local-authority`.
   - `systemd-runner.service`, a user unit:
     - `[Unit] Description=vibey sovereign review runner (__LABEL__)`;
     - `[Service] ExecStart=__INSTALL_DIR__/vibey-runner.sh`, `WorkingDirectory=__INSTALL_DIR__`,
       one `Environment=` line per variable above except `PATH`, `Restart=always`,
       `RestartSec=__THROTTLE__`;
     - `[Install] WantedBy=default.target`.
   - `systemd-authority.service`: likewise for the authority script.
   - Paths use the literal text `__INSTALL_DIR__`, which the renderer expands, turning `~` into the home it is given.
2. New module `src/vibey_tools/gh/vibey_gh/runners.py` with the provenance header:
   - `@dataclass(frozen=True) class RenderedUnit`: `filename: str`, `text: str`.
   - `class RunnerUnits` with `__init__(self, *, home: Path, templates: Path | None = None)`
     (the default is the package's `templates/runners`). It has two methods:
     - `render(self, target: str, runners: RunnersConfig, fallback: PrAutomationFallbackConfig, platform: PlatformConfig) -> tuple[tuple[RenderedUnit, ...], str]`:
       - `target` is `"launchd"` or `"systemd"`; anything else returns `((), "unknown runner target <t>; expected launchd or systemd")`;
       - an empty `registration_url` returns `((), <its problem>)`;
       - the unit name is `f"{runners.unit_prefix}-{fallback.runner_label}"`. launchd filenames
         are `<Label>.plist`; systemd filenames are `<name>.service` and `<prefix>-local-authority.service`;
       - placeholders are replaced by exact string substitution;
       - the result is sorted by filename.
     - `check(self, target: str, directory: Path, runners, fallback, platform) -> list[str]`:
       for each rendered unit, `"missing: <path>"` when absent, or `"drift: <path>"` when the
       file's text differs. An empty list means in sync, and render problems are returned as-is.
   - `__all__`.
3. New interface `src/vibey_tools/gh/vibey_gh/interfaces/runners_interface.py`:
   `RunnerUnitsInterface(Protocol)` with `render` and `check`. Export it from the package's
   `interfaces/__init__.py` if that module re-exports.
4. File-system access is limited to reading the templates and the directory given, so tests use `tmp_path` and no patching.

## Where to change
- New: the four templates, `vibey_gh/runners.py` and `vibey_gh/interfaces/runners_interface.py`.
- New test file `src/vibey_tools/gh/test/test_runners.py`.

## Acceptance criteria
- [ ] Rendering `launchd` with the root config (`-1`) gives
      `com.adammatthewsteinberger.vibey-runner-vibey-local-vibey.plist` and
      `com.adammatthewsteinberger.vibey-runner.local-authority.plist`. The runner plist
      carries `VIBEY_REPO_URL` = `https://github.com/the-vibey-project/vibey`, and
      `plistlib.loads` parses both.
- [ ] Rendering `systemd` gives two `.service` files. `configparser` with `strict=False`
      reads `ExecStart` under the expanded home.
- [ ] An unknown target and an underivable URL return the exact problem texts, with no units.
- [ ] `check` reports `missing:` and `drift:` exactly, and `[]` after the rendered files are written.
- [ ] No `__[A-Z_]+__` placeholder survives in any rendered text.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_runners.py`:
- `test_launchd_units_render_from_config`
- `test_systemd_units_render_from_config`
- `test_unknown_target_and_missing_url_are_refused`
- `test_check_reports_missing_and_drift_then_passes`
- `test_no_placeholder_survives_rendering` (parametrized over both targets)
- `test_runner_units_satisfy_their_interface`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The command line (`-3`); installing units into `~/Library/LaunchAgents` or `~/.config/systemd/user` (the operator runs the command).
- The heartbeat logic (`gap-heartbeat-registered`), and docs.

Commit as `feat(gh): render the sovereign runner's units from [runners]`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
