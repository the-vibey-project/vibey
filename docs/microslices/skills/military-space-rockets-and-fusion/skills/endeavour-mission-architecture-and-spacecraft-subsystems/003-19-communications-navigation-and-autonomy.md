---
id: skill-19-communications-navigation-and-autonomy-bf7f34e526
purpose: 19 communications navigation and autonomy
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mission-architecture-and-spacecraft-subsystems/SKILL.md
requires: ["skill-18-spacecraft-power-and-thermal-control-c22f9581f6"]
links: ["skill-20-attitude-control-in-space-propulsion-and-entry-descent-and-landing-39aad0ce65"]
---

## §19 Communications, navigation, and autonomy

### The link budget

    P_r = P_t + G_t + G_r − L_fs − L_other

Path loss scales as d², so **data rate falls as 1/d²**. Mars at opposition versus conjunction varies
by ~7× in distance — about 17 dB. **Coding buys enormous margin:** turbo and LDPC codes operate
within ~1 dB of the Shannon limit, against the ~9 dB gap of uncoded BPSK — an order of magnitude in
effective data rate for free, and the reason deep space missions return anything at all.

> **THE NUMBERS THAT SHOW THE PROBLEM.** Voyager 1 at ~24 billion km returns ~160 bit/s on a 3.7 m
> dish with 23 W. New Horizons at Pluto returned ~1–2 kbit/s and took **16 months** to downlink the
> encounter data. Data volume, not instrument capability, is frequently the limiting factor for
> outer-planet science. And the Deep Space Network (Goldstone, Madrid, Canberra — 120° apart for
> continuous coverage) is **oversubscribed**, a real and under-appreciated constraint on mission
> planning.

**Light-time**, one-way: Moon 1.3 s (teleoperation marginal); Mars 3–22 min (teleoperation
impossible); Jupiter 33–53 min; Voyager 1 ~23 hours. Round-trip to Mars exceeds 40 minutes at
conjunction. This is the single reason surface robots must be autonomous and why EDL must be
entirely self-contained — **the spacecraft has landed or crashed before Earth knows it entered.**

**Relay architecture.** Mars surface missions overwhelmingly return data via orbiters rather than
direct-to-Earth, because an orbiter passes overhead at ~400 km instead of 200 million, and the 1/d²
advantage is astronomical. The Mars relay fleet and the conjunction blackout are at §31 →
`endeavour-mars-mission-design-and-settlement`.

### Navigation

Three complementary measurement types, plus one optical. **Doppler** gives line-of-sight velocity,
precise to ~0.1 mm/s. **Ranging** gives round-trip time — metres at planetary distance. **Delta-DOR**
has two stations observe the spacecraft and a quasar alternately, and differencing removes common
errors to give plane-of-sky position to **nanoradians**. **Optical navigation** — imaging the target
against background stars — is essential for approach and for small bodies where the ephemeris is
poor.

### Autonomy

Autonomy is not a nicety at distance; **it is forced by light-time.** **Safe mode** — power-positive,
thermally stable, Earth-pointed, awaiting instructions — is entered by every deep space mission, and
the design question is whether it can survive there indefinitely. **Command loss timers** reconfigure
after N days without a command, which has saved missions whose primary receivers failed. And **fault
protection that misfires is itself a hazard**: a spurious safe-mode entry during a critical event can
lose the mission. The detect/isolate/recover machinery that implements all of this, and the rules for
not recovering into the fault, are at §27 → `endeavour-satellites-flight-software-and-instruments`.
