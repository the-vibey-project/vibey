---
name: physsec-securing-buildings
description: "Use when hardening a home or an organization's buildings — what the incarcerated-burglar survey says and how far to trust it, home hardening prioritized by cost-effectiveness (life safety first, door frames and strike-plate screws, deadbolt grades, sliding doors and garages, windows that stay escape routes, monitored alarms with cellular backup, cameras treated as an information-security system, safe rooms and UL RSC vs TL safe ratings, key and information control, red-teaming your own home legally), organizational security programs, tailgating, social engineering and cloned proximity badges, authorized physical penetration testing, NFPA 730/731, UFC 4-010-01 and the ISC process, life-safety codes, and targeted violence — the pathway to violence, BTAM teams, and Run–Hide–Fight. Skill 2 of 8 of the Physical Security, Self-Defense, Firearms and the ATF Substances reference."
---

# Securing Buildings

> **Skill 2 of 8** of the *Physical Security, Self-Defense, Firearms, and the "ATF Substances"* reference
> (plugin `physical-security-self-defense-and-firearms`), carrying source Part II, *Securing Buildings*: §5–§8 — homes, home hardening, organizations and commercial buildings, and targeted violence. Sibling skills:
> `physsec-foundations-and-threat-modeling` (§0–§4 — how to read the reference, threat modeling, the security mindset, layered defense and CPTED),
> `physsec-personal-security-and-self-defense` (§9–§13 — personal security, the self-defense hierarchy, training evidence, less-lethal tools and Stop the Bleed),
> `physsec-firearms-mechanics-safety-and-carry` (§14–§16 — how firearms work (conceptual), safety, storage and the risk ledger, choosing, training and carrying),
> `physsec-firearms-and-self-defense-law` (§17–§18 — federal firearms law and South Carolina carry and self-defense law, as of September 2026),
> `physsec-alcohol-tobacco-and-cannabis` (§19–§23 — cannabis, alcohol and tobacco/nicotine on mechanism, medicine, harms, law and self-defense),
> `physsec-decision-tools-and-contested-questions` (§24–§26 and Part VIII — the personal security plan, spending priorities, the organizational checklist and the contested questions),
> `physsec-reference` (§27–§30 — training and references, the glossary, the currency notes and the sources).
>
> Section numbers are **the source's own and shared across the whole set**: a reference written
> as §N → `skill` points into that sibling skill.

> **Read this first — the source's own limits and tags** (in full at §0 →
> `physsec-foundations-and-threat-modeling`). **Not legal advice** (self-defense law is
> fact-specific and South Carolina case law is detailed — talk to a criminal-defense attorney
> before you need one). **Not medical advice** (no dosing, no regimens). **Not a substitute for
> hands-on training** — firearms handling, medical skills and physical self-defense cannot be
> learned from text. Evidence tags: **\[STRONG\]** replicated, large-sample, or randomized
> evidence; professional consensus · **\[MODERATE\]** consistent observational evidence;
> plausible mechanism · **\[WEAK\]** self-report surveys, small or industry-funded studies,
> expert opinion · **\[CONTESTED\]** serious researchers disagree; both positions presented ·
> **\[LAW-2026\]** legal state as of Sept 2026; verify before relying on it. The source was
> compiled on September 30, 2026 and has not been re-checked for this pack; what will go stale
> first is listed at §29 → `physsec-reference`.

> **Pack orientation** (the pack's words, not the source's): Part II of the source, whole: homes, then organizations and commercial buildings, then
> targeted violence. Its first control is life safety, and the source is explicit that life
> safety always wins over security (§2 → `physsec-foundations-and-threat-modeling`, and §7 below).

## §5 Homes: what burglars say and what that implies

The most-cited source is UNC Charlotte's survey of **422 incarcerated burglars** in NC, KY and OH (Blevins et al.). Findings: most try to determine whether an alarm is present; roughly **60% said an alarm would make them seek another target**; about half would abandon an attempt if they discovered an alarm mid-attempt; only \~16% said they'd try to disable one. Occupancy cues (people or cars present) and nearby police rank high as deterrents. **\[WEAK–MODERATE\]** — *self-report from caught offenders, and the study was underwritten by the alarm industry's research foundation; directionally credible, but don't treat the percentages as precise.*

**Implications:** burglary is overwhelmingly about **daytime, unoccupied, easy** homes. Occupancy signals, visible alarms, good locks actually *used*, and neighbors are the backbone.

## §6 Home hardening, prioritized by cost-effectiveness

**Tier 0 — Life safety first (cheap, highest expected value)**

