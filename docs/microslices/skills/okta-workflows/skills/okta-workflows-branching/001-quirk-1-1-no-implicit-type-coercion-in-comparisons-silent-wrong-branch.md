---
id: skill-quirk-1-1-no-implicit-type-coercion-in-comparisons-silent-wrong-branch-26b3d9f317
purpose: quirk 1 1 no implicit type coercion in comparisons silent wrong branch
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-branching/SKILL.md
requires: []
links: ["skill-quirk-1-2-nesting-depth-don-t-exceed-3-nested-if-elseif-399c76476f"]
---

## Quirk 1.1 — No implicit type coercion in comparisons (silent wrong branch)

The True/False Compare, If/Else, If/ElseIf, Continue If, and Return Error If cards do NOT
auto-convert data types. Comparing value A `"6"` (Text) `<` value B `30` (Number) returns FALSE,
because when a number is passed as text a *text* (alphabetical) comparison is performed: `"80" > "9"`
is false even though `80 > 9` is true. This manifests constantly in Entra → Okta sync when
Graph/Okta API values arrive as strings.

- *Mechanism:* "Workflows does not perform implicit datatype conversions for comparisons" (Okta KB,
  "True/False Compare Card Output Result Might Be Incorrect," last updated Jan 9, 2026).
- *Workaround:* Explicitly set both value A and value B to the same type in the card's type
  dropdowns; when in doubt, coerce upstream with a Number or Text conversion card.
- *Source:* support.okta.com/help/s/article/true-false-compare-card-output-result-might-be-incorrect
