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
    runtime_group_logical_names,
    runtime_parameter_name,
)
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.registry_stack import RegistryStack

# Decided direction: TWO EC2 instances + Docker Compose (not ECS/ALB, no
# NAT Gateway, no paid interface endpoints) — the "cheapest hardened"
# shape in docs/cost-model.md, detailed in
# docs/implementation-sketch/caddy-ec2-implementation-notes.md:
#
#   - PUBLIC proxy EC2 (public subnet, Elastic IP): Caddy terminates TLS
#     for api.<public_site_domain> and reverse proxies to the app
#     instance's PRIVATE IP; Squid is the outbound forward proxy with a
#     domain allow-list (Auth0 + the AWS service endpoints the app uses).
#   - PRIVATE app EC2 (private subnet, no public IP, NO internet route):
#     runs the Flask/Gunicorn backend via docker-compose. All external
#     traffic — including AWS API calls — rides the proxy on 3128; ECR
#     image LAYERS ride the free S3 gateway endpoint; RDS is local VPC.
#
# Postgres does NOT run on either instance; both logical databases
# (core + response) live on RDS (database_stack, later milestone).
#
# TODO: build out
#   - network_stack: private app subnet with NO 0.0.0.0/0 route, free S3
#     gateway endpoint, RDS subnets — see the notes doc
#   - proxy instance (t4g.small, public subnet, EIP): SG inbound 80/443
#     from anywhere + 3128 from the app SG only; its own slim role
#     (Route 53 zone-scoped changes for DNS-01, ECR pull, SSM core)
#   - app instance (t4g.small, private subnet): SG inbound backend port
#     from proxy SG only; instance profile wraps security_stack.task_role
#     (secrets/KMS/SES/ECR)
#   - IMDSv2 hop limit 2 on BOTH instances (containers need role creds)
#   - proxy env plumbing on the app instance: HTTP(S)_PROXY for the
#     Docker daemon and the backend container; NO_PROXY must include
#     localhost,127.0.0.1,169.254.169.254 (IMDS), the VPC CIDR (RDS +
#     S3 endpoint must not hairpin), and Docker service names
#   - management path: both hosts via SSM; the private app host's SSM Agent
#     uses the HTTP Squid proxy. The FREE EC2 Instance Connect Endpoint remains
#     a direct emergency-management path that requires no public ingress.
#   - Route 53 A record api.<public_site_domain> -> proxy Elastic IP
#   - backend deploy job in .github/workflows/deploy.yml: build/push
#     image to ECR, run migrations, then restart compose on the app
#     instance via the management path (no SSH from CI)
#
# Secrets delivery (resolved): keep the existing *_FILE pattern from
# docker-compose.dev.yml. The APP instance bootstrap (user data / deploy
# command, re-run on every deploy) does two fetches using the instance
# role, with the AWS calls riding the egress proxy — the app containers
# never call Secrets Manager/SSM for config themselves:
#   1. Secrets Manager -> /run/flowform/secrets/<NAME>.secret.txt
#      (Flask secret key and Auth0 Management API client secret; tmpfs mount,
#      root-owned 0600 — memory-backed, nothing rests on EBS, gone on reboot
#      until bootstrap re-runs). AWS database connections use IAM auth and do
#      not mount password files.
#   2. SSM get-parameters-by-path /flowform/<scope>/backend/ ->
#      /opt/flowform/backend.env (non-secret FLOWFORM_* config: Auth0
#      IDs, KMS key ARN, linkage secret ARN, SES from-address, logging,
#      DB hosts/names/users/auth modes, image refs, private IPs,
#      HTTP(S)_PROXY/NO_PROXY).
#      Compose is invoked with `--env-file /opt/flowform/backend.env`
#      (interpolation) and the backend service also loads it via `env_file:`
#      (container env).
# See infra/runtime/compose/docker-compose.proxy.yml and docker-compose.app.yml for the
# consuming side: the proxy instance runs Caddy+Squid, and the app instance
# runs only the backend.
#
# Backend AWS calls (boto3 SESv2/KMS/Secrets Manager) use the instance
# role via IMDS and honor HTTPS_PROXY from the environment — AwsSettings'
# static keys are already optional (dev-only).


def _pascal_case(logical_name: str) -> str:
    """Turn a contract logical name into a stable CDK construct id."""
    return "".join(part.capitalize() for part in logical_name.split("_"))


