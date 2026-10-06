---
id: skill-13-public-systems-as-publicly-described-5316c45f34
purpose: 13 public systems as publicly described
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-12-reference-architecture-830f2bc1f0"]
links: ["skill-14-deployment-checklist-28e4ad55eb"]
---

## 13. Public systems, as publicly described

These summaries restate each organization's own public descriptions at a high level; they are not independent assessments, and product status changes quickly.

- **Apple Private Cloud Compute (PCC)** — described on the Apple Security Research blog (10 June 2024) with stated requirements: stateless computation on personal user data, enforceable guarantees, no privileged runtime access, non-targetability, and verifiable transparency. Public descriptions cover custom Apple-silicon servers with Secure Enclave and Secure Boot; requests routed through third-party OHTTP relays; devices encrypting requests to keys of specific nodes whose attestations they verify; and software images published to a transparency log so devices only talk to logged software. Apple published a PCC Security Guide, a Virtual Research Environment and selected source code (October 2024) and added PCC categories to its security bounty ⚠️ verify current bounty amounts.
- **Microsoft Azure** — confidential VMs on SEV-SNP and TDX; confidential GPU VMs with NVIDIA H100 (NCCadsH100v5 series) ⚠️ verify regions and status; Microsoft Azure Attestation; Secure Key Release. Microsoft has publicly described **Azure AI confidential inferencing** combining OHTTP, confidential GPU VMs, an attested key-management service and a transparency ledger ⚠️ verify availability and current architecture.
- **Google Cloud** — Confidential VMs (AMD SEV, SEV-SNP, Intel TDX), **Confidential Space** for attested workloads with attestation-conditioned workload identity, and confidential VMs with NVIDIA H100 ⚠️ verify. Google announced **Private AI Compute** in November 2025 for Gemini processing in a hardware-isolated environment ⚠️ verify details.
- **AWS** — the **Nitro System** design restricting operator access (with an independent NCC Group review published in 2023 ⚠️ verify), **Nitro Enclaves** with attestation-conditioned KMS policies, and SEV-SNP on selected EC2 instance families. ⚠️ verify the current state of GPU confidential computing on AWS.
- **Meta WhatsApp Private Processing** — announced April 2025 for AI features over messages; public descriptions cite confidential VMs and confidential-mode GPUs, OHTTP via a third-party relay, anonymous credentials and a transparency log of binary digests ⚠️ verify.
- **NVIDIA** — Hopper and Blackwell confidential computing, the open-source `nvtrust` repository, the attestation SDK and NRAS.
- **Open source** — **Confidential Containers** (CNCF; Kata-based pod isolation in CVMs) with **Trustee** for attestation and key brokering; **Veraison** for verification components.
- **Precedent** — Signal's SGX-based private contact discovery (2017) showed the attest-then-send pattern at consumer scale; the steady stream of SGX attacks published since then is why TEE trust must be re-evaluated as research evolves.

---
