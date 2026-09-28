---
id: skill-8-serverless-cd3ad0f337
purpose: 8 serverless
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-networking-compute-containers-and-serverless/SKILL.md
requires: ["skill-7-containers-and-kubernetes-5a6b6757bd"]
links: []
---

## §8. Serverless

```
FaaS       Lambda           Azure Functions    Cloud Functions
Container  ⚠️ Fargate/Lambda container  Container Apps  ⚠️ CLOUD RUN
Workflow   Step Functions   Logic Apps / Durable  Workflows
Events     EventBridge      Event Grid         Eventarc / Pub-Sub
API        API Gateway      APIM               API Gateway / Apigee
```
**⚠️ Cloud Run is the standout**: **it runs any container that listens on a port, scales
to zero, and has none of FaaS's packaging constraints.** ⚠️ **It is the easiest path from
"I have a Dockerfile" to "it's in production and costs nothing when idle" on any of the
three.**
**⚠️ Serverless caveats that apply everywhere**: **cold starts** (⚠️ **worse for JVM/.NET,
mitigated by provisioned concurrency — which costs money and removes the scale-to-zero
benefit**), **execution time limits**, **⚠️ per-invocation pricing that becomes more
expensive than a VM above a sustained request rate**, **and the difficulty of local
testing.**
> **⚠️ GOTCHA — serverless is cheap for spiky/low traffic and expensive for steady high
> traffic.** ⚠️ **There is a crossover point where a small always-on instance is
> dramatically cheaper**, and **teams that adopted serverless for cost reasons at low
> volume frequently discover this the hard way after growth.**
