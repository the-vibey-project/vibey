<!-- split of #335: child 3 of 3; audit: issue-audit/updates/335.md -->

## Title
feat(gh): the forge adapter adds, removes and creates labels

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`)
and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). The
merge train, PR automation and issue automation label pull requests and create labels with raw
`gh`: `vibey_gh/merge_train.py:93-105` (`pr edit N --add-label L`, then `label create L --color
D93F0B --description …` and a retry), `vibey_gh/pr_automation.py:734-739` (`pr edit N
--add-label`), `vibey_gh/pr_automation.py:634-647` (`pr edit N --repo R --remove-label L`), and
`vibey_gh/pr_automation.py:651-673` and `vibey_gh/issue_automation.py:383-399`
(`label create NAME --color C --description D --force`). vibey-gh ADR 0001
(`docs/adr/0001-forge-neutral-nouns.md:57-63`): each verb answers `(value, problem)` and arrives
with its first caller; this lane adds the three label verbs so parts 1, 4 and 5 can move off `gh`.

## Required behaviour
Every path in this spec is relative to `src/vibey_tools/gh/` (package `vibey_gh`). Every verb
returns `tuple[bool, str]`, answers `(False, problem)` on any transport or client problem, and
never raises. Forgejo is the default adapter (8.b): implement and test it first. `{R}` =
`self._repository()` (Forgejo), `{P}` = `self._project()` (GitLab). A label colour is given as six
hex digits without `#` (`"D93F0B"`), as `gh` takes it; Forgejo and GitLab are sent `f"#{colour}"`.

1. `vibey_gh/interfaces/forge_adapter_interface.py` declares, in a new block headed
   `    # --- Labels ---` placed at the end of the Protocol class (after the last declaration):
   ```python
       # --- Labels ---

       def add_label(self, number: int, label: str) -> tuple[bool, str]:
           """Attach the label `label` to a change request, and a problem."""
           ...

       def remove_label(self, number: int, label: str) -> tuple[bool, str]:
           """Detach the label `label` from a change request, and a problem."""
           ...

       def create_label(
           self, name: str, *, colour: str, description: str, update_existing: bool
       ) -> tuple[bool, str]:
           """Create a label, or update an existing one only when asked, and a problem."""
           ...
   ```
2. `add_label(self, number: int, label: str) -> tuple[bool, str]`:
   - Forgejo: `self._sent(f"repos/{R}/issues/{number}/labels", "POST", {"labels": [label]})`.
   - GitLab: `self._sent(f"projects/{P}/merge_requests/{number}", "PUT", {"add_labels": label})`.
   - GitHub:
     `self._acted(self._scoped(["pr", "edit", str(number)], ["--add-label", label]), "gh pr edit")`.
3. `remove_label(self, number: int, label: str) -> tuple[bool, str]`:
   - Forgejo:
     ```python
         def remove_label(self, number: int, label: str) -> tuple[bool, str]:
             label_id, problem = self._label_id(label)
             if problem:
                 return False, problem
             if label_id is None:
                 return True, ""
             path = f"repos/{self._repository()}/issues/{number}/labels/{label_id}"
             return self._sent(path, "DELETE", None)
     ```
     A label the repository does not have is already absent from the change request, so it
     answers `(True, "")` with no DELETE.
   - GitLab:
     `self._sent(f"projects/{P}/merge_requests/{number}", "PUT", {"remove_labels": label})`.
   - GitHub:
     `self._acted(self._scoped(["pr", "edit", str(number)], ["--remove-label", label]), "gh pr edit")`.
