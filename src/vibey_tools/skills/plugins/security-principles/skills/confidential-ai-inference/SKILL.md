---
name: confidential-ai-inference
description: "Use when designing, reviewing or explaining confidential AI inference: serving models so that prompts, outputs and weights stay protected from the cloud operator and host, verifiably. Covers the threat model and what TEEs do not stop, CPU confidential VMs (AMD SEV-SNP, Intel TDX, Arm CCA), NVIDIA GPU confidential computing and the bounce-buffer path, IETF RATS remote attestation (RFC 9334), attested TLS and channel binding, Oblivious HTTP relays (RFC 9458), transparency logs and reproducible builds (RFC 6962, RFC 9162, Sigstore Rekor), zkML and redundant execution, attestation-gated key release, a reference architecture, a deployment checklist and common failure modes. Companion to threat-modeling-playbook and ai-security-practices."
---

# Confidential AI Inference: Protecting Prompts, Outputs and Weights — Verifiably

> **Part of the `security-principles` plugin.** Sibling skills: `threat-modeling-playbook` (STRIDE, trust boundaries, data flow diagrams — run it on the architecture in §12), `ai-security-practices` (prompt injection, output handling, secrets, SLSA/Sigstore supply chain — everything *inside* the enclave still needs it), `ai-era-security` (OWASP LLM/Agentic Top 10, post-quantum cryptography — relevant to the HPKE keys in §7), `cybersecurity-principles` (least privilege, open design, complete mediation — the principles this skill applies to hardware trust).
>
> **Currency:** compiled October 2026 from public specifications, RFCs and vendor documentation. The IETF RFCs cited are stable. Vendor product names, GPU confidential-computing modes, cloud SKUs, verifier services and every attack paper move quickly: anything marked **⚠️ verify** was believed accurate at compilation but must be re-checked against the vendor's current documentation before you rely on it.
>
> **Not a certification or compliance claim.** This is an engineering reference; a production system needs its own threat model, an independent review and the hardware vendors' current security guidance.

> **The three ideas that organize this document:**
> 1. **ATTESTATION PROVES IDENTITY, NOT VIRTUE.** A valid attestation proves you are talking to exactly the code that was measured — including its bugs and its logging statements. Confidentiality comes from *what that code does*, so the code must be published, reproducible and reviewed.
> 2. **EVERY MECHANISM MOVES TRUST; NONE REMOVES IT.** TEEs move trust from the cloud operator to the hardware vendor; OHTTP moves it to a non-colluding relay; transparency logs move it to witnesses and auditors. Write down who is left in the trusted set and why.
> 3. **THE CLIENT IS THE ENFORCEMENT POINT.** Nothing is verifiable if the client does not verify. A server that attests to nobody, or a client that continues on a failed check, is ordinary hosting with extra steps.

---

## 1. What confidential inference is — and what it is not

**Confidential inference** is serving a model so that the parties operating the infrastructure — the cloud provider, its administrators, the host OS and hypervisor, and ideally the service operator's own staff — cannot read user prompts, model outputs, or (optionally) the model weights, and so that a client can **verify** this before sending data, rather than trusting a policy document.

It combines four layers, each answering a different question:

| Layer | Question it answers | Primary mechanism |
|---|---|---|
| Isolation | Can the host read or tamper with memory in use? | TEE: confidential VM or enclave, confidential GPU (§3, §4) |
| Attestation | Is the thing I am talking to the genuine, expected TEE and software? | Remote attestation, IETF RATS (§5, §6) |
| Unlinkability | Can the service tie *what* I asked to *who* I am? | Oblivious HTTP relays, anonymous credentials (§7) |
| Accountability | Is the software that runs the same software everyone else can inspect? | Transparency logs, reproducible builds (§8) |

What it is **not**:
- **Not end-to-end encryption to a person.** The plaintext exists in the server's memory; the protection is hardware isolation plus code you can inspect, not mathematics alone.
- **Not a guarantee of correct output.** It protects data and constrains which code runs; whether the code computes the right answer is a separate integrity question (§9).
- **Not protection from the model itself** — prompt injection, data leakage through outputs, and tool misuse are unchanged. See `ai-security-practices`.
- **Not availability.** The host can always stop, starve or restart the workload.

---

## 2. Threat model: parties, assets, and the trust you cannot remove