- Interconnected smoke alarms on every level and in/near bedrooms; CO alarms if any fuel-burning appliance or attached garage.
- Fire extinguishers (kitchen, garage); a practiced escape plan with two exits per room.
- House numbers visible from the street (EMS needs to find you).
- A real first-aid kit including a **commercial tourniquet** (§11). **\[Pack note: the source's pointer says §11; the tourniquet material is §13 → `physsec-personal-security-and-self-defense`.\]**

**Tier 1 — Doors (most forced entries are through doors)**

- **The weak point is usually the frame, not the lock.** Replace the short strike-plate screws with **3"+ screws** into the stud; use a reinforced/box strike; consider a door-jamb reinforcement kit.
- Solid-core or steel exterior doors; hinge-side security (non-removable pins for outswing doors; long hinge screws).
- Deadbolts rated **ANSI/BHMA Grade 1 or 2** with at least a 1" throw. Add pick/bump resistance if it matters to you.
- **Sliding doors**: a bar/pin in the track plus a secondary lock; anti-lift blocks.
- **Garage**: many modern homes are breached through the garage. Secure the emergency-release (the "coat hanger trick" targets it), lock the house-to-garage door like an exterior door, don't leave openers in cars parked outside.

**Tier 2 — Windows**

- Working latches plus secondary locks/pins; ground-floor laminated glass or security film (film delays, it does not make glass bulletproof).
- **Egress**: bedroom windows must remain escape routes. Any bars must have inside quick-release.

**Tier 3 — Detection**

- Monitored alarm with **cellular backup** (not just landline/Wi-Fi); door/window contacts, glass-break, motion; a keypad placed so it can't be seen from the door. The best alarm is the one you **actually arm** — many failures are simply "it wasn't on."
- Cameras: covering entries, driveway and package area. Treat cloud cameras as an **information-security system**: strong unique passwords, MFA, firmware updates, and awareness that footage can be subpoenaed or breached. Video doorbells are useful for deterring package theft and for documentation.
- Lighting: motion-activated at entries; dusk-to-dawn at dark approaches.

**Tier 4 — Delay and deny inside**

- A **safe room** is simply a room you can lock, with a solid-core door, reinforced frame, a charged phone, a light, a medical kit, and (if you choose) a defensive tool. For most families: the primary bedroom.
- Safes: know the rating language. **UL RSC** (Residential Security Container) resists \~5 minutes of attack with hand tools; **TL-15/TL-30** ratings are commercial-grade and far stronger. Fire ratings are separate and don't imply burglary resistance. Bolt larger safes to the floor.

**Tier 5 — Key and information control**

- Rekey after moving in; track who has keys/codes; use smart-lock guest codes that expire.
- Don't broadcast absences (social media, overflowing mailbox); use timers.
- Shred mail with personal data; remove address data from data brokers where possible (also a stalking countermeasure — §9 → `physsec-personal-security-and-self-defense`).

**Red-team your own home (legally).** Walk the property at night and in daytime as an opportunistic thief would. Which door is hidden from the street? Where's the ladder? Which window is unlocked? This is the physical version of a penetration test — and like any pen test, only test what you own or are explicitly authorized to test.

## §7 Organizations and commercial buildings

**Program structure (ASIS, CISA, Interagency Security Committee practice):**

1. Risk assessment (threats, vulnerabilities, consequences, existing controls).
2. Security plan with owners and budgets.
3. Access control: credentials, zones, schedules, visitor management, key control.
4. Detection: intrusion alarm, video, guard tours, SOC/monitoring.
5. Response: emergency action plan, lockdown/evacuation, liaison with police/fire/EMS.
6. **Behavioral threat assessment and management (BTAM)** — the single most important prevention layer for targeted violence (§8).
7. Training and exercises; after-action reviews.

**Access control realities:**

- **Tailgating** and **social engineering** defeat most badge systems. Physical penetration testers routinely enter with a hi-vis vest, a ladder, a clipboard, or a box of donuts. Anti-tailgating turnstiles/mantraps, "challenge culture," and receptionist visitor processes matter more than badge encryption.
- Legacy 125 kHz proximity badges are trivially cloned; modern encrypted credentials (and mobile credentials) raise the bar.
- If you commission physical testing, it requires **explicit written authorization** naming techniques, an authorization letter carried by testers, a 24/7 contact, and rules that avoid distressing pretexts or impersonating police.

**Design standards worth knowing:**

- **NFPA 730/731** (premises security guide; installation of electronic premises security systems).
- **UFC 4-010-01** (DoD minimum antiterrorism standards for buildings) — standoff distance is the most effective protection against vehicle-borne threats; bollards and hostile-vehicle mitigation for crowded places.
- **ISC Risk Management Process** for federal facilities — a well-documented, public methodology anyone can borrow.
- **Life safety codes always win** — egress, fire separation, and accessibility can't be traded for security.

## §8 Targeted violence and active assailants

**Prevention: the pathway to violence.** The US Secret Service National Threat Assessment Center (NTAC) and CISA material converge on this: attackers usually show **observable, escalating behaviors** first — grievances, fixation, threats or "leakage," research and planning, acquiring weapons, rehearsal. Organizations that have a **BTAM team** (HR, security, legal, mental health, management), a low-friction reporting channel, and a culture where people report concerns, intervene earlier. CISA's *Pathway to Violence* resources and FEMA **IS-907 "Active Shooter: What You Can Do"** (free, online) are the standard starting points. **\[MODERATE–STRONG\]**

**Response: Run – Hide – Fight** (federal guidance; many trainers use the equivalent *Avoid – Deny – Defend*):

- **Run** if there's a safe path: leave belongings, help others if possible, keep hands visible to arriving police.
- **Hide** if you can't escape: out of the shooter's view, behind locked/barricaded doors, silence phones, lights off. Cover (stops bullets) ≠ concealment (only hides you).
- **Fight** as a last resort, with total commitment, as a group if possible.
- For organizations: lockdown hardware that works from inside without special tools, pre-staged **Stop the Bleed kits** co-located with AEDs, plans for people with disabilities, and drills.

## Where to go next (pack navigation, not source text)

- **The principles these controls come from** — §1–§4 → `physsec-foundations-and-threat-modeling`.
- **Stop the Bleed kits and tourniquets** — §13 → `physsec-personal-security-and-self-defense`.
- **Household spending order and the organizational checklist** — §25–§26 → `physsec-decision-tools-and-contested-questions`.
- **FEMA IS-907, CISA and NTAC resources** — §27 → `physsec-reference`.
