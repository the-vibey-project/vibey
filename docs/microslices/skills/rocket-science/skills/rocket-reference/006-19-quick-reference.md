---
id: skill-19-quick-reference-9fea30388f
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-reference/SKILL.md
requires: ["skill-18-textbooks-479e7680a1"]
links: ["skill-20-method-227005a0ba"]
---

## §19. Quick Reference

### 19.1 The equations that carry the load
```
Δv = Isp·g₀·ln(m₀/m_f)                        rocket equation
F = ṁ·v_e + (p_e−p_a)·A_e                     thrust
Isp·g₀ = c* · C_F                             performance factorization
v_e = √( (2γ/(γ−1))·(R_u T_c/M_w)·[1−(p_e/p_c)^((γ−1)/γ)] )
v² = μ(2/r − 1/a)                             vis-viva
ε = −μ/(2a)                                   specific energy
T = 2π√(a³/μ)                                 period
Δv_plane = 2v·sin(Δi/2)                       plane change
q_s = k·√(ρ/R_n)·v³                           Sutton–Graves stagnation heating
a_max = v_e²·sin γ/(2eH)                      Allen–Eggers peak deceleration
σ_h = pR/t                                    hoop stress
I_ρ = Isp × ρ_bulk                            density impulse
```

### 19.2 Diagnostic table
| Symptom | Physics |
|---|---|
| Low measured Isp, `c*` nominal | Nozzle: separation, contour, or expansion ratio (§2.3 → `rocket-equation-nozzles-and-combustion`) |
| Low `c*` | Injector mixing / incomplete combustion (§3 → `rocket-equation-nozzles-and-combustion`) |
| High-frequency chamber oscillation | ⚠️ Tangential acoustic mode (§13.1 → `rocket-aerodynamics-structures-guidance-and-reentry`) |
| Longitudinal vehicle oscillation | ⚠️ POGO — feedline/structure coupling (§10 → `rocket-aerodynamics-structures-guidance-and-reentry`) |
| Wall burn-through at throat | Coolant boiling crisis or channel blockage (§5 → `rocket-turbomachinery-cooling-and-propellants`) |
| Turbopump destroyed on start | ⚠️ Cavitation / insufficient NPSH (§4.1 → `rocket-turbomachinery-cooling-and-propellants`) |
| Control divergence late in burn | Slosh, or bending mode as CoM shifts (§11 → `rocket-aerodynamics-structures-guidance-and-reentry`) |
| Payload short of target orbit | Check gravity loss and staging velocity (§8 → `rocket-orbital-mechanics-and-ascent`) |
| Buckled tank at max-g | ⚠️ Empty tank, high axial load — knockdown factor (§10 → `rocket-aerodynamics-structures-guidance-and-reentry`) |
| TPS recession above prediction | Radiative heating or transition location (§12 → `rocket-aerodynamics-structures-guidance-and-reentry`, §17) |

---
