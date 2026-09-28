---
id: skill-aks-security-hardening-eccb2957dc
purpose: aks security hardening
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-bicep-azure-native-alternative-c0f0d41e6d"]
links: ["skill-node-pool-design-08e852584a"]
---

## AKS Security Hardening

### Pod Security Standards (Replace Deprecated PSPs)

Enforce the **Restricted** profile on all production namespaces:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp-prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.28
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

A Restricted-compliant pod security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

Migrate gradually: set `warn` and `audit` modes first, then switch to `enforce` after validating workloads.

### Network Policies — Default Deny

Apply a default deny-all NetworkPolicy to every namespace, then explicitly allow required communication:

```yaml
# 1. Default deny all ingress and egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

# 2. Allow DNS (always required)
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

With Cilium on AKS, leverage CiliumNetworkPolicy for L7 and FQDN-based filtering (Azure CNI Overlay + Cilium is the recommended stack for new clusters).

### Workload Identity Setup (Replaces Deprecated Pod Identity)

```bash
# Enable on cluster
az aks update \
  --resource-group myRG \
  --name myAKS \
  --enable-oidc-issuer \
  --enable-workload-identity

# Create user-assigned managed identity
az identity create \
  --name myapp-identity \
  --resource-group myRG

# Get OIDC issuer URL
OIDC_ISSUER=$(az aks show --resource-group myRG --name myAKS \
  --query "oidcIssuerProfile.issuerUrl" -o tsv)

# Create federated credential
az identity federated-credential create \
  --name myapp-federated \
  --identity-name myapp-identity \
  --resource-group myRG \
  --issuer "$OIDC_ISSUER" \
  --subject "system:serviceaccount:myapp:myapp-sa" \
  --audiences api://AzureADTokenExchange
```

Kubernetes service account annotation:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: myapp
  annotations:
    azure.workload.identity/client-id: "<managed-identity-client-id>"
```

Pod label to trigger token injection:
```yaml
spec:
  serviceAccountName: myapp-sa
  labels:
    azure.workload.identity/use: "true"
```

### OPA Gatekeeper / Azure Policy

Azure Policy for AKS enforces governance at admission time using built-in initiative including Deployment Safeguards. Key policies to enforce:

- Require resource limits on containers
- Disallow privileged containers
- Require non-root user
- Require readOnlyRootFilesystem
- Restrict allowed registries (only pull from ACR)
- Enforce image signing (via Ratify + cosign)

Enable via Terraform:
```hcl
resource "azurerm_kubernetes_cluster" "main" {
  # ...
  azure_policy_enabled = true
}
```

### Container Scanning — Trivy

Run Trivy in CI/CD pipeline to fail builds on CRITICAL/HIGH findings:

```yaml
- name: Scan container image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'myapp:${{ github.sha }}'
    format: 'sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'
    output: 'trivy-results.sarif'

- name: Upload Trivy scan results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-results.sarif'
  if: always()
```

Deploy Trivy Operator for continuous in-cluster scanning of running workloads.

### Private Cluster Configuration

Production AKS clusters should use API server VNet integration — control plane accessible only from private network:

```hcl
resource "azurerm_kubernetes_cluster" "main" {
  private_cluster_enabled             = true
  private_cluster_public_fqdn_enabled = false
  api_server_access_profile {
    vnet_integration_enabled = true
    subnet_id                = azurerm_subnet.apiserver.id
  }
}
```

For management access use Azure Bastion for SSH tunneling, or `az aks command invoke` to run kubectl without direct network access.

---
