<!-- split of #341: child 2 of 2; audit: issue-audit/updates/341.md -->

## Title
feat(gh): release publication reaches the forge only through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, with GitHub and GitLab declared-only, and `[platform] kind` defaults to `forgejo`
(`vibey_gh/config.py:288`). `vibey_gh/github_release.py` tags and publishes through a private
runner: `_run` (`github_release.py:22-23`, `subprocess.run` with `cwd=None`) and `_repository`
(26-30, an unconditional `gh repo view`) feed the five `gh` calls of `publish` (33-93), so
release publication ignores `[platform]`. This is live release machinery:
`.github/workflows/github-release.yml:136` runs `vibey-gh github-release --target "$TARGET"`,
which reaches `publish` through `cli.py:397-405`. 8.b routes every forge call through
`ForgeAdapterInterface` (`doctrines.md:168-184`), and sub-doctrine 9.b (`doctrines.md:349`:
"Substitution happens at the declared seam, never by patching an import") moves the tests off
the `_run` monkeypatch onto the `forge=` seam.

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`).

1. Delete `_run` and `_repository` (`github_release.py:22-30`) and the imports that become
   unused, `import json` and `import subprocess` (6-7). Add
   `from vibey_gh.forge_selector import ForgeSelector` and
   `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface` between
   `from vibey_gh.config import GhConfig` and `from vibey_gh.versioning import read_version`.
2. `publish` gains a keyword-only last parameter and runs, in this order:
   ```python
   # Module-level (ADR-0016): cli.py calls publish by name; the module converges on a
   # class in its own lane.
   def publish(
       cfg: GhConfig,
       *,
       target: str,
       version: str | None = None,
       forge: ForgeAdapterInterface | None = None,
   ) -> ReleaseResult:
       """Create, but never move or delete, the version tag and its release.

       A release-branch push that carries no version bump already tags the exact same
       version at an earlier commit. That is a no-op, not a failure, unless
       `require_new_version` opts the adopting repository into treating it as one.
       """
       if not cfg.github_release.enabled:
           raise RuntimeError("releases are disabled by [github_release]")
       version = version or read_version(cfg)
       tag = f"{cfg.github_release.tag_prefix}{version}"
       forge = ForgeSelector().resolve(forge, cfg)
       name, problem = forge.repository_name()
       if problem:
           raise RuntimeError(f"could not identify the repository: {problem}")
       bound = forge.for_repository(name)

       tagged, _ = bound.tag_target(tag)
       tag_created = False
       if tagged is not None:
           if tagged != target:
               if cfg.github_release.require_new_version:
                   raise RuntimeError(f"refusing to move existing tag {tag}: {tagged} != {target}")
               return ReleaseResult(tag, tagged, False, False)
       else:
           ok, problem = bound.create_tag(tag, target)
           if not ok:
               raise RuntimeError(f"could not create immutable tag {tag}: {problem}")
           tag_created = True

       release, _ = bound.release_by_tag(tag)
       release_created = False
       if release is None:
           created, problem = bound.create_release(
               tag,
               target=target,
               title=tag,
               generate_notes=cfg.github_release.generate_notes,
           )
           if created is None:
               raise RuntimeError(f"tag {tag} exists but release creation failed: {problem}")
           release_created = True
       return ReleaseResult(tag, target, tag_created, release_created)
   ```
3. `tag_target`'s problem is ignored on purpose: any answer but a SHA leads to `create_tag`,
   which reports the real failure. That is today's behaviour (any non-zero `gh api
   repos/R/git/ref/tags/TAG` led to the create).
4. The module docstring (line 2) becomes
   `"""Idempotent, immutable tagging and release publication through the repository's forge."""`.
   `ReleaseResult` is unchanged. The config key keeps its name, `[github_release]`.
5. On GitHub the argv is unchanged byte for byte: `repo view --json nameWithOwner`,
   `api repos/<R>/git/ref/tags/<tag>`, `api repos/<R>/git/refs --method POST --field
   ref=refs/tags/<tag> --field sha=<target>`, `release view <tag> --repo <R>`, `release create
   <tag> --repo <R> --target <target> --title <tag>` plus `--generate-notes` when
   `generate_notes`. The only deliberate differences:
   - **D1 cwd:** `gh` now runs in `cfg.root` (the adapter's `cwd=self.root`), where `_run` ran
     it in the process's working directory; same repository for `gh`.
   - **D2 `$GH_REPO` first:** the adapter's `repository_name()` consults a non-empty
     `$GH_REPO` before running `gh repo view`, as `github_state.repository()` always has; one
     fewer `gh` call when it is set.
   - **D3 neutral wording:** `"GitHub Releases are disabled by [github_release]"` becomes
     `"releases are disabled by [github_release]"`; `"could not identify GitHub repository:
     <stderr>"` becomes `"could not identify the repository: <problem>"`; `"tag <tag> exists but
     GitHub Release creation failed: <stderr>"` becomes `"tag <tag> exists but release creation
     failed: <problem>"`.
   - **D5 exception type:** a missing `gh`, or output that is not JSON, now surfaces as a
     `RuntimeError` naming the problem, where a `FileNotFoundError` or a JSON error escaped
     before. `cli._github_release` (`cli.py:397-405`) already catches `RuntimeError`.
