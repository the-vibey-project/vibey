---
id: skill-3-operator-workflow-in-chat-b1e30cb405
purpose: 3 operator workflow in chat
source: src/vibey_tools/skills/plugins/vibey/skills/vibey-chat-driver/SKILL.md
requires: ["skill-2-security-boundary-the-scoped-agent-principal-046fb6537a"]
links: ["skill-4-driving-vibey-over-acp-zed-and-other-acp-clients-9cb332ba44"]
---

## 3. Operator Workflow in Chat

### Step 1: Orient (`vibey_projects` and `vibey_gates`)
At the start of a session or when the user asks "what is vibey doing?":
1. Call `vibey_projects` to list active projects, their current phase, and `open_gates` count.
2. Call `vibey_gates` to see any parked human gates waiting for a decision.
3. Call `vibey_status` with `project_id` for the active project to inspect cycle progress, queue depth, and engine circuit health (`gptossloop`, `claudeloop`, `codexloop`, `qwenloop`).

### Step 2: Start or Resume Work (`vibey_start_project`, `vibey_start_work`, `vibey_pause_work`)
- To kick off a new project from the user's description: call `vibey_start_project(name="<slug>", intake="<requirements>")`, then `vibey_start_work(project_id="<uuid>")`.
- To pause or resume a project's background worker: call `vibey_pause_work` or `vibey_start_work`.

### Step 3: Resolve Human Gates (`vibey_answer_gate`)
When a project parks on a human gate:
1. Read the gate's `kind`, `prompt`, and `options` from `vibey_gates`.
2. Present the decision clearly to the user in chat (or apply the user's stated decision).
3. Call `vibey_answer_gate(gate_id="<uuid>", answer={...})`:
   - Design interview gate: `{"answers": {...}}` or `{"defaults": true}`
   - Review verdict gate: `{"verdict": "accept"}` or `{"verdict": "changes", "feedback": "..."}`
   - Choice gate: `{"choice": "<option>"}`

### Step 4: Inspect the Queue, Ledger, and Health
- `vibey_queue(project_id="<uuid>")` — see queued and leased jobs in claim order.
- `vibey_ledger(project_id="<uuid>", text="...", kind=["..."], limit=50)` — search the append-only audit ledger.
- `vibey_budget(project_id="<uuid>")` — check cycle and project spend against caps.
- `vibey_loops`, `vibey_lanes`, `vibey_doctor` — inspect local/paid engine availability, active runner lanes, and hub readiness.

---
