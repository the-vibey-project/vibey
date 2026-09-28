---
id: skill-18-engine-anatomy-and-the-rebuild-process-c525d46130
purpose: 18 engine anatomy and the rebuild process
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-rebuilding-engines-materials-and-tolerances/SKILL.md
requires: []
links: ["skill-19-engine-management-and-forced-induction-17f5911b32"]
---

## §18 Engine anatomy and the rebuild process

### Why rebuild rather than build

Building a car engine from scratch — machining your own block, crank, rods and pistons — is beyond the
scope of any individual without a full machine shop and years of experience. What is practical and
enormously educational is **rebuilding an existing engine**: disassembling it, inspecting every
component, machining what needs machining, replacing what needs replacing, and reassembling with
correct tolerances — where the Otto-cycle theory of §7 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`
meets the tolerance discipline of §20 below.

### Engine anatomy — what each part does

| Part | What it is | What it does / what to know |
|---|---|---|
| **Block** | The structural foundation. Usually cast iron or aluminium | Holds the cylinders (bore), water jackets, oil galleries and main bearing supports. Cylinders may have pressed-in iron liners or be nikasil-coated aluminium. |
| **Cylinder head** | Bolts to the top of the block | Contains valves, combustion chamber, spark plugs (or injectors for diesel/GDI) and the valvetrain. |
| **Crankshaft** | Converts linear piston motion to rotation | Runs in main bearings; counterweights balance reciprocating mass. Journals must be round, straight and properly sized. |
| **Connecting rods** | Link piston to crank | Big end attaches to the crank journal via split bearings; small end to the piston via the wrist pin. Rods must be straight, the big end round, bearings within spec. |
| **Pistons and rings** | Seal and transmit combustion pressure | Compression rings seal combustion pressure; the oil control ring scrapes excess oil off the cylinder wall. |
| **Valvetrain** | Opens and closes the valves | **OHV/pushrod** (cam in block, pushrods to rockers — simpler, lower centre of gravity, many V8s); **SOHC** (one cam per bank); **DOHC** (separate intake and exhaust cams, enables four valves per cylinder). |

**Head gasket — why failure symptoms vary so much.** The head gasket seals combustion pressure,
coolant and oil **simultaneously**. That is exactly why head gasket failure produces such varied
symptoms: overheating, oil in coolant, coolant in oil, loss of compression, persistent pressurization
of the cooling system.

**Crankshaft clearances.** Bearing clearances are typically **0.02–0.05 mm** (less than a thou),
measured with plastigauge during rebuild. **Rod bearing failure** is one of the most common and
destructive engine failures — a deep knocking that intensifies with load.

**Pistons and rings — the diagnostic distinction.** This pair of symptoms narrows where to look; the
confirming test tells you which:

| Symptom set | What is worn |
|---|---|
| Oil consumption **without** compression loss (blue smoke) | Possible oil-control rings, valve-stem seals, PCV faults or turbo seals; test before disassembly |
| Oil consumption **and** loss of compression (poor starting, blow-by, reduced power) | Possible compression-ring, valve, head-gasket or cylinder wear; confirm with compression/leak-down tests |

Pistons are aluminium and expand with heat, which is why piston-to-cylinder clearance is critical and
why cold engines are noisy until warm.

**Variable timing and lift.** Variable valve timing (cam phasing) and variable lift (VTEC-type)
broaden the useful torque curve by optimizing valve events for different RPM ranges.

> ### ⚠ INTERFERENCE ENGINES
> On an interference engine the valves extend into the space the piston occupies at top dead centre.
> **If the timing belt or chain breaks or jumps, valves and pistons collide, destroying the engine.**
> On a non-interference engine they do not touch, so a timing failure strands you but the engine
> survives. **Most modern engines are interference** (for efficiency — higher compression, better
> breathing), which makes timing belt replacement intervals non-advisory. Check whether your engine is
> interference and follow the belt/chain service interval religiously.

### Rebuild process overview

1. **Disassembly and inspection.** Everything is measured: cylinder bore (taper, out-of-round, size),
   crankshaft journals (wear, size), bearing clearances (plastigauge), valve guides and seats,
   piston-to-wall clearance, deck flatness. A machine shop handles what you cannot: boring/honing
   cylinders, grinding crank journals, surfacing the head and block, valve seat cutting, guide
   replacement.
2. **Machining.** Cylinders may be bored oversize (requiring oversize pistons) or just honed if within
   spec. The crank may be ground undersize (requiring undersize bearings). Head and block surfaces are
   machined flat to ensure head gasket sealing — **warpage beyond about 0.05 mm in 100 mm is too
   much**. Valve seats are recut.
3. **Cleaning.** Every oil gallery, water jacket and bolt hole must be spotless. Debris in an oil
   gallery destroys bearings on first start. Threaded holes must be chased so torque readings are
   accurate — a dirty bolt hole gives a false torque reading.
4. **Reassembly with correct torque and tolerances.** Every bolt has a torque spec. Critical bolts
   (head, rod, main bearing) often have a torque-plus-angle procedure or are **torque-to-yield**
   (single-use bolts that stretch and must be replaced). Assembly lube on bearings, correct ring gap
   orientation, valve timing set precisely to marks.
5. **Break-in.** New rings and bearings need a break-in period. Vary the RPM, avoid sustained full
   load, change the oil early (**first 500 km / 300 miles**) to remove machining debris and assembly
   lube.

> Valve springs and clutch pressure-plate springs store significant energy, and a vehicle on a jack is
> a crush hazard — see §21 → `engines-safety-and-reference` before disassembly.
