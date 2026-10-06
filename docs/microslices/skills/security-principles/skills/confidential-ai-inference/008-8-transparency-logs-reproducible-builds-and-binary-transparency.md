---
id: skill-8-transparency-logs-reproducible-builds-and-binary-transparency-dadaab3f53
purpose: 8 transparency logs reproducible builds and binary transparency
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-7-oblivious-http-and-relays-separating-who-you-are-from-what-you-ask-db90ee5e2d"]
links: ["skill-9-verifiable-inference-beyond-tees-6972b55a95"]
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
