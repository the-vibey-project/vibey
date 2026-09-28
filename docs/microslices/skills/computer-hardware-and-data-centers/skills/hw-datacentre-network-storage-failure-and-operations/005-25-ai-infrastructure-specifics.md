---
id: skill-25-ai-infrastructure-specifics-0427de2955
purpose: 25 ai infrastructure specifics
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-datacentre-network-storage-failure-and-operations/SKILL.md
requires: ["skill-24-operations-f04e2206d7"]
links: []
---

## §25. AI Infrastructure Specifics

**⚠️ AI training clusters break several assumptions that ordinary data centre design
relies on:**
⚠️ **the load is SYNCHRONIZED and near-constant rather than diverse and averaging out —
thousands of GPUs stepping together produce power swings that stress the electrical
system; ⚠️ power density per rack is an order of magnitude above conventional (§26.2 → `hw-reference`);
⚠️ the network is part of the compute path (§21); ⚠️ a single failed node can stall an
entire training job, so checkpointing and fast recovery are architectural requirements;
and ⚠️ utilization is expected to be extremely high, so there is no diversity factor to
exploit.**
**⚠️ Inference has a different profile** — ⚠️ **more variable, more latency-sensitive, more
amenable to scaling and to cheaper hardware.**
**⚠️ The stranded-asset risk is real**: ⚠️ **a facility built for one generation's density
may not physically support the next, and the accelerator refresh cadence is now faster
than the building's depreciation schedule.**
