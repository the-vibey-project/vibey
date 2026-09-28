---
id: skill-17-currency-snapshot-verified-august-2026-e0ebc6b3b2
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-reference/SKILL.md
requires: ["skill-16-contested-questions-ce782b808c"]
links: ["skill-18-the-canon-d4393d5958"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Google Willow** | **105 superconducting qubits, announced 9 December 2024.** First **below-threshold** error correction on real hardware — surface code at **distance 3/5/7 on one chip**, logical error rate falling roughly by half per distance increase. Published in *Nature*. ⚠️ **Not fault tolerance at useful scale**; d=7 uses 49 physical qubits per logical qubit | Low (historical) |
| **Google roadmap** | Self-assessed at **Milestone 2** (~10² physical qubits, ~10⁻² logical error). Milestone 3: long-lived logical qubit (~10³ physical, 10⁻⁶). **Milestone 6: ~10⁶ physical qubits at 10⁻¹³** — presented as a destination, **not a near-term spec** | Medium |
| **IBM roadmap** | **Nighthawk**: 120 qubits, 218 tunable couplers, ~30% more circuit complexity than Heron; **~7,500 gates in 2026** (up to 3×120-qubit modules = 360 qubits), 10,000 in 2027, 15,000 in 2028. **Loon** (2025): c-couplers for qLDPC. **Kookaburra**: ~4,158 physical qubits, first qLDPC memory + logical processing unit. **Starling (2029): 200 logical qubits from ~10,000 physical, 100M operations. Blue Jay (2033): 2,000 logical qubits, 1B operations.** Real-time decoder prototype targeted 2026 | **High** |
| **Others** | **PsiQuantum**: million-qubit photonic on a similar horizon. **DARPA QBI** funds Atom Computing, Photonic Inc., **Oxford Ionics (now part of IonQ)** and others toward 2033. **Microsoft/Quantinuum** reported logical-qubit milestones on H-series. **Atom Computing** demonstrated 1000+ neutral-atom qubits | **High** |
| **Advantage claims** | ⚠️ **30 July 2026: IBM coordinated three announcements** (arXiv preprints, 27–28 July) presented as "the quantum advantage era." **They do not carry equal evidentiary weight** — the IBM/UChicago paper has complexity-theoretic hardness arguments plus a fidelity certificate; the Qedma and Algorithmiq papers are more empirical. One ran **70 logical qubits through thousands of logical operations, logical error ~10× below physical**, in ~15 minutes | **High** |
| **Dequantization, live** | An October 2025 **peaked-circuit advantage claim on Quantinuum's 56-qubit H2** was followed by an **April 2026 IBM Quantum paper demonstrating efficient classical simulation of those circuits.** The pattern continues | **High** |
| **QEC research volume** | Peer-reviewed QEC-code papers: **36 in 2024 → 120+ between January and October 2025** | Medium |
| **NIST PQC standards** | **FIPS 203 (ML-KEM), 204 (ML-DSA), 205 (SLH-DSA)** finalized **13 August 2024**. **HQC selected March 2025** as a code-based backup KEM — **standard still being drafted** | Low |
| **NIST transition** | **RSA and ECC deprecated after 2030, disallowed after 2035**; 112-bit security deprecated after 2030 (IR 8547) | Low |
| **US federal deadlines** | ⚠️ **EO 14412 (June 2026)** mandates accelerated migration and **FAR Council contractor compliance**. **OMB M-26-15**: migration lead named by late July 2026, plan by late October 2026; **key establishment by 31 Dec 2030, signatures by 31 Dec 2031, remainder by 2035**. **EO 14144: TLS 1.3 by 2 Jan 2030** | Medium |
| **CNSA 2.0 (NSS)** | **ML-KEM-1024 + ML-DSA-87**, AES-256, SHA-384/512. Software/firmware signing **exclusive by 1 Jan 2027**; **new NSS acquisitions compliant 1 Jan 2027**; networking **2030**; OS/apps/cloud **2033**; **all NSS by 2035**. Extends across the defense supply chain. **QKD explicitly rejected** | Medium |
| **EU / UK / AU** | **EU (NIS CG, June 2025)**: roadmaps by **31 Dec 2026**, high-risk cases by **2030**, full transition by **2035**. **UK NCSC**: three-phase to 2035. **Australia ASD**: eliminate classical public-key **by 2030** | Medium |
| **Q-Day estimates** | ⚠️ **NCSC, NSA, and NIST did not revise the ~2033–2035 central estimate upward** in response to Willow, Nighthawk, or Majorana 1, and **no standards body changed its deprecation schedule as a result** | Medium |
| **Software** | **Qiskit 2.x** (12-month release cycle since 1.0; native OpenQASM 3, primitives V2). **PennyLane 0.4x**. Cirq, Q#, **CUDA-Q**, PyTKET, Braket active. **OpenQASM 3** is the portable IR | Medium |
| **US policy** | **EO 14413 (June 2026)** — national effort toward a science-enabling quantum computer, National Quantum Strategy update, domestic workforce institutes, sensing/networking plans, supply-chain strategy | Medium |

**Goes stale fastest:** vendor roadmaps and hardware milestones; advantage claims and their
refutations; federal deadline implementation details. **Essentially never stale:** §1 → `quantum-foundations-and-algorithms`
(foundations), §2 → `quantum-foundations-and-algorithms` (complexity), §3 → `quantum-foundations-and-algorithms`'s speedup classification, §4.1 → `quantum-noise-error-correction-and-hardware`, §5.1 → `quantum-noise-error-correction-and-hardware`–5.2, §9.1 → `quantum-software-and-resource-estimation`, §10.2 → `quantum-software-and-resource-estimation`–10.3
(evaluation method), §13.1 → `quantum-applications-and-post-quantum-crypto` (HNDL logic), §15 (myths).

---
