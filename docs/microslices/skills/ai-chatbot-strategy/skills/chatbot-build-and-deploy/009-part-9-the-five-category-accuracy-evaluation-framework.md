---
id: skill-part-9-the-five-category-accuracy-evaluation-framework-1374ec35bb
purpose: part 9 the five category accuracy evaluation framework
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/chatbot-build-and-deploy/SKILL.md
requires: ["skill-part-8-data-privacy-and-security-architecture-632bc63def"]
links: ["skill-part-10-organizational-readiness-0e3b24512c"]
---

## Part 9: The Five-Category Accuracy Evaluation Framework

Most organizations that deploy AI chatbots cannot tell you their chatbot's accuracy rate. They know interaction volume and support ticket reduction. They do not have a measurement framework for whether the chatbot is giving correct, relevant, on-brand answers. This is the equivalent of running a customer service team with no quality assurance process.

Five categories together provide a complete picture. No single metric tells the whole story. The combination does.

### Category 1: Accuracy (Comprehension and Correctness)

| Metric | What It Measures |
|---|---|
| Intent Recognition Accuracy | Did the bot understand what the user wanted to do? |
| Entity Extraction Accuracy | Did it catch all key details (names, dates, places)? |
| Response Correctness | Did it answer the question factually and in context? |
| Non-Response Rate | How often did it fail to answer or get confused? |

Calculated using precision, recall, and F1 scores—measures from classification tasks that quantify correctness at scale. Accuracy metrics must be measured against real user conversations, not just test scenarios. The gap between lab performance and real-world performance is routinely significant.

### Category 2: User Satisfaction (Quality of Experience)

| Metric | What It Measures |
|---|---|
| CSAT (Customer Satisfaction Score) | Post-interaction survey, typically 1–5 scale |
| NPS (Net Promoter Score) | Would users recommend this chatbot to others? |
| Task Completion Rate | Did the user finish what they came to do? |
| User Feedback | Qualitative patterns in what users actually say |
| Retention Rate | Do users return and use it again? |

Task completion rate and retention correlate directly with whether a chatbot is generating measurable business value. Satisfaction data surfaces issues automated metrics miss: tone mismatches, confusing escalation flows, failure to acknowledge frustration.

### Category 3: Response Speed and Scalability

| Response Time | User Experience | Business Impact |
|---|---|---|
| < 1 second | Excellent | High conversion rates |
| 1–2 seconds | Good | Normal conversion rates |
| 2–4 seconds | Acceptable | Some user drop-off |
| > 4 seconds | Poor | Significant drop-off |

Users begin to drop off when response times exceed 2–4 seconds, particularly in e-commerce and technical support contexts. Speed should not come at the cost of accuracy—a fast wrong answer is worse than a slightly slower correct one.

### Category 4: RAG-Specific Retrieval Quality

For RAG deployments, standard accuracy metrics are necessary but insufficient. The retrieval engine and generation layer can each fail independently.

| Metric | What It Measures |
|---|---|
| Context Precision@k | Are the top-k retrieved documents relevant? |
| Context Recall@k | Are all relevant documents included in the retrieved set? |
| Mean Reciprocal Rank (MRR) | How early does the right answer appear in retrieved results? |
| Mean Average Precision (MAP) | Overall quality across all retrieved results? |
| Faithfulness | Does the generated answer stay within the bounds of source material—or does it hallucinate content not present in retrieved documents? |
| Answer Relevance and Similarity | Does the response actually answer the question in a way a domain expert would confirm? |

**Faithfulness is the primary instrument for catching hallucination in RAG systems.** In regulated industries like healthcare and finance, an unfaithful answer is not merely a quality problem—it is a liability.

### Category 5: Multi-Turn Conversation Quality

For chatbots handling longer or more complex conversations:

| Metric | What It Measures |
|---|---|
| Role Adherence | Does it stay in character consistently (support agent, not generic AI)? |
| Conversation Relevance | Do responses remain on-topic across several turns? |
| Knowledge Retention | Does it remember and correctly reference earlier parts of the conversation? |
| Conversation Completeness | Does it help users fully achieve their goal, or leave the interaction unresolved? |

A bot that forgets a user's account type three messages into the conversation is not operationally useful regardless of its accuracy on individual responses.

### Evaluation Methodology

The best evaluation methodology combines:
- **Automated metrics** (consistent, scalable, catches quantifiable failures)
- **Periodic human evaluation** (catches nuanced failures automated systems routinely miss)

Neither alone is sufficient. Four test types matter during development:

1. **Functional testing**: Correct intent understanding, right information retrieved, appropriate responses across a defined query set
2. **Performance testing**: System handles anticipated load—concurrent users, peak traffic—without degrading response time
3. **User acceptance testing (UAT)**: Real users (not developers) surface phrasing variations and conversational patterns test suites missed
4. **Semantic validation**: Checks not just that an answer was returned, but that the answer is factually correct and tonally consistent with the brand. Semantic validators function as automated proofreaders comparing outputs against a ground-truth answer set. **Skipping semantic validation is the most common testing gap in first-time deployments**—and the gap most likely to produce visible customer-facing failures.

---
