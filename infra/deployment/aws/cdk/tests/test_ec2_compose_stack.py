from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_route53 as route53
from aws_cdk.assertions import Match, Template

from flowform_infra.config import DOMAIN_NAME, get_env_config
from flowform_infra.stacks.application_stack import ApplicationStack
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.registry_stack import RegistryStack

_EMPTY_ENV_DIR = Path(__file__).parent


def _staging_config():
    return get_env_config("staging", env_dir=_EMPTY_ENV_DIR)


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
    application = ApplicationStack(
        app,
        "Application",
        env_config=env_config,
        network_stack=network,
        registry_stack=registry,
        task_role=task_role,
        kms_key=kms_key,
        hosted_zone=hosted_zone,
        env=cdk_env,
    )
    return Template.from_stack(application)


def test_network_has_no_nat_gateway_and_app_s3_gateway_endpoint():
    template = _synth_network_stack()
    template.resource_count_is("AWS::EC2::NatGateway", 0)
    template.has_resource_properties(
        "AWS::EC2::VPCEndpoint",
        {
            "VpcEndpointType": "Gateway",
            "ServiceName": {"Fn::Join": ["", ["com.amazonaws.", {"Ref": "AWS::Region"}, ".s3"]]},
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
