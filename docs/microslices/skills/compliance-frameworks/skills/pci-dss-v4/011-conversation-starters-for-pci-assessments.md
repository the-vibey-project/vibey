---
id: skill-conversation-starters-for-pci-assessments-36f48359f8
purpose: conversation starters for pci assessments
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/pci-dss-v4/SKILL.md
requires: ["skill-common-pci-dss-gaps-and-remediation-675dfd7df5"]
links: []
---

## Conversation Starters for PCI Assessments

When a user needs PCI help, ask:

1. **"Are you a merchant or service provider, and what is your annual card transaction volume?"**
   - Determines merchant level and validation requirements

2. **"How do you accept card payments — e-commerce, in-person terminals, phone/mail order?"**
   - Critical for SAQ selection

3. **"Do your web servers or payment pages host any of the payment form code, or is the entire payment UI hosted by your processor?"**
   - SAQ-A vs SAQ-A-EP determination

4. **"Have you identified your complete cardholder data environment and confirmed network segmentation?"**
   - Scope definition is the foundation of any assessment

5. **"Are there any payment page scripts (analytics, chat, tracking) that load in the browser on your payment page?"**
   - Triggers Req 6.4.3 / 11.6.1 conversation for v4.0 compliance
