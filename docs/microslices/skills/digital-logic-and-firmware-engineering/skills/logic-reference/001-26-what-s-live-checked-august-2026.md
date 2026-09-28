---
id: skill-26-what-s-live-checked-august-2026-3425a6a385
purpose: 26 what s live checked august 2026
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-reference/SKILL.md
requires: []
links: ["skill-27-misconceptions-4eac353a50"]
---

## §26. What's Live — checked August 2026

### 26.1 ⚠️ The Secure Boot certificates expire — a fifteen-year clock running out
**⚠️ §22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`'s key hierarchy meeting a hard date, and it affects essentially every PC sold since
around 2012.**

- **⚠️ THE DATES, and these are specific.** ⚠️ **Microsoft's original 2011 Secure Boot
  certificates have 15-year validity and expire on a staggered schedule: Microsoft
  Corporation KEK CA 2011 on 24 June 2026; Microsoft Corporation UEFI CA 2011 (which signs
  third-party bootloaders including the Linux shim) on 27 June 2026; and Microsoft Windows
  Production PCA 2011 (which signs the Windows bootloader) on 19 October 2026.**
  ⚠️ **The replacements are the 2023 family — Windows UEFI CA 2023 and Microsoft Corporation
  KEK 2K CA 2023.**
- **⚠️ WHAT ACTUALLY BREAKS — and the answer is narrower than the alarm suggests.**
  ⚠️ **Red Hat states it plainly: systems with the 2011 certificate already enrolled will
  continue to boot after 27 June 2026, because the expiration affects the ability to SIGN
  NEW BINARIES, not to boot existing ones.** ⚠️ **Microsoft's framing is that devices will
  still boot but will lose the ability to install Secure Boot security updates — entering
  what one analysis calls a degraded security state.**
- **⚠️ WHY THE KEK MATTERS MOST.** ⚠️ **One security vendor makes the sharpest point: the
  KEK is the credential that authorizes Windows Update to push new entries to a device's
  allow list (DB) and deny list (DBX).** ⚠️ **Lose that and you lose the revocation
  mechanism — meaning newly discovered malicious bootloaders can no longer be blocked.**
- **⚠️ THE THREAT THIS PROTECTS AGAINST IS REAL AND CURRENT.** ⚠️ **Microsoft cites the
  BlackLotus UEFI bootkit (CVE-2023-24932) as an example of the unsecured boot path being
  used as an attack vector today, noting bootkit malware can be difficult or impossible to
  detect with standard antivirus.**

> **⚠️ GOTCHA — the operational problem is VISIBILITY, not the update itself.** ⚠️ **One
> vendor's assessment is that most enterprises cannot answer the basic question of which
> devices in their fleet still have the 2011 KEK — and that gap is the core of the
> problem.**
> ⚠️ **Most consumer devices receive the update automatically via Windows Update, but older
> systems may require an OEM FIRMWARE update, which is a different and much less reliable
> distribution channel.**
> **⚠️ It is not only Windows.** ⚠️ **Red Hat has released shim signed with BOTH the 2011 and
> 2023 certificates so it boots on machines with either enrolled; fwupd is being used to
> distribute updated certificates on Linux, noting that at least one major OEM will not ship
> the expired key on new hardware — so existing install media may not boot on some new
> machines.** ⚠️ **Google documents the same requirement for Compute Engine Shielded VMs,
> flagging it as critical for instances using full-disk encryption or secrets sealed to
> vTPM PCRs** (§22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`'s sealing).

**⚠️ Two forward-looking notes.** ⚠️ **The 2023 certificates are reported valid until 2038 —
so this recurs.** ⚠️ **And a post-quantum transition for the boot chain is reported as
separately underway, which is the same migration problem a cryptography reference describes
arriving in the least updateable code in the machine.**
**⚠️ Sourcing note: dates and mechanics come from Microsoft, Red Hat and Google
documentation directly, which agree.** ⚠️ **The most alarming framings come from a firmware
security vendor selling fleet visibility — the underlying KEK/revocation point is
nonetheless correct and worth taking seriously.**

