from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from constructs import Construct

from flowform_infra.config import EnvConfig


class AppEmailIdentity(Construct):
    """The already hand-configured Route53 hosted zone + SES domain identity.

    Both are imported by reference only — this construct never creates or
    modifies the hosted zone, its records, or SES verification. DNS and SES
    setup stay fully out-of-band; this just gives the rest of the CDK app a
    typed way to reference them and grant send access.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, domain_name: str) -> None:
        super().__init__(scope, construct_id)

        self.domain_name = domain_name
        self.hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=domain_name)
        self._identity_arn = f"arn:aws:ses:{env_config.region}:{env_config.account}:identity/{domain_name}"

    def grant_send(self, grantee: iam.IGrantable) -> None:
        """Grant ses:SendEmail / ses:SendRawEmail, scoped to this domain identity.

        SES identities have no CDK-managed resource to call `.grant_send()`
        on natively, so this is the hand-written equivalent — kept here
        rather than inline in a stack so the identity and its access rule
        live in one place.
        """
        grantee.grant_principal.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=[self._identity_arn],
            )
        )