class ApplicationStack(Stack):
    """Public proxy EC2 (Caddy+Squid) + private app EC2 (Flask/Gunicorn)."""

    # Static private addresses. Each host's bootstrap needs the other's IP, so
    # deriving them from the instances would make the two user-data blocks
    # reference each other and form a circular CloudFormation dependency.
    # AWS reserves the first four addresses in a subnet, so .4 is the first
    # assignable one.
    PROXY_PRIVATE_IP = "10.42.0.4"
    APP_PRIVATE_IP = "10.42.1.4"

    # Where the golden image installs the bootstrap scripts and Compose files.
    # Must match install-runtime-assets.sh in the Packer provisioners.
    RUNTIME_ASSET_ROOT = "/opt/flowform/repo"

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
        if env_config.ec2_base_ami_id:
            machine_image = ec2.MachineImage.generic_linux({env_config.region: env_config.ec2_base_ami_id})
        elif env_config.ec2_base_ami_ssm_parameter:
            machine_image = ec2.MachineImage.from_ssm_parameter(
                env_config.ec2_base_ami_ssm_parameter,
                os=ec2.OperatingSystemType.LINUX,
            )
        else:
            raise ValueError(
                f"EnvConfig for '{env_config.env_name}' must provide a Packer-built EC2 base AMI "
                "via ec2_base_ami_id or ec2_base_ami_ssm_parameter"
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
            machine_image=machine_image,
            role=cast(iam.IRole, self.proxy_role),
            security_group=network_stack.proxy_security_group,
            private_ip_address=self.PROXY_PRIVATE_IP,
            http_tokens=ec2.HttpTokens.REQUIRED,
            http_put_response_hop_limit=2,
            block_devices=root_block_devices,
            user_data=self._build_user_data(
                "proxy",
                {
                    "FLOWFORM_SCOPE": env_config.security_scope,
                    "AWS_REGION": env_config.region,
                    "PROXY_PRIVATE_IP": self.PROXY_PRIVATE_IP,
                    "APP_PRIVATE_IP": self.APP_PRIVATE_IP,
                },
            ),
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
            machine_image=machine_image,
            role=task_role,
            security_group=network_stack.app_security_group,
            associate_public_ip_address=False,
            private_ip_address=self.APP_PRIVATE_IP,
            http_tokens=ec2.HttpTokens.REQUIRED,
            http_put_response_hop_limit=2,
            block_devices=root_block_devices,
            user_data=self._build_user_data(
                "app",
                {
                    # Selects the credential strategy: IAM database auth, no
                    # database passwords fetched or written.
                    "FLOWFORM_DEPLOYMENT_TARGET": "aws",
                    "FLOWFORM_SCOPE": env_config.security_scope,
                    "AWS_REGION": env_config.region,
                    "PROXY_PRIVATE_IP": self.PROXY_PRIVATE_IP,
                    "APP_PRIVATE_IP": self.APP_PRIVATE_IP,
                },
            ),
        )
        self.app_instance.node.add_dependency(self.proxy_instance)
        self.app_instance.node.add_dependency(app_ecr_policy)
        self.proxy_instance.node.add_dependency(proxy_ecr_policy)
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

    def _build_user_data(self, host: str, bootstrap_env: dict[str, str]) -> ec2.UserData:
        """Write the host's bootstrap inputs, then run its bootstrap script.

        The bootstrap scripts and Compose files are baked into the golden AMI,
        so user data only supplies the values the image cannot know: the
        deployment target, scope, region, and the two private addresses. There
        is no artifact fetch, so a host needs no network path to begin
        converging.

        Fails closed: `set -euo pipefail` means a host that cannot converge
        stops rather than idling in a half-booted state that looks healthy.
        """
        env_file = f"/etc/flowform/bootstrap-{host}.env"
        bootstrap = f"{self.RUNTIME_ASSET_ROOT}/infra/deployment/bootstrap/bootstrap-{host}.sh"

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -euo pipefail",
            "install -d -m 0755 /etc/flowform",
            f"cat > {env_file} <<'FLOWFORM_ENV'",
            *(f"{key}={value}" for key, value in bootstrap_env.items()),
            "FLOWFORM_ENV",
            f"chmod 0644 {env_file}",
            # Fail with a clear cause if the AMI predates the baked assets,
            # rather than a bare "no such file" from the exec below.
            f"test -x {bootstrap} || {{ echo 'golden AMI has no {host} bootstrap' >&2; exit 1; }}",
            f"set -a; . {env_file}; set +a",
            f"exec {bootstrap}",
        )
        return user_data

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
