<!-- split of #332: child 4 of 4; audit: issue-audit/updates/332.md -->

## Title
feat(gh): ForgeSelector resolves an injected forge and binds GitHub only to an explicit repository

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge
(`src/vibey_tools/gh/docs/doctrines.md:138`) and routes every forge call through
`ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Every later lane that moves a module onto
the adapter starts each public function with one call that returns the injected forge, else the
forge for the caller's configuration, else the forge for the working directory's configuration;
that call does not exist yet (`vibey_gh/forge_selector.py:61-65` has only `select`). Those lanes
also need one recording forge double to inject.

`ForgeSelector._github` binds the adapter to the repository parsed from the clone's `origin`
remote (`vibey_gh/forge_selector.py:67-71`, through `_repository` at `:92-110`). That is wrong for
GitHub: `gh` resolves the repository itself from `$GH_REPO` and the clone, honouring
`gh repo set-default`, which an origin-URL parse ignores, and every `gh` call site relies on
that. A bound GitHub adapter also adds `--repo <name>` to every `pr`/`issue` command, so GitHub
must be bound only when the operator names `[platform] repository` explicitly. Forgejo and GitLab
keep reading `origin`: their REST paths need a name.

## Required behaviour
1. `ForgeSelector._github` (`vibey_gh/forge_selector.py:67-71`) binds
   `repository=cfg.platform.repository` and does not call `_repository(cfg)`:
   ```python
       @staticmethod
       def _github(cfg: GhConfig) -> ForgeAdapterInterface:
           host = cfg.platform.host
           transport = GhTransport(host=None if not host or host == GH_DEFAULT_HOST else host)
           return GitHubForge(
               root=cfg.root,
               repository=cfg.platform.repository,
               transport=transport,
           )
   ```
   `_forgejo` and `_gitlab` are unchanged (they keep `repository=_repository(cfg)`).
2. `ForgeSelector` gains, directly after `select` (lines 61-65):
   ```python
       def current(self) -> ForgeAdapterInterface:
           return self.select(load_config())

       def resolve(
           self, forge: ForgeAdapterInterface | None, cfg: GhConfig | None = None
       ) -> ForgeAdapterInterface:
           if forge is not None:
               return forge
           if cfg is not None:
               return self.select(cfg)
           return self.current()
   ```
   and the import becomes
   `from vibey_gh.config import ADAPTED_PLATFORM_KINDS, GhConfig, PlatformConfig, load_config`.
   `load_config()` finds the configuration by walking up from the working directory
   (`vibey_gh/config.py:1630-1650`, `:1690`). Neither method asks the forge anything.
3. `vibey_gh/interfaces/forge_selector_interface.py` declares both after `select` (lines 27-34):
   ```python
       def current(self) -> ForgeAdapterInterface:
           """The adapter for the configuration `load_config()` finds from the working
           directory. Builds it and asks the forge nothing, like `select`."""
           ...

       def resolve(
           self, forge: ForgeAdapterInterface | None, cfg: GhConfig | None = None
       ) -> ForgeAdapterInterface:
           """`forge` when a caller injected one, else `select(cfg)` when `cfg` is given, else
           `current()`. Every function that reaches the forge starts with this call."""
           ...
   ```
4. `test/forge_doubles.py` gains `RecordingForge`, appended after `RoutedTransport`, exactly:
   ```python
   class RecordingForge:
       """A forge adapter double for the modules that call the adapter.

       Scripted per verb by keyword, as `RecordingForge(change_request_facts=(facts, ""))`. A
       scripted verb returns its answer, or calls it with the verb's arguments when the answer
       is callable. `repository_name()` answers `("o/r", "")` unless scripted, and
       `for_repository(name)` records the call and returns this same double. `calls` lists every
       call as `(verb, *args, *sorted(kwargs.items()))`. An unscripted verb raises
       `AttributeError`, so a test cannot pass by calling a verb it never named.
       """

       def __init__(self, **answers: Any) -> None:
           self.answers: dict[str, Any] = {"repository_name": ("o/r", ""), **answers}
           self.calls: list[tuple[Any, ...]] = []

       def for_repository(self, repository: str) -> RecordingForge:
           self.calls.append(("for_repository", repository))
           return self

       def __getattr__(self, verb: str) -> Any:
           answers = self.__dict__.get("answers", {})
           if verb not in answers:
               raise AttributeError(f"RecordingForge was not scripted to answer {verb}")
           answer = answers[verb]

           def call(*args: Any, **kwargs: Any) -> Any:
               self.calls.append((verb, *args, *sorted(kwargs.items())))
               return answer(*args, **kwargs) if callable(answer) else answer

           return call
   ```
   Add `RecordingForge` to the module docstring's import example
   (`from forge_doubles import RecordingForge, RoutedTransport`).
5. `test/test_platform.py:276` (in
   `test_selector_binds_an_explicit_repository_and_reads_one_from_origin`) becomes
   `assert ForgeSelector._github(GhConfig(root=repo)).repository == ""`: an origin-only GitHub
   clone is now unbound. The explicit-repository case is the new test below.
6. No other module changes. `test/test_forge_github.py` and `test/test_tidy.py` pass unmodified.

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. Line anchors are those of the storm integration branch at `4317cff6`;
child lane 2 changed `_gitlab` and `_forgejo` in `vibey_gh/forge_selector.py` (lines 73-89) to
pass `host=host`, so read that file again before editing it.

- `vibey_gh/forge_selector.py`: the import (line 20), `current` and `resolve` after `select`
  (after line 65), and `_github` (lines 67-71).
- `vibey_gh/interfaces/forge_selector_interface.py`: `current` and `resolve` after `select`
  (after line 34).
- `test/forge_doubles.py`: `RecordingForge` appended; docstring import example updated.
- `test/test_forge_foundation.py`: new imports in the top import block, new tests appended.
- `test/test_platform.py:276`: the one assertion.
- Only if `test/test_patching_ratchet.py` exists when you start (another storm lane adds the
  tenant's patching ratchet) and it fails on a test file this lane created: record that file in
  `test/patching_baseline.json` with its true counts, all zero (this lane adds no patch). Never
  raise a count. If the ratchet does not exist, skip this.

`ForgeSelector` already has its interface (`ForgeSelectorInterface`), so no new interface file is
needed; `RecordingForge` is a test double.

## Acceptance criteria
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`.
- [ ] `test/test_platform.py::test_the_default_sovereign_selection_is_the_self_hosted_forgejo`
      and `::test_github_on_github_com_leaves_gh_to_find_its_own_host` pass unmodified.
