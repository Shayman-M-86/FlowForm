import dataclasses
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_route53 as route53
from aws_cdk.assertions import Match, Template

from flowform_infra.config import (
    DOMAIN_NAME,
    Auth0PublicConfig,
    RuntimePublicConfig,
    get_env_config,
    runtime_group_logical_names,
    runtime_parameter_name,
)
from flowform_infra.stacks.application_stack import ApplicationStack
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.registry_stack import RegistryStack

_EMPTY_ENV_DIR = Path(__file__).parent


def _staging_config():
    return dataclasses.replace(
        get_env_config("staging", env_dir=_EMPTY_ENV_DIR),
        auth0_public=Auth0PublicConfig(
            domain="auth.example.test",
            client_id="staging-client",
            audience="https://api.example.test",
        ),
        runtime_public=RuntimePublicConfig(
            auth0_management_domain="tenant.example.test",
            auth0_management_id="management-client",
            email_from_address="no-reply@example.test",
            grafana_cloud_loki_url="https://logs.example.test/loki/api/v1/push",
            grafana_cloud_loki_user="loki-user",
            grafana_cloud_tempo_endpoint="tempo.example.test:443",
            grafana_cloud_tempo_user="tempo-user",
        ),
    )


def _synth_network_stack() -> Template:
    env_config = _staging_config()
    app = cdk.App()
    stack = NetworkStack(
        app,
        "Network",
        env_config=env_config,
        env=cdk.Environment(account=env_config.account, region=env_config.region),
    )
    return Template.from_stack(stack)


def _synth_application_stack() -> Template:
    env_config = _staging_config()
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
    app = cdk.App()

    support = cdk.Stack(app, "Support", env=cdk_env)
    task_role = iam.Role(
        support,
        "TaskRole",
        assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
    )
    kms_key = kms.Key(support, "KmsKey")
    hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
        support,
        "HostedZone",
        hosted_zone_id="Z1234567890ABC",
        zone_name=DOMAIN_NAME,
    )
    image_publisher_role = iam.Role(
        support,
        "ImagePublisherRole",
        assumed_by=iam.AccountRootPrincipal(),
    )

    network = NetworkStack(app, "Network", env_config=env_config, env=cdk_env)
    registry = RegistryStack(
        app,
        "Registry",
        env_config=env_config,
        kms_key=kms_key,
        publisher_role=image_publisher_role,
        env=cdk_env,
    )
    database = DatabaseStack(
        app,
        "Database",
        env_config=env_config,
        network_stack=network,
        kms_key=kms_key,
        env=cdk_env,
    )
    application = ApplicationStack(
        app,
        "Application",
        env_config=env_config,
        network_stack=network,
        registry_stack=registry,
        task_role=task_role,
        kms_key=kms_key,
        database_stack=database,
        linkage_secret_arn="arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/nonprod/linkage",
        observability_secret_arn=(
            "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/nonprod/observability"
        ),
        hosted_zone=hosted_zone,
        env=cdk_env,
    )
    return Template.from_stack(application)


def _backend_parameters() -> dict[str, object]:
    """Return the published backend runtime group keyed by env-var name."""
    resources = _synth_application_stack().find_resources("AWS::SSM::Parameter")
    published: dict[str, object] = {}
    for resource in resources.values():
        name = resource["Properties"]["Name"]
        if isinstance(name, str) and "/backend/" in name:
            published[name.rsplit("/", 1)[-1]] = resource["Properties"]["Value"]
    return published


def test_network_has_no_nat_gateway_and_app_s3_gateway_endpoint():
    template = _synth_network_stack()
    template.resource_count_is("AWS::EC2::NatGateway", 0)
    template.resource_count_is("AWS::EC2::VPCEndpoint", 1)
    template.has_resource_properties(
        "AWS::EC2::VPCEndpoint",
        {
            "VpcEndpointType": "Gateway",
            "ServiceName": {"Fn::Join": ["", ["com.amazonaws.", {"Ref": "AWS::Region"}, ".s3"]]},
            "RouteTableIds": [{"Ref": Match.string_like_regexp("AppIsolatedSubnetARouteTable")}],
            "PolicyDocument": {
                "Statement": [
                    Match.object_like(
                        {
                            "Action": "s3:GetObject",
                            "Resource": "arn:aws:s3:::prod-ap-southeast-2-starport-layer-bucket/*",
                        }
                    )
                ]
            },
        },
    )


