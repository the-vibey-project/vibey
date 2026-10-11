import pytest

from vibey.infrastructure.aws.adapter import InMemoryAWSClientAdapter
from vibey.domain.deployment import (
    AzureTargetScope,
    DeploymentSpec,
    DeploymentConsent,
    IdentityAuthority,
    TopologyConfig,
    RecoveryPolicy,
    VerificationContract,
    CostBoundary,
)
from datetime import datetime

@pytest.mark.asyncio
async def test_inmemory_aws_adapter_contract():
    adapter = InMemoryAWSClientAdapter()
    scope = AzureTargetScope(
        tenant_id="t",
        subscription_id="s",
        resource_group="rg",
        environment="env",
        region="us-east-1",
    )
    discover = await adapter.discover_environment(scope)
    assert discover.location == "us-east-1"

    spec = DeploymentSpec(
        spec_id="demo",
        version="1",
        target_scope=scope,
        identity=IdentityAuthority(identity_type="user", principal_id="p"),
        topology=TopologyConfig(service_type="svc", iac_provider="tf", sku="sku"),
        recovery_policy=RecoveryPolicy(progressive_exposure="exp"),
        verification=VerificationContract(),
        cost_boundary=CostBoundary(max_monthly_budget_usd=10.0, max_deployment_cost_usd=5.0),
    )
    consent = DeploymentConsent(
        consent_id="consent1",
        target_scope_digest=scope.digest(),
        granted_by="tester",
        granted_at=datetime.utcnow(),
        explicit_mutation_authorized=True,
    )
    result = await adapter.execute_plan(spec, consent)
    assert result.deployment_id == "aws-dep-demo"
    status = await adapter.get_resource_status(scope, "demo")
    assert status.provisioning_state == "Succeeded"
    await adapter.delete_resource(scope, "demo", consent)
    status2 = await adapter.get_resource_status(scope, "demo")
    assert status2.provisioning_state == "Succeeded"  # remains same, declared only