6. On Forgejo (the default) and GitLab the same code runs; each adapter tells "the tag or
   release does not exist" (`(None, "")`) from "could not ask" (`(None, problem)`).

## Where to change
- `vibey_gh/github_release.py` (93 lines): imports (6-11), delete 22-30, rewrite `publish`
  (33-93), docstring line 2. The pattern to copy for obtaining a forge is `vibey_gh/tidy.py:128-129`
  (the clean-repo survey), with `ForgeSelector().resolve(forge, cfg)` in place of its
  `if forge is None` test.
- Tests: `test/test_github_release.py` (169 lines: change it with `edit_file`, never
  `write_file`).
- Once the edits are in, format the touched files once from `src/vibey_tools/gh`:
  `python -m black --line-length 100 vibey_gh/github_release.py test/test_github_release.py` then
  `isort vibey_gh/github_release.py test/test_github_release.py`; then run the check block. If `ruff format --check` still
  disagrees on a line, restructure that line (C8); never alternate formatters.
- No new class, so no new interface.

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -nE '"gh"|subprocess|json|github_state' vibey_gh/github_release.py`
  prints nothing.
- [ ] `grep -c 'monkeypatch.setattr' test/test_github_release.py` prints `0` (3 at `4317cff6`).
- [ ] `test_publication_on_github_is_todays_argv` pins all five GitHub argv and their `cwd`.
- [ ] `test/test_gh_cli.py::test_github_release_cli` passes unmodified.
- [ ] `python -m pytest -q` passes at 100% line and branch coverage of `vibey_gh`; black, isort,
  mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
All in `test/test_github_release.py`. Substitution happens only at declared seams (C7):
`forge=`, the conftest `fake_gh` fixture, `monkeypatch.setenv/delenv`.

**Imports.** The block at `test/test_github_release.py:4-12` becomes:
```python
from __future__ import annotations

from pathlib import Path

import pytest
from forge_doubles import RecordingForge

from vibey_gh import github_release
from vibey_gh.config import GhConfig, GithubReleaseConfig, load_config
from vibey_gh.forge import ForgeRelease
from vibey_gh.forge_github import GitHubForge
```
If `isort --check-only` places `from forge_doubles import RecordingForge` differently, take
isort's placement and confirm `ruff check` agrees.

**Delete** `done` (24-25), `test_run_uses_noninteractive_subprocess` (28-38; its runner is gone)
and `fake` (41-52). `cfg` (15-21) and `test_config_parses_and_validates` (55-64) stay.

**Replace** the tests at 67-169 with these (keep the names):
```python
def test_existing_matching_tag_and_release_are_idempotent(tmp_path):
    forge = RecordingForge(
        tag_target=("abc", ""),
        release_by_tag=(ForgeRelease(tag="v1.2.3"), ""),
    )
    result = github_release.publish(cfg(tmp_path), target="abc", forge=forge)
    assert result == github_release.ReleaseResult("v1.2.3", "abc", False, False)
    assert ("for_repository", "o/r") in forge.calls
    assert not any(call[0].startswith("create") for call in forge.calls)


def test_creates_tag_and_generated_release(tmp_path):
    forge = RecordingForge(
        tag_target=(None, ""),
        create_tag=(True, ""),
        release_by_tag=(None, ""),
        create_release=(ForgeRelease(tag="v2.0.0", name="v2.0.0"), ""),
    )
    result = github_release.publish(cfg(tmp_path), target="def", version="2.0.0", forge=forge)
    assert result.tag_created and result.release_created
    assert ("create_tag", "v2.0.0", "def") in forge.calls
    made = (
        "create_release",
        "v2.0.0",
        ("generate_notes", True),
        ("target", "def"),
        ("title", "v2.0.0"),
    )
    assert made in forge.calls


