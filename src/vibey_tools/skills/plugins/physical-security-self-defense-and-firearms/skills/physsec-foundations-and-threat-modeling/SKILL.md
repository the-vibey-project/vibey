---
name: physsec-foundations-and-threat-modeling
description: "Use when starting any physical-security, personal-safety or self-defense question and you need the frame first — the reference's scope and why alcohol, tobacco, firearms and cannabis are grouped, its evidence tags and limits (not legal advice, not medical advice, no dosing, not a substitute for hands-on training), the five ideas that organize it, threat modeling as risk as threat times vulnerability times consequence with what US victimization and firearm-death data say realistic risk looks like, the Saltzer–Schroeder principles translated to buildings and people including the fail-safe vs fail-secure egress tension, layered defense (deter, detect, delay, deny, respond, recover) with time as the currency, and CPTED with the CCTV and street-lighting evidence. Skill 1 of 8 of the Physical Security, Self-Defense, Firearms and the ATF Substances reference."
---

# Foundations: How to Read This, Threat Modeling, the Security Mindset, Layers and CPTED

> **Skill 1 of 8** of the *Physical Security, Self-Defense, Firearms, and the "ATF Substances"* reference
> (plugin `physical-security-self-defense-and-firearms`), carrying the source's front matter, §0 and Part I, *Foundations*: §0–§4 — how to read the reference, threat modeling, the security mindset, layered defense and CPTED. Sibling skills:
> `physsec-securing-buildings` (§5–§8 — homes, home hardening, organizations and commercial buildings, and targeted violence),
> `physsec-personal-security-and-self-defense` (§9–§13 — personal security, the self-defense hierarchy, training evidence, less-lethal tools and Stop the Bleed),
> `physsec-firearms-mechanics-safety-and-carry` (§14–§16 — how firearms work (conceptual), safety, storage and the risk ledger, choosing, training and carrying),
> `physsec-firearms-and-self-defense-law` (§17–§18 — federal firearms law and South Carolina carry and self-defense law, as of September 2026),
> `physsec-alcohol-tobacco-and-cannabis` (§19–§23 — cannabis, alcohol and tobacco/nicotine on mechanism, medicine, harms, law and self-defense),
> `physsec-decision-tools-and-contested-questions` (§24–§26 and Part VIII — the personal security plan, spending priorities, the organizational checklist and the contested questions),
> `physsec-reference` (§27–§30 — training and references, the glossary, the currency notes and the sources).
>
> Section numbers are **the source's own and shared across the whole set**: a reference written
> as §N → `skill` points into that sibling skill.