**Assets:** prompts and attachments; outputs (including streamed tokens); per-user state (conversation history, KV cache); model weights and adapters; request metadata (identity, IP, timing, sizes); and the signing and decryption keys that protect all of the above.

### Parties and residual trust

| Party | What they could do without controls | What constrains them | What you still trust them for |
|---|---|---|---|
| **Client** (device + app) | Nothing against itself, but it runs the verification code | Open client code; client binary transparency | Correctly verifying evidence; not leaking locally |
| **Model provider / service operator** | Write serving code that logs or exfiltrates prompts | Published, reproducible, transparency-logged code; attestation pins it | Authoring honest code — *mitigated only by public audit*, never by the TEE |
| **Cloud / host operator** | Read guest memory, snapshot VMs, tamper with disk and network, inject interrupts | CPU memory encryption and integrity (SEV-SNP, TDX, CCA); GPU CC mode | Availability; not mounting physical or side-channel attacks beyond the vendor's threat model |
| **Hardware vendor** (CPU, GPU) | Sign false endorsements; ship flawed firmware or microcode | Very little — public scrutiny, published TCB recovery | Root keys, firmware (AMD Secure Processor, Intel TDX module, NVIDIA GPU firmware), honest endorsement |
| **Verifier service** (if third party) | Issue false attestation results | Running verification yourself; multiple verifiers | Correct appraisal, if you delegate to it |
| **OHTTP relay operator** | Link IP to timing and size; collude with the gateway | Operated by an independent organization; contractual non-collusion | Not colluding; stripping identifying headers |
| **Transparency log operator** | Show different log views to different clients (split view) | Witness cosigning, gossip, independent monitors | Availability; the witness set not colluding |
| **KMS / key-release administrator** | Relax a release policy so keys go to unattested code | Policy under multi-party control; logged policy changes | Not changing the policy silently |

**Note:** the service operator is the hardest party to exclude. A TEE cannot tell whether the measured code is honest — it only guarantees that the code is the code that was measured. Exclusion of the operator therefore rests on §8 (public, reproducible, logged releases that someone actually audits).

### Which mechanism gives which property

| Mechanism | Confidentiality | Integrity | Verifiability | Unlinkability |
|---|---|---|---|---|
| Confidential VM / enclave | Yes, against host software and admins | Yes, of memory against host software | No, not by itself | No |
| Confidential GPU mode | Yes, for data in GPU memory and on the PCIe path | Yes, of transfers (authenticated encryption) | Via GPU attestation | No |
| Remote attestation | No (it is a signed statement) | Proves initial state and measured changes | Yes — of identity and configuration, at a point in time | No |
| Channel binding (attested TLS, HPKE) | Yes — ensures you encrypt *to the TEE* | Prevents relay and diversion | Ties evidence to the session | No |
| OHTTP + relay | No (gateway sees plaintext request) | Request integrity via AEAD | No | Yes, given relay and gateway do not collude |
| Transparency log | No | Append-only history of releases | Yes — non-equivocation, after-the-fact detection | No |
| Reproducible build | No | Links source to binary to measurement | Yes, for anyone who rebuilds | No |
| zkML proof | No (the prover sees the input) | Yes, cryptographically | Yes, without trusting hardware | No |

### What TEEs do NOT protect against