def test_release_without_generated_notes(tmp_path):
    forge = RecordingForge(
        tag_target=("abc", ""),
        release_by_tag=(None, ""),
        create_release=(ForgeRelease(tag="release-1.2.3"), ""),
    )
    config = cfg(tmp_path, tag_prefix="release-", generate_notes=False)
    github_release.publish(config, target="abc", forge=forge)
    made = [call for call in forge.calls if call[0] == "create_release"]
    expected = [
        (
            "create_release",
            "release-1.2.3",
            ("generate_notes", False),
            ("target", "abc"),
            ("title", "release-1.2.3"),
        )
    ]
    assert made == expected


@pytest.mark.parametrize(
    "answers,match",
    [
        (
            {"repository_name": ("", "gh repo view --json nameWithOwner: no repo")},
            "could not identify the repository: gh repo view",
        ),
        (
            {"tag_target": (None, ""), "create_tag": (False, "denied")},
            "could not create immutable tag v1.2.3: denied",
        ),
        (
            {
                "tag_target": ("abc", ""),
                "release_by_tag": (None, ""),
                "create_release": (None, "denied"),
            },
            "tag v1.2.3 exists but release creation failed: denied",
        ),
    ],
)
def test_release_failures_are_safe(tmp_path, answers, match):
    with pytest.raises(RuntimeError, match=match):
        github_release.publish(cfg(tmp_path), target="abc", forge=RecordingForge(**answers))


def test_existing_tag_at_other_sha_is_a_no_op_by_default(tmp_path):
    forge = RecordingForge(tag_target=("other", ""))
    result = github_release.publish(cfg(tmp_path), target="abc", forge=forge)
    assert result == github_release.ReleaseResult("v1.2.3", "other", False, False)
    # never reaches the release-view/create step
    assert not any(call[0] in {"release_by_tag", "create_release"} for call in forge.calls)


def test_existing_tag_at_other_sha_raises_when_new_version_required(tmp_path):
    forge = RecordingForge(tag_target=("other", ""))
    config = cfg(tmp_path, require_new_version=True)
    with pytest.raises(RuntimeError, match="refusing to move"):
        github_release.publish(config, target="abc", forge=forge)


def test_disabled_release_does_not_touch_github(tmp_path):
    forge = RecordingForge()
    with pytest.raises(RuntimeError) as raised:
        github_release.publish(cfg(tmp_path, enabled=False), target="abc", forge=forge)
    assert str(raised.value) == "releases are disabled by [github_release]"
    assert forge.calls == []
```

**New tests (append at the end of the file):**
```python
def test_a_tag_the_forge_could_not_read_is_created_and_the_create_says_why(tmp_path):
    forge = RecordingForge(
        tag_target=(None, "gh api repos/o/r/git/ref/tags/v1.2.3: HTTP 502"),
        create_tag=(False, "Reference already exists"),
    )
    with pytest.raises(RuntimeError) as raised:
        github_release.publish(cfg(tmp_path), target="abc", forge=forge)
    expected = "could not create immutable tag v1.2.3: Reference already exists"
    assert str(raised.value) == expected


def test_publication_on_github_is_todays_argv(monkeypatch, tmp_path, fake_gh):
    monkeypatch.delenv("GH_REPO", raising=False)
    view = "repo view --json nameWithOwner"
    ref = "api repos/o/r/git/ref/tags/v1.0.0"
    tag = "api repos/o/r/git/refs --method POST --field ref=refs/tags/v1.0.0 --field sha=abc"
    shown = "release view v1.0.0 --repo o/r"
    made = "release create v1.0.0 --repo o/r --target abc --title v1.0.0 --generate-notes"
    fake_gh.script(
        {
            view: {"out": '{"nameWithOwner":"o/r"}'},
            ref: {"err": "gh: Not Found (HTTP 404)\n", "code": 1},
            tag: {"out": "{}"},
            shown: {"err": "release not found\n", "code": 1},
            made: {"out": "https://github.com/o/r/releases/tag/v1.0.0\n"},
        }
    )
    forge = GitHubForge(root=tmp_path)
    result = github_release.publish(cfg(tmp_path), target="abc", version="1.0.0", forge=forge)
    assert result == github_release.ReleaseResult("v1.0.0", "abc", True, True)
    cwd = str(tmp_path.resolve())
    expected = [
        {"argv": line.split(), "cwd": cwd, "stdin": None}
        for line in (view, ref, tag, shown, made)
    ]
    assert fake_gh.invocations() == expected
