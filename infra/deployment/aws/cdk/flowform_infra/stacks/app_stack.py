import json

from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import EnvConfig, runtime_group_logical_names, runtime_parameter_name
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.host_stack import RoleHostStack, pascal_case
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.registry_stack import RegistryStack


class AppStack(RoleHostStack):
    """Private App EC2 host and its backend runtime contract."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        registry_stack: RegistryStack,
        database_stack: DatabaseStack,
        task_role: iam.IRole,
        kms_key: kms.Key,
        linkage_secret_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, env_config=env_config, **kwargs)

        if env_config.public_site_domain is None:
            raise ValueError("AppStack requires public_site_domain")
        if env_config.auth0_public is None:
            raise ValueError(f"AppStack requires Auth0 public configuration for {env_config.env_name}")
        if env_config.runtime_public is None:
            raise ValueError(f"AppStack requires runtime public configuration for {env_config.env_name}")

        self.database_stack = database_stack
        self.kms_key = kms_key
        self.linkage_secret_arn = linkage_secret_arn

        ecr_policy = self.attach_ecr_pull_policy(
            "AppEcrPullPolicy",
            task_role,
            [
                registry_stack.backend_repository,
                registry_stack.alloy_repository,
            ],
        )
        release_policy = self.attach_release_read_policy("AppReleaseReadPolicy", task_role, "app")

        self.app_instance = ec2.Instance(
            self,
            "AppInstance",
            vpc=network_stack.vpc,
            vpc_subnets=network_stack.app_subnets,
            instance_name=f"flowform-{env_config.env_name}-app",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL),
            machine_image=self.role_machine_image("app"),
            role=task_role,
            security_group=network_stack.app_security_group,
            associate_public_ip_address=False,
            http_tokens=ec2.HttpTokens.REQUIRED,
            http_put_response_hop_limit=2,
            block_devices=self.root_block_devices(),
            user_data=self.build_user_data("app", network_stack.proxy_private_dns_name),
        )
        self.app_instance.node.add_dependency(ecr_policy)
        self.app_instance.node.add_dependency(release_policy)

        self.app_private_dns_record = route53.ARecord(
            self,
            "AppPrivateDnsRecord",
            zone=network_stack.private_hosted_zone,
            record_name="app",
            target=route53.RecordTarget.from_ip_addresses(self.app_instance.instance_private_ip),
            ttl=Duration.minutes(1),
        )

        self._publish_runtime_parameters()

    def _publish_runtime_parameters(self) -> None:
        env_config = self.env_config
        auth0_public = env_config.auth0_public
        runtime_public = env_config.runtime_public
        assert auth0_public is not None
        assert runtime_public is not None
        assert env_config.public_site_domain is not None

        values: dict[str, str] = {
            "runtime_environment": env_config.env_name,
            "logging_json": "true",
            "logging_level": "INFO",
            "tracing_enabled": "true",
            "tracing_otlp_endpoint": "http://alloy:4317",
            "tracing_sample_ratio": "1.0",
            "tracing_service_name": "backend",
            "site_url": f"https://{env_config.studio_domain}",
            "aws_region": env_config.region,
            "kms_key_arn": self.kms_key.key_arn,
            "cors_supports_credentials": "true",
            "auth0_domain": auth0_public.domain,
            "auth0_audience": auth0_public.audience,
            "auth0_client_id": auth0_public.client_id,
            "auth0_management_domain": runtime_public.auth0_management_domain,
            "auth0_management_id": runtime_public.auth0_management_id,
            "auth0_management_validate_on_startup": "true",
            "email_from_address": runtime_public.email_from_address,
            "database_core_name": "flowform_core",
            "database_core_app_user": DatabaseStack.CORE_APP_USER,
            "database_response_name": "flowform_response",
            "database_response_app_user": DatabaseStack.RESPONSE_APP_USER,
            "database_core_auth_mode": "iam",
            "database_response_auth_mode": "iam",
            "database_core_host": self.database_stack.endpoint_address,
            "database_response_host": self.database_stack.endpoint_address,
            "linkage_secret_arn": self.linkage_secret_arn,
        }

        if env_config.studio_domain is not None:
            values["cors_origins"] = json.dumps(
                [f"https://{env_config.studio_domain}", f"https://{env_config.public_site_domain}"]
            )

        unknown = set(values) - runtime_group_logical_names("backend")
        if unknown:
            raise ValueError(f"backend runtime parameters not in the contract: {sorted(unknown)}")

        for logical_name, value in values.items():
            parameter = ssm.StringParameter(
                self,
                f"BackendParam{pascal_case(logical_name)}",
                parameter_name=runtime_parameter_name(env_config.security_scope, "backend", logical_name),
                string_value=value,
            )
            self.app_instance.node.add_dependency(parameter)
