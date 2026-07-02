from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.constructs.kms_construct import AppKmsKey
from flowform_infra.constructs.secrets_construct import AppSecret

# TODO(decision): dev already has a hand-created KMS key + Secrets Manager
# secret (see infra/docker/.backend.env FLOWFORM_ENCRYPTION_KMS_KEY_ARN /
# FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN). Before deploying this stack to
# dev, decide whether to:
#   (a) import those existing resources by ARN (kms.Key.from_key_arn /
#       secretsmanager.Secret.from_secret_complete_arn) so CDK adopts what's
#       already there, or
#   (b) let this stack create fresh resources and treat the current ones as
#       legacy to be decommissioned.
# Deferred intentionally — not resolved by this scaffold.


class SecurityStack(Stack):
    """KMS keys, Secrets Manager entries, SSM parameters, and the IAM role.
    
    shapes that later stacks (application_stack) will attach to. This is
    the foundation stack — everything else depends on it.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.kms_key = AppKmsKey(self, "AppKmsKey", env_config=env_config).key

        self.linkage_secret = AppSecret(
            self,
            "LinkageSecret",
            env_config=env_config,
            secret_name_suffix="linkage-secret",
            description="HMAC secret used to derive opaque locators linking core/response DBs",
            encryption_key=self.kms_key,
        ).secret

        self.app_secret_key = AppSecret(
            self,
            "AppSecretKey",
            env_config=env_config,
            secret_name_suffix="app-secret-key",
            description="Flask FLOWFORM_APP_SECRET_KEY",
            encryption_key=self.kms_key,
        ).secret

        self.auth0_client_secret = AppSecret(
            self,
            "Auth0ClientSecret",
            env_config=env_config,
            secret_name_suffix="auth0-client-secret",
            description="Auth0 application client secret",
            encryption_key=self.kms_key,
        ).secret

        self.auth0_mgmt_secret = AppSecret(
            self,
            "Auth0MgmtSecret",
            env_config=env_config,
            secret_name_suffix="auth0-mgmt-secret",
            description="Auth0 Management API client secret",
            encryption_key=self.kms_key,
        ).secret

        self.db_core_app_password = AppSecret(
            self,
            "DbCoreAppPassword",
            env_config=env_config,
            secret_name_suffix="db-core-app-password",
            description="App-user password for the core Postgres database",
            encryption_key=self.kms_key,
        ).secret

        self.db_response_app_password = AppSecret(
            self,
            "DbResponseAppPassword",
            env_config=env_config,
            secret_name_suffix="db-response-app-password",
            description="App-user password for the response Postgres database",
            encryption_key=self.kms_key,
        ).secret

        # Non-secret config, readable without Secrets Manager decrypt perms.
        ssm.StringParameter(
            self,
            "KmsKeyArnParam",
            parameter_name=f"/flowform/{env_config.env_name}/kms-key-arn",
            string_value=self.kms_key.key_arn,
        )

        ssm.StringParameter(
            self,
            "RegionParam",
            parameter_name=f"/flowform/{env_config.env_name}/aws-region",
            string_value=env_config.region,
        )

        # Task role shape for the future ECS service (application_stack).
        # Scoped to read-only on exactly the secrets/params this stack owns.
        self.task_role = iam.Role(
            self,
            "AppTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description=f"Task role for the FlowForm API ({env_config.env_name})",
        )

        for secret in (
            self.linkage_secret,
            self.app_secret_key,
            self.auth0_client_secret,
            self.auth0_mgmt_secret,
            self.db_core_app_password,
            self.db_response_app_password,
        ):
            secret.grant_read(self.task_role)

        self.kms_key.grant_decrypt(self.task_role)
