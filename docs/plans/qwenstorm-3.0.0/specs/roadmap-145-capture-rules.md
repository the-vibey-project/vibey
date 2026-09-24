## Title
feat(gh): forge-snapshot reads back rulesets and branch protection, and a token without administration is a named could-not-look

## Why
Issue #145 (rewrite: `issue-audit/updates/145.md`, "Proposed child issues" 5, and Scope §3
"settings read-back (repository metadata, rulesets, branch protection) for drift against the
declared state") and #136 ("rulesets and branch protections", slice S3) both ask for these
classes; the coordinator places them in the snapshot. Repository metadata is already captured
by `roadmap-136-capture-repo-metadata`, so this lane does not touch it. Today both are excluded:
`("ruleset", "Repository rulesets are not read.")` and
`("branch-protection", "Classic branch protection needs administration permission.")`
(`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:154-155` at integration `4317cff6`).

12.c says repository settings are declared in the repository and "reality is checked against
it" (`src/vibey_tools/gh/docs/doctrines.md:455`); vibey-gh reconciles rulesets into the forge
(`.vibey-gh.toml` `[rulesets]`, `vibey-gh rulesets`) but nothing reads them back. Two GitHub
facts shape the walk:
- `GET /repos/{repo}/rulesets` lists summaries only; each ruleset's rules, conditions and
  bypass actors come from `GET /repos/{repo}/rulesets/{id}`. `includes_parents=true` includes
  organisation rulesets that apply.
- Classic protection is per branch (`GET /repos/{repo}/branches/{branch}/protection`) and
  needs administration permission. The protected branches are listed with
  `GET /repos/{repo}/branches?protected=true` (read access). A refused protection read is
  "could not look" with the reason, never a branch recorded as unprotected (10.f,
  `doctrines.md:419`). A branch name can hold `/`, so it is percent-encoded
  (`urllib.parse.quote(name, safe="")`, stdlib: vibey-gh stays `dependencies = []`,
  `src/vibey_tools/gh/pyproject.toml:30`).

No host-specific code: the suite runs unchanged on Arch Linux and macOS (8.h, `doctrines.md:326-333`).

## Required behaviour
All in `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` unless named otherwise. This lane runs
after `roadmap-145-capture-workflow-runs`; anchors are text.
1. `from urllib.parse import quote` directly after `from typing import Any`.
2. `CLASSES`: replace `)\n\nEXCLUDED: tuple[tuple[str, str], ...] = (` with
   ```python
       ForgeClass(
           "ruleset",
           "repository_ruleset",
           "repos/{repository}/rulesets?includes_parents=true&per_page={per_page}",
       ),
       ForgeClass(
           "branch-protection",
           "branch_protection",
           "repos/{repository}/branches?protected=true&per_page={per_page}",
           id_field="name",
       ),
   )

   EXCLUDED: tuple[tuple[str, str], ...] = (
   ```
   Both are walked whole every capture (no cursor).
3. `EXCLUDED`: delete exactly `    ("ruleset", "Repository rulesets are not read."),` and
   `    ("branch-protection", "Classic branch protection needs administration permission."),`.
4. `read`: directly above `        return self._walk(spec, since)` insert
   ```python
           if spec.name == "ruleset":
               return self._rulesets(spec)
           if spec.name == "branch-protection":
               return self._protections(spec)
   ```
5. Two new methods, directly above `    @staticmethod\n    def _observed(` (`_object` is from
   `roadmap-136-capture-repo-metadata`):
   ```python
       def _rulesets(self, spec: ForgeClass) -> ForgeRead:
           """Every ruleset in full: the listing only names them, and only the ruleset holds
           its rules, conditions and (to an administrator) its bypass actors."""
           listed, problem = self._listing(
               spec.endpoint.format(repository=self.repository, per_page=self._per_page)
           )
           if problem:
               return ForgeRead(spec.name, spec.native_class, problem=problem)
           items: list[dict[str, Any]] = []
           for summary in listed:
               ruleset_id = summary.get("id")
               if not isinstance(ruleset_id, int) or isinstance(ruleset_id, bool):
                   return ForgeRead(
                       spec.name,
                       spec.native_class,
                       problem=f"the forge listed a {spec.native_class} with no `id`",
                   )
               detail, problem = self._object(
                   f"repos/{self.repository}/rulesets/{ruleset_id}?includes_parents=true"
               )
               if problem:
                   return ForgeRead(spec.name, spec.native_class, problem=problem)
               items.append(detail)
           return self._observed(spec, items, None)

       def _protections(self, spec: ForgeClass) -> ForgeRead:
           """Each protected branch's classic protection, named by its branch.

           Reading a protection needs administration permission. A token without it is a
           named could-not-look, never a branch recorded as unprotected.
           """
           branches, problem = self._listing(
               spec.endpoint.format(repository=self.repository, per_page=self._per_page)
           )
           if problem:
               return ForgeRead(spec.name, spec.native_class, problem=problem)
           observations: list[Observation] = []
           for branch in branches:
               name = branch.get("name")
               if not isinstance(name, str) or not name:
                   return ForgeRead(
                       spec.name,
                       spec.native_class,
                       problem="the forge listed a protected branch with no `name`",
                   )
               protection, problem = self._object(
                   f"repos/{self.repository}/branches/{quote(name, safe='')}/protection"
               )
               if problem:
                   return ForgeRead(
                       spec.name,
                       spec.native_class,
                       problem=(
                           f"could not read the protection of branch {name!r} (reading it needs"
                           f" administration permission): {problem}"
                       ),
                   )
               observations.append((name, protection))
           return ForgeRead(spec.name, spec.native_class, tuple(observations))
   ```
