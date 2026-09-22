<!-- split of #344: child 1 of 2; audit: issue-audit/updates/344.md -->
## Title
feat(gh): ruleset reconciliation reaches the forge only through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the default forge, with GitHub and GitLab declared-only; `[platform] kind` defaults to `forgejo` (`vibey_gh/config.py:288`). `vibey_gh/rulesets.py` reconciles branch rulesets through a private `gh api` runner, `_api` (`rulesets.py:179-196`), called by `fetch_ruleset` (`:198-209`), `create_ruleset` (`:212-213`) and `update_ruleset` (`:216-222`), each naming the repository with `github_state.repository()`; it ignores `[platform]`. A rule a forge cannot express must come back as a problem, never be dropped: `reconcile_one` already refuses to skip silently (`rulesets.py:226-230`), and #338 (forge-0g) makes the Forgejo adapter refuse what `branch_protections` cannot express with a NotSupported sentence. The default `[rulesets]` policy asks for rules Forgejo refuses (merge queue, linear history, review-thread resolution, code-owner review, bypass actors), so on the sovereign default `vibey-gh rulesets` fails loudly until the operator chooses an expressible policy, which is honest (10.f), and this lane must keep it that way. When a paid forge is declared, 8.b says it "relays through the sovereign host rather than replacing it" (`doctrines.md:179-184`); that relay belongs behind `ForgeAdapterInterface`, and this lane keeps every call on the interface.

#344 was split: this lane covers `rulesets.py` only; `flatten.py`'s review-thread walk is `split-344-2-flatten`. Every path below is relative to `src/vibey_tools/gh/` (package `vibey_gh`) unless it starts with `src/`.

## Required behaviour
1. Delete `_api` (`rulesets.py:179-196`) and the imports that become unused: `import json`, `import subprocess`, `cast` (from `from typing import Any, cast`, which becomes `from typing import Any`) and `from vibey_gh import github_state`. Rename the section banner at `rulesets.py:176` from `gh adapters` to `forge adapter`.
2. Add a private helper that binds (C6.2), with its reason written at the definition:
   ```python
   # Module-level: the three forge functions below share it and are module-level themselves
   # (see their comments); the module converges on a class in its own lane (ADR-0016).
   def _bind(forge: ForgeAdapterInterface) -> ForgeAdapterInterface:
       name, problem = forge.repository_name()
       if problem:
           raise RuntimeError(problem)
       return forge.for_repository(name)
   ```
