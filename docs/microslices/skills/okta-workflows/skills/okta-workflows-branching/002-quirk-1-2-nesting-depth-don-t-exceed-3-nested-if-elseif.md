---
id: skill-quirk-1-2-nesting-depth-don-t-exceed-3-nested-if-elseif-399c76476f
purpose: quirk 1 2 nesting depth don t exceed 3 nested if elseif
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-branching/SKILL.md
requires: ["skill-quirk-1-1-no-implicit-type-coercion-in-comparisons-silent-wrong-branch-26b3d9f317"]
links: ["skill-quirk-1-3-passing-a-value-directly-into-an-if-elseif-condition-throws-an-error-tip-bug-5d455f9bc1"]
---

## Quirk 1.2 — Nesting depth: don't exceed 3 nested If/ElseIf

Per AJ Ahrens, Workflows Team Lead at Okta (quoted verbatim in Max Katz "Workflows Tips #13,"
maxkatz.net, 2022/03/25): "Don't nest more than 3 If/Elseif statements. It is difficult to understand
how it works and debugging is even more challenging." This corroborates the user's finding that deep
nesting of branch/if-else cards is fragile.

- *Workaround:* Flatten to a single If/ElseIf with multiple conditions (evaluated top-down; only the
  *first* true branch runs), or precompute a boolean with True/False And/Or/Not/XNOR cards and feed
  it into one If/Else.
- *Source:* maxkatz.net Workflows Tips #13
