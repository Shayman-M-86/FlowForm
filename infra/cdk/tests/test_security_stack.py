import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from flowform_infra.config import DOMAIN_NAME, get_env_config
from flowform_infra.stacks.security_stack import SecurityStack


def _synth_security_stack(env_name: str) -> Template:
    env_config = get_env_config(env_name)
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)

    # HostedZone.from_lookup queries a context provider at synth time, which
    # needs real AWS creds outside a deployed app. Pre-seed the context
    # cache with a fake result so tests stay hermetic — same pattern the
    # CDK docs recommend for testing from_lookup-based code. The context key
    # has to be computed from a real stack/env, so use a throwaway one.
    probe_app = cdk.App()
    probe_stack = cdk.Stack(probe_app, "ContextProbe", env=cdk_env)
    context_key = cdk.ContextProvider.get_key(
        probe_stack, provider="hosted-zone", props={"domainName": DOMAIN_NAME}
    ).key

    app = cdk.App(
        context={
            context_key: {
                "Id": "/hostedzone/Z1234567890ABC",
                "Name": f"{DOMAIN_NAME}.",
            }
        }
    )
    stack = SecurityStack(app, "TestSecurityStack", env_config=env_config, env=cdk_env)
    return Template.from_stack(stack)


def test_creates_one_kms_key_with_rotation_enabled():
    template = _synth_security_stack("dev")
    template.resource_count_is("AWS::KMS::Key", 1)
    template.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})


def test_creates_expected_secrets():
    template = _synth_security_stack("dev")
    # app-secrets (app_secret_key, auth0_mgmt_secret), db-secrets
    # (db_core_app_password, db_response_app_password), and the standalone
    # versioned linkage secret
    template.resource_count_is("AWS::SecretsManager::Secret", 3)


def test_dev_app_role_assumable_by_account_principal():
    # dev's backend runs locally, so the role is assumable by principals in
    # the dev account (via sts:AssumeRole) rather than by ECS tasks.
    template = _synth_security_stack("dev")
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"AWS": Match.any_value()},
                    }
                ],
            }
        },
    )


def test_full_deployment_app_role_assumable_by_ec2():
    template = _synth_security_stack("staging")
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                    }
                ],
            }
        },
    )


def test_ssm_parameters_created():
    template = _synth_security_stack("dev")
    # kms-key-arn, aws-region, hosted-zone-id, app-role-arn,
    # linkage-secret-arn
    template.resource_count_is("AWS::SSM::Parameter", 5)
