---
id: skill-9-when-to-use-and-when-not-to-496245990d
purpose: 9 when to use and when not to
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-adoption-governance-and-security/SKILL.md
requires: []
links: ["skill-10-governance-and-shadow-it-7cf26db979"]
---

## §9. When to Use — and When Not To

**[DURABLE] The most important section here.**

### 9.1 Use low-code when

- **The alternative is a spreadsheet emailed around**, or a manual process.
- **The problem is well-understood, common, and stable** — approvals, intake forms,
  notification routing, inventory tracking, leave requests.
- ⚠️ **The people who own the process should own the tool.** *This is the strongest
  argument in the whole category*: an ops manager who can change their own workflow
  without a ticket is a genuine organizational win, and it's the thing AI code generation
  **does not** replicate (§4.2 → `lowcode-landscape-automation-and-ai-generation`).
- **You're prototyping** and will rebuild if it works.
- **The integration already exists as a connector** and building it yourself is
  undifferentiated work.
- **Volume is low enough that per-task pricing stays sane** (§11).

### 9.2 Write code when

- **The logic is genuinely complex** — branching, state machines, real algorithms.
- **You need version control, code review, automated testing, and CI/CD** and the platform
  can't give you them (§14 → `lowcode-lock-in-and-engineering-practice`).
- **Performance or scale matters.**
- **It's core to your product** — ⚠️ **never build your differentiator on someone else's
  ceiling.**
- **The regulatory environment demands auditability** you can prove.
- **Per-seat or per-task cost will exceed engineering cost** at your volume (§11).
- **It'll live for years** and be maintained by people who haven't been hired yet.

**[DURABLE] The question that resolves most of these**: **"what happens when the person who
built this leaves?"** If the answer is "nobody can maintain it," you've made a staffing
decision disguised as a tooling decision.

---
