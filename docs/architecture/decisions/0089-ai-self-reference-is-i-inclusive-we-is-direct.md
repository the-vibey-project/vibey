# 0089 — AI self-reference is I; inclusive we is only direct address

**Status:** proposed · **Date:** 2026-10-21 · **Cites:** proposed sub-doctrine 12.m; sub-doctrines 10.f, 12.b and 12.e · **Related:** ADR-0020, ADR-0040, ADR-0047, ADR-0075

## Context

AI-authored text often slides between “I”, “the assistant”, “the reviewer”, and “we”. The
last form silently groups the model with the person operating it. That blurs authorship:
the model can make its own conclusion sound jointly agreed, or describe an action as “ours”
when only one party performed or authorized it. Third-person self-labels create the same
distance from responsibility.

The operator requires one unambiguous distinction everywhere: the model speaks about itself
as “I” and addresses the operator as “you”. Inclusive “we” remains natural when the model is
speaking directly to the operator and genuinely means both parties. The defect is plural
self-reference: using “we” for the AI alone, for its self-talk or internal reasoning, or for
a collective of agents in place of an accountable singular speaker.

## Decision

Every prompt boundary this repository controls carries one mandatory voice contract:

1. Model-authored prose refers to the model only in first-person singular: “I”, “me”, “my”,
   “mine”, and “myself”. It never substitutes “the agent”, “the assistant”, “the model”,
   “the reviewer”, “the triager”, or another third-person self-label.
2. Model-authored prose addresses the operator only in second person: “you”, “your”,
   “yours”, and “yourself”.
3. Model-authored prose may use “we”, “us”, “our”, “ours”, or “ourselves” only in direct
   speech to the operator where the pronoun explicitly includes the model and operator
   together. It never uses those plural forms for the model alone, in self-talk, in its
   hidden thinking and reasoning channel, or as a collective self-label for multiple AIs or
   agents. Plans, questions, summaries, status reports, structured-output prose, and
   templates carry the distinction. The thinking channel is model-authored text like any
   other: it is not direct speech to the operator, so the plural forms do not belong there.
4. Exact quotation remains exact only when quotation itself is the task. Retrieved source,
   diffs, issue bodies, and operator input remain data and are not rewritten; the model's
   own framing around them still obeys the contract.
5. The contract is applied at runtime seams, not left to individual task authors: direct
   Ollama calls, each autonomous runner, local review and triage, continuation prompts, and
   managed AI workflows. Tests inspect those seams and the managed workflow templates.

## Consequences

- Authorship stays explicit. “I found” is the model's claim; “you chose” is the operator's
  act; “we can inspect it together” is permitted direct address. A plural pronoun cannot
  manufacture a shared observation, action, authority, responsibility, or consent.
- Existing task prompts may contain any pronoun inside untrusted or quoted data. The rule
  governs what the model authors, not bytes it must faithfully inspect.
- A prompt can constrain but cannot mathematically guarantee arbitrary model output. The
  repository therefore places the instruction at every controllable boundary and tests its
  presence; a later output validator may reject violations where a surface needs a hard
  machine guarantee.
- The words cost a small number of context tokens on every call. The clarity is intentional
  and the instruction is short enough to remain a microslice.

## Alternatives rejected

- **Ban every use of “we”.** That rejects ordinary inclusive direct address. The rule is
  about who the pronoun denotes, not the token in isolation.
- **Apply the rule only to user-facing chat.** Reviews, triage, plans, and status artifacts
  are later shown to people and can carry the same false joint voice.
- **Rely on style guidance in one root agent file.** Direct Ollama calls, absorbed runners,
  and managed workflows do not all consume that file. The rule belongs at each prompt seam.
- **Silently rewrite completed output.** Pronoun replacement can corrupt code, quotations,
  paths, and source evidence. Instruction at generation time preserves the record.

## Rule status

This binds future conduct and survives every implementation, so ADR-0020 requires law as
well as a decision record. It is filed as proposed sub-doctrine **12.m**. Only the operator's
merge ratifies it.
