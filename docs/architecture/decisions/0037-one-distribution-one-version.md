# 0037 — One distribution, one version: the whole family ships inside `vibey`

**Status:** accepted · **Date:** 2026-09-18 · **Supersedes in part:** ADR-0021, ADR-0019, ADR-0034, ADR-0015

**Owes:** nothing — mechanism (ADR-0020). The conduct rule this applies already
exists: sub-doctrine 2.b, *installable wherever its users already are*, ratified
with ADR-0019. What changes here is how the family is packaged, not how it is
meant to behave, so it files as an ADR and not as a sub-doctrine.

## Context

Ten distributions came out of this tree. Nine of them no longer exist. Measured
against PyPI on 2026-09-18, `curl -o /dev/null -w '%{http_code}'` on
`https://pypi.org/pypi/<name>/json`:

```
vibey                  200    (0.8.0)
vibey-gh               404
vibey-skills           404
vibey-bootstrap        404
claudeloop             404
codexloop              404
cursorloop             404
agyloop                404
qwenloop               404
vibey-runners-common   404
```

The tree had not caught up with that, and the gap was not cosmetic.

**The wheel carries one package.** `[tool.hatch.build.targets.wheel] packages =
["src/vibey"]`. `pip install vibey` delivers the conductor and nothing else —
no engine, no tool — even though the engines and tools are in the same
repository and the conductor cannot work without at least one engine on `PATH`.

**Extras and cross-tenant requirements resolve to nothing.** `vibey[dev]`
requires `vibey-gh>=1.2`; `vibey[skills]` requires `vibey-skills>=2.18,<3`.
`vibey-bootstrap` requires `vibey-gh>=1.70,<2` as a *core* dependency;
`claudeloop` and `codexloop` require `vibey-runners-common`;
`vibey-runners-common` requires the three runners. Every one of those names
404s. CI was already red on it: the `agyloop on 3.12` row of the `tools` matrix
fails with `No matching distribution found for vibey-gh>=1.2`, because the
matrix installs each tenant with plain `pip`, which knows nothing about
`[tool.uv.sources] workspace = true` and therefore goes to the index (ADR-0022
explains why plain pip is deliberate there).

**Sixteen rendered workflows reach for a package that cannot be installed.**
Each managed workflow installs `vibey-gh` from `[install] self_source` and
falls back to `pip install vibey-gh` when that path does not hold the package.
`self_source` defaults to `"."`, so in *any* adopting repository the guard
fails and the fallback runs — which means, with `vibey-gh` unpublished, no
external repository can adopt the managed automation at all.

**And the documentation said the opposite of all of it** — eight README
banners, five runner PyPI links in the most-read table in the repository,
sixteen `pipx install <runner>` lines, a shipped skill instructing
`pip install vibey-bootstrap`, and the release skill's flat assertion that the
tenants "still exist on PyPI under their own names".

ADR-0021 considered exactly this collapse and rejected it. Its final
*Alternatives rejected* bullet reads:

> **One package, one version.** Collapsing eight distributions into `vibey`
> would break every existing `pip install claudeloop` and make a runner bump a
> conductor release. The workspace keeps the distributions independent for
> exactly this reason.

Both halves of that objection are answered below rather than dodged.

## Decision

**The repository publishes one distribution, `vibey`, and it carries the whole
family.** `pip install vibey` delivers the conductor, all five `*loop` engines,
`vibey-gh`, `vibey-skills`, `vibey-bootstrap` and `vibey-runners-common`, with
every console script on `PATH`. Concretely:

