import dataclasses
from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from flowform_infra.config import DOMAIN_NAME, Auth0PublicConfig, EnvConfig, get_env_config
from flowform_infra.stacks.frontend_cert_stack import FrontendCertStack
from flowform_infra.stacks.frontend_stack import FrontendStack
from flowform_infra.stacks.security_stack import SecurityStack

_FAKE_AUTH0 = Auth0PublicConfig(
    domain="test-tenant.au.auth0.com",
    client_id="testclientid",
    audience="https://flowform.auth.api",
)

# env_dir with no .env.* files, so get_env_config never picks up real
# local config (e.g. an actual infra/cdk/.env.staging).
_EMPTY_ENV_DIR = Path(__file__).parent


def _staging_config(auth0_public: Auth0PublicConfig | None = _FAKE_AUTH0) -> EnvConfig:
    base = get_env_config("staging", env_dir=_EMPTY_ENV_DIR)
    return dataclasses.replace(base, auth0_public=auth0_public)


def _hosted_zone_context(account: str, region: str) -> dict:
    # HostedZone.from_lookup queries a context provider at synth time;
    # pre-seed a fake result so tests stay hermetic (same pattern as
    # test_security_stack.py). The key must be computed per stack env,
    # and the frontend stacks span two regions (cert lives in us-east-1).
    probe_app = cdk.App()
    probe_stack = cdk.Stack(probe_app, "ContextProbe", env=cdk.Environment(account=account, region=region))
    key = cdk.ContextProvider.get_key(probe_stack, provider="hosted-zone", props={"domainName": DOMAIN_NAME}).key
    return {key: {"Id": "/hostedzone/Z1234567890ABC", "Name": f"{DOMAIN_NAME}."}}


def _synth_staging(env_config: EnvConfig | None = None) -> tuple[Template, Template]:
    """Synth the cert + frontend stacks for staging; returns both templates."""
    env_config = env_config or _staging_config()
    app_env = cdk.Environment(account=env_config.account, region=env_config.region)
    cert_env = cdk.Environment(account=env_config.account, region="us-east-1")

    app = cdk.App(
        context={
            **_hosted_zone_context(env_config.account, env_config.region),
            **_hosted_zone_context(env_config.account, "us-east-1"),
        }
    )
    security = SecurityStack(app, "TestSecurity", env_config=env_config, env=app_env)
    cert = FrontendCertStack(
        app, "TestFrontendCert", env_config=env_config, env=cert_env, cross_region_references=True
    )
    frontend = FrontendStack(
        app,
        "TestFrontend",
        env_config=env_config,
        certificate=cert.certificate,
        deploy_role=security.frontend_deploy_role,
        env=app_env,
        cross_region_references=True,
    )
    return Template.from_stack(cert), Template.from_stack(frontend)


def test_two_private_buckets_and_distributions():
    _, frontend = _synth_staging()
    frontend.resource_count_is("AWS::S3::Bucket", 2)
    frontend.resource_count_is("AWS::CloudFront::Distribution", 2)
    for name in ("flowform-staging-public-site", "flowform-staging-studio-app"):
        frontend.has_resource_properties(
            "AWS::S3::Bucket",
            {
                "BucketName": name,
                "PublicAccessBlockConfiguration": Match.object_like({"BlockPublicAcls": True}),
            },
        )


def test_spa_fallback_on_both_distributions():
    _, frontend = _synth_staging()
    frontend.resource_properties_count_is(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "CustomErrorResponses": [
                        {"ErrorCode": 403, "ResponseCode": 200, "ResponsePagePath": "/index.html"},
                        {"ErrorCode": 404, "ResponseCode": 200, "ResponsePagePath": "/index.html"},
                    ]
                }
            )
        },
        2,
    )


def test_route53_aliases_for_both_domains():
    _, frontend = _synth_staging()
    for domain in ("staging.flow-form.com.au.", "studio.staging.flow-form.com.au."):
        frontend.has_resource_properties(
            "AWS::Route53::RecordSet",
            {"Name": domain, "Type": "A", "AliasTarget": Match.any_value()},
        )


def test_cert_in_us_east_1_covers_both_domains():
    cert, _ = _synth_staging()
    cert.has_resource_properties(
        "AWS::CertificateManager::Certificate",
        {
            "DomainName": "staging.flow-form.com.au",
            "SubjectAlternativeNames": ["studio.staging.flow-form.com.au"],
            "ValidationMethod": "DNS",
        },
    )


def test_frontend_config_published_to_ssm():
    _, frontend = _synth_staging()
    # 4 vite-* params + 2 distribution-id params
    frontend.resource_count_is("AWS::SSM::Parameter", 6)
    frontend.has_resource_properties(
        "AWS::SSM::Parameter",
        {"Name": "/flowform/staging/frontend/vite-auth0-domain", "Value": _FAKE_AUTH0.domain},
    )


def test_outputs_expose_bucket_and_distribution():
    _, frontend = _synth_staging()
    outputs = frontend.to_json().get("Outputs", {})
    joined = " ".join(outputs)
    expected = (
        "PublicSiteBucketName",
        "PublicSiteDistributionId",
        "StudioAppBucketName",
        "StudioAppDistributionId",
    )
    for fragment in expected:
        assert fragment in joined, f"missing output {fragment}: {list(outputs)}"


def test_missing_auth0_config_fails_synth():
    with pytest.raises(ValueError, match="auth0_public"):
        _synth_staging(_staging_config(auth0_public=None))


def test_staging_security_creates_github_oidc_and_deploy_role():
    env_config = _staging_config()
    app = cdk.App(context=_hosted_zone_context(env_config.account, env_config.region))
    stack = SecurityStack(
        app,
        "TestSecurity",
        env_config=env_config,
        env=cdk.Environment(account=env_config.account, region=env_config.region),
    )
    template = Template.from_stack(stack)
    # Read-only CI preview role (cdk diff) with the same OIDC trust.
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "flowform-staging-ci-preview",
            "ManagedPolicyArns": Match.any_value(),
        },
    )
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "flowform-staging-frontend-deploy",
            "AssumeRolePolicyDocument": {
                "Statement": [
                    Match.object_like(
                        {
                            "Action": "sts:AssumeRoleWithWebIdentity",
                            "Condition": Match.object_like(
                                {
                                    "StringLike": {
                                        "token.actions.githubusercontent.com:sub": "repo:Shayman-M-86/FlowForm:*"
                                    }
                                }
                            ),
                        }
                    )
                ],
            },
        },
    )