4. `create_label(self, name: str, *, colour: str, description: str, update_existing: bool) -> tuple[bool, str]`:
   - Forgejo:
     ```python
         def create_label(
             self, name: str, *, colour: str, description: str, update_existing: bool
         ) -> tuple[bool, str]:
             label_id, problem = self._label_id(name)
             if problem:
                 return False, problem
             fields = {"color": f"#{colour}", "description": description}
             if label_id is None:
                 return self._sent(
                     f"repos/{self._repository()}/labels", "POST", {"name": name, **fields}
                 )
             if not update_existing:
                 return False, f"label {name!r} already exists"
             return self._sent(f"repos/{self._repository()}/labels/{label_id}", "PATCH", fields)
     ```
   - The Forgejo lookup, a new private method used by both:
     ```python
         def _label_id(self, name: str) -> tuple[int | None, str]:
             rows, problem = self._pages(f"repos/{self._repository()}/labels")
             if problem:
                 return None, problem
             for row in rows:
                 if row.get("name") == name and isinstance(row.get("id"), int):
                     return row["id"], ""
             return None, ""
     ```
   - GitLab:
     ```python
         def create_label(
             self, name: str, *, colour: str, description: str, update_existing: bool
         ) -> tuple[bool, str]:
             fields = {"color": f"#{colour}", "description": description}
             created, problem = self._sent(
                 f"projects/{self._project()}/labels", "POST", {"name": name, **fields}
             )
             if created:
                 return True, ""
             if update_existing and problem.startswith("GitLab API error 409"):
                 path = f"projects/{self._project()}/labels/{quote(name, safe='')}"
                 return self._sent(path, "PUT", fields)
             return False, problem
     ```
     (`quote` is already imported in `forge_gitlab.py`.) A 409 without `update_existing`, or any
     other problem, answers `(False, problem)` unchanged.
   - GitHub, today's argv (`pr_automation.py:659-670`):
     ```python
         def create_label(
             self, name: str, *, colour: str, description: str, update_existing: bool
         ) -> tuple[bool, str]:
             args = self._scoped(
                 ["label", "create", name], ["--color", colour, "--description", description]
             )
             if update_existing:
                 args += ["--force"]
             return self._acted(args, "gh label create")
     ```
5. No consumer changes: `merge_train.py`, `pr_automation.py` and `issue_automation.py` move in
   parts 1, 4 and 5.

## Where to change
The protocol change forces all three adapters to change in the same lane (they subclass it).
- `vibey_gh/interfaces/forge_adapter_interface.py`: append the `# --- Labels ---` block to the end
  of the file (the Protocol class is its last statement) with a heredoc.
- `vibey_gh/forge_forgejo.py`: append `add_label`, `remove_label`, `create_label` and `_label_id`
  to the end of the file.
- `vibey_gh/forge_gitlab.py`: append `add_label`, `remove_label` and `create_label`.
- `vibey_gh/forge_github.py`: append `add_label`, `remove_label` and `create_label`.
- Appending: each class is its module's last statement, so append with `edit_file` (the lane's `shell` tool takes an argv list, so a shell heredoc cannot run): `old_string` is the file's last three lines copied exactly from `read_file`, and `new_string` is those same lines followed by the new code;
  (four-space indentation, eight inside a method, starting with one blank line) appends into the
  class. Then run
  `python -m black --line-length 100 vibey_gh/forge_github.py vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py vibey_gh/interfaces/forge_adapter_interface.py test/test_forge_labels.py`
  and `isort` on the same files once. Read only slices (`sed -n 'a,bp'`, `tail -n 60`); never
  rewrite a module; never `write_file` an existing file.
- `test/test_forge_labels.py` (new), starting with the provenance header line copied from line 1
  of `vibey_gh/forge.py` and a one-line docstring.

## Acceptance criteria
- [ ] `python -m pytest -q --no-cov test/test_forge_labels.py test/test_forge_adapters.py` passes.
- [ ] `test_github_label_argvs_are_todays` pins `pr edit 5 --add-label L`,
      `pr edit 5 --repo o/r --remove-label L`, and `label create held --color D93F0B --description
      …` with and without `--force`, unbound and bound, each with `cwd == str(tmp_path.resolve())`.
- [ ] `test_forgejo_labels_are_looked_up_by_name` asserts that no write is sent when a label is
      absent (remove) or present without `update_existing` (create).
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`.
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are clean (block below).
- [ ] `git diff --stat` lists only the five files named under "Where to change".

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` an import or a module/class
attribute, never `mock.patch`, `MagicMock` or `AsyncMock`.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`), a real `gh` put first on
  `PATH`. `fake_gh.script({"<argv joined by single spaces>": {"out": ..., "err": ..., "code":
  ...}})` replaces every answer; unscripted argv exits 3. `fake_gh.invocations()` lists
  `{"argv": [...], "cwd": ..., "stdin": None}` per call; `fake_gh.forget()` clears the records.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py`
  (`from forge_doubles import RoutedTransport`); keys `"<path>"` for a GET and
  `"<path> <METHOD>"` otherwise; every `args` tuple is recorded in `.calls`; an unrouted key
  answers `([], "no route for <key>")`. Read `sed -n '1,80p' test/forge_doubles.py` first and
  build it the way its constructor takes the route table (a dict of key → `(value, problem)`,
  written below as `RoutedTransport(routes)`). Forgejo's `_pages` adds `page=N&limit=50` and stops
  at an empty page, so route `"repos/o/r/labels?page=1&limit=50"` to the listing and
  `"repos/o/r/labels?page=2&limit=50"` to `([], "")`. Assert JSON bodies with
  `json.loads(call[2])`. Adapters: `ForgejoForge(root=tmp_path, repository="o/r", transport=t)`,
  `GitLabForge(root=tmp_path, repository="o/r", transport=t)` (`{P}` is `o%2Fr`).

