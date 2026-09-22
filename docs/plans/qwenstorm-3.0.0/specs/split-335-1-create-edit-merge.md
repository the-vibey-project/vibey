<!-- split of #335: child 1 of 3; audit: issue-audit/updates/335.md -->

## Title
feat(gh)!: the forge adapter creates, edits and merges change requests

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`,
`src/vibey_tools/gh/vibey_gh/config.py:288`), and every forge call must go through
`ForgeAdapterInterface` (`docs/doctrines.md:168-176`). The merge train and promotion create, edit
and merge pull requests with raw `gh`: `vibey_gh/promote.py:103-127` and
`vibey_gh/pr_automation.py:712-733` (`pr create`), `vibey_gh/promote.py:331-354` (`pr edit`, with a
REST fallback for Projects-classic refusals), `vibey_gh/merge_train.py:378-388` and
`vibey_gh/promote.py:136-142` (`pr merge`, then `--admin`). The adapter's existing
`update_change_request` and `merge_change_request` cannot stand in: on GitHub they go through
`survey`, which demands JSON, but `gh pr edit/merge` print a URL or nothing, so each reports
failure after succeeding (`vibey_gh/forge_github.py:231-253`), and they use `-t`/`-b` where
today's callers use `--title`/`--body`; Forgejo merge sends no `Do` field
(`vibey_gh/forge_forgejo.py:218-227`); GitLab merge uses POST where the API takes PUT
(`vibey_gh/forge_gitlab.py:230-241`). Neither verb has a caller yet, so both are reshaped to what
their first callers need (vibey-gh ADR 0001, `docs/adr/0001-forge-neutral-nouns.md:57-63`: a verb
arrives with its first caller). The `!` is because two `ForgeAdapterInterface` signatures change;
neither has a caller outside the adapters and their tests.

## Required behaviour
Every path in this spec is relative to `src/vibey_tools/gh/` (package `vibey_gh`).

Conventions:
- Every verb answers `(value, problem)` and never raises. `problem` is `""` exactly when the forge
  answered.
- Forgejo is the default adapter (8.b): implement and test it first.
- A verb a forge has no equivalent for answers `(False, NotSupported(kind, verb, reason).problem)`.
  `NotSupported` is in `vibey_gh.forge` (split-332-1); its `problem` is
  `f"{kind.value} does not support {verb}: {reason}"`.
- Forgejo `{R}` = `self._repository()`, GitLab `{P}` = `self._project()`.
- Mutation bodies are always `json.dumps(payload)`, sent as
  `self.transport.survey([path, METHOD, body], cwd=self.root)`.

In `vibey_gh/interfaces/forge_adapter_interface.py`, add the first verb and **replace** the two old
signatures. Implement all three on every adapter.

1. `create_change_request(self, *, base: str, head: str, title: str, body: str) -> tuple[int | None, str]`
   - Forgejo: POST `repos/{R}/pulls` with `{"base": base, "head": head, "title": title, "body":
     body}`. A transport problem → `(None, problem)`. An answer dict with an int `number` →
     `(number, "")`; anything else →
     `(None, "Forgejo opened a pull request but did not answer its number")`.
   - GitLab: POST `projects/{P}/merge_requests` with `{"source_branch": head, "target_branch":
     base, "title": title, "description": body}`. A problem → `(None, problem)`. An int `iid` →
     `(iid, "")`; anything else →
     `(None, "GitLab opened a merge request but did not answer its number")`.
   - GitHub:
     `run, problem = self._run(self._scoped(["pr", "create"], ["--base", base, "--head", head, "--title", title, "--body", body]))`.
     - `run is None` → `(None, problem)`;
     - rc ≠ 0 → `(None, self._failed(run, "gh pr create"))`;
     - `digits = "".join(c for c in (run.stdout or "").strip().rsplit("/", 1)[-1] if c.isdigit())`,
       the rule at `promote.py:126-127` → `(int(digits), "")`;
     - no digits → ``(None, "`gh pr create` printed no pull request number")``.
2. `update_change_request(self, number: int, *, title: str, body: str) -> tuple[bool, str]`
   - Forgejo: PATCH `repos/{R}/pulls/{n}` with `{"title": title, "body": body}` → `(True, "")`,
     or `(False, problem)`.
   - GitLab: PUT `projects/{P}/merge_requests/{n}` with `{"title": title, "description": body}` →
     `(True, "")`, or `(False, problem)`.
   - GitHub, byte-identical to `promote.py:331-354` and `:391-396`:
     ```python
         def update_change_request(
             self, number: int, *, title: str, body: str
         ) -> tuple[bool, str]:
             run, problem = self._run(
                 self._scoped(["pr", "edit", str(number)], ["--title", title, "--body", body])
             )
             if run is None:
                 return False, problem
             if run.returncode == 0:
                 return True, ""
             detail = self._collapsed(run, "gh pr edit")
             if not _PROJECTS_CLASSIC.search(detail):
                 return False, detail
             # `{owner}` and `{repo}` are gh's own placeholders, filled from the clone at `root`
             # exactly as `gh pr edit` resolved it; no `--repo` here, as today.
             patch, problem = self._run(
                 [
                     "api",
                     f"repos/{{owner}}/{{repo}}/pulls/{number}",
                     "--method",
                     "PATCH",
                     "-f",
                     f"title={title}",
                     "-f",
                     f"body={body}",
                 ]
             )
             if patch is not None and patch.returncode == 0:
                 return True, ""
             fallback = self._collapsed(patch, "gh api") if patch is not None else problem
             return False, f"{detail}; the REST fallback failed too — {fallback}"

         @staticmethod
         def _collapsed(run: subprocess.CompletedProcess[str], label: str) -> str:
             text = " ".join(((run.stderr or run.stdout) or "").split())[:300]
             return text or f"{label} exited {run.returncode}"
     ```
     So: rc 0 → `(True, "")`; otherwise `detail` is stderr (else stdout) with all whitespace
     runs collapsed to single spaces, cut to 300 characters, or `"gh pr edit exited <rc>"` when
     empty (no backticks: this is promote's `_detail` text). If `_PROJECTS_CLASSIC` does not match
     `detail` → `(False, detail)`. If it matches → the REST `api … --method PATCH -f title=… -f
     body=…` call with the literal `{owner}/{repo}` placeholders and no scope; rc 0 →
     `(True, "")`; else `(False, f"{detail}; the REST fallback failed too — {detail2}")`, where
     `detail2` is built the same way labelled `"gh api"` (the dash is an em dash, U+2014, with a
     space either side). Before adding `_collapsed`, run
     `grep -n "def _collapsed\|\[:300\]" vibey_gh/forge_github.py`: if split-333-3 already added a
     static helper with exactly this behaviour, reuse it under its existing name instead of adding
     a second one.
   - `_PROJECTS_CLASSIC` is copied to the top of `forge_github.py` from `promote.py:52`, placed
     after the `GH_DEFAULT_HOST = "github.com"` line, with `import re` added to the stdlib imports:
     ```python
     # `gh pr edit` reads the pull request over GraphQL first, and a gh old enough to still ask
     # for `projectCards` is refused outright now that Projects (classic) is sunset. The REST
     # endpoint asks for no such field. Part 2 of the wave deletes promote's copy.
     _PROJECTS_CLASSIC = re.compile(r"projects \(classic\)|projectcards", re.IGNORECASE)
     ```
3. `merge_change_request(self, number: int, *, method: str, commit_body: str | None = None, bypass_rules: bool = False) -> tuple[bool, str]`
   - Forgejo:
     - a `method` outside `{"squash", "rebase", "merge"}` →
       `(False, f"Forgejo cannot merge with method {method!r}")`, with no request;
     - else POST `repos/{R}/pulls/{n}/merge` with `{"Do": method, "force_merge": bypass_rules}`,
       plus `"MergeMessageField": commit_body` when it is not `None` → `(True, "")` or
       `(False, problem)`.
   - GitLab, checked in this order, each refusal with no request:
     - `method == "rebase"` → `(False, NotSupported(ForgeKind.GITLAB, "merge_change_request(method='rebase')", "GitLab sets the merge method per project, not per merge").problem)`,
       that is `"gitlab does not support merge_change_request(method='rebase'): GitLab sets the merge method per project, not per merge"`;
     - `bypass_rules` → `(False, NotSupported(ForgeKind.GITLAB, "merge_change_request(bypass_rules=True)", "GitLab has no per-merge override of approval rules").problem)`,
       that is `"gitlab does not support merge_change_request(bypass_rules=True): GitLab has no per-merge override of approval rules"`;
     - another method outside `{"squash", "merge"}` →
       `(False, f"GitLab cannot merge with method {method!r}")`;
     - else PUT `projects/{P}/merge_requests/{n}/merge` with `{"squash": method == "squash"}`,
       plus `"squash_commit_message": commit_body` (squash) or `"merge_commit_message":
       commit_body` (merge) when `commit_body` is not `None` → `(True, "")` or `(False, problem)`.
   - GitHub: `args = self._scoped(["pr", "merge", str(number)], [f"--{method}"])`, then
     `args += ["--body", commit_body]` when `commit_body is not None`, then `args += ["--admin"]`
     when `bypass_rules`; `run, problem = self._run(args)`; `run is None` → `(False, problem)`;
     rc 0 → `(True, "")`; else `(False, self._failed(run, "gh pr merge", with_stdout=True))`.
     The adapter passes `--body` whenever it is given; the caller decides (the merge train only
     gives it for a squash).
   The Forgejo code (the two replaced methods in place, `create_change_request` appended):
   ```python
       def update_change_request(self, number: int, *, title: str, body: str) -> tuple[bool, str]:
           payload = {"title": title, "body": body}
           _, problem = self.transport.survey(
               [f"repos/{self._repository()}/pulls/{number}", "PATCH", json.dumps(payload)],
               cwd=self.root,
           )
           return (False, problem) if problem else (True, "")

       def merge_change_request(
           self,
           number: int,
           *,
           method: str,
           commit_body: str | None = None,
           bypass_rules: bool = False,
       ) -> tuple[bool, str]:
           if method not in {"squash", "rebase", "merge"}:
               return False, f"Forgejo cannot merge with method {method!r}"
           payload: dict[str, Any] = {"Do": method, "force_merge": bypass_rules}
           if commit_body is not None:
               payload["MergeMessageField"] = commit_body
           _, problem = self.transport.survey(
               [f"repos/{self._repository()}/pulls/{number}/merge", "POST", json.dumps(payload)],
               cwd=self.root,
           )
           return (False, problem) if problem else (True, "")

       def create_change_request(
           self, *, base: str, head: str, title: str, body: str
       ) -> tuple[int | None, str]:
           payload = {"base": base, "head": head, "title": title, "body": body}
           value, problem = self.transport.survey(
               [f"repos/{self._repository()}/pulls", "POST", json.dumps(payload)], cwd=self.root
           )
           if problem:
               return None, problem
           number = value.get("number") if isinstance(value, dict) else None
           if not isinstance(number, int):
               return None, "Forgejo opened a pull request but did not answer its number"
           return number, ""
   ```
   The GitLab code:
   ```python
       def update_change_request(self, number: int, *, title: str, body: str) -> tuple[bool, str]:
           payload = {"title": title, "description": body}
           _, problem = self.transport.survey(
               [f"projects/{self._project()}/merge_requests/{number}", "PUT", json.dumps(payload)],
               cwd=self.root,
           )
           return (False, problem) if problem else (True, "")

       def merge_change_request(
           self,
           number: int,
           *,
           method: str,
           commit_body: str | None = None,
           bypass_rules: bool = False,
       ) -> tuple[bool, str]:
           if method == "rebase":
               refusal = NotSupported(
                   ForgeKind.GITLAB,
                   "merge_change_request(method='rebase')",
                   "GitLab sets the merge method per project, not per merge",
               )
               return False, refusal.problem
           if bypass_rules:
               refusal = NotSupported(
                   ForgeKind.GITLAB,
                   "merge_change_request(bypass_rules=True)",
                   "GitLab has no per-merge override of approval rules",
               )
               return False, refusal.problem
           if method not in {"squash", "merge"}:
               return False, f"GitLab cannot merge with method {method!r}"
           payload: dict[str, Any] = {"squash": method == "squash"}
           if commit_body is not None:
               message = "squash_commit_message" if method == "squash" else "merge_commit_message"
               payload[message] = commit_body
           path = f"projects/{self._project()}/merge_requests/{number}/merge"
           _, problem = self.transport.survey([path, "PUT", json.dumps(payload)], cwd=self.root)
           return (False, problem) if problem else (True, "")

       def create_change_request(
           self, *, base: str, head: str, title: str, body: str
       ) -> tuple[int | None, str]:
           payload = {
               "source_branch": head,
               "target_branch": base,
               "title": title,
               "description": body,
           }
           value, problem = self.transport.survey(
               [f"projects/{self._project()}/merge_requests", "POST", json.dumps(payload)],
               cwd=self.root,
           )
           if problem:
               return None, problem
           number = value.get("iid") if isinstance(value, dict) else None
           if not isinstance(number, int):
               return None, "GitLab opened a merge request but did not answer its number"
           return number, ""
   ```
   The GitHub `create_change_request` (appended) and `merge_change_request` (in place):
   ```python
       def merge_change_request(
           self,
           number: int,
           *,
           method: str,
           commit_body: str | None = None,
           bypass_rules: bool = False,
       ) -> tuple[bool, str]:
           args = self._scoped(["pr", "merge", str(number)], [f"--{method}"])
           if commit_body is not None:
               args += ["--body", commit_body]
           if bypass_rules:
               args += ["--admin"]
           run, problem = self._run(args)
           if run is None:
               return False, problem
           if run.returncode == 0:
               return True, ""
           return False, self._failed(run, "gh pr merge", with_stdout=True)

       def create_change_request(
           self, *, base: str, head: str, title: str, body: str
       ) -> tuple[int | None, str]:
           run, problem = self._run(
               self._scoped(
                   ["pr", "create"],
                   ["--base", base, "--head", head, "--title", title, "--body", body],
               )
           )
           if run is None:
               return None, problem
           if run.returncode != 0:
               return None, self._failed(run, "gh pr create")
           tail = (run.stdout or "").strip().rsplit("/", 1)[-1]
           digits = "".join(c for c in tail if c.isdigit())
           if not digits:
               return None, "`gh pr create` printed no pull request number"
           return int(digits), ""
   ```
4. Delete the old `update_change_request(number, title=None, body=None) -> tuple[ChangeRequest | None, str]`
   and `merge_change_request(number, method="squash", admin=False)` bodies from all three adapters,
   replacing them in place. Remove imports that become unused (ruff reports them as F401).

## Where to change
The protocol change forces all three adapters to change in the same lane (they subclass it).
- `vibey_gh/interfaces/forge_adapter_interface.py`: under `    # --- Mutations ---`, replace this
  exact text (lines 96-109 at integration HEAD `4317cff6`; find it with
  `grep -n "def update_change_request" vibey_gh/interfaces/forge_adapter_interface.py`):
  ```python
      def update_change_request(
          self,
          number: int,
          title: str | None = None,
          body: str | None = None,
      ) -> tuple[ChangeRequest | None, str]:
          """Updates to a change request, and a problem."""
          ...

      def merge_change_request(
          self, number: int, method: str = "squash", admin: bool = False
      ) -> tuple[bool, str]:
          """Merges a change request, and a problem."""
          ...
  ```
  with:
  ```python
      def create_change_request(
          self, *, base: str, head: str, title: str, body: str
      ) -> tuple[int | None, str]:
          """Open a change request from `head` into `base`; its number, and a problem."""
          ...

      def update_change_request(self, number: int, *, title: str, body: str) -> tuple[bool, str]:
          """Replace a change request's title and body, and a problem."""
          ...

      def merge_change_request(
          self,
          number: int,
          *,
          method: str,
          commit_body: str | None = None,
          bypass_rules: bool = False,
      ) -> tuple[bool, str]:
          """Merge a change request by `method`, bypassing rules only when asked, and a problem."""
          ...
  ```
