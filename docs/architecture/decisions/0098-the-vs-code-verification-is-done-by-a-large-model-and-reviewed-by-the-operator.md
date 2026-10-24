# 0098 — The VS Code verification is done by a large model and reviewed by the operator

**Status:** proposed · **Date:** 2026-10-24 · **Cites:** sub-doctrines 8.a, 8.b, 10.f · **Related:** ADR-0059 · **Ruling:** #668, item 12

## Context

The storm's two-loops draft (`docs/plans/qwenstorm-3.0.0/specs/ADR-two-loops.md`, *Verification owed*)
gates its Code - OSS driver, lane L20, on six recorded checks. At the draft's cutoff there was no
evidence of a headless, account-free way to drive an agent session in Code - OSS or VSCodium:

- **V-VS1.** A headless or virtual-display invocation of Code - OSS (`codium`) that runs an agent session to
  completion in a given folder with no GUI interaction. Record the exact command.
- **V-VS2.** The agent extension used, with its licence (OSI-approved) and its source (Open VSX), and
  confirmation that it needs no account.
- **V-VS3.** Settings that register an OpenAI-compatible local provider at a given base URL and model, with
  the resulting network traffic limited to that host. Record a packet or proxy capture.
- **V-VS4.** The event stream obtainable from the session (turns, tool calls, text, errors), for the
  `events.jsonl` mapping.
- **V-VS5.** How to tell the open-source build from Microsoft's (`product.json` fields), for `doctor`.
- **V-CC1.** Claude Code's licence and its default network behaviour with a local profile.

Work that depends on the result stays gated, including #762 (refusing `opencode` by name), whose own
first step says to change nothing until the check passes on both Arch Linux and macOS.

## Decision

**A large model carries out the verification, and the operator reviews it.** The evidence is recorded in
this repository, under `docs/architecture/evidence/`, so the gate can be read from the tree.

## Consequences

- **It has not started.** This record assigns the work; no check has run and none is claimed.
- **The runs need real machines.** The checks must run on Arch Linux and on macOS (8.h), and V-VS3 needs
  a packet or proxy capture. The model needs a machine of each kind, which the operator provides or
  authorises, and the operator reviews the V-VS3 capture, because "no call home" is only as good as the
  capture that shows it.
- **Evidence is bounded (10.f).** Each check records what was run, on which OS and version of the editor and
  extension, and when. A check that could not be run is recorded as not run, never as passed.
- **Until it is recorded, the gate stays shut.** L20 and what depends on it stay blocked, visibly.
- **Rule status.** An assignment of work, not a rule: it owes no sub-doctrine (ADR-0020).