1. **The wheel ships every tenant package root, declared as `packages`, not as
   `force-include`.** `packages` maps a directory to a top-level name taken from
   its last path segment, so each tenant lands under its own importable name with
   no renaming and no hand-written file list — and it follows the tree, so a file
   added to a tenant next month is in the wheel without anyone remembering to
   list it. It is also the only form an *editable* install exposes, which
   matters concretely: `.importlinter` names `vibey_gh` a root package, so
   `uv run lint-imports` needs `import vibey_gh` to work in the root
   environment. `force-include` remains for what it is actually for — content
   that must land somewhere it does not live: the 12 MB skills `plugins/` tree
   and its marketplace manifest, and vibey-gh's release site assets.

   One non-obvious consequence is worth writing down, because it fails
   confusingly: `packages` alone derives a source prefix from each entry's
   *parent*, and `src/vibey`'s parent is plain `src/`, which is an ancestor of
   the other nine. Hatchling strips the first matching source in sort order, so
   `vibey_gh/cli.py` landed as `vibey_tools/gh/vibey_gh/cli.py` and the editable
   build failed on "src/vibey_tools is not a valid Python package". A
   `[tool.hatch.build.targets.wheel.sources]` table naming each package's own
   directory fixes it and is not redundant.

2. **No family package is requested from an index, anywhere.** Not in `vibey`'s
   extras, not in a tenant's dependencies, not in a test or tooling extra, not
   in a CI step, not in a rendered workflow. A tenant that needs a sibling at
   runtime now has it because they ship together; a tenant that needs one in CI
   installs it from the tree first, which is the shape ci.yml already used for
   `vibey-runners-common` and now generalises.

3. **The workspace is unchanged.** Every tenant keeps its own `pyproject.toml`,
   version, Python floor, test suite and gates. ADR-0021's subtree import and
   ADR-0022's per-tenant gates stand exactly as written. What ends is separate
   *publication*, not separate *projects* — the distinction ADR-0021 did not
   need to draw because the two had never come apart.

4. **Every extra that named a real dependency is re-homed onto `vibey`, and
   nothing is silently dropped.** `claudeloop[voice]` becomes `vibey[voice]`;
   `vibey-bootstrap`'s Azure core becomes `vibey[azure]`; the ~40 per-feature
   bootstrap extras become one `vibey[bootstrap-all]` carrying every third-party
   package any of them named. `vibey[skills]` is kept as an empty alias rather
   than deleted, because removing a declared key breaks `uv sync --extra skills`
   outright where an unknown extra on `pip install` only warns.

   The aggregate is the one place this decision gives ground, and it is recorded
   as a cost rather than a win. Thirty-odd of those extras were empty markers
   over stdlib-only code, but a handful selected real dependencies per feature,
   and `vibey[bootstrap-all]` installs all of them for someone who wanted one.
   Sub-doctrine 12.c is about not taking a decision away from the next adopter;
   an aggregate takes away the ability to install `apscheduler` without
   `sqlalchemy`. The reason it was accepted anyway: the per-feature names
   described *one package's* optional surface, and there is no longer a package
   for them to qualify — `vibey[scheduler]` would claim a granularity the
   distribution does not otherwise have, in a namespace now shared by nine
   tenants. If a consumer turns up who needs the split, the fix is to add the
   specific extra back under `vibey[bootstrap-<name>]`, not to reinstate forty.

   Either way, every runtime error message that names an extra must be rewritten
   to a spelling that works. Shipping an unactionable `pip install` instruction
   inside the product is the worst version of this bug, not the smallest.

5. **The managed-workflow fallback is repointed at `vibey`, not deleted.** A
   fallback that can never succeed is worse than none — but the fix is to make
   it succeed. `pip install vibey` puts `vibey-gh` on `PATH`, every managed
   template already pins `python-version: "3.12"`, and `[install] pin_version`
   keeps its meaning. Deleting the branch would instead remove the only route an
   external adopter has to the managed automation, and would make a configurable
   key a no-op: less generic, again 12.c.