- `vibey_gh/forge_github.py`: replace in place, with one exact `edit_file`, this block (lines
  231-253 at `4317cff6`; find it with `grep -n "def update_change_request" vibey_gh/forge_github.py`)
  with the new `update_change_request` and `merge_change_request`:
  ```python
      def update_change_request(
          self, number: int, title: str | None = None, body: str | None = None
      ) -> tuple[ChangeRequest | None, str]:
          args = ["pr", "edit", str(number)]
          if title:
              args += ["-t", title]
          if body:
              args += ["-b", body]
          _, problem = self.transport.survey(args, cwd=self.root)
          if problem:
              return None, problem
          return self.get_change_request(number)

      def merge_change_request(
          self, number: int, method: str = "squash", admin: bool = False
      ) -> tuple[bool, str]:
          args = ["pr", "merge", str(number), f"--{method}"]
          if admin:
              args += ["--admin"]
          _, problem = self.transport.survey(args, cwd=self.root)
          if problem:
              return False, problem
          return True, ""
  ```
  Append `create_change_request` and (unless reused) `_collapsed` to the end of the file. Add
  `import re` and `_PROJECTS_CLASSIC` at the top. `subprocess` is already imported (split-332-3
  added it for `_run`); confirm with `grep -n "^import" vibey_gh/forge_github.py`.
