from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from constructs import Construct


class AppEmailIdentity(Construct):
    """The already hand-configured Route53 hosted zone + SES domain identity.

    Both are imported by reference only — this construct never creates or
    modifies the hosted zone, its records, or SES verification. DNS and SES
    setup stay fully out-of-band; this just gives the rest of the CDK app a
    typed way to reference them and grant send access.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        account: str,
        region: str,
        domain_name: str,
        configuration_set_name: str,
    ) -> None:
        super().__init__(scope, construct_id)

        self.domain_name = domain_name
        self.hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=domain_name)
        self._identity_arn = f"arn:aws:ses:{region}:{account}:identity/{domain_name}"
        self._configuration_set_arn = f"arn:aws:ses:{region}:{account}:configuration-set/{configuration_set_name}"

    def grant_send(self, grantee: iam.IGrantable) -> None:
        """Grant SES sending through this identity and its configuration set.

        SES authorizes a send against both the sender identity and the
        configuration set attached to it. Neither imported resource has a
        CDK-managed object to call ``grant_send()`` on, so keep both exact
        resource ARNs together here.
        """
        grantee.grant_principal.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=[self._identity_arn, self._configuration_set_arn],
            )
        )