def test_network_uses_one_runtime_az_and_a_second_rds_subnet_only():
    template = _synth_network_stack()
    rendered = template.to_json()
    subnets = {
        next(tag["Value"] for tag in resource["Properties"]["Tags"] if tag["Key"] == "Name"): resource["Properties"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::EC2::Subnet"
    }

    assert set(subnets) == {
        "flowform-staging-proxy-public-a",
        "flowform-staging-app-isolated-a",
        "flowform-staging-rds-isolated-a",
        "flowform-staging-rds-isolated-b",
    }
    assert subnets["flowform-staging-proxy-public-a"]["CidrBlock"] == "10.42.0.0/24"
    assert subnets["flowform-staging-app-isolated-a"]["CidrBlock"] == "10.42.1.0/24"
    assert subnets["flowform-staging-rds-isolated-a"]["CidrBlock"] == "10.42.2.0/24"
    assert subnets["flowform-staging-rds-isolated-b"]["CidrBlock"] == "10.42.3.0/24"

    runtime_az = subnets["flowform-staging-proxy-public-a"]["AvailabilityZone"]
    assert subnets["flowform-staging-app-isolated-a"]["AvailabilityZone"] == runtime_az
    assert subnets["flowform-staging-rds-isolated-a"]["AvailabilityZone"] == runtime_az
    assert subnets["flowform-staging-rds-isolated-b"]["AvailabilityZone"] != runtime_az

    template.resource_count_is("AWS::EC2::Route", 1)
    template.has_resource_properties(
        "AWS::EC2::Route",
        {
            "DestinationCidrBlock": "0.0.0.0/0",
            "GatewayId": {"Ref": "InternetGateway"},
            "RouteTableId": {"Ref": Match.string_like_regexp("ProxyPublicSubnetARouteTable")},
        },
    )


def test_network_flow_logs_all_traffic_to_seven_day_cloudwatch_group():
    template = _synth_network_stack()
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/flowform/staging/vpc-flow",
            "RetentionInDays": 7,
        },
    )
    template.has_resource_properties(
        "AWS::EC2::FlowLog",
        {
            "LogDestinationType": "cloud-watch-logs",
            "LogGroupName": {"Ref": Match.string_like_regexp("VpcFlowLogGroup")},
            "MaxAggregationInterval": 600,
            "ResourceType": "VPC",
            "TrafficType": "ALL",
        },
    )


