---
id: skill-12-research-and-evaluation-59954690dd
purpose: 12 research and evaluation
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-writing-forms-research-and-ethics/SKILL.md
requires: ["skill-11-forms-onboarding-and-conversion-7db671e793"]
links: ["skill-13-ethics-persuasion-and-dark-patterns-7be0195082"]
---

## §12. Research and Evaluation

### 12.1 Choosing a method

| Question | Method |
|---|---|
| Can people *do* the task? | **Usability test** (moderated or unmoderated) |
| Why do they behave that way? | Interviews, contextual inquiry, diary study |
| What do they do at scale? | Analytics, funnels, session replay |
| Which version performs better? | A/B test |
| How do they think about the domain? | Card sort, tree test, mental-model interview |
| Can they *find* it? | **Tree test** (IA without UI) / first-click test |
| Is it accessible? | Expert audit + AT testing + testing with disabled users (§9.5 → `ui-ux-design-systems-platforms-and-accessibility`) |
| How do they feel over time? | Longitudinal survey (SUS/UMUX-Lite/NPS), diary |
| Does it violate known principles? | **Heuristic evaluation** (§2.1 → `ui-ux-cognition-heuristics-and-navigation`) — cheap, fast, and finds different issues than testing |

**[DURABLE] Attitudinal ≠ behavioural.** What people *say* they'd do is a poor predictor of
what they *do*. Never ship a feature on survey preference alone.

### 12.2 Sample sizes — the number everyone quotes and misuses

**Nielsen & Landauer's "5 users find ~85% of usability problems"** is the most cited and
most abused finding in UX. What it actually says: with a problem-detection probability of
~31% per user per problem, five users find about 85% of problems **in a single homogeneous
user group performing similar tasks**. What it does *not* say:
- It doesn't apply across **distinct user segments** — each segment needs its own ~5.
- It doesn't apply to **quantitative** measures (task time, success rate, satisfaction).
  Those need 20+ per condition for anything resembling a confidence interval.
- It doesn't mean five is *enough*; it means five is the point of diminishing returns for
  *one round*, and **three rounds of five beats one round of fifteen** because you fix
  things between rounds.
- The 31% detection rate itself varies with task and interface complexity.

**Rough guide:** qualitative usability 5–8 per segment per round; card sort 15–30;
tree test 30–50; quantitative benchmark 20+ per condition; A/B test — whatever your power
analysis says, calculated *before* you start.

### 12.3 Running a usability test that produces truth

- **Give tasks, not instructions.** "Find out how much it would cost to ship two of these
  to Berlin" — not "click the shipping calculator."
- **Don't lead.** When they ask "should I click here?", answer "what would you do if I
  weren't here?"
- **Silence is data.** Let them struggle for a bit; the struggle is the finding.
- **Watch behaviour, weight it above commentary.** Users are unreliable narrators of their
  own difficulty and are systematically polite about your work.
- **Recruit for the actual user**, not for whoever's convenient. Testing an enterprise tool
  on your friends produces confident nonsense.
- **Separate observation from interpretation** in your notes. "Clicked Back three times" is
  an observation; "was confused by the nav" is a hypothesis.
- **⚠️ Beware of testing only success paths.** Most real-world pain is in errors, edge cases,
  recovery, and the second session — not the happy path you designed the prototype for.

### 12.4 Metrics

**HEART** (Google) — pick per-project, and pair each with a **Goal → Signal → Metric**:
Happiness, Engagement, Adoption, Retention, Task success.

Complementary standards:
- **SUS** (System Usability Scale) — 10 items, 0–100; ~68 is average, 80+ is good.
  Comparable across products and time, which is its real value.
- **SEQ** (Single Ease Question) — one 7-point question after each task. Startlingly
  informative for its cost.
- **Task success rate, time on task, error rate** — the core behavioural triad.
- **Core Web Vitals** (§6.6 → `ui-ux-interaction-layout-and-visual-design`) for web performance.

**⚠️ Choose metrics that can go *down* when you make things worse.** Engagement metrics are
notorious for rewarding dark patterns: time-on-site rises when users are confused, and
session count rises when notifications are manipulative. Pair every engagement metric with a
quality metric (task success, retention, complaint rate, unsubscribe rate).

---
