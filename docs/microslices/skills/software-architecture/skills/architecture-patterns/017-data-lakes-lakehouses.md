---
id: skill-data-lakes-lakehouses-0e973d9cf5
purpose: data lakes lakehouses
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-vector-search-3bc6f56154"]
links: ["skill-azure-api-management-apim-8ef604f319"]
---

## Data Lakes & Lakehouses
- **ADLS Gen2**: hierarchical namespace on Blob
- **Microsoft Fabric OneLake**: universal tenant-wide logical lake (built on ADLS Gen2); all tabular data in **Delta Parquet**; zero-copy **Shortcuts** to S3/GCS/ADLS; **Mirroring** for zero-ETL from Cosmos/SQL/PostgreSQL/Snowflake (GA Nov 15, 2023)
- **Medallion architecture**: Bronze (raw) → Silver (cleaned) → Gold (business-ready)
- **Data Mesh on Azure**: Fabric workspaces (domains) governed centrally via **Microsoft Purview** (catalog, lineage, sensitivity labels)

---

# PART 4: SECRETS MANAGEMENT

**Never store secrets in config files, baked images, or source control.**

**Azure Key Vault (Standard = software-protected; Premium = HSM-backed)**
- **Key Vault references** in App Service/Functions: `@Microsoft.KeyVault(...)`
- **AKS**: Secrets Store CSI Driver + AKV provider mounts secrets as files or syncs to K8s Secrets; combine with **Workload Identity** for zero-secret-in-config
- Key Vault references resolve at app start and on a refresh interval — rotating a secret doesn't instantly propagate unless you handle refresh
- Cache high-RPS secret reads to avoid throttling

**Azure Managed HSM**: dedicated, FIPS 140-2 Level 3, single-tenant.

**HashiCorp Vault on Azure**: beats Key Vault for true dynamic secrets (short-lived, on-demand), multi-cloud, or Vault Agent sidecar injection.

**Injection patterns:** Startup pull, sidecar injection (Vault Agent / Dapr), or **CSI driver mount** (AKS preferred).

---

# PART 5: API GATEWAY & EDGE
