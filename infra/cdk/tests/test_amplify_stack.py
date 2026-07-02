import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from flowform_infra.config import get_env_config
from flowform_infra.stacks.amplify_stack import AmplifyStack


def _synth_dev_amplify_stack() -> Template:
    env_config = get_env_config("dev")
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
    app = cdk.App()
    stack = AmplifyStack(app, "TestAmplifyStack", env_config=env_config, env=cdk_env)
    return Template.from_stack(stack)


def test_creates_two_amplify_apps():
    template = _synth_dev_amplify_stack()
    template.resource_count_is("AWS::Amplify::App", 2)


def test_public_site_app_named_correctly():
    template = _synth_dev_amplify_stack()
    template.has_resource_properties(
        "AWS::Amplify::App", {"Name": Match.string_like_regexp("public-site")}
    )


def test_studio_app_named_correctly():
    template = _synth_dev_amplify_stack()
    template.has_resource_properties(
        "AWS::Amplify::App", {"Name": Match.string_like_regexp("studio-app")}
    )


def test_creates_one_main_branch_per_app():
    template = _synth_dev_amplify_stack()
    template.resource_count_is("AWS::Amplify::Branch", 2)