- `vibey_gh/forge_forgejo.py`: replace in place this block (lines 202-227 at `4317cff6`):
  ```python
      def update_change_request(
          self, number: int, title: str | None = None, body: str | None = None
      ) -> tuple[ChangeRequest | None, str]:
          payload = {}
          if title:
              payload["title"] = title
          if body:
              payload["body"] = body
          _, problem = self.transport.survey(
              [f"repos/{self._repository()}/pulls/{number}", "PATCH", json.dumps(payload)],
              cwd=self.root,
          )
          if problem:
              return None, problem
          return self.get_change_request(number)

      def merge_change_request(
          self, number: int, method: str = "squash", admin: bool = False
      ) -> tuple[bool, str]:
          # Forgejo: POST /repos/{owner}/{repo}/pulls/{id}/merge
          _, problem = self.transport.survey(
              [f"repos/{self._repository()}/pulls/{number}/merge", "POST", ""], cwd=self.root
          )
          if problem:
              return False, problem
          return True, ""
  ```
  Append `create_change_request` to the end of the file.
- `vibey_gh/forge_gitlab.py`: replace in place this block (lines 214-241 at `4317cff6`):
  ```python
      def update_change_request(
          self, number: int, title: str | None = None, body: str | None = None
      ) -> tuple[ChangeRequest | None, str]:
          payload = {}
          if title:
              payload["title"] = title
          if body:
              payload["description"] = body
          _, problem = self.transport.survey(
              [f"projects/{self._project()}/merge_requests/{number}", "PUT", json.dumps(payload)],
              cwd=self.root,
          )
          if problem:
              return None, problem
          return self.get_change_request(number)

      def merge_change_request(
          self, number: int, method: str = "squash", admin: bool = False
      ) -> tuple[bool, str]:
          # GitLab: POST /projects/:id/merge_requests/:iid/merge
          # method: squash is handled via a different API or project setting
          _, problem = self.transport.survey(
              [f"projects/{self._project()}/merge_requests/{number}/merge", "POST", ""],
              cwd=self.root,
          )
          if problem:
              return False, problem
          return True, ""
  ```
  Append `create_change_request` to the end of the file. Add `ForgeKind` and `NotSupported` to
  the module's `from vibey_gh.forge import (…)` list if they are missing, keeping it alphabetical.
  Annotate the merge payload `payload: dict[str, Any] = {...}` (`Any` is already imported).