def test_network_private_dns_zone_and_application_records_track_instance_addresses():
    network_template = _synth_network_stack()
    network_template.has_resource_properties(
        "AWS::Route53::HostedZone",
        {
            "Name": "internal.staging.flow-form.com.au.",
            "VPCs": [
                {
                    "VPCId": {"Ref": Match.string_like_regexp("Vpc")},
                    "VPCRegion": "ap-southeast-2",
                }
            ],
        },
    )

    application_template = _synth_application_stack()
    rendered = application_template.to_json()
    records = {
        resource["Properties"]["Name"]: resource["Properties"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::Route53::RecordSet"
    }

    assert {name for name in records if name.endswith(".internal.staging.flow-form.com.au.")} == {
        "app.internal.staging.flow-form.com.au.",
        "proxy.internal.staging.flow-form.com.au.",
    }
    app_target = records["app.internal.staging.flow-form.com.au."]["ResourceRecords"][0]["Fn::GetAtt"]
    proxy_target = records["proxy.internal.staging.flow-form.com.au."]["ResourceRecords"][0]["Fn::GetAtt"]
    assert app_target[0].startswith("AppInstance")
    assert app_target[1] == "PrivateIp"
    assert proxy_target[0].startswith("ProxyInstance")
    assert proxy_target[1] == "PrivateIp"
    assert {record["TTL"] for record in records.values()} == {"60"}
    assert {record["Type"] for record in records.values()} == {"A"}

    public_api = records["api.staging.flow-form.com.au."]
    assert public_api["HostedZoneId"] == "Z1234567890ABC"
    assert public_api["ResourceRecords"][0]["Ref"].startswith("ProxyElasticIp")


def test_proxy_security_group_public_http_https_only_and_squid_from_app_only():
    template = _synth_network_stack()
    template.has_resource_properties(
        "AWS::EC2::SecurityGroup",
        {
            "GroupDescription": "Public proxy EC2: Caddy ingress and Squid egress gateway",
            "SecurityGroupIngress": Match.array_with(
                [
                    Match.object_like({"CidrIp": "0.0.0.0/0", "FromPort": 80, "ToPort": 80}),
                    Match.object_like({"CidrIp": "0.0.0.0/0", "FromPort": 443, "ToPort": 443}),
                ]
            ),
        },
    )
    template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        Match.object_like(
            {
                "Description": "App to Squid forward proxy",
                "FromPort": 3128,
                "SourceSecurityGroupId": Match.any_value(),
                "ToPort": 3128,
            }
        ),
    )
    for description, port in (
        ("App Alloy to proxy Loki gateway", 3500),
        ("App Alloy to proxy OTLP gateway", 4317),
    ):
        template.has_resource_properties(
            "AWS::EC2::SecurityGroupIngress",
            Match.object_like(
                {
                    "Description": description,
                    "FromPort": port,
                    "SourceSecurityGroupId": Match.any_value(),
                    "ToPort": port,
                }
            ),
        )


def test_app_and_rds_security_group_sources_are_locked_to_peer_groups():
    template = _synth_network_stack()
    template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        Match.object_like(
            {
                "Description": "Proxy to app backend",
                "FromPort": 5000,
                "SourceSecurityGroupId": Match.any_value(),
                "ToPort": 5000,
            }
        ),
    )
    for description, port in (
        ("App HTTPS proxy egress through Squid", 3128),
        ("App logs to proxy Alloy gateway", 3500),
        ("App traces to proxy Alloy gateway", 4317),
        ("App PostgreSQL to RDS", 5432),
    ):
        template.has_resource_properties(
            "AWS::EC2::SecurityGroupEgress",
            Match.object_like(
                {
                    "Description": description,
                    "DestinationSecurityGroupId": Match.any_value(),
                    "FromPort": port,
                    "ToPort": port,
                }
            ),
        )

    rendered = template.to_json()
    public_ingress = []
    public_egress = []
    for resource in rendered["Resources"].values():
        properties = resource.get("Properties", {})
        if resource["Type"] == "AWS::EC2::SecurityGroup":
            public_ingress.extend(
                rule for rule in properties.get("SecurityGroupIngress", []) if rule.get("CidrIp") == "0.0.0.0/0"
            )
            public_egress.extend(
                rule for rule in properties.get("SecurityGroupEgress", []) if rule.get("CidrIp") == "0.0.0.0/0"
            )
        elif resource["Type"] == "AWS::EC2::SecurityGroupIngress" and properties.get("CidrIp") == "0.0.0.0/0":
            public_ingress.append(properties)
        elif resource["Type"] == "AWS::EC2::SecurityGroupEgress" and properties.get("CidrIp") == "0.0.0.0/0":
            public_egress.append(properties)

    assert {(rule["Description"], rule["FromPort"], rule["ToPort"]) for rule in public_ingress} == {
        ("Public HTTP to Caddy", 80, 80),
        ("Public HTTPS to Caddy", 443, 443),
    }
    assert {(rule["Description"], rule["FromPort"], rule["ToPort"]) for rule in public_egress} == {
        ("Proxy HTTPS egress for ACME, Route53, ECR, and Squid allow-list", 443, 443)
    }