```

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_github_release.py test/test_gh_cli.py
python -c "import vibey_gh.github_release, vibey_gh.cli, vibey_gh.forge_selector"
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
`vibey_gh` (`pyproject.toml:64-71`). `git diff --stat` must list only
`src/vibey_tools/gh/vibey_gh/github_release.py` and
`src/vibey_tools/gh/test/test_github_release.py`. Nothing here is platform-specific: run the same
block on macOS and on Arch Linux (8.h); CI's `tools` job reruns it on Linux.

## Out of scope
- `vibey_gh/reconcile.py`: child lane `split-341-1-reconcile`.
- `vibey_gh/cli.py`, `.github/workflows/github-release.yml`, every adapter file
  (`forge_*.py`, `interfaces/`), `vibey_gh/config.py` (the `[github_release]` key and its
  `GithubReleaseConfig` keep their names), `test/forge_doubles.py`.
- **Recorded open question, not this lane's work:** the adapter lane forge-0f (#337) makes
  Forgejo's and GitLab's `create_release` ignore `generate_notes` (their releases get an empty
  body) instead of answering NotSupported. That is a silent approximation C1 forbids, and the
  default `generate_notes = true` (`config.py:839`) makes it the sovereign default's normal
  path. This lane passes `generate_notes` through unchanged and does not special-case any
  forge; the fix, if the operator wants one, belongs to the adapter lane.
- `test/conftest.py`: never touched.
- This repository's root `.vibey-gh.toml`: its `[platform]` / `kind = "github"` declaration
  (lines 18-19, merged into integration as `d3b4a388`) is the operator's, written by a human
  per 8.b (`doctrines.md:179-181`). The lane never writes or changes it.
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
problem (10.f), never special-cases a forge, and never skips silently.

**C6 — how this module calls the adapter.**
1. Obtain: `publish` gains a keyword-only last parameter
   `forge: ForgeAdapterInterface | None = None` and, after the `enabled` check and the tag
   computation, runs `forge = ForgeSelector().resolve(forge, cfg)`. `resolve(forge, cfg=None)`
   returns the injected `forge` when it is not `None`, else `self.select(cfg)` when `cfg` is
   given, else `self.select(load_config())`.
2. Bind where today's code called `_repository()`, once per call:
   `name, problem = forge.repository_name()`; on a problem raise
   `RuntimeError(f"could not identify the repository: {problem}")`;
   `bound = forge.for_repository(name)`.
3. A site that raised keeps raising, with its prefix; a site that ignored a result keeps
   ignoring it.

**V — the adapter verbs this lane calls** (all declared on `ForgeAdapterInterface` by wave 1).
- `repository_name(self) -> tuple[str, str]`. GitHub: the bound `self.repository`, else a
  non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner` → its `nameWithOwner`; a `gh`
  failure answers `("", "gh repo view --json nameWithOwner: <stderr>")`, a missing `gh` answers
  ``("", "the GitHub CLI (`gh`) is not installed")``. Forgejo/GitLab: `(self.repository, "")`,
  or `("", "no Forgejo repository is named: set [platform] repository, or give the clone an
  origin remote")` (with `GitLab` in the GitLab text).
- `for_repository(self, repository: str) -> ForgeAdapterInterface`: the same adapter bound to
  that repository. A bound GitHub adapter inserts `--repo <name>` right after the subcommand's
  positional argument (`release view v1.0.0 --repo o/r`).
- `tag_target(self, tag: str) -> tuple[str | None, str]`: `(sha, "")` the tag exists,
  `(None, "")` the forge said it does not, `(None, problem)` the adapter could not ask. GitHub:
  `api repos/<R>/git/ref/tags/<tag>`; non-zero exit → `(None, "")` when `(HTTP 404)` is in
  stderr, else the stripped stderr as the problem; unreadable stdout or no str `object.sha` →
  ``(None, "`gh api` returned a tag reference that could not be read")``. Forgejo: GET
  `repos/{R}/git/refs/tags/{tag}`, an exact `ref == "refs/tags/<tag>"` match (Forgejo
  prefix-matches, so `v1` must not take `v10`), 404 → `(None, "")`. GitLab: GET
  `projects/{P}/repository/tags/<quoted tag>` → `commit.id`, 404 → `(None, "")`.
