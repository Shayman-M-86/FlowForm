from aws_cdk import Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_route53 as route53
from constructs import Construct

from flowform_infra.config import EnvConfig


class NetworkStack(Stack):
    """VPC, subnets, endpoints, and security groups for the split EC2 runtime."""

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        if env_config.private_dns_zone is None:
            raise ValueError(f"EnvConfig for '{env_config.env_name}' must define private_dns_zone")

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.42.0.0/16"),
            max_azs=2,
            nat_gateways=0,
            create_internet_gateway=False,
            subnet_configuration=[],
        )

        self.internet_gateway = ec2.CfnInternetGateway(self, "InternetGateway")
        self.internet_gateway_attachment = ec2.CfnVPCGatewayAttachment(
            self,
            "InternetGatewayAttachment",
            vpc_id=self.vpc.vpc_id,
            internet_gateway_id=self.internet_gateway.ref,
        )

        az_a, az_b = self.vpc.availability_zones
        self.proxy_subnet = ec2.PublicSubnet(
            self,
            "ProxyPublicSubnetA",
            vpc_id=self.vpc.vpc_id,
            availability_zone=az_a,
            cidr_block="10.42.0.0/24",
            map_public_ip_on_launch=False,
        )
        self.proxy_subnet.add_default_internet_route(
            self.internet_gateway.ref,
            self.internet_gateway_attachment,
        )
        self.app_subnet = ec2.PrivateSubnet(
            self,
            "AppIsolatedSubnetA",
            vpc_id=self.vpc.vpc_id,
            availability_zone=az_a,
            cidr_block="10.42.1.0/24",
        )
        self.rds_subnet_a = ec2.PrivateSubnet(
            self,
            "RdsIsolatedSubnetA",
            vpc_id=self.vpc.vpc_id,
            availability_zone=az_a,
            cidr_block="10.42.2.0/24",
        )
        self.rds_subnet_b = ec2.PrivateSubnet(
            self,
            "RdsIsolatedSubnetB",
            vpc_id=self.vpc.vpc_id,
            availability_zone=az_b,
            cidr_block="10.42.3.0/24",
        )
        Tags.of(self.proxy_subnet).add("Name", f"flowform-{env_config.env_name}-proxy-public-a")
        Tags.of(self.app_subnet).add("Name", f"flowform-{env_config.env_name}-app-isolated-a")
        Tags.of(self.rds_subnet_a).add("Name", f"flowform-{env_config.env_name}-rds-isolated-a")
        Tags.of(self.rds_subnet_b).add("Name", f"flowform-{env_config.env_name}-rds-isolated-b")

        self.proxy_subnets = ec2.SubnetSelection(subnets=[self.proxy_subnet])
        self.app_subnets = ec2.SubnetSelection(subnets=[self.app_subnet])
        self.rds_subnets = ec2.SubnetSelection(subnets=[self.rds_subnet_a, self.rds_subnet_b])

        self.flow_log_group = logs.LogGroup(
            self,
            "VpcFlowLogGroup",
            log_group_name=f"/flowform/{env_config.env_name}/vpc-flow",
            retention=env_config.vpc_flow_log_retention,
            removal_policy=env_config.removal_policy,
        )
        self.vpc_flow_log = ec2.FlowLog(
            self,
            "VpcFlowLog",
            resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc),
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(self.flow_log_group),
            traffic_type=ec2.FlowLogTrafficType.ALL,
            max_aggregation_interval=ec2.FlowLogMaxAggregationInterval.TEN_MINUTES,
            flow_log_name=f"flowform-{env_config.env_name}-vpc",
        )

        self.private_hosted_zone = route53.PrivateHostedZone(
            self,
            "PrivateHostedZone",
            zone_name=env_config.private_dns_zone,
            vpc=self.vpc,
            comment=f"FlowForm {env_config.env_name} private host discovery",
        )
        self.proxy_private_dns_name = f"proxy.{env_config.private_dns_zone}"
        self.app_private_dns_name = f"app.{env_config.private_dns_zone}"

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
        self.proxy_security_group.add_ingress_rule(
            self.app_security_group,
            ec2.Port.tcp(3500),
            "App Alloy to proxy Loki gateway",
        )
        self.proxy_security_group.add_ingress_rule(
            self.app_security_group,
            ec2.Port.tcp(4317),
            "App Alloy to proxy OTLP gateway",
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
        self.proxy_security_group.add_egress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(53),
            "Proxy DNS TCP to VPC resolver path",
        )
        self.proxy_security_group.add_egress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.udp(53),
            "Proxy DNS UDP to VPC resolver path",
        )
        self.proxy_security_group.add_egress_rule(
            ec2.Peer.ipv4("169.254.169.123/32"),
            ec2.Port.udp(123),
            "Proxy NTP to Amazon Time Sync",
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
            self.proxy_security_group,
            ec2.Port.tcp(3500),
            "App logs to proxy Alloy gateway",
        )
        self.app_security_group.add_egress_rule(
            self.proxy_security_group,
            ec2.Port.tcp(4317),
            "App traces to proxy Alloy gateway",
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

        self.eice_endpoint = ec2.CfnInstanceConnectEndpoint(
            self,
            "AppInstanceConnectEndpoint",
            subnet_id=self.app_subnet.subnet_id,
            preserve_client_ip=False,
            security_group_ids=[self.eice_security_group.security_group_id],
        )
