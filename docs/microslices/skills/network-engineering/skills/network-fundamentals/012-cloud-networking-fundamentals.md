---
id: skill-cloud-networking-fundamentals-95561870b7
purpose: cloud networking fundamentals
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-data-center-networking-spine-leaf-0f660a8c73"]
links: ["skill-performance-metrics-b09b968337"]
---

## Cloud networking fundamentals

**VNets (Azure) / VPCs (AWS/GCP)**: isolated virtual networks in the cloud. Subnets divide the address space. Route tables control traffic flow.

**VNet/VPC peering**: connects two virtual networks at the cloud backbone layer. Traffic stays on Microsoft's/Amazon's network, not the public Internet.

**Private endpoints**: expose Azure PaaS services (Storage, SQL, Key Vault) with a private IP inside your VNet, eliminating public Internet exposure.

**ExpressRoute (Azure) / Direct Connect (AWS)**: dedicated private connectivity between your on-premises network and the cloud. Bypass the public Internet for reliability and predictable performance.
