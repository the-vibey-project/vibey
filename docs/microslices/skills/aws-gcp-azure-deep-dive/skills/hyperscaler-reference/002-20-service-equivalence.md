---
id: skill-20-service-equivalence-f4861e878c
purpose: 20 service equivalence
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-reference/SKILL.md
requires: ["skill-19-anti-patterns-758bf8cf72"]
links: ["skill-21-what-moved-verified-august-2026-88c6f1660d"]
---

## §20. Service Equivalence

| Capability | AWS | Azure | GCP |
|---|---|---|---|
| VMs | EC2 | Virtual Machines | Compute Engine |
| Autoscaling | Auto Scaling Group | VM Scale Sets | Managed Instance Group |
| Serverless functions | Lambda | Functions | Cloud Functions |
| Serverless containers | Fargate / App Runner | Container Apps | **⚠️ Cloud Run** |
| Managed Kubernetes | EKS | AKS | **⚠️ GKE** |
| Object storage | S3 | Blob Storage | Cloud Storage |
| Block storage | EBS | Managed Disks | Persistent Disk / Hyperdisk |
| File storage | EFS / FSx | Azure Files | Filestore |
| Managed relational | RDS / Aurora | Azure SQL / Flexible | Cloud SQL / AlloyDB |
| Global distributed DB | Aurora DSQL | **Cosmos DB** | **⚠️ Spanner** |
| NoSQL | DynamoDB | Cosmos DB | Firestore / Bigtable |
| Cache | ElastiCache | Azure Cache for Redis | Memorystore |
| Data warehouse | Redshift | Fabric / Synapse | **⚠️ BigQuery** |
| ETL | Glue | Data Factory | Dataflow / Dataproc |
| Streaming | Kinesis / MSK | Event Hubs | Pub/Sub |
| BI | QuickSight | **Power BI** | Looker |
| Message queue | SQS | Service Bus / Queue Storage | Pub/Sub / Tasks |
| Event bus | EventBridge | Event Grid | Eventarc |
| Workflow | Step Functions | Logic Apps / Durable | Workflows |
| API gateway | API Gateway | API Management | API Gateway / Apigee |
| CDN | CloudFront | Azure Front Door / CDN | Cloud CDN |
| DNS | Route 53 | Azure DNS | Cloud DNS |
| Load balancer | ALB / NLB | Load Balancer / App Gateway | **⚠️ Global LB** |
| Private network | VPC | VNet | **⚠️ VPC (global)** |
| Private service access | PrivateLink | Private Link | Private Service Connect |
| On-prem link | Direct Connect | ExpressRoute | Cloud Interconnect |
| Identity | IAM | **⚠️ Entra ID + Azure RBAC** | Cloud IAM |
| Secrets | Secrets Manager / SSM | Key Vault | Secret Manager |
| Key management | KMS / CloudHSM | Key Vault / Managed HSM | Cloud KMS |
| Audit log | **CloudTrail** | **Activity Log** | **Cloud Audit Logs** |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring |
| Tracing | X-Ray | Application Insights | Cloud Trace |
| Posture management | Security Hub | Defender for Cloud | Security Command Center |
| Policy guardrails | SCPs / Config | Azure Policy | Organization Policy |
| Native IaC | CloudFormation | Bicep / ARM | (Terraform in practice) |
| ML platform | SageMaker | Azure ML / Foundry | Vertex AI |
| Model API | Bedrock | Azure OpenAI / Foundry | Vertex / Gemini API |
| Edge compute | Lambda@Edge / CloudFront Fn | Azure Functions on Edge | Cloud Run / CDN |

---
