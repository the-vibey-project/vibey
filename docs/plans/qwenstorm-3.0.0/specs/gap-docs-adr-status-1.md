## Title
docs(adr): ADR-0042's table states 8.b as ratified, ADR-0043 names Forgejo, and the amended records say so

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-194`, as amended by the merge of
#392 on 2026-09-22) names the sovereign default of every surface. ADR-0042's table
(`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:35-46`)
still names `qwenloop`+`opencode` for engines, `bitwarden` for secrets, `forward-email` for
email and `fossify` for SMS, and has no rows for configuration, cache, bus, blob storage or
security events (`issue-audit/gaps.md` M7, lines 671-682). Under 7.b and 10.f a decision record
that contradicts the ratified law misleads the reader it exists for.

ADR-0043 still names Gitea as the forge (`0043-sovereign-surfaces-install.md:24` and `:46`)
and claims every image drops all capabilities (`:74`). Lane `chart-operator-forgejo-p2` (#327)
made the forge Forgejo; its rewritten issue (`STORM/issue-audit/updates/327.md`, "Out of
scope") hands these three lines to the docs wave.

Records amended by later ones must say so on their status line, as ADR-0002 already does for
ADR-0044 (`0002-postgres-not-sqlite.md:3`). ADR-0044 amends ADR-0009 (§6) and ADR-0025 (§12);
ADR-0046 amends ADR-0005 (`0046-two-loops-sovereignloop-and-paidloop.md:3`, landed by
`gap-docs-adr-land`). ADR-0046's own notes on ADR-0015, 0038, 0042 and 0044 are listed in its
"Owes 3" and belong to its docs lane, not this one.

## Required behaviour
1. **ADR-0042 table.** Replace lines 35-46 (the header row through the Messaging row) with:
   ```
   | Surface | Protocol | Sovereign default | Declared-only |
   |---|---|---|---|
   | Engines | `EngineDescriptor`/`EngineProvider` (ADR-0005) | `sovereignloop`: this era's default model (8.d), and VS Code on a local provider | `paidloop`: `claudeloop` (the paid default), `codexloop`, `cursorloop`, `agyloop`, VS Code on a paid provider |
   | Cloud | `CloudClientPort` | self-hosted `openstack` | `aws` (the paid default), `azure`, `gcp` |
   | Forge | `ForgeAdapterInterface` (vibey-gh #138) | self-hosted `forgejo` | `github` (the paid default), `gitlab` |
   | Ticketing | `IssueTrackerPort` | self-hosted free `plane` | `jira`, `linear`, `asana` (+ sibling sovereign `openproject`) |
   | Documentation | `DocsPort` | self-hosted free `bookstack` | `confluence`, `notion`, `gitbook` |
   | Secrets | `SecretsPort` | self-hosted free `openbao` | `lastpass`, `1password`, `proton` |
   | Files | `FilesPort` | self-hosted free `nextcloud` | `gdrive`, `icloud` |
   | Email | `EmailPort` | self-hosted free SMTP: Postfix in the cluster, or a self-hosted Forward Email | `proton`, `gmail`, `apple` |
   | SMS | `SmsPort` | self-hosted free `kannel` gateway; Fossify Messages on the operator's handsets | `google-messages`, `imessage` |
   | Messaging | `MessagingPort` | self-hosted free Matrix (`matrix`/`element`) | `signal`, `discord`, `slack`, `zoom`, `whatsapp`, `telegram`, `messenger`, `facebook`, `instagram`, `tiktok` |
   | Configuration | `ConfigStorePort` | self-hosted `infisical` | hosted equivalents |
   | Cache | `CachePort` | self-hosted Valkey (the Redis protocol) | hosted equivalents |
   | Bus | `BusPort` | self-hosted `rabbitmq` | hosted equivalents |
   | Blob storage | `BlobPort` | self-hosted `garage` (the S3 protocol) | hosted equivalents |
   | Security events | `SiemPort` | self-hosted `wazuh` | hosted equivalents |
   ```
   Then, after the table and before the blank line that precedes `Mechanically:` (`:48`), add
   one paragraph:
   > The table states sub-doctrine 8.b as the merge of #392 left it on 2026-09-22: OpenCode is
   > repealed as an engine of either loop, VS Code takes its place in both, and paid defaults
   > are Claude, VS Code, AWS and GitHub. Bitwarden stays a person's own password vault; it has
   > no self-hostable server for a machine's secrets. The cache is Valkey by the operator's
   > ruling of 2026-09-22; 8.b's "Redis" names the protocol. How the engine pool follows the
   > engines row is ADR-0046. The "Mechanically" list below records how this ADR's own change
   > first did it.
2. **ADR-0043.**
   - Line 24 (it starts `- **Forge: Gitea.**`) is replaced by this line:
     ```
     - **Forge: Forgejo.** Sub-doctrine 8.b names Forgejo as the forge default. The chart runs the rootful `codeberg.org/forgejo/forgejo` image, pinned by `surfaces.forgejo.image.digest` in `deploy/helm/vibey/values.yaml` and configured through `FORGEJO__` environment variables (#327). It replaced `gitea/gitea`. Forgejo migrates data only from Gitea 1.22 or earlier, so the old `<release>-vibey-gitea-data` volume is not reused.
     ```
     Then append one more sentence to that same line. If
     `grep -c "this upgrade would delete the old Gitea volume" deploy/helm/vibey/templates/surfaces.yaml`
     prints 1 or more, append:
     ```
      An upgrade from a Gitea release refuses to render until a human keeps that volume (`helm.sh/resource-policy=keep`) or deletes it.
     ```
     Otherwise append:
     ```
      Helm deletes that volume on upgrade, because the chart no longer renders it; back it up first.
     ```
   - Line 46 (it is `   - **Forge:** Gitea (` then `` `gitea/gitea` `` then `)`) is replaced by:
     ```
        - **Forge:** Forgejo (`codeberg.org/forgejo/forgejo`)
     ```
   - On line 74, the first sentence (it starts `All images run with restricted capabilities`
     and ends at the first `.`) is replaced by:
     ```
     Images run with restricted capabilities (`drop: [ALL]`), with one recorded exception: the rootful Forgejo image's setup needs root to prepare `/data` before it drops to uid 1000, so the forge pod carries no securityContext, as the Gitea pod before it did not.
     ```
     First verify it: in `deploy/helm/vibey/templates/surfaces.yaml`, the block from the line
     containing `8. Forgejo (Forge)` to the line containing `9. Registry` has no
     `securityContext`. If it has one, STOP and report the lines; the sentence would be false.
3. **Status lines** (line 3 of each; exact replacements):
   - `0005-smooth-weighted-round-robin.md`: `**Status:** accepted · **Date:** 2026-08-14` →
     `**Status:** accepted; where the round robin runs, and where its cursor lives in service mode, amended by ADR-0046 · **Date:** 2026-08-14`
   - `0009-human-gates-are-parked-jobs.md`: `**Status:** accepted · **Date:** 2026-08-14 · **Extended by:** ADR-0024` →
     `**Status:** accepted; how an answer re-readies a parked job amended by ADR-0044 §6 (an answer also re-dispatches) · **Date:** 2026-08-14 · **Extended by:** ADR-0024`
   - `0025-kubernetes-operator-crd-keda.md`: `**Status:** accepted; one Consequences clause outdated by ADR-0037 ·` →
     `**Status:** accepted; one Consequences clause outdated by ADR-0037; the autoscaling trigger amended by ADR-0044 §12 ·`

## Where to change
- `docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md`
  (84+ lines: edit_file only).
- `docs/architecture/decisions/0043-sovereign-surfaces-install.md` (edit_file only).
- `docs/architecture/decisions/0005-…`, `0009-…`, `0025-…` (one line each).

## Acceptance criteria
- [ ] The table names none of the repealed or replaced defaults:
      `awk '/^\| Surface \|/,/^$/' docs/architecture/decisions/0042-*.md | grep -c 'bitwarden\|forward-email\|qwenloop\|opencode'`
      prints 0.
- [ ] The table has 15 data rows; `grep -c "^| Security events |" …0042-*.md` prints 1.
- [ ] `grep -n -i gitea docs/architecture/decisions/0043-*.md` shows only line 24's history
      sentence and line 74's "as the Gitea pod before it did not".
- [ ] The three status lines read exactly as in behaviour 3.
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes.

## Tests to write first (TDD)
None. The meta-tests are the tests; `gap-docs-adr-status-2` adds the one that ties statuses to the canon.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    grep -c "securityContext" deploy/helm/vibey/templates/surfaces.yaml
    uv run --with 'properdocs==1.6.7' --with 'properdocs-theme-mkdocs==1.6.7' properdocs build --strict --site-dir "$TMPDIR/vibey-site"
If the pytest session fails at start because no PostgreSQL is reachable, add `--noconftest`.

## Out of scope
- The `**Status:**` word of ADR-0039 to ADR-0049 (`gap-docs-adr-status-2`).
- ADR-0046's status notes on ADR-0015, 0038, 0042 and 0044 (ADR-0046's docs lane).
- ADR-0043's cache line (`:42`, Redis): it describes the chart, which changes only when a lane
  swaps the image to Valkey.
- The chart itself, and every other docs file.

Commit as `docs(adr): ADR-0042's table states 8.b as ratified, ADR-0043 names Forgejo, and the amended records say so`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
