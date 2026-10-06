# 0084 — A rolling nightly of every krypton interface, from the release builders

**Status:** accepted · **Date:** 2026-10-06 · **Cites:** sub-doctrines 10.f, 12.c, 12.d and 12.e · **Related:** ADR-0059, ADR-0067, ADR-0069, ADR-0083 · **Evidence:** `release-binaries.yml` and `scripts/release_binaries.toml` at `0f594d6f3`

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry for this record; `docs/llms.txt`
regenerated from that nav. All are in the change that carries this record.

## Context

The operator asked for a daily release of the krypton user interfaces. Today they reach people
only with a versioned release on `main`. `release-binaries.yml` builds every interface on
GitHub-hosted runners: desktop Flatpak and tarball, macOS `.dmg`, app web bundle, `.apk` and
`.ipa`, the `.vsix`, and the krypton launcher's wheel. It runs after a successful release, and
attaches the files, with `SHA256SUMS` and a provenance attestation, to the version's GitHub
Release. The app has a `nightly` identity and the desktop a `channel=nightly` build option.
No workflow publishes either.

A second set of builders would drift from the first. Publishing every day to a store, PyPI or
Open VSX is public and largely irreversible, and a store's review makes a daily cadence
meaningless for iOS and Android.

## Decision

1. **A `nightly` mode of the release builders**, not a second workflow. It builds every target
   from the integration branch's source, as a dry run does, and holds the files to the same
   plan and checksums.
2. **One rolling prerelease.** `[release_binaries.nightly]` declares the tag
   (`krypton-nightly`), the title and the paths the interfaces ship from. A new `nightly` job,
   which checks out nothing from the tree as `attach` does, creates the prerelease or moves
   that one tag to the commit built. It removes files an earlier nightly carried that this one
   does not, uploads the rest, and verifies every file and size. The release is a prerelease
   and never `latest`.
3. **Daily, but only when something moved.** The workflow gains a nightly `schedule`, and
   `continuation_prompts.py check` holds it to firing every day. A night when no path under
   `paths` changed since the commit the tag names builds nothing. The compare API lists at
   most 300 files, so a longer list counts as changed. A dispatch with *nightly* builds now,
   from `develop` only.
4. **Signing is the release's.** Each file is signed by whichever credentials the repository
   holds. A target that lacks its credential is left out of the nightly without opening a
   tracking issue, which the versioned release keeps.
5. **Checked, not assumed.** `release_binaries.py check` fails when a nightly is declared and
   the workflow has no schedule. The meta-tests hold the `nightly` job to running nothing from
   the tree, writing only its prerelease, and refusing a tag that names another commit.

## Consequences

- Anyone can install today's interfaces from one stable URL, checked against `SHA256SUMS` and
  the attestation, without waiting for a version.
- The `krypton-nightly` tag moves. It is the one tag a lane rewrites, declared as such, and a
  ruleset protecting it would make the job fail loudly rather than publish stale files.
- A night with changes costs an hour or so of GitHub-hosted Linux and macOS runner time. A
  quiet night costs one short planning job.