- If an `edit_file` `old_string` does not match because an earlier lane re-wrapped a line, read
  the method with `sed -n` and copy the current text exactly; never fall back to rewriting a file.
- Appending: each adapter class is its module's last statement, so append with `edit_file` (the lane's `shell` tool takes an argv list, so a shell heredoc cannot run): `old_string` is the file's last three lines copied exactly from `read_file`, and `new_string` is those same lines followed by the new code;
  (four-space indentation, eight inside a method, starting with one blank line) appends into the
  class. Then run
  `python -m black --line-length 100 vibey_gh/forge_github.py vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py vibey_gh/interfaces/forge_adapter_interface.py test/test_forge_change_request_writes.py test/test_forge_adapters.py`
  and `isort` on the same files once. Read only slices (`sed -n 'a,bp'`, `tail -n 60`).
- `test/test_forge_change_request_writes.py` (new), starting with the provenance header line
  copied from line 1 of `vibey_gh/forge.py` and a one-line docstring.
- `test/test_forge_adapters.py`: delete the old-signature assertions from three tests (the new
  file covers the new verbs). With one `edit_file` each, delete exactly:
  - in `test_github_reads_and_writes_every_neutral_verb` (lines 130-139 at `4317cff6`):
    ```python
        update_transport = ScriptedTransport(({}, ""), (change, ""))
        updated, problem = _github(update_transport).update_change_request(7, "New", "Text")
        assert updated is not None and not problem
        assert update_transport.calls[0] == ("pr", "edit", "7", "-t", "New", "-b", "Text")
        no_fields = ScriptedTransport(({}, ""), (change, ""))
        assert _github(no_fields).update_change_request(7) == (updated, "")
        assert _github(ScriptedTransport(([], "denied"))).update_change_request(7) == (None, "denied")

        assert _github(ScriptedTransport(({}, ""))).merge_change_request(7, admin=True) == (True, "")
        assert _github(ScriptedTransport(([], "denied"))).merge_change_request(7) == (False, "denied")
    ```
  - in `test_gitlab_adapter_covers_list_and_mutation_paths` (lines 248-252 at `4317cff6`):
    ```python
        edit = ScriptedTransport(({}, ""), (mr, ""))
        assert _gitlab(edit).update_change_request(7, "Title", "Body")[0].title == "MR"
        assert _gitlab(ScriptedTransport(([], "down"))).update_change_request(7) == (None, "down")
        assert _gitlab(ScriptedTransport(({}, ""))).merge_change_request(7) == (True, "")
        assert _gitlab(ScriptedTransport(([], "down"))).merge_change_request(7) == (False, "down")
    ```
  - in `test_forgejo_adapter_covers_list_and_mutation_paths` (lines 355-359 at `4317cff6`):
    ```python
        edit = ScriptedTransport(({}, ""), (pr, ""))
        assert _forgejo(edit).update_change_request(7, "Title", "Body")[0].title == "PR"
        assert _forgejo(ScriptedTransport(([], "down"))).update_change_request(7) == (None, "down")
        assert _forgejo(ScriptedTransport(({}, ""))).merge_change_request(7) == (True, "")
        assert _forgejo(ScriptedTransport(([], "down"))).merge_change_request(7) == (False, "down")
    ```
  Afterwards `grep -n "update_change_request\|merge_change_request" test/test_forge_adapters.py`
  finds nothing. Touch nothing else in that file.

