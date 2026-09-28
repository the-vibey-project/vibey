---
id: skill-19-quick-reference-72f285262f
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-reference/SKILL.md
requires: ["skill-18-books-7f8d2270b9"]
links: ["skill-20-method-4f6f58d9ef"]
---

## §19. Quick Reference

### 19.1 Picker
| Need | Approach |
|---|---|
| Estimate lift | `L = ½ρV²S·C_L` (§1 → `aero-aerodynamics-airfoils-and-compressible-flow`) |
| Reduce induced drag | ⚠️ **Higher aspect ratio; elliptical loading** (§2 → `aero-aerodynamics-airfoils-and-compressible-flow`, §3 → `aero-aerodynamics-airfoils-and-compressible-flow`) |
| Fly efficiently in transonic cruise | ⚠️ **Sweep, supercritical airfoil, area ruling** (§4 → `aero-aerodynamics-airfoils-and-compressible-flow`) |
| Maximize range | ⚠️ **Breguet — L/D, SFC, weight fraction** (§5 → `aero-performance-stability-and-propulsion`) |
| Maximum glide distance | Best `L/D` speed — ⚠️ **not slowest** (§3 → `aero-aerodynamics-airfoils-and-compressible-flow`, §5 → `aero-performance-stability-and-propulsion`) |
| Improve manoeuvrability | ⚠️ **Relaxed static stability + FBW** (§6 → `aero-performance-stability-and-propulsion`, §10 → `aero-structures-aeroelasticity-and-avionics`) |
| Efficient subsonic thrust | ⚠️ **High bypass — accelerate more air, less** (§7 → `aero-performance-stability-and-propulsion`) |
| Reduce structural weight safely | ⚠️ **Damage tolerance, not just higher allowables** (§8 → `aero-structures-aeroelasticity-and-avionics`) |
| Prevent flutter | ⚠️ **Mass balance, stiffness, incremental envelope expansion** (§9 → `aero-structures-aeroelasticity-and-avionics`) |
| Tune a multirotor | ⚠️ **Rate loop first, then attitude, then position** (§11.1 → `aero-drones-launch-vehicles-flight-test-and-design`) |
| Long drone endurance | ⚠️ **Fixed-wing or VTOL hybrid — not a better battery** (§11.1 → `aero-drones-launch-vehicles-flight-test-and-design`) |
| Fly a drone BVLOS today | ⚠️ **Part 107 waiver — Part 108 not final** (§16.1) |
| Size a new aircraft | ⚠️ **Sizing loop + constraint diagram** (§14 → `aero-drones-launch-vehicles-flight-test-and-design`) |

### 19.2 Design review checklist
- [ ] Has the sizing loop actually converged, with weight margin? (§14 → `aero-drones-launch-vehicles-flight-test-and-design`)
- [ ] Does the design point satisfy every constraint line? (§14 → `aero-drones-launch-vehicles-flight-test-and-design`)
- [ ] CG range within limits at all loadings, all fuel states? (§6 → `aero-performance-stability-and-propulsion`)
- [ ] Static margin acceptable — or is FBW assumed and specified? (§6 → `aero-performance-stability-and-propulsion`, §10 → `aero-structures-aeroelasticity-and-avionics`)
- [ ] Flutter cleared across the envelope, control surfaces mass balanced? (§9 → `aero-structures-aeroelasticity-and-avionics`)
- [ ] Fatigue spectrum defined and inspection intervals set? (§8 → `aero-structures-aeroelasticity-and-avionics`)
- [ ] Ultimate = 1.5 × limit demonstrated by test, not analysis alone? (§8 → `aero-structures-aeroelasticity-and-avionics`, §13 → `aero-drones-launch-vehicles-flight-test-and-design`)
- [ ] Stall characteristics benign — does the root stall first? (§2 → `aero-aerodynamics-airfoils-and-compressible-flow`)
- [ ] Single sensor failures handled without hazardous control response? (§10 → `aero-structures-aeroelasticity-and-avionics`)
- [ ] Certification basis agreed and means of compliance accepted? (§13 → `aero-drones-launch-vehicles-flight-test-and-design`)
- [ ] For UAS: airspace class, Remote ID, DAA, and current rule status? (§11.3 → `aero-drones-launch-vehicles-flight-test-and-design`, §16.1)

---
