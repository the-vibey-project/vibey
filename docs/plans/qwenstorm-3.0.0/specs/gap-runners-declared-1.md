## Title
feat(gh): a declared `[runners]` table names where the sovereign review runner registers and how its units are named

## Why
The sovereign review runner's registration URL, unit names, image and model endpoint live
only in the operator's launchd plists. When the repository moved to
`the-vibey-project/vibey`, those plists kept `VIBEY_REPO_URL=https://github.com/adammatthewsteinberger/<repo>`,
and registration has returned 404 since 2026-08-31 (`issue-audit/gaps.md` L2, L3).
12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) requires that state to be declared and
reconciled from the tree. This lane adds the configuration table. `gap-runners-declared-2`
renders units from it, and `-3` adds the command.

The runner's **label** is already declared, as `[pr_automation.fallback] runner_label`
(`vibey_gh/config.py:480-535`; `.vibey-gh.toml:218-224` sets `vibey-local-vibey`). It is
reused here and never declared twice (10.e).

## Required behaviour
1. `src/vibey_tools/gh/vibey_gh/config.py` gains
   `@dataclass(frozen=True) class RunnersConfig`, placed after `PrAutomationConfig`. Each
   field has a comment giving its reason:
   - `repo_url: str = ""`: empty means derive from `[platform]`, as `https://github.com/{platform.repository}` when `kind == "github"`.
   - `unit_prefix: str = "org.vibey.runner"`: the launchd Label and systemd unit name prefix.
   - `install_dir: str = "~/.local/share/vibey-runner"`: where `deploy/runners/*` is installed on the host.
   - `image: str = "vibey-runner:latest"`
   - `ollama_url: str = "http://127.0.0.1:11434"`
   - `require_ac: bool = True`
   - `throttle_seconds: int = 120`

   `__post_init__` raises `ValueError` with the `runners.<field>` prefix in these cases:
   - `unit_prefix` does not match `^[A-Za-z0-9][A-Za-z0-9.-]*$`;
   - `repo_url` is non-empty and does not start with `https://`;
   - `throttle_seconds` is not between 10 and 3600;
   - `image` or `install_dir` is empty.
2. The method `registration_url(self, platform: PlatformConfig) -> tuple[str, str]` returns
   `(url, problem)`:
   - `repo_url` when it is set;
   - otherwise, when `platform.kind == "github"` and `platform.repository` is set,
     `f"https://github.com/{platform.repository}"`;
   - otherwise `("", "runners.repo_url is empty and [platform] names no GitHub repository to derive it from")`.
3. `GhConfig` gains `runners: RunnersConfig = RunnersConfig()`. `load_config` parses a
   `[runners]` table, copying the `fallback=PrAutomationFallbackConfig(...)` pattern at
   `:1752-1762`. `_check_unknown_keys` in `vibey_gh/doctor.py:104-144` must accept the new
   table: follow how it discovers dataclass fields (`_fields`, `:64`).
4. The root `.vibey-gh.toml` gains, after `[pr_automation.fallback]` (`:218-224`):
   ```toml
   [runners]
   # The sovereign review runner this repository registers (12.c): rendered into launchd or
   # systemd units by `vibey-gh runners render`. The label is [pr_automation.fallback] runner_label.
   repo_url = "https://github.com/the-vibey-project/vibey"
   unit_prefix = "com.adammatthewsteinberger.vibey-runner"
   ```
5. Because the tenant's `docs/configuration.md` belongs to the docs wave, nothing documents the
   keys yet. Say so in the commit body.

## Where to change
- `src/vibey_tools/gh/vibey_gh/config.py` (large; edit_file only).
- `src/vibey_tools/gh/vibey_gh/doctor.py`, only if the unknown-key check needs the new table registered.
- `.vibey-gh.toml` (root).
- Tests: append to `src/vibey_tools/gh/test/test_config.py`.
- There is no new interface: `RunnersConfig` is a frozen configuration value, like its
  neighbours `PrAutomationFallbackConfig` and `PlatformConfig`.

## Acceptance criteria
- [ ] `load_config()` at the repository root gives
      `runners.registration_url(platform) == ("https://github.com/the-vibey-project/vibey", "")`.
- [ ] With no `repo_url` and `[platform] kind = "github", repository = "o/r"`, the URL is
      `https://github.com/o/r`. With `kind = "forgejo"` and no URL, the problem text is exact.
- [ ] Each invalid field raises `ValueError` naming `runners.<field>`.
- [ ] `vibey-gh doctor` reports no unknown key for `[runners]`.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_config.py`:
- `test_runners_table_defaults`
- `test_runners_registration_url_is_declared_or_derived` (parametrized)
- `test_runners_invalid_fields_are_refused` (parametrized)
- `test_repository_declares_its_runner_registration`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Rendering units (`-2`), the CLI (`-3`), the heartbeat (`gap-heartbeat-registered`), and docs.

Commit as `feat(gh): declare the sovereign review runner's registration in [runners]`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
