---
id: skill-scoping-system-boundaries-for-cui-149f73e955
purpose: scoping system boundaries for cui
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/cmmc-cui/SKILL.md
requires: ["skill-cybersecurity-incident-disclosure-framework-674b15fdab"]
links: ["skill-assessment-types-in-detail-fa308c70e4"]
---

## Scoping System Boundaries for CUI

### What to Include in Your CUI Enclave
All systems, devices, and cloud services that:
- Store CUI (databases, file servers, cloud storage, email with CUI)
- Process CUI (workstations where CUI is accessed, servers, applications)
- Transmit CUI (email servers, VPN endpoints, collaboration tools with CUI)
- Provide security functions to the above (domain controllers, PAM, SIEM, patch management)

### Scope Reduction Strategies
**CUI Segregation:** Create a dedicated CUI environment (physical or logical) that is isolated from general corporate systems. Only systems in the CUI enclave need to meet 800-171.

**Cloud Enclave:** Use a FedRAMP Authorized cloud service (e.g., Microsoft 365 GCC High, Azure Government) for CUI processing. The cloud provider handles many controls; contractor inherits them.

**Enclave Documentation:**
- Network diagram showing CUI boundary
- Data flow diagram showing CUI movement
- List of all in-scope system components (hardware, software, cloud services)
- Interconnection agreements for any external systems that touch CUI

---
