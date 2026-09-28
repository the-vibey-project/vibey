---
id: skill-17-quick-reference-a25bd2d8a3
purpose: 17 quick reference
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-reference/SKILL.md
requires: ["skill-16-books-f91124d028"]
links: ["skill-18-method-ee087900f4"]
---

## §17. Quick Reference

### 17.1 Picker
| Need | Use |
|---|---|
| Bus voltages and line flows | **Power flow, Newton-Raphson** (§4.1 → `power-system-analysis-and-protection`) |
| Fast approximate flows for markets | ⚠️ **DC power flow** (§4.1 → `power-system-analysis-and-protection`) |
| Best estimate of current system state | **State estimation** (§4.2 → `power-system-analysis-and-protection`) |
| Breaker sizing, relay settings | **Fault analysis, symmetrical components** (§4.3 → `power-system-analysis-and-protection`) |
| Inverter control dynamics | ⚠️ **EMT simulation (PSCAD/EMTP), not phasor domain** (§11.3 → `power-inverters-storage-markets-and-datacenters`) |
| Distribution feeder study | **OpenDSS / GridLAB-D** (§11.3 → `power-inverters-storage-markets-and-datacenters`) |
| Open research / scripting | **pandapower, MATPOWER, PowerModels.jl** (§11.3 → `power-inverters-storage-markets-and-datacenters`) |
| Fast protection signalling | ⚠️ **IEC 61850 GOOSE (~4 ms)** (§7 → `power-scada-ems-and-protocols`) |
| Network model exchange | **CIM** (§7 → `power-scada-ems-and-protocols`) |
| Wide-area dynamics visibility | **PMUs / synchrophasors** (§4.2 → `power-system-analysis-and-protection`) |
| Inertia in a low-inertia system | ⚠️ **Synchronous condenser or GFM inverter — and see §8.2 → `power-inverters-storage-markets-and-datacenters`** |
| Fast frequency response | **BESS** (§9 → `power-inverters-storage-markets-and-datacenters`) |
| Connect a large load sooner | ⚠️ **Demonstrable demand flexibility** (§15.2) |

### 17.2 Orientation questions for grid software work
- [ ] Which timescale am I in — protection, control, dispatch, or planning? (§11.1 → `power-inverters-storage-markets-and-datacenters`)
- [ ] Per-unit or physical units, and on what base? (§1.5 → `power-ac-fundamentals-generation-and-grid`)
- [ ] Is this phasor-domain or does it need EMT? (§11.3 → `power-inverters-storage-markets-and-datacenters`)
- [ ] Does the network model match reality, and when was it last validated? (§11.3 → `power-inverters-storage-markets-and-datacenters`)
- [ ] Are timestamps traceable to a synchronized source? (§11.3 → `power-inverters-storage-markets-and-datacenters`)
- [ ] What happens to this system during an alarm flood? (§6 → `power-scada-ems-and-protocols`)
- [ ] Is this in NERC CIP scope? (§11.2 → `power-inverters-storage-markets-and-datacenters`)
- [ ] What does it do when it can't converge / can't reach a device / is late? (§4.1 → `power-system-analysis-and-protection`, §10 → `power-inverters-storage-markets-and-datacenters`)

---