> **Read this first — the source's own limits and tags** (in full at §0
> below). **Not legal advice** (self-defense law is
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

> **If anyone in the household is in crisis**, the source's own list (§27 → `physsec-reference`):
> the **988** Suicide & Crisis Lifeline; the National DV Hotline **1-800-799-7233**; the SAMHSA
> National Helpline **1-800-662-4357**.

> **Pack orientation** (the pack's words, not the source's): The source's front matter, §0 and Part I. §0 is the frame for every other skill in the set:
> its scope, its evidence tags, what it is not, and the five ideas that organize everything
> below. Part I then sets out the foundations the rest builds on.

## About the source

> **Physical Security, Self-Defense, Firearms, and the "ATF Substances"**
>
> A research compendium — people and buildings, force and law, and how alcohol, tobacco, cannabis and firearms actually intersect with medicine and self-defense
>
> *Compiled September 30, 2026. Sources: live web research (listed in §12) **\[Pack note: the sources are listed at §30 → `physsec-reference`; the source's own pointer says §12.\]**, plus the installed reference skills for research methodology, survival and field medicine, penetration testing (physical/social engineering), cybersecurity principles, psychology of perception and memory, and medicine/pharmacology evidence standards.*

## §0 How to read this

**Scope.** Two questions were asked, and they were treated as one project:

1. *All aspects of physical security (people and buildings) and self-defense, including firearms.*
2. *How firearms, tobacco, alcohol and marijuana "work" for medicine and for self-defense.*

The second question groups four things that federal law has historically grouped together — the Bureau of **Alcohol, Tobacco, Firearms** and Explosives exists because all of them were originally regulated through excise taxes. The honest answer is lopsided: firearms have a real self-defense role and essentially no medical one; alcohol, tobacco and cannabis have narrow, specific medical roles (mostly not in the forms people consume recreationally) and essentially no self-defense role — but they matter enormously to self-defense **legally and physiologically**, because intoxication changes both what you can do and what the law will forgive. Part V covers all of that. **\[Pack note: the source says Part V; the substances are Part VI, §19–§23 → `physsec-alcohol-tobacco-and-cannabis`. Part V is firearms.\]**

**Evidence grading used throughout.**

| Tag | Meaning |
| --- | --- |
| **\[STRONG\]** | Replicated, large-sample, or randomized evidence; professional consensus |
| **\[MODERATE\]** | Consistent observational evidence; plausible mechanism |
| **\[WEAK\]** | Self-report surveys, small or industry-funded studies, expert opinion |
| **\[CONTESTED\]** | Serious researchers disagree; both positions presented |
| **\[LAW-2026\]** | Legal state as of Sept 2026; verify before relying on it |

**What this is not.** Not legal advice (self-defense law is fact-specific and South Carolina case law is detailed — talk to a criminal-defense attorney before you need one). Not medical advice (no dosing, no regimens). Not a substitute for hands-on training — firearms handling, medical skills and physical self-defense cannot be learned from text.

**The five ideas that organize everything below:**

1. **Most harm is prevented, not repelled.** Awareness, avoidance, hardening and being findable beat any fighting skill or weapon.
2. **Your realistic threat is not your imagined threat.** Most violence comes from people you know; most burglaries are opportunistic and happen when no one is home; most gun deaths are suicides. Plan for the distribution, not the movie.
3. **Layers, not silver bullets.** Deter → detect → delay → deny → respond → recover. Every layer buys time for the next.
4. **Force is the last layer and the most legally expensive one.** Every tool you carry changes your legal and moral obligations.
5. **Intoxication and weapons don't mix — medically, tactically or legally.** This is the actual intersection between the "ATF substances."

## §1 Threat modeling for the physical world

The same discipline used in cybersecurity applies here:

**Risk ≈ Threat × Vulnerability × Consequence.**

- **Threat**: who could harm you, with what capability and intent?
- **Vulnerability**: what makes you, your people or your building easy to harm?
- **Consequence**: how bad is it if it happens (injury, death, loss, trauma, legal exposure)?

Ask, in order: *What am I protecting? From whom? How likely? How bad? What will I accept? What does each countermeasure actually cost — in money, convenience, relationships, and new risks?*

**What the data says your risk actually looks like (US):**

- Violent victimization in 2024 ran about **23.3 per 1,000 persons age 12+**, and only about half of it is ever reported to police (BJS, *Criminal Victimization 2024*). **\[STRONG\]**
- Stranger violence is a **minority** of violent victimization; offenders known to the victim (partners, family, acquaintances) account for most of it. That single fact should reshape most personal security plans. **\[STRONG\]**
- Firearm deaths: **44,447 in 2024**; about **62% were suicides, 35% homicides, \~1% unintentional** (CDC WONDER via NSC and Pew). **\[STRONG\]**
- Most burglars are opportunistic amateurs who avoid occupied homes (see §5 → `physsec-securing-buildings`).
- For many households, **fire, CO, falls and vehicle crashes are larger mortality risks than crime** — a security plan that ignores smoke alarms but buys a rifle has its priorities inverted.

## §2 The security mindset (translated from information security)

The Saltzer–Schroeder principles (1975) map cleanly onto buildings and people:

| Principle | Physical translation |
| --- | --- |
| **Least privilege** | Only people who need a key/code get one; contractors get time-limited codes. |
| **Fail-safe defaults** | Doors default locked; but see the life-safety tension below. |
| **Open design** | Don't rely on a "hidden" spare key or an obscure alarm code; assume the attacker knows your layout. |
| **Separation of privilege** | Two-person rules for vaults, cash rooms, weapons storage. |
| **Complete mediation** | Every entry is checked — tailgating defeats a perfect badge system. |
| **Economy of mechanism** | Simple, robust hardware beats complex fragile systems. |
| **Psychological acceptability** | A system people find annoying gets propped open, disabled, or never armed. |

**The fail-safe vs. fail-secure tension is real and life-critical.** Electric locks that *fail open* on power loss protect occupants' ability to escape a fire; locks that *fail secure* protect the space. Building and fire codes (IBC/NFPA 101) generally require free egress — you must be able to get *out* without a key, special knowledge or effort. Never "harden" a home or business in a way that traps people in a fire. (Security-bars-without-quick-release on bedroom windows kill people every year.)

## §3 Layered defense: the "5 Ds + R"

1. **Deter** — look like a hard, risky, low-reward target (lighting, visible alarm/camera, occupancy cues, maintenance).
2. **Detect** — know early (alarms, cameras, dogs, neighbors, sensors, your own awareness).
3. **Delay** — make entry slow and noisy (reinforced doors, laminated glass, locked interior doors, safes).
4. **Deny** — keep the attacker away from the target (safe room, locked bedroom, vault).
5. **Defend/Respond** — call help, escape, or (last) use force.
6. **Recover** — medical care, documentation, legal counsel, psychological recovery, fixing the gap.

**Time is the currency.** Delay only matters if detection happens *before* the delay runs out and a response arrives. A monitored alarm with an 8-minute police response and a door that falls to one kick is a mismatch; a door that holds 3+ minutes plus a locked safe room and a phone is a coherent system.

## §4 CPTED — Crime Prevention Through Environmental Design

The core principles (first generation):

- **Natural surveillance** — sightlines. Trim shrubs below \~3 ft and tree canopies above \~6–7 ft near entries and windows; avoid "blind" recessed entrances.
- **Natural access control** — funnel people through observable entrances with paths, fencing, landscaping.
- **Territorial reinforcement** — signal ownership (well-kept yard, clear property lines, signage).
- **Maintenance / image** — the "broken windows" signal of neglect invites testing.

Second-generation CPTED adds **social cohesion and connectivity** — neighbors who know each other and notice anomalies. This is consistently among the cheapest effective controls.

**Evidence on the big environmental interventions:**

- **CCTV**: a 40-year systematic review/meta-analysis (Piza, Welsh, Farrington & Thomas, 2019) found a **modest, significant** crime reduction overall (\~13–16%), strongest in **car parks** and meaningful in residential areas, and larger when **actively monitored** and combined with other interventions; stand-alone passive cameras performed poorly. **\[STRONG\]**
- **Improved street lighting**: Welsh & Farrington's updated half-century review (2022) supports lighting as an effective public-place intervention. **\[MODERATE–STRONG\]**

## Where to go next (pack navigation, not source text)

- **Homes and buildings** — §5–§8 → `physsec-securing-buildings`.
- **People, de-escalation and non-firearm self-defense** — §9–§13 → `physsec-personal-security-and-self-defense`.
- **Firearms** — §14–§16 → `physsec-firearms-mechanics-safety-and-carry`; the law, §17–§18 → `physsec-firearms-and-self-defense-law`.
- **Alcohol, tobacco and cannabis** — §19–§23 → `physsec-alcohol-tobacco-and-cannabis`.
- **A plan built from all of it** — §24–§26 → `physsec-decision-tools-and-contested-questions`.
