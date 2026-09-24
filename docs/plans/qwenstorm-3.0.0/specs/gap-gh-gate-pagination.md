## Title
fix(gh): the exact-head gate reads every page of check runs on GitHub

## Why
Constitution Article V.1 requires the merge train to judge the **exact** head, and 10.f
(`src/vibey_tools/gh/docs/doctrines.md:419`) forbids a verdict wider than its evidence. The
gate read calls `repos/{R}/commits/{sha}/check-runs` once:
- `vibey_gh/merge_train.py:290-313`, `_include_exact_head_gate`;
- after forge-0b and forge-1, `GitHubForge.get_check_results` (`vibey_gh/forge_github.py:199-219` today).

GitHub returns 30 check runs per page by default. On a head with more than 30 runs (this
repository's CI matrix alone has dozens of jobs), a required gate on page 2 is invisible. The
train then waits, or judges on a partial list. `specs/forge-adapter.md:1873` records this as
"latent GitHub behaviour kept byte-for-byte", so no forge lane fixes it
(`issue-audit/gaps.md` L5).

The Forgejo and GitLab adapters page with declared `page_size` and `max_pages` fields
(`split-332-2-adapter-paging`). The GitHub adapter gets the same shape (10.e: one pattern in the family).

## Required behaviour
1. `GitHubForge` (`vibey_gh/forge_github.py:38-43`) gains two dataclass fields after
   `transport`: `check_page_size: int = 100` and `check_max_pages: int = 50`. They are fields,
   not literals, because a forge's page limits are the adopter's to tune (12.c).
2. `get_check_results(head_sha)`, in the shape forge-0b leaves it (returning
   `tuple[CheckResult, ...]` and a problem), reads pages:
   - for `page` from 1 to `check_max_pages`, argv
     `["api", f"repos/{R}/commits/{head_sha}/check-runs?per_page={check_page_size}&page={page}"]`
     through the same `_read`/`transport.survey` call it uses today;
   - it keeps today's validation per page (an object with a `check_runs` list) and its problem texts;
   - it collects every page's `check_runs`;
   - it stops after the first page with fewer than `check_page_size` items, or once the
     collected count reaches the page's `total_count` when present;
   - if `check_max_pages` pages were read and the last was full, it returns
     `((), f"check-runs for {head_sha} exceed {check_max_pages} pages of {check_page_size}; refusing a partial gate read")`.
     That is loud, never a silent truncation.
3. Result construction is unchanged, so gate names and conclusions are read exactly as before.
4. If `merge_train._include_exact_head_gate` still calls `gh api` directly at the time the lane
   runs, because forge-1 has not yet routed it, stop and report BLOCKED. This lane's dependency
   on forge-1 exists to prevent that.

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_github.py` (edit_file).
- Tests: append to `src/vibey_tools/gh/test/test_forge_github.py`, with a transport double
  implementing `GhTransportInterface` (`vibey_gh/interfaces/gh_transport_interface.py`) that
  answers per argv. Use the routed double from `split-332-2-adapter-paging` if it exists
  (`grep -rn "class .*Routed" src/vibey_tools/gh/test`). No patching.
- No new interface. `get_check_results` is already on `ForgeAdapterInterface`, and the new
  fields are configuration of an existing class.

## Acceptance criteria
- [ ] 130 check runs over two pages (100 + 30): all 130 are returned, the second argv carries
      `page=2`, and there is no third request.
- [ ] A required gate that appears only on page 2 is returned.
- [ ] `total_count: 100` on a full first page stops after one request.
- [ ] 50 full pages give the exact refusal text and an empty tuple.
- [ ] A malformed page 2 returns today's problem text for a malformed page.
- [ ] Every existing test in `test_forge_github.py` and `test_merge_train*.py` passes; the argv
      assertions for the single-page case are updated only where a test pinned the
      un-paginated URL, and each such edit is listed in the commit body.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_forge_github.py`:
- `test_check_results_read_every_page`
- `test_a_gate_on_page_two_is_seen`
- `test_total_count_ends_the_listing`
- `test_too_many_pages_is_refused_not_truncated`
- `test_a_malformed_later_page_is_a_problem`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Other GitHub listings (a follow-up if any are found unpaginated); the Forgejo and GitLab adapters; docs.

Commit as `fix(gh): the exact-head gate reads every page of check runs`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
