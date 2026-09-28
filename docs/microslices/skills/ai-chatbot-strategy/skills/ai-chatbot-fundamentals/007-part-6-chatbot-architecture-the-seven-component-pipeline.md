---
id: skill-part-6-chatbot-architecture-the-seven-component-pipeline-13b72f1284
purpose: part 6 chatbot architecture the seven component pipeline
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/ai-chatbot-fundamentals/SKILL.md
requires: ["skill-part-5-prompt-engineering-4ae62b4295"]
links: ["skill-part-7-how-chatbots-process-language-nlp-mechanics-90e584bd61"]
---

## Part 6: Chatbot Architecture — The Seven-Component Pipeline

### What a Chatbot Is

A chatbot is software designed to simulate human conversation. Some follow simple scripts. Others use powerful AI to understand meaning, learn from conversation, and adapt to new situations. The more sophisticated the underlying architecture, the less robotic the interaction feels — though the interaction is never something the bot experiences. It is a pipeline processing an input and producing an output.

A chatbot is not a monolithic intelligence — it is an engineered pipeline, and the quality of any deployment is only as good as the weakest component in that pipeline.

### How a Chatbot Works in Simple Steps

When a user messages a bank's chatbot asking "What's my checking balance?", the following happens in sequence in under a second:

1. The message is received and the text is broken into analyzable components
2. The system determines what the user is trying to accomplish (check account balance)
3. The relevant information is retrieved from a database
4. A response is composed in natural language
5. The response is returned to the user

If the pipeline works, it feels seamless. If any component fails — if intent recognition misclassifies the request, if the knowledge base has no matching record, if the language generation produces an ambiguous reply — the user encounters the familiar "Sorry, I didn't understand that."

### The Seven Components

#### 1. User Interface (UI)
The front end — where a user types or speaks. This could be a chat window on a website, a voice assistant, or a messaging integration with WhatsApp or Slack. The UI determines how input enters the system.

#### 2. Natural Language Processing (NLP)
Where the chatbot begins to interpret user input. NLP includes:
- **Tokenization:** Splitting text into analyzable units
- **Normalization:** Lowercasing, punctuation handling, spelling correction
- **Named Entity Recognition:** Identifying terms like "New York" or "Tuesday"
- **Intent Recognition:** Determining what the user is trying to do (e.g., "book a flight")

#### 3. Natural Language Understanding (NLU)
NLU goes deeper than NLP — it maps what the user *said* to what they *meant*. Using ML models trained on labeled examples, NLU identifies:
- **Intent:** The action the user wants
- **Entities:** The specific details — who, what, when, where

For "Book a flight to Paris tomorrow": Intent = `BookFlight`, Destination = `Paris`, Date = `Tomorrow`.

#### 4. Dialogue Manager
The conversation memory of the chatbot. Tracks what has been said, what information is still needed, and what should happen next. When a user says "Yes" as a follow-up message, the Dialogue Manager determines what that "yes" refers to. Without it, each message would be processed in isolation — multi-turn conversation would be impossible.

#### 5. Knowledge Base
Where the bot retrieves answers. May contain FAQs, API connections, product databases, policy documents, or a RAG system that dynamically retrieves relevant content at query time. The quality and coverage of the knowledge base is one of the most significant determinants of chatbot usefulness.

#### 6. Natural Language Generation (NLG)
Once the chatbot knows what to say, NLG converts that information into a sentence. This could be a prewritten template, a retrieved sentence from a database, or a dynamically generated response from a language model. GPT-class models handle this layer in modern AI-driven chatbots.

#### 7. Data Storage and Logging
Chatbots store interaction logs for: improving responses over time through ML feedback, personalizing future interactions, and maintaining session continuity. Stored data powers smarter bots that remember preferences and prior exchanges.

### Chatbot Types

| Type | How It Works | Use Case |
|---|---|---|
| Rule-Based | Follows scripts, uses keywords | FAQs, support bots |
| AI-Driven | Uses ML to understand and learn | Personal assistants, RAG bots |
| Task-Oriented | Focused on doing one job well | Booking, scheduling, onboarding |
| Conversational | Maintains memory, adjusts tone, handles open-ended dialogue | Advanced support, AI companions |

### Real-World Deployments

- **E-commerce bot:** Helps customers find products, routes to checkout
- **HR assistant:** Answers policy questions, processes time-off requests, connects to HRIS systems
- **Healthcare bot:** Schedules appointments, sends medication reminders, answers insurance questions
- **Internal operations chatbot:** Answers operational questions using RAG connected to internal documentation
- **Domino's "Dom":** Processes more than 50% of U.S. orders through digital channels, handling order customization, upselling, payment routing, and customer confirmation at scale without a human agent in the loop

### Consistent Failure Modes

Any deployment needs to account for these: ambiguous inputs are difficult to route without additional context; generative chatbots can hallucinate — producing confident, plausible, incorrect answers; training data bias surfaces as response bias; tone control across a wide range of inputs requires ongoing calibration; multilingual capability varies significantly by system.

---
