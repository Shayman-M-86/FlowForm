from collections.abc import Sequence

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from constructs import Construct

from flowform_infra.config import EnvConfig


class RegistryStack(Stack):
    """Private ECR repositories and exact image-publisher permissions."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        kms_key: kms.IKey,
        publisher_role: iam.IRole,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.kms_key = kms_key
        release_retention_count = 100 if env_config.env_name == "prod" else 30

        self.backend_repository = self._create_repository(
            "BackendRepository",
            repository_suffix="backend",
            release_retention_count=release_retention_count,
        )
        self.caddy_repository = self._create_repository(
            "CaddyRepository",
            repository_suffix="caddy",
            release_retention_count=release_retention_count,
        )
        self.squid_repository = self._create_repository(
            "SquidRepository",
            repository_suffix="squid",
            release_retention_count=release_retention_count,
        )
        self.alloy_repository = self._create_repository(
            "AlloyRepository",
            repository_suffix="alloy",
            release_retention_count=release_retention_count,
        )

        self.repositories: tuple[ecr.IRepository, ...] = (
            self.backend_repository,
            self.caddy_repository,
            self.squid_repository,
            self.alloy_repository,
        )

        publish_policy = iam.Policy(
            self,
            "ImagePublishPolicy",
            statements=self._publisher_statements(self.repositories),
        )
        # Keep the stable OIDC role in the scope-level Security stack while
        # placing repository-specific permissions with the repositories. This
        # mirrors FrontendStack and keeps the shared nonprod template free of
        # staging-only resource references.
        publish_policy.attach_to_role(publisher_role)

    def _create_repository(
        self,
        construct_id: str,
        *,
        repository_suffix: str,
        release_retention_count: int,
    ) -> ecr.Repository:
        repository = ecr.Repository(
            self,
            construct_id,
            repository_name=f"flowform-{self.env_config.env_name}-{repository_suffix}",
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            image_scan_on_push=True,
            encryption=ecr.RepositoryEncryption.KMS,
            encryption_key=self.kms_key,
            removal_policy=self.env_config.removal_policy,
            empty_on_delete=self.env_config.removal_policy == RemovalPolicy.DESTROY,
        )
        repository.add_lifecycle_rule(
            description="Expire incomplete or abandoned untagged uploads after seven days",
            tag_status=ecr.TagStatus.UNTAGGED,
            max_image_age=Duration.days(7),
            rule_priority=1,
        )
        repository.add_lifecycle_rule(
            description=f"Retain the newest {release_retention_count} release images",
            tag_status=ecr.TagStatus.ANY,
            max_image_count=release_retention_count,
            rule_priority=2,
        )
        return repository

    @staticmethod
    def _publisher_statements(repositories: Sequence[ecr.IRepository]) -> list[iam.PolicyStatement]:
        return [
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:CompleteLayerUpload",
                    "ecr:InitiateLayerUpload",
                    "ecr:PutImage",
                    "ecr:UploadLayerPart",
                ],
                resources=[repository.repository_arn for repository in repositories],
            ),
        ]