6. **The version is 1.0.0, and it is derived, not typed.** `vibey-gh`'s
   `bump()` could express only minor and patch, so the number this change
   deserves was unreachable by the deriver that owns it (ADR-0028: the version
   is derived, never chosen). It learns `major`, triggered by the signal the
   repository already uses for that meaning — a `BREAKING CHANGE:` /
   `BREAKING-CHANGE:` footer, or a `!` before the colon in a subject, anywhere
   in the released range — reusing `flatten.py`'s existing parser rather than
   spelling the shape a second time, because the commit `vibey-gh` writes and
   the version `vibey-gh` derives must never disagree.

   The deriver alone is not enough, because a major must still be *reached*
   through a path that classifies. `_classify` returns "nothing to release"
   before it ever consults the breaking marker, so `[version] content_paths`
   widens in the same change from one prefix to fourteen — every `packages`
   root and every `force-include` source in `[tool.hatch.build.targets.wheel]`,
   including the four that are easy to miss because they are not package roots:
   `src/vibey_tools/skills/.claude-plugin/marketplace.json` and vibey-gh's three
   site assets under `docs/stylesheets/` and `docs/javascripts/`. Per-tenant
   `src/` and package-dir prefixes rather than a bare `src/vibey_runners/`, so a
   tenant's `docs/` and `tests/` still release nothing. `code_paths` gains
   `pyproject.toml`, because the root manifest now decides what ships — which
   packages, which console scripts, which extras — and a change confined to it
   must reach a release; the precedent is
   `src/vibey_tools/bootstrap/.vibey-gh.toml`, which has carried it for longer.
   `CITATION.cff` joins `[version] files`, and `apply_version` learns the Citation
   File Format's top-level `version:` to write it: GitHub renders that file as
   "Cite this repository", it had sat at 0.6.0 through two releases, and a
   release that changes the version scheme is the worst one to leave it stale in.
   `deploy/helm/vibey/Chart.yaml`'s `appVersion` is deliberately NOT added: the
   file carries two version keys and the chart's own `version` is a separate
   contract released on its own cadence, so a second config key would be needed
   to say which one moves — worth doing, and not in this change.

   Left narrow, a release that touches only tenants and manifests would classify
   as "nothing to release" and republish 0.8.0 into `skip-existing` — green, and
   publishing nothing. `startswith` cannot express a glob, which is why this is
   fourteen literal prefixes rather than a pattern; teaching `content_paths` to
   accept globs is the more generic answer and the right follow-up.
   `tests/meta/test_shipped_trees_are_reachable.py` binds the list to the wheel
   so an eleventh package root fails a test instead of silently releasing
   nothing, and it binds the same list to the Dockerfile's `COPY` block.

## Rationale

**The split had stopped paying for itself.** Independent distributions buy
independent release cadence. That is worth having when the packages have
independent audiences and independent repositories. Since ADR-0021 they have had
neither: one tree, one CI run, one reviewed pull request per cross-cutting
change. What remained of the split was its costs — nine PyPI projects to
version, nine release paths to keep honest, and a resolver edge between packages
that are built from the same commit.

**The failure mode was the one that matters.** A cross-tenant dependency
resolved from an index is a dependency on a *published artifact*, not on the
code in the tree. When the artifact went away, CI broke; when it drifted, the
tree would have been testing a combination nobody had reviewed. Shipping
together removes the edge rather than pinning it.

**One install instruction is the product.** `vibey doctor` reports an engine
`NOT INSTALLED` and the remedy used to be a second, third and fourth install.
The conductor's own value proposition is that it does the babysitting; asking
the user to assemble the fleet by hand before it can start was the first thing
it made them do.

## Consequences

**A runner change is now a conductor release.** This is the half of ADR-0021's
objection that is simply true, and it is accepted: it is the price of the
artifact and the tree agreeing. It is also smaller than it was in 2026-09-15,
because `[version] content_paths` had to widen anyway — under the old setting a
runner change released *nothing at all*, which is worse than releasing too
often. The widening is exact rather than generous: fourteen prefixes derived
from the wheel's own `packages` and `force-include` lists, with a meta test
holding the two together.

**Every `pip install claudeloop` breaks.** This is the other half, and it is
why the version is 1.0.0 rather than 0.9.0. It is not made worse by this
decision: the distributions were already gone before this change was written,
so the install those users type already fails. What this change fixes is that
it now fails with a documented replacement instead of a 404 and a README that
insists the package exists.

