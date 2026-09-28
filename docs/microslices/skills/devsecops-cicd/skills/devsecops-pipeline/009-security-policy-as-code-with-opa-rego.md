---
id: skill-security-policy-as-code-with-opa-rego-d02d9ec443
purpose: security policy as code with opa rego
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-reusable-security-workflow-pattern-66034e170e"]
links: ["skill-dependency-management-dependabot-snyk-renovate-7a4b1f604f"]
---

## Security Policy as Code with OPA/Rego

Enforce security policies across the stack using OPA with Conftest:

```rego
# policy/kubernetes.rego
package kubernetes.security

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.securityContext.readOnlyRootFilesystem
  msg := sprintf("Container '%s' must have readOnlyRootFilesystem: true", [container.name])
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not container.resources.limits.memory
  msg := sprintf("Container '%s' must have memory limits set", [container.name])
}

deny[msg] {
  input.kind == "Deployment"
  input.spec.template.spec.containers[_].image
  endswith(input.spec.template.spec.containers[_].image, ":latest")
  msg := "Images must not use :latest tag — pin by digest or semver"
}
```

Run in CI:
```yaml
- name: Policy check with Conftest
  run: |
    helm template ./charts/myapp | conftest test - \
      --policy policy/ \
      --namespace kubernetes.security
```

---