## Acceptance criteria
- [ ] `python -m pytest -q --no-cov test/test_forge_change_request_writes.py test/test_forge_adapters.py` passes.
- [ ] A `fake_gh` test pins every GitHub argv, unbound and bound
      (`pr create --repo o/r …`, `pr edit 5 --repo o/r …`,
      `pr merge 5 --repo o/r --squash --body B --admin`).
- [ ] GitLab's two NotSupported answers are asserted verbatim
      (`test_gitlab_writes_route_and_refuse_what_gitlab_cannot_do`).
- [ ] `grep -nE 'admin: bool|title: str \| None = None' vibey_gh/forge*.py vibey_gh/interfaces/forge_adapter_interface.py`
      prints nothing.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`.
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are clean (block below).
- [ ] `git diff --stat` lists only the six files named under "Where to change".

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` an import or a module/class
attribute, never `mock.patch`, `MagicMock` or `AsyncMock`.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`), a real `gh` put first on
  `PATH`. `fake_gh.script({"<argv joined by single spaces>": {"out": ..., "err": ..., "code":
  ...}})` replaces every answer; an unscripted argv exits 3 (`no scripted answer`).
  `fake_gh.invocations()` lists `{"argv": [...], "cwd": ..., "stdin": None}` per call;
  `fake_gh.forget()` clears the records. Build `GitHubForge(root=tmp_path)` (unbound) or
  `GitHubForge(root=tmp_path, repository="o/r")` (bound); compare `cwd` with
  `str(tmp_path.resolve())`.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py`
  (`from forge_doubles import RoutedTransport`). Keys are `"<path>"` for a GET and
  `"<path> <METHOD>"` otherwise; every `args` tuple is recorded in `.calls`; an unrouted key
  answers `([], "no route for <key>")`. Read `sed -n '1,80p' test/forge_doubles.py` first and
  build it the way its constructor takes the route table (a dict of key → `(value, problem)`,
  written below as `RoutedTransport(routes)`). Assert a JSON body with `json.loads(call[2])`.
  Build `ForgejoForge(root=tmp_path, repository="o/r", transport=t)` and
  `GitLabForge(root=tmp_path, repository="o/r", transport=t)` (`{P}` is `o%2Fr`).

