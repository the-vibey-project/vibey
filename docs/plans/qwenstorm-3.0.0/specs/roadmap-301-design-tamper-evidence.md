## Title
docs(design): draft the ADR for anchoring the ledger chain's head outside the database, with its threat model

## Why
Issue #301 (rewrite: `issue-audit/updates/301.md`, workstream 5 "ledger tamper evidence", "Proposed
child issues" 7, marked "Design needed first — An external anchor for the chain head (for example
signed tags or a transparency log), and its threat model"). The ledger already carries tamper
**evidence** derived from its rows: `src/vibey/domain/ledger_chain.py:1-37` defines each event's link
as the SHA-256 of the previous link and every stored field, starting from a per-project genesis, and
states that "an anchored newest link anchors the whole history behind it". But nothing anchors the
newest link anywhere a database administrator cannot rewrite: an attacker with write access to the
`event` table (the append-only RULE of `migrations/0002_event.sql` is a guard against mistakes, not
against a superuser) can recompute every link. Sub-doctrines 7.a (the searchable ledger,
`src/vibey_tools/gh/docs/doctrines.md:72-78`), 7.c (`:82-91`), 10.a (censorship resistance,
`:385-388`) and 10.f (`:419`) bind the answer; 8.b (`doctrines.md:120-194`) means the anchor's
default must be sovereign (a hosted transparency log is a counterparty, 10.a). The storage tiers
(#114; `STORM/specs/roadmap-114-*`) fold over the same links (`ledger_chain.py:19-26`).

This is a design spike: the deliverable is one draft ADR. No code changes.
**Implementer: a large model or the operator (design, not code); like `gap-spike-*`, the storm
runner skips `roadmap-*-design-*`.**

## Required behaviour
1. Write exactly one file:
   `/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-301-tamper-evidence.md`.
   Change no file in the lane's clone; commit nothing.
2. **Threat model** as a table: actor (outside attacker; compromised worker; database superuser;
   forge administrator; the operator themselves), capability, what the current derived chain
   detects, what it cannot, and what each anchoring option adds.
3. **Options**, each with what verifies it, who can forge it, its cost, and its 8.a/8.b/10.a
   standing: (a) a signed git tag or signed commit carrying the head link on the sovereign forge
   (Forgejo default); (b) a self-hosted transparency log; (c) a hosted transparency log
   (declared-only, a counterparty); (d) the public ledger shard (7.a) carrying the head link and its
   signature; (e) publishing the head through the release artifacts. Signing keys live in the secrets
   surface (OpenBao, 8.b `doctrines.md:147-150`), never in a workflow file.
4. **Cadence and scope**: per project or per deployment; on every append, per phase transition, or
   per release; how a verifier walks from an anchor (`LedgerChain.verify(..., anchors=…)`,
   `ledger_chain.py:117`) and what "anchor missing" reports (10.f: unknown, not "intact").
5. **Interaction with #114's tiers**: a chunk is identified by `link(a-1)` and `link(b)`
   (`ledger_chain.py:19-26`); state how anchors and chunk manifests compose.
6. Facts about external tools (Sigstore/Rekor, Trillian, OpenTimestamps, git signing formats) that the
   tree cannot prove are **Verification owed** items, never asserted.

## Where to change
- Create only the ADR draft above (Markdown, outside the clone).
- Read: `src/vibey/domain/ledger_chain.py`, `src/vibey/domain/ledger.py:209-225` (`digest_event`,
  `digest_range`), `migrations/0002_event.sql`, `migrations/0013_ledger_partitioning.sql`,
  `src/vibey/infrastructure/ledger/static_export.py`, `src/vibey/domain/publication_policy.py:1-40`.

## Acceptance criteria (the ADR's required sections)
- [ ] First line `# Anchoring the ledger chain's head` (no ADR number).
- [ ] `**Status:** proposed`, `**Date:**`, `**Cites:**` naming ADR-0003, ADR-0004, 7.a, 7.c, 8.b,
      10.a, 10.f with `doctrines.md` line anchors.
- [ ] `## Context` with at least 10 verified `path:line` anchors, including `ledger_chain.py:19`.
- [ ] `## Threat model` (item 2).
- [ ] `## Options considered` (item 3), `## Decision` (items 3–5), `## Consequences`.
- [ ] `## Interaction with storage tiers` (item 5).
- [ ] `## Lanes this unblocks` (20B-sized lanes: slug-to-be, title, scope, files).
- [ ] `## Open decisions for the operator` (at minimum: whether a hosted transparency log may be
      declared at all, and who holds the signing key).
- [ ] `## Verification owed` (item 6).

## Tests to write first (TDD)
None (a design spike). The check script below is the test.

## Checks the lane must run (all must pass)
    python3 - <<'PY'
    import re
    from pathlib import Path
    p = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-roadmap-301-tamper-evidence.md")
    assert p.is_file(), "the ADR draft was not written"
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# Anchoring the ledger chain's head"), "wrong title line"
    required = ["**Status:** proposed", "**Date:**", "**Cites:**", "## Context", "## Threat model",
                "## Options considered", "## Decision", "## Consequences",
                "## Interaction with storage tiers", "## Lanes this unblocks",
                "## Open decisions for the operator", "## Verification owed", "ledger_chain.py:19"]
    missing = [h for h in required if h not in text]
    assert not missing, f"missing: {missing}"
    anchors = re.findall(r"[\w./-]+\.(?:py|sql|md|toml):\d+", text)
    assert len(anchors) >= 10, f"only {len(anchors)} path:line anchors"
    for word in ("TBD", "lorem"):
        assert word not in text, f"placeholder {word!r} left in the draft"
    print("ADR draft complete")
    PY
    git status --porcelain   # must print nothing: the clone is unchanged

## Out of scope
- Any code, key material or workflow; the paper text (docs wave). Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
