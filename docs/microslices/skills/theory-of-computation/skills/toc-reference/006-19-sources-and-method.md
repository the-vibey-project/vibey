---
id: skill-19-sources-and-method-ed1b6e5dd9
purpose: 19 sources and method
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-reference/SKILL.md
requires: ["skill-18-quick-reference-793df50c98"]
links: []
---

## §19. Sources and Method

**Method.** Narrative review, written as **working knowledge for practitioners** rather
than as a course. **This is the most durable domain in this collection**, and the document
reflects that: §1–§6 → `toc-automata-regex-and-parsing`, `toc-computability-and-complexity`, §8 → `toc-beyond-np-space-and-distributed-limits`, §11 → `toc-beyond-np-space-and-distributed-limits`, §12 → `toc-type-systems-and-randomization` and §14 rest on theorems established between the 1930s
and the 1980s, together with practice that has been stable for decades. Rather than
manufacture a currency layer, §16 reports honestly that the field does not move much and
identifies the few things that genuinely did. Three targeted searches were run in
**August 2026** on the areas where movement was plausible; the durable material was not
"verified" against web sources because it does not need to be — Sipser, Arora–Barak,
Garey–Johnson, and the primary literature are the authority, and they are stable.

**Search log** (August 2026): Ryan Williams' time–space simulation result and its reception ·
SAT/SMT solver state, competition standing, and industrial verification practice ·
fine-grained complexity, SETH-based conditional lower bounds, and the quantum analogues.

**Primary and near-primary sources consulted (selected):**
- **R. Ryan Williams, "Simulating Time With Square-Root Space"** — ECCC Report TR25-017
  (February 2025) and the STOC 2025 paper, read directly; plus **Lance Fortnow's**
  *Computational Complexity* blog and **Scott Aaronson's** *Shtetl-Optimized* for expert
  reception, and **Quanta** and **Scientific American** for the accessible framing
- **Fine-grained complexity**: Bringmann's survey on conditional lower bounds for
  computational geometry; Abboud–Bringmann–Hermelin–Shabtay on SETH-based Subset Sum
  bounds; **Buhrman–Patro–Speelman** on the QSETH framework and the 2025–26 follow-ups,
  including the no-go results on approximate CVP
- **Solver landscape**: the **cvc5** TACAS 2022 system description; the 2026 **ESBMC**
  survey for the portfolio-dispatch practice and solver strengths; **Mariposa** (CMU) on
  measuring SMT instability in automated program verification; **SMTStabilizer** on
  context-driven normalization

**Confidence statement.** **Very high confidence** in §1–§6 → `toc-automata-regex-and-parsing`, `toc-computability-and-complexity`, §8 → `toc-beyond-np-space-and-distributed-limits`, §10 → `toc-beyond-np-space-and-distributed-limits`'s classical results,
§11 → `toc-beyond-np-space-and-distributed-limits`, §12 → `toc-type-systems-and-randomization` and §13 → `toc-type-systems-and-randomization` — these are proven theorems and long-settled practice, and my confidence
here rests on the standard textbook literature rather than on any web source. **High
confidence** in §10 → `toc-beyond-np-space-and-distributed-limits`'s Williams result, which I read in the primary paper (ECCC TR25-017)
and which is corroborated by expert commentary from within the field. **Moderate
confidence** in §16's solver-landscape details and the instability figures: those come from
individual research papers and tool surveys, the specific percentages are
benchmark-and-workload dependent, and solver versions move. **The fine-grained results in
§9 → `toc-beyond-np-space-and-distributed-limits` are conditional by construction** — they hold *if* SETH holds, and I have flagged that
rather than stating them as unconditional. Where I have characterized community consensus
(P ≠ NP, P = BPP), that is **expert opinion, not proof**, and §15 labels it as such. The
practical guidance in §6 → `toc-computability-and-complexity` and §7 → `toc-computability-and-complexity` reflects widely-reported engineering experience rather than
formal results, and should be read that way.
