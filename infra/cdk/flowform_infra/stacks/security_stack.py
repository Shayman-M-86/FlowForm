from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import DOMAIN_NAME, EnvConfig
from flowform_infra.constructs.kms_construct import AppKmsKey
from flowform_infra.constructs.secrets_construct import AppMultiSecret
from flowform_infra.constructs.ses_construct import AppEmailIdentity

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
#
# Route53 + SES are also already hand-configured (hosted zone for
# flow-form.com.au, domain-verified SES identity — see
# FLOWFORM_EMAIL_FROM_ADDRESS in infra/docker/.backend.env). Unlike the KMS
# key/secret above, these are only *imported by reference* below, never
# created or modified by CDK — DNS and SES verification stay fully
# out-of-band.


class SecurityStack(Stack):
    """KMS keys, Secrets Manager entries, SSM parameters, and the IAM role.
    
    shapes that later stacks (application_stack) will attach to. This is
    the foundation stack — everything else depends on it.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.kms_key = AppKmsKey(self, "AppKmsKey", env_config=env_config).key

        # Imported by reference only — CDK never creates/modifies the zone,
        # its records, or SES verification. Later stacks (e.g.
        # application_stack, for an ALB alias record) can take the hosted
        # zone from the stack's public attribute.
        self.email_identity = AppEmailIdentity(
            self, "EmailIdentity", env_config=env_config, domain_name=DOMAIN_NAME
        )

        # App boot-time config, always read together by the running Flask
        # service. Keyed on jsonKey so ECS can still map each value back
        # out to its own env var (secretName:jsonKey::) without any change
        # to how the app reads its settings.
        self.app_secrets = AppMultiSecret(
            self,
            "AppSecrets",
            env_config=env_config,
            secret_name_suffix="app-secrets",
            description=(
                "Flask app secret key, Auth0 management secret, and the "
                "core/response DB linkage HMAC secret"
            ),
            encryption_key=self.kms_key,
            keys=[
                "app_secret_key",
                "auth0_mgmt_secret",
                "linkage_secret",
            ],
        ).secret

        # DB app-user passwords, grouped since both are needed together at
        # boot and neither is meaningful on its own.
        self.db_secrets = AppMultiSecret(
            self,
            "DbSecrets",
            env_config=env_config,
            secret_name_suffix="db-secrets",
            description="App-user passwords for the core and response Postgres databases",
            encryption_key=self.kms_key,
            keys=["db_core_app_password", "db_response_app_password"],
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

        ssm.StringParameter(
            self,
            "HostedZoneIdParam",
            parameter_name=f"/flowform/{env_config.env_name}/hosted-zone-id",
            string_value=self.email_identity.hosted_zone.hosted_zone_id,
        )

        # Task role shape for the future ECS service (application_stack).
        # Scoped to read-only on exactly the secrets/params this stack owns.
        self.task_role = iam.Role(
            self,
            "AppTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description=f"Task role for the FlowForm API ({env_config.env_name})",
        )

        for secret in (self.app_secrets, self.db_secrets):
            secret.grant_read(self.task_role)

        self.kms_key.grant_decrypt(self.task_role)

        self.email_identity.grant_send(self.task_role)
