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

### Step 5: Look Something Up (`vibey_search`, `vibey_fetch`)
- `vibey_search(query="...", limit=5, project_id="<uuid>")` — the hub asks its local SearXNG first and Brave only as a backup (the hub holds the key; you never need one). The answer names the `backend`, and a `notice` the first time the hub used Brave.
- `vibey_fetch(url="https://...", project_id="<uuid>")` — one public page as text. Private, loopback, link-local and metadata addresses, other schemes, compressed answers and PDF or other binary types are refused (a `422` saying `refused: ...`); that is the guard working, never something to route around.
- Pass the `project_id` you are working on, so the use is recorded on that project's ledger too (the latest project's always has it). Each principal has an hourly budget (`[web] searches_per_hour`, `fetches_per_hour`); a `429` names it. Engine sessions' searches and fetches count against the agent's hourly budget too (each session also has its own cap), so a `429` can come from BUILD runs' use in the same hour. With no project at all the hub refuses (`503`) rather than search unrecorded.
- If neither tool is listed, the operator has not granted the agent `web` (`[hub] agent_scopes`); say so rather than reaching for another way.

---
