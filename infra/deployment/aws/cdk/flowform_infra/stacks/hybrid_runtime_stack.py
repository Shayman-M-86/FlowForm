from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import EnvConfig, runtime_group_logical_names, runtime_parameter_name
from flowform_infra.stacks.host_stack import pascal_case
from flowform_infra.stacks.runtime_parameters import backend_runtime_values, proxy_runtime_values
from flowform_infra.stacks.security_stack import SecurityStack


class HybridRuntimeStack(Stack):
    """Runtime configuration for the Proxmox app and proxy."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        security_stack: SecurityStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if env_config.auth0_public is None or env_config.runtime_public is None:
            raise ValueError(f"HybridRuntimeStack requires Auth0 and runtime configuration for {env_config.env_name}")
        if env_config.api_domain is None or env_config.public_site_domain is None:
            raise ValueError(f"HybridRuntimeStack requires API and public site domains for {env_config.env_name}")

        # The hybrid bootstrap supplies the database host and authentication
        # mode locally. SSM still supplies the database names and users.
        groups = {
            "backend": backend_runtime_values(
                env_config,
                kms_key_arn=security_stack.kms_key.key_arn,
                linkage_secret_arn=security_stack.linkage_secret.secret_arn,
            ),
            "proxy": proxy_runtime_values(env_config),
        }
        for group, values in groups.items():
            unknown = set(values) - runtime_group_logical_names(group)
            if unknown:
                raise ValueError(f"{group} runtime parameters not in the contract: {sorted(unknown)}")

            for logical_name, value in values.items():
                parameter = ssm.StringParameter(
                    self,
                    f"{group.capitalize()}Param{pascal_case(logical_name)}",
                    parameter_name=runtime_parameter_name(env_config.security_scope, group, logical_name),
                    string_value=value,
                )
                parameter.apply_removal_policy(RemovalPolicy.RETAIN)