- [ ] `grep -n "_repository(cfg)" vibey_gh/forge_selector.py` shows only `_gitlab` and `_forgejo`.
- [ ] `test/test_forge_github.py` and `test/test_tidy.py` pass unmodified.
- [ ] Every test named below passes.
- [ ] black, isort, mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
Substitute only at declared seams: `ForgeSelector.resolve`'s `forge` argument takes the
`RecordingForge`; `monkeypatch.chdir` changes the working directory `load_config()` walks from.
Never patch a module attribute or an import.

**`test/test_forge_foundation.py`.** The top import block's `forge_doubles` line becomes
`from forge_doubles import RecordingForge, RoutedTransport`. Then append:
```python
def test_recording_forge_answers_only_what_it_was_scripted():
    facts = {"number": 7}
    forge = RecordingForge(
        change_request_facts=(facts, ""),
        delete_branch=lambda branch: (branch == "topic", ""),
    )
    assert forge.repository_name() == ("o/r", "")
    assert forge.for_repository("a/b") is forge
    assert forge.change_request_facts(7) == (facts, "")
    assert forge.delete_branch("topic") == (True, "")
    assert forge.delete_branch(branch="other") == (False, "")
    expected = [
        ("repository_name",),
        ("for_repository", "a/b"),
        ("change_request_facts", 7),
        ("delete_branch", "topic"),
        ("delete_branch", ("branch", "other")),
    ]
    assert forge.calls == expected
    with pytest.raises(AttributeError):
        forge.get_issue(8)
    assert RecordingForge(repository_name=("x/y", "")).repository_name() == ("x/y", "")


def test_selector_binds_github_only_to_an_explicit_repository(tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    origin = "https://github.example/group/tool.git"
    subprocess.run(["git", "remote", "add", "origin", origin], cwd=repo, check=True)
    assert ForgeSelector._github(GhConfig(root=repo)).repository == ""
    assert ForgeSelector._forgejo(GhConfig(root=repo)).repository == "group/tool"
    platform = PlatformConfig(kind="github", repository="o/r")
    bound = ForgeSelector().select(GhConfig(root=repo, platform=platform))
    assert bound == GitHubForge(root=repo, repository="o/r", transport=GhTransport(host=None))


def test_selector_current_loads_the_configuration(tmp_path, monkeypatch):
    config = '[platform]\nkind = "gitlab"\nrepository = "group/tool"\n'
    (tmp_path / ".vibey-gh.toml").write_text(config, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    forge = ForgeSelector().current()
    assert isinstance(forge, GitLabForge)
    assert forge.repository == "group/tool"
    assert forge.root == tmp_path.resolve()


def test_resolve_prefers_injection_then_cfg(tmp_path, monkeypatch):
    injected = RecordingForge()
    selector = ForgeSelector()
    assert selector.resolve(injected) is injected
    assert selector.resolve(injected, GhConfig(root=tmp_path)) is injected
    assert injected.calls == []
    transport = ForgejoTransport(host="forgejo.local", token="")
    expected = ForgejoForge(root=tmp_path, transport=transport)
    assert selector.resolve(None, GhConfig(root=tmp_path)) == expected
    config = '[platform]\nkind = "gitlab"\n'
    (tmp_path / ".vibey-gh.toml").write_text(config, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert isinstance(selector.resolve(None), GitLabForge)
```
(`subprocess`, `GhConfig`, `PlatformConfig`, `ForgejoForge`, `GitLabForge`, `GitHubForge`,
`GhTransport`, `ForgejoTransport` and `ForgeSelector` are already imported by child lanes 1-3.)

