<!-- split of #342: child 3 of 4; audit: issue-audit/updates/342.md -->

## Title
feat(gh): the fork mirror clones from the forge's own URL through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, with GitHub and GitLab declared-only, and `[platform] kind` defaults to `forgejo`
(`vibey_gh/config.py:288`). `pr_automation.mirror_fork` (`vibey_gh/pr_automation.py:676-761`)
fetches the fork head from a hard-coded `https://github.com/{owner}/{repo}.git` (688) and then
opens, labels, comments on and closes pull requests with four raw `gh` calls (712-755), so on
the sovereign default it would clone from GitHub and drive GitHub. It is live:
`vibey-gh pr-automation mirror-fork` calls it (`cli.py:345`). 8.b routes every forge call
through `ForgeAdapterInterface` (`doctrines.md:168-184`), and sub-doctrine 9.b
(`doctrines.md:349`: "Substitution happens at the declared seam, never by patching an import")
moves the test off `monkeypatch.setattr(pa, "fetch_pr", ...)` onto the `forge=` seam.

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`).
This lane starts after child lane `split-342-2-pr-automation`, so `fetch_pr(number, *,
forge=None)` exists and `pr_automation.py` already imports `ForgeSelector` and
`ForgeAdapterInterface`.

1. `mirror_fork` gains a keyword-only last parameter and resolves with its `cfg`:
   ```python
   # Module-level (ADR-0016): cli.py calls this module's functions by name; the module
   # converges on a class in its own lane.
   def mirror_fork(
       number: int, cfg: GhConfig, *, forge: ForgeAdapterInterface | None = None
   ) -> dict[str, Any]:
       """Mirror an exact fork head and open a repository-owned replacement PR."""
       forge = ForgeSelector().resolve(forge, cfg)
       pr = fetch_pr(number, forge=forge)
   ```
2. The checks are unchanged: `head`, `short`, `branch`, `refspec = repair_refspec(branch)`,
   `owner`, `repo`, and `RuntimeError("pull request does not expose a fork repository")` when
   either is empty (`pr_automation.py:679-686`).
3. The clone URL comes from the forge, and a problem stops the mirror before any git runs:
   ```python
   url, problem = forge.fork_clone_url(owner, repo)
   if problem:
       raise RuntimeError(problem)
   fetch = subprocess.run(
       ["git", "fetch", "--quiet", url, head],
       cwd=cfg.root,
       capture_output=True,
       text=True,
       check=False,
   )
   ```
   The `git fetch` failure check, the `git push` (696-704), `author`, `title` and `body`
   (705-711) are unchanged.
4. The replacement pull request is opened through the adapter; `replacement` is the number it
   answers:
   ```python
   replacement, problem = forge.create_change_request(
       base=str(pr["baseRefName"]),
       head=branch,
       title=f"Repair #{number}: {title}",
       body=body,
   )
   if replacement is None:
       raise RuntimeError(f"could not open replacement pull request: {problem}")
   ```
   This replaces the `gh pr create` block and the `re.sub` number parse (712-733).
5. Then, **unbound** as today (their `gh` calls carried no `--repo`), results ignored:
   ```python
   forge.add_label(replacement, EXTERNAL_REPAIR_LABEL)
   forge.comment_on_change_request(
       number,
       f"Repairs continue in #{replacement}; closing this fork PR only after preserving "
       "its exact head and attribution.",
   )
   forge.close_change_request(number)
   ```
   The comment text is the same sentence as today (747), written as two literals because the
   whole line would pass 100 columns. The returned dict (756-761) is unchanged.
6. After this lane `pr_automation.py` runs no `gh` at all. `import subprocess` stays (the two
   git calls) and `import re` stays (the workflow parsers at 69-71).
7. On GitHub the argv and working directory are unchanged byte for byte: `git fetch --quiet
   https://github.com/<owner>/<repo>.git <head>` (the GitHub adapter's `fork_clone_url` answers
   today's literal), `pr create --base <base> --head <branch> --title <title> --body <body>`,
   `pr edit <replacement> --add-label vibey-gh:external-repair`, `pr comment <n> --body <text>`,
   `pr close <n>`, all in `cfg.root`. The deliberate differences: **D1** `fetch_pr`'s `pr view`
   now runs in `cfg.root` rather than the process's working directory; **D5** a `gh pr create`
   that prints no number now raises `RuntimeError("could not open replacement pull request:
   `gh pr create` printed no pull request number")` instead of an escaping `ValueError`, and a
   missing `gh` raises `RuntimeError(problem)` instead of `FileNotFoundError`.