**The published Python floor is 3.12, and only 3.12.** `vibey` requires
`>=3.12`, so the 3.10 floor `claudeloop`, `vibey-runners-common` and
`vibey-skills` used to publish, and the 3.11 floor `vibey-gh` and
`vibey-bootstrap` used to publish, cease to exist as shipped artifacts. The
tenants keep those floors and CI keeps running them (ADR-0022), which means CI
now exercises floors nothing ships. ADR-0022's own line — *a floor nothing runs
on is a claim* — cuts the other way here, and this is recorded rather than
quietly dropped: the floors are kept because a tenant that is importable at 3.10
is a tenant that can be extracted again, and because lowering `vibey`'s own
floor to 3.10 would be a much larger decision than this one.

**The wheel is roughly 15 MB.** About 12 MB of that is the skills `plugins/`
tree, which the `vibey-skills` wheel already carried; the rest is ~4.7 MB of
source. This is a transfer of weight between distributions, not new weight —
but it lands on everyone who installs `vibey`, where before it landed only on
people who asked for skills.

**The container build context grows, and ADR-0021's image-size argument is
reversed.** `deploy/docker/Dockerfile` copied `src/vibey/` and
`src/vibey_tools/skills/` deliberately, because `COPY src/ ./src/` had been
shipping ~160 MB of sources into an image that could not execute them
(ADR-0021). The final `uv sync` builds the project, so hatchling now demands
every path `[tool.hatch.build.targets.wheel]` names: ten package roots, five
force-include sources, and the nine tenant manifests uv's workspace globs
require of any member directory present in the context. Without them the build
dies on `FileNotFoundError: Forced include not found`, which is how this was
found — the `image` job fails on both arches and takes `cluster-smoke` with it.

The discipline is kept even though the premise is reversed: the list is exactly
those paths and no further, so each tenant's `tests/`, `docs/` and README still
stay out, and the measured context is ~25 MB rather than the ~160 MB
`COPY src/ ./src/` produced. Two things keep it honest —
`tests/meta/test_shipped_trees_are_reachable.py`, which fails when a declared
path has no `COPY`, and a fifth image contract asserting all eleven console
scripts resolve on `PATH` in the runtime stage, which is the cheapest proof the
bundle survived the copy list at all.

The dependency layer got *simpler* in the same change: it no longer needs a
workspace member. `vibey[skills]` used to require `vibey-skills`, so uv had to
build that member to resolve it; with no family package a requirement of
anything, `--no-install-project` resolves third-party dependencies alone and
that layer caches on the lockfile by itself.

**A bundled tool's `--version` is its tenant's, not the distribution's.**
`claudeloop --version` prints 0.8.0, `vibey-gh --version` 1.73.0,
`vibey_bootstrap` 4.2.3 — inside a wheel that is 1.0.0. That is deliberate and
follows from ADR-0021/ADR-0022 keeping the tenants as projects with their own
version lines; it is recorded here because it is genuinely confusing and was
worth a decision rather than a shrug. The distribution's version is
`vibey --version`. Nothing resolves its version through `importlib.metadata`
(checked across `src/vibey`, `src/vibey_runners` and `src/vibey_tools`), so no
tenant raises `PackageNotFoundError` now that the distributions are gone — the
numbers are literals and they are the tenant's own. If the mismatch proves
confusing in use, the fix is for each tenant's version output to name both, not
to collapse the tenants' versions into one.

**Five shipped error paths named an extra that no longer exists.**
`vibey_bootstrap`'s guarded optional imports raised
`pip install vibey-bootstrap[scheduler]`, `[retry]`, `[servicebus]` and
`[fastapi]` (twice). The distribution 404s *and* no distribution provides those
extra names, so a user hitting one had no actionable next step at all. All five
now name `vibey[bootstrap-all]`, the aggregate Decision 4 created, and keep the
feature word in the prose so the message still says what is missing. The same
class, one level smaller: `claudeloop voice` pointed at `claudeloop[voice]`,
which is now `vibey[voice]`.

