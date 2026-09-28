---
id: skill-the-five-phase-discovery-to-deployment-process-b5a12cc265
purpose: the five phase discovery to deployment process
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/chatbot-business-value/SKILL.md
requires: ["skill-defining-organizational-goals-the-smart-framework-applied-703dd41cf0"]
links: ["skill-handling-limited-data-what-to-do-when-you-cannot-build-a-comprehensive-knowledge-base-f8181e7122"]
---

## The Five-Phase Discovery-to-Deployment Process

The difference between a chatbot that runs reliably in production and one that creates new problems at the same rate it solves old ones is not the technology. It is the process.

### Phase 1: Discovery — Clarify the Why Before You Touch the How

The discovery phase runs workshops or structured interviews with key stakeholders to establish goals, constraints, and context. The four questions that must be answered:

1. What will the chatbot actually do? (Not "improve the customer experience" — the specific, measurable function it will perform.)
2. What existing systems must it connect to — CRM, ERP, legal database, product catalog?
3. Who are the users, and what are their actual behaviors and frustrations?
4. What are the compliance and data handling requirements that constrain the architecture?

**Deliverable:** A project brief with goals, user needs, technical requirements, and scope. This document is what makes every subsequent phase coherent — and what prevents scope creep from compounding after budget is committed.

**Why it matters:** A law firm that wants a client intake bot may discover in discovery that client data is stored in an outdated system with no API exposure. That finding does not end the project — it reshapes the scope before budget is committed rather than after.

### Phase 2: Planning and Design — Blueprint Before You Build

Once goals are clear, the planning phase defines the technical stack, determines whether RAG is appropriate for the knowledge retrieval requirements, and maps conversation design before any code is written.

Conversation design is underestimated by organizations that think of chatbots as primarily engineering problems. The questions that require deliberate design:
- How does the chatbot handle a user who asks about a refund in informal language?
- What happens when a user says "talk to a human"?
- What does the handoff path look like when the chatbot reaches the edge of its knowledge?

**Deliverable:** Tech stack specification, conversation flow diagrams, UI mockups, and project timeline. This document prevents scope creep from becoming scope explosion.

### Phase 3: Development — Where the Chatbot Comes to Life

Development builds the backend intent recognition and retrieval logic, the frontend interface, system integrations with existing tools, and security architecture.

For regulated industries, security is not a feature added at the end — it is a design requirement that shapes every architectural decision: encryption in transit and at rest, authentication controls, audit logging, data residency, and API security.

**Deliverable:** A working prototype with real integrations and security built in — not a demo environment that approximates production.

### Phase 4: Testing — Try to Break It Before Your Users Do

Testing covers four dimensions:
- **Functional QA:** Does the chatbot understand the questions it is supposed to understand?
- **Performance testing:** Can it handle peak query volumes without degrading?
- **User acceptance testing:** Do real users — not developers — find it helpful?
- **Security testing:** Does it resist prompt injection, data leakage, and unauthorized access?

Semantic validation is a fifth test type that most vendors skip: the distinction between an accurate answer and a relevant one. A chatbot can produce factually correct output that fails to address the user's actual intent.

**Deliverable:** A production-ready system with complete documentation — not a list of known issues to be addressed after launch.

### Phase 5: Deployment and Ongoing Support — Launch and Keep It Alive

Post-launch, the engagement continues: monitoring accuracy and user satisfaction, updating the knowledge base as the business evolves, addressing edge cases that only appear at production volume, scaling infrastructure as usage grows, and supporting compliance audits when required.

**Deliverable:** Monitoring dashboards and a maintenance plan — not just a live URL.

**The most common failure mode:** Organizations that treat launch as completion. A chatbot that is not actively maintained degrades. The businesses that achieve the documented ROI results treat the deployment as a measurement-and-improvement cycle, not a one-time project.

---
