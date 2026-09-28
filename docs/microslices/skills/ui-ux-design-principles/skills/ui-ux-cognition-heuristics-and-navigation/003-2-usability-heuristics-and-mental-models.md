---
id: skill-2-usability-heuristics-and-mental-models-7c3aeb1de0
purpose: 2 usability heuristics and mental models
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-cognition-heuristics-and-navigation/SKILL.md
requires: ["skill-1-the-science-underneath-why-interfaces-work-or-don-t-bfea79d860"]
links: ["skill-3-information-architecture-and-navigation-5ceb0725db"]
---

## §2. Usability Heuristics and Mental Models

### 2.1 Nielsen's 10 heuristics — with the failure mode of each

Still the most useful evaluation checklist ever written (Nielsen & Molich 1990, refined
1994). Below, each heuristic plus how it's commonly violated *by teams who think they're
following it*:

| Heuristic | What it means | How it fails in practice |
|---|---|---|
| 1. **Visibility of system status** | Always tell the user what's happening | A spinner with no ETA, no cancel, and no indication of what's loading. "Saving…" that never resolves. Optimistic UI that silently fails. |
| 2. **Match between system and the real world** | Speak the user's language | Internal jargon leaking into UI ("Entity", "Object", "Instance", "Sync conflict"). Icons that mean something only to the team. |
| 3. **User control and freedom** | Emergency exits, undo | Modals with no Escape. Wizards with no Back. Destructive actions with confirm-only and no undo (§2.3). |
| 4. **Consistency and standards** | Internal + platform consistency | Three different date pickers. A "Save" that means Apply on one screen and Commit on another. |
| 5. **Error prevention** | Prevent > handle | Free-text where a picker belongs. No inline validation. Allowing a state the system will reject later. |
| 6. **Recognition rather than recall** | Show, don't make them remember | Hiding the filter you applied. Requiring a code from a previous screen. Icon-only toolbars with no labels. |
| 7. **Flexibility and efficiency of use** | Accelerators for experts | No keyboard shortcuts. No bulk actions. No saved views. Optimizing solely for first-run. |
| 8. **Aesthetic and minimalist design** | No irrelevant information | **Most misread heuristic.** It says *irrelevant* — not *sparse*. Hiding necessary controls to look clean is a violation, not compliance. |
| 9. **Help users recognize, diagnose, recover from errors** | Plain language, cause, remedy | "Error 0x8007." "Something went wrong." Errors that don't say which field. |
| 10. **Help and documentation** | Findable, task-oriented | A 60-page PDF. A help center that doesn't cover the thing that's confusing. |

### 2.2 Norman's model — the vocabulary for diagnosing *why*

- **Affordance** — what an object *permits* (a real relationship between object and user).
- **Signifier** — the *perceivable cue* that communicates the affordance. In UI, you almost
  always mean signifier. A flat rectangle affords clicking; it needs a signifier to say so.
- **Mapping** — relationship between control and effect. Natural mapping = spatial
  correspondence (the volume slider goes up for louder).
- **Feedback** — immediate, informative confirmation that the system received the action.
- **Constraints** — physical, semantic, cultural, logical limits on what can be done.
- **Conceptual model** — the user's story about how the thing works.

**The Gulf of Execution** (how do I do it?) and the **Gulf of Evaluation** (did it work?).
Every usability problem lives in one of these two gaps. When someone says "the UX is bad,"
ask which gulf — the answers are completely different interventions.

> **⚠️ GOTCHA — the flat-design signifier deficit.** The flat/minimal aesthetic that has
> dominated since ~2013 systematically removed signifiers (shadows, bevels, borders,
> underlines). Research repeatedly finds users hesitate over, or fail to find, weak-signifier
> controls — and it disproportionately affects older and less experienced users. **Ghost
> buttons, borderless inputs, and unlined links are aesthetic choices with a measurable
> usability cost.** Make it deliberate, and compensate (hover states, cursor changes,
> generous targets, at minimum a border on inputs).

### 2.3 Confirmation vs. undo

**[DURABLE] Undo beats confirmation almost always.** Confirmation dialogs:
- are dismissed reflexively after the third exposure (habituation),
- interrupt flow for the 99% of cases that were intentional,
- and provide no help in the 1% where the user was wrong but *confident*.

Prefer: perform the action → show a **toast with Undo** → make it durable for a reasonable
window. Reserve confirmation for actions that are genuinely irreversible *and* consequential
(deleting an account, sending money, publishing). When you must confirm:
- Name the specific object ("Delete *Q3 Budget.xlsx*?"), never "Are you sure?"
- Label buttons with **verbs**, not Yes/No ("Delete" / "Cancel").
- State the consequence, including irreversibility.
- Make the destructive option *not* the default and *not* adjacent to the safe one.

### 2.4 Progressive disclosure and defaults

**[DURABLE] Defaults are the most powerful design decision you make.** Most users never
change them; the default *is* the product for the majority. Choose them for the user's
benefit, and be aware that choosing them for yours is what regulators now call a dark
pattern (§13 → `ui-ux-writing-forms-research-and-ethics`).

**Progressive disclosure** — show the common case; make the advanced case reachable, not
absent. The discipline is: (a) the entry point to the hidden layer must be visible,
(b) hiding must be based on *frequency of use*, not on *how tidy it looks*, and (c) never
hide something the user needs in order to understand what's on screen.

---
