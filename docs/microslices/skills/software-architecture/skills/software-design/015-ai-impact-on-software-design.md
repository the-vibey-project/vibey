---
id: skill-ai-impact-on-software-design-6285a65681
purpose: ai impact on software design
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-non-functional-design-b8a23c6331"]
links: ["skill-legacy-brownfield-design-0fcfd11cf1"]
---

## AI Impact on Software Design

### GitClear 2024 Findings (211 Million Changed Lines)
The most comprehensive empirical study on AI coding tools' effect on maintainability:
- **Duplicated code blocks rose eightfold during 2024**
- **Refactored ("moved") lines fell from 25% of changes in 2021 to under 10% in 2024**
- **Short-term churn** (code revised within two weeks) rose from 3.1% (2020) to 5.7% (2024)
- 2024 was the **first year copy-pasted lines exceeded moved lines**

### DORA 2024 and Harness 2025
- Increasing AI adoption **correlated with reduced delivery throughput and stability** despite higher perceived productivity
- Majority of developers spend **more time debugging AI-generated code** and more time resolving AI-generated security vulnerabilities

### The Design Implication
AI lowers the cost of **producing** artifacts. It raises the premium on the human disciplines — **refactoring, abstraction judgment, boundary enforcement** — that keep systems maintainable.

> "There has been more evidence every year that code duplication keeps growing." — Bill Harding, GitClear CEO

### Where AI Genuinely Helps
- Brainstorming architectural alternatives
- Generating boilerplate and C4/Structurizr diagrams from code
- Explaining legacy systems ("archaeology")
- Architecture knowledge management

### Where AI Fails
- Generates "plausible but incorrect designs" requiring human validation
- Must be validated via compilers, tests, simulation
- Partial satisfaction of architectural drivers — human oversight and iterative refinement are non-negotiable

### 2026 Context Engineering Shift
Thoughtworks Vol 33 Radar (Nov 2025): "Vibe coding practically disappeared," replaced by **context engineering** and spec-driven development (Amazon Kiro, GitHub Spec Kit). This is a move toward structured human-AI collaboration on design artifacts.

---
