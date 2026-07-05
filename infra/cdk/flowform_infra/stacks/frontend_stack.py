from aws_cdk import Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from flowform_infra.config import DOMAIN_NAME, EnvConfig
from flowform_infra.constructs.static_site_construct import StaticSiteApp


class FrontendStack(Stack):
    """S3 + CloudFront hosting for public-site and studio-app.

    Replaces the earlier Amplify Hosting approach. Each frontend is a
    StaticSiteApp (private bucket + distribution + Route 53 alias); the
    GitHub Actions deploy role (security_stack.frontend_deploy_role) gets
    exactly sync + invalidate on these two apps, plus read access to the
    /flowform/<env>/frontend/* SSM parameters that carry the SPA's
    build-time config into CI.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        certificate: acm.ICertificate,
        deploy_role: iam.IRole,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if env_config.public_site_domain is None or env_config.studio_domain is None:
            raise ValueError(
                f"EnvConfig for '{env_config.env_name}' has no frontend domains — "
                "the frontend stacks are only meant for full-deployment envs."
            )
        if env_config.auth0_public is None:
            raise ValueError(
                f"EnvConfig for '{env_config.env_name}' has no auth0_public config — "
                f"create infra/cdk/.env.{env_config.env_name} with AUTH0_DOMAIN, "
                "AUTH0_CLIENT_ID, and AUTH0_AUDIENCE (see .env.dev.example) "
                "before deploying the frontend stack."
            )

        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=DOMAIN_NAME)

        self.public_site = StaticSiteApp(
            self,
            "PublicSite",
            env_config=env_config,
            app_name="public-site",
            domain_name=env_config.public_site_domain,
            extra_domain_names=tuple(
                f"{p}.{env_config.public_site_domain}" for p in env_config.public_site_extra_prefixes
            ),
            hosted_zone=hosted_zone,
            certificate=certificate,
        )

        self.studio_app = StaticSiteApp(
            self,
            "StudioApp",
            env_config=env_config,
            app_name="studio-app",
            domain_name=env_config.studio_domain,
            hosted_zone=hosted_zone,
            certificate=certificate,
        )


        # Build-time config for the CI frontend builds (all non-secret,
        # client-side values — they ship in the JS bundle). The deploy
        # workflow reads these before running vite build.
        #
        # TODO: api-base-url points at the planned API hostname; create the
        # ALB + Route 53 record for it when application_stack.py is built.
        api_base_url = f"https://api.{env_config.public_site_domain}"
        frontend_params = {
            "vite-auth0-domain": env_config.auth0_public.domain,
            "vite-auth0-client-id": env_config.auth0_public.client_id,
            "vite-auth0-audience": env_config.auth0_public.audience,
            "vite-api-base-url": api_base_url,
            # Distribution IDs aren't deterministic like bucket names, so
            # the deploy workflow reads them from here for invalidations.
            "public-site-distribution-id": self.public_site.distribution.distribution_id,
            "studio-app-distribution-id": self.studio_app.distribution.distribution_id,
        }
        for suffix, value in frontend_params.items():
            ssm.StringParameter(
                self,
                f"Param-{suffix}",
                parameter_name=f"/flowform/{env_config.env_name}/frontend/{suffix}",
                string_value=value,
            )

        # The policy resource lives in THIS stack (attached to the security
        # stack's role by name) — see StaticSiteApp.deploy_policy_statements
        # for why granting onto the role directly would create a cycle.
        deploy_policy = iam.Policy(
            self,
            "FrontendDeployPolicy",
            statements=[
                *self.public_site.deploy_policy_statements(),
                *self.studio_app.deploy_policy_statements(),
                iam.PolicyStatement(
                    actions=["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/flowform/{env_config.env_name}/frontend/*"
                    ],
                ),
            ],
        )
        deploy_policy.attach_to_role(deploy_role)