8. On Forgejo (the default) and GitLab the fork is fetched from `https://<host>/<owner>/<repo>.git`
   on the forge's own host, and the replacement is opened, labelled, commented on and closed on
   that forge.

## Where to change
- `vibey_gh/pr_automation.py` (`edit_file` only, never `write_file`): `mirror_fork` only
  (676-761 at `4317cff6`; child lane `split-342-2-pr-automation` has shifted the lines, so find
  it by `def mirror_fork`).
- Tests: `test/test_pr_automation.py`: `test_mirror_fork_success_and_failures` (659-694 at
  `4317cff6`; find it by name) and one new test appended at the end.
- Once the edits are in, format the touched files once from `src/vibey_tools/gh`:
  `python -m black --line-length 100 vibey_gh/pr_automation.py test/test_pr_automation.py` then
  `isort vibey_gh/pr_automation.py test/test_pr_automation.py`; then run the check block. If `ruff format --check` still
  disagrees on a line, restructure that line (C8); never alternate formatters.
- No new class, so no new interface.

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -c '"gh"' vibey_gh/pr_automation.py` prints `0`.
- [ ] `grep -n 'https://github.com/{owner}' vibey_gh/pr_automation.py` prints nothing.
- [ ] `grep -n 'setattr(pa, "fetch_pr"' test/test_pr_automation.py` prints nothing, and
  `grep -c 'monkeypatch.setattr' test/test_pr_automation.py` is exactly 3 lower than before this
  lane (the three `fetch_pr` patches go; the two `subprocess.run` patches that drive git stay,
  and no new patch is added).
- [ ] `test/test_gh_cli.py`'s mirror-fork test (it replaces `pr_automation.mirror_fork` by name)
  passes unmodified.
- [ ] `python -m pytest -q` passes at 100% line and branch coverage of `vibey_gh`; black, isort,
  mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
All in `test/test_pr_automation.py`; `RecordingForge` is already imported (child lane
`split-342-2-pr-automation` added it). The `git fetch`/`git push` calls stay on the existing
`subprocess.run` fake until a git seam exists; this lane adds no new patch.

**Replace `test_mirror_fork_success_and_failures` in place with:**
```python
def test_mirror_fork_success_and_failures(monkeypatch, tmp_path):
    fork = pr(
        author={"login": "alice"},
        headRepositoryOwner={"login": "alice"},
        headRepository={"name": "fork"},
    )
    url = "https://forge.example/alice/fork.git"

    def forge_for(facts, created=(44, "")):
        return RecordingForge(
            change_request_with_thread=(facts, ""),
            fork_clone_url=(url, ""),
            create_change_request=created,
            add_label=(True, ""),
            comment_on_change_request=(True, ""),
            close_change_request=(True, ""),
        )

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: calls.append(args) or completed())
    forge = forge_for(fork)
    result = pa.mirror_fork(12, cfg(tmp_path), forge=forge)
    assert result["replacement_pr"] == 44
    assert ["git", "fetch", "--quiet", url, "abc"] in calls
    branch = "vibey-gh/repair/pr-12-abc"
    body = (
        "Repository-owned repair continuation of #12 from @alice.\n\n"
        "Original head: `abc`. The original contributor retains attribution; this branch "
        "exists only because privileged automation cannot write to a contributor fork."
    )
    note = (
        "Repairs continue in #44; closing this fork PR only after preserving its exact head "
        "and attribution."
    )
    opened = (
        "create_change_request",
        ("base", "develop"),
        ("body", body),
        ("head", branch),
        ("title", "Repair #12: change"),
    )
    expected = [
        ("fork_clone_url", "alice", "fork"),
        opened,
        ("add_label", 44, pa.EXTERNAL_REPAIR_LABEL),
        ("comment_on_change_request", 12, note),
        ("close_change_request", 12),
    ]
    skipped = {"repository_name", "change_request_with_thread"}
    assert [call for call in forge.calls if call[0] not in skipped] == expected

    nameless = forge_for(pr(headRepositoryOwner={}, headRepository={}))
    with pytest.raises(RuntimeError, match="does not expose"):
        pa.mirror_fork(12, cfg(tmp_path), forge=nameless)

    for failure, message, created in (
        ("fetch", "fetch fork", (44, "")),
        ("push", "publish", (44, "")),
        ("create", "could not open replacement pull request: no", (None, "no")),
    ):

        def fail(args, failure=failure, **kwargs):
            return completed(1, err="no") if failure in " ".join(args) else completed()

        monkeypatch.setattr(subprocess, "run", fail)
        with pytest.raises(RuntimeError, match=message):
            pa.mirror_fork(12, cfg(tmp_path), forge=forge_for(fork, created))