`test/test_forge_labels.py`:
- `test_forgejo_add_label_posts_the_name(tmp_path)`: route `"repos/o/r/issues/5/labels POST"` →
  `([{"id": 17, "name": "held"}], "")`; `add_label(5, "held") == (True, "")` with body
  `{"labels": ["held"]}`.
- `test_forgejo_labels_are_looked_up_by_name(tmp_path)`: label listing
  `[{"id": "x", "name": "held"}, {"id": 17, "name": "held"}, {"id": 18, "name": "other"}]`.
  - `remove_label(5, "held")` → `(True, "")`, with the call
    `("repos/o/r/issues/5/labels/17", "DELETE", "")` routed as
    `"repos/o/r/issues/5/labels/17 DELETE"` → `({}, "")`;
  - `remove_label(5, "missing")` → `(True, "")` and no DELETE recorded;
  - `create_label("held", colour="D93F0B", description="Outside contribution",
    update_existing=True)` → PATCH `"repos/o/r/labels/17"` with body
    `{"color": "#D93F0B", "description": "Outside contribution"}`;
  - the same with `update_existing=False` → `(False, "label 'held' already exists")` and no write;
  - `create_label("fresh", colour="5319E7", description="New", update_existing=False)` → POST
    `"repos/o/r/labels"` with body `{"name": "fresh", "color": "#5319E7", "description": "New"}`.
- `test_gitlab_labels_route_and_retry_a_conflict_only_when_asked(tmp_path)`:
  - `add_label(5, "held")` → PUT `"projects/o%2Fr/merge_requests/5"` with body
    `{"add_labels": "held"}`; `remove_label(5, "held")` → the same route with
    `{"remove_labels": "held"}`;
  - `create_label("needs review", colour="D93F0B", description="D", update_existing=False)` with
    `"projects/o%2Fr/labels POST"` → `({"id": 3}, "")` answers `(True, "")` and sends
    `{"name": "needs review", "color": "#D93F0B", "description": "D"}`;
  - with the POST answering `([], "GitLab API error 409: Conflict")` and `update_existing=True`,
    it PUTs `"projects/o%2Fr/labels/needs%20review"` with `{"color": "#D93F0B", "description":
    "D"}` and answers `(True, "")`;
  - the same 409 with `update_existing=False` → `(False, "GitLab API error 409: Conflict")`, no
    PUT;
  - a POST answering `([], "GitLab API error 403: Forbidden")` with `update_existing=True` →
    `(False, "GitLab API error 403: Forbidden")`, no PUT.
- `test_github_label_argvs_are_todays(fake_gh, tmp_path, bound)`, parametrised
  `bound in (False, True)`; the adapter is `GitHubForge(root=tmp_path, repository="o/r" if bound
  else "")`, `scope = ["--repo", "o/r"] if bound else []`:
  - `add_label(5, "L")` runs `["pr", "edit", "5", *scope, "--add-label", "L"]`;
  - `remove_label(5, "L")` runs `["pr", "edit", "5", *scope, "--remove-label", "L"]`;
  - `create_label("held", colour="D93F0B", description="Outside contribution awaiting the code owner", update_existing=False)`
    runs `["label", "create", "held", *scope, "--color", "D93F0B", "--description", "Outside contribution awaiting the code owner"]`;
    with `update_existing=True` the same argv ends with `"--force"`;
  - each with code 0 answers `(True, "")`; code 1 with err `denied` answers `(False, "denied")`;
    code 1 with no output answers ``"`gh pr edit` exited 1"`` or ``"`gh label create` exited 1"``.
  Bind long argv lists and expected values to locals before asserting (C8).
