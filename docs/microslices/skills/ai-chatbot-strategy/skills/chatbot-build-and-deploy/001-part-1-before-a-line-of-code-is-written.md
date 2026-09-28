---
id: skill-part-1-before-a-line-of-code-is-written-a4cdeaa038
purpose: part 1 before a line of code is written
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/chatbot-build-and-deploy/SKILL.md
requires: []
links: ["skill-part-2-the-four-functional-layers-f8328be3f9"]
---

## Part 1: Before a Line of Code Is Written

### Defining Purpose (Step 1)

A chatbot without a defined purpose is a demo. The first decision is what the chatbot is specifically responsible for handling—and what it is explicitly not responsible for.

Use cases drive everything else:
- **Customer service**: Reduce wait times by X%, deflect Y% of tier-1 support volume
- **Lead generation**: Qualify Z leads per month at a lower cost-per-lead than current channels
- **Internal automation**: Reduce HR query volume by W% in the first two quarters
- **Sales enablement**: Handle 24/7 qualification so leads contacted within 5 minutes are 9x more likely to convert than those contacted after 30 minutes (documented finding on lead response timing)
- **Employee onboarding**: Route new hires to accurate answers without burdening HR staff

**The SMART framework** applies directly: Specific, Measurable, Aspirational, Realistic, Time-bound. A law firm that sets a goal of automating 70% of client intake by Q4 has a deployment target, a measurement baseline, and an accountability structure. A firm that sets a goal of "improving the client experience with AI" has none of those things.

McKinsey found that organizations with specific, measurable AI goals achieve **20% higher ROI** than those that deploy to explore capabilities. 75% of organizations reporting significant cost or revenue improvements from AI had defined specific business goals before deployment.

The scope decision also determines human handoff design. A customer service chatbot needs a clear escalation protocol for interaction types it cannot handle. A sales qualification chatbot needs to know at what point in the conversation it should route to a human representative. Defining these boundaries at the outset is not a detail—it is foundational to the user experience the chatbot will deliver.

### Choosing Deployment Channels (Step 2)

Where the chatbot lives determines who can reach it and how. Each channel has different API requirements, different user expectations about response time and format, and different integration complexity.

| Channel | Best For | Key Consideration |
|---|---|---|
| Website widget | General customer support, lead capture | Lowest barrier to entry; direct CRM integration |
| WhatsApp | Consumer-facing, high-volume markets | 76% open rates; requires WhatsApp Business API |
| Slack / Microsoft Teams | Internal employee tools | SSO integration simplifies auth; users already present |
| Mobile app (embedded) | High-engagement consumer products | Native UX; push notification capability |
| Internal portal | HR, legal, finance self-service | RBAC required; document sensitivity tagging critical |
| Facebook Messenger | Travel, hospitality, retail | Marriott handles room service and rebooking here |

**KLM BlueBot** deployed across nine channels simultaneously, handling 1.7 million messages per week within 18 months. Multi-channel deployment is achievable but requires additional abstraction in the architecture to ensure consistent behavior across surfaces.

---
