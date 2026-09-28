---
id: skill-quirk-1-3-passing-a-value-directly-into-an-if-elseif-condition-throws-an-error-tip-bug-5d455f9bc1
purpose: quirk 1 3 passing a value directly into an if elseif condition throws an error tip bug
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-branching/SKILL.md
requires: ["skill-quirk-1-2-nesting-depth-don-t-exceed-3-nested-if-elseif-399c76476f"]
links: ["skill-quirk-1-4-return-continue-if-behave-differently-inside-if-elseif-and-if-error-blocks-9af16d60f0"]
---

## Quirk 1.3 — Passing a value directly into an If/ElseIf condition throws an error (tip-bug)

Per Max Katz Tips #13, quoting Okta staff: passing a value into an If/Elseif card produces an error.
Documented workaround at the time: "use Flow Control - Assign card inside the If/Elseif card to pass
in the value." Okta labeled this a "tip-bug" that "will be fixed."

- *Status:* Possibly resolved in a later release; treat as version-dependent and test in the target
  org.
