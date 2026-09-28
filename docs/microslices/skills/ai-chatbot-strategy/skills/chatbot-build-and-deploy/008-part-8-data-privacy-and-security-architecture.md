---
id: skill-part-8-data-privacy-and-security-architecture-632bc63def
purpose: part 8 data privacy and security architecture
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/chatbot-build-and-deploy/SKILL.md
requires: ["skill-part-7-the-three-layer-guardrail-framework-7e9be6e42f"]
links: ["skill-part-9-the-five-category-accuracy-evaluation-framework-1374ec35bb"]
---

## Part 8: Data Privacy and Security Architecture

### The Fundamental Principle: Data Minimization

Data minimization is the most underrated security control available. A chatbot that stores only a customer's email address and order number has a fundamentally smaller exposure surface than one that stores full contact records, purchase history, and session transcripts. In the event of a breach, the blast radius scales with what was collected.

In 2023, Samsung engineers used ChatGPT to debug proprietary source code. The code—and its trade secrets—was transmitted to OpenAI's servers and incorporated into training data. The incident was not a data breach in the traditional sense. It was a routine employee action that became a permanent disclosure. Most security frameworks are not designed to catch this failure mode.

**Responsible data collection practices**:
- Consent prompts before data is gathered
- Anonymization of any data used for training or analytics
- Privacy policies specifying what is collected, why it is retained, and how long it is kept
- Deletion request fulfillment capability

### Encryption: The Baseline Requirement

- **Data in transit**: HTTPS or TLS for all traffic between the chatbot and users
- **Data at rest**: AES-256 encryption for vector databases, relational stores, and document repositories; implemented by default in AWS Bedrock and Pinecone
- **Tokenization**: For particularly sensitive data fields (payment card numbers, government identifiers)—replaces the actual value with a non-reversible token useless if intercepted
- **Key rotation**: Regular encryption key rotation limits exposure window if a key is compromised

### Compliance by Regulatory Framework

| Framework | Scope | Key Requirements | Penalties |
|---|---|---|---|
| GDPR | EU resident data (applies extraterritorially) | Informed consent, documented processing purposes, deletion requests, DPIAs for high-risk activities | Up to €20M or 4% of global annual turnover |
| CCPA | California residents | Rights to access, delete, opt out of sale of personal data | Varies; enforced by California AG |
| HIPAA | US healthcare (protected health information) | Encrypt all PHI, strict access controls, detailed audit logs | Civil and criminal penalties |
| PCI DSS | Payment card data | Tokenization, regular security audits | Card network fines, loss of processing privileges |
| PSD2 | EU financial data | Specific financial data handling requirements | EU member state enforcement |

**Enforcement is real**: In 2022, Meta was fined €405 million by the Irish Data Protection Commission for GDPR violations related to processing children's data. Chatbot deployments that handle EU resident data are fully within scope.

**GDPR risk specific to chatbots**: Many deployments log every conversation, route data through external AI APIs without user disclosure, and retain sensitive information beyond its operational purpose without explicit consent mechanisms. Each of these practices is a GDPR enforcement candidate.

### Internal Access Controls

**Role-Based Access Control (RBAC)**: Determines which documents, data sources, and system capabilities each user role can access. Critically, RBAC must be enforced at the **retrieval layer**, not just at the application layer—the vector database itself must only return documents the requesting user is authorized to see.

**Multi-Factor Authentication (MFA)**: Verifies identity of anyone accessing sensitive chatbot functionality.

**Single Sign-On (SSO)**: Integrates chatbot authentication with the organization's existing identity provider, ensuring access permissions mirror the employee's role in the organizational directory.

**Audit logs**: Record every interaction, every document retrieved, and every query issued to connected systems. Creates the evidentiary record required for compliance audits and incident investigation.

**Data masking**: Limits what is displayed in responses even when the underlying data is available to the system.

### RAG-Specific Security: Document Sensitivity Tagging

RAG chatbots retrieve documents dynamically—the scope of what a user might access is determined by the entire knowledge base unless retrieval is explicitly scoped.

**Document sensitivity tagging** classifies each document as public, internal, or confidential. The retrieval layer filters against the requesting user's clearance level before returning any results:
- External user → public-tagged documents only
- Authenticated employee → internal documents appropriate to role
- Confidential documents → excluded unless explicitly authorized

This architecture limits blast radius. Even if an attacker obtains valid credentials, they receive only what that credential level authorizes—not the full knowledge base. This is the step most organizations skip, and the one that most directly prevents knowledge base exploitation.

### Four Security Risks Requiring Specific Mitigations

1. **Prompt injection**: Structured user inputs designed to cause the chatbot to bypass operating instructions. Requires input validation at every entry point. Pattern-matching on injection signatures (requests to ignore instructions, reveal system configuration, access out-of-scope documents) before processing by the retrieval pipeline. Anomaly detection on query frequency and topic clustering adds a second detection layer.

2. **Adversarial inputs**: Small perturbations designed to confuse classification layers. Requires adversarial training during development.

3. **Third-party platform risk**: Vendor evaluation against SOC 2 compliance standards and explicit data processing agreements.

4. **RAG knowledge base poisoning**: Injection of incorrect or misleading documents into the retrieval corpus. Requires source validation and access controls on the knowledge base itself.

**Technical security checklist**:
- HTTPS/TLS for all traffic
- AES-256 at-rest encryption
- OAuth 2.0 for API authentication
- Rate limiting on all API endpoints
- Regular penetration testing and vulnerability scanning
- Guardrail implementation (input and output filters)
- Clean, curated, access-controlled knowledge bases with sensitivity tagging

---