`test/test_forge_change_request_writes.py`:
- `test_forgejo_writes_route_and_send_json(tmp_path)`: routes `"repos/o/r/pulls POST"` →
  `({"number": 12}, "")`, `"repos/o/r/pulls/5 PATCH"` → `({}, "")`,
  `"repos/o/r/pulls/5/merge POST"` → `({}, "")`.
  - `create_change_request(base="develop", head="topic", title="T", body="B") == (12, "")` with
    body `{"base": "develop", "head": "topic", "title": "T", "body": "B"}`;
  - with the POST answering `({}, "")`, create answers
    `(None, "Forgejo opened a pull request but did not answer its number")`;
  - `update_change_request(5, title="T", body="B") == (True, "")` with body
    `{"title": "T", "body": "B"}`;
  - `merge_change_request(5, method="squash", commit_body="C", bypass_rules=True) == (True, "")`
    with body `{"Do": "squash", "force_merge": True, "MergeMessageField": "C"}`;
    `merge_change_request(5, method="rebase")` sends `{"Do": "rebase", "force_merge": False}`;
  - `merge_change_request(5, method="fast-forward")` on a fresh transport answers
    `(False, "Forgejo cannot merge with method 'fast-forward'")` and `transport.calls == []`.
- `test_gitlab_writes_route_and_refuse_what_gitlab_cannot_do(tmp_path)`: routes
  `"projects/o%2Fr/merge_requests POST"` → `({"iid": 4}, "")`,
  `"projects/o%2Fr/merge_requests/5 PUT"` → `({}, "")`,
  `"projects/o%2Fr/merge_requests/5/merge PUT"` → `({}, "")`.
  - create → `(4, "")` with body `{"source_branch": "topic", "target_branch": "develop",
    "title": "T", "description": "B"}`; answering `({}, "")` →
    `(None, "GitLab opened a merge request but did not answer its number")`;
  - update → `(True, "")` with body `{"title": "T", "description": "B"}`;
  - merge squash with `commit_body="C"` → body `{"squash": True, "squash_commit_message": "C"}`;
    merge `"merge"` with `commit_body="C"` → `{"squash": False, "merge_commit_message": "C"}`;
    merge squash without a body → `{"squash": True}`;
  - on a fresh transport, each with `transport.calls == []`:
    `merge_change_request(5, method="rebase")` answers `(False, "gitlab does not support merge_change_request(method='rebase'): GitLab sets the merge method per project, not per merge")`;
    `merge_change_request(5, method="squash", bypass_rules=True)` answers `(False, "gitlab does not support merge_change_request(bypass_rules=True): GitLab has no per-merge override of approval rules")`;
    `merge_change_request(5, method="fast-forward")` answers
    `(False, "GitLab cannot merge with method 'fast-forward'")`. Bind each expected sentence to a
    local before the `assert` (C8).
