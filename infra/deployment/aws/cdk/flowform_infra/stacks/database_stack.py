from aws_cdk import ArnFormat, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.network_stack import NetworkStack


class DatabaseStack(Stack):
    """Private RDS PostgreSQL instance for the core/response database split.

    CDK owns the server, managed master credential, encryption, networking,
    backup, and logging contracts. Logical databases, roles, schemas, and
    migrations remain a separate controlled release operation.
    """

    POSTGRES_ENGINE_VERSION = "17.9"
    POSTGRES_PORT = "5432"
    BACKUP_WINDOW = "16:00-16:30"
    MAINTENANCE_WINDOW = "sun:17:00-sun:18:00"

    # The two low-privilege runtime identities the backend authenticates as.
    # These must match the PostgreSQL roles granted `rds_iam` by the database
    # bootstrap; an rds-db:connect grant naming a role that lacks `rds_iam`
    # silently fails at connection time.
    CORE_APP_USER = "flowform_core_app"
    RESPONSE_APP_USER = "flowform_response_app"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        kms_key: kms.Key,
        task_role: iam.IRole | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.network_stack = network_stack
        self.kms_key = kms_key

        database_identifier = f"flowform-{env_config.env_name}-postgres"

        self.subnet_group = rds.CfnDBSubnetGroup(
            self,
            "DatabaseSubnetGroup",
            db_subnet_group_description=f"FlowForm {env_config.env_name} isolated RDS subnets",
            db_subnet_group_name=f"flowform-{env_config.env_name}-rds",
            subnet_ids=[
                network_stack.rds_subnet_a.subnet_id,
                network_stack.rds_subnet_b.subnet_id,
            ],
        )

        self.parameter_group = rds.CfnDBParameterGroup(
            self,
            "DatabaseParameterGroup",
            description=f"FlowForm {env_config.env_name} PostgreSQL 17 TLS and SCRAM policy",
            family="postgres17",
            parameters={
                "rds.force_ssl": "1",
                "password_encryption": "scram-sha-256",
                # RDS-specific parameter; accepts only "scram" or "md5+scram",
                # not PostgreSQL's "scram-sha-256" spelling used above.
                "rds.accepted_password_auth_method": "scram",
            },
        )

        self.postgresql_log_group = self._create_database_log_group(
            "PostgresqlLogGroup",
            database_identifier=database_identifier,
            log_name="postgresql",
        )
        self.upgrade_log_group = self._create_database_log_group(
            "UpgradeLogGroup",
            database_identifier=database_identifier,
            log_name="upgrade",
        )

        self.instance = rds.CfnDBInstance(
            self,
            "Database",
            db_instance_identifier=database_identifier,
            engine="postgres",
            engine_version=self.POSTGRES_ENGINE_VERSION,
            db_instance_class=env_config.db_instance_class,
            allocated_storage=str(env_config.db_allocated_storage_gib),
            max_allocated_storage=env_config.db_max_allocated_storage_gib,
            storage_type="gp3",
            storage_encrypted=True,
            kms_key_id=kms_key.key_arn,
            db_subnet_group_name=self.subnet_group.ref,
            availability_zone=network_stack.rds_subnet_a.availability_zone,
            multi_az=False,
            publicly_accessible=False,
            network_type="IPV4",
            port=self.POSTGRES_PORT,
            vpc_security_groups=[network_stack.rds_security_group.security_group_id],
            db_parameter_group_name=self.parameter_group.ref,
            master_username="flowform_admin",
            manage_master_user_password=True,
            # The application authenticates with short-lived IAM tokens rather
            # than a stored password. Without this, RDS rejects every token
            # regardless of the rds-db:connect grant below.
            enable_iam_database_authentication=True,
            master_user_secret=rds.CfnDBInstance.MasterUserSecretProperty(
                kms_key_id=kms_key.key_arn,
            ),
            backup_retention_period=env_config.db_backup_retention_days,
            preferred_backup_window=self.BACKUP_WINDOW,
            preferred_maintenance_window=self.MAINTENANCE_WINDOW,
            copy_tags_to_snapshot=True,
            delete_automated_backups=False,
            deletion_protection=env_config.deletion_protection,
            allow_major_version_upgrade=False,
            auto_minor_version_upgrade=True,
            apply_immediately=False,
            enable_cloudwatch_logs_exports=["postgresql", "upgrade"],
            database_insights_mode="standard",
            enable_performance_insights=True,
            performance_insights_retention_period=7,
        )
        self.instance.apply_removal_policy(env_config.database_removal_policy)
        self.instance.add_dependency(self.subnet_group)
        self.instance.add_dependency(self.parameter_group)
        self.instance.add_dependency(self.postgresql_log_group.node.default_child)
        self.instance.add_dependency(self.upgrade_log_group.node.default_child)

        self.admin_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "DatabaseAdminSecret",
            self.instance.attr_master_user_secret_secret_arn,
        )
        self.endpoint_address = self.instance.attr_endpoint_address
        self.endpoint_port = self.instance.attr_endpoint_port

        # rds-db:connect ARNs are scoped by the DB resource ID (dbu-XXXX), not
        # the instance identifier, and the resource ID is only known after the
        # instance exists.
        self.db_resource_id = self.instance.get_att("DbiResourceId").to_string()

        ssm.StringParameter(
            self,
            "DatabaseResourceIdParam",
            parameter_name=f"/flowform/{env_config.env_name}/database/db_resource_id",
            string_value=self.db_resource_id,
        )

        if task_role is not None:
            self.grant_iam_connect(task_role)

    def grant_iam_connect(self, role: iam.IRole) -> None:
        """Allow a role to open IAM-authenticated sessions as the app users.

        The grant is scoped to exactly the two runtime database users; it does
        not permit connecting as `flowform_admin` or any future role.

        The policy is created here rather than added to the role's own stack.
        This stack already depends on the stack owning the role, so mutating
        that role with a reference to this instance's resource ID would form a
        stack dependency cycle.
        """
        iam.Policy(
            self,
            "DatabaseIamConnectPolicy",
            roles=[role],
            statements=[
                iam.PolicyStatement(
                    actions=["rds-db:connect"],
                    resources=[
                        self.format_arn(
                            service="rds-db",
                            resource="dbuser",
                            resource_name=f"{self.db_resource_id}/{app_user}",
                            arn_format=ArnFormat.COLON_RESOURCE_NAME,
                        )
                        for app_user in (self.CORE_APP_USER, self.RESPONSE_APP_USER)
                    ],
                )
            ],
        )

    def _create_database_log_group(
        self,
        construct_id: str,
        *,
        database_identifier: str,
        log_name: str,
    ) -> logs.LogGroup:
        """Create an RDS log group before the DB starts exporting to it."""
        return logs.LogGroup(
            self,
            construct_id,
            log_group_name=f"/aws/rds/instance/{database_identifier}/{log_name}",
            retention=self.env_config.db_log_retention,
            removal_policy=self.env_config.removal_policy,
        )
