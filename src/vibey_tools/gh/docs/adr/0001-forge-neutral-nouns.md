# 0001 — The forge-neutral nouns

**Status:** proposed — needs operator ratification · **Date:** 2026-09-18 ·
**Issue:** [#138](https://github.com/the-vibey-project/vibey/issues/138)

The vocabulary below is an operator decision. It was defaulted to these names while the
operator was away, and it binds only once the operator ratifies it by merging the change
that carries it. Until then, every name here may still change.

## Context

vibey-gh speaks to exactly one forge, and it does so in that forge's own words. Its modules
run `gh pr list`, read `headRefName` and `isDraft`, and call the result a pull request.
#138 asks for one platform-neutral standard with an adapter per forge: GitHub, then GitLab,
then Forgejo, which is the rung that lets the whole pipeline run on one machine with no
cloud at all. Nothing above an adapter may name a platform.

That needs a vocabulary first. The code above the adapter has to call a GitHub pull request
and a GitLab merge request by one name, and every adapter has to agree on what that name
holds. The forge snapshot (#136) and forge capture (#145) need the same nouns, so the names
are settled once, here, rather than three times.

The `gh` transport (`vibey_gh.gh_transport`, the slice before this one) already gives the
package one way to run `gh`. It does not say what the answers mean. This decision does.

## Options

1. **Borrow GitHub's names** (`PullRequest`, `Ruleset`). Every GitLab adapter would then
   translate into a foreign vocabulary, and "ruleset" means something GitLab does not have.
2. **Borrow each forge's names per adapter**, with no shared nouns. The code above the
   adapter would have to know which forge it is talking to, which is the thing #138 forbids.
3. **Neutral nouns in one module, pure data**, with each adapter translating into them.

## Decision

Option 3. `vibey_gh/forge.py` holds these frozen records:

| Noun | Is | GitHub | GitLab | Forgejo |
|---|---|---|---|---|
| `ForgeKind` | which forge (an enum: `github`, `gitlab`, `forgejo`) | | | |
| `ForgeRepository` | one repository: kind, host, owner (the whole namespace), name | repository | project | repository |
| `ChangeRequest` | a proposed change, bound to its exact head SHA | pull request | merge request | pull request |
| `ForgeComment` | a comment, with the forge's own opaque id | issue comment | note | comment |
| `CheckResult` | one check's conclusion on one exact commit | check run / status | pipeline job | commit status |
| `ForgeRelease` | a release, draft or published | release | release | release |
| `ForgeLabel` | a label | label | label | label |
| `ProtectedRef` | a branch the forge will not let anyone rewrite | ruleset / branch protection | protected branch | protected branch |

Four rules come with them:

- **Nouns carry identity and nothing speculative.** A field is added by the first verb that
  reads it from a real forge, never ahead of one. `ForgeRelease` is the only noun a verb
  returns today, so it is the only one whose fields have been tested against a forge.
- **A verdict binds to a SHA.** `ChangeRequest` and `CheckResult` carry the commit they are
  about, because a change request's head moves and a verdict about "the head" is a verdict
  about nothing in particular.
- **Every adapter verb answers `(value, problem)`.** `problem` is empty exactly when the
  forge answered. The shape comes from the clean-repo survey (sub-doctrine 9.a), which
  learned that a forge that could not be asked must never read as a forge that said
  "nothing". It is the contract of `ForgeAdapterInterface`, not a habit of one caller.
- **A verb arrives with its first caller** (vibey-gh PR #186). The interface declares
  `open_change_request_heads` and `releases` because the clean-repo survey reads them; it
  declares nothing else yet.

`[platform] kind` chooses the adapter, through `vibey_gh.forge_selector`, which is the one
place a platform is named by kind. `github` is the only kind with an adapter. `gitlab` and
`forgejo` are named by the standard and refused at load with "the … adapter is not
implemented yet", because every command that has not moved onto the adapter still speaks
to GitHub directly, and accepting the key would have them drive the wrong forge quietly.

## Security impact

None to the trust boundary. The adapter runs the same `gh` command lines in the same
working directory that the survey ran before, which `test/test_forge_github.py` proves by
driving the old code and the new through one fake `gh`. `[platform] host` is new input that
reaches `gh`'s environment as `GH_HOST`, so it is validated as a bare host name (no scheme,
path, user or whitespace) and exported only when it is not `gh`'s own default. It never
reaches a shell.

## Migration

None for an adopter. `[platform]` defaults to `kind = "github"`, `host = "github.com"`, and
that default changes neither the argv nor the environment of any `gh` call. Modules move
onto the adapter one at a time, each with its own before/after proof; the clean-repo survey
is the first.

## Consequences

- A GitLab or Forgejo adapter implements two verbs today, not the whole of vibey-gh, and
  grows one verb at a time as modules move over.
- Renaming a noun after ratification is a breaking change to every adapter, so the names
  are an operator decision now rather than a refactor later.
- Some fields a later forge needs will be missing from these records. That is by design:
  the verb that needs one adds it, with a test against a real answer.
