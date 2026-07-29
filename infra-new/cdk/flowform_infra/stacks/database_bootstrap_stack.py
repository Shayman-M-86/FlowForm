# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
"""Operator-invoked resources for the one-shot PostgreSQL bootstrap."""

import hashlib
from pathlib import Path

from aws_cdk import ArnFormat, CfnOutput, Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack


class DatabaseBootstrapStack(Stack):
    """Deploy an operator-invoked Lambda without owning the RDS lifecycle.

    The stack intentionally contains no custom resource and no interface VPC
    endpoint. The operator script creates a tagged Secrets Manager endpoint,
    invokes the idempotent Lambda, and removes the paid endpoint in a finally
    path. A bootstrap failure therefore cannot roll back the database.
    """

    BOOTSTRAP_VERSION = "3"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        database_stack: DatabaseStack,
        kms_key: kms.IKey,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        environment = env_config.env_name
        bootstrap_path = Path(__file__).parents[1] / "database_bootstrap" / "bootstrap"
        database_init_path = Path(__file__).parents[5] / "database" / "init"
        bootstrap_checksum = self._bootstrap_checksum(
            bootstrap_path,
            database_init_path,
        )
        function_name = f"flowform-{environment}-database-bootstrap"
        function_arn = self.format_arn(
            service="lambda",
            resource="function",
            resource_name=function_name,
            arn_format=ArnFormat.COLON_RESOURCE_NAME,
        )

        self.bootstrap_security_group = ec2.SecurityGroup(
            self,
            "DatabaseBootstrapSecurityGroup",
            vpc=network_stack.vpc,
            allow_all_outbound=False,
            description="Database bootstrap Lambda: RDS and temporary Secrets Manager endpoint only",
        )
        self.endpoint_security_group = ec2.SecurityGroup(
            self,
            "DatabaseBootstrapEndpointSecurityGroup",
            vpc=network_stack.vpc,
            allow_all_outbound=False,
            description="Operator-created Secrets Manager endpoint: bootstrap Lambda ingress only",
        )
        self.bootstrap_security_group.add_egress_rule(
            network_stack.rds_security_group,
            ec2.Port.tcp(5432),
            "Bootstrap PostgreSQL to RDS",
        )
        self.bootstrap_security_group.add_egress_rule(
            self.endpoint_security_group,
            ec2.Port.tcp(443),
            "Bootstrap HTTPS to temporary Secrets Manager endpoint",
        )
        self.endpoint_security_group.add_ingress_rule(
            self.bootstrap_security_group,
            ec2.Port.tcp(443),
            "Bootstrap Lambda to Secrets Manager endpoint",
        )
        self.bootstrap_rds_ingress = ec2.CfnSecurityGroupIngress(
            self,
            "DatabaseBootstrapRdsIngress",
            group_id=network_stack.rds_security_group.security_group_id,
            ip_protocol="tcp",
            from_port=5432,
            to_port=5432,
            source_security_group_id=self.bootstrap_security_group.security_group_id,
            description="Database bootstrap Lambda to RDS",
        )

        self.bootstrap_log_group = logs.LogGroup(
            self,
            "DatabaseBootstrapLogGroup",
            log_group_name=f"/flowform/{environment}/database-bootstrap",
            retention=env_config.db_log_retention,
            removal_policy=env_config.removal_policy,
        )
        self.bootstrap_role = iam.Role(
            self,
            "DatabaseBootstrapRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Runs the operator-invoked PostgreSQL bootstrap",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ],
        )
        self.bootstrap_log_group.grant_write(self.bootstrap_role)
        self.bootstrap_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[database_stack.instance.attr_master_user_secret_secret_arn],
            )
        )
        self.bootstrap_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=[
                    "ec2:AssignPrivateIpAddresses",
                    "ec2:CreateNetworkInterface",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeSubnets",
                    "ec2:DetachNetworkInterface",
                    "ec2:UnassignPrivateIpAddresses",
                ],
                resources=["*"],
                conditions={
                    "ArnEquals": {
                        "lambda:SourceFunctionArn": function_arn,
                    }
                },
            )
        )
        kms_key.grant_decrypt(self.bootstrap_role)

        self.bootstrap_function = lambda_.DockerImageFunction(
            self,
            "DatabaseBootstrapFunction",
            function_name=function_name,
            code=lambda_.DockerImageCode.from_image_asset(
                str(bootstrap_path),
                build_contexts={"database_init": str(database_init_path)},
                extra_hash=bootstrap_checksum,
            ),
            architecture=lambda_.Architecture.X86_64,
            memory_size=512,
            timeout=Duration.minutes(10),
            role=self.bootstrap_role,
            log_group=self.bootstrap_log_group,
            vpc=network_stack.vpc,
            vpc_subnets=network_stack.app_subnets,
            security_groups=[self.bootstrap_security_group],
            environment={
                "BOOTSTRAP_CHECKSUM": bootstrap_checksum,
                "BOOTSTRAP_VERSION": self.BOOTSTRAP_VERSION,
                "DATABASE_HOST": database_stack.endpoint_address,
                "DATABASE_PORT": DatabaseStack.POSTGRES_PORT,
                "DATABASE_SECRET_ARN": database_stack.instance.attr_master_user_secret_secret_arn,
            },
            description="Idempotently creates and verifies FlowForm PostgreSQL databases and baseline schemas",
        )
        self.bootstrap_function.node.add_dependency(self.bootstrap_rds_ingress)

        self._create_operator_outputs(
            environment=environment,
            network_stack=network_stack,
            bootstrap_checksum=bootstrap_checksum,
        )

    def _create_operator_outputs(
        self,
        *,
        environment: str,
        network_stack: NetworkStack,
        bootstrap_checksum: str,
    ) -> None:
        """Publish only the non-secret values required by the operator script."""
        outputs = {
            "BootstrapFunctionName": self.bootstrap_function.function_name,
            "BootstrapVersion": self.BOOTSTRAP_VERSION,
            "BootstrapChecksum": bootstrap_checksum,
            "BootstrapVpcId": network_stack.vpc.vpc_id,
            "BootstrapSubnetId": network_stack.app_subnet.subnet_id,
            "BootstrapEndpointSecurityGroupId": self.endpoint_security_group.security_group_id,
            "BootstrapEndpointServiceName": f"com.amazonaws.{self.region}.secretsmanager",
            "BootstrapLogGroupName": self.bootstrap_log_group.log_group_name,
        }
        for output_name, value in outputs.items():
            CfnOutput(
                self,
                output_name,
                key=output_name,
                value=value,
                description=f"FlowForm {environment} database bootstrap operator input",
            )

    @staticmethod
    def _bootstrap_checksum(
        bootstrap_path: Path,
        database_init_path: Path,
    ) -> str:
        """Hash only explicit bootstrap inputs used for reconciliation."""
        digest = hashlib.sha256()
        inputs = [
            (
                path.relative_to(bootstrap_path).as_posix(),
                path,
            )
            for path in [
                bootstrap_path / "Dockerfile",
                bootstrap_path / "requirements.txt",
                *sorted(bootstrap_path.glob("*.py")),
            ]
        ]
        inputs.extend(
            (path.relative_to(database_init_path).as_posix(), path)
            for path in [
                *sorted((database_init_path / "aws").glob("*.sql")),
                database_init_path / "schema" / "flowform_core_db_schema_v4.sql",
                database_init_path / "schema" / "flowform_response_db_schema_v4.sql",
            ]
        )
        for input_name, path in inputs:
            digest.update(input_name.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()
