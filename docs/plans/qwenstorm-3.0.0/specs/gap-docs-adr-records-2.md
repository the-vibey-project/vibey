## Title
docs(adr): decision records for 8.d (the default model, chosen by measurement) and 8.h (Arch Linux and macOS)

## Why
Sub-doctrine 12.b and ADR-0020 require a decision record beside every ratified rule. No file
under `docs/architecture/decisions/` cites 8.d or 8.h (`issue-audit/gaps.md` M8, lines 684-692).
- 8.d, the living model standard, with its designated default for this era (GPT-OSS 20B on
  Ollama, recorded 2026-09-22): `src/vibey_tools/gh/docs/doctrines.md:236-269`.
- 8.h, the default operating systems: `doctrines.md:326-333`.
The code already follows 8.d: `DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"`
(`src/vibey/infrastructure/engines/ollama_chat.py:39`), qwenloop's `DEFAULT_ENDPOINT_MODEL`
(`src/vibey_runners/qwen/src/qwenloop/domain/config.py:16`) and vibey-gh's fallback reviewer
(`src/vibey_tools/gh/vibey_gh/config.py:502`), from lanes `default-model-p1`–`p3`. 8.h is
carried by CI (`gap-ci-arch-gates`, `gap-ci-macos-gates`) and the installer (ADR-0048).

## Required behaviour
1. Numbers: the four digits of `ls docs/architecture/decisions | tail -1` are `L`
   (after `gap-docs-adr-records-1`, `0051`). The 8.d record is `NC = L+1`, the 8.h record
   `ND = L+2`, zero-padded (`0052`, `0053`).