**The fallback distribution became a key, not a constant.** The rendered
workflows and the pre-push hook each carried their own literal for "what to
install when this repository has no copy of the tooling". They drifted — the
workflows moved to `vibey` and the hook went on saying `pip install vibey-gh`,
correctly rendered and therefore invisible to the drift check. They now render
from one `[install] fallback_package`, defaulting to `"vibey"`, which is what
sub-doctrine 12.c asks for: a fork, a mirror or an internal index publishing
this tooling under another name has somewhere to say so, and the alternative was
an adopter hand-editing rendered output that `installed()` then reports as drift.
Rendering the hook rather than copying it verbatim is the one behavioural change
this needed; `installed()` compares against the rendered text, so a deployed hook
is still exactly reproducible.

**A bump now re-renders the workflows it pins.** With `[install] pin_version`
on, each managed workflow pins the fallback to *this repository's own*
`[project] version`, so the deployed copies are a function of the number
`apply_version` writes. Bumping without re-rendering left every one of them
pinning the previous release, and — now that CI gates the root copy's drift as
well as vibey-gh's — would fail on the release commit itself. `apply_version`
therefore re-renders them in the same breath, exactly as it already re-ran
`uv lock` and for exactly the same reason.

**Provenance jobs pull more than they did.** The rendered fallback now installs
`vibey`, which carries typer, asyncpg, structlog and textual, where a
stdlib-only `vibey-gh` carried nothing. Across sixteen rendered steps that is
real time, and it is a standing argument for keeping `vibey`'s core
`dependencies` small and pushing anything heavy — the Azure stack above all —
behind an extra.

**One marketplace, for real.** ADR-0034 named the root manifest `vibey` rather
than `vibey-skills` because Claude Code registers one marketplace per name and
a packaged `vibey-skills` manifest would have collided. There is no packaged
`vibey-skills` any more, so the collision it avoided cannot occur. The decision
stands on its own merits — the root is where `/plugin marketplace add
owner/repo` looks — but its stated rationale is now history.

## Alternatives rejected

- **Re-publish the nine tenants.** The distributions were removed
  deliberately; restoring them would restore the resolver edge, the nine
  release paths and the nine version numbers, and would leave the product's
  install story as "run four commands and hope they agree". Rejected as undoing
  the decision rather than implementing it.

- **A meta-package: keep the tenants published, make `vibey` depend on all of
  them.** This is the shape that preserves independent cadence and gives one
  install instruction. It requires the tenants to exist on an index, which is
  precisely what is no longer true, and it reintroduces the edge where the tree
  and the resolved artifact can disagree. Rejected on both counts.

- **`force-include` the tenant trees into the wheel instead of `packages`.** It
  would produce a similar wheel and a worse repository: ten hand-written path
  pairs per tree that silently miss files added later, and no editable-install
  exposure, which breaks `uv run lint-imports` at Gate 5. The two in-tree
  `force-include` pairs already in the tenants (agy's baselines, cursor's
  OpenAPI file) are belt-and-braces over paths `packages` already covers, not a
  precedent for this.

- **Vendor copies of the tenants under `src/vibey/`.** Same wheel, but the
  workspace, the per-tenant gates and the preserved history all go — everything
  ADR-0021 bought.

- **Re-home all ~40 bootstrap extras under `vibey[bootstrap-<name>]`.** The
  most configurable answer, and the first one written into this record. Not
  taken: the names qualified one package's optional surface, and forty
  per-feature keys in a distribution namespace shared by nine tenants claim a
  granularity nothing else in it has. The cost is stated in Decision 4 rather
  than argued away, and the door back is one extra at a time.

- **Hand-write `1.0.0` and leave the deriver as it was.** The number would be
  correct once and unreproducible afterwards: the next release would derive from
  a version the machine does not believe it could have produced. ADR-0028 made
  the version derived on purpose; the fix for a deriver that cannot say what the
  repository needs to say is to teach it, not to work around it.
