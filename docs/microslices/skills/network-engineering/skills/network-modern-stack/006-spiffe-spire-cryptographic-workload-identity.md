---
id: skill-spiffe-spire-cryptographic-workload-identity-5df13ab509
purpose: spiffe spire cryptographic workload identity
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-aks-networking-the-complete-decision-guide-2067eddce0"]
links: ["skill-zero-trust-networking-in-production-dbd7f416f3"]
---

## SPIFFE/SPIRE: cryptographic workload identity

**IP addresses are not identity** in dynamic environments. Pod IPs change with every restart. VMs are ephemeral. IP-based ACLs become stale within minutes.

**SPIFFE** (CNCF graduated) solves this with a universal identity format: `spiffe://trust-domain/workload-identifier` (e.g., `spiffe://acme.com/ns/payments/sa/payment-processor`).

Identity is encoded in a cryptographically verifiable document called an **SVID**:
- **X.509 SVID** (preferred): used for mTLS between services
- **JWT SVID**: used when mTLS is not possible

SVIDs are short-lived (typically 1 hour), automatically rotated, and issued without static secrets.

**SPIRE architecture**:
- **SPIRE Server** (StatefulSet): central authority, signs SVIDs, manages the trust domain
- **SPIRE Agents** (DaemonSet on every node): expose the Workload API via Unix domain socket, perform attestation

**Two-phase attestation**:
1. Agent proves node identity (using AWS Instance Identity Documents, Kubernetes service account tokens, GCP Identity Tokens)
2. When a workload requests identity, Agent inspects kernel metadata (cgroups, PID, container properties) and matches against registration entries mapping workload properties to SPIFFE IDs

In AKS, **Microsoft Entra Workload Identity** provides federated identity credentials. The cluster exposes an OIDC issuer endpoint; a trust relationship links Kubernetes ServiceAccounts to Entra managed identities; pods receive projected tokens exchanged for Entra tokens to access Azure resources.