def test_network_management_path_is_one_eice_in_the_app_subnet():
    template = _synth_network_stack()
    template.resource_count_is("AWS::EC2::InstanceConnectEndpoint", 1)
    template.has_resource_properties(
        "AWS::EC2::InstanceConnectEndpoint",
        {
            "PreserveClientIp": False,
            "SecurityGroupIds": Match.any_value(),
            "SubnetId": {"Ref": Match.string_like_regexp("AppIsolatedSubnetASubnet")},
        },
    )
    template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        Match.object_like(
            {
                "Description": "EICE SSH to app",
                "FromPort": 22,
                "SourceSecurityGroupId": Match.any_value(),
                "ToPort": 22,
            }
        ),
    )
    template.has_resource_properties(
        "AWS::EC2::SecurityGroupEgress",
        Match.object_like(
            {
                "Description": "App HTTPS to S3 gateway endpoint",
                "DestinationPrefixListId": Match.any_value(),
                "FromPort": 443,
                "ToPort": 443,
            }
        ),
    )
    template.has_resource_properties(
        "AWS::EC2::SecurityGroupIngress",
        Match.object_like(
            {
                "Description": "App PostgreSQL to RDS",
                "FromPort": 5432,
                "SourceSecurityGroupId": Match.any_value(),
                "ToPort": 5432,
            }
        ),
    )


def test_app_instance_has_no_public_ip_and_both_instances_require_imdsv2_hop_limit_two():
    template = _synth_application_stack()
    template.resource_properties_count_is(
        "AWS::EC2::Instance",
        {"MetadataOptions": {"HttpTokens": "required", "HttpPutResponseHopLimit": 2}},
        2,
    )
    template.has_resource_properties(
        "AWS::EC2::Instance",
        {
            "NetworkInterfaces": [Match.object_like({"AssociatePublicIpAddress": False})],
            "Tags": Match.array_with([{"Key": "Name", "Value": "flowform-staging-app"}]),
        },
    )
    template.has_resource_properties("AWS::EC2::EIP", {"Domain": "vpc"})


def test_proxy_role_has_hosted_zone_scoped_route53_change_access():
    template = _synth_application_stack()
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": [
                                    "route53:ChangeResourceRecordSets",
                                    "route53:ListResourceRecordSets",
                                ],
                                "Resource": "arn:aws:route53:::hostedzone/Z1234567890ABC",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_proxy_role_can_read_only_the_observability_secret():
    template = _synth_application_stack()
    rendered = str(template.to_json())
    assert "flowform/nonprod/observability" in rendered
    assert "secretsmanager:GetSecretValue" in rendered
    assert "secretsmanager:DescribeSecret" in rendered
    assert "secret:flowform/nonprod/app-secrets" not in rendered


def test_proxy_role_can_read_only_its_runtime_parameter_path():
    template = _synth_application_stack()
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        {
                            "Action": "ssm:GetParametersByPath",
                            "Effect": "Allow",
                            "Resource": Match.any_value(),
                        }
                    ]
                )
            }
        },
    )

    statements = [
        statement
        for resource in template.to_json()["Resources"].values()
        if resource["Type"] == "AWS::IAM::Policy"
        for statement in resource["Properties"]["PolicyDocument"]["Statement"]
        if statement["Action"] == "ssm:GetParametersByPath"
    ]
    assert len(statements) == 1
    rendered_resource = str(statements[0]["Resource"])
    assert "parameter/flowform/nonprod/proxy/*" in rendered_resource
    assert "parameter/flowform/nonprod/*" not in rendered_resource