- **Microarchitectural and software side channels.** Cache and page-fault channels, single-stepping, and ciphertext side channels have repeatedly been shown against SGX and SEV (for example Foreshadow 2018 on SGX; CipherLeaks 2021 and CacheWarp, CVE-2023-20592, on SEV; Heckler and WeSee in 2024 abusing interrupt injection from a malicious hypervisor). Vendors typically place many side channels outside their threat model and expect constant-time code inside the guest. ⚠️ verify each vendor's current side-channel guidance.
- **Metadata leakage specific to LLMs.** Streaming one token per encrypted packet leaks token lengths; Weiss et al., *What Was Your Prompt? A Remote Keylogging Attack on AI Assistants* (USENIX Security 2024) reconstructed responses from packet sizes. Microsoft's *Whisper Leak* (November 2025) reported topic inference from encrypted streaming traffic timing and sizes ⚠️ verify. Pad and batch tokens; the TEE does not hide traffic shape.
- **Shared-cache timing across users.** Cross-user prefix or KV-cache sharing can reveal whether another user sent a given prefix through time-to-first-token differences (several 2024–2025 papers) ⚠️ verify. Isolate caches.
- **Rollback.** Of firmware (old, vulnerable TCB versions still produce cryptographically valid reports unless policy enforces a minimum), of sealed state (confidential VMs have no hardware monotonic counters for your data), and of evidence (replay of an old report without a fresh nonce).
- **Vendor key compromise.** Extraction of attestation keys lets an attacker forge evidence for *every* deployment trusting that root — SGAxe (2020) extracted SGX attestation keys from production parts.
- **Physical attacks.** CPU memory encryption for confidential VMs uses deterministic, address-tweaked encryption without freshness on DRAM, so a memory-bus interposer or address aliasing can replay or observe ciphertext. BadRAM (December 2024, CVE-2024-21944) aliased memory via a tampered DIMM SPD chip against SEV-SNP; Battering RAM, WireTap and TEE.fail (2025) reported low-cost DDR4/DDR5 interposers against SGX, SEV-SNP and TDX, including attestation-key extraction ⚠️ verify the details and vendor responses. Vendors generally exclude physical attackers from the confidential-VM threat model; your data-centre and supply-chain controls still matter.
- **Bugs in the attested code.** Attestation faithfully certifies a vulnerable inference server, a debug endpoint left enabled, or a log line that prints prompts. Guest-kernel hardening against a malicious host (virtio, shared-memory parsing, `#VC`/`#VE` exception handlers) is part of your TCB.
- **Anything the code sends out.** Telemetry, crash reports, tool calls, retrieval queries and outbound HTTP all leave the TEE by design if the code allows them.
- **Denial of service** and **model-level attacks** (memorization, extraction via the API, prompt injection).

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

## 5. Remote attestation: the IETF RATS model (RFC 9334)

**RFC 9334** (*Remote ATtestation procedureS (RATS) Architecture*, January 2023) gives the vocabulary every design review should use.

### Roles

| Role | In a confidential inference deployment |
|---|---|
| **Attester** | The confidential VM plus GPU, producing evidence |
| **Verifier** | Appraises evidence against policy — a client library, your service, or a SaaS verifier |
| **Relying Party** | Acts on the result — the client deciding to send a prompt; the KMS deciding to release a key |
| **Endorser** | Vouches for the attester's signing capability — AMD (VCEK chain), Intel (PCK chain), NVIDIA (device CA) |
| **Reference Value Provider** | Publishes expected measurements — your reproducible release pipeline, NVIDIA RIMs |
| **Verifier Owner / Relying Party Owner** | Set the appraisal policies |

### Conceptual messages

- **Evidence** — signed claims about the attester (the SNP report, TDX Quote, CCA token, GPU report).
- **Endorsements** — vendor statements that make the evidence trustworthy (certificate chains, TCB info).
- **Reference Values** — the measurements you expect.
- **Appraisal Policy for Evidence** — the verifier's rules; **Appraisal Policy for Attestation Results** — the relying party's rules.
- **Attestation Results** — the verifier's signed verdict (often a JWT or EAT) consumed by the relying party.

**Topologies:** in the **passport model** the attester obtains an attestation result and presents it to the relying party; in the **background-check model** the relying party forwards raw evidence to a verifier. CPU-plus-GPU is a **composite attester** — each component's evidence must be appraised and linked.

### Measurements

