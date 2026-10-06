---
id: skill-4-gpu-confidential-computing-and-the-cpu-gpu-path-40ad89339f
purpose: 4 gpu confidential computing and the cpu gpu path
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-3-trusted-execution-cpu-confidential-vms-and-enclaves-5ff5798053"]
links: ["skill-5-remote-attestation-the-ietf-rats-model-rfc-9334-9d53a24197"]
---

## 4. GPU confidential computing and the CPU–GPU path

- **NVIDIA Hopper (H100, H200)** introduced GPU confidential computing; **Blackwell** extends it ⚠️ verify the exact Blackwell features and multi-GPU modes. The GPU has an on-die hardware root of trust, measured and signed firmware, and a device identity key whose certificate chains to an NVIDIA CA.
- **Modes:** CC off, CC on, and a developer-tools mode that permits debugging. ⚠️ verify the current mode names; a debug-capable mode must be rejected by policy.
- **GPU attestation:** the GPU produces a signed report of firmware and VBIOS measurements, appraised against NVIDIA **Reference Integrity Manifests (RIMs)** and certificate revocation status (OCSP), either locally with the NVIDIA attestation SDK and the open-source `nvtrust` tooling or via the **NVIDIA Remote Attestation Service (NRAS)**.
- **The bounce-buffer path.** A confidential VM's private memory is encrypted with a key the GPU does not hold, so without TEE-I/O the device cannot DMA into it. The CVM driver therefore stages data in **shared (unencrypted) bounce buffers**, encrypted with AES-GCM under session keys negotiated between the driver inside the CVM and the GPU using **DMTF SPDM**. The GPU decrypts into a protected region of its own memory. Consequences:
  - The host sees only ciphertext on the PCIe path, but it does see **sizes and timing** of transfers.
  - Overhead concentrates on CPU–GPU transfers (weight loading, host-side paging, large inputs); compute-bound decoding with resident weights is affected much less. ⚠️ verify current vendor and academic benchmarks for your model size and batch shape.
  - On-package HBM is protected by access control on the GPU rather than by memory encryption on H100 ⚠️ verify.
- **Multi-GPU:** tensor-parallel inference crosses NVLink/NVSwitch. NVIDIA documents specific multi-GPU confidential modes (for example a "protected PCIe" mode for HGX systems) with their own assumptions about which links are encrypted and what is in the attested set ⚠️ verify before deploying multi-GPU confidential inference.
- **TEE-I/O (the successor path):** **PCIe IDE** (link encryption) plus **TDISP** (TEE Device Interface Security Protocol, PCI-SIG) plus SPDM let a trusted device DMA directly into private memory. CPU-side support is Intel **TDX Connect**, AMD **SEV-TIO** and Arm **RME-DA** ⚠️ verify availability in shipping CPUs, GPUs and clouds.
- **Other accelerators** (AMD Instinct, cloud-provider TPUs and custom silicon) have different and evolving confidential-computing stories ⚠️ verify per vendor; do not assume parity with NVIDIA's mode.

**Composite attestation is mandatory.** The client must verify CPU evidence *and* GPU evidence *and* the binding between them. The usual pattern: code inside the measured CVM attests the GPU with a fresh nonce, refuses to use a GPU that fails (NVIDIA's flow gates the GPU's ready state on attestation ⚠️ verify), and folds the GPU evidence hash into an RTMR, PCR or `REPORT_DATA`. Because that gating logic is in the measured image, the client learns the policy was enforced.

---
