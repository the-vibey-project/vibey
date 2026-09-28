---
id: skill-30-quick-reference-5a51faf466
purpose: 30 quick reference
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-reference/SKILL.md
requires: ["skill-29-books-98429f3645"]
links: ["skill-31-method-95ce896a33"]
---

## §30. Quick Reference

### 30.1 Picker
| Question | Where |
|---|---|
| Why does the light come on instantly? | ⚠️ **Fields propagate; electrons crawl** (§6 → `em-current-energy-flow-circuits-and-ac`, §8 → `em-current-energy-flow-circuits-and-ac`) |
| Where does the energy actually go? | ⚠️ **Poynting — through the field into the load** (§8 → `em-current-energy-flow-circuits-and-ac`) |
| Can I use circuit theory here? | ⚠️ **Is the circuit ≪ λ?** (§9 → `em-current-energy-flow-circuits-and-ac`, §18 → `em-maxwell-waves-transmission-lines-and-relativity`) |
| Why is my decoupling not working? | ⚠️ **Above the capacitor's self-resonance** (§9 → `em-current-energy-flow-circuits-and-ac`) |
| Why is there ringing on my trace? | ⚠️ **Reflection. Terminate it** (§18 → `em-maxwell-waves-transmission-lines-and-relativity`) |
| Where should the return current flow? | ⚠️ **Directly under the trace. Don't split the plane** (§24 → `em-conduction-semiconductors-grounding-and-electrical-safety`) |
| Why does my inductor saturate? | ⚠️ **B-H curve limit, not heat** (§15 → `em-magnetism-induction-and-transformers`) |
| Why does the relay kill my transistor? | ⚠️ **L dI/dt spike. Flyback diode** (§14 → `em-magnetism-induction-and-transformers`) |
| Why high-voltage transmission? | ⚠️ **I²R falls as the square of current** (§14 → `em-magnetism-induction-and-transformers`) |
| Why does power factor matter? | ⚠️ **Apparent power sizes the infrastructure** (§11 → `em-current-energy-flow-circuits-and-ac`) |
| Is magnetism a separate force? | ⚠️ **No — same field, different frame** (§19 → `em-maxwell-waves-transmission-lines-and-relativity`) |
| Does this material superconduct? | ⚠️ **Show me the Meissner effect** (§22 → `em-conduction-semiconductors-grounding-and-electrical-safety`, §26.1) |
| SiC or GaN? | ⚠️ **Voltage and frequency decide** (§26.2) |
| Why did I get a shock but they didn't? | ⚠️ **Path, skin condition, and let-go threshold** (§25 → `em-conduction-semiconductors-grounding-and-electrical-safety`) |

### 30.2 Sanity checks
- [ ] ⚠️ **Which rung of §1 → `em-electrostatics-fields-potential-and-dielectrics`'s ladder am I on, and is it valid here?**
- [ ] ⚠️ **Have I drawn the CURRENT LOOP, including the return path?** (§24 → `em-conduction-semiconductors-grounding-and-electrical-safety`)
- [ ] Units consistent; RMS vs peak resolved (§11 → `em-current-energy-flow-circuits-and-ac`)
- [ ] ⚠️ **Is the circuit small compared to the wavelength of the fastest EDGE?** (§9 → `em-current-energy-flow-circuits-and-ac`, §18 → `em-maxwell-waves-transmission-lines-and-relativity`)
- [ ] Parasitics considered — ESL, ESR, trace inductance (§9 → `em-current-energy-flow-circuits-and-ac`)
- [ ] ⚠️ **Is any flux changing through a loop I'm measuring across?** (§13 → `em-magnetism-induction-and-transformers`)
- [ ] Core saturation and thermal limits checked (§15 → `em-magnetism-induction-and-transformers`)
- [ ] ⚠️ **Capacitors discharged before touching anything** (§25 → `em-conduction-semiconductors-grounding-and-electrical-safety`)

---