- `test_github_create_reads_the_number_from_the_url(fake_gh, tmp_path)`: unbound argv
  `["pr", "create", "--base", "develop", "--head", "topic", "--title", "T", "--body", "B"]`, out
  `"https://github.com/o/r/pull/12\n"` → `(12, "")`, one invocation with that argv and cwd;
  bound argv `["pr", "create", "--repo", "o/r", "--base", "develop", "--head", "topic", "--title", "T", "--body", "B"]`;
  out `"\n"` → ``(None, "`gh pr create` printed no pull request number")``; code 1 with err
  `boom` → `(None, "boom")`.
- `test_github_update_falls_back_to_rest_only_for_projects_classic(fake_gh, tmp_path)`, argv
  `EDIT = ["pr", "edit", "5", "--title", "T", "--body", "B"]` and
  `REST = ["api", "repos/{owner}/{repo}/pulls/5", "--method", "PATCH", "-f", "title=T", "-f", "body=B"]`:
  - success: EDIT code 0 → `(True, "")`, invocations are EDIT only;
  - plain refusal: EDIT code 1, err `"  HTTP 403:\n  Resource not accessible  "` →
    `(False, "HTTP 403: Resource not accessible")`, no REST call; code 1 with no output →
    `(False, "gh pr edit exited 1")`;
  - Projects-classic refusal then REST success: EDIT code 1, err
    `"GraphQL: Projects (classic) is being deprecated (repository.pullRequest.projectCards)"`,
    REST code 0 → `(True, "")`, invocations EDIT then REST;
  - both fail: EDIT err `"projectCards is gone"`, REST code 1 err `"HTTP 404: Not Found"` →
    `(False, "projectCards is gone; the REST fallback failed too — HTTP 404: Not Found")`;
  - bound: `GitHubForge(root=tmp_path, repository="o/r")` runs
    `["pr", "edit", "5", "--repo", "o/r", "--title", "T", "--body", "B"]`, and its REST argv
    stays exactly REST (no `--repo`).
- `test_github_merge_argv_orders_method_body_admin(fake_gh, tmp_path)`: unbound
  `merge_change_request(5, method="squash", commit_body="B", bypass_rules=True)` runs
  `["pr", "merge", "5", "--squash", "--body", "B", "--admin"]` → `(True, "")`; bound runs
  `["pr", "merge", "5", "--repo", "o/r", "--squash", "--body", "B", "--admin"]`;
  `merge_change_request(5, method="rebase")` runs `["pr", "merge", "5", "--rebase"]`; a refusal
  with err `denied` → `(False, "denied")`; with no err and out `"not mergeable"` →
  `(False, "not mergeable")`; with no output → ``(False, "`gh pr merge` exited 1")``.
- `test_every_write_passes_a_transport_problem_through(kind, verb, tmp_path)`, parametrised over
  `kind` in `("forgejo", "gitlab", "github")` and `verb` in `("create", "update", "merge")`:
  Forgejo/GitLab use a `RoutedTransport` with no routes, GitHub uses
  `GitHubForge(root=tmp_path, transport=GhTransport(executable="gh-not-installed"))`
  (`from vibey_gh.gh_transport import GhTransport`). Calls:
  `create_change_request(base="develop", head="topic", title="T", body="B")` (value `None`),
  `update_change_request(5, title="T", body="B")` (value `False`),
  `merge_change_request(5, method="squash")` (value `False`). The problem is exactly
  ``"the GitHub CLI (`gh-not-installed`) is not installed"`` for GitHub and starts with
  `"no route for "` for Forgejo and GitLab.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_change_request_writes.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the six files named under "Where to change"
