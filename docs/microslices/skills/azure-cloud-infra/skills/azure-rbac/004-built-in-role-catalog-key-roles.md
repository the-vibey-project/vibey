---
id: skill-built-in-role-catalog-key-roles-1b7de826d2
purpose: built in role catalog key roles
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-scope-hierarchy-and-inheritance-fbbd4ac8ec"]
links: ["skill-role-definition-structure-c18b99e499"]
---

## Built-In Role Catalog: Key Roles

### Privileged roles
| Role | GUID | Key permissions |
|---|---|---|
| **Owner** | `8e3af657-a8ff-443c-a75c-2fe8c4bcb635` | `Actions: ["*"]` — full management + role assignment |
| **Contributor** | `b24988ac-6180-42a0-ab88-20f7382dd24c` | `Actions: ["*"]` minus authorization writes. Cannot assign roles. |
| **Reader** | `acdd72a7-3385-48ef-bd42-f606fba81ae7` | `Actions: ["*/read"]` — no data plane access |
| **User Access Administrator** | `18d7d88d-d35e-4fb5-a5c3-7773c20a72d9` | Manage RBAC only |
| **Role Based Access Control Administrator** | `f58310d9-a9f6-439a-9e8d-f62e7b41a168` | Narrower UAA alternative; supports ABAC conditions |

### Storage roles
| Role | Plane | Key capability |
|---|---|---|
| Storage Account Contributor | Control | Manage accounts; can retrieve keys |
| Storage Blob Data Owner | Data | Full blob CRUD + ACL owner (ADLS Gen2 super-user) |
| Storage Blob Data Contributor | Data | Read/write/delete blobs and containers |
| Storage Blob Data Reader | Data | Read and list blobs/containers |

### Key Vault roles
| Role | Plane | Scope |
|---|---|---|
| Key Vault Contributor | Control ONLY | Manage vault resource, NOT access secrets/keys |
| Key Vault Secrets User | Data | Read secret contents only |
| Key Vault Secrets Officer | Data | Full CRUD on secrets |
| Key Vault Administrator | Data | All data plane operations |

### AKS roles — two separate systems
**ARM-level (control plane for the AKS resource):**
| Role | GUID | Grants |
|---|---|---|
| AKS Cluster Admin Role | `0ab0b1a8-8aac-4efd-b8c2-3ee1fb270be8` | Retrieves admin kubeconfig with `cluster-admin` binding |
| AKS Cluster User Role | `4abbcc35-e782-43d8-92c5-2d3f1bd2253f` | Retrieves user kubeconfig (required for `az aks get-credentials`) |

**Kubernetes data plane (DataActions):**
| Role | Access level |
|---|---|
| AKS RBAC Cluster Admin | Super-user — all resources in all namespaces |
| AKS RBAC Admin | Admin within namespace |
| AKS RBAC Writer | Read/write most objects including Secrets |
| AKS RBAC Reader | Read-only; cannot view Secrets |

Scope Azure RBAC assignments to a specific Kubernetes namespace:
```bash
az role assignment create --role "AKS RBAC Writer" \
  --assignee <AAD-ENTITY-ID> \
  --scope "$AKS_ID/namespaces/my-namespace"
```

### Cosmos DB — data plane is its own RBAC system
Cosmos DB data plane RBAC is **not standard Azure RBAC**. Built-in data roles:
- `00000000-0000-0000-0000-000000000001` — Cosmos DB Built-in Data Reader
- `00000000-0000-0000-0000-000000000002` — Cosmos DB Built-in Data Contributor

Assign with `az cosmosdb sql role assignment create`. Not available in the Azure portal.

```bash
az cosmosdb sql role assignment create \
  --account-name myCosmosAccount --resource-group myRG \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --principal-id "<managed-identity-object-id>" --scope "/"
```

---
