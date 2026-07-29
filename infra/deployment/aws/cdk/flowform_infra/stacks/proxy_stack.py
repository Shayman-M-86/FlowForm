from typing import cast

from aws_cdk import ArnFormat, Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import EnvConfig, runtime_group_logical_names, runtime_parameter_name
from flowform_infra.stacks.host_stack import RoleHostStack, pascal_case
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.registry_stack import RegistryStack


class ProxyStack(RoleHostStack):
    """Public Proxy EC2 host, ingress DNS, and proxy runtime contract."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        registry_stack: RegistryStack,
        kms_key: kms.Key,
        observability_secret_arn: str,
        hosted_zone: route53.IHostedZone,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, env_config=env_config, **kwargs)

        if env_config.public_site_domain is None:
            raise ValueError("ProxyStack requires public_site_domain")
        if env_config.runtime_public is None:
            raise ValueError(f"ProxyStack requires runtime public configuration for {env_config.env_name}")

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

        ecr_policy = self.attach_ecr_pull_policy(
            "ProxyEcrPullPolicy",
            cast(iam.IRole, self.proxy_role),
            [
                registry_stack.caddy_repository,
                registry_stack.squid_repository,
                registry_stack.alloy_repository,
            ],
        )
        release_policy = self.attach_release_read_policy(
            "ProxyReleaseReadPolicy",
            cast(iam.IRole, self.proxy_role),
            "proxy",
        )

        self.proxy_instance = ec2.Instance(
            self,
            "ProxyInstance",
            vpc=network_stack.vpc,
            vpc_subnets=network_stack.proxy_subnets,
            instance_name=f"flowform-{env_config.env_name}-proxy",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL),
            machine_image=self.role_machine_image("proxy"),
            role=cast(iam.IRole, self.proxy_role),
            security_group=network_stack.proxy_security_group,
            http_tokens=ec2.HttpTokens.REQUIRED,
            http_put_response_hop_limit=2,
            block_devices=self.root_block_devices(),
            user_data=self.build_user_data("proxy", network_stack.app_private_dns_name),
        )
        self.proxy_instance.node.add_dependency(ecr_policy)
        self.proxy_instance.node.add_dependency(release_policy)
        proxy_default_policy = self.proxy_role.node.try_find_child("DefaultPolicy")
        if proxy_default_policy is not None:
            self.proxy_instance.node.add_dependency(proxy_default_policy)

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
        self.proxy_private_dns_record = route53.ARecord(
            self,
            "ProxyPrivateDnsRecord",
            zone=network_stack.private_hosted_zone,
            record_name="proxy",
            target=route53.RecordTarget.from_ip_addresses(self.proxy_instance.instance_private_ip),
            ttl=Duration.minutes(1),
        )

        self._publish_runtime_parameters()

    def _publish_runtime_parameters(self) -> None:
        env_config = self.env_config
        runtime_public = env_config.runtime_public
        assert runtime_public is not None
        assert env_config.public_site_domain is not None

        values = {
            "runtime_environment": "prod",
            "api_domain": f"api.{env_config.public_site_domain}",
            "grafana_cloud_loki_url": runtime_public.grafana_cloud_loki_url,
            "grafana_cloud_loki_user": runtime_public.grafana_cloud_loki_user,
            "grafana_cloud_tempo_endpoint": runtime_public.grafana_cloud_tempo_endpoint,
            "grafana_cloud_tempo_user": runtime_public.grafana_cloud_tempo_user,
        }
        unknown = set(values) - runtime_group_logical_names("proxy")
        if unknown:
            raise ValueError(f"proxy runtime parameters not in the contract: {sorted(unknown)}")

        for logical_name, value in values.items():
            parameter = ssm.StringParameter(
                self,
                f"ProxyParam{pascal_case(logical_name)}",
                parameter_name=runtime_parameter_name(env_config.security_scope, "proxy", logical_name),
                string_value=value,
            )
            self.proxy_instance.node.add_dependency(parameter)
