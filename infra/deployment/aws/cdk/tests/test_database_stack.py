from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_kms as kms
from aws_cdk.assertions import Match, Template

from flowform_infra.config import get_env_config
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack

_EMPTY_ENV_DIR = Path(__file__).parent


@lru_cache
def _synth_database_stack(env_name: str = "staging") -> Template:
    env_config = get_env_config(env_name, env_dir=_EMPTY_ENV_DIR)
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
    app = cdk.App()

    support = cdk.Stack(app, "Support", env=cdk_env)
    database_key = kms.Key(support, "DatabaseKey")
    network = NetworkStack(app, "Network", env_config=env_config, env=cdk_env)
    database = DatabaseStack(
        app,
        "Database",
        env_config=env_config,
        network_stack=network,
        kms_key=database_key,
        env=cdk_env,
    )
    return Template.from_stack(database)


def _database_resource(env_name: str = "staging") -> Mapping[str, Any]:
    resources = _synth_database_stack(env_name).find_resources("AWS::RDS::DBInstance")
    assert len(resources) == 1
    return next(iter(resources.values()))


def test_staging_database_is_private_single_az_postgresql_17_9():
    template = _synth_database_stack()
    template.resource_count_is("AWS::RDS::DBInstance", 1)
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "DBInstanceIdentifier": "flowform-staging-postgres",
            "Engine": "postgres",
            "EngineVersion": "17.9",
            "DBInstanceClass": "db.t4g.small",
            "AvailabilityZone": Match.any_value(),
            "MultiAZ": False,
            "NetworkType": "IPV4",
            "Port": "5432",
            "PubliclyAccessible": False,
            "VPCSecurityGroups": [Match.any_value()],
        },
    )


def test_staging_database_uses_only_the_two_isolated_rds_subnets():
    template = _synth_database_stack()
    template.resource_count_is("AWS::RDS::DBSubnetGroup", 1)
    template.has_resource_properties(
        "AWS::RDS::DBSubnetGroup",
        {
            "DBSubnetGroupDescription": "FlowForm staging isolated RDS subnets",
            "DBSubnetGroupName": "flowform-staging-rds",
            "SubnetIds": [
                Match.object_like({"Fn::ImportValue": Match.string_like_regexp("RdsIsolatedSubnetA")}),
                Match.object_like({"Fn::ImportValue": Match.string_like_regexp("RdsIsolatedSubnetB")}),
            ],
        },
    )

    database = _database_resource()["Properties"]
    assert database["DBSubnetGroupName"] == {"Ref": "DatabaseSubnetGroup"}
    assert len(database["VPCSecurityGroups"]) == 1
    assert "RdsSecurityGroup" in str(database["VPCSecurityGroups"][0])


def test_staging_database_encrypts_gp3_storage_and_bounds_autoscaling():
    template = _synth_database_stack()
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "AllocatedStorage": "20",
            "MaxAllocatedStorage": 40,
            "StorageType": "gp3",
            "StorageEncrypted": True,
            "KmsKeyId": Match.any_value(),
        },
    )


def test_rds_manages_the_master_password_with_the_flowform_key():
    template = _synth_database_stack()
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "MasterUsername": "flowform_admin",
            "ManageMasterUserPassword": True,
            "MasterUserSecret": {"KmsKeyId": Match.any_value()},
        },
    )
    template.resource_count_is("AWS::SecretsManager::Secret", 0)
    assert "MasterUserPassword" not in _database_resource()["Properties"]


def test_parameter_group_requires_tls_and_scram():
    template = _synth_database_stack()
    template.resource_count_is("AWS::RDS::DBParameterGroup", 1)
    template.has_resource_properties(
        "AWS::RDS::DBParameterGroup",
        {
            "Family": "postgres17",
            "Parameters": {
                "rds.force_ssl": "1",
                "password_encryption": "scram-sha-256",
                "rds.accepted_password_auth_method": "scram-sha-256",
            },
        },
    )
    assert _database_resource()["Properties"]["DBParameterGroupName"] == {"Ref": "DatabaseParameterGroup"}


def test_staging_database_has_seven_day_backups_logs_and_standard_insights():
    template = _synth_database_stack()
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "BackupRetentionPeriod": 7,
            "CopyTagsToSnapshot": True,
            "DeleteAutomatedBackups": False,
            "PreferredBackupWindow": "16:00-16:30",
            "PreferredMaintenanceWindow": "sun:17:00-sun:18:00",
            "EnableCloudwatchLogsExports": ["postgresql", "upgrade"],
            "DatabaseInsightsMode": "standard",
            "EnablePerformanceInsights": True,
            "PerformanceInsightsRetentionPeriod": 7,
        },
    )
    template.resource_properties_count_is(
        "AWS::Logs::LogGroup",
        {"RetentionInDays": 7},
        2,
    )
    rendered = template.to_json()
    log_group_names = {
        resource["Properties"]["LogGroupName"]
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::Logs::LogGroup"
    }
    assert log_group_names == {
        "/aws/rds/instance/flowform-staging-postgres/postgresql",
        "/aws/rds/instance/flowform-staging-postgres/upgrade",
    }


def test_staging_database_snapshots_on_delete_without_deletion_protection():
    database = _database_resource()
    assert database["DeletionPolicy"] == "Snapshot"
    assert database["UpdateReplacePolicy"] == "Snapshot"
    assert database["Properties"]["DeletionProtection"] is False


def test_database_upgrades_are_maintenance_window_controlled():
    template = _synth_database_stack()
    template.has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "AllowMajorVersionUpgrade": False,
            "AutoMinorVersionUpgrade": True,
            "ApplyImmediately": False,
        },
    )


def test_prod_database_uses_protected_single_az_retained_configuration():
    database = _database_resource("prod")
    properties = database["Properties"]

    assert properties["DBInstanceClass"] == "db.t4g.small"
    assert properties["MultiAZ"] is False
    assert "AvailabilityZone" in properties
    assert properties["AllocatedStorage"] == "20"
    assert properties["MaxAllocatedStorage"] == 50
    assert properties["BackupRetentionPeriod"] == 30
    assert properties["DeletionProtection"] is True
    assert database["DeletionPolicy"] == "Retain"
    assert database["UpdateReplacePolicy"] == "Retain"

    _synth_database_stack("prod").resource_properties_count_is(
        "AWS::Logs::LogGroup",
        {"RetentionInDays": 90},
        2,
    )
