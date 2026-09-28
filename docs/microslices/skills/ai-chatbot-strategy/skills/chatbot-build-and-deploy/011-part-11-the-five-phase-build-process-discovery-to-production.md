---
id: skill-part-11-the-five-phase-build-process-discovery-to-production-6398ff12b8
purpose: part 11 the five phase build process discovery to production
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/chatbot-build-and-deploy/SKILL.md
requires: ["skill-part-10-organizational-readiness-0e3b24512c"]
links: ["skill-part-12-industry-case-studies-and-benchmarks-dced279a5e"]
---

## Part 11: The Five-Phase Build Process (Discovery to Production)

The five-phase process is what separates a chatbot that works in production from one that worked in a demo. The engagement is not primarily about software delivery—it is about getting to a system that works reliably for real users.

### Phase 1: Discovery — Clarify the Why Before the How

You cannot build the right chatbot without knowing what it is for. Discovery runs structured workshops or interviews with key stakeholders to establish:

- What will the chatbot specifically do? (Not "improve the customer experience"—the measurable function it will perform)
- What existing systems must it connect to—CRM, ERP, legal database, product catalog?
- Who are the users, and what are their actual behaviors and frustrations?
- What compliance and data handling requirements constrain the architecture?

**Discovery deliverable**: A project brief with goals, user needs, technical requirements, and scope. This document makes every subsequent phase coherent.

A critical discovery finding can reshape the entire project before budget is committed: a law firm seeking a client intake bot may discover in discovery that client data is stored in an outdated system with no API exposure. That finding does not end the project—it reshapes the scope before resources are committed rather than after.

### Phase 2: Planning and Design — Blueprint Before You Build

Once goals are clear, the planning phase:
- Defines the technical stack
- Determines whether RAG is appropriate for the knowledge retrieval requirements
- Maps conversation design before any code is written

**Conversation design is underestimated** by organizations that think of chatbots as primarily engineering problems. How does the chatbot handle a user who asks about a refund in informal language? What happens when a user says "talk to a human"? What does the handoff path look like when the chatbot reaches the edge of its knowledge? These flows require deliberate design—not just adequate technology.

**Planning deliverable**: Tech stack specification, conversation flow diagrams, UI mockups, and project timeline. This document prevents scope creep from becoming scope explosion.

### Phase 3: Development — Where the Chatbot Comes to Life

The development phase builds:
- Backend intent recognition and retrieval logic
- Frontend interface (website widget, Slack integration, internal portal)
- System integrations with existing tools
- Security architecture

For regulated industries, **security is not a feature added at the end—it is a design requirement that shapes every architectural decision**: encryption in transit and at rest, authentication controls, audit logging, data residency, and API security.

A self-hosted RAG architecture built on Mistral-7B with FAISS vector search achieves complete data privacy with zero external dependencies using Docker containerization, Grafana/Prometheus monitoring, and an OpenAI-compatible API layer. This architecture must be designed from day one for the privacy requirement—not retrofitted to it.

**Development deliverable**: A working prototype with real integrations and security built in—not a demo environment that approximates production.

### Phase 4: Testing — Try to Break It Before Your Users Do

Testing covers four dimensions:

1. **Functional QA**: Does the chatbot understand the questions it is supposed to understand?
2. **Performance testing**: Can it handle peak query volumes without degrading?
3. **User acceptance testing**: Do real users—not developers—find it helpful? Do they phrase things in unanticipated ways?
4. **Security testing**: Does it resist prompt injection, data leakage, and unauthorized access?

Simulating real user behavior—diverse phrasing, multi-turn conversations, edge cases, deliberately misleading inputs—in a staging environment before launch surfaces failure modes that matter. Testing with adversarial inputs is more productive at this stage than testing with clean, expected queries.

Most chatbot failures in production originate in data quality and retrieval architecture, not in the generative model. The testing framework established at the planning phase—not appended after development—is what makes production-ready delivery achievable.

**Testing deliverable**: A production-ready system with complete documentation—not a list of known issues to be addressed after launch.

### Phase 5: Deployment and Ongoing Support — Launch and Keep It Alive

Deployment puts the chatbot where users encounter it. Post-launch, the engagement continues:
- Monitoring accuracy and user satisfaction
- Updating the knowledge base as the business evolves
- Addressing edge cases that only appear at production volume
- Scaling infrastructure as usage grows
- Supporting compliance audits when required

**A chatbot that is not actively maintained degrades.** The business it represents changes—products evolve, policies update, new questions emerge—and a knowledge base accurate at launch becomes progressively less accurate without deliberate upkeep. Continuously updated RAG systems show measurably better first-contact resolution than static deployments, a gap that compounds over time as the knowledge base diverges from operational reality.

**Deployment deliverable**: Monitoring dashboards and a maintenance plan—not just a live URL.

---