6. `src/vibey_tools/gh/docs/forge-snapshot.md` (rows only; the schema-document test
   `test/test_forge_snapshot.py:1143-1153` owns them):
   - replace `\n\nA few things about GitHub that the files keep rather than hide:` with a newline,
     these two rows, and the same text:
     ```
     | `ruleset.jsonl` | `ruleset` | `repository_ruleset` | `/repos/{repo}/rulesets?includes_parents=true`, then each ruleset in full | `id` | no |
     | `branch-protection.jsonl` | `branch-protection` | `branch_protection` | `/repos/{repo}/branches?protected=true`, then each branch's `/protection` | the branch's `name` | no |
     ```
   - delete the rows
     `| `ruleset` | Not read. vibey-gh's own are declared in `.vibey-gh.toml` and reconciled by `vibey-gh rulesets`. |`
     and `| `branch-protection` | Needs administration permission to read. |`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 1-5).
- `src/vibey_tools/gh/docs/forge-snapshot.md` (behaviour 6, four rows only).
- `src/vibey_tools/gh/test/test_forge_snapshot.py` — add `from urllib.parse import quote`
  directly after `from typing import Any` (`:24`), the fixture edits below, then append the
  tests. Use `edit_file`; each anchor is unique:
  1. `World` fields: directly above `\n    @classmethod\n    def seeded(cls, per_page: int = 100) -> World:` insert
     `    rulesets: list[dict[str, Any]] = field(default_factory=list)` and
     `    protections: dict[str, dict[str, Any]] = field(default_factory=dict)`.
  2. `World.seeded`: directly above `        return world\n\n    # -- the command lines a capture makes` insert
     ```python
             world.rulesets = [
                 {
                     "id": 5001,
                     "name": "develop",
                     "target": "branch",
                     "source_type": "Repository",
                     "source": REPO,
                     "enforcement": "active",
                     "conditions": {"ref_name": {"include": ["refs/heads/develop"], "exclude": []}},
                     "rules": [{"type": "pull_request"}, {"type": "non_fast_forward"}],
                     "bypass_actors": [],
                     "node_id": "RRS_5001",
                     "created_at": "2026-08-01T00:00:00Z",
                     "updated_at": "2026-09-01T00:00:00Z",
                 },
             ]
             world.protections = {
                 "main": {
                     "url": f"{API}/branches/main/protection",
                     "required_linear_history": {"enabled": True},
                     "allow_force_pushes": {"enabled": False},
                     "allow_deletions": {"enabled": False},
                     "enforce_admins": {
                         "url": f"{API}/branches/main/protection/enforce_admins",
                         "enabled": True,
                     },
                 },
             }
     ```
  3. `World.answers`: directly above its last line `        return out` insert
     ```python
             summary_keys = ("id", "name", "target", "source_type", "source", "enforcement", "node_id")
             summaries = [{key: ruleset[key] for key in summary_keys} for ruleset in self.rulesets]
             out[self.listing(self.path("ruleset"))] = {"out": json.dumps(self._pages(summaries))}
             for ruleset in self.rulesets:
                 detail = f"api repos/{REPO}/rulesets/{ruleset['id']}?includes_parents=true"
                 out[detail] = {"out": json.dumps(ruleset)}
             branches = [{"name": name, "protected": True} for name in self.protections]
             out[self.listing(self.path("branch-protection"))] = {
                 "out": json.dumps(self._pages(branches))
             }
             for name, protection in self.protections.items():
                 out[f"api repos/{REPO}/branches/{quote(name, safe='')}/protection"] = {
                     "out": json.dumps(protection)
                 }
     ```
  4. `test_a_full_capture_writes_every_class_verbatim_and_chained`: replace
     `    }\n    for name, items in expected.items():` with
     `        "ruleset": world.rulesets,\n    }\n    for name, items in expected.items():`
     (branch protection is not added: its native id is the branch name, not a payload field),
     and replace `    }\n    assert manifest["resume_since"] == floor` with
     `        "ruleset": None,\n        "branch-protection": None,\n    }\n    assert manifest["resume_since"] == floor`.
  5. `test_a_capture_resumes_from_its_cursor_and_continues_every_chain`: replace
     `    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")` with
     `        "ruleset": (1, 0, 1),\n        "branch-protection": (1, 0, 1),\n    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")`.
  Change no other existing test.
