# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""AWS infrastructure adapters implementing CloudClientPort.

At minimum we provide a stub that satisfies the CloudClientPort protocol.
This suffices for contract testing – no real AWS calls are made.
The adapter is declared-only: the sovereign default remains the OpenStack
adapter in infrastructure.
"""

from datetime import UTC, datetime
from typing import Any

from vibey.application.interfaces.azure import (
    AzureDiscoveryResult,
    AzureExecutionResult,
    AzureResourceStatus,
    CloudClientPort,
    DeploymentConsentStore,
    DeploymentSpecStore,
)
from vibey.domain.deployment import AzureTargetScope, DeploymentConsent, DeploymentSpec


class InMemoryAWSClientAdapter:
    """A deterministic test double that implements CloudClientPort.

    The AWS adapter is *declared-only*: it never mutates real resources.
    The public contract matches AzureAdapter for compatibility.
    """

    def __init__(self) -> None:
        self.resources: dict[str, dict[str, Any]] = {}
        self.deployments: list[AzureExecutionResult] = []

    async def discover_environment(self, scope: AzureTargetScope) -> AzureDiscoveryResult:
        # Simple static response reflecting the scope provider.
        return AzureDiscoveryResult(
            tenant_id=scope.tenant_id,
            subscription_id=scope.subscription_id,
            resource_group=scope.resource_group,
            location=scope.region,
            existing_resources=(),
            policies=(),
        )

    async def execute_plan(
        self, spec: DeploymentSpec, consent: DeploymentConsent
    ) -> AzureExecutionResult:
        # In declared-only mode simply record without mutation.
        now = datetime.now(UTC)
        result = AzureExecutionResult(
            deployment_id=f"aws-dep-{spec.spec_id}",
            provisioning_state="Succeeded",
            outputs={"endpoint": f"https://{spec.spec_id}.amazonaws.com"},
            applied_at=now,
        )
        self.deployments.append(result)
        self.resources[spec.spec_id] = {
            "provisioning_state": "Succeeded",
            "health_state": "Healthy",
        }
        return result

    async def get_resource_status(
        self, scope: AzureTargetScope, resource_id: str
    ) -> AzureResourceStatus:
        res = self.resources.get(resource_id, {})
        return AzureResourceStatus(
            resource_id=resource_id,
            provisioning_state=res.get("provisioning_state", "Succeeded"),
            health_state=res.get("health_state", "Healthy"),
        )

    async def delete_resource(
        self, scope: AzureTargetScope, resource_id: str, consent: DeploymentConsent
    ) -> None:
        # Declared-only: no real deletion, just keep state.
        self.resources.pop(resource_id, None)

# Expose the protocol alias used by the application layer
AWSClientPort = CloudClientPort
