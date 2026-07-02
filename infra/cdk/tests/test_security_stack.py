import aws_cdk as cdk
from aws_cdk.assertions import Template

from flowform_infra.config import get_env_config
from flowform_infra.stacks.security_stack import SecurityStack


def _synth_dev_security_stack() -> Template:
    app = cdk.App()
    env_config = get_env_config("dev")
    stack = SecurityStack(app, "TestSecurityStack", env_config=env_config)
    return Template.from_stack(stack)


def test_creates_one_kms_key_with_rotation_enabled():
    template = _synth_dev_security_stack()
    template.resource_count_is("AWS::KMS::Key", 1)
    template.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})


def test_creates_expected_secrets():
    template = _synth_dev_security_stack()
    # linkage, app secret key, auth0 client, auth0 mgmt, db core, db response
    template.resource_count_is("AWS::SecretsManager::Secret", 6)


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
    template.resource_count_is("AWS::SSM::Parameter", 2)
