---
id: skill-20-sources-and-method-bf462cdfbe
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-reference/SKILL.md
requires: ["skill-19-quick-reference-31f48abeba"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §1 → `quantum-foundations-and-algorithms` (foundations),
§2 → `quantum-foundations-and-algorithms` (complexity), §3 → `quantum-foundations-and-algorithms`'s classification of speedups, §4.1 → `quantum-noise-error-correction-and-hardware`, §5.1 → `quantum-noise-error-correction-and-hardware`–5.2, §9.1 → `quantum-software-and-resource-estimation`, §10.2 → `quantum-software-and-resource-estimation`–10.3,
§13.1 → `quantum-applications-and-post-quantum-crypto`'s HNDL logic, §14, §15 — rests on textbook physics, established complexity theory,
and results that have been stable for years to decades. Every **time-sensitive** claim
(hardware milestones, roadmaps, advantage claims, regulatory deadlines, software versions)
was verified against a primary or near-primary source in **August 2026** and is flagged in
§17 with a decay-risk rating. This field has an unusually high hype-to-substance ratio, so
where claims are contested I have said so explicitly rather than picking a side (§16), and
§10.3 → `quantum-software-and-resource-estimation` documents the dequantization pattern precisely because it recurs.

**Search log** (August 2026): quantum error correction, logical qubits, and vendor roadmaps ·
NIST PQC migration deadlines, CNSA 2.0, and HQC · quantum advantage claims, verifiability,
and dequantization · quantum SDKs and programming frameworks.

**Primary and near-primary sources consulted (selected):**
- **IBM Technology Atlas / IBM Quantum roadmap 2026** (`ibm.com/roadmaps/quantum/2026`) —
  Nighthawk, Loon, Kookaburra, Starling, Blue Jay, and the real-time decoder target
- **Google Quantum AI** roadmap and the Willow *Nature* result, plus the arXiv review of
  Google's milestone structure
- **NIST** — FIPS 203/204/205; Dustin Moody's "NIST PQC: The Road Ahead" (March 2025)
  transition tables; **NCCoE Migration to PQC** documentation (EO 14412, EO 14413, HQC)
- **NSA CNSA 2.0** requirements as documented across implementation guides;
  **OMB M-26-15** as reported by the **OpenSSL Corporation** analysis; **UK NCSC** PQC
  migration roadmap; **EU NIS Cooperation Group** PQC roadmap via PQShield
- **IEEE Spectrum** and **phys.org** on IBM's July 2026 verifiable-advantage papers
  (Martiel et al., arXiv 2607.25941); **postquantum.com**'s fact-check of the three claims;
  **Kremer & Dupuis (IBM Quantum, arXiv 2604.21908)** on classical simulation of peaked
  circuits, against **Gharibyan et al. (arXiv 2510.25838)**
- **Aaronson & Zhang**, "On verifiable quantum advantage with peaked circuit sampling"
  (arXiv 2404.14493); **"The Grand Challenge of Quantum Applications"** (arXiv 2511.09124)
  on verifiability as a necessary condition
- **Riverlane** on QEC publication volume; **The Quantum Insider** on migration timelines
  and the advantage debate; **IBM Quantum documentation** and **PennyLane docs** for the
  software stack

**Confidence statement.** **High confidence** in §1–§5 → `quantum-foundations-and-algorithms`, `quantum-noise-error-correction-and-hardware`'s physics, mathematics, and
complexity theory, and in §13.2 → `quantum-applications-and-post-quantum-crypto`'s standards — these are textbook material and published
federal standards. **High confidence** in the Willow result (peer-reviewed in *Nature*) and
in the IBM roadmap figures, which come from IBM's own published roadmap. **Moderate
confidence** in §7 → `quantum-noise-error-correction-and-hardware`'s broader vendor landscape and §17's competitor milestones: much of this
is drawn from press releases, preprints, and trade coverage rather than peer-reviewed work,
and **vendors have systematic incentives to present the most flattering framing** — the
qubit-count-versus-fidelity issue in §6 → `quantum-noise-error-correction-and-hardware` is exactly this problem. **Moderate confidence,
deliberately hedged, on §10.4 → `quantum-software-and-resource-estimation`'s advantage claims**: these are days-to-weeks-old preprints as
of writing, they have not been peer-reviewed, the field's own history (§10.3 → `quantum-software-and-resource-estimation`) says some
advantage claims are later matched classically, and I have reported both IBM's framing and
the documented criticism that the three papers carry unequal evidentiary weight. **Lower
confidence on §9.2 → `quantum-software-and-resource-estimation`'s specific RSA resource numbers** — these are model-dependent, have been
revised downward repeatedly, and I have deliberately given a range and a direction rather
than a point estimate. Regulatory deadlines in §13.3 → `quantum-applications-and-post-quantum-crypto` were verified against multiple
independent summaries and, where possible, primary documents, but **implementation details
change and you should verify against the current official text before making a compliance
decision.** Q-Day estimates (§16.1) are expert judgment, not measurement.
