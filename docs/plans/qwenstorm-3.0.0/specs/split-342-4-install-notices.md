<!-- split of #342: child 4 of 4; audit: issue-audit/updates/342.md -->

## Title
feat(gh): install notices list secrets through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, with GitHub and GitLab declared-only, and `[platform] kind` defaults to `forgejo`
(`vibey_gh/config.py:288`). `install.installation_notices` (`vibey_gh/install.py:465-487`)
inventories secrets with a raw `gh secret list --json name`, reports `"gh not found; skipping
secret/permission checks"` only when `gh` is missing and stays silent on every other failure,
so `vibey-gh install` (`cli._install`, `cli.py:164-174`) ignores `[platform]` and hides a
listing it could not make. 8.b routes every forge call through `ForgeAdapterInterface`
(`doctrines.md:168-184`), 10.f requires a status that could not be established to be reported
as such, and sub-doctrine 9.b (`doctrines.md:349`: "Substitution happens at the declared seam,
never by patching an import") moves the tests off the faked `subprocess.run` onto the `forge=`
seam, the same seam `_install` already uses for its `resolver`.

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`).

1. `installation_notices` lists secrets through the adapter:
   ```python
   # Module-level (ADR-0016): cli._install calls it by name; the module converges on a
   # class in its own lane.
   def installation_notices(*, forge: ForgeAdapterInterface | None = None) -> tuple[str, ...]:
       """Best-effort secret inventory plus settings the forge's API cannot infer safely."""
       notices = [
           "enable Actions read/write permissions and allow Actions to create pull requests",
       ]
       names, problem = ForgeSelector().resolve(forge).secret_names()
       if problem:
           skipped = (
               f"could not list repository secrets ({problem}); "
               "skipping secret/permission checks"
           )
           return (*notices, skipped)
       for name in ("ANTHROPIC_API_KEY", "AUTOMERGE_TOKEN"):
           if name not in names:
               notices.append(f"configure repository secret {name}")
       return tuple(notices)
   ```
   Unbound, as today (`gh secret list` carried no `--repo`).
2. **D3:** the notice was `"gh not found; skipping secret/permission checks"` for a missing
   `gh`, and nothing at all for any other failure; now every failure names itself, for example
   ``"could not list repository secrets (the GitHub CLI (`gh`) is not installed); skipping
   secret/permission checks"``. Output that is not a JSON list, which today silently produced
   both "configure repository secret" notices, is now such a failure too. **D1:** `gh secret
   list` runs in the root `load_config()` finds rather than the process's working directory;
   same repository for `gh`. On GitHub the argv is otherwise unchanged:
   `secret list --json name`.
3. Imports in `install.py`: add `from vibey_gh.forge_selector import ForgeSelector` after
   `from vibey_gh.fallback_pin import FallbackPinResolver` (24) and
   `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface` after
   `from vibey_gh.interfaces.fallback_pin_resolver_interface import FallbackPin` (25).
   `import json` and `import subprocess` stay (used elsewhere in the module).
4. `cli._install` gains the declared seam and passes it on:
   ```python
   def _install(
       args,
       resolver: FallbackPinResolverInterface | None = None,
       forge: ForgeAdapterInterface | None = None,
   ) -> int:
       # Module-level like every other handler in this file: argparse dispatches through
       # `set_defaults(func=_install)`. `resolver` and `forge` are its declared seams.
       cfg = load_config()
       pin = (resolver or FallbackPinResolver()).resolve(cfg)
       for action in install.install(cfg, fallback_pin=pin):
           print(f"  {action.hook}: {action.outcome}")
       for notice in install.installation_notices(forge=forge):
           print(f"  notice: {notice}")
       if pin.notice:
           print(f"  notice: {pin.notice}")
       print(f"vibey-gh: installed into {cfg.root}")
       return 0
   ```
   `cli.py` imports `from vibey_gh.interfaces.forge_adapter_interface import
   ForgeAdapterInterface` between `from vibey_gh.interfaces.fallback_pin_resolver_interface
   import FallbackPinResolverInterface` (35) and
   `from vibey_gh.interfaces.marketplace_renderer_interface import MarketplaceRendererInterface`
   (36). argparse still calls `_install(args)` (`cli.py:1260-1261`), so `forge` defaults to
   `None` and the selector resolves the repository's own forge.
5. On Forgejo (the default) the inventory is the repository's Actions secrets; an older Forgejo
   without that route answers a 404, which is reported through the notice like any other
   problem, never skipped silently.

## Where to change
- `vibey_gh/install.py` (701 lines, `edit_file` only): imports (24-25) and
  `installation_notices` (465-487) only.
- `vibey_gh/cli.py` (1887 lines, `edit_file` only): one import line (after 35) and `_install`
  (164-174) only.
- Tests: `test/test_pr_automation.py` (the install-notice tests at 162-214 and one new test),
  `test/test_gh_cli.py` (the `repo` fixture at 32-55 and two new tests),
  `test/test_marketplace.py` (the `repo` fixture at 283-305). All three are longer than 100
  lines: `edit_file` only.
- Once the edits are in, format the touched files once from `src/vibey_tools/gh`:
  `python -m black --line-length 100 vibey_gh/install.py vibey_gh/cli.py test/test_pr_automation.py test/test_gh_cli.py test/test_marketplace.py` then
  `isort vibey_gh/install.py vibey_gh/cli.py test/test_pr_automation.py test/test_gh_cli.py test/test_marketplace.py`; then run the check block. If `ruff format --check` still
  disagrees on a line, restructure that line (C8); never alternate formatters.
- Two source files, because `cli._install` is the declared seam through which the CLI tests
  reach `installation_notices`; three test files, because every test that runs `install` must
  stop reaching for the default forge's host (`https://forgejo.local/`). No new class, so no new
  interface.

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -n '"gh"' vibey_gh/install.py` prints nothing, and
  `grep -rn 'gh not found' vibey_gh test` prints nothing.
- [ ] `grep -c 'monkeypatch.setattr' test/test_pr_automation.py` is exactly 3 lower than before
  this lane (the three `subprocess.run` patches of the install-notice tests go; nothing is added).
- [ ] No test that runs `install` resolves the default forge: every `main(["install"])` and
  `_install(...)` in `test/test_gh_cli.py` (60, 71, 91, 96, 104, 114, 139, 437) and
  `test/test_marketplace.py:376` runs against a `repo` fixture that declares GitHub and puts the
  conftest `fake_gh` on `PATH`; `test/test_tidy.py`'s `checkable` fixture already does both
  (`test/test_tidy.py:357-370`) and passes unmodified.
- [ ] `python -m pytest -q` passes at 100% line and branch coverage of `vibey_gh`; black, isort,
  mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
Substitution happens only at declared seams (C7): `forge=`, the conftest `fake_gh` fixture,
`monkeypatch.setenv/chdir`.

**`test/test_pr_automation.py`.** If they are not already imported at the top of the file, add
`from forge_doubles import RecordingForge` after `import pytest` (10) and
`from vibey_gh.forge_github import GitHubForge` between the `from vibey_gh.config import (`
block (13-18) and `from vibey_gh.install import WORKFLOWS, installation_notices, render_workflow`
(19); if either is already there, leave it.
- Replace `test_installation_notices_report_missing_secrets` (162-174):
  ```python
  def test_installation_notices_report_missing_secrets():
      only_one = RecordingForge(secret_names=(frozenset({"ANTHROPIC_API_KEY"}), ""))
      notices = installation_notices(forge=only_one)
      assert any("AUTOMERGE_TOKEN" in item for item in notices)
      assert not any("ANTHROPIC_API_KEY" in item for item in notices)
      assert ("secret_names",) in only_one.calls
      none_set = RecordingForge(secret_names=(frozenset(), ""))
      assert any("ANTHROPIC_API_KEY" in item for item in installation_notices(forge=none_set))
  ```
- Replace `test_installation_notices_degrade_when_gh_is_not_installed` (177-187), keeping its
  docstring:
  ```python
  def test_installation_notices_degrade_when_gh_is_not_installed():
      """`install` writes every file BEFORE it asks for notices, so a missing `gh` raising
      FileNotFoundError here turned a finished install into a traceback and exit 1."""
      missing = "the GitHub CLI (`gh`) is not installed"
      notices = installation_notices(forge=RecordingForge(secret_names=(frozenset(), missing)))
      expected = f"could not list repository secrets ({missing}); skipping secret/permission checks"
      assert expected in notices
      assert not any("configure repository secret" in item for item in notices)
  ```
- In `test_install_finishes_when_gh_is_not_on_path` (190-214) change exactly two statements.
  Line 207 becomes
  `(repo / ".vibey-gh.toml").write_text('[platform]\nkind = "github"\n[install]\nworkflows = []\n')`,
  so the install resolves GitHub and never reaches for a Forgejo host; and line 213 becomes
  ```python
      notice = (
          "notice: could not list repository secrets (the GitHub CLI (`gh`) is not installed); "
          "skipping secret/permission checks"
      )
      assert notice in out
  ```
- New test (append at the end of the file):
  ```python
  def test_installation_notices_list_secrets_with_todays_argv(tmp_path, fake_gh):
      fake_gh.script({"secret list --json name": {"out": '[{"name":"ANTHROPIC_API_KEY"}]'}})
      notices = installation_notices(forge=GitHubForge(root=tmp_path))
      assert "configure repository secret AUTOMERGE_TOKEN" in notices
      assert "configure repository secret ANTHROPIC_API_KEY" not in notices
      cwd = str(tmp_path.resolve())
      expected = [{"argv": ["secret", "list", "--json", "name"], "cwd": cwd, "stdin": None}]
      assert fake_gh.invocations() == expected
  ```

**`test/test_gh_cli.py`.** Add `from forge_doubles import RecordingForge` after `import pytest`
(15). The `repo` fixture (32-55) takes the conftest `fake_gh` and declares GitHub first:
```python
@pytest.fixture
def repo(tmp_path: Path, monkeypatch, fake_gh) -> Path:
    # GitHub is declared and a fake `gh` is first on PATH, so `install`'s secret inventory
    # never reaches a real forge: the fake has no answer, and install says so.
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, check=True)
```
and the config text gains `'[platform]\nkind = "github"\n'` as its **first** literal, directly
before `'[fingerprint]\nsources = ["src/*.py"]\n'`; everything else in the fixture stays. This
covers every install-reaching test in the file, including the two direct `_install(...)` calls
at 91 and 96. New tests (append at the end of the file):
```python
def test_install_lists_secrets_through_the_forge_it_is_given(repo, capsys):
    forge = RecordingForge(secret_names=(frozenset({"ANTHROPIC_API_KEY"}), ""))
    resolver = _Resolved(FallbackPin("1.0.0"))
    assert _install(argparse.Namespace(), resolver=resolver, forge=forge) == 0
    out = capsys.readouterr().out
    assert "  notice: configure repository secret AUTOMERGE_TOKEN\n" in out
    assert "configure repository secret ANTHROPIC_API_KEY" not in out
    assert ("secret_names",) in forge.calls


def test_install_says_when_it_could_not_list_secrets(repo, capsys):
    assert main(["install"]) == 0
    notice = (
        "  notice: could not list repository secrets "
        "(gh secret list --json name: no scripted answer); skipping secret/permission checks\n"
    )
    assert notice in capsys.readouterr().out
```

**`test/test_marketplace.py`.** The `repo` fixture (283-305) takes `fake_gh` the same way
(`def repo(tmp_path: Path, monkeypatch, fake_gh) -> Path:`) and its config text gains
`'[platform]\nkind = "github"\n'` as its **first** literal, directly before
`'[fingerprint]\nsources = ["src/*.py"]\n'`. It must be first, not last:
`test_doctor_knows_the_section_and_names_a_misspelt_key` appends a key that must land in
`[marketplace]`, the last table, and `test_load_config_defaults_to_no_marketplace` keeps only
the text before `[marketplace]`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_pr_automation.py test/test_gh_cli.py test/test_marketplace.py test/test_tidy.py
python -c "import vibey_gh.install, vibey_gh.cli, vibey_gh.forge_selector"
python -m pytest -q
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
git diff --stat
```
`python -m pytest -q` (no `--no-cov`) is the whole suite at 100% line and branch coverage of
`vibey_gh` (`pyproject.toml:64-71`). `git diff --stat` must list only the two source files and
three test files named under "Where to change". Nothing here is platform-specific: run the same
block on macOS and on Arch Linux (8.h); CI's `tools` job reruns it on Linux.

## Out of scope
- The rest of `install.py` and `cli.py`; `pr_automation.py` and the other tests in
  `test/test_pr_automation.py` (child lanes `split-342-1-state-comment`,
  `split-342-2-pr-automation`, `split-342-3-fork-mirror`); `test/test_tidy.py` (it already
  declares GitHub and passes unmodified).
- The secret names `ANTHROPIC_API_KEY` and `AUTOMERGE_TOKEN` and the first notice's wording
  stay as they are; making them configurable is not this lane's.
- Every adapter file (`forge_*.py`, `interfaces/`), `test/forge_doubles.py`.
- `test/conftest.py`: never touched.
- This repository's root `.vibey-gh.toml`: its `[platform]` / `kind = "github"` declaration
  (lines 18-19, merged into integration as `d3b4a388`) is the operator's, written by a human
  per 8.b (`doctrines.md:179-181`). The lane never writes or changes it; the `[platform]`
  tables this lane writes are in temporary test repositories only.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the
  docs wave owns those. Do not push, open PRs, or change git remotes. Commit locally with a
  Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every adapter verb answers `(value, problem)`. `problem` is `""`
exactly when the forge answered; otherwise `value` is the empty value for its type (`None`,
`()`, `frozenset()`, `False`, `{}`) and `problem` is one sentence. No verb raises for a failed
call, a missing client, a non-2xx status or unreadable output
(`vibey_gh/interfaces/forge_adapter_interface.py:9-16`). A verb a forge has no equivalent for
answers `(<empty>, NotSupported(kind, verb, reason).problem)`, whose text is
`f"{kind.value} does not support {verb}: {reason}"`; the caller reports it like any other
problem (10.f).

**C6 — how this module calls the adapter.**
1. Obtain: `installation_notices` gains a keyword-only parameter
   `forge: ForgeAdapterInterface | None = None` and resolves with
   `ForgeSelector().resolve(forge)` (it has no `cfg`). `resolve(forge, cfg=None)` returns the
   injected `forge` when it is not `None`, else `self.select(cfg)` when `cfg` is given, else
   `self.select(load_config())`. `cli._install` passes `forge=forge` down.
2. No binding here: today's `gh secret list` never called `github_state.repository()` and passed
   no `--repo`, so the verb runs on the unbound adapter.
3. A site that returned a value keeps returning one: a problem becomes a notice, never an
   exception.

**V — the adapter verb this lane calls** (declared on `ForgeAdapterInterface` by forge-0f).
- `secret_names(self) -> tuple[frozenset[str], str]`. GitHub: `secret list [--repo <R>] --json
  name` (unbound here, so no `--repo`); a list → the `frozenset` of the str `name` of every dict
  item; anything else → ``(frozenset(), "`gh secret list` returned JSON that is not a list")``;
  a `gh` failure → `(frozenset(), "gh secret list --json name: <stderr>")`; a missing `gh` →
  ``(frozenset(), "the GitHub CLI (`gh`) is not installed")``. Forgejo: the `name`s of the paged
  `repos/{R}/actions/secrets` (an older Forgejo answers 404, reported as the transport's problem
  `"Forgejo API error 404: <reason>"`, never special-cased). GitLab: the `key`s of the paged
  `projects/{P}/variables`.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`).
  Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never `monkeypatch.setattr` a module or
  class attribute (`subprocess.run`, a module function), never `mock.patch`, `MagicMock` or
  `AsyncMock`. `monkeypatch.setenv/delenv/chdir` are fine.
- `RecordingForge` (`test/forge_doubles.py`, import with `from forge_doubles import
  RecordingForge`; pytest puts `test/` on `sys.path`) is the in-memory fake of
  `ForgeAdapterInterface`. It is scripted per verb by keyword:
  `RecordingForge(secret_names=(frozenset({"X"}), ""))`. Each scripted verb returns its value.
  `.calls` lists `(verb, *args, *sorted(kwargs.items()))`, so `secret_names()` is recorded as
  `("secret_names",)`. An unscripted verb raises `AttributeError`.
- GitHub argv proofs use the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real
  `gh` executable put first on `PATH` (in `<tmp_path>/bin`). `fake_gh.script({...})` replaces
  every answer, keyed by the argv joined with single spaces, each answer an object with optional
  `out`, `err`, `code`; an unscripted argv exits 3 with `no scripted answer` on stderr (which the
  GitHub adapter reports as `gh secret list --json name: no scripted answer`).
  `fake_gh.invocations()` lists `{"argv": [...], "cwd": <dir>, "stdin": None}` per run. Build the
  adapter as `GitHubForge(root=tmp_path)` and compare `cwd` with `str(tmp_path.resolve())`.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch
  `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
and the root `ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
comparisons to a local before asserting; no implicit string concatenation that would fit on one
line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters fight over a line, restructure the line; never alternate.

**Depends on:** forge-0g, forge-0f, split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve
- forge-0g: the end of wave 1 (#338); this lane starts from a branch where every wave-1 lane has merged.
- forge-0f: `secret_names()` on all three adapters.
- split-332-1-transport-seams: the transports that time out and answer a problem instead of hanging, so a slow forge cannot stall `install`.
- split-332-2-adapter-paging: the paged Forgejo/GitLab listing behind `secret_names`, and `test/forge_doubles.py`.
- split-332-3-repository-name: the GitHub `_read`/`_scoped` helpers whose not-installed and failure sentences the new notice carries.
- split-332-4-selector-resolve: `ForgeSelector.resolve` and the `RecordingForge` double.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
