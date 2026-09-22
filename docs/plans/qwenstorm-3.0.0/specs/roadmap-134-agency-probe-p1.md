## Title
feat(gh): the forge adapter says what this identity may do to a branch — merge rights, whether rules govern it, and whether it may bypass them

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *agency*: "merge rights and token scopes
through the forge adapter (#138), ruleset bypass"; "Proposed child issues" 1: "Through
`ForgeAdapterInterface`: can this identity merge to `develop` / `main`, which scopes does the token
hold, and is ruleset bypass present"). Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`):
Forgejo is the default forge and GitHub is declared-only, so the question is asked through the
adapter, never through `gh` directly. vibey-gh ADR 0001, restated in the seam itself
(`src/vibey_tools/gh/vibey_gh/interfaces/forge_adapter_interface.py:9-20`): every verb answers
`(value, problem)`, never raises, and "a verb arrives with its first caller" — the caller here is
the agency probe, `roadmap-134-agency-probe-p3`.

Verified gap: no verb in the forge wave answers this. The catalogue in `specs/forge-adapter.md`
(V1-V39, parts 0a-0g) has `merge_change_request(bypass_rules=...)` (V18), which *exercises* a
bypass, and `branch_rules(name, branch)` (V37), which reads a ruleset document by name; none reports
what the calling identity may do to a branch, and today's interface has nothing near it
(`forge_adapter_interface.py:36-123`). So this lane adds one verb, `branch_access(branch)`, to the
seam, to all three adapters (the Protocol obliges each), and one frozen record to the forge nouns.
10.f (`doctrines.md:419`): what a forge does not say stays `None`, never read as yes or no.

It lands after the whole of Wave 1 (`forge-0g`), because every Wave-1 part edits these same adapter
and protocol files; it follows convention C9 of `specs/forge-adapter.md` (append each method at the
end of its adapter module). Every path below is relative to `src/vibey_tools/gh/`.

## Required behaviour
1. **The record.** Appended at the end of `vibey_gh/forge.py` (after the last record, `NotSupported`,
   which `forge-0a` added), and `"BranchAccess"` added to `__all__` in sorted position:
   ```python
   @dataclass(frozen=True)
   class BranchAccess:
       """What the identity a forge adapter speaks as may do to one branch (#134, agency).

       `can_merge`: whether it holds the permission to merge a change request into `branch`.
       `rules_apply`: whether protection rules (GitHub rulesets, Forgejo branch protection)
       govern `branch`. `can_bypass`: whether it may bypass every rule that applies. Each is
       `None` when the forge does not say, which is never read as either answer (10.f).
       `basis` is one sentence naming what the forge's answer rested on.
       """

       branch: str
       can_merge: bool | None
       rules_apply: bool | None
       can_bypass: bool | None
       basis: str
   ```
2. **The seam.** In `vibey_gh/interfaces/forge_adapter_interface.py`, `BranchAccess` joins the
   `from vibey_gh.forge import (...)` list, and a new section is appended at the end of the
   Protocol:
   ```python
       # --- Agency (#134) ---

       def branch_access(self, branch: str) -> tuple[BranchAccess | None, str]:
           """What this identity may do to `branch`, and a problem. `(None, "")` when the forge
           says the branch does not exist."""
           ...
   ```
3. **GitHub** (`vibey_gh/forge_github.py`, appended at the end of the class; add `quote` to the
   existing `from urllib.parse import urlencode` line and `BranchAccess` to the `vibey_gh.forge`
   import):
   ```python
       def branch_access(self, branch: str) -> tuple[BranchAccess | None, str]:
           name, problem = self.repository_name()
           if problem:
               return None, problem
           repository, problem = self._read(["api", f"repos/{name}"])
           if problem:
               return None, problem
           permissions = repository.get("permissions") if isinstance(repository, dict) else None
           if isinstance(permissions, dict):
               held = sorted(key for key, value in permissions.items() if value is True)
               can_merge: bool | None = any(k in held for k in ("admin", "maintain", "push"))
               stated = ", ".join(held) or "none"
           else:
               can_merge, stated = None, "not stated"
           path = f"repos/{name}/rules/branches/{quote(branch, safe='')}"
           rules, problem = self._read(["api", path])
           if problem:
               return None, problem
           if not isinstance(rules, list):
               return None, f"`gh api {path}` did not answer a list"
           ids = sorted(
               {
                   rule["ruleset_id"]
                   for rule in rules
                   if isinstance(rule, dict) and isinstance(rule.get("ruleset_id"), int)
               }
           )
           answers: list[str] = []
           for ruleset_id in ids:
               ruleset, problem = self._read(["api", f"repos/{name}/rulesets/{ruleset_id}"])
               if problem:
                   return None, problem
               answer = ruleset.get("current_user_can_bypass") if isinstance(ruleset, dict) else None
               answers.append(answer if isinstance(answer, str) else "not stated")
           if not ids:
               can_bypass: bool | None = None
           elif "never" in answers:
               can_bypass = False
           elif all(answer in BYPASSING for answer in answers):
               can_bypass = True
           else:
               can_bypass = None
           basis = f"GitHub: repository permissions {stated}; {len(ids)} ruleset(s) govern {branch}"
           if ids:
               basis += f"; current_user_can_bypass: {', '.join(answers)}"
           return BranchAccess(branch, can_merge, bool(rules), can_bypass, basis), ""
   ```
   with the module constant, beside `GH_DEFAULT_HOST`:
   `BYPASSING = frozenset({"always", "pull_requests_only", "exempt"})  # GitHub's current_user_can_bypass values that let this identity past a ruleset`.
   GitHub reads rules by name pattern, so a branch that does not exist yet is answered with the
   rules that would govern it; this adapter never answers `(None, "")`.
4. **Forgejo** (`vibey_gh/forge_forgejo.py`, appended at the end of the class; `quote` is already
   imported; add `BranchAccess` to the `vibey_gh.forge` import):
   ```python
       def branch_access(self, branch: str) -> tuple[BranchAccess | None, str]:
           path = f"repos/{self._repository()}/branches/{quote(branch, safe='')}"
           found, problem = self.transport.survey([path], cwd=self.root)
           if problem:
               return (None, "") if self._absent(problem) else (None, problem)
           if not isinstance(found, dict):
               return None, f"Forgejo answered no branch object for {branch}"
           merge, protected = found.get("user_can_merge"), found.get("protected")
           basis = (
               f"Forgejo: user_can_merge={merge!r}, protected={protected!r}; Forgejo reports no"
               " separate bypass, and user_can_merge already counts any merge whitelist"
           )
           return (
               BranchAccess(
                   branch,
                   merge if isinstance(merge, bool) else None,
                   protected if isinstance(protected, bool) else None,
                   None,
                   basis,
               ),
               "",
           )
   ```
   (`_absent` is the 404 test `forge-0a` added; `_repository()` is the existing helper.)
5. **GitLab** (`vibey_gh/forge_gitlab.py`, appended at the end of the class; import `BranchAccess`,
   and `NotSupported`/`ForgeKind` if not already imported):
   ```python
       def branch_access(self, branch: str) -> tuple[BranchAccess | None, str]:
           reason = "GitLab states push access per branch, not whether this identity may merge into it"
           return None, NotSupported(ForgeKind.GITLAB, "branch_access", reason).problem
   ```
6. **The class contract.** `vibey_gh/interfaces/class_contracts.py` gains, directly after
   `ProtectedRefInterface` (`:167-170`):
   ```python
   @runtime_checkable
   class BranchAccessInterface(Protocol):
       @property
       def branch(self) -> str: ...

       @property
       def can_merge(self) -> bool | None: ...

       @property
       def rules_apply(self) -> bool | None: ...

       @property
       def can_bypass(self) -> bool | None: ...

       @property
       def basis(self) -> str: ...
   ```
   and `vibey_gh/interfaces/__init__.py` imports and exports it (the import list and `__all__`,
   each in sorted position), exactly as it does `ProtectedRefInterface` (`__init__.py:68`, `:202`).

## Where to change
- Edit (append per C9 with a shell heredoc, then run black once; never rewrite a module):
  `vibey_gh/forge.py`, `vibey_gh/interfaces/forge_adapter_interface.py`,
  `vibey_gh/forge_github.py`, `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`,
  `vibey_gh/interfaces/class_contracts.py`, `vibey_gh/interfaces/__init__.py`.
- New test file `test/test_forge_branch_access.py`.
- No change to `test/forge_doubles.py`: `RecordingForge` answers any scripted verb by name and
  `RoutedTransport` routes by path (both from `forge-0a`, `specs/forge-adapter.md` C7).

## Acceptance criteria
- [ ] GitHub runs exactly `gh api repos/o/r`, `gh api repos/o/r/rules/branches/<branch>` and one
      `gh api repos/o/r/rulesets/<id>` per distinct ruleset, in that order, in the clone's root.
- [ ] A permission, rule or bypass the forge did not state is `None`; a failed call is a problem,
      never a raise and never an empty answer.
- [ ] GitLab answers `NotSupported` with the exact sentence above; Forgejo maps a 404 to `(None, "")`.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_forge_branch_access.py` (provenance line 1 from `test/test_forge_adapters.py:1`;
`from forge_doubles import RoutedTransport`; the conftest `fake_gh` fixture for GitHub, with
`monkeypatch.setenv("GH_REPO", "o/r")` so `repository_name()` asks nothing):
- `test_github_reads_permissions_rules_and_each_rulesets_bypass` — script
  `"api repos/o/r"` → `{"out": json.dumps({"permissions": {"admin": False, "maintain": False, "push": True, "triage": True, "pull": True}})}`,
  `"api repos/o/r/rules/branches/develop"` → `{"out": json.dumps([{"type": "pull_request", "ruleset_id": 7}, {"type": "deletion", "ruleset_id": 7}])}`,
  `"api repos/o/r/rulesets/7"` → `{"out": json.dumps({"id": 7, "current_user_can_bypass": "never"})}`;
  `GitHubForge(root=tmp_path).branch_access("develop")` ==
  `(BranchAccess("develop", True, True, False, "GitHub: repository permissions pull, push, triage; 1 ruleset(s) govern develop; current_user_can_bypass: never"), "")`,
  and `fake_gh.calls() == ["api repos/o/r", "api repos/o/r/rules/branches/develop", "api repos/o/r/rulesets/7"]`.
- `test_github_bypass_needs_every_ruleset_to_allow_it` (parametrised over the second ruleset's
  answer): rulesets 7 (`"always"`) and 9 — `"exempt"` → `can_bypass is True`; `"never"` →
  `False`; a document without the field → `None` (its basis says `not stated`).
- `test_github_with_no_rules_has_nothing_to_bypass` — rules `[]`: `rules_apply is False`,
  `can_bypass is None`, no `rulesets/` call.
- `test_github_without_stated_permissions_cannot_say_who_may_merge` — `"api repos/o/r"` →
  `{"out": "{}"}`: `can_merge is None` and the basis says `repository permissions not stated`.
- `test_github_failures_are_problems` — a non-zero exit on each of the three calls in turn
  (`{"code": 1, "err": "HTTP 403: forbidden"}`) returns `(None, <problem>)` with the problem
  naming the call; rules answered as `{"out": "{}"}` returns
  `(None, "`gh api repos/o/r/rules/branches/develop` did not answer a list")`.
- `test_forgejo_reads_the_branch_object` — `RoutedTransport({"repos/o/r/branches/main": ({"name": "main", "protected": True, "user_can_merge": False, "user_can_push": False}, "")})`,
  `ForgejoForge(root=tmp_path, repository="o/r", transport=routed).branch_access("main")` →
  `BranchAccess("main", False, True, None, <basis naming user_can_merge=False>)`, problem `""`.
- `test_forgejo_absent_branch_and_failures` — route answering `([], "Forgejo API error 404: Not Found")`
  → `(None, "")`; `([], "Forgejo transport failure: refused")` → `(None, that text)`; a list answer
  → `(None, "Forgejo answered no branch object for main")`; unstated fields → `None`s.
- `test_gitlab_branch_access_is_not_supported` — the exact `NotSupported` problem:
  `"gitlab does not support branch_access: GitLab states push access per branch, not whether this identity may merge into it"`.
- `test_branch_access_is_a_forge_noun_with_a_contract` — `BranchAccess` is frozen (assigning a field
  raises `FrozenInstanceError`) and `isinstance(BranchAccess("b", None, None, None, ""), BranchAccessInterface)`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_forge_branch_access.py test/test_forge_adapters.py test/test_forge_github.py test/test_platform.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on (the GitHub method's
longest lines are the ones to watch).

## Out of scope
- Token scopes (`roadmap-134-agency-probe-p2`), the agency probe and its configuration
  (`roadmap-134-agency-probe-p3`).
- Paid credit balance (the conductor-bridge lane `roadmap-134-agent-information-probes`).
- GitHub classic branch protection (this repository governs its branches with rulesets,
  `vibey-gh rulesets`); a GitLab mapping of access levels.
- Every Wave-2 module (`merge_train`, `promote`, …) and `test/forge_doubles.py`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
