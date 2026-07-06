from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from constructs import Construct

from flowform_infra.config import EnvConfig

# Path patterns shared by both apps. CloudFront's `*` matches any characters
# including `/`, so `*.woff2` catches fonts anywhere in the tree.
_FONT_PATTERNS = ("*.woff2", "*.woff")
_IMAGE_PATTERNS = ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.svg", "*.ico")


class SiteCachingPolicies(Construct):
    """Cache + response-header policies shared by every StaticSiteApp.

    Browser caching (Cache-Control response headers) and edge caching
    (CloudFront cache policies) are separate knobs; each tier sets both.
    The tiers carry over the rules the old Amplify customHttp.yml applied:

      immutable — content-hashed build assets and fonts. Safe to cache for
        a year everywhere: a new build ships new filenames.
      media — images whose names are NOT content-hashed. A day in the
        browser with a week of stale-while-revalidate, a week at the edge.
      html — index.html and anything unmatched. `no-cache` so browsers
        revalidate on every load; short edge TTL, flushed by the deploy
        workflow's invalidation anyway.

    Cache/response-header policies are account-scoped with a small quota,
    so instantiate this once per stack and share it across apps.
    """

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        self.immutable_cache = cloudfront.CachePolicy(
            self,
            "ImmutableCache",
            comment="Content-hashed assets and fonts: a year at the edge",
            min_ttl=Duration.days(1),
            default_ttl=Duration.days(365),
            max_ttl=Duration.days(365),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )
        self.immutable_headers = _cache_control_headers(
            self, "ImmutableHeaders", "public, max-age=31536000, immutable"
        )

        self.media_cache = cloudfront.CachePolicy(
            self,
            "MediaCache",
            comment="Un-hashed images: a week at the edge",
            min_ttl=Duration.minutes(1),
            default_ttl=Duration.days(1),
            max_ttl=Duration.days(7),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )
        self.media_headers = _cache_control_headers(
            self, "MediaHeaders", "public, max-age=86400, stale-while-revalidate=604800"
        )

        self.html_cache = cloudfront.CachePolicy(
            self,
            "HtmlCache",
            comment="index.html and unmatched paths: minutes at the edge",
            min_ttl=Duration.seconds(0),
            default_ttl=Duration.minutes(5),
            max_ttl=Duration.hours(1),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )
        self.html_headers = _cache_control_headers(self, "HtmlHeaders", "no-cache")


def _cache_control_headers(
    scope: Construct, construct_id: str, cache_control: str
) -> cloudfront.ResponseHeadersPolicy:
    return cloudfront.ResponseHeadersPolicy(
        scope,
        construct_id,
        custom_headers_behavior=cloudfront.ResponseCustomHeadersBehavior(
            custom_headers=[
                cloudfront.ResponseCustomHeader(
                    header="Cache-Control", value=cache_control, override=True
                )
            ]
        ),
    )


class StaticSiteApp(Construct):
    """One statically-hosted frontend: private S3 bucket behind CloudFront.

    The bucket blocks all public access; CloudFront reaches it through an
    Origin Access Control, so the distribution is the only way in. 403/404
    from the origin fall back to /index.html (SPA client-side routing; for
    the static public site it doubles as a soft-404). Deploys are plain
    `aws s3 sync` + a CloudFront invalidation — grant_deploy() scopes a
    CI role to exactly that.

    Caching is defined entirely here (not in the deploy workflow):
    `immutable_path_patterns` names each app's content-hashed build output
    dir (Astro's /_astro/*, Vite's /assets/*); fonts and images get shared
    behaviors from SiteCachingPolicies.
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
        caching: SiteCachingPolicies,
        immutable_path_patterns: tuple[str, ...],
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

        origin = origins.S3BucketOrigin.with_origin_access_control(self.bucket)

        def behavior(
            cache_policy: cloudfront.ICachePolicy,
            response_headers_policy: cloudfront.IResponseHeadersPolicy,
        ) -> cloudfront.BehaviorOptions:
            return cloudfront.BehaviorOptions(
                origin=origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cache_policy,
                response_headers_policy=response_headers_policy,
            )

        immutable = behavior(caching.immutable_cache, caching.immutable_headers)
        media = behavior(caching.media_cache, caching.media_headers)

        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment=f"flowform-{env_config.env_name}-{app_name}",
            default_behavior=behavior(caching.html_cache, caching.html_headers),
            additional_behaviors={
                **dict.fromkeys((*immutable_path_patterns, *_FONT_PATTERNS), immutable),
                **dict.fromkeys(_IMAGE_PATTERNS, media),
            },
            default_root_object="index.html",
            domain_names=[domain_name, *extra_domain_names],
            certificate=certificate,
            error_responses=[
                # The SPA fallback caches index.html at the edge under
                # whatever path 403/404'd; keep that window short so stale
                # fallbacks don't outlive a deploy by much (the workflow's
                # /* invalidation clears them immediately anyway).
                cloudfront.ErrorResponse(
                    http_status=status,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5),
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
