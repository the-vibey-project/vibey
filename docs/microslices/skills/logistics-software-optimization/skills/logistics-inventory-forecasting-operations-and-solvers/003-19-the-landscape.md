---
id: skill-19-the-landscape-0cc4cb5c6a
purpose: 19 the landscape
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-inventory-forecasting-operations-and-solvers/SKILL.md
requires: ["skill-18-forecasting-b865482847"]
links: ["skill-20-warehouse-operations-0caaec109d"]
---

## §19. The Landscape

```
ERP    the system of record — orders, inventory, finance
OMS    order management, allocation, sourcing decisions
⚠️ WMS warehouse management — receiving, putaway, picking, packing, shipping
⚠️ TMS transportation management — planning, tendering, execution, freight audit
YMS    yard management — trailers, docks, gates
WES/WCS  execution/control — the real-time layer talking to conveyors,
       sorters and robots
LMD    last-mile delivery platforms, driver apps, customer tracking
```
**⚠️ The integration reality**: **these are usually different vendors with different data
models, and the join keys don't line up.** ⚠️ **EDI (X12/EDIFACT) remains pervasive in
freight** — **214 shipment status, 204 load tender, 990 response, 210 invoice** — **and
API-first carriers coexist with partners who will only do EDI over an SFTP drop.**
**⚠️ Budget for the integration layer as a first-class component**; **in most logistics
projects it is larger than the optimization component.**

---
