from aws_cdk import aws_kms as kms
from constructs import Construct

from flowform_infra.config import EnvConfig


class AppKmsKey(Construct):
    """A single customer-managed KMS key used for app-level encryption.

    (e.g. the session-linkage HMAC secret, at-rest encryption for
    Secrets Manager entries this stack owns).
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig) -> None:
        super().__init__(scope, construct_id)

        self.key = kms.Key(
            self,
            "Key",
            alias=f"alias/flowform-{env_config.env_name}",
            description=f"FlowForm app-level encryption key ({env_config.env_name})",
            enable_key_rotation=True,
            removal_policy=env_config.removal_policy,
        )
