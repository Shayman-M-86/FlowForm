from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import DOMAIN_NAME, EnvConfig
from flowform_infra.constructs.kms_construct import AppKmsKey
from flowform_infra.constructs.secrets_construct import AppMultiSecret
from flowform_infra.constructs.ses_construct import AppEmailIdentity

# Decision (resolved): this stack always CREATES the KMS key and secrets —
# no import-by-ARN path. Dev's hand-created key + linkage secret (the
# FLOWFORM_ENCRYPTION_* ARNs in infra/docker/.backend.env) are legacy: after
# the first dev deploy, point .backend.env at the new ARNs, reseed local dev
# data (existing opaque locators were derived from the old HMAC secret, so
# cross-DB lookups on old rows break — dev data is disposable), then delete
# the old key/secret. Prod's "never recreate" guarantee comes from
# RemovalPolicy.RETAIN plus never renaming these construct IDs (a rename
# forces CloudFormation to replace the resource).
#
# Route53 + SES are hand-configured (hosted zone for flow-form.com.au,
# domain-verified SES identity) and only *imported by reference* below —
# but for different reasons with different lifetimes:
#   - Hosted zone: PERMANENTLY manual. Recreating a zone assigns new
#     nameservers the registrar would have to be repointed at by hand, so
#     the zone stays out of CDK by design (records inside it are fair game).
#   - SES identity: manual FOR NOW. Planned to move into a shared CDK
#     stack (ses.EmailIdentity + DKIM records, adopted via `cdk import`)
#     when email infra is next touched.
# Full list of hand-done steps: docs/manual-prerequisites.md.


class SecurityStack(Stack):
    """KMS key, Secrets Manager entries, SSM parameters, and the app IAM role.

    This is the foundation stack — everything else depends on it, and for
    dev it is the ONLY stack deployed (the app/databases/frontends run
    locally; see app.py).
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

        # The role the running backend uses to reach KMS/secrets/SES, scoped
        # to read-only on exactly the resources this stack owns. Who assumes
        # it differs by environment:
        #   - full deployments: the ECS task (application_stack)
        #   - dev: the locally hosted backend — any principal in the dev
        #     account can `sts:AssumeRole` it, so local AWS credentials get
        #     the same scoped access an ECS task would, instead of carrying
        #     broad user permissions.
        if env_config.full_deployment:
            assumed_by = iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        else:
            assumed_by = iam.AccountPrincipal(env_config.account)

        self.task_role = iam.Role(
            self,
            "AppTaskRole",
            assumed_by=assumed_by,
            description=f"App role for the FlowForm API ({env_config.env_name})",
        )

        for secret in (self.app_secrets, self.db_secrets):
            secret.grant_read(self.task_role)

        self.kms_key.grant_decrypt(self.task_role)

        self.email_identity.grant_send(self.task_role)
