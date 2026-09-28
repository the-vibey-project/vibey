---
id: skill-quirk-1-4-return-continue-if-behave-differently-inside-if-elseif-and-if-error-blocks-9af16d60f0
purpose: quirk 1 4 return continue if behave differently inside if elseif and if error blocks
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-branching/SKILL.md
requires: ["skill-quirk-1-3-passing-a-value-directly-into-an-if-elseif-condition-throws-an-error-tip-bug-5d455f9bc1"]
links: ["skill-quirk-1-5-cannot-drag-outputs-from-inside-a-branch-to-cards-after-the-block-e2d6298459"]
---

## Quirk 1.4 — Return / Continue If behave differently inside If/ElseIf and If Error blocks

Inside an If/ElseIf or If Error block, these blocks behave as "anonymous helper flows." A Return (or
Continue If when false) does NOT halt the flow — it proceeds to the step immediately *after* the
If/ElseIf or If Error container. To actually halt, use Return Error, Return Error If, or a Continue If
placed *outside* the block.

- *Sources:* Okta docs branching_continueif.htm, flocontrol_return.htm, errorhandling_trycatch.htm