- `test_every_label_verb_passes_a_problem_through(kind, verb, tmp_path)`, parametrised over
  `kind` in `("forgejo", "gitlab", "github")` and `verb` in `("add", "remove", "create")`:
  Forgejo/GitLab with a `RoutedTransport` that has no routes, GitHub with
  `GitHubForge(root=tmp_path, transport=GhTransport(executable="gh-not-installed"))`
  (`from vibey_gh.gh_transport import GhTransport`). Calls: `add_label(5, "L")`,
  `remove_label(5, "L")`, `create_label("L", colour="D93F0B", description="D",
  update_existing=True)`. Each answers `False` with a problem that equals
  ``"the GitHub CLI (`gh-not-installed`) is not installed"`` (GitHub) or starts with
  `"no route for "` (Forgejo, GitLab).

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_labels.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the five files named under "Where to change"
```

## Out of scope
- Every other verb (split-335-1, split-335-2, already merged).
- `merge_train.py`, `pr_automation.py`, `issue_automation.py` and every other consumer module
  (parts 1, 4 and 5). The label names, colours and descriptions stay with their callers.
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_forge_adapters.py`,
  `test/test_forge_github.py` (never edit them).
- `.vibey-gh.toml` and its `[platform] kind = "github"` declaration: never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  (this spec's title) when done.

## Conventions this lane relies on (everything needed is here)
**C1, the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when
the forge answered; otherwise `value` is `False` and `problem` is one sentence. No verb raises for
a failed call, a missing client, a non-2xx status or unreadable output (vibey-gh ADR 0001).

**C2, GitHub argv fidelity.** The GitHub argv is today's call site's, byte for byte. `[scope]` is
`["--repo", self.repository]` when bound and nothing otherwise, right after the subcommand's
positional argument (`pr edit 5 [scope] --add-label …`, `label create NAME [scope] --color …`).
Every call runs with `cwd=self.root`.

**Helpers already on the branch (do not re-add them):**
- `GitHubForge._scoped(self, head: list[str], tail: list[str]) -> list[str]` =
  `head + (["--repo", self.repository] if self.repository else []) + tail`.
- `GitHubForge._acted(self, args: list[str], label: str) -> tuple[bool, str]` (split-335-2): runs
  `self._run(args)`; `None` → `(False, <not-installed problem>)`; rc 0 → `(True, "")`; else
  `(False, self._failed(run, label))`, which is the stripped stderr or ``"`<label>` exited <rc>"``.
- `ForgejoForge._sent` / `GitLabForge._sent(self, path: str, method: str, payload: dict[str, Any] | None) -> tuple[bool, str]`
  (split-335-2): sends `json.dumps(payload)` (or `""` for `None`) as
  `self.transport.survey([path, method, body], cwd=self.root)`; `(True, "")` or
  `(False, problem)`.
- `ForgejoForge._pages(self, path: str, *, most: int | None = None) -> tuple[list[dict[str, Any]], str]`
  (split-332-2): walks `page=N&limit=50` until an empty page, keeps dict items only, answers
  `([], problem)` on any problem.
- `ForgejoForge._repository()` = `quote(self.repository, safe="/")`;
  `GitLabForge._project()` = `quote(self.repository, safe="")`.
- Transports: a failure answers `([], problem)`; GitLab's HTTP error sentence is
  `"GitLab API error <code>: <reason>"`; a 2xx with an empty body answers `({}, "")`.

**C7, tests.** 100% line and branch coverage of all of `vibey_gh`; focused runs need `--no-cov`.

**C8, the formatter trap.** black + isort and root `ruff format` must both be clean: lines at or
under 100 columns (95 for nested calls); bind long expected values to a local before the
`assert`; no implicit string concatenation; multi-line calls one argument per line with a
trailing comma; no backslash continuations. If they fight, restructure the line.

**C9, the big files.** Append with a heredoc, run black once, read only slices, never rewrite a
module.

**Depends on:** split-335-2-ready-close-comment
- split-335-2-ready-close-comment: `GitHubForge._acted` and `ForgejoForge._sent` / `GitLabForge._sent`, and the adapter files at their latest state. #336's lanes depend on this lane.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
