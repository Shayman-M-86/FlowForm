from aws_cdk import RemovalPolicy
from aws_cdk import aws_kms as kms
from constructs import Construct


class AppKmsKey(Construct):
    """A single customer-managed KMS key used for app-level encryption.

    (e.g. the session-linkage HMAC secret, at-rest encryption for
    Secrets Manager entries this stack owns).
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        scope_name: str,
        removal_policy: RemovalPolicy,
    ) -> None:
        super().__init__(scope, construct_id)

        self.key = kms.Key(
            self,
            "Key",
            alias=f"alias/flowform-{scope_name}",
            description=f"FlowForm app-level encryption key ({scope_name})",
            enable_key_rotation=True,
            removal_policy=removal_policy,
        )
