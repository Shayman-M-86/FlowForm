import json
from collections.abc import Sequence
from typing import cast

from aws_cdk import ArnFormat, Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import (
    EnvConfig,
    HostRole,
    host_service_name,
    instance_context_mode,
    instance_context_path,
    peer_context_key,
    release_parameter_name,
    runtime_group_logical_names,
    runtime_parameter_name,
)
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.registry_stack import RegistryStack

# The stack owns the two EC2 resources and their AWS-facing contracts, not
# runtime implementation. The public Proxy role provides Caddy ingress and
# Squid egress; the isolated App role runs the backend and reaches approved
# external services through Squid. Each instance launches a role AMI built
# under infra/machine-images/definitions/. User data writes only the canonical
# non-secret instance context and starts the baked role systemd unit.
#
# Container images own service binaries and configuration under
# infra/containers/images/. Runtime Compose topology and release helpers live
# under infra/containers/runtime/. Immutable container digests are promoted as
# one complete role release through the external SSM release parameter; CDK
# grants read access but deliberately does not own that mutable value.


def _pascal_case(logical_name: str) -> str:
    """Turn a contract logical name into a stable CDK construct id."""
    return "".join(part.capitalize() for part in logical_name.split("_"))


class ApplicationStack(Stack):
    """Public proxy EC2 (Caddy+Squid) + private app EC2 (Flask/Gunicorn)."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        registry_stack: RegistryStack,
        task_role: iam.IRole,
        kms_key: kms.Key,
        database_stack: DatabaseStack | None = None,
        linkage_secret_arn: str | None = None,
        observability_secret_arn: str | None = None,
        hosted_zone: route53.IHostedZone | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.network_stack = network_stack
        self.registry_stack = registry_stack
        self.task_role = task_role
        self.kms_key = kms_key
        self.database_stack = database_stack
        self.linkage_secret_arn = linkage_secret_arn
        self.observability_secret_arn = observability_secret_arn
        self.hosted_zone = hosted_zone

        if env_config.public_site_domain is None:
            raise ValueError("ApplicationStack requires public_site_domain")
        if env_config.auth0_public is None:
            raise ValueError(f"ApplicationStack requires Auth0 public configuration for {env_config.env_name}")
        if env_config.runtime_public is None:
            raise ValueError(f"ApplicationStack requires runtime public configuration for {env_config.env_name}")
        if hosted_zone is None:
            raise ValueError("ApplicationStack requires the public Route 53 hosted zone")
        if observability_secret_arn is None:
            raise ValueError("ApplicationStack requires the observability secret ARN")

        # aws-cdk-lib's generated concrete principal methods use parameter
        # names that do not structurally match the IPrincipal protocol. The
        # cast contains that jsii typing mismatch without changing the
        # synthesized IAM role or trust policy.
        self.proxy_role = iam.Role(
            self,
            "ProxyInstanceRole",
            assumed_by=cast(iam.IPrincipal, iam.ServicePrincipal("ec2.amazonaws.com")),
            description=f"Proxy EC2 role for FlowForm {env_config.env_name}",
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")],
        )
        self.proxy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParametersByPath"],
                resources=[
                    self.format_arn(
                        service="ssm",
                        resource="parameter",
                        resource_name=f"flowform/{env_config.security_scope}/proxy/*",
                        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
                    )
                ],
            )
        )

        if hosted_zone is not None:
            hosted_zone_arn = f"arn:aws:route53:::hostedzone/{hosted_zone.hosted_zone_id}"
            self.proxy_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "route53:ChangeResourceRecordSets",
                        "route53:ListResourceRecordSets",
                    ],
                    resources=[hosted_zone_arn],
                )
            )
            self.proxy_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["route53:GetChange"],
                    resources=["arn:aws:route53:::change/*"],
                )
            )
            self.proxy_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["route53:ListHostedZonesByName"],
                    resources=["*"],
                )
            )

        app_ecr_policy = self._attach_ecr_pull_policy(
            "AppEcrPullPolicy",
            task_role,
            [
                registry_stack.backend_repository,
                registry_stack.alloy_repository,
            ],
        )
        self.proxy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"],
                resources=[observability_secret_arn],
            )
        )
        self.proxy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt"],
                resources=[kms_key.key_arn],
                conditions={
                    "StringEquals": {
                        "kms:ViaService": f"secretsmanager.{env_config.region}.amazonaws.com",
                    }
                },
            )
        )
        proxy_ecr_policy = self._attach_ecr_pull_policy(
            "ProxyEcrPullPolicy",
            cast(iam.IRole, self.proxy_role),
            [
                registry_stack.caddy_repository,
                registry_stack.squid_repository,
                registry_stack.alloy_repository,
            ],
        )

        instance_type = ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL)
        app_machine_image = self._role_machine_image("app")
        proxy_machine_image = self._role_machine_image("proxy")
        app_release_policy = self._attach_release_read_policy("AppReleaseReadPolicy", task_role, "app")
        proxy_release_policy = self._attach_release_read_policy(
            "ProxyReleaseReadPolicy",
            cast(iam.IRole, self.proxy_role),
            "proxy",
        )

        root_block_devices = [
            ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(
                    env_config.ec2_root_volume_size_gib,
                    volume_type=ec2.EbsDeviceVolumeType.GP3,
                    encrypted=True,
                    delete_on_termination=True,
                ),
            )
        ]

        self.proxy_instance = ec2.Instance(
            self,
            "ProxyInstance",
            vpc=network_stack.vpc,
            vpc_subnets=network_stack.proxy_subnets,
            instance_name=f"flowform-{env_config.env_name}-proxy",
            instance_type=instance_type,
            machine_image=proxy_machine_image,
            role=cast(iam.IRole, self.proxy_role),
            security_group=network_stack.proxy_security_group,
            http_tokens=ec2.HttpTokens.REQUIRED,
            http_put_response_hop_limit=2,
            block_devices=root_block_devices,
            user_data=self._build_user_data("proxy", network_stack.app_private_dns_name),
        )

        self.proxy_elastic_ip = ec2.CfnEIP(
            self,
            "ProxyElasticIp",
            domain="vpc",
            instance_id=self.proxy_instance.instance_id,
        )
        self.api_dns_record = route53.ARecord(
            self,
            "ApiDnsRecord",
            zone=hosted_zone,
            record_name=f"api.{env_config.public_site_domain}",
            target=route53.RecordTarget.from_ip_addresses(self.proxy_elastic_ip.ref),
            ttl=Duration.minutes(1),
        )

        self.app_instance = ec2.Instance(
            self,
            "AppInstance",
            vpc=network_stack.vpc,
            vpc_subnets=network_stack.app_subnets,
            instance_name=f"flowform-{env_config.env_name}-app",
            instance_type=instance_type,
            machine_image=app_machine_image,
            role=task_role,
            security_group=network_stack.app_security_group,
            associate_public_ip_address=False,
            http_tokens=ec2.HttpTokens.REQUIRED,
            http_put_response_hop_limit=2,
            block_devices=root_block_devices,
            user_data=self._build_user_data("app", network_stack.proxy_private_dns_name),
        )
        self.app_instance.node.add_dependency(self.proxy_instance)
        self.app_instance.node.add_dependency(app_ecr_policy)
        self.app_instance.node.add_dependency(app_release_policy)
        self.proxy_instance.node.add_dependency(proxy_ecr_policy)
        self.proxy_instance.node.add_dependency(proxy_release_policy)
        proxy_default_policy = self.proxy_role.node.try_find_child("DefaultPolicy")
        if proxy_default_policy is not None:
            self.proxy_instance.node.add_dependency(proxy_default_policy)

        self.proxy_private_dns_record = route53.ARecord(
            self,
            "ProxyPrivateDnsRecord",
            zone=network_stack.private_hosted_zone,
            record_name="proxy",
            target=route53.RecordTarget.from_ip_addresses(self.proxy_instance.instance_private_ip),
            ttl=Duration.minutes(1),
        )
        self.app_private_dns_record = route53.ARecord(
            self,
            "AppPrivateDnsRecord",
            zone=network_stack.private_hosted_zone,
            record_name="app",
            target=route53.RecordTarget.from_ip_addresses(self.app_instance.instance_private_ip),
            ttl=Duration.minutes(1),
        )

        self._publish_runtime_parameters()

    def _build_user_data(self, role: HostRole, peer_dns_name: str) -> ec2.UserData:
        """Write non-secret instance identity and start the baked role service."""
        context = {
            "schema_version": 1,
            "environment": self.env_config.env_name,
            "role": role,
            "region": self.env_config.region,
            "parameter_root": f"/flowform/{self.env_config.env_name}",
            "configuration_root": f"/flowform/{self.env_config.security_scope}",
            peer_context_key(role): peer_dns_name,
        }
        context_path = instance_context_path()
        context_json = json.dumps(context, indent=2, sort_keys=True)
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -euo pipefail",
            "install -d -m 0755 /etc/flowform",
            "umask 077",
            f"cat > {context_path} <<'FLOWFORM_CONTEXT'",
            context_json,
            "FLOWFORM_CONTEXT",
            f"chown root:root {context_path}",
            f"chmod {instance_context_mode()} {context_path}",
            f"systemctl enable --now {host_service_name(role)}",
        )
        return user_data

    def _role_machine_image(self, role: HostRole) -> ec2.IMachineImage:
        direct_ami_id = self.env_config.ec2_app_ami_id if role == "app" else self.env_config.ec2_proxy_ami_id
        parameter = (
            self.env_config.ec2_app_ami_ssm_parameter if role == "app" else self.env_config.ec2_proxy_ami_ssm_parameter
        )
        if direct_ami_id:
            return ec2.MachineImage.generic_linux({self.env_config.region: direct_ami_id})
        if parameter:
            return ec2.MachineImage.from_ssm_parameter(
                parameter,
                os=ec2.OperatingSystemType.LINUX,
            )
        raise ValueError(f"EnvConfig for '{self.env_config.env_name}' must provide a Packer-built {role} AMI")

    def _attach_release_read_policy(
        self,
        construct_id: str,
        role: iam.IRole,
        host_role: HostRole,
    ) -> iam.Policy:
        """Grant read-only access to the role's atomic release pointer."""
        parameter_name = release_parameter_name(self.env_config.env_name, host_role)
        policy = iam.Policy(
            self,
            construct_id,
            statements=[
                iam.PolicyStatement(
                    actions=["ssm:GetParameter"],
                    resources=[
                        self.format_arn(
                            service="ssm",
                            resource="parameter",
                            resource_name=parameter_name.removeprefix("/"),
                            arn_format=ArnFormat.SLASH_RESOURCE_NAME,
                        )
                    ],
                )
            ],
        )
        policy.attach_to_role(role)
        return policy

    def _publish_runtime_parameters(self) -> None:
        """Publish the backend runtime group to SSM.

        App bootstrap reads every parameter under this path and renders each
        one into a `KEY=value` line of backend.env, so the last path segment is
        the environment-variable name and the values here must be exactly what
        the backend expects.

        Only non-secret configuration belongs here. Secrets stay in Secrets
        Manager and are materialised into tmpfs files by bootstrap.
        """
        env_config = self.env_config
        scope_name = env_config.security_scope
        auth0_public = env_config.auth0_public
        runtime_public = env_config.runtime_public
        assert auth0_public is not None
        assert runtime_public is not None
        assert env_config.public_site_domain is not None

        values: dict[str, str] = {
            "runtime_environment": "prod",
            "logging_json": "true",
            "logging_level": "INFO",
            "tracing_enabled": "true",
            "tracing_otlp_endpoint": "http://alloy:4317",
            "tracing_sample_ratio": "1.0",
            "tracing_service_name": "backend",
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
            # Database connection parts. Both databases live on one RDS
            # instance, so they share a host and differ only by name and user.
            "database_core_name": "flowform_core",
            "database_core_app_user": DatabaseStack.CORE_APP_USER,
            "database_response_name": "flowform_response",
            "database_response_app_user": DatabaseStack.RESPONSE_APP_USER,
            # No database password exists on AWS; the backend authenticates
            # with short-lived RDS IAM tokens. App bootstrap refuses to deploy
            # if these disagree with its deployment target.
            "database_core_auth_mode": "iam",
            "database_response_auth_mode": "iam",
        }

        if self.database_stack is not None:
            values["database_core_host"] = self.database_stack.endpoint_address
            values["database_response_host"] = self.database_stack.endpoint_address

        if self.linkage_secret_arn is not None:
            values["linkage_secret_arn"] = self.linkage_secret_arn

        if env_config.studio_domain is not None and env_config.public_site_domain is not None:
            values["cors_origins"] = json.dumps(
                [f"https://{env_config.studio_domain}", f"https://{env_config.public_site_domain}"]
            )

        unknown = set(values) - runtime_group_logical_names("backend")
        if unknown:
            raise ValueError(f"backend runtime parameters not in the contract: {sorted(unknown)}")

        for logical_name, value in values.items():
            parameter = ssm.StringParameter(
                self,
                f"BackendParam{_pascal_case(logical_name)}",
                parameter_name=runtime_parameter_name(scope_name, "backend", logical_name),
                string_value=value,
            )
            self.app_instance.node.add_dependency(parameter)

        proxy_values = {
            "runtime_environment": "prod",
            "api_domain": f"api.{env_config.public_site_domain}",
            "grafana_cloud_loki_url": runtime_public.grafana_cloud_loki_url,
            "grafana_cloud_loki_user": runtime_public.grafana_cloud_loki_user,
            "grafana_cloud_tempo_endpoint": runtime_public.grafana_cloud_tempo_endpoint,
            "grafana_cloud_tempo_user": runtime_public.grafana_cloud_tempo_user,
        }
        unknown = set(proxy_values) - runtime_group_logical_names("proxy")
        if unknown:
            raise ValueError(f"proxy runtime parameters not in the contract: {sorted(unknown)}")
        for logical_name, value in proxy_values.items():
            parameter = ssm.StringParameter(
                self,
                f"ProxyParam{_pascal_case(logical_name)}",
                parameter_name=runtime_parameter_name(scope_name, "proxy", logical_name),
                string_value=value,
            )
            self.proxy_instance.node.add_dependency(parameter)

    def _attach_ecr_pull_policy(
        self,
        construct_id: str,
        role: iam.IRole,
        repositories: Sequence[ecr.IRepository],
    ) -> iam.Policy:
        """Attach exact ECR pull permissions without mutating another stack."""
        policy = iam.Policy(
            self,
            construct_id,
            statements=[
                iam.PolicyStatement(
                    actions=["ecr:GetAuthorizationToken"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer",
                    ],
                    resources=[repository.repository_arn for repository in repositories],
                ),
            ],
        )
        policy.attach_to_role(role)
        return policy
