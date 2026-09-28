---
id: skill-1-the-science-underneath-why-interfaces-work-or-don-t-bfea79d860
purpose: 1 the science underneath why interfaces work or don t
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-cognition-heuristics-and-navigation/SKILL.md
requires: ["skill-0-routing-efd17c5aba"]
links: ["skill-2-usability-heuristics-and-mental-models-7c3aeb1de0"]
---

## §1. The Science Underneath — why interfaces work or don't

Almost every defensible design decision reduces to one of these. Knowing them turns
"I don't like it" into "this will cost users ~600 ms per interaction and here's why."

### 1.1 Motor control

**Fitts's Law [DURABLE]** — time to acquire a target is a function of distance and size:
`MT = a + b·log₂(2D/W)`. Practical consequences, in rough order of value:
- **Bigger targets are faster and more accurate.** Non-negotiable, measurable, and the
  basis of every touch-target guideline in §4.2 → `ui-ux-interaction-layout-and-visual-design`.
- **Closer targets are faster.** Put the primary action near where the user's attention
  and pointer already are — not in a corner because the grid says so.
- **Screen edges and corners have effectively infinite width** in one dimension, because
  the pointer stops there. This is why the macOS menu bar (screen top) is faster to hit
  than a Windows in-window menu bar, and why the corners are the most valuable real estate
  on a desktop screen. On touch, edges have the *opposite* property — they're where the
  hand occludes and where system gestures live.
- **Dangerous actions should violate Fitts deliberately**: make Delete smaller, farther, or
  behind a confirm. Never place Cancel adjacent to a destructive primary.

**Steering Law [DURABLE]** — time to move *through* a constrained path grows with path
length and shrinks with tunnel width. This is why deep cascading menus are painful (you
must steer down a narrow corridor without leaving it) and why macOS's diagonal-tolerance
in submenus was a genuine innovation. If your nav requires precise steering, add
dwell tolerance or convert to click-to-open.

### 1.2 Decision and attention

**Hick–Hyman Law [DURABLE, but frequently over-applied]** — decision time grows
logarithmically with the number of *equally likely* alternatives: `RT = a + b·log₂(n+1)`.
- Correct use: don't put 40 undifferentiated options in one flat list.
- **⚠️ Misuse:** "Hick's Law says fewer menu items are always better" — false. The log is
  cheap; a well-*categorized* list of 40 is faster than a flat list of 8 that requires
  drilling. And options are rarely equally likely — a good default collapses the decision
  entirely. **Categorization beats reduction.**

**Miller's "7±2" [DURABLE finding, WIDELY misapplied]** — Miller (1956) described
short-term memory capacity for *chunks* in a recall task. It was never a rule about menu
length or navigation items, and Miller himself objected to that use. The better modern
number is **Cowan's ~4±1** chunks for working memory without rehearsal. The design
implication is real but different: **don't require users to hold state in their heads**.
Show the previous step. Persist the filter. Display the total. Recognition over recall
(§2.1) is the actual principle.

**Cognitive load [DURABLE]** — three types worth distinguishing:
- *Intrinsic*: inherent difficulty of the task. You can't remove it, only sequence it.
- *Extraneous*: load imposed by the interface itself. **This is the entire target of UI
  design.** Inconsistent labels, hidden state, unclear hierarchy, unnecessary choices.
- *Germane*: effort spent building a useful mental model. Worth preserving.

**Attention is selective and change-blind.** Users do not see your banner. Inattentional
blindness and **banner blindness** are well replicated: elements that look like ads, sit in
ad-shaped positions, or animate like ads get filtered out pre-consciously. If something
must be seen, it goes in the content flow, not the periphery.

### 1.3 Perception and grouping

**Gestalt principles [DURABLE]** — the visual system groups before you consciously read.
In rough order of strength:
1. **Proximity** — nearest elements group. *The single most powerful and most misused tool
   in UI layout.* If a label is equidistant between two fields, users will guess.
2. **Similarity** — same color/shape/size groups. This is why "everything is a button" and
   "nothing looks like a button" are both failures.
3. **Common region** — a shared border or background box groups strongly, and *overrides
   proximity*. Cards work because of this.
4. **Continuity / Common fate** — aligned or co-moving elements group. Alignment isn't
   aesthetics, it's grouping.
5. **Closure / Figure-ground** — the mind completes shapes and separates foreground.

**⚠️ GOTCHA — the proximity bug.** The most common spacing error in real products:
equal margins above and below a label, so it visually belongs to neither the field above
nor the field below. **Rule: the space *within* a group must be smaller than the space
*between* groups.** Almost every "this form feels cluttered" complaint is this.

**Von Restorff (isolation) effect [DURABLE]** — the item that differs is remembered and
found. This is the entire justification for having exactly **one** primary button per view.
Two primary buttons = zero primary buttons.

**Serial position effect [DURABLE]** — first and last items in a list are recalled best.
Put the most important nav item first, the second-most last.

### 1.4 Memory of the experience

**Peak-End Rule [DURABLE]** — people judge an experience by its most intense moment and
its ending, not its average. Design consequences:
- Invest disproportionately in the **worst moment** (the error, the wait, the failed
  payment) and the **last moment** (the confirmation, the success state, the offboarding).
- A pleasant confirmation screen genuinely changes the remembered quality of a tedious form.

**Zeigarnik effect [DURABLE-ish]** — incomplete tasks stay in memory. Progress indicators
and "3 of 5 steps" work partly because of this. It is also the mechanism behind
completion-pressure dark patterns (§13 → `ui-ux-writing-forms-research-and-ethics`) — same lever, different intent.

**Doherty Threshold (~400 ms) [DURABLE]** — below roughly 400 ms of system response,
users stay in flow and productivity rises superlinearly. Above ~1 s, attention wanders.
This is why perceived performance is a *design* concern (§6.6 → `ui-ux-interaction-layout-and-visual-design`), not just an engineering one.

**Time perception is malleable.** Progress bars that accelerate toward the end feel
faster. Skeleton screens feel faster than spinners because they signal *what* is coming.
Optimistic UI (show the result immediately, reconcile later) feels instant — but you must
then design the failure path honestly, not silently drop the change.

### 1.5 Learning and expertise

**Power law of practice [DURABLE]** — performance improves as a power function of
repetitions. Two consequences:
- **Novices and experts need different affordances of the same function.** A menu item
  (discoverable, slow) and a keyboard shortcut (fast, invisible) for the same command is
  not redundancy — it's the correct design. **Show the shortcut in the menu** so the
  transition happens.
- **Consistency is compound interest.** Every deviation resets the learning curve.

**Jakob's Law [DURABLE]** — users spend most of their time on *other* products, so they
expect yours to work like those. Novel interaction models carry an enormous, usually
underestimated cost. Innovate on the *product*, not on where the close button lives.

---
