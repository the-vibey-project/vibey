---
id: skill-13-functional-safety-and-standards-ca9acfbfe8
purpose: 13 functional safety and standards
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-safety-standards-and-deployment/SKILL.md
requires: ["skill-12-testing-debugging-and-deployment-070457cd15"]
links: ["skill-14-aerospace-flight-software-adc519bb93"]
---

## §13. Functional Safety and Standards

**[VERSIONED — and this regime changed substantially in 2025, which many practitioners
have not caught up with.]**

### 13.1 ⚠️ The ISO 10218:2025 revision

**ISO 10218-1:2025** (robot manufacturers) and **ISO 10218-2:2025** (integrators,
applications, and cells) were **published February 2025 and came into force 1 April 2025**
— **the first major revision since 2011**, taking experts from **20+ countries nearly
eight years**.

**What changed, and why it matters:**
- ⚠️ **ISO/TS 15066 no longer exists as a standalone specification.** Its power-and-force-
  limiting and collaborative-application requirements were **folded directly into
  ISO 10218-2**. **There is no separate cobot standard to cite anymore.**
- ⚠️ **The terms "collaborative robot" and "collaborative operation" do not appear in the
  revised standard.** **Collaboration is a property of the *application*, not the robot** —
  only an application can be assessed. **This kills the "we bought a collaborative robot,
  therefore we're safe" reasoning outright**, and that reasoning was extremely common.
- **Functional safety requirements are now explicit rather than implied**, with a
  robot **classification scheme** (Class I / Class II).
- ⚠️ **Cybersecurity requirements were added** — for the first time, on the reasoning that
  millions of networked industrial robots exist.
- Manual load/unload and end-effector guidance folded in from separate technical reports.
- **ISO 10218-2:2025 nearly tripled in length.**

**The standards stack around it**: **ISO 12100** (risk assessment methodology) and
**ISO 13849-1:2023** (safety-related control systems, PL/categories) underneath;
**ANSI/A3 R15.06-2025** and **CSA Z434** as the North American adoptions;
**IEC 61508** for general functional safety; **ISO 26262** (automotive) and **ISO 21448
/ SOTIF** (⚠️ **safety of the intended function — hazards from performance limitations
rather than faults, which is exactly the right frame for learned perception**).

**⚠️ On enforceability**: ISO standards are voluntary in themselves. **They become binding
through contracts and through harmonisation** — in the EU under **Machinery Regulation
2023/1230, which applies from 20 January 2027**. In the US, OSHA enforcement provides the
pressure.

### 13.2 ⚠️ The humanoid gap

**[VERSIONED and genuinely unresolved.]** The 2025 revision **explicitly leaves regulatory
gaps around AI, humanoids, and mobile manipulation.** ISO/TS 15066's contact-force model
addressed **stationary arms**; **humanoids walk, balance, and carry energy-dense
batteries** — different hazards entirely (fall zones, dynamic stability, thermal events).
**ISO 25785-1 is under development for dynamically stable robots**, and until it lands,
**humanoid deployments are being certified against a standard that wasn't written for
them.** ⚠️ **If you are deploying humanoids, this gap is your problem, not the standard's.**

### 13.3 [DURABLE] The engineering practices
**Risk assessment first** (ISO 12100 methodology), **safety functions on rated hardware**
(⚠️ **a safety-rated stop is not `if (bad) stop();` in your application code**),
**redundancy and diversity** for safety functions, **safe states designed rather than
inherited**, **E-stop reachable from anywhere in the workspace**, **speed and separation
monitoring** or **power and force limiting** as the collaborative strategies, and
**⚠️ a written safety case** — the artifact that says what the system will not do and why
you believe it.

---
