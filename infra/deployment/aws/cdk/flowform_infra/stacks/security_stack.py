from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import (
    DOMAIN_NAME,
    GITHUB_OWNER,
    GITHUB_REPOSITORY,
    SecurityScopeConfig,
)
from flowform_infra.constructs.kms_construct import AppKmsKey
from flowform_infra.constructs.secrets_construct import AppMultiSecret
from flowform_infra.constructs.ses_construct import AppEmailIdentity

# This stack is deployed once per SECURITY SCOPE, not per environment:
# dev and staging share "nonprod" (FlowForm-Nonprod-Security) because they
# are simulation environments and duplicating KMS keys / Secrets Manager
# entries between them is pure cost; prod gets its own isolated scope.
# See SecurityScopeConfig in config/environments.py. Everything in here
# must derive from scope_config alone so the template is identical no
# matter which `-c env=...` context synthesized it.
#
# Decision (resolved): this stack always CREATES the KMS key and secrets —
# no import-by-ARN path, so a brand-new AWS account bootstraps with zero
# special cases. Prod's "never recreate" guarantee comes from
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
    locally; see app.py). One instance serves every env in its scope.
    """

    def __init__(self, scope: Construct, construct_id: str, *, scope_config: SecurityScopeConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        scope_name = scope_config.scope_name

        self.kms_key = AppKmsKey(
            self,
            "AppKmsKey",
            scope_name=scope_name,
            removal_policy=scope_config.removal_policy,
        ).key

        # Imported by reference only — CDK never creates/modifies the zone,
        # its records, or SES verification. Later stacks (e.g.
        # application_stack, for the api.<domain> record) can take the
        # hosted zone from the stack's public attribute.
        self.email_identity = AppEmailIdentity(
            self,
            "EmailIdentity",
            account=scope_config.account,
            region=scope_config.region,
            domain_name=DOMAIN_NAME,
        )

        # App boot-time config, always read together by the running Flask
        # service. Keyed on jsonKey so the EC2 bootstrap can still map each
        # value back out to its own file/env var without any change to how
        # the app reads its settings.
        self.app_secrets = AppMultiSecret(
            self,
            "AppSecrets",
            namespace=scope_name,
            removal_policy=scope_config.removal_policy,
            secret_name_suffix="app-secrets",
            description="Flask app secret key and Auth0 management secret",
            encryption_key=self.kms_key,
            keys=[
                "app_secret_key",
                "auth0_mgmt_secret",
            ],
        ).secret

        # The core/response linkage HMAC secret is deliberately NOT part of
        # app_secrets: the backend rotates and fetches it via Secrets
        # Manager versioning (AWSCURRENT = active key, older keys looked up
        # by VersionId — see backend/app/crypto/_internal/linkage_secrets.py),
        # so it must own its version history instead of sharing one with
        # unrelated keys. SecretString shape the backend requires:
        # {"version": N, "secret_b64": "<base64 key>"}. The generated
        # placeholder is NOT that shape on purpose — seed the real value
        # out-of-band (put-secret-value), like every other secret here.
        self.linkage_secret = secretsmanager.Secret(
            self,
            "LinkageSecret",
            secret_name=f"flowform/{scope_name}/linkage-secret",
            description="Versioned core/response DB linkage HMAC secret",
            encryption_key=self.kms_key,
            removal_policy=scope_config.removal_policy,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"version": 1}',
                generate_string_key="secret_b64",
                exclude_punctuation=True,
            ),
        )

        # DB app-user passwords, grouped since both are needed together at
        # boot and neither is meaningful on its own. These serve the RDS
        # databases in staging/prod only — dev's local Postgres passwords
        # are machine-local throwaways generated by
        # scripts/secrets/generate-secrets.sh and never stored here.
        self.db_secrets = AppMultiSecret(
            self,
            "DbSecrets",
            namespace=scope_name,
            removal_policy=scope_config.removal_policy,
            secret_name_suffix="db-secrets",
            description="App-user passwords for the core and response Postgres databases",
            encryption_key=self.kms_key,
            keys=["db_core_app_password", "db_response_app_password"],
        ).secret

        # Non-secret config, readable without Secrets Manager decrypt perms.
        ssm.StringParameter(
            self,
            "KmsKeyArnParam",
            parameter_name=f"/flowform/{scope_name}/kms-key-arn",
            string_value=self.kms_key.key_arn,
        )

        ssm.StringParameter(
            self,
            "RegionParam",
            parameter_name=f"/flowform/{scope_name}/aws-region",
            string_value=scope_config.region,
        )

        # The ARN (not the value) — consumed by .backend.env in dev and the
        # EC2 bootstrap's SSM-to-env-file step in staging/prod.
        ssm.StringParameter(
            self,
            "LinkageSecretArnParam",
            parameter_name=f"/flowform/{scope_name}/linkage-secret-arn",
            string_value=self.linkage_secret.secret_arn,
        )

        ssm.StringParameter(
            self,
            "HostedZoneIdParam",
            parameter_name=f"/flowform/{scope_name}/hosted-zone-id",
            string_value=self.email_identity.hosted_zone.hosted_zone_id,
        )

        # The role the running backend uses to reach KMS/secrets/SES, scoped
        # to read-only on exactly the resources this stack owns. Who assumes
        # it depends on the scope:
        #   - always: the EC2 app instance (application_stack wraps it in an
        #     instance profile) for the scope's deployed env(s)
        #   - nonprod additionally: any principal in the account, so the
        #     locally hosted dev backend (an assume-role profile over
        #     `aws login`) gets the same scoped access the EC2 instance
        #     would, instead of carrying broad user permissions.
        assumed_by: iam.PrincipalBase = iam.ServicePrincipal("ec2.amazonaws.com")
        if scope_config.local_dev_assume:
            assumed_by = iam.CompositePrincipal(assumed_by, iam.AccountPrincipal(scope_config.account))

        self.task_role = iam.Role(
            self,
            "AppTaskRole",
            assumed_by=assumed_by,
            description=f"App role for the FlowForm API ({scope_name})",
        )

        for secret in (self.app_secrets, self.db_secrets, self.linkage_secret):
            secret.grant_read(self.task_role)

        # The backend both wraps (Encrypt) and unwraps (Decrypt) per-session
        # DEKs — see backend/app/crypto/_internal/wrapping.py.
        self.kms_key.grant_encrypt_decrypt(self.task_role)

        self.email_identity.grant_send(self.task_role)
        self._grant_backend_runtime_reads(scope_config)

        # Published so consumers can find the role without hardcoding the
        # CDK-generated name: dev assume-role profiles (~/.aws/config
        # role_arn) and, later, the EC2 bootstrap.
        ssm.StringParameter(
            self,
            "AppRoleArnParam",
            parameter_name=f"/flowform/{scope_name}/app-role-arn",
            string_value=self.task_role.role_arn,
        )

        # GitHub Actions deploys the frontends (S3 sync + CloudFront
        # invalidation) by assuming this role via OIDC — no long-lived AWS
        # keys in GitHub. The role starts with no permissions; the frontend
        # stack grants sync/invalidate/SSM-read on exactly its resources.
        # Role names keep the ENV name (flowform-staging-...), not the scope
        # name, so the GitHub workflows never change.
        #
        # The OIDC identity provider is an account-level singleton (one per
        # provider URL), so exactly one scope creates it (nonprod); prod
        # imports it by its deterministic ARN and deploys after nonprod.
        if scope_config.creates_oidc_provider:
            oidc_provider_arn = iam.OpenIdConnectProvider(
                self,
                "GitHubOidcProvider",
                url="https://token.actions.githubusercontent.com",
                client_ids=["sts.amazonaws.com"],
            ).open_id_connect_provider_arn
        else:
            oidc_provider_arn = f"arn:aws:iam::{scope_config.account}:oidc-provider/token.actions.githubusercontent.com"

        github_actions_principal = iam.FederatedPrincipal(
            oidc_provider_arn,
            conditions={
                "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                "StringLike": {"token.actions.githubusercontent.com:sub": f"repo:{GITHUB_OWNER}/{GITHUB_REPOSITORY}:*"},
            },
            assume_role_action="sts:AssumeRoleWithWebIdentity",
        )

        self.frontend_deploy_role = iam.Role(
            self,
            "FrontendDeployRole",
            # Deterministic name so the GitHub workflow can reference the
            # role ARN without reading stack outputs.
            role_name=f"flowform-{scope_config.ci_env_name}-frontend-deploy",
            assumed_by=github_actions_principal,
            description=f"GitHub Actions frontend deploy ({scope_config.ci_env_name})",
        )

        # Read-only role for CI preview work (`cdk diff` describes the
        # deployed stacks to compare against the synthesized templates).
        # Same OIDC trust as the deploy role, but no write access at all.
        self.ci_preview_role = iam.Role(
            self,
            "CiPreviewRole",
            role_name=f"flowform-{scope_config.ci_env_name}-ci-preview",
            assumed_by=github_actions_principal,
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess")],
            description=f"GitHub Actions read-only CI preview, e.g. cdk diff ({scope_config.ci_env_name})",
        )

    def _grant_backend_runtime_reads(self, scope_config: SecurityScopeConfig) -> None:
        """Grant EC2 app-host reads that belong to the shared backend role."""
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                ],
                resources=[
                    self.format_arn(
                        service="ssm",
                        resource="parameter",
                        resource_name=f"flowform/{scope_config.scope_name}/*",
                    ),
                    self.format_arn(
                        service="ssm",
                        resource="parameter",
                        resource_name=f"flowform/{scope_config.ci_env_name}/*",
                    ),
                ],
            )
        )
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                ],
                # TODO: tighten to the exact backend ECR repository ARN when
                # the repository is added to CDK. NOTE: the proxy box's role
                # gets the matching grant in
                # application_stack.py::_grant_ecr_pull — keep both ECR
                # wildcards in sync until real repo ARNs replace them.
                resources=[
                    self.format_arn(
                        service="ecr",
                        resource="repository",
                        resource_name=f"flowform-{scope_config.ci_env_name}-*",
                    )
                ],
            )
        )
