---
id: skill-31-mars-mission-design-windows-edl-communications-and-surface-power-8ca7ce05e7
purpose: 31 mars mission design windows edl communications and surface power
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mars-mission-design-and-settlement/SKILL.md
requires: []
links: ["skill-32-mars-settlement-habitats-mobility-eclss-closure-and-the-psychological-challenge-114c15aa10"]
---

## §31 Mars mission design: windows, EDL, communications, and surface power

### Launch windows and transfer

The Earth-Mars **synodic period is 25.6 months (780 days)**. Launch windows open for roughly **3–4
weeks every 26 months**, and missing one means waiting over two years. This is the hardest scheduling
constraint in planetary exploration and the reason Mars mission cadence is so low: a slipped vehicle
does not slip by a quarter, it slips by a synodic period. (Why windows exist at all, and porkchop
plots as the working tool for choosing one: §17 → `endeavour-mission-architecture-and-spacecraft-subsystems`.)

The **Hohmann transfer takes about 258 days each way**, with a required **stay at Mars of about 500
days** to wait for the next window — a **total mission duration of ~900 days**. (The source's own
three figures sum to **1,016 days**, not the ~900 it states; all three are carried here as given
rather than recomputed, and the conclusion is unaffected either way — a Hohmann crewed mission is a
commitment of roughly three years.) Faster trajectories are possible with higher Δv:
**opposition-class trajectories can reduce total mission time to ~600 days** but require
significantly more energy and often involve **Venus flybys**. The Hohmann remains the baseline for
mass-efficient crewed missions.

| Trajectory class | Transit each way | Stay at Mars | Total mission | Entry velocity | The trade |
|---|---|---|---|---|---|
| Hohmann (minimum energy) | ~258 days | ~500 days | ~900 days † | ~5.5–6.0 km/s | Mass-efficient; the baseline for crewed missions, at the cost of a very long total commitment |
| Opposition-class (fast transit) | source gives only the total | source gives only the total | ~600 days | can exceed 7.5 km/s | A shorter total mission, bought with significantly more energy, often a Venus flyby, and a harder entry |

† The three Hohmann figures are the source's own and do not sum: 258 + 258 + 500 = **1,016 days**
against the ~900 stated. Carried as given.

Entry velocity matters more than the two numbers suggest, because **heating scales as v³ and the
entry corridor narrows with higher velocity** — so the opposition-class trajectory does not just cost
propellant, it moves the entry system into a harder regime (the Sutton-Graves v³ scaling and the
corridor argument: §15 → `endeavour-orbits-ascent-structures-and-reentry`). **Entry interface is
typically at ~125 km altitude**, and the full EDL sequence from entry to touchdown is **about 7
minutes**, during which the spacecraft is fully autonomous — light-time to Earth is 3–22 minutes, so
the vehicle has landed or crashed before Earth knows it entered.

### EDL — the Martian squeeze

> **THE FUNDAMENTAL PROBLEM**
>
> The atmosphere is **~1% of Earth's**. That is thick enough to **require a heat shield**, because
> entry velocities are hypersonic — and **too thin to slow a vehicle to landing speed with parachutes
> alone**. You pay the full cost of carrying an atmosphere through entry, and collect only part of the
> benefit. Everything difficult about Martian EDL follows from being caught between those two facts.

The practical ceiling for **parachute-descended landed mass on Mars is about 1–1.5 tonnes** with
current technology. The **sky crane** method approaches it: **MSL at ~900 kg**, **Perseverance at
~1,025 kg**. (The landing-method families — airbags, legs, sky crane — and the seven-minute sequence
in general: §20 → `endeavour-mission-architecture-and-spacecraft-subsystems`.)

Going beyond that ceiling requires one of three things:

- **Much larger supersonic decelerators** — inflatable aerodynamic decelerators, SIAD.
- **Supersonic retropropulsion**, which SpaceX has demonstrated with Falcon 9 boosters **but not yet
  at Mars**.
- **A fundamentally different approach.**

**Starship proposes supersonic retropropulsion at Mars** — a direct entry from interplanetary
velocity with full propulsive landing, using the atmosphere for initial deceleration only. **This has
never been done and is the largest single technical risk in that architecture.** Carry that sentence
as written: the architecture is not disqualified by it, and it is not de-risked by confidence either.

### Communications

One-way light time to Mars ranges from **3 minutes at closest approach to 22 minutes at conjunction**,
when Mars is behind the Sun. **Round-trip light time at conjunction exceeds 40 minutes**, and during
**solar conjunction — roughly 2 weeks every 26 months — communication is effectively impossible** due
to solar radio interference.

Two operational consequences, both hard:

- **Earth cannot pilot a rover in real time.** Surface operations are autonomous or crew-directed;
  there is no third option. (Autonomy, safe mode and command loss timers as the general design
  response to light-time: §19 → `endeavour-mission-architecture-and-spacecraft-subsystems`; the
  flight-software discipline that makes autonomy survivable: §27 →
  `endeavour-satellites-flight-software-and-instruments`.)
- **A human crew on Mars cannot call Earth for help in an emergency.** A round trip of 40 minutes is
  not a conversation, and for two weeks in every 26 months there is no link at all.

**The relay architecture.** Surface missions return data via orbiters — **Mars Reconnaissance
Orbiter, Mars Odyssey, MAVEN, ESA's Mars Express and Trace Gas Orbiter** — that pass overhead at
**~400 km altitude**. The **1/d² advantage** over direct-to-Earth from the surface is enormous: the
same transmitter that struggles across an interplanetary distance is comfortable across a few hundred
kilometres. **A dedicated Mars communication relay network is a prerequisite for sustained surface
operations**, not an enhancement to them.

### Power on the surface

Solar flux at Mars averages **~590 W/m² at the top of the atmosphere (1.52 AU)**, with significant
variation from orbital eccentricity (**~20% between perihelion and aphelion**) and from dust. **Dust
accumulation on panels and global dust storms make solar power unreliable for critical systems** —
the storm behaviour, the up-to-97% irradiance loss and what it did to flown rovers is in §29 →
`endeavour-the-martian-environment-and-in-situ-resources`.

For a sustained presence, **fission surface power is the consensus baseline**:

| Load | Power | Status |
|---|---|---|
| Habitat, ISRU pilot plant and communications, continuously, regardless of season or dust | **10–40 kWe** | The consensus baseline; **Kilopower/KRUSTY has demonstrated the technology at 1 kWe**, and scaling to 10–40 kWe is the engineering path |
| Propellant plant producing tens of tonnes of methalox | **~1–2 MWe** | A small nuclear power station, delivered and set up autonomously |
| Small rovers and instruments | RTG-class | **RTGs are too low-power for ISRU but valuable** here |

The 1–2 MWe figure is the one that reshapes an architecture. It is not an instrument, not a payload
and not a generator bolted to a lander — it is a power station that has to arrive, deploy and run
itself for 16–26 months (the propellant chain it feeds, and that duration, are in §30 →
`endeavour-the-martian-environment-and-in-situ-resources`; radioisotope and fission power in general,
including Kilopower's place among spacecraft power sources, in §18 →
`endeavour-mission-architecture-and-spacecraft-subsystems`).