- Then run `python -m black vibey_gh test` and `isort vibey_gh test` from `src/vibey_tools/gh`.

## Acceptance criteria
- [ ] `ruleset` and `branch-protection` are captured classes, gone from `EXCLUDED`, and in the docs table.
- [ ] A ruleset record is the full `rulesets/{id}` answer (with `rules` and `conditions`), not
      the listing summary; the calls are the listing, then one detail call per ruleset.
- [ ] Branch protection is one record per protected branch, named by the branch; a branch name
      with `/` is sent percent-encoded (`release%2F1.0`).
- [ ] A refused protection read is `could-not-look` naming the branch and the administration
      requirement, the manifest is not `complete`, and nothing is written; a repository with no
      protected branches is `captured` with `observed == 0`.
- [ ] Failed listings, a failed detail read, a ruleset with no `id` and a branch with no `name`
      are each `could-not-look` with the exact message.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py`:
- `test_each_ruleset_is_captured_in_full_not_as_its_listing_summary` —
  `capture(classes=["ruleset"])`: payloads equal `world.rulesets`, native id `"5001"`, `"rules"`
  in the payload, and `fake_gh.calls() == [World.listing(world.path("ruleset")),
  f"api repos/{REPO}/rulesets/5001?includes_parents=true"]`.
- `test_branch_protection_is_read_for_every_protected_branch` — add
  `world.protections["release/1.0"] = {"url": f"{API}/branches/release/1.0/protection"}`;
  native ids `["main", "release/1.0"]`, payloads `list(world.protections.values())`, and
  `f"api repos/{REPO}/branches/release%2F1.0/protection"` is in the calls.
- `test_branch_protection_without_administration_is_a_named_could_not_look` — the `main`
  protection call answers `{"err": "HTTP 403: Must have admin rights to Repository.\n", "code":
  1}`; `capture(classes=["branch-protection", "label"])`: status `could-not-look`, problem
  exactly `"could not read the protection of branch 'main' (reading it needs administration"
  f" permission): `gh api repos/{REPO}/branches/main/protection` failed: HTTP 403: Must have
  admin rights to Repository."`, no file, `complete is False`, and `label` is `captured`.
- `test_a_repository_with_no_protected_branches_is_captured_as_having_none` —
  `world.protections = {}`: `(status, observed) == ("captured", 0)` and no file.
- `test_a_failed_ruleset_or_protected_branch_listing_is_could_not_look` — parametrized over
  `("ruleset", listing, "502")`, `("ruleset", the detail call, "404")` and
  `("branch-protection", listing, "502")`, answering `{"err": f"HTTP {code}\n", "code": 1}`:
  status `could-not-look`, problem ends with `f"failed: HTTP {code}"`.
- `test_rulesets_and_protected_branches_the_forge_cannot_identify_are_refused` — the ruleset
  listing answers `json.dumps([[{"name": "no id"}]])` and the branch listing
  `json.dumps([[{"protected": True}]])`: problems are
  ``"the forge listed a repository_ruleset with no `id`"`` and
  ``"the forge listed a protected branch with no `name`"``.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh, black, isort, yaml" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_snapshot.py test/test_forge_adapters.py
python -m pytest -q          # the whole suite; pyproject.toml:64-70 fails it under 100% line+branch
python -m black --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
uv run ruff check . && uv run ruff format --check .
uv run lint-imports
git diff --stat              # only the three files above
```

## Out of scope
- Repository metadata (`roadmap-136-capture-repo-metadata`, already a class).
- Reporting drift between the captured settings and `[repository_profile]` / `[rulesets]`
  (#145's `vibey-gh check` criterion; a later lane reads these records).
- Webhooks, deploy keys, autolinks, collaborators, security alerts (still excluded; security
  alerts wait on #145's open question 4).
- Forgejo branch protection and `ForgeAdapterReader` (after the gaps.md §L8 lane).
- Any prose in `docs/forge-snapshot.md` beyond the four rows: the docs wave. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
