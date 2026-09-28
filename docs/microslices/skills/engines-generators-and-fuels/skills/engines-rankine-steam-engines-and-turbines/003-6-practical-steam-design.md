---
id: skill-6-practical-steam-design-dd2ecac840
purpose: 6 practical steam design
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-rankine-steam-engines-and-turbines/SKILL.md
requires: ["skill-5-steam-engines-in-detail-5df95aaa2e"]
links: []
---

## §6 Practical steam design

> ## ⚠ SAFETY FIRST — BOILERS KILL
>
> **Pressurized steam carries enormous energy. A small boiler at 10 bar contains enough stored energy to launch shrapnel through walls. Boiler explosions were the leading industrial killer of the 19th century. Any steam engine build requires: (1) a boiler designed to recognized code (ASME in the US, equivalent elsewhere), (2) a certified pressure relief valve, (3) a low-water cutoff, (4) proper water treatment, (5) regular inspection. For a model or small engine, work at low pressure (1–3 bar) and treat every component as if it could fail. Never cap or bypass the safety valve. Never operate a boiler unattended.**

Read this before anything below it. The full boiler-explosion and high-pressure-steam hazard treatment is §21 → `engines-safety-and-reference`.

### Small steam engine (model / educational)

| Element | Specification |
|---|---|
| **Boiler** | A vertical **fire-tube (Cornish type)** boiler is the simplest practical design — a steel or copper shell with tubes carrying hot gases from a burner through the water space. **Copper is preferred for models** (easy to silver-solder, excellent thermal conductivity). Must have a **water gauge glass, a pressure gauge, a safety valve set to lift at design pressure, and a filler plug**. **1–3 bar (15–45 psi)** is sufficient and relatively safe. |
| **Engine** | Single-cylinder **double-acting** reciprocating. Double-acting means steam acts on both sides of the piston alternately (admission one side while exhausting the other), **doubling power per cylinder** and giving more uniform torque. Cylinder brass or bronze with a honed bore; piston uses **PTFE or graphite rings** for low friction at temperature; **slide valve (D-valve)** driven by an eccentric on the crankshaft, or a **piston valve** for better efficiency; steel connecting rod and crankshaft; bronze bearings for the crank journals. |
| **Cut-off control** | A simple fixed-cut-off slide valve is adequate; a **Walschaerts-type linkage with variable cut-off** demonstrates the efficiency principle beautifully — you can watch steam consumption drop as you notch up. |
| **Condenser** (optional, educational) | Even a coil of copper tube in a bucket of water demonstrates the vacuum principle. Connect the exhaust to a sealed cooled container and the condensing steam creates a vacuum that pulls the piston on the exhaust stroke, **measurably increasing power and efficiency**. |
| **Output** | At **2–3 bar with a 20–30 mm bore, perhaps 10–50 W** — enough to spin a small generator (a small DC motor driven backwards, or a PMA) and light an LED. Demonstrates the complete chain **fuel → heat → steam → mechanical work → electricity**. |

Generator selection for that last step: §13 → `engines-generators-and-house-power`.

### Larger steam engine (1–10 kW)

**Safety becomes genuinely critical; a boiler at 10–15 bar is a bomb if it fails. Not a beginner project.**

| Element | Specification |
|---|---|
| **Boiler** | A **monotube (once-through)** boiler is safer than a fire-tube because it holds very little water at any moment — tubing contains **a few litres rather than hundreds**. Water is pumped continuously through a long coiled tube heated by a burner and emerges as steam. **If water flow stops the tube overheats rapidly, so a reliable feed pump and low-flow cutoff are essential.** Monotube boilers can produce **10–20 bar at 300–400°C**. |
| **Engine** | Single-stage or compound reciprocating, or a small single-stage impulse turbine. A well-designed reciprocating engine with **50–80 mm bore** and a condenser can achieve **15–20% thermal efficiency**. A small turbine (Tesla or single-stage impulse) is simpler mechanically but **less efficient at small scale** (tip-clearance losses and low Reynolds numbers). |
| **Generator** | A **PMA or wound-field alternator**, belt-driven or direct-coupled. A modified automotive alternator (with a proper regulator) can work for low output; a **purpose-built alternator is better**. |

### The practical efficiency chain

| Stage | Efficiency |
|---|---|
| Combustion (in a good boiler) | **80–90%** |
| Steam cycle | **15–25%** small reciprocating · **20–30%** small turbine |
| Mechanical-to-electrical | **85–95%** |
| **Overall fuel-to-electricity** | **10–20%** |

Low compared with a commercial combined-cycle plant at **60%** — but those are **500 MW machines at 250 bar and 600°C**. (The combined cycle and why it wins: §11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`.)
