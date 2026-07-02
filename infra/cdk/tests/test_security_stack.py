import aws_cdk as cdk
from aws_cdk.assertions import Template

from flowform_infra.config import DOMAIN_NAME, get_env_config
from flowform_infra.stacks.security_stack import SecurityStack


def _synth_dev_security_stack() -> Template:
    env_config = get_env_config("dev")
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
    template = _synth_dev_security_stack()
    template.resource_count_is("AWS::KMS::Key", 1)
    template.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})


def test_creates_expected_secrets():
    template = _synth_dev_security_stack()
    # app-secrets (app_secret_key, auth0_mgmt_secret, linkage_secret) and
    # db-secrets (db_core_app_password, db_response_app_password)
    template.resource_count_is("AWS::SecretsManager::Secret", 2)


def test_task_role_can_assume_from_ecs_tasks():
    template = _synth_dev_security_stack()
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    }
                ],
            }
        },
    )


def test_ssm_parameters_created():
    template = _synth_dev_security_stack()
    # kms-key-arn, aws-region, hosted-zone-id
    template.resource_count_is("AWS::SSM::Parameter", 3)