**`test/test_platform.py:276`**: `== "group/tool"` becomes `== ""` on the `ForgeSelector._github`
assertion. Nothing else in that file changes.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_foundation.py test/test_platform.py test/test_forge_github.py test/test_tidy.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change"
git status --short   # no new file
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- The adapters (`vibey_gh/forge_github.py`, `vibey_gh/forge_forgejo.py`,
  `vibey_gh/forge_gitlab.py`) and `vibey_gh/interfaces/forge_adapter_interface.py`.
- Every consuming module (`tidy.py`, `merge_train.py`, `promote.py`, …): later forge lanes call
  `resolve`; this lane only provides it.
- `_repository` (`vibey_gh/forge_selector.py:92-110`) keeps serving `_forgejo` and `_gitlab`.
- `test/conftest.py`, and every assertion in `test/test_platform.py` except line 276.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it. Tests write their own `.vibey-gh.toml` under
  `tmp_path` only.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **How later lanes call the adapter.** Every public function that reaches the forge gains a
  keyword-only last parameter `forge: ForgeAdapterInterface | None = None` and starts with
  `forge = ForgeSelector().resolve(forge, cfg)` (or `ForgeSelector().resolve(forge)` when it has
  no `cfg`). Their tests inject a `RecordingForge`. That is why `resolve` must return an injected
  forge untouched and ask it nothing.
- **GitHub scope.** A GitHub adapter is bound exactly when `self.repository` is non-empty, and a
  bound adapter adds `--repo <name>` to its `pr`/`issue`/`label`/`release`/`secret` commands. An
  adopter who sets `[platform] repository` with `kind = "github"` gets a bound adapter; with the
  key unset (this repository, and the default) nothing changes, because `gh` finds the repository
  from `$GH_REPO` and the clone.
- **Tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`). Focused runs need `--no-cov`; the whole-suite run must pass without
  it. Substitute only at a declared seam: no `monkeypatch.setattr` of an import or of a module or
  class attribute, no `mock.patch`, no `MagicMock`/`AsyncMock` (sub-doctrine 9.b). Never touch
  `test/conftest.py`. New test code goes at the end of the test file; new imports go into the
  file's top import block. Use `edit_file` for every existing file; never `write_file` on one.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns, and at or under 95 for anything with nested calls;
  - bind a long comparison or expected value to a local before the `assert`;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - write multi-line calls with one argument per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **Platforms (8.h).** The suite must pass on Arch Linux and macOS: `git` is the only external
  tool the tests run, and paths are compared through `Path.resolve()` (macOS puts `tmp_path`
  behind a `/private` symlink).

**Depends on:** split-332-3-repository-name
- split-332-3-repository-name: the adapters' `repository_name`, the `subprocess`, `GitHubForge`
  and `GhTransport` imports in `test/test_forge_foundation.py`, and (through lane 2) the selector
  passing `host` and `test/forge_doubles.py` with `RoutedTransport`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