```
The `expected` list has no `for_repository` entry: the mirror's forge calls stay unbound. For the
`"create"` case no git argv contains `create`, so both git calls succeed and the forge's
`(None, "no")` answer is what fails.

**New test (append at the end of the file):**
```python
def test_mirror_fork_asks_the_forge_for_the_clone_url_first(tmp_path):
    fork = pr(headRepositoryOwner={"login": "alice"}, headRepository={"name": "fork"})
    forge = RecordingForge(
        change_request_with_thread=(fork, ""),
        fork_clone_url=("", "the change request names no fork repository"),
    )
    with pytest.raises(RuntimeError) as raised:
        pa.mirror_fork(12, cfg(tmp_path), forge=forge)
    assert str(raised.value) == "the change request names no fork repository"
    assert ("fork_clone_url", "alice", "fork") in forge.calls
    assert not any(call[0] == "for_repository" for call in forge.calls)
```
It raises before any git command runs, so it needs no `subprocess.run` fake; every write verb is
unscripted, so reaching one would raise `AttributeError`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_pr_automation.py test/test_gh_cli.py
python -c "import vibey_gh.pr_automation, vibey_gh.cli, vibey_gh.forge_selector"
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
`src/vibey_tools/gh/vibey_gh/pr_automation.py` and `src/vibey_tools/gh/test/test_pr_automation.py`.
Nothing here is platform-specific: run the same block on macOS and on Arch Linux (8.h); CI's
`tools` job reruns it on Linux.

## Out of scope
- Every other function in `pr_automation.py` (child lanes `split-342-1-state-comment` and
  `split-342-2-pr-automation`), `install.py` (child lane `split-342-4-install-notices`).
- A git seam for `git fetch`/`git push`: the existing `subprocess.run` fake that drives them
  stays until a later lane gives git a declared seam.
- `vibey_gh/cli.py`, every adapter file (`forge_*.py`, `interfaces/`), `test/forge_doubles.py`,
  `test/test_gh_cli.py`.
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
`()`, `frozenset()`, `False`, `""`) and `problem` is one sentence. No verb raises for a failed
call, a missing client, a non-2xx status or unreadable output
(`vibey_gh/interfaces/forge_adapter_interface.py:9-16`). A verb a forge has no equivalent for
answers `(<empty>, NotSupported(kind, verb, reason).problem)`, whose text is
`f"{kind.value} does not support {verb}: {reason}"`; the caller reports it like any other
problem (10.f).

**C6 — how this module calls the adapter.**
1. Obtain: `mirror_fork` gains a keyword-only last parameter
   `forge: ForgeAdapterInterface | None = None` and starts with
   `forge = ForgeSelector().resolve(forge, cfg)`. `resolve(forge, cfg=None)` returns the injected
   `forge` when it is not `None`, else `self.select(cfg)` when `cfg` is given, else
   `self.select(load_config())`. Pass `forge=forge` to `fetch_pr`.
2. No binding here: today's mirror never called `github_state.repository()` and passed no
   `--repo`, so every verb runs on the unbound adapter.
3. A site that raised keeps raising, with its prefix; a site that ignored a result keeps
   ignoring it.

**V — the adapter verbs this lane calls** (all declared on `ForgeAdapterInterface` by wave 1).
- `change_request_with_thread(self, number: int) -> tuple[dict[str, Any] | None, str]`
  (through `fetch_pr`, which raises `RuntimeError(problem)` on a problem): the pull request with
  the keys `mirror_fork` reads, including `headRefOid`, `baseRefName`, `title`, `author`
  (`{"login"}`), `headRepository` (`{"name"}`) and `headRepositoryOwner` (`{"login"}`, with
  empty strings when the forge does not know them).
- `fork_clone_url(self, owner: str, name: str) -> tuple[str, str]`. An empty owner or name →
  `("", "the change request names no fork repository")`. GitHub:
  `f"https://github.com/{owner}/{name}.git"` (today's literal). Forgejo/GitLab:
  `f"https://{self.host}/{owner}/{name}.git"` on the forge's configured host.
- `create_change_request(self, *, base: str, head: str, title: str, body: str) -> tuple[int |
  None, str]`. GitHub: `pr create [--repo <R>] --base <base> --head <head> --title <title>
  --body <body>`; a non-zero exit → `(None, <stripped stderr>)`; the number is the digits of the
  last `/`-separated part of the printed URL, and none → ``(None, "`gh pr create` printed no
  pull request number")``. Forgejo: POST `repos/{R}/pulls`; GitLab: POST
  `projects/{P}/merge_requests`; each answers the new number or `(None, <sentence>)`.
- `add_label(self, number: int, label: str) -> tuple[bool, str]`. GitHub:
  `pr edit <n> [--repo <R>] --add-label <label>`. Forgejo: POST `repos/{R}/issues/{n}/labels`;
  GitLab: PUT the merge request with `{"add_labels": label}`.
- `comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]`. GitHub:
  `pr comment <n> [--repo <R>] --body <body>`. Forgejo: POST `repos/{R}/issues/{n}/comments`;
  GitLab: POST `projects/{P}/merge_requests/{n}/notes`.
- `close_change_request(self, number: int) -> tuple[bool, str]`. GitHub: `pr close <n> [--repo
  <R>]`. Forgejo: PATCH the pull with `{"state": "closed"}`; GitLab: PUT with
  `{"state_event": "close"}`.
- On an unbound GitHub adapter (the mirror's case) `[--repo <R>]` is absent, so every argv is
  today's.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`).
  Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never add a `monkeypatch.setattr` of a
  module or class attribute (`pa.fetch_pr`, a module function), never `mock.patch`, `MagicMock`
  or `AsyncMock`. The existing `subprocess.run` fake that drives git is the one tolerated
  residue, and it is not multiplied.
