from aws_cdk import CfnOutput, RemovalPolicy
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from constructs import Construct

from flowform_infra.config import EnvConfig


class StaticSiteApp(Construct):
    """One statically-hosted frontend: private S3 bucket behind CloudFront.

    The bucket blocks all public access; CloudFront reaches it through an
    Origin Access Control, so the distribution is the only way in. 403/404
    from the origin fall back to /index.html (SPA client-side routing; for
    the static public site it doubles as a soft-404). Deploys are plain
    `aws s3 sync` + a CloudFront invalidation — grant_deploy() scopes a
    CI role to exactly that.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        app_name: str,
        domain_name: str,
        extra_domain_names: tuple[str, ...] = (),
        hosted_zone: route53.IHostedZone,
        certificate: acm.ICertificate,
    ) -> None:
        super().__init__(scope, construct_id)

        # Explicit bucket name so the deploy workflow can address it
        # without reading stack outputs first.
        self.bucket = s3.Bucket(
            self,
            "Bucket",
            bucket_name=f"flowform-{env_config.env_name}-{app_name}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=env_config.removal_policy,
            auto_delete_objects=env_config.removal_policy == RemovalPolicy.DESTROY,
        )

        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment=f"flowform-{env_config.env_name}-{app_name}",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            default_root_object="index.html",
            domain_names=[domain_name, *extra_domain_names],
            certificate=certificate,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=status,
                    response_http_status=200,
                    response_page_path="/index.html",
                )
                for status in (403, 404)
            ],
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
        )

        for name in (domain_name, *extra_domain_names):
            route53.ARecord(
                self,
                f"Alias-{name}",
                zone=hosted_zone,
                record_name=name,
                target=route53.RecordTarget.from_alias(targets.CloudFrontTarget(self.distribution)),
            )

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=self.distribution.distribution_id)

    def deploy_policy_statements(self) -> list[iam.PolicyStatement]:
        """Exactly what a frontend deploy needs: S3 sync + invalidation.

        Returned as statements (rather than granted directly onto the
        role) so the stack can attach them via a policy that lives HERE —
        granting onto a role owned by the security stack would write into
        that stack's template, referencing this stack's bucket ARNs and
        creating a cross-stack dependency cycle.
        """
        return [
            iam.PolicyStatement(actions=["s3:ListBucket"], resources=[self.bucket.bucket_arn]),
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                resources=[self.bucket.arn_for_objects("*")],
            ),
            iam.PolicyStatement(
                actions=["cloudfront:CreateInvalidation"],
                resources=[
                    f"arn:aws:cloudfront::{self.distribution.stack.account}:distribution/{self.distribution.distribution_id}"
                ],
            ),
        ]