- **Launch measurement:** SEV-SNP `MEASUREMENT`, TDX `MRTD`, CCA Realm Initial Measurement. Covers only what was loaded at launch — everything later must be *chained*.
- **Runtime measurements:** TDX `RTMR`s, CCA extensible measurements, and **TPM PCRs** (including a **vTPM** inside the CVM, hosted by a paravisor or SVSM). A vTPM is only meaningful if its attestation key is bound to the hardware report (for example, its public key hash in `REPORT_DATA`).
- **Event logs:** a PCR or RTMR value is an opaque hash chain. The verifier must **replay the event log** (TCG PC Client firmware event log, or the kernel's IMA log) to recompute the register *and then appraise each event*.

### Freshness

RFC 9334 discusses nonces, timestamps and epoch identifiers. For interactive inference, use a **client-chosen nonce** in `REPORT_DATA` or the equivalent, or a short-lived signed attestation result whose validity window your policy bounds. Cached evidence without freshness invites replay of a report from a since-revoked TCB.

### Formats and open implementations

- **EAT** — *The Entity Attestation Token* (RFC 9711, 2025) ⚠️ verify the RFC number and date.
- **CoRIM** — Concise Reference Integrity Manifest (`draft-ietf-rats-corim`) for reference values and endorsements ⚠️ verify status.
- **EAR** — EAT Attestation Results (`draft-ietf-rats-ar4si` and related) ⚠️ verify status.
- **Veraison** (open-source verifier components) and **Trustee** (the Confidential Containers key broker and attestation service) are vendor-neutral starting points.

### Verifier services (third parties join your trusted set)

Intel Trust Authority; Microsoft Azure Attestation; Google Cloud Attestation (used by Confidential Space); NVIDIA Remote Attestation Service; AWS Nitro Enclaves attestation documents verified directly or by AWS KMS ⚠️ verify current product names. Delegating appraisal adds the verifier to the trusted set; verifying on the client removes it but means shipping collateral, revocation data and policy updates to every client.

---

## 6. Binding attestation to the channel — and what the client must check

An attestation report by itself proves that *some* genuine TEE produced it. It does not prove that the bytes you are about to encrypt will reach *that* TEE. An attacker can relay your challenge to a genuine TEE and serve you from elsewhere (a relay or diversion attack). The fix is to **bind a key generated inside the TEE to the evidence**: put `hash(public key ‖ nonce)` into `REPORT_DATA` (SNP), `REPORTDATA` (TDX), the realm challenge (CCA) or the `public_key`/`user_data` fields (Nitro).

Binding patterns:
- **RA-TLS / attested certificates:** the TEE generates its TLS key and embeds evidence in an X.509 extension; the client verifies evidence instead of (or as well as) WebPKI.
- **Post-handshake attestation over a TLS exporter:** evidence covers a value from the TLS 1.3 exporter (RFC 8446 §7.5, RFC 5705; channel binding type `tls-exporter`, RFC 9266), proving the evidence belongs to this session.
- **Attested HPKE keys:** the gateway publishes an HPKE public key together with evidence binding it; the client encrypts each request to that key. This is the natural fit for OHTTP (§7).
- **Standards work:** the IETF is working on attestation in TLS (for example `draft-fossati-tls-attestation` and the SEAT working group) ⚠️ verify current names and status.

**Terminate TLS or HPKE inside the TEE.** A load balancer or API gateway outside the TEE that terminates TLS defeats everything above it.

### The client checklist

1. **Signature chain** to a pinned vendor root (AMD ARK, Intel SGX Root CA, NVIDIA device CA, Arm CCA platform root), with revocation checked.
2. **TCB at or above your minimum** — not merely "valid". Reject `OutOfDate` TDX statuses and SNP reported TCBs below policy.
3. **Debug disabled** — SNP policy debug bit clear, TDX debug attribute clear, GPU not in a developer-tools mode, Nitro not in debug mode (its PCRs read as zeros in debug mode).
4. **Launch and runtime measurements match published reference values**, with event logs replayed and appraised.
5. **The release is in the transparency log** — inclusion proof against a checkpoint consistent with the last one you saw, cosigned by your required witnesses (§8).
6. **Freshness** — your nonce, or a result inside your validity window.
7. **Channel binding** — the key you encrypt to is the key in the evidence.
8. **GPU evidence verified and bound** to the CPU evidence; CC mode on.
9. **Model identity** — the weight digest (or the key-release policy that gates the weight key) is in the measured state.
10. **Host-controlled fields** (`HOST_DATA`, `MRCONFIGID`, `MROWNER`) treated as untrusted unless pinned.
11. **Fail closed.** No "continue anyway", no silent fallback to a non-confidential endpoint.

---

## 7. Oblivious HTTP and relays: separating who-you-are from what-you-ask

**RFC 9458** (*Oblivious HTTP*, January 2024) splits a request across two parties that must not collude.

| OHTTP resource | Sees | Does not see |
|---|---|---|
| **Client** | Everything about its own request | — |
| **Oblivious Relay Resource** | Client IP address, timing, encapsulated size | Request or response content |
| **Oblivious Gateway Resource** | Decrypted request and response | Client IP (only the relay's) |
| **Target Resource** | The request as forwarded by the gateway | Client IP |

- **Encapsulation:** requests are **Binary HTTP** messages (RFC 9292) encrypted with **HPKE** (RFC 9180) to the gateway's public key; responses are encrypted under a key derived from that exchange, so only the requesting client can read the reply.
- **Key configuration:** a key identifier, KEM and KDF/AEAD pairs, served as `application/ohttp-keys`. Discovery via SVCB/HTTPS records is specified in RFC 9540 ⚠️ verify.
- **Key consistency is a privacy requirement.** A malicious gateway can give each client a *unique* key configuration and so tag users. Clients must obtain the same configuration as everyone else — fetched through the relay, pinned in the app, or published in a transparency log — ⚠️ verify the current state of IETF key-consistency drafts.
- **Authorization without identity:** an account token inside the encapsulated request re-links identity to content. Use **Privacy Pass** anonymous tokens (RFC 9576 architecture, RFC 9577 HTTP authentication scheme, RFC 9578 issuance protocols, June 2024) for rate limiting and entitlement.
- **Streaming:** RFC 9458 encapsulates whole messages. Token streaming needs an incremental variant — `draft-ietf-ohai-chunked-ohttp` ⚠️ verify status — and padding to blunt the token-length side channel in §2.
- **Post-quantum:** prompts captured today could be decrypted later if HPKE uses only X25519. Consider a hybrid post-quantum KEM once your HPKE library and the relevant drafts support one ⚠️ verify (see `ai-era-security` §7).

**Combining OHTTP with an attested gateway.** Put the gateway inside a TEE, generate its HPKE key inside the TEE, publish the key configuration *with evidence binding it* (§6), and have the client verify before encapsulating. The cloud then sees only ciphertext, the relay sees only the IP, and the gateway's plaintext view is constrained to attested, published code.

**Collusion assumptions to write down:** relay and gateway run by different organizations; the relay does not log beyond operational need; no shared telemetry. OHTTP is **not a mixnet** — a global passive observer, or a low-volume service with a tiny anonymity set, can still correlate timing and sizes.

---

## 8. Transparency logs, reproducible builds and binary transparency

Attestation says *which* measurement is running. Transparency makes that measurement **publicly committed**, so that the operator cannot run a special build for one target without the world being able to see it.

### Merkle logs

- **Certificate Transparency** — RFC 6962 (June 2013, experimental) and **CT 2.0**, RFC 9162 (December 2021). An append-only Merkle tree; the log signs a **tree head** (checkpoint) over size and root hash.
- **Inclusion proof:** about log2(n) sibling hashes from a leaf to the root, proving the entry is in the tree.
- **Consistency proof:** proves the tree of size *m* is a prefix of the tree of size *n* — nothing was rewritten.
- **Split view** — the log showing different trees to different clients — is the main threat. Mitigate with **witnesses** that cosign checkpoints only after checking consistency (C2SP `tlog-checkpoint`, `tlog-cosignature`, `tlog-witness` specifications ⚠️ verify names) and with independent **monitors** that watch for unexpected entries.
- **Sigstore Rekor** — the transparency log for signatures and attestations in the Sigstore ecosystem; a tile-based Rekor v2 ⚠️ verify version and status. The **Go checksum database** (`sum.golang.org`) and Android/Pixel **binary transparency** are working precedents for logging binaries that clients check.

### What to log for confidential inference

A signed **release manifest** per deployable image: source commit; build recipe and toolchain digests; image digest; expected launch measurement(s) for each supported CPU platform; expected RTMR/PCR reference values or the event-log policy; GPU driver and firmware expectations; **model weight and tokenizer digests**; and the version of the key-release policy. Clients and the KMS accept only manifests with valid inclusion proofs.

### Reproducible builds

If the measurement can only be produced by your build farm, users must trust your build farm. **Reproducible builds** (reproducible-builds.org) let third parties rebuild from source and obtain the identical image and measurement. Pair them with **SLSA** provenance and **in-toto** attestations (see `ai-security-practices`). Launch measurements can be predicted offline — the SEV-SNP launch digest from the firmware binary plus kernel, initrd and command-line hashes; TDX `MRTD` from the TD firmware and RTMRs from the event log — with open-source measurement calculators ⚠️ verify tool names.

### How a client verifies

1. Fetch the manifest, its inclusion proof and the latest checkpoint (with witness cosignatures).
2. Verify the checkpoint signature and the required cosignatures.
3. Verify the inclusion proof for the manifest leaf.
4. Verify a consistency proof from the last checkpoint the client stored to the new one; store the new one.
5. Check that the attested measurement equals the manifest's reference value.

**Note:** transparency provides **non-equivocation and after-the-fact detection**, not safety. It only helps if someone audits the logged releases — independent researchers, a published research environment, bounties.

---

## 9. Verifiable inference beyond TEEs

TEEs ask you to trust hardware vendors. The alternatives replace that with cryptography or redundancy, at a cost.

| Approach | What it proves | Confidentiality of the prompt | Practical status (October 2026) |
|---|---|---|---|
| **zkML** (SNARK/STARK proof of inference) | Output = model(committed weights, input) | No — the prover sees the input; weights *can* stay hidden from the verifier | Small models practical; LLM-scale proofs research-grade and orders of magnitude slower than inference ⚠️ verify |
| **Optimistic / fraud-proof** | Output is correct unless someone disputes in a window; bisection to a single step | No | Needs determinism and a challenge period; suited to on-chain or batch settings |
| **Redundant execution** | k independent providers agree | No — *k* parties now see the prompt | Simple; multiplies cost and data exposure unless each replica is itself a TEE |
| **Sampled spot-checks / activation fingerprints** | Statistical evidence the claimed model ran | No | Emerging (for example locality-sensitive hashes of activations) ⚠️ verify |
| **FHE / MPC** | Computation on encrypted data / secret shares | Yes, cryptographically | FHE far too slow for LLM-scale serving; MPC prototypes carry large communication overhead ⚠️ verify |

- **zkML detail:** tooling such as EZKL targets small models; *zkLLM* (ACM CCS 2024) reported proofs for 13B-parameter LLaMA-family inference in minutes per inference on large GPUs ⚠️ verify the figures. Fixed-point quantization for circuits changes numerics, so the proven model is not bit-identical to the served one unless you serve the quantized version.
- **Where each fits:** TEEs for interactive, confidential serving at scale; zkML for high-value, low-volume claims ("this credit score used the audited model"); optimistic and redundant schemes for decentralized compute markets where integrity matters more than secrecy.

### Deterministic inference

Every scheme that compares outputs needs reproducibility, and GPU inference is not deterministic by default: floating-point addition is not associative, kernels use atomics, and **batch composition changes reduction order**, so the same prompt can yield different tokens depending on server load. Thinking Machines' *Defeating Nondeterminism in LLM Inference* (September 2025) attributed much of this to lack of batch invariance ⚠️ verify. Mitigations: batch-invariant kernels, fixed seeds and greedy decoding for verification runs, pinned library and driver versions, identical GPU SKUs and parallelism layout, and tolerance-based (top-k or logit-distance) comparison rather than exact token equality.

---

## 10. Engineering the system

### Key release on attestation

Never bake secrets into images. The gateway's HPKE and TLS keys, weight-decryption keys and any log-encryption keys are released by a key broker **only to evidence that satisfies policy**:

- **Azure Key Vault Premium / Managed HSM Secure Key Release** — a release policy evaluated over Microsoft Azure Attestation token claims ⚠️ verify claim names.
- **AWS KMS with Nitro Enclaves** — key-policy condition keys on the attestation document, such as `kms:RecipientAttestation:ImageSha384` and `kms:RecipientAttestation:PCR<n>`.
- **Google Cloud Confidential Space** — workload identity federation with attribute conditions over the attestation token (image digest, support attributes) ⚠️ verify.
- **Confidential Containers Trustee** — a key broker service with policy (for example Rego) over appraised evidence.

Policy content: pinned measurement *or* "signed by the release key **and** included in the transparency log"; minimum TCB; debug off; GPU in CC mode; freshness. The **policy itself is a trust point** — whoever can edit it can release keys to anything. Put it under multi-party control, log every change, and treat KMS audit logs (which record each release and the evidence presented) as security records.

### Model-weight protection

- Encrypt weights at rest per shard (AEAD); decrypt only inside the CVM; move to the GPU only over the CC path.
- Never write plaintext weights to host-visible storage — use memory, or dm-crypt with a key held inside the TEE.
- Put weight and tokenizer digests in the release manifest so clients know *which* model answered.
- Be honest about the limit: weights are plaintext in CVM and GPU memory, so physical and side-channel attacks (§2) still apply, and **model extraction through the API is out of TEE scope** entirely.

### Logging without leaking prompts

- **Allow-list, not deny-list:** log only enumerated fields — status codes, bucketed latencies, model version, token counts if necessary. No request bodies, token text, embeddings, retrieved documents or tool arguments.
- **Disable core dumps and verbose GPU error dumps** in the measured image; they contain prompts.
- **Watch cardinality and joins:** precise per-request token counts with timestamps can re-identify content when joined with relay logs. Aggregate, coarsen, or add calibrated noise.
- **The logging code is attested code** — reviewers should be able to read the exporter configuration in the published source and confirm nothing else leaves.
- **Abuse monitoring:** if classifiers run inside the TEE, publish what they flag and what (if anything) leaves the boundary. An undisclosed exception is the most common way a confidential design quietly stops being one.

### Stateless design

- No persistent storage of prompts or outputs; conversation history, if any, is kept by the client and re-sent.
- **KV and prefix caches** are per-request state: isolate per user or tenant, or disable cross-user sharing (§2).
- Zero buffers after each request where the runtime allows; restart nodes on a schedule; generate ephemeral keys per boot.
- No SSH, no shell, no remote-exec, no debug or profiling endpoints in production images; remote management limited to a measured, narrow API.
- **Non-targetability:** the routing layer outside the TEE should not be able to steer a chosen user to a chosen node. Prefer client-side choice among attested nodes, or routing that cannot see identity (OHTTP plus anonymous tokens).

---

## 11. Updates, rotation and incident response

- **Release flow:** reproducible build → sign → publish manifest to the transparency log → update reference values in the KMS policy → staged rollout. Clients accept only logged releases; retire old releases by removing them from the accepted set and giving reference values a validity period.
- **TCB recovery:** when AMD, Intel or NVIDIA publish a firmware or microcode fix with a TCB or security-version bump, raise the minimum TCB in client and KMS policy after the grace period. Old-TCB reports remain *cryptographically* valid (the SNP VCEK is per-TCB), so only policy rejects them.
- **Key rotation:** rotate OHTTP/HPKE key configurations on a fixed schedule with key identifiers; generate TLS keys per boot; rotate weight-encryption keys with re-encryption; version KMS policies.
- **Incident triggers:** a vendor security bulletin, a new side-channel or physical-attack paper, a monitor seeing an unexpected log entry, a spike in attestation failures, or anomalous key-release events.
- **Response:** freeze rollouts; raise minimum TCB or revoke affected measurements; **assume every key released to an affected TCB or measurement is compromised** and rotate it; drain and re-provision nodes; publish a disclosure.
- **Forensics by design:** you deliberately have no prompt logs. Plan investigations around release manifests, the transparency log, KMS release audit records and attestation-failure telemetry — and say so in your incident plan.

---

## 12. Reference architecture

```
  Client app (open source, verifies)                 Transparency log  <-- witnesses cosign checkpoints
    | 1. fetch key config + evidence bundle  <------ release manifests: image, measurements, weight digests
    | 2. verify chain, TCB, debug, measurements,           ^
    |    inclusion + consistency, nonce, key binding       | published by reproducible build pipeline
    | 3. HPKE-encapsulate request (Binary HTTP)
    v
  OHTTP relay  (organization A)          sees: client IP, timing, sizes      not: content
    v
  Cloud load balancer / router           sees: ciphertext, sizes, timing    not: content, client IP
    v
  Attested gateway  (CVM, organization B)  HPKE private key released by KMS on attestation
    | 4. decapsulate, check Privacy Pass token, pick node, re-encrypt to node's attested key
    v
  Confidential GPU node(s):  CVM (SEV-SNP or TDX)  +  GPU in CC mode (SPDM session, encrypted bounce buffers)
    | 5. weights decrypted inside with key from KMS; inference; padded streaming response
    v
  response encapsulated to the client's response key, back through relay

  Key broker / KMS  -- releases keys only to evidence matching policy (measurement + TCB + debug off + GPU CC + fresh)
  Verifier          -- client-side library, or a named third-party service (then it is in the trusted set)
```

| Component | Sees plaintext prompt? | Sees client identity? | Trusted for |
|---|---|---|---|
| Client | Yes | Yes | Verifying correctly |
| OHTTP relay | No | IP address | Not colluding with the gateway operator |
| Cloud network and hosts | No | No (relay IP only) | Availability |
| Attested gateway | Yes, inside the TEE | No | Running the published, logged code |
| GPU node | Yes, inside the TEE | No | Running the published, logged code |
| KMS / key broker | No | No | Enforcing the logged release policy |
| Hardware vendors | No (absent compromise) | No | Roots of trust, firmware, endorsements |

Run `threat-modeling-playbook` STRIDE over each arrow: every arrow is a trust boundary, and the two "trusted for" columns are your assumption register.

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

## 14. Deployment checklist

**Threat model and claims**
- [ ] Written threat model naming every party in §2 and what each is trusted for; reviewed with `threat-modeling-playbook`.
- [ ] Public claims say exactly what is protected (prompts, outputs, weights, metadata) and from whom — no broader.

**Platform**
- [ ] Confidential VM on SEV-SNP or TDX at a current TCB; GPU in CC mode (not developer-tools); debug off everywhere.
- [ ] Minimal immutable guest: measured kernel or UKI, dm-verity root, no SSH, shell, package manager or debug endpoints.
- [ ] Guest kernel and drivers hardened for a malicious host; device and shared-memory interfaces reviewed.

**Attestation and binding**
- [ ] Client verifies CPU and GPU evidence, the CPU–GPU binding, freshness and key binding; fails closed.
- [ ] Minimum TCB and accepted TDX statuses defined in policy; host-controlled fields pinned or ignored.
- [ ] TLS or HPKE terminated inside the TEE; no plaintext hop outside it.

**Transparency and supply chain**
- [ ] Reproducible builds; SLSA provenance; signed release manifests including model and tokenizer digests.
- [ ] Manifests in an append-only log with witnesses; clients check inclusion and consistency; monitors running.
- [ ] Source, measurement calculators and a research environment published for independent audit.

**Keys and data**
- [ ] All secrets released by attestation-gated KMS; policy under multi-party control; changes logged.
- [ ] Weights encrypted at rest, decrypted only in the TEE; never on host-visible disk.
- [ ] Logging allow-list; core dumps off; metrics coarsened; abuse-monitoring behaviour published.
- [ ] Stateless request handling; per-user or per-tenant KV and prefix caches.

**Privacy of identity**
- [ ] OHTTP through an independently operated relay; consistent key configuration for all clients.
- [ ] Anonymous tokens for authorization; no identifiers inside encapsulated requests.
- [ ] Response padding and token batching against length and timing side channels.

**Operations**
- [ ] TCB-recovery runbook; key-rotation schedule; incident plan that works without prompt logs.

---

## 15. Common failure modes

1. **Attesting to nobody** — the server produces evidence but no client checks it, or the client logs a failure and continues.
2. **Unbound evidence** — the report carries no key or nonce, so a relay attack goes undetected.
3. **TLS terminated outside the TEE** at a cloud load balancer or API gateway.
4. **Launch-only measurement** — firmware measured, but the root filesystem, container image or weights loaded afterwards are not chained.
5. **Accepting any valid TCB** — no minimum version, so a patched-but-not-enforced vulnerability stays exploitable.
6. **Debug or developer modes in production** on the CPU or GPU.
7. **CPU attested, GPU not** — or both attested but not bound to each other.
8. **Opaque PCR comparisons** without event-log replay, so nobody knows what was actually measured.
9. **Unpublished or irreproducible images** — attestation pins a binary nobody outside can inspect.
10. **Transparency without consistency checks or witnesses**, leaving split-view equivocation open.
11. **Prompts in logs, traces, crash dumps or error reports** emitted by the attested code itself.
12. **Identity leaked inside OHTTP** — account tokens or device identifiers in the encapsulated request — or relay and gateway run by the same organization.
13. **Per-client OHTTP key configurations** that let the gateway tag users.
14. **Cross-user prefix or KV caches** creating timing side channels.
15. **Unpadded token streaming** leaking response lengths.
16. **KMS policy editable by one administrator** with no log, silently widening key release.
17. **Treating a third-party verifier as neutral** without listing it in the trusted set.
18. **Over-claiming** — "even we cannot see your data" while abuse monitoring, telemetry or support tooling quietly exports content.

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
