## Title
fix(gh): vibey-gh's own project declares its forge as github, and a meta test holds every tracked `.vibey-gh.toml` to a declared forge

## Why
Issue #138 (rewrite: `issue-audit/updates/138.md`, "Proposed child issues" 1). Sub-doctrine 8.b
(`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the default forge and
GitHub declared-only; 12.c (`doctrines.md:455`) requires the platform to be declared, never
assumed. vibey-gh ADR 0002 flipped the default `[platform] kind` to `forgejo`
(`src/vibey_tools/gh/vibey_gh/config.py:288`).

The repository root already declares it: `.vibey-gh.toml:14-19` (`[platform] kind = "github"`,
commit `03e59eb4`, merged into `storm/integration` as `d3b4a388`). But this repository tracks
**two** vibey-gh projects (`git ls-files` → `.vibey-gh.toml`, `src/vibey_tools/gh/.vibey-gh.toml`),
and `find_root` (`config.py:1630-1652`) stops at the nearest directory carrying its own
`.vibey-gh.toml`. So every `vibey-gh` command run with `src/vibey_tools/gh` as its working
directory — for example the CI drift step at `.github/workflows/ci.yml:712-720` — loads the
tenant file, which has no `[platform]` table (its tables start at
`src/vibey_tools/gh/.vibey-gh.toml:4` `[fingerprint]` and run to `:220` `[yank]`; none is
`platform`) and therefore resolves to
`PlatformConfig(kind="forgejo")`. When the forge wave (#339–#344, specs `forge-1`…`forge-6`)
routes every command through the adapter, those runs would aim this GitHub repository at
`forgejo.local`. This is the tenant half of the root fix, and a guard so a third project file
can never be added without a declaration.

## Required behaviour
1. `src/vibey_tools/gh/.vibey-gh.toml`: insert, directly after the `[fingerprint]` table (after
   its closing `]` at line 8 and the blank line that follows), this block, copied from the
   root's wording:
   ```
   # This project lives on GitHub. Since vibey-gh ADR 0002 the forge default is the sovereign
   # `forgejo`, and `github` is declared-only -- so the kind is written here rather than
   # inherited. An empty host keeps the `gh` client's own github.com: no `gh` call's argv or
   # environment changes.
   [platform]
   kind = "github"

   ```
2. New root meta test `tests/meta/test_every_vibey_gh_config_declares_its_forge.py`:
   - `REPO = Path(__file__).resolve().parents[2]`.
   - `_tracked_configs() -> list[Path]`: `subprocess.run(["git", "ls-files", "-z", "--", ".vibey-gh.toml", "*/.vibey-gh.toml"], cwd=REPO, capture_output=True, check=True)`,
     split on `"\0"`, drop empties, map to `REPO / name`. (Module-level test helpers, with the
     reason `tests/meta/test_protected_paths_agree.py:15-17` gives, copied as the module
     docstring's last paragraph.)
   - `test_this_repository_tracks_two_vibey_gh_projects`: the sorted relative names are exactly
     `[".vibey-gh.toml", "src/vibey_tools/gh/.vibey-gh.toml"]` (a third file must be added here
     on purpose).
   - `test_every_tracked_config_declares_its_platform_table` (parametrized over the configs,
     `ids` = relative path): `tomllib.loads(path.read_text("utf-8"))` has a `"platform"` table
     with a `"kind"` key — declared, not defaulted.
   - `test_every_tracked_config_resolves_to_github` (parametrized the same way):
     `vibey_gh.config.load_config(path.parent).platform.kind == "github"` and
     `.platform.host == ""`.
3. No code change: the loader already reads `[platform]` (`config.py:1732`).

## Where to change
- `src/vibey_tools/gh/.vibey-gh.toml` (insert one block; use `edit_file` with the
  `[fingerprint]` table's last lines as `old_string`).
- New `tests/meta/test_every_vibey_gh_config_declares_its_forge.py` (provenance header copied
  from `tests/meta/test_protected_paths_agree.py:1`).

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && python -c "from vibey_gh.config import load_config; print(load_config().platform.kind)"` prints `github`.
- [ ] The three meta tests pass.
- [ ] Both rendered automation sets still have no drift (the two drift commands in *Checks*).
- [ ] vibey-gh's own suite still passes with its 100% floor (nothing in it reads the tenant file's platform).

## Tests to write first (TDD)
`tests/meta/test_every_vibey_gh_config_declares_its_forge.py`:
- `test_this_repository_tracks_two_vibey_gh_projects`
- `test_every_tracked_config_declares_its_platform_table` (fails before step 1 for the tenant file)
- `test_every_tracked_config_resolves_to_github` (fails before step 1: the tenant resolves to `forgejo`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta/test_every_vibey_gh_config_declares_its_forge.py
    cd src/vibey_tools/gh && python -c "from vibey_gh.config import load_config; from vibey_gh.install import installed; ok, problems = installed(load_config(), local=False); raise SystemExit('managed automation drift: ' + '; '.join(problems) if not ok else 0)"
    python -c "from vibey_gh.config import load_config; from vibey_gh.install import installed; ok, problems = installed(load_config(), local=False); raise SystemExit('root automation drift: ' + '; '.join(problems) if not ok else 0)"
    cd src/vibey_tools/gh && python -m pytest -q

## Out of scope
- The root `.vibey-gh.toml` (already declared).
- The hosted-origin warning (`roadmap-138-origin-platform-warning`) and gaps.md §L6.
- Any adapter or command change; docs (`docs/configuration.md`) and CHANGELOG.
- This is a human declaration under 8.b: the operator merges it. Do not push; commit locally
  with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