2. `docs/architecture/decisions/<NC>-the-default-model-is-chosen-by-measurement.md` (about
   60-90 lines, every section present, plain words, from these facts):
   - Line 1: `# <NC> — The default local model is chosen by measurement and recorded with its evidence: GPT-OSS 20B on Ollama, for this era`
   - Line 3: `**Status:** accepted — sub-doctrine 8.d, which it argues, is ratified · **Date:** <date +%F> · **Cites:** sub-doctrines 8.d, 8.a, 10.f, 12.c · **Related:** ADR-0015, ADR-0027, ADR-0038, ADR-0046, ADR-0048 · **Evidence:** the tree at the commit this record lands on, and 8.d's recorded measurement`
   - `**Owes:**`: the conduct rule is 8.d; its designation paragraph is the one part of the
     canon written to be replaced by a ratified amendment when a better free model is measured.
   - `## Context`: the previous default, Qwen2.5-Coder-14B on llama.cpp, ran a ten-turn agent
     session in 215 seconds at a 32,768-token context; GPT-OSS 20B on Ollama ran it in 86
     seconds at 131,072 tokens in 13.1 GB, on an M5 with 24 GB, and a live storm lane on it
     averaged about thirteen seconds a turn (all from 8.d's text). It is 13.8 GB on disk.
     Ollama returns the model's reasoning in `message.thinking`, separately from
     `message.content`, and only `message.content` is read.
   - `## Decision`, five numbered points:
     1. Every install that configures nothing asks Ollama for `gpt-oss:20b`: vibey's own
        providers, qwenloop's endpoint default and vibey-gh's local reviewer and `fit`
        (the three constants above).
     2. Where the model does not fit the machine, the catalogue's default for that RAM tier
        applies (`local-model-catalogue`, `split-383-4-ram-tier-selection`). Other models are
        opt-in alternatives, except in tiers where GPT-OSS 20B does not fit; within a tier an
        OSI-approved licence wins a tie (the operator's ruling of 2026-09-22; 8.a).
     3. Every catalogue entry pins its weights (source, revision, digest) and records the
        evidence and the date behind its choice (8.d). The bench that produces that evidence
        is `qwenloop model bench <entry>` (`gap-models-bench-*`); its results are appended to
        the tree, dated.
     4. The model is served by Ollama by default; llama.cpp applies once its own weights are
        pinned there (8.d).
     5. Replacing the default is a ratified amendment of 8.d's designation paragraph, with
        its evidence and date, followed by the catalogue and the three constants. The
        displaced model stays supported until nothing depends on it.
   - `## Consequences`: a default install needs about 14 GB of disk and 13 GB of memory for
     the model; `vibey install` asks before pulling it (ADR-0048); a machine that cannot hold
     it gets its tier's default rather than a failure.
   - `## Alternatives rejected`: keeping Qwen2.5-Coder-14B (measured slower at a quarter of
     the context); choosing by leaderboard rather than by measurement on the target laptop
     (8.d: recorded, not asserted); a paid model as the default (8.a).
3. `docs/architecture/decisions/<ND>-arch-linux-and-macos-are-the-default-operating-systems.md`:
   - Line 1: `# <ND> — Arch Linux and macOS are the default operating systems, and every change is proven on both`
   - Line 3: `**Status:** accepted — sub-doctrine 8.h, which it argues, is ratified · **Date:** <date +%F> · **Cites:** sub-doctrines 8.h, 8.a, 8.b · **Related:** ADR-0019, ADR-0022, ADR-0023, ADR-0048 · **Evidence:** the tree at the commit this record lands on`
   - `**Owes:**`: the conduct rule is 8.h.
   - `## Context`: before 8.h, CI ran every gate on `ubuntu-latest` only
     (`.github/workflows/ci.yml`), the README said "macOS / Linux", and `vibey install
     --postgres` used Homebrew, apt or dnf.
   - `## Decision`, five numbered points:
     1. Arch Linux is the default sovereign OS and macOS the default paid OS; the sovereign one
        comes first (8.a), and both have the same standing.
     2. Every change is proven on both: the seven-gate sweep runs as `gates (Arch Linux)`
        (`gap-ci-arch-gates`) and `gates (macOS)` (`gap-ci-macos-gates`) on every change, the
        tenants' suites run there too (`gap-ci-tenants-arch-macos-*`), and both are required
        checks (`gap-ci-os-required-checks`).
     3. `vibey install` installs the whole local stack on both (ADR-0048): pacman and the AUR
        on Arch, Homebrew on macOS; `vibey install --check` and `vibey doctor` are smoke-tested
        on both (`gap-ci-installer-smoke`).
     4. The operator's rulings of 2026-09-22 fix three platform choices: Arch gets the FOSS
        Docker engine from pacman with docker-buildx and macOS the Docker Desktop cask;
        sovereignloop's VS Code is Code - OSS (Arch `code`, macOS `vscodium`); the cache is
        Valkey on both.
     5. Other operating systems are supported where they can be, never at the expense of these
        two. Whether container images are exempt from 8.h is an open operator ruling
        (`gap-image-arch` waits on it); this record does not decide it.
   - `## Consequences`: every change waits on the gate sweep on each OS CI runs it on (read
     the job names from `.github/workflows/ci.yml`; state no timing); a change that works on
     one default OS but not the other is not done.
   - `## Alternatives rejected`: Ubuntu as the sovereign default (8.h names Arch); proving
     only on Linux and trusting macOS (8.h: both, same standing); Windows (not supported).
4. `properdocs.yml`: after the last decision-record entry add
   `- "<NC> — The default local model is chosen by measurement": architecture/decisions/<NC>-the-default-model-is-chosen-by-measurement.md`
   and `- "<ND> — Arch Linux and macOS are the default operating systems": architecture/decisions/<ND>-arch-linux-and-macos-are-the-default-operating-systems.md`,
   in the same form and indentation as the entry above them.
5. The advertised count in `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/index.md` and
   `GEMINI.md` (with its `0001–<last>` range) becomes the number of files on disk.

## Where to change
- New: the two ADR files. Edit with edit_file: `properdocs.yml` and the five count lines.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes (counts, nav, contiguity,
      status against the canon).
- [ ] Each new record has `## Context`, `## Decision`, `## Consequences`,
      `## Alternatives rejected` and an `**Owes:**` paragraph.
- [ ] The 8.h record states the image question as open (`grep -c "open operator ruling"` ≥ 1).
- [ ] Every number in the 8.d record (86, 215, 131,072, 32,768, 13.1 GB, 13.8 GB, 24 GB) is one
      of the facts above; no other measurement is introduced.

## Tests to write first (TDD)
None new: `tests/meta/test_adr_counts.py` and `tests/meta/test_adr_status_follows_canon.py` hold it.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    uv run --with 'properdocs==1.6.7' --with 'properdocs-theme-mkdocs==1.6.7' properdocs build --strict --site-dir "$TMPDIR/vibey-site"

## Out of scope
- The 7.a and reader-rule records (`gap-docs-adr-records-3`).
- Code, the canon, CI, and every other docs file.

Commit as `docs(adr): decision records for 8.d (the default model) and 8.h (Arch Linux and macOS)`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