```

## Out of scope
- `mark_ready`, `close_change_request`, the comment verb, `fork_clone_url`,
  `update_change_request_branch` and removing `create_comment` (split-335-2-ready-close-comment);
  the label verbs (split-335-3-labels).
- `promote.py`, `merge_train.py`, `pr_automation.py` and every other consumer module (parts 1, 2
  and 4). Promote keeps its own `_PROJECTS_CLASSIC` until part 2 deletes it.
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_forge_github.py` (never edit them).
- `.vibey-gh.toml` and its `[platform] kind = "github"` declaration: never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  (this spec's title) when done.

## Conventions this lane relies on (everything needed is here)
**C1, the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when
the forge answered; otherwise `value` is the empty value (`None` or `False` here) and `problem` is
one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable
output. A verb a forge has no equivalent for answers the empty value plus
`NotSupported(kind, verb, reason).problem`; never silently approximate it.

**C2, GitHub argv fidelity.** Each GitHub verb's argv is copied verbatim from today's call site: do
not reorder or rename flags (`--title`, not `-t`) or add fields. `[scope]` is
`["--repo", self.repository]` when bound and nothing otherwise, right after the subcommand's
positional argument, or after the two-word subcommand when there is none
(`pr create [scope] --base …`, `pr edit 5 [scope] --title …`). Literal `repos/{owner}/{repo}/…`
is gh's own placeholder and stays literal, unscoped, where today's call site used it. Every call
runs with `cwd=self.root`.

**Helpers already on the branch (do not re-add them):**
- `vibey_gh.forge.NotSupported(kind: ForgeKind, verb: str, reason: str)`, frozen, with
  `problem -> str` = `f"{kind.value} does not support {verb}: {reason}"`; `ForgeKind.GITLAB.value`
  is `"gitlab"`.
- `GitHubForge._scoped(self, head: list[str], tail: list[str]) -> list[str]` =
  `head + (["--repo", self.repository] if self.repository else []) + tail`.
- `GitHubForge._run(self, args: Sequence[str], *, stdin: str | None = None) ->
  tuple[subprocess.CompletedProcess[str] | None, str]`: the finished process and `""`, or `None`
  and ``"the GitHub CLI (`<executable>`) is not installed"``.
- `GitHubForge._failed(run, label: str, *, with_stdout: bool = False) -> str` (static):
  `(run.stderr or (run.stdout if with_stdout else "") or "").strip()`, or
  ``f"`{label}` exited {run.returncode}"`` when that is empty.
- `ForgejoForge._repository()` = `quote(self.repository, safe="/")`;
  `GitLabForge._project()` = `quote(self.repository, safe="")`.
- Transports: `survey([path, "POST"|"PATCH"|"PUT"|"DELETE", body])` sends `body`; a 2xx with an
  empty body answers `({}, "")`; a failure answers `([], problem)`.

**C7, tests.** 100% line and branch coverage of all of `vibey_gh`; focused runs need `--no-cov`.
Tests import only the double they need.

**C8, the formatter trap.** black + isort (CI tools-lint) and root `ruff format` must both be
clean, and they disagree on some wraps: keep lines at or under 100 columns (95 for nested calls);
bind a long expected value to a local before the `assert`; no implicit string concatenation;
multi-line calls one argument per line with a trailing comma; no backslash continuations. If they
fight, restructure the line; never alternate between them.

**C9, the big files.** Append with a heredoc, replace in place with an exact `edit_file`, run
black once, read only slices, never rewrite a module.

**Depends on:** split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve, split-333-1-facts-translators, split-333-2-change-request-reads, split-333-3-change-request-text, split-334-1-labelled-listings, split-334-2-open-branches, split-334-3-wait-for-checks
- split-332-1-transport-seams: `NotSupported` and transports that answer an empty 2xx as `({}, "")`.
- split-332-2-adapter-paging: `RoutedTransport` in `test/forge_doubles.py`, and the post-paging Forgejo/GitLab files.
- split-332-3-repository-name: `GitHubForge._scoped`, `_run`, `_failed`, and `import subprocess` in `forge_github.py`.
- split-332-4-selector-resolve: nothing directly; merged so the adapter files are at their post-foundation state.
- split-333-1-facts-translators: nothing directly; merged first (the wave's first half is sequential).
- split-333-2-change-request-reads: nothing directly; its methods sit in the same adapter files.
- split-333-3-change-request-text: possibly a static stderr-collapsing helper in `forge_github.py` that this lane reuses instead of `_collapsed`.
- split-334-1-labelled-listings: nothing directly; the adapter files at their post-listing state.
- split-334-2-open-branches: nothing directly; the adapter files at their post-listing state.
- split-334-3-wait-for-checks: the adapter files at their latest state (the `sleep` field is the last Forgejo/GitLab field).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
