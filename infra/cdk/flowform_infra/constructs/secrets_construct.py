from aws_cdk import aws_kms as kms
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from flowform_infra.config import EnvConfig


class AppSecret(Construct):
    """A single Secrets Manager secret, named to match the ARN pattern
    already in use (see infra/docker/.backend.env,
    e.g. flowform/dev/linkage-secret-*).

    Creates the secret with a generated placeholder value — the real value
    is set out-of-band (console, CLI, or a rotation Lambda), never through
    CDK, so secret values never appear in a synthesized template or in git.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        secret_name_suffix: str,
        description: str,
        encryption_key: kms.IKey,
    ) -> None:
        super().__init__(scope, construct_id)

        self.secret = secretsmanager.Secret(
            self,
            "Secret",
            secret_name=f"flowform/{env_config.env_name}/{secret_name_suffix}",
            description=description,
            encryption_key=encryption_key,
            removal_policy=env_config.removal_policy,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                password_length=32,
            ),
        )
