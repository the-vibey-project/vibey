# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""AzCliClientAdapter: the real AzureClientPort, over the `az` CLI.

Deliberately never a default -- bootstrap keeps the in-memory adapter
unless a caller passes this one explicitly (`vibey worker --azure az`).
Every mutating call re-verifies consent against the spec's scope digest
here, at the last boundary before real infrastructure changes, even
though the acceptance handler already did: consent is never assumed to
have survived transport.

Reads are `az ... -o json` subprocesses; the deployment path renders the
spec into an ARM template (arm.py) and submits it with
`az deployment group create`. `az` must be installed and logged in
(`az login`) -- preflight that with `az account show` before trusting a
worker to this adapter.
"""

import asyncio
import json
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Any

from vibey.application.interfaces import (
    AzureDiscoveryResult,
    AzureExecutionResult,
    AzureResourceStatus,
)
from vibey.domain.deployment import AzureTargetScope, DeploymentConsent, DeploymentSpec
from vibey.domain.errors import VibeyError
from vibey.infrastructure.azure.arm import DEFAULT_IMAGE, render_template
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.interfaces import CommandExecutor
from vibey.infrastructure.process import SYSTEM_ENVIRONMENT, ChildEnvironment

# What `az` reads of its environment beyond the system basics: where its login and
# extensions live, and its configuration, which it takes from `AZURE_<SECTION>_<NAME>`
# for the sections it has. Nothing of vibey's -- `az` runs Python extensions -- and no
# model-endpoint key (`AZURE_OPENAI_*`) it never reads. An operator who logs `az` in
# from the environment instead of `az login` declares more through `env_allow`.
AZ_CLI_ENV_ALLOW: tuple[str, ...] = (
    "AZURE_CONFIG_DIR",
    "AZURE_EXTENSION_DIR",
    "AZURE_HTTP_USER_AGENT",
    "AZURE_CORE_*",
    "AZURE_DEFAULTS_*",
    "AZURE_CLOUD_*",
    "AZURE_LOGGING_*",
    "AZURE_EXTENSION_*",
)


class AzCliSubprocessExecutor:
    """Runs one `az` command, with an environment built from its own declaration and
    never copied from the worker's. Satisfies `infrastructure/interfaces.CommandExecutor`;
    declared by `interfaces/az_cli_interface.py`.

    It used to share vibey's git executor, which then copied the worker's environment
    minus `GIT_*` -- `VIBEY_PG_URL` included -- into a CLI that loads extensions.
    """

    __slots__ = ("_environment",)

    def __init__(self, *, env_allow: Iterable[str] = ()) -> None:
        self._environment = ChildEnvironment(
            SYSTEM_ENVIRONMENT.extended((*AZ_CLI_ENV_ALLOW, *env_allow), where="az CLI environment")
        )

    @property
    def environment(self) -> ChildEnvironment:
        return self._environment

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        if not argv or PurePath(argv[0]).name != "az":
            raise ValueError(f"the az executor runs az only, not {argv[:1]!r}")
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._environment.build(),
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise
        return CommandResult(process.returncode or 0, stdout.decode(), stderr.decode())


class AzCliError(VibeyError):
    def __init__(self, argv: tuple[str, ...], stderr: str) -> None:
        self.argv = argv
        self.stderr = stderr
        super().__init__(f"{' '.join(argv[:4])}... failed: {stderr.strip()[:500]}")


class MutationNotAuthorized(VibeyError):
    """Raised when a mutating call arrives without digest-bound consent."""


class AzCliClientAdapter:
    def __init__(
        self,
        *,
        executor: CommandExecutor | None = None,
        image: str = DEFAULT_IMAGE,
    ) -> None:
        self._executor = executor or AzCliSubprocessExecutor()
        self._image = image

    @property
    def executor(self) -> CommandExecutor:
        """What every `az` call goes through."""
        return self._executor

    async def _az_json(self, *args: str) -> Any:
        argv = ("az", *args, "-o", "json")
        result = await self._executor.execute(argv)
        if result.returncode != 0:
            raise AzCliError(argv, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    async def discover_environment(self, scope: AzureTargetScope) -> AzureDiscoveryResult:
        account = await self._az_json("account", "show", "--subscription", scope.subscription_id)
        try:
            resources = await self._az_json(
                "resource",
                "list",
                "--resource-group",
                scope.resource_group,
                "--subscription",
                scope.subscription_id,
            )
        except AzCliError:
            # A resource group that does not exist yet is a valid discovery
            # result for a first deployment, not an error.
            resources = []
        return AzureDiscoveryResult(
            tenant_id=str(account.get("tenantId", scope.tenant_id)),
            subscription_id=scope.subscription_id,
            resource_group=scope.resource_group,
            location=scope.region,
            existing_resources=tuple(resources) if isinstance(resources, list) else (),
        )

    def _require_consent(self, spec_or_scope_digest: str, consent: DeploymentConsent) -> None:
        if (
            not consent.explicit_mutation_authorized
            or consent.target_scope_digest != spec_or_scope_digest
        ):
            raise MutationNotAuthorized(
                "mutation refused: consent is missing, unauthorized, or bound to a "
                "different target scope digest"
            )

    async def execute_plan(
        self, spec: DeploymentSpec, consent: DeploymentConsent
    ) -> AzureExecutionResult:
        self._require_consent(spec.scope_digest(), consent)
        scope = spec.target_scope

        await self._az_json(
            "group",
            "create",
            "--name",
            scope.resource_group,
            "--location",
            scope.region,
            "--subscription",
            scope.subscription_id,
        )

        template = render_template(spec, image=self._image)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", prefix="vibey-arm-", delete=False
        ) as handle:
            json.dump(template, handle)
            template_path = Path(handle.name)
        try:
            deployment = await self._az_json(
                "deployment",
                "group",
                "create",
                "--resource-group",
                scope.resource_group,
                "--subscription",
                scope.subscription_id,
                "--name",
                f"vibey-{spec.spec_id[:40]}",
                "--template-file",
                str(template_path),
            )
        finally:
            template_path.unlink(missing_ok=True)

        properties = deployment.get("properties", {}) if isinstance(deployment, dict) else {}
        return AzureExecutionResult(
            deployment_id=str(deployment.get("id", "")) if isinstance(deployment, dict) else "",
            provisioning_state=str(properties.get("provisioningState", "Unknown")),
            outputs=properties.get("outputs", {}) or {},
            applied_at=datetime.now(UTC),
        )

    async def get_resource_status(
        self, scope: AzureTargetScope, resource_id: str
    ) -> AzureResourceStatus:
        resource = await self._az_json(
            "resource", "show", "--ids", resource_id, "--subscription", scope.subscription_id
        )
        properties = resource.get("properties", {}) if isinstance(resource, dict) else {}
        state = str(properties.get("provisioningState", "Unknown"))
        return AzureResourceStatus(
            resource_id=resource_id,
            provisioning_state=state,
            health_state="Healthy" if state == "Succeeded" else "Degraded",
        )

    async def delete_resource(
        self, scope: AzureTargetScope, resource_id: str, consent: DeploymentConsent
    ) -> None:
        self._require_consent(scope.digest(), consent)
        await self._az_json(
            "resource", "delete", "--ids", resource_id, "--subscription", scope.subscription_id
        )
