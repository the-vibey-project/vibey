---
id: skill-3-trusted-execution-cpu-confidential-vms-and-enclaves-5ff5798053
purpose: 3 trusted execution cpu confidential vms and enclaves
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-2-threat-model-parties-assets-and-the-trust-you-cannot-remove-41c68db807"]
links: ["skill-4-gpu-confidential-computing-and-the-cpu-gpu-path-40ad89339f"]
---

## 3. Trusted execution: CPU confidential VMs and enclaves

### AMD SEV-SNP (Secure Encrypted Virtualization – Secure Nested Paging)

- Available on AMD EPYC from the 3rd generation (Milan) onward. Per-VM memory encryption keys are managed by the **AMD Secure Processor** and never exposed to the hypervisor.
- **Integrity:** the **Reverse Map Table (RMP)** records ownership of every physical page, so the hypervisor cannot remap, replay or alias guest pages through software. **VM Privilege Levels (VMPLs)** let a small paravisor or **SVSM** (Secure VM Service Module) run at VMPL0 below the guest OS, for example hosting a vTPM.
- **Attestation report** (requested by the guest from firmware) includes: `MEASUREMENT` (launch digest of the initial guest memory — firmware and, with measured direct boot, hashes of kernel, initrd and command line), `REPORT_DATA` (64 bytes chosen by the guest — put your nonce and key hash here), `HOST_DATA` (set by the host, so untrusted unless pinned), `POLICY` (including whether debug is allowed), TCB version fields and `CHIP_ID`.
- **Signed by** the **VCEK** (Versioned Chip Endorsement Key, unique per chip *and* per TCB version) chaining via ASK to the AMD Root Key (ARK), or by a **VLEK** (Versioned Loaded Endorsement Key) provisioned to a cloud provider. Certificates come from the **AMD Key Distribution Service (KDS)**.
- **Spec:** AMD *SEV Secure Nested Paging Firmware ABI Specification* (publication 56860).

### Intel TDX (Trust Domain Extensions)

- Available on Intel Xeon Scalable processors from 4th generation (limited SKUs) and broadly from 5th generation ⚠️ verify the SKU list. Trust Domains (TDs) are managed by the Intel-signed **TDX module** running in SEAM mode.
- **Measurements:** `MRTD` (build-time measurement of initial TD contents, typically the TD virtual firmware), four runtime-extendable registers `RTMR[0..3]` (firmware configuration, kernel and initrd, command line, application — analogous to TPM PCRs), plus host-supplied `MRCONFIGID`, `MROWNER` and `MROWNERCONFIG` (untrusted unless your policy pins them). `REPORTDATA` is 64 guest-chosen bytes.
- **Quote path:** the locally MACed `TDREPORT` is converted into a signed **Quote** by an SGX-based quoting enclave using **DCAP** (Data Center Attestation Primitives). The PCK certificate chain roots at the Intel SGX Root CA; collateral (TCB Info, QE Identity, CRLs) comes from the **Intel Provisioning Certification Service (PCS)** or a caching service. Appraisal yields a TCB status such as `UpToDate`, `SWHardeningNeeded` or `OutOfDate` — decide in policy which statuses you accept.

### Arm CCA (Confidential Compute Architecture)

- Built on the Armv9-A **Realm Management Extension (RME)**: four physical address spaces (Normal, Secure, Realm, Root) enforced by Granule Protection Checks; **Realms** are managed by the **Realm Management Monitor (RMM)**.
- **Attestation token** is a CBOR/COSE structure in the EAT family combining a **platform token** (signed by the CCA platform attestation key) and a **realm token** (Realm Initial Measurement plus Realm Extensible Measurements).
- ⚠️ verify: availability of CCA in shipping server silicon and public clouds was limited as of compilation; treat it as the architecture to plan for on Arm rather than a deployable inference target today.

### Enclaves versus confidential VMs

| | Process enclave (Intel SGX) | Confidential VM (SEV-SNP, TDX, CCA) | Hypervisor-isolated enclave (AWS Nitro Enclaves) |
|---|---|---|---|
| Isolation boundary | Part of one process | Whole guest VM | Carved-out VM with no network, no storage, vsock only |
| TCB | Smallest — your enclave code plus CPU | Guest firmware, kernel, userland plus CPU | Your image plus the AWS Nitro hypervisor and cards |
| Root of trust | CPU vendor | CPU vendor | Cloud provider (AWS Nitro PKI), not a CPU vendor |
| Porting | Partition the app or use a library OS (Gramine, Occlum) | Lift and shift | Repackage as an enclave image |
| GPU access | No | Yes, with a CC-capable GPU (§4) | No |

**For GPU inference in 2026 the confidential VM is the practical route.** Its weakness is the large guest TCB, so shrink it: a minimal immutable image, no SSH or interactive shell, a read-only root filesystem verified by **dm-verity** whose root hash is in the measured kernel command line (or a measured Unified Kernel Image), and no package manager at runtime.

**Note:** SGX was removed from Intel client processors from the 11th/12th generation but remains on Xeon server parts ⚠️ verify. It remains useful for small key-handling or gateway components, not for model execution.

---