- `create_tag(self, tag: str, sha: str) -> tuple[bool, str]`. GitHub:
  `api repos/<R>/git/refs --method POST --field ref=refs/tags/<tag> --field sha=<sha>`; exit 0 →
  `(True, "")`, else ``(False, <stripped stderr, or "`gh api` exited <code>">)``. Forgejo: POST
  `repos/{R}/tags` `{"tag_name", "target"}`; GitLab: POST `projects/{P}/repository/tags`
  `{"tag_name", "ref"}`.
- `release_by_tag(self, tag: str) -> tuple[ForgeRelease | None, str]`. GitHub:
  `release view <tag> [--repo <R>]`; exit 0 → `(ForgeRelease(tag=tag), "")`; `release not
  found` in the lower-cased stderr → `(None, "")`; otherwise `(None, <stripped stderr>)`.
  Forgejo: GET `repos/{R}/releases/tags/<tag>`; GitLab: GET `projects/{P}/releases/<tag>`;
  404 → `(None, "")` on both.
- `create_release(self, tag: str, *, target: str, title: str, generate_notes: bool) ->
  tuple[ForgeRelease | None, str]`. GitHub: `release create <tag> [--repo <R>] --target
  <target> --title <title>` plus `--generate-notes` when `generate_notes`; exit 0 →
  `(ForgeRelease(tag=tag, name=title), "")`, else ``(None, <stripped stderr, or "`gh release
  create` exited <code>">)``. Forgejo: POST `repos/{R}/releases`; GitLab: POST
  `projects/{P}/releases` (both ignore `generate_notes`; see Out of scope).
- `ForgeRelease` (`vibey_gh/forge.py:133-148`): `ForgeRelease(tag: str, name: str = "", draft:
  bool = False)`, frozen.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`).
  Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never `monkeypatch.setattr` a module or
  class attribute (`subprocess.run`, `github_release._run`, a module function), never
  `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv/delenv/chdir` are fine.
- `RecordingForge` (`test/forge_doubles.py`, import with `from forge_doubles import
  RecordingForge`; pytest puts `test/` on `sys.path`) is the in-memory fake of
  `ForgeAdapterInterface`. It is scripted per verb by keyword: `RecordingForge(tag_target=("abc",
  ""), ...)`. Each scripted verb returns its value, or, when the value is callable, calls it with
  the verb's own arguments and returns what it returns. `repository_name()` defaults to
  `("o/r", "")` and can be scripted like any verb. `for_repository(name)` records the call and
  returns the same double. `.calls` lists `(verb, *args, *sorted(kwargs.items()))`, so
  `create_release("v2.0.0", target="def", title="v2.0.0", generate_notes=True)` is recorded as
  `("create_release", "v2.0.0", ("generate_notes", True), ("target", "def"), ("title",
  "v2.0.0"))`. An unscripted verb raises `AttributeError`. Whether `repository_name` itself
  appears in `.calls` is the double's business: no assertion in this spec depends on it.
- GitHub argv proofs use the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real
  `gh` executable put first on `PATH`. `fake_gh.script({...})` replaces every answer, keyed by
  the argv joined with single spaces, each answer an object with optional `out`, `err`, `code`
  (`{}` is a silent success); an unscripted argv exits 3 with `no scripted answer` on stderr.
  `fake_gh.invocations()` lists `{"argv": [...], "cwd": <dir>, "stdin": None}` per run. Build
  the adapter as `GitHubForge(root=tmp_path)` and compare `cwd` with `str(tmp_path.resolve())`.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch
  `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
and the root `ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
comparisons to a local before asserting; no implicit string concatenation that would fit on one
line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters fight over a line, restructure the line; never alternate.

**Depends on:** forge-0g, forge-0f, split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve
- forge-0g: the end of wave 1 (#338); this lane starts from a branch where every wave-1 lane has merged.
- forge-0f: `tag_target`, `create_tag`, `release_by_tag` and the reshaped `create_release(tag, *, target, title, generate_notes)` on all three adapters.
- split-332-1-transport-seams: `NotSupported` and the transports that read an empty 2xx answer and time out.
- split-332-2-adapter-paging: `_absent` (Forgejo/GitLab tell a missing tag or release from a failed read) and `test/forge_doubles.py`.
- split-332-3-repository-name: `repository_name()` and the GitHub `_scoped`/`_read`/`_run` helpers that keep the argv byte-identical.
- split-332-4-selector-resolve: `ForgeSelector.resolve` and the `RecordingForge` double.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
