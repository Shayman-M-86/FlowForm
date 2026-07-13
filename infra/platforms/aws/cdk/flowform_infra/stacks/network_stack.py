from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct

from flowform_infra.config import EnvConfig


class NetworkStack(Stack):
    """VPC, subnets, endpoints, and security groups for the split EC2 runtime."""

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.42.0.0/16"),
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="proxy-public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="app-isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="rds-isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        self.proxy_subnets = ec2.SubnetSelection(subnet_group_name="proxy-public")
        self.app_subnets = ec2.SubnetSelection(subnet_group_name="app-isolated")
        self.rds_subnets = ec2.SubnetSelection(subnet_group_name="rds-isolated")

        self.proxy_security_group = ec2.SecurityGroup(
            self,
            "ProxySecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=False,
            description="Public proxy EC2: Caddy ingress and Squid egress gateway",
        )
        self.app_security_group = ec2.SecurityGroup(
            self,
            "AppSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=False,
            description="Private app EC2: backend only, no direct internet egress",
        )
        self.rds_security_group = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=False,
            description="RDS PostgreSQL access from private app EC2 only",
        )
        self.eice_security_group = ec2.SecurityGroup(
            self,
            "EiceSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=False,
            description="EC2 Instance Connect Endpoint access to private app EC2",
        )

        self.proxy_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Public HTTP to Caddy",
        )
        self.proxy_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Public HTTPS to Caddy",
        )
        self.proxy_security_group.add_ingress_rule(
            self.app_security_group,
            ec2.Port.tcp(3128),
            "App to Squid forward proxy",
        )

        self.proxy_security_group.add_egress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Proxy HTTPS egress for ACME, Route53, ECR, and Squid allow-list",
        )
        self.proxy_security_group.add_egress_rule(
            self.app_security_group,
            ec2.Port.tcp(5000),
            "Proxy to app backend",
        )

        self.app_security_group.add_ingress_rule(
            self.proxy_security_group,
            ec2.Port.tcp(5000),
            "Proxy to app backend",
        )
        self.app_security_group.add_ingress_rule(
            self.eice_security_group,
            ec2.Port.tcp(22),
            "EICE SSH to app",
        )

        self.app_security_group.add_egress_rule(
            self.proxy_security_group,
            ec2.Port.tcp(3128),
            "App HTTPS proxy egress through Squid",
        )
        self.app_security_group.add_egress_rule(
            self.rds_security_group,
            ec2.Port.tcp(5432),
            "App PostgreSQL to RDS",
        )
        self.s3_prefix_list = ec2.PrefixList.from_lookup(
            self,
            "S3PrefixList",
            prefix_list_name=f"com.amazonaws.{env_config.region}.s3",
        )
        self.app_security_group.add_egress_rule(
            self.s3_prefix_list,
            ec2.Port.tcp(443),
            "App HTTPS to S3 gateway endpoint",
        )
        self.app_security_group.add_egress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(53),
            "App DNS TCP to VPC resolver path",
        )
        self.app_security_group.add_egress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.udp(53),
            "App DNS UDP to VPC resolver path",
        )
        self.app_security_group.add_egress_rule(
            ec2.Peer.ipv4("169.254.169.123/32"),
            ec2.Port.udp(123),
            "App NTP to Amazon Time Sync",
        )

        self.rds_security_group.add_ingress_rule(
            self.app_security_group,
            ec2.Port.tcp(5432),
            "App PostgreSQL to RDS",
        )

        self.eice_security_group.add_egress_rule(
            self.app_security_group,
            ec2.Port.tcp(22),
            "EICE SSH to app",
        )

        self.s3_gateway_endpoint = self.vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[self.app_subnets],
        )
        self.s3_gateway_endpoint.add_to_policy(
            iam.PolicyStatement(
                principals=[iam.AnyPrincipal()],
                actions=["s3:GetObject"],
                resources=[f"arn:aws:s3:::prod-{env_config.region}-starport-layer-bucket/*"],
            )
        )

        selected_app_subnet = self.vpc.select_subnets(subnet_group_name="app-isolated").subnet_ids[0]
        self.eice_endpoint = ec2.CfnInstanceConnectEndpoint(
            self,
            "AppInstanceConnectEndpoint",
            subnet_id=selected_app_subnet,
            preserve_client_ip=False,
            security_group_ids=[self.eice_security_group.security_group_id],
        )
