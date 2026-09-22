## Title
feat(gh): `vibey-gh doctor` warns when GitHub Actions runs automation whose forge is the undeclared Forgejo default

## Why
Sub-doctrine 8.b makes Forgejo the default forge and GitHub declared-only. `[platform] kind`
therefore defaults to `forgejo` (`vibey_gh/config.py:288`). Once the forge wave routes commands
through the adapter (#339–#344), an adopter on GitHub who never declared `[platform]` has a
merge train, promotion and PR automation that talk to `forgejo.local`.
`specs/forge-adapter.md:1855-1860` names a doctor warning as the follow-up, and no lane
writes it (`issue-audit/gaps.md` L6, lines 573-578).

Forgejo Actions also sets `GITHUB_ACTIONS=true`, for compatibility. The discriminator is
therefore the server URL, `GITHUB_SERVER_URL`, which is `https://github.com` only on GitHub.
The finding is a **warning**, not an error: a GitHub mirror that relays a Forgejo source of
truth on purpose (8.b's relay rule) may run with `kind = "forgejo"` and a declared `host`.

## Required behaviour
1. `vibey_gh/doctor.py`:
   - `diagnose(cfg=None, root=None)` (`:260-270`) gains the keyword
     `env: Mapping[str, str] | None = None`, where `None` means `os.environ`. It is a declared
     seam, so tests pass a dict.
   - It appends `_check_actions_forge(cfg, env)` after `_check_superseded_headers`.
2. New `_check_actions_forge(cfg: GhConfig, env: Mapping[str, str]) -> list[Finding]`. It is a
   private module function like its siblings (`:104-257`), so the module keeps one style;
   write that reason in its docstring. It returns one `Finding("warning", ...)` exactly when:
   - `env.get("GITHUB_ACTIONS") == "true"`;
   - `urlsplit(env.get("GITHUB_SERVER_URL", "")).hostname == "github.com"`;
   - `cfg.platform.kind == "forgejo"`;
   - `cfg.platform.host` is empty.

   The message is exactly:
   `"GitHub Actions is running this repository's automation, but [platform] kind is 'forgejo' (the default when undeclared), so every command on the forge adapter talks to forgejo.local. Declare [platform] kind = \"github\" in .vibey-gh.toml; or, if GitHub relays a Forgejo source of truth on purpose, set [platform] host to that Forgejo host."`
3. When `kind == "forgejo"` and `host` is set, under GitHub Actions: `Finding("info", f"[platform] forgejo at {host} while GitHub Actions runs the automation: a relay, by declaration")`.
4. Otherwise there is no finding. The doctor's exit code is unchanged, because warnings and
   infos never fail it (`cli.py:932-952`).

## Where to change
- `src/vibey_tools/gh/vibey_gh/doctor.py` (270 lines; edit_file only).
- Tests: append to `src/vibey_tools/gh/test/test_doctor.py`. Build a `GhConfig` the way that
  file already does, and pass `env` explicitly. No `monkeypatch.setattr`; `setenv` is not needed.

## Acceptance criteria
- [ ] GitHub env (`GITHUB_ACTIONS=true`, `GITHUB_SERVER_URL=https://github.com`), with no
      `[platform]`, gives exactly one warning with the exact text.
- [ ] A Forgejo runner env (`GITHUB_ACTIONS=true`, `GITHUB_SERVER_URL=https://forge.example`) gives no finding.
- [ ] `kind = "github"` gives no finding.
- [ ] `kind = "forgejo"` with `host = "forge.example"` under the GitHub env gives the info finding.
- [ ] Outside Actions (an empty env) there is no finding.
- [ ] This repository's own `.vibey-gh.toml` (`[platform] kind = "github"`, `:18-19`) gives
      no finding under the GitHub env.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_doctor.py`:
- `test_github_actions_with_the_forgejo_default_warns`
- `test_forgejo_actions_does_not_warn`
- `test_declared_github_does_not_warn`
- `test_declared_forgejo_relay_is_info`
- `test_outside_actions_nothing_is_reported`
- `test_this_repository_is_clean_under_github_actions`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Making it an error, or failing CI on it. That is an operator decision after forge wave 2.
- Docs.

Commit as `feat(gh): doctor warns when GitHub Actions runs with the forgejo default`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
