---
id: skill-quirk-1-5-cannot-drag-outputs-from-inside-a-branch-to-cards-after-the-block-e2d6298459
purpose: quirk 1 5 cannot drag outputs from inside a branch to cards after the block
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-branching/SKILL.md
requires: ["skill-quirk-1-4-return-continue-if-behave-differently-inside-if-elseif-and-if-error-blocks-9af16d60f0"]
links: ["skill-quirk-1-6-if-else-supports-only-one-condition-07915c6db7"]
---

## Quirk 1.5 — Cannot drag outputs from inside a branch to cards after the block

"You can drag outputs from cards that run before the If/ElseIf into a condition or branch inside the
If/ElseIf, but you cannot drag outputs from inside a branch to cards that are run after the If/ElseIf.
This is because an output from inside a branch will be undefined any time a different branch is run."
Workaround: use the block's optional Outputs feature (View Outputs / Create Outputs) which assigns
values after whichever branch completes.

- *Sources:* Okta docs branching_branch.htm; support.okta.com
  how-to-use-if-else-if-elseif-and-if-error-card-outputs