def test_application_ecr_pulls_are_scoped_to_exact_host_repositories():
    template = _synth_application_stack()
    rendered = template.to_json()
    policies = {
        resource["Properties"]["PolicyName"]: resource["Properties"]["PolicyDocument"]["Statement"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::IAM::Policy"
        and resource["Properties"]["PolicyName"].startswith(("AppEcrPullPolicy", "ProxyEcrPullPolicy"))
    }

    assert len(policies) == 2
    assert "repository/flowform-staging-*" not in str(policies)

    app_statements = next(value for key, value in policies.items() if key.startswith("AppEcrPullPolicy"))
    proxy_statements = next(value for key, value in policies.items() if key.startswith("ProxyEcrPullPolicy"))
    app_resources = app_statements[1]["Resource"]
    proxy_resources = proxy_statements[1]["Resource"]

    assert len(app_resources) == 2
    assert "BackendRepository" in str(app_resources)
    assert "AlloyRepository" in str(app_resources)
    assert "CaddyRepository" not in str(app_resources)
    assert "SquidRepository" not in str(app_resources)

    assert len(proxy_resources) == 3
    assert "CaddyRepository" in str(proxy_resources)
    assert "SquidRepository" in str(proxy_resources)
    assert "AlloyRepository" in str(proxy_resources)
    assert "BackendRepository" not in str(proxy_resources)


def test_application_instances_use_packer_ami_ssm_parameter_not_latest_base_image():
    template = _synth_application_stack()
    rendered = template.to_json()
    ami_parameters = {
        logical_id: value
        for logical_id, value in rendered["Parameters"].items()
        if value.get("Type") == "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>"
    }

    assert len(ami_parameters) == 1
    parameter_logical_id, parameter = next(iter(ami_parameters.items()))
    assert parameter["Default"] == "/flowform/staging/ec2/baseAmiId"

    instance_image_ids = [
        resource["Properties"]["ImageId"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::EC2::Instance"
    ]
    assert instance_image_ids == [{"Ref": parameter_logical_id}] * 2


def test_application_instances_use_ten_gib_gp3_encrypted_root_volumes():
    template = _synth_application_stack()
    template.resource_properties_count_is(
        "AWS::EC2::Instance",
        {
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": True,
                        "Encrypted": True,
                        "VolumeSize": 10,
                        "VolumeType": "gp3",
                    },
                }
            ]
        },
        2,
    )


def test_backend_parameters_are_published_under_the_contract_path():
    """Bootstrap reads /flowform/<scope>/backend/ and renders KEY=value lines."""
    template = _synth_application_stack()
    template.has_resource_properties(
        "AWS::SSM::Parameter",
        {
            "Name": "/flowform/nonprod/backend/DATABASE_CORE_AUTH_MODE",
            "Value": "iam",
        },
    )
    template.has_resource_properties(
        "AWS::SSM::Parameter",
        {
            "Name": "/flowform/nonprod/backend/DATABASE_RESPONSE_AUTH_MODE",
            "Value": "iam",
        },
    )


def test_proxy_runtime_parameters_include_domain_and_observability_routes():
    template = _synth_application_stack()
    expected = {
        "API_DOMAIN": "api.staging.flow-form.com.au",
        "FLOWFORM_ENV": "prod",
        "GRAFANA_CLOUD_LOKI_URL": "https://logs.example.test/loki/api/v1/push",
        "GRAFANA_CLOUD_LOKI_USER": "loki-user",
        "GRAFANA_CLOUD_TEMPO_ENDPOINT": "tempo.example.test:443",
        "GRAFANA_CLOUD_TEMPO_USER": "tempo-user",
    }
    resources = template.find_resources("AWS::SSM::Parameter")
    actual = {
        resource["Properties"]["Name"].rsplit("/", 1)[-1]: resource["Properties"]["Value"]
        for resource in resources.values()
        if "/proxy/" in resource["Properties"]["Name"]
    }
    assert actual == expected


def test_published_backend_parameters_are_all_declared_in_the_contract():
    """A parameter name outside the contract would never reach backend.env."""
    contract_env_names = {
        name.rsplit("/", 1)[-1]
        for logical in runtime_group_logical_names("backend")
        for name in [runtime_parameter_name("nonprod", "backend", logical)]
    }
    assert set(_backend_parameters()) <= contract_env_names


