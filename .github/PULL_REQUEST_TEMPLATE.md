## What does this change?

<!-- One or two sentences: the problem first, then what this does about it. Link the issue it closes, if any. -->

## Checklist

<!-- First pull request here? Welcome. Tick what you can, and say which boxes you could not tick or did not understand — a reviewer will help with the rest. The first-hour guide covers the basics: https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour -->

- [ ] Branched from `develop`; targets `develop` (not `main`)
- [ ] Commits (or the squash-merge title) follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] `uv run vibey-gh check` passes (file headers and `Made-With:` trailers)
- [ ] `uv run pre-commit run --all-files --hook-stage pre-push` passes
- [ ] If a tenant under `src/vibey_runners/` or `src/vibey_tools/` changed, its own checks pass (CONTRIBUTING → The workspace tenants)
- [ ] New or changed classes have an interface beside them (ADR-0016)
- [ ] All four 100% branch-coverage gates pass (`domain`, `application`, `infrastructure`, `cli`)
- [ ] Protected tests untouched (or maintainer sign-off noted here)
- [ ] Agent-surface trees (`.claude/skills/`, `.cursor/rules/`, `.agents/skills/`, `.agent/rules/`) updated if a procedure changed
- [ ] Docs updated if behavior changed; a new ADR bumps the count and the nav
- [ ] A user-visible change adds a changelog fragment (`changelog.d/<slug>.<type>.md`), never an edit to `CHANGELOG.md` (CONTRIBUTING → The changelog)
- [ ] Any new governing rule is proposed as a sub-doctrine with the corpus index regenerated (ADR-0020)
- [ ] I agree to the [Code of Conduct](https://github.com/the-vibey-project/vibey/blob/develop/CODE_OF_CONDUCT.md) and to license this contribution under the MIT License
