---
id: skill-16-sources-e5e5ef47f3
purpose: 16 sources
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-15-common-failure-modes-6ca8b1bb28"]
links: []
---

## 16. Sources

All references are public. Dates are publication dates; vendor documentation is cited by name because URLs move.

**IETF RFCs and drafts**
- RFC 9334 — Remote ATtestation procedureS (RATS) Architecture, January 2023 — https://www.rfc-editor.org/rfc/rfc9334
- RFC 9711 — The Entity Attestation Token (EAT), 2025 ⚠️ verify — https://www.rfc-editor.org/rfc/rfc9711
- RFC 9458 — Oblivious HTTP, January 2024 — https://www.rfc-editor.org/rfc/rfc9458
- RFC 9540 — Discovery of Oblivious Services via Service Binding Records, 2024 ⚠️ verify — https://www.rfc-editor.org/rfc/rfc9540
- RFC 9292 — Binary Representation of HTTP Messages, August 2022 — https://www.rfc-editor.org/rfc/rfc9292
- RFC 9180 — Hybrid Public Key Encryption (HPKE), February 2022 — https://www.rfc-editor.org/rfc/rfc9180
- RFC 9576, RFC 9577, RFC 9578 — Privacy Pass architecture, HTTP authentication scheme and issuance protocols, June 2024
- RFC 6962 — Certificate Transparency, June 2013 — https://www.rfc-editor.org/rfc/rfc6962
- RFC 9162 — Certificate Transparency Version 2.0, December 2021 — https://www.rfc-editor.org/rfc/rfc9162
- RFC 8446 (§7.5 exporters), RFC 5705 (keying material exporters), RFC 9266 (channel bindings for TLS 1.3)
- Drafts (status ⚠️ verify): `draft-ietf-rats-corim`, `draft-ietf-rats-ar4si`, `draft-ietf-ohai-chunked-ohttp`, `draft-fossati-tls-attestation`, OHAI/Privacy Pass key-consistency drafts

**Other specifications**
- DMTF DSP0274 — Security Protocol and Data Model (SPDM)
- PCI-SIG — Integrity and Data Encryption (IDE) and TEE Device Interface Security Protocol (TDISP)
- TCG — TPM 2.0 Library specification; PC Client Platform Firmware Profile (event log)
- C2SP — signed-note, tlog-checkpoint, tlog-cosignature, tlog-witness ⚠️ verify names
- SLSA specification; in-toto attestation framework; reproducible-builds.org documentation

**Vendor documentation (by name)**
- AMD — *SEV Secure Nested Paging Firmware ABI Specification* (publication 56860); *AMD SEV-SNP: Strengthening VM Isolation with Integrity Protection and More* (white paper, 2020); AMD Key Distribution Service documentation; AMD product security bulletins
- Intel — *Intel TDX Module* specifications; Intel SGX/TDX DCAP documentation; Intel Provisioning Certification Service; Intel Trust Authority documentation; Intel security advisories and TCB recovery notices
- Arm — Arm Confidential Compute Architecture documentation: Realm Management Monitor specification, CCA Security Model, RME system architecture
- NVIDIA — *Confidential Computing on NVIDIA H100 GPUs* (2023) and the NVIDIA trusted computing deployment guides; `nvtrust` repository; NVIDIA Attestation SDK and Remote Attestation Service documentation
- Microsoft — Azure confidential computing documentation (confidential VMs, confidential GPU VMs, Microsoft Azure Attestation, Secure Key Release); Azure AI confidential inferencing publications ⚠️ verify
- Google Cloud — Confidential VM and Confidential Space documentation; Google Private AI Compute announcement (2025) ⚠️ verify
- AWS — *The Security Design of the AWS Nitro System* (white paper); Nitro Enclaves and AWS KMS condition-key documentation
- Apple — *Private Cloud Compute: A new frontier for AI privacy in the cloud* (Apple Security Research, 10 June 2024); *Private Cloud Compute Security Guide* and Virtual Research Environment (October 2024)
- Meta — *Building Private Processing for AI tools on WhatsApp* (engineering publication, April 2025) ⚠️ verify title
- Sigstore and CNCF — Rekor documentation; Confidential Containers and Trustee documentation; Veraison project documentation

**Research cited (details ⚠️ verify where marked above)**
- Weiss et al., *What Was Your Prompt? A Remote Keylogging Attack on AI Assistants*, USENIX Security 2024
- Van Bulck et al., *Foreshadow*, USENIX Security 2018; van Schaik et al., *SGAxe*, 2020
- Li et al., *CipherLeaks*, USENIX Security 2021; Zhang et al., *CacheWarp*, 2023 (CVE-2023-20592)
- Schlüter et al., *Heckler* and *WeSee*, 2024
- De Meulemeester et al., *BadRAM*, 2024 (CVE-2024-21944); *Battering RAM*, *WireTap*, *TEE.fail*, 2025 ⚠️ verify
- Sun et al., *zkLLM: Zero Knowledge Proofs for Large Language Models*, ACM CCS 2024 ⚠️ verify
- Thinking Machines Lab, *Defeating Nondeterminism in LLM Inference*, September 2025 ⚠️ verify
- Microsoft Security, *Whisper Leak*, November 2025 ⚠️ verify
