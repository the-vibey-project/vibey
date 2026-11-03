---
id: skill-gate-0-5-release-readiness-contract-4dbe9671af
purpose: gate 0 5 release readiness contract
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-gate-0-source-and-manuscript-audit-e7687b5dfd"]
links: ["skill-gate-1-deterministic-print-build-220664ec11"]
---

## Gate 0.5: release-readiness contract

Before spending time on typesetting, verify the commercial and evidentiary
inputs that were previously likely to live in a spreadsheet, a launch note, or
the operator's memory. The book configuration is the source of record. A
release contract should declare and the native publisher command should measure:

- title, subtitle, author, description, and the description's minimum useful
  length;
- the exact store-keyword count required by the target retailer, with unique,
  non-empty keywords and no accidental duplication;
- the required research apparatus files and a minimum count of reader-facing
  source URLs, so a researched book cannot pass after its evidence register was
  omitted from the build;
- the date, source URL, currency, list prices, royalty assumptions, delivery
  costs, and print-cost assumptions used for the pricing decision;
- estimated unit economics for every configured format, reported as evidence
  rather than treated as a promise of retailer payout;
- page-count and trim constraints for each retailer and format. If a book
  exceeds a platform limit, the contract must disable that format for that
  platform or name the external provider and variant that will carry it.

The gate must fail on missing metadata, an invalid keyword cardinality, missing
research apparatus, absent or stale pricing verification, impossible prices,
or a configured format whose page count cannot be accepted by its retailer. It
may warn on a deliberate alternative such as an external hardcover provider,
but that warning must be explicit in the machine-readable report. The report
must be written beside the other release evidence before the build continues.

This gate is intentionally separate from human approval. A machine can prove
that seven keywords exist, that a pricing source was checked on a stated date,
and that a 607-page interior exceeds a 550-page KDP hardcover limit. It cannot
decide whether the positioning is honest, whether the price is wise, or whether
the final cover deserves approval. Those remain recorded human judgments.
