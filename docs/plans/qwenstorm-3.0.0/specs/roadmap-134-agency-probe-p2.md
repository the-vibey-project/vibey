## Title
feat(gh): the forge adapter says which scopes the calling token holds, or that its forge cannot say

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *agency*: "merge rights and token scopes
through the forge adapter (#138)"; "Proposed child issues" 1: "which scopes does the token hold").
The agency probe (`roadmap-134-agency-probe-p3`) reports the scopes and refuses a token that lacks a
declared one. No verb in the forge wave's catalogue (`specs/forge-adapter.md`, V1-V39) reads a
token's scopes, and today's seam has nothing near it
(`src/vibey_tools/gh/vibey_gh/interfaces/forge_adapter_interface.py:36-123`). vibey-gh ADR 0001, as
the seam states it (`forge_adapter_interface.py:9-20`): one verb per question, answering
`(value, problem)`, never raising, arriving with its first caller; a forge with no equivalent
answers `NotSupported` rather than approximating (`specs/forge-adapter.md` C1). Sub-doctrine 10.f
(`src/vibey_tools/gh/docs/doctrines.md:419`): a token that publishes no scope list is answered as
"no list" (`None`), never as "no scopes". 8.b (`doctrines.md:138-139`): the question goes through
the adapter on every forge.

It lands after `roadmap-134-agency-probe-p1` (same four files). Every path below is relative to
`src/vibey_tools/gh/`.

## Required behaviour
1. **The seam.** Appended to the `# --- Agency (#134) ---` section of
   `vibey_gh/interfaces/forge_adapter_interface.py`:
   ```python
       def token_scopes(self) -> tuple[frozenset[str] | None, str]:
           """The scopes the calling token holds, and a problem. `(None, "")` when the forge
           answered but the token publishes no scope list (a fine-grained or app token)."""
           ...
   ```
2. **GitHub** (`vibey_gh/forge_github.py`, appended at the end of the class):
   ```python
       def token_scopes(self) -> tuple[frozenset[str] | None, str]:
           run, problem = self._run(["api", "user", "--include"])
           if run is None:
               return None, problem
           if run.returncode != 0:
               return None, self._failed(run, "gh api user")
           for line in run.stdout.splitlines():
               if not line.strip():
                   break  # the headers end at the first blank line
               name, _, value = line.partition(":")
               if name.strip().lower() == "x-oauth-scopes":
                   return frozenset(s.strip() for s in value.split(",") if s.strip()), ""
           return None, ""
   ```
   (`_run` and `_failed` are the helpers `forge-0a` added: `_run` answers `(None, <not installed>)`
   without a `gh`, `_failed` is the stderr or ``"`gh api user` exited N"``.)
3. **Forgejo** (`vibey_gh/forge_forgejo.py`, appended at the end of the class):
   ```python
       def token_scopes(self) -> tuple[frozenset[str] | None, str]:
           reason = "Forgejo does not report the scopes of the token a call is made with"
           return None, NotSupported(ForgeKind.FORGEJO, "token_scopes", reason).problem
   ```
   (import `NotSupported` and `ForgeKind` from `vibey_gh.forge` if not already imported).
4. **GitLab** (`vibey_gh/forge_gitlab.py`, appended at the end of the class):
   ```python
       def token_scopes(self) -> tuple[frozenset[str] | None, str]:
           token, problem = self.transport.survey(["personal_access_tokens/self"], cwd=self.root)
           if problem:
               return None, problem
           scopes = token.get("scopes") if isinstance(token, dict) else None
           if not isinstance(scopes, list):
               return None, "GitLab answered no scope list for this token"
           return frozenset(str(scope) for scope in scopes), ""
   ```

## Where to change
- Edit (append per `specs/forge-adapter.md` C9 with a heredoc, then black once):
  `vibey_gh/interfaces/forge_adapter_interface.py`, `vibey_gh/forge_github.py`,
  `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`.
- New test file `test/test_forge_token_scopes.py`.

## Acceptance criteria
- [ ] GitHub runs exactly `gh api user --include` in the clone's root and reads only the header
      block; a missing `X-Oauth-Scopes` header is `(None, "")`, an empty one `(frozenset(), "")`.
- [ ] Forgejo answers `NotSupported` with the exact sentence above; GitLab reads
      `personal_access_tokens/self`.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_forge_token_scopes.py` (provenance line 1 from `test/test_forge_adapters.py:1`;
`from forge_doubles import RoutedTransport`; the conftest `fake_gh` fixture for GitHub):
- `test_github_reads_the_scopes_header` — script `"api user --include"` →
  `{"out": "HTTP/2.0 200 OK\nContent-Type: application/json; charset=utf-8\nX-Oauth-Scopes: repo, workflow, read:org\nX-Accepted-Oauth-Scopes: \n\n{\"login\": \"octo\"}"}`;
  `GitHubForge(root=tmp_path).token_scopes() == (frozenset({"repo", "workflow", "read:org"}), "")`;
  `fake_gh.invocations() == [{"argv": ["api", "user", "--include"], "cwd": str(tmp_path.resolve()), "stdin": None}]`.
- `test_github_a_token_without_a_scope_list_says_so` — no `X-Oauth-Scopes` header → `(None, "")`;
  a body line `"X-Oauth-Scopes: fake"` after the blank line is not read; `"X-Oauth-Scopes: \n\n{}"`
  → `(frozenset(), "")`.
- `test_github_failures_are_problems` — `{"code": 1, "err": "HTTP 401: Bad credentials"}` →
  `(None, "HTTP 401: Bad credentials")`; with `PATH` set (`monkeypatch.setenv`) to an empty
  directory, the problem says the GitHub CLI is not installed.
- `test_forgejo_token_scopes_are_not_supported` — exactly
  `(None, "forgejo does not support token_scopes: Forgejo does not report the scopes of the token a call is made with")`.
- `test_gitlab_reads_its_token` — `RoutedTransport({"personal_access_tokens/self": ({"scopes": ["api", "read_repository"]}, "")})`
  → `(frozenset({"api", "read_repository"}), "")`; `({"name": "t"}, "")` →
  `(None, "GitLab answered no scope list for this token")`; `([], "GitLab API error 401: Unauthorized")`
  → `(None, "GitLab API error 401: Unauthorized")`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_forge_token_scopes.py test/test_forge_branch_access.py test/test_forge_adapters.py test/test_forge_github.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- Which scopes a run requires (`[estimate] required_token_scopes`, `roadmap-134-agency-probe-p3`).
- Paid credit balance (the conductor-bridge lane `roadmap-134-agent-information-probes`).
- Reading Forgejo token scopes through a password-authenticated listing (this tenant never holds a
  password).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