- `RecordingForge` (`test/forge_doubles.py`, import with `from forge_doubles import
  RecordingForge`) is the in-memory fake of `ForgeAdapterInterface`. It is scripted per verb by
  keyword: `RecordingForge(add_label=(True, ""), ...)`. Each scripted verb returns its value,
  or, when the value is callable, calls it with the verb's own arguments and returns what it
  returns. `repository_name()` defaults to `("o/r", "")`. `for_repository(name)` records the
  call and returns the same double. `.calls` lists `(verb, *args, *sorted(kwargs.items()))`, so
  `create_change_request(base="develop", head=b, title=t, body=x)` is recorded as
  `("create_change_request", ("base", "develop"), ("body", x), ("head", b), ("title", t))`. An
  unscripted verb raises `AttributeError`. Whether `repository_name` itself appears in `.calls`
  is the double's business: every assertion in this spec filters it out or looks for specific
  entries.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch
  `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
and the root `ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
comparisons to a local before asserting; no implicit string concatenation that would fit on one
line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters fight over a line, restructure the line; never alternate.

**Depends on:** split-342-2-pr-automation, split-335-1-create-edit-merge, split-335-2-ready-close-comment, split-335-3-labels
- split-342-2-pr-automation: `fetch_pr(number, *, forge=None)`, the `ForgeSelector` import in `pr_automation.py`, and the `RecordingForge` import in `test/test_pr_automation.py` (same files, so it lands first).
- split-335-1-create-edit-merge: `create_change_request(*, base, head, title, body)`.
- split-335-2-ready-close-comment: `fork_clone_url(owner, name)`, `comment_on_change_request(number, body)` and `close_change_request(number)`.
- split-335-3-labels: `add_label(number, label)`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
