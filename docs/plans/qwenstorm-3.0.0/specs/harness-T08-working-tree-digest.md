## Title
feat(test-harness): a digest of the working tree a test run reads

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:279-282`) keys a run by "the
tree" it tests. Draft ADR-0045 §5 defines that as what `git add -A` would record: the index,
plus each modified, deleted and untracked-but-not-ignored path. That is what a storm lane
actually tests (uncommitted edits, and new test files it never added), which a HEAD tree id
would miss. The digest must:
- write nothing to `.git` and never touch the real index, so it is safe inside a hook;
- run git with every `GIT_*` variable stripped, because a hook exports `GIT_DIR`
  (`.githooks/framework-hook.sh:35-53`). `CleanGitEnvSubprocessExecutor`
  (`src/vibey/infrastructure/git/clean_env.py:23-38`) already does that; it is the family's, so
  it is used (10.e).

`.hypothesis/` is not in the root `.gitignore` (`.gitignore:1-20`), although the runner
tenants ignore it (for example `src/vibey_runners/claude/.gitignore:22`). A Hypothesis run writes
there, so without an exclusion every run would look as if it had changed the tree it tested.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/tree_digest.py`:
1. **`WorkingTreeDigestError(RuntimeError)`**, carrying the failing command's stderr in its message.
2. **`WorkingTreeDigest(executor: CommandExecutor | None = None, *, exclude: tuple[str, ...] = (".hypothesis/",), batch_size: int = 200)`**.
   `executor` defaults to `CleanGitEnvSubprocessExecutor()`. `CommandExecutor` is the Protocol at
   `src/vibey/infrastructure/interfaces/__init__.py:72-73` (`async execute(argv: tuple[str, ...]) -> CommandResult`,
   `CommandResult(returncode, stdout, stderr)` at `src/vibey/infrastructure/engines/claudeloop_process.py:26-31`).

   `async def digest(self, cwd: Path) -> str`:
   1. `git -C <cwd> rev-parse --show-toplevel`. A non-zero exit returns
      `"untracked:" + uuid.uuid4().hex`, which never matches anything, so it is never reused.
      Otherwise `top` is the stripped stdout.
   2. `pathspec = (".", *(f":(exclude){p}" for p in exclude))`.
   3. `git -C <top> ls-files -s -z -- <pathspec>`. Parse each NUL-terminated record,
      `"<mode> <blob> <stage>\t<path>"`, into `entries[key] = (mode, blob)`, where `key` is `path`
      for stage `0`, and `f"{path}\x00{stage}"` with `blob = f"{blob}:{stage}"` for a conflicted stage.
   4. `git -C <top> ls-files -z -m -d -o --exclude-standard -- <pathspec>` gives the changed
      paths. De-duplicate them. For each one:
      - if `os.path.lexists(top / path)` is false, remove `entries[path]` (it was deleted);
      - if the path ends with `/` (a nested repository), skip it;
      - if it is a symlink, set `entries[path] = ("120000", "link:" + hashlib.sha256(os.readlink(top / path).encode()).hexdigest())`;
      - otherwise collect it for hashing.
   5. Hash the collected paths in batches of `batch_size` with
      `git -C <top> hash-object -- <paths...>`, which prints one id per line in input order. The
      mode is `"100755"` if `os.access(top / path, os.X_OK)`, else `"100644"`.
   6. Build `f"{mode} {blob}\t{path}"` for every entry (a conflicted key keeps its
      `path\x00stage` form) and return
      `"wt1:" + hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()`.
   7. Any git command after step 1 that exits non-zero raises `WorkingTreeDigestError` carrying its stderr.
3. **The interface** `src/vibey/infrastructure/test_harness/interfaces/tree_digest_interface.py`
   declares `@runtime_checkable` `WorkingTreeDigestInterface` with `digest`.
4. **`.gitignore`**: add `.hypothesis/` on the line after `.coverage.*` (`:8`).
5. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry: `REGISTRY`,
   `PENDING` from a port's `__qualname__` to the lane that owes its fake, `DRIVER_SEAMS`), import
   `from vibey.infrastructure.test_harness.interfaces import tree_digest_interface`, append
   `tree_digest_interface.WorkingTreeDigestInterface` to `DRIVER_SEAMS`, and add
   `"WorkingTreeDigestInterface": "fakes-test-harness"` to `PENDING` (fakes-test-harness registers
   `ScriptedTreeDigest`).

## Where to change
- New `src/vibey/infrastructure/test_harness/tree_digest.py` and its interface module.
- `.gitignore` and `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_tree_digest.py`.

## Acceptance criteria
- [ ] The same content gives the same digest. Each kind of change gives a different one: a modified tracked file, a new untracked file, a deleted file, a flipped executable bit.
- [ ] An ignored file and an excluded path (`.hypothesis/…`) do not change the digest.
- [ ] The digest equals one computed from `git add -A`'s view: in the test, build that view with a temporary index (`GIT_INDEX_FILE=<tmp> git read-tree HEAD && git add -A && git ls-files -s`) and apply the same line format. This is the ADR-0045 *Verification owed* item for `git ls-files -m -d -o` plus `git hash-object`.
- [ ] A `GIT_DIR` in the caller's environment, pointing at another repository, does not change the result.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_tree_digest.py` (`from vibey.infrastructure.test_harness import tree_digest as td`).
Write a helper class `ScratchRepo` that runs `git init -q -b main`, sets `user.name` and
`user.email`, and commits, using `subprocess.run` with
`{k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"GIT_CONFIG_NOSYSTEM": "1"}`
(git is inside the default tier; the repositories live under `tmp_path`):
- `test_same_tree_same_digest`
- `test_modified_tracked_file_changes_the_digest`
- `test_untracked_file_changes_it_and_an_ignored_file_does_not`
- `test_deleted_file_changes_the_digest`
- `test_executable_bit_changes_the_digest`
- `test_symlink_target_changes_the_digest`
- `test_excluded_path_does_not_change_the_digest`
- `test_digest_matches_git_add_all_view`
- `test_outside_a_work_tree_is_untracked_and_unique`
- `test_callers_git_dir_is_ignored` (`monkeypatch.setenv("GIT_DIR", str(other_repo / ".git"))`)
- `test_git_failure_raises`: use `ScriptedCommandExecutor` from `tests/fakes/process.py` (lane
  fakes-process-executor; read its constructor there). Script only the
  `("git", "-C", str(cwd), "rev-parse", "--show-toplevel")` prefix to succeed with the top
  directory; the unscripted `ls-files` call then gets its `CommandResult(127, ...)`, and
  `digest` raises `WorkingTreeDigestError`.
- `test_digest_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/infrastructure/git tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The key itself (harness-T01) and its use (harness-T13, T14a). The scripted digest fake (fakes-test-harness).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T05-test-harness-config (the package), fakes-registry, fakes-process-executor (`ScriptedCommandExecutor`).
- **Files touched:** the two new source files, `.gitignore`, `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** `tests/infrastructure/git/*` (`test_clean_env.py` in particular), `tests/meta/test_githooks_reach_the_framework.py`, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (the `executor` keyword). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out); `git` and `tmp_path` are inside.
  - No test waits longer than 5 s. POSIX only.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
