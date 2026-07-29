# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
from functools import lru_cache
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk.assertions import Match, Template

from flowform_infra.config import get_env_config
from flowform_infra.stacks.database_bootstrap_stack import DatabaseBootstrapStack
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack

_EMPTY_ENV_DIR = Path(__file__).parent


@lru_cache
def _synth_bootstrap_stack() -> Template:
    env_config = get_env_config("staging", env_dir=_EMPTY_ENV_DIR)
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
    app = cdk.App()

    support = cdk.Stack(app, "Support", env=cdk_env)
    database_key = kms.Key(support, "DatabaseKey")
    task_role = iam.Role(
        support,
        "AppTaskRole",
        assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
    )
    network = NetworkStack(app, "Network", env_config=env_config, env=cdk_env)
    database = DatabaseStack(
        app,
        "Database",
        env_config=env_config,
        network_stack=network,
        kms_key=database_key,
        task_role=task_role,
        env=cdk_env,
    )
    bootstrap = DatabaseBootstrapStack(
        app,
        "DatabaseBootstrap",
        env_config=env_config,
        network_stack=network,
        database_stack=database,
        kms_key=database_key,
        env=cdk_env,
    )
    return Template.from_stack(bootstrap)


def test_bootstrap_stack_has_one_operator_invoked_vpc_lambda():
    template = _synth_bootstrap_stack()
    template.resource_count_is("AWS::Lambda::Function", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "FunctionName": "flowform-staging-database-bootstrap",
            "PackageType": "Image",
            "Timeout": 600,
            "Environment": {
                "Variables": {
                    "BOOTSTRAP_CHECKSUM": Match.string_like_regexp("[0-9a-f]{64}"),
                    "BOOTSTRAP_VERSION": "3",
                    "DATABASE_HOST": Match.object_like(
                        {"Fn::ImportValue": Match.string_like_regexp("DatabaseEndpointAddress")}
                    ),
                    "DATABASE_PORT": "5432",
                    "DATABASE_SECRET_ARN": Match.any_value(),
                }
            },
            "VpcConfig": {
                "SecurityGroupIds": [Match.any_value()],
                "SubnetIds": [Match.object_like({"Fn::ImportValue": Match.string_like_regexp("AppIsolatedSubnetA")})],
            },
        },
    )
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/flowform/staging/database-bootstrap",
            "RetentionInDays": 7,
        },
    )


def test_bootstrap_stack_is_not_a_cloudformation_database_gate():
    template = _synth_bootstrap_stack()
    template.resource_count_is("AWS::RDS::DBInstance", 0)
    template.resource_count_is("AWS::EC2::VPCEndpoint", 0)
    template.resource_count_is("AWS::StepFunctions::StateMachine", 0)
    template.resource_count_is("AWS::SSM::Parameter", 0)
    assert not any(resource["Type"].startswith("Custom::") for resource in template.to_json()["Resources"].values())


def test_bootstrap_networking_uses_dedicated_security_group_references():
    template = _synth_bootstrap_stack()
    template.resource_count_is("AWS::EC2::SecurityGroup", 2)
    rendered = template.to_json()

    ingress_rules = [
        resource["Properties"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::EC2::SecurityGroupIngress"
    ]
    assert len(ingress_rules) == 2
    assert {rule["FromPort"] for rule in ingress_rules} == {443, 5432}
    assert all("SourceSecurityGroupId" in rule for rule in ingress_rules)
    assert all("CidrIp" not in rule for rule in ingress_rules)

    egress_rules = [
        resource["Properties"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::EC2::SecurityGroupEgress"
    ]
    assert len(egress_rules) == 2
    assert {rule["FromPort"] for rule in egress_rules} == {443, 5432}
    assert all("DestinationSecurityGroupId" in rule for rule in egress_rules)
    assert all("CidrIp" not in rule for rule in egress_rules)


def test_bootstrap_role_can_read_only_the_managed_database_secret():
    template = _synth_bootstrap_stack()
    rendered = template.to_json()
    statements = [
        statement
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::IAM::Policy"
        for statement in resource["Properties"]["PolicyDocument"]["Statement"]
    ]

    secret_reads = [statement for statement in statements if statement["Action"] == "secretsmanager:GetSecretValue"]
    assert len(secret_reads) == 1
    assert "MasterUserSecret" in str(secret_reads[0]["Resource"])
    actions: set[str] = set()
    for statement in statements:
        statement_actions = statement["Action"]
        actions.update(statement_actions if isinstance(statement_actions, list) else [statement_actions])
    assert actions.isdisjoint({"ec2:CreateVpcEndpoint", "ec2:DeleteVpcEndpoints"})

    ec2_denies = [
        statement
        for statement in statements
        if statement["Effect"] == "Deny" and "ec2:CreateNetworkInterface" in statement["Action"]
    ]
    assert len(ec2_denies) == 1
    assert ec2_denies[0]["Resource"] == "*"
    condition = ec2_denies[0]["Condition"]["ArnEquals"]
    assert set(condition) == {"lambda:SourceFunctionArn"}
    assert "function:flowform-staging-database-bootstrap" in str(condition["lambda:SourceFunctionArn"])


def test_bootstrap_stack_outputs_non_secret_operator_inputs():
    outputs = _synth_bootstrap_stack().to_json()["Outputs"]
    assert set(outputs) == {
        "BootstrapChecksum",
        "BootstrapEndpointSecurityGroupId",
        "BootstrapEndpointServiceName",
        "BootstrapFunctionName",
        "BootstrapLogGroupName",
        "BootstrapSubnetId",
        "BootstrapVersion",
        "BootstrapVpcId",
    }
    assert outputs["BootstrapVersion"]["Value"] == "3"
    assert len(outputs["BootstrapChecksum"]["Value"]) == 64
    assert outputs["BootstrapEndpointServiceName"]["Value"] == "com.amazonaws.ap-southeast-2.secretsmanager"


def test_bootstrap_checksum_includes_the_authoritative_schema_snapshots(tmp_path):
    bootstrap_path = tmp_path / "bootstrap"
    database_init_path = tmp_path / "database_init"
    aws_path = database_init_path / "aws"
    schema_path = database_init_path / "schema"
    bootstrap_path.mkdir()
    aws_path.mkdir(parents=True)
    schema_path.mkdir()

    (bootstrap_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (bootstrap_path / "requirements.txt").write_text("", encoding="utf-8")
    (bootstrap_path / "handler.py").write_text("def handler(): pass\n", encoding="utf-8")
    (aws_path / "roles.sql").write_text("SELECT 1;\n", encoding="utf-8")
    core_schema = schema_path / "flowform_core_db_schema_v4.sql"
    response_schema = schema_path / "flowform_response_db_schema_v4.sql"
    core_schema.write_text("CREATE TABLE core_table (id bigint);\n", encoding="utf-8")
    response_schema.write_text(
        "CREATE TABLE response_table (id bigint);\n",
        encoding="utf-8",
    )

    initial_checksum = DatabaseBootstrapStack._bootstrap_checksum(
        bootstrap_path,
        database_init_path,
    )
    core_schema.write_text(
        "CREATE TABLE changed_core_table (id bigint);\n",
        encoding="utf-8",
    )
    changed_checksum = DatabaseBootstrapStack._bootstrap_checksum(
        bootstrap_path,
        database_init_path,
    )

    assert changed_checksum != initial_checksum
