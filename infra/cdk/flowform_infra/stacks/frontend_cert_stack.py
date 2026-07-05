from aws_cdk import Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_route53 as route53
from constructs import Construct

from flowform_infra.config import DOMAIN_NAME, EnvConfig


class FrontendCertStack(Stack):
    """ACM certificate for the frontend CloudFront distributions.

    Lives in us-east-1 (app.py pins the stack env) because CloudFront only
    accepts certificates from that region; `cross_region_references=True`
    on both this stack and FrontendStack lets CDK hand the cert across.
    One cert covers both frontends via subject alternative names,
    DNS-validated against the imported hosted zone.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if env_config.public_site_domain is None or env_config.studio_domain is None:
            raise ValueError(
                f"EnvConfig for '{env_config.env_name}' has no frontend domains — "
                "the frontend stacks are only meant for full-deployment envs."
            )

        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=DOMAIN_NAME)

        alternative_names = [
            *(f"{p}.{env_config.public_site_domain}" for p in env_config.public_site_extra_prefixes),
            env_config.studio_domain,
        ]

        self.certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=env_config.public_site_domain,
            subject_alternative_names=alternative_names,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )
