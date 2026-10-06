---
id: skill-2-threat-model-parties-assets-and-the-trust-you-cannot-remove-41c68db807
purpose: 2 threat model parties assets and the trust you cannot remove
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-1-what-confidential-inference-is-and-what-it-is-not-eaa6c32a35"]
links: ["skill-3-trusted-execution-cpu-confidential-vms-and-enclaves-5ff5798053"]
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