def test_staging_backend_runs_as_prod_with_iam_database_auth():
    """Staging is production-shaped, so FLOWFORM_ENV is prod."""
    published = _backend_parameters()
    assert published["FLOWFORM_ENV"] == "prod"
    assert published["DATABASE_CORE_APP_USER"] == "flowform_core_app"
    assert published["DATABASE_RESPONSE_APP_USER"] == "flowform_response_app"
    assert published["DATABASE_CORE_NAME"] == "flowform_core"
    assert published["DATABASE_RESPONSE_NAME"] == "flowform_response"


def test_no_database_password_parameter_is_published():
    """Under IAM auth no database credential exists to publish."""
    published = _backend_parameters()
    assert not any("PASSWORD" in name for name in published)


def test_cors_origins_are_explicit_json_for_staging():
    """The backend parses this as a JSON list; wildcards are rejected in prod."""
    origins = _backend_parameters()["FLOWFORM_CORS_ORIGINS"]
    assert isinstance(origins, str)
    assert "*" not in origins
    assert "https://studio.staging." in origins


def _user_data(instance_logical_prefix: str) -> str:
    """Return one instance's user data as a flattened string."""
    resources = _synth_application_stack().find_resources("AWS::EC2::Instance")
    for logical_id, resource in resources.items():
        if not logical_id.startswith(instance_logical_prefix):
            continue
        encoded = resource["Properties"]["UserData"]["Fn::Base64"]
        # A script with no CloudFormation references renders as a plain
        # string; one with references renders as an Fn::Join of fragments.
        if isinstance(encoded, str):
            return encoded
        parts = encoded["Fn::Join"][1]
        return "".join(part for part in parts if isinstance(part, str))
    raise AssertionError(f"no instance matching {instance_logical_prefix}")


def test_app_user_data_selects_the_aws_deployment_target():
    """Bootstrap branches its credential strategy on this value."""
    assert "FLOWFORM_DEPLOYMENT_TARGET=aws" in _user_data("AppInstance")


def test_proxy_user_data_does_not_set_a_deployment_target():
    """Only the app bootstrap consumes the deployment target."""
    assert "FLOWFORM_DEPLOYMENT_TARGET" not in _user_data("ProxyInstance")


def test_user_data_execs_the_baked_bootstrap_without_fetching_anything():
    """The scripts are baked into the AMI, so nothing is downloaded at boot."""
    for prefix, host in (("AppInstance", "app"), ("ProxyInstance", "proxy")):
        script = _user_data(prefix)
        assert f"{ApplicationStack.RUNTIME_ASSET_ROOT}/infra/deployment/bootstrap/bootstrap-{host}.sh" in script
        assert "set -euo pipefail" in script
        assert "aws s3 cp" not in script
        assert "tar -xzf" not in script


def test_user_data_passes_both_static_private_ips():
    """Each host needs the other's address; static IPs avoid a CFN cycle."""
    for prefix in ("AppInstance", "ProxyInstance"):
        script = _user_data(prefix)
        assert f"PROXY_PRIVATE_IP={ApplicationStack.PROXY_PRIVATE_IP}" in script
        assert f"APP_PRIVATE_IP={ApplicationStack.APP_PRIVATE_IP}" in script


def test_instances_use_the_static_private_addresses():
    """The two hosts must hold exactly the addresses user data hardcodes."""
    resources = _synth_application_stack().find_resources("AWS::EC2::Instance")
    assigned = set()
    for resource in resources.values():
        properties = resource["Properties"]
        if "PrivateIpAddress" in properties:
            assigned.add(properties["PrivateIpAddress"])
        else:
            # Suppressing a public IP forces the address onto an explicit
            # network interface instead of the top-level property.
            assigned.add(properties["NetworkInterfaces"][0]["PrivateIpAddress"])

    assert assigned == {
        ApplicationStack.PROXY_PRIVATE_IP,
        ApplicationStack.APP_PRIVATE_IP,
    }
