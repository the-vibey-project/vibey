---
id: skill-applying-the-playbook-per-engagement-checklist-e74ecb3263
purpose: applying the playbook per engagement checklist
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-the-delivery-first-operating-model-seven-principles-1eca58a55c"]
links: []
---

## Applying the Playbook: Per-Engagement Checklist

### Week 0 (Setup)
- [ ] Establish 2-week fixed cycles and scope-as-release-valve agreement with client
- [ ] Apply WSJF to full proposed feature list; cut to 20% of original scope
- [ ] Write hypotheses for all Must-Have features
- [ ] Set up CI/CD pipeline with commit-to-production target of < 1 hour
- [ ] Configure trunk-based development; no long-lived branches
- [ ] Establish WIP limits at ~2/3 team size
- [ ] Define decision SLA with client (4-hour response commitment)

### Each Cycle Boundary
- [ ] Demo deployed increment to client (not a slide deck — working software)
- [ ] WSJF re-ranking of remaining backlog based on what was learned
- [ ] Scope review: cut Could-Haves, reassess Should-Haves
- [ ] Measure cycle time (commit to production); identify and remove top bottleneck
- [ ] Check WIP levels; reduce if above limit

### Signs Velocity Is Being Constrained (in order of frequency)
1. Decision latency > 4 hours → escalate decision SLA issue immediately
2. WIP above limit → enforce limit; do not start new work until existing work ships
3. Batch size > 3 days → break stories further before pulling into WIP
4. Long-lived branches → force merge to trunk; resolve conflicts now
5. Manual approval gates → automate or eliminate
6. Team > 7 people → split or reduce; do not add members to a late project