3. `fetch_ruleset(name: str, branch: str, *, forge: ForgeAdapterInterface | None = None) -> dict[str, Any] | None`: `bound = _bind(ForgeSelector().resolve(forge))`; `document, problem = bound.branch_rules(name, branch)`; a problem → `raise RuntimeError(problem)`; return `document` (`None` when no ruleset has that name). Keep the docstring's reason for re-fetching by ID, saying the GitHub adapter now does it, and add that `branch` is what a per-branch forge (Forgejo) keys its protection by.
4. `create_ruleset(payload: dict[str, Any], *, forge: ForgeAdapterInterface | None = None) -> None`: `bound = _bind(ForgeSelector().resolve(forge))`; `ok, problem = bound.create_branch_rules(payload)`; not `ok` → `raise RuntimeError(problem)`.
5. `update_ruleset(ruleset_id: int | str, payload: dict[str, Any], *, forge: ForgeAdapterInterface | None = None) -> None`: bind the same way; `ok, problem = bound.update_branch_rules(str(ruleset_id), payload)`; not `ok` → `raise RuntimeError(problem)`. (`int | str` because a Forgejo document's `"id"` is its branch name.)
6. `reconcile_one(branch, policy, *, dry_run=False, forge: ForgeAdapterInterface | None = None)`: `forge = ForgeSelector().resolve(forge)` once at the start; `existing = fetch_ruleset(name, branch, forge=forge)`; `create_ruleset(result.payload, forge=forge)` / `update_ruleset(existing["id"], result.payload, forge=forge)`. Everything else (the outcome dict, the dry-run and unchanged early return) is unchanged.
7. `reconcile(cfg, *, dry_run=False, forge: ForgeAdapterInterface | None = None)`: after the `if not cfg.rulesets.enabled: return []` early return, `forge = ForgeSelector().resolve(forge, cfg)` once, then `[reconcile_one(branch, policy, dry_run=dry_run, forge=forge) for branch, policy in targets]`.
8. The pure half (`ruleset_name`, `desired_rules`, `bypass_actor_payload`, `build_ruleset`, `_rules_by_type`, `_bypass_key`, `Diff`, `diff_ruleset`) is untouched.
9. On GitHub the argv and stdin are unchanged byte for byte (the #338 GitHub verbs run `api repos/<R>/rulesets`, `api repos/<R>/rulesets/<id>`, and `api repos/<R>/rulesets --method POST --input -` / `api repos/<R>/rulesets/<id> --method PUT --input -` with the JSON on stdin, and answer today's failure text `"gh api repos/<R>/rulesets --method POST: <stderr>"`). Deliberate differences: **D1** `gh` runs in `load_config().root` (or `cfg.root` when `reconcile` resolves with a `cfg`) instead of the process's working directory (the same repository); **D5** a missing `gh` or unreadable output raises `RuntimeError(problem)` instead of `FileNotFoundError`/`json.JSONDecodeError`.
10. The five public functions stay module-level; each carries a one-line reason at its definition (9.b, `doctrines.md:349`), for example `# Module-level: cli.py and its tests address these by name; the module converges on a class in its own lane (ADR-0016).`
11. `cli.py` is not changed: `_rulesets` still calls `rulesets.reconcile(cfg, dry_run=args.dry_run)` (`cli.py:1171-1185`), which now resolves its forge from `cfg`.

## Where to change
- `vibey_gh/rulesets.py` only (261 lines: use `edit_file`, never `write_file`). New imports, placed by isort among the first-party imports: `from vibey_gh.forge_selector import ForgeSelector` and `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface`.
- Tests: `test/test_rulesets.py` (619 lines: `edit_file` per test, or checked `python3 -c` replacements; never rewrite the file). New tests may be appended.

## Acceptance criteria
- [ ] `grep -nE '"gh"|gh_json|github_state|subprocess|_api\(' vibey_gh/rulesets.py` finds nothing.
- [ ] `grep -nE 'rs\._api|setattr\(rs|setattr\(subprocess' test/test_rulesets.py` finds nothing, and `grep -c 'monkeypatch.setattr' test/test_rulesets.py` prints `0` (it is 22 at the integration branch; every one is in the converted tests).
- [ ] `test_fetch_ruleset_end_to_end_through_the_real_gh_adapter` and `test_a_request_body_is_actually_sent` still prove, through a real `gh` executable on `PATH`, that a read sends no body and a write sends `--input -` with the payload on stdin.
- [ ] `test/test_gh_cli.py`'s two rulesets tests (`test_rulesets_cli_reports_each_outcome`, `test_rulesets_cli_reports_failures`) pass unmodified.
- [ ] Whole suite green at 100% line and branch coverage of `vibey_gh`; black, isort, mypy, `ruff check` and `ruff format --check` clean; `git diff --stat` lists only `vibey_gh/rulesets.py` and `test/test_rulesets.py`.

## Tests to write first (TDD)
In `test/test_rulesets.py`, add `from forge_doubles import RecordingForge` (third-party block, after `import pytest`), `from vibey_gh.forge_forgejo import ForgejoForge` and `from vibey_gh.forge_github import GitHubForge`. Rewrite the module docstring's last sentence: the forge half is tested through the adapter, with `RecordingForge` for the orchestration and the real GitHub adapter driving the conftest `fake_gh` for the argv.
- New:
  - `test_rulesets_bind_and_use_branch_rule_verbs`: `desired = rs.build_ruleset("develop", policy(required_approvals=1))`, `stale = {**desired, "id": 9, "rules": rs.desired_rules(policy(required_approvals=0))}`, `forge = RecordingForge(branch_rules=(stale, ""), update_branch_rules=(True, ""))`; `rs.reconcile_one("develop", policy(required_approvals=1), forge=forge)` is applied; `("for_repository", "o/r") in forge.calls`; and `[c for c in forge.calls if c[0].endswith("branch_rules")] == [("branch_rules", "vibey-gh: develop", "develop"), ("update_branch_rules", "9", rs.diff_ruleset(desired, stale).payload)]`.
  - `test_a_forge_that_refuses_the_rules_raises_its_problem`: `RecordingForge(branch_rules=(None, ""), create_branch_rules=(False, "forgejo does not support branch rules: no equivalent for merge_queue"))` → `pytest.raises(RuntimeError, match="does not support branch rules")` around `rs.reconcile_one("develop", policy(), forge=forge)`.
  - `test_reconcile_one_passes_the_branch_to_the_fetch`: `RecordingForge(branch_rules=(None, ""))`, `rs.reconcile_one("main", policy(), dry_run=True, forge=forge)`; `("branch_rules", "vibey-gh: main", "main") in forge.calls`.
  - `test_a_forge_that_cannot_name_the_repository_raises_its_problem`: parametrised over `lambda f: rs.fetch_ruleset("n", "develop", forge=f)`, `lambda f: rs.create_ruleset({"name": "x"}, forge=f)` and `lambda f: rs.update_ruleset(7, {"name": "x"}, forge=f)`, each with `ForgejoForge(root=tmp_path)` (no repository named, so `repository_name()` answers its problem and no request is made) → `pytest.raises(RuntimeError, match="no Forgejo repository is named")`.
  - `test_a_failed_read_or_update_raises_the_forges_problem`: `rs.fetch_ruleset("n", "develop", forge=RecordingForge(branch_rules=(None, "Forgejo API error 500: boom")))` raises with `"boom"`; `rs.update_ruleset(7, {"name": "x"}, forge=RecordingForge(update_branch_rules=(False, "Forgejo API error 422: no")))` raises with `"422"`.
- Delete `test_api_raises_with_the_apis_own_reason_on_failure` and `test_api_returns_none_for_an_empty_body` (`test/test_rulesets.py:441-449`): their runner is gone, and #338 pins the same failure text on the GitHub verb.
- `fake_gh` argv proofs, each taking `fake_gh, tmp_path, monkeypatch`, with `monkeypatch.setenv("GH_REPO", "o/r")` and `forge=GitHubForge(root=tmp_path)` (no `subprocess.run` patch). `fake_gh.script({...})` replaces every answer, so each test scripts all the argv it will run in one call, keyed by the space-joined argv:
  - `test_fetch_ruleset_refetches_the_named_entry_by_id_for_its_rules` (`:452-466`) and `test_fetch_ruleset_end_to_end_through_the_real_gh_adapter` (`:469-483`, docstring now: it exercises the real GitHub adapter through a real `gh` on `PATH`) script `api repos/o/r/rulesets` (out `json.dumps([{"id": 1, "name": "other"}, {"id": 2, "name": "vibey-gh: develop"}])`) and `api repos/o/r/rulesets/2` (out `json.dumps({"id": 2, "name": "vibey-gh: develop", "rules": []})`), call `rs.fetch_ruleset("vibey-gh: develop", "develop", forge=forge)`, and assert the document; the end-to-end test also asserts `fake_gh.invocations() == [{"argv": ["api", "repos/o/r/rulesets"], "cwd": str(tmp_path.resolve()), "stdin": None}, {"argv": ["api", "repos/o/r/rulesets/2"], "cwd": str(tmp_path.resolve()), "stdin": None}]`.
  - `test_fetch_ruleset_returns_none_when_no_ruleset_has_that_name` (`:485-489`) scripts only the listing (`[{"id": 1, "name": "other"}]`) and asserts `None` and `fake_gh.calls() == ["api repos/o/r/rulesets"]`.
  - `test_create_and_update_ruleset_post_the_payload_as_json` (`:491-505`) and `test_a_request_body_is_actually_sent` (`:596-619`, keep its docstring) script `api repos/o/r/rulesets --method POST --input -` and `api repos/o/r/rulesets/7 --method PUT --input -` with `{"out": "{}", "read_stdin": True}`, call `rs.create_ruleset({"name": "x"}, forge=forge)` and `rs.update_ruleset(7, {"name": "x"}, forge=forge)`, and assert each invocation's argv and `json.loads(invocation["stdin"]) == {"name": "x"}`. The body test also scripts the listing `api repos/o/r/rulesets` (out `"[]"`) in the same `script` call, then calls `rs.fetch_ruleset("x", "develop", forge=forge)`, and asserts that invocation's argv has no `--input` and its `stdin` is `None`.
- Orchestration (`:508-594`): pass `forge=RecordingForge(...)` instead of patching `fetch_ruleset`/`create_ruleset`/`update_ruleset`/`reconcile_one`. Script `branch_rules=(None, "")` or `({**desired, "id": 9}, "")`, `create_branch_rules=(True, "")` or `(False, "422 required status check contexts must be unique")`, `update_branch_rules=(True, "")`. A test that asserts a verb is never called scripts nothing for it (an unscripted verb raises `AttributeError`, which fails the test). Assert what was written from `forge.calls` (for example `("create_branch_rules", rs.build_ruleset("develop", policy()))` for the create test and `"9"` as the update's id).
  - `test_reconcile_covers_the_integration_and_release_branches`: keep its `cfg`; `expected = {"develop": cfg.rulesets.integration, "main": cfg.rulesets.release}`; script `branch_rules` as a callable returning the full answer tuple, `lambda name, branch: (rs.build_ruleset(branch, expected[branch]) | {"id": branch}, "")`; run `outcomes = rs.reconcile(cfg, dry_run=True, forge=forge)`; assert both outcomes are `changed` false and `applied` false, which holds only if each branch was reconciled with its own policy, and that the `branch_rules` calls are `("branch_rules", "vibey-gh: develop", "develop")` then `("branch_rules", "vibey-gh: main", "main")`.
  - `test_reconcile_is_a_noop_when_disabled` passes `RecordingForge()` and asserts `rs.reconcile(cfg, forge=forge) == []` and `forge.calls == []`.
- After the conversion, delete the `completed` helper and `import subprocess` if nothing uses them any more (ruff flags an unused import).

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_rulesets.py test/test_gh_cli.py test/test_forge_branch_rules.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
git diff --stat   # only vibey_gh/rulesets.py and test/test_rulesets.py
```
Nothing here is platform-specific: the same commands prove the change on macOS (the lane host) and on Linux (CI's `tools` job), per 8.h.

## Out of scope
- `flatten.py` (`split-344-2-flatten`), `reconcile.py` (#341), `cli.py`, every adapter file (`vibey_gh/forge*.py`, `vibey_gh/*transport*.py`, anything under `vibey_gh/interfaces/`), `test/conftest.py`, `test/forge_doubles.py`, `test/test_gh_cli.py`.
- This repository's `.vibey-gh.toml`: its `[platform] kind = "github"` declaration is the operator's; it is already on the integration branch (d3b4a388), and the lane never writes or changes it.
- The mapping decision for the default policy on Forgejo: the operator's.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every adapter verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered; otherwise `value` is the empty value for its type and `problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable output (`vibey_gh/interfaces/forge_adapter_interface.py:9-16`). A verb a forge has no equivalent for answers `(<empty>, NotSupported(kind, verb, reason).problem)`, text `f"{kind.value} does not support {verb}: {reason}"`; the caller reports it like any other problem (10.f), never special-cases a forge, never skips silently.

**C5 — branch rules are the ruleset document.** `branch_rules(name, branch) -> tuple[dict[str, Any] | None, str]` answers the document `build_ruleset` builds (`rulesets.py:122-131`) plus `"id"` (a string branch name on Forgejo), so `diff_ruleset` is unchanged. `create_branch_rules(document) -> tuple[bool, str]` and `update_branch_rules(rules_id: str, document) -> tuple[bool, str]` write it. On Forgejo, a document with a rule `branch_protections` cannot express is refused with `forgejo does not support branch rules: no equivalent for <items>` and no request; on GitLab all three answer NotSupported.

**C6 — how this module calls the adapter.** Each public function gains a keyword-only last parameter `forge: ForgeAdapterInterface | None = None` and resolves with `ForgeSelector().resolve(forge, cfg)` (or `.resolve(forge)` without a `cfg`): it returns the injected forge, else `select(cfg)`, else `select(load_config())`. Bind where today's code called `github_state.repository()`: `name, problem = forge.repository_name()`; `if problem: raise RuntimeError(problem)`; `bound = forge.for_repository(name)`. A site that raised keeps raising with the problem as its message.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`). Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never `monkeypatch.setattr` a module or class attribute (`rs._api`, `rs.fetch_ruleset`, `subprocess.run`), never `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv/delenv/chdir` are fine.
- `RecordingForge` (`test/forge_doubles.py`, from `split-332-4-selector-resolve`): `RecordingForge(branch_rules=(document, ""), create_branch_rules=(True, ""))` scripts each verb by keyword; each scripted verb returns its value, or calls it with the verb's arguments if it is callable (so a callable returns the whole `(value, problem)` tuple); `repository_name()` defaults to `("o/r", "")`; `for_repository(name)` records the call and returns the same double; `.calls` lists `(verb, *args, *sorted(kwargs.items()))`; an unscripted verb raises `AttributeError`. Read its class docstring before the first test.
- GitHub argv proofs: the conftest `fake_gh` fixture (`test/conftest.py:87-156`; a real `gh` executable first on `PATH`; `script({...})` keyed by the space-joined argv, with `"read_stdin": true` to capture a body; `calls()` the joined argv lines; `invocations()` with `argv`, `cwd` and `stdin`; an unscripted argv exits 3 with `no scripted answer`).
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch `test/conftest.py`.

**C8 — the formatter trap.** Checked by both `black --line-length 100` + `isort` and the root `ruff format`. Keep lines ≤ 100 columns (≤ 95 with nested calls); bind long comparisons to a local before asserting; no implicit string concatenation that would fit on one line; one argument per line with a trailing comma in multi-line calls; no backslash continuations. If the two fight, restructure the line; never alternate between them.

**Depends on:** forge-0g, split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve
- forge-0g: `branch_rules`, `create_branch_rules`, `update_branch_rules` on all three adapters, with today's GitHub argv, stdin and failure text, and Forgejo's refusal of what it cannot express.
- split-332-1-transport-seams: `NotSupported`, whose sentence the refusal test raises.
- split-332-2-adapter-paging: `ForgejoForge` as the naming-problem test builds it (no request before the name is known).
- split-332-3-repository-name: `repository_name()` on every adapter (GitHub's reads `$GH_REPO`, Forgejo's answers its "no Forgejo repository is named" problem).
- split-332-4-selector-resolve: `ForgeSelector().resolve(forge, cfg)` and `RecordingForge`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