### 26.2 ⚠️ Open-source firmware and open silicon roots of trust
**⚠️ §20 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`'s uncomfortable truth being addressed from two directions at once.**

- **⚠️ CALIPTRA is the notable one, because it is open-source SILICON, not just firmware.**
  ⚠️ **Announced at OCP 2022 by Microsoft, Google and AMD, with NVIDIA joining, it is a
  reusable silicon-level root-of-trust IP block for datacentre-class SoCs — CPUs, GPUs,
  DPUs, TPUs, NICs and SSDs — and it is open source down to the RTL, along with the ROM and
  firmware.** ⚠️ **It now lives in the CHIPS Alliance.**
- **⚠️ THE SCOPE IS DELIBERATELY NARROW, which is why it may succeed.** ⚠️ **The project
  states the minimalist scope explicitly: define core RoT capabilities — identity, measured
  boot, attestation — and nothing else, to maximize composability, reuse across cloud
  providers and vendors, and the feasibility of open-sourcing at all.** ⚠️ **Caliptra 2.0
  defines a Root of Trust for Measurement baseline; the SoC must measure the code and
  configuration it boots into Caliptra.**
- **⚠️ CONCRETE NUMBERS from Caliptra 2.1**: ⚠️ **the complete subsystem totals 1,640,145
  gates, with approximately 62% dedicated to cryptographic accelerators, the key vault and
  key mover logic, and the remainder RISC-V cores and interface logic.** ⚠️ **That is a
  useful sanity check on what a hardware root of trust actually costs in area.**
- **⚠️ ADOPTION.** ⚠️ **AMD stated strategic plans to integrate Caliptra into its 2026+
  product lineup.** ⚠️ **One analysis reports that Microsoft and Google intend to make a
  Caliptra-based root of trust a REQUIREMENT for compute, networking and storage controller
  chips supplied to their datacentres — and that in new deployments Caliptra owns boot I/O,
  firmware layout, SoC sequencing, resets and DMA islands, with proprietary forked firmware
  not permitted.**
- **⚠️ ON THE PLATFORM FIRMWARE SIDE**: ⚠️ **AMD's openSIL abstracts silicon initialization
  so alternative bootloaders — coreboot, oreboot, LinuxBoot — can accept hand-off, replacing
  the assumption baked into AGESA and Intel FSP that UEFI comes next.** ⚠️ **AMD is explicit
  that openSIL is not intended to replace UEFI, but to enable alternatives.**
  ⚠️ **Concretely, Dasharo v0.9.0 is reported as the first officially released open-source
  firmware for a consumer AMD AM5 platform, combining coreboot with openSIL on an MSI
  PRO B850-P.**

> **⚠️ GOTCHA — "open source" here means auditable, not user-controlled, and the distinction
> matters.** ⚠️ **A Caliptra root of trust still enforces signatures against keys the SoC
> vendor or cloud operator controls; making the RTL public means the DESIGN can be
> inspected, not that you can run your own firmware on it.**
> ⚠️ **One analyst note is worth keeping in view: vendors with existing proprietary roots of
> trust — NVIDIA is named — are founding members while also keeping their own solutions, and
> "not every implementation may use Caliptra exclusively."** **⚠️ Expect coexistence rather
> than replacement.**
> **⚠️ And the consumer picture is far behind the datacentre one.** ⚠️ **A single
> motherboard being the FIRST consumer AM5 board with open-source firmware, in 2026, is the
> honest measure of how niche this remains outside hyperscale.**

**⚠️ Sourcing note: Caliptra material comes from the project's own repository and
specifications plus vendor blogs — all interested parties, though the gate counts and
architectural scope are checkable in the public RTL.** ⚠️ **The claim about hyperscaler
procurement requirements is from a paid analysis newsletter reporting conversations at OCP
and is marked accordingly.**

---
