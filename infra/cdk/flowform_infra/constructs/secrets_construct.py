import json

from aws_cdk import aws_kms as kms
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from flowform_infra.config import EnvConfig


class AppMultiSecret(Construct):
    """A single Secrets Manager secret holding multiple named keys as JSON.

    Used to group secret values that are always consumed together at
    runtime (e.g. all of the app's boot-time config, or both DB app
    passwords), so they don't each need their own Secrets Manager entry.
    ECS task definitions can still map each JSON key back out to its own
    env var via the `secretName:jsonKey::` ARN suffix — no application
    code has to change to parse the blob itself.

    Each key gets its own CDK-generated placeholder value at creation;
    real values are set out-of-band (console, CLI, or a rotation Lambda),
    never through CDK, so secret values never appear in a synthesized
    template or in git.
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
        keys: list[str],
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
                secret_string_template=json.dumps(dict.fromkeys(keys, "")),
                generate_string_key=keys[0],
                exclude_punctuation=True,
                password_length=32,
            ),
        )
