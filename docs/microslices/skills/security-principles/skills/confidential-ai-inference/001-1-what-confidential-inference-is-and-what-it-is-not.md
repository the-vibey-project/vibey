---
id: skill-1-what-confidential-inference-is-and-what-it-is-not-eaa6c32a35
purpose: 1 what confidential inference is and what it is not
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: []
links: ["skill-2-threat-model-parties-assets-and-the-trust-you-cannot-remove-41c68db807"]
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
