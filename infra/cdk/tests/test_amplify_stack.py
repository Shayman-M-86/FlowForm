import dataclasses
from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from flowform_infra.config import Auth0PublicConfig, EnvConfig, get_env_config
from flowform_infra.stacks.amplify_stack import AmplifyStack

# The Amplify stack is only synthesized for full deployments (staging/prod),
# and it requires auth0_public to be filled in. In the real app that comes
# from the gitignored .env.<env> file; tests patch fake values in directly
# so they never depend on files present on the developer's machine.
_FAKE_AUTH0 = Auth0PublicConfig(
    domain="test-tenant.au.auth0.com",
    client_id="testclientid",
    audience="https://flowform.auth.api",
)

# env_dir with no .env.* files, so get_env_config never picks up real
# local config (e.g. an actual infra/cdk/.env.staging).
_EMPTY_ENV_DIR = Path(__file__).parent


def _staging_config(auth0_public: Auth0PublicConfig | None) -> EnvConfig:
    base = get_env_config("staging", env_dir=_EMPTY_ENV_DIR)
    return dataclasses.replace(base, auth0_public=auth0_public)


def _prod_config(auth0_public: Auth0PublicConfig | None) -> EnvConfig:
    base = get_env_config("prod", env_dir=_EMPTY_ENV_DIR)
    return dataclasses.replace(base, auth0_public=auth0_public)


def _synth_amplify_stack(env_config: EnvConfig) -> Template:
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
    app = cdk.App()
    stack = AmplifyStack(app, "TestAmplifyStack", env_config=env_config, env=cdk_env)
    return Template.from_stack(stack)


def _synth_staging_amplify_stack() -> Template:
    return _synth_amplify_stack(_staging_config(_FAKE_AUTH0))


def test_creates_two_amplify_apps():
    template = _synth_staging_amplify_stack()
    template.resource_count_is("AWS::Amplify::App", 2)


def test_public_site_app_named_correctly():
    template = _synth_staging_amplify_stack()
    template.has_resource_properties(
        "AWS::Amplify::App", {"Name": Match.string_like_regexp("public-site")}
    )


def test_studio_app_named_correctly():
    template = _synth_staging_amplify_stack()
    template.has_resource_properties(
        "AWS::Amplify::App", {"Name": Match.string_like_regexp("studio-app")}
    )


def test_creates_one_branch_per_app():
    template = _synth_staging_amplify_stack()
    template.resource_count_is("AWS::Amplify::Branch", 2)


def test_staging_uses_staging_branch():
    template = _synth_staging_amplify_stack()
    template.resource_properties_count_is("AWS::Amplify::Branch", {"BranchName": "staging"}, 2)


def test_prod_uses_main_branch():
    template = _synth_amplify_stack(_prod_config(_FAKE_AUTH0))
    template.resource_properties_count_is("AWS::Amplify::Branch", {"BranchName": "main"}, 2)


def test_build_specs_use_monorepo_format_with_app_root():
    template = _synth_staging_amplify_stack()
    apps = template.find_resources("AWS::Amplify::App")
    app_roots = set()
    for app in apps.values():
        build_spec = app["Properties"]["BuildSpec"]
        assert "applications" in build_spec, "expected monorepo build-spec format"
        for line in build_spec.splitlines():
            if "appRoot:" in line:
                app_roots.add(line.split("appRoot:")[1].strip())
    assert app_roots == {"frontend/apps/public-site", "frontend/apps/studio-app"}


def test_apps_set_monorepo_app_root_env_var():
    template = _synth_staging_amplify_stack()
    for app_root in ("frontend/apps/public-site", "frontend/apps/studio-app"):
        template.has_resource_properties(
            "AWS::Amplify::App",
            {
                "EnvironmentVariables": Match.array_with(
                    [{"Name": "AMPLIFY_MONOREPO_APP_ROOT", "Value": app_root}]
                )
            },
        )


def test_studio_app_has_spa_rewrite_rule():
    template = _synth_staging_amplify_stack()
    template.has_resource_properties(
        "AWS::Amplify::App",
        {
            "Name": Match.string_like_regexp("studio-app"),
            "CustomRules": Match.array_with(
                [Match.object_like({"Target": "/index.html", "Status": "200"})]
            ),
        },
    )


def test_apps_connected_to_github_via_access_token():
    template = _synth_staging_amplify_stack()
    apps = template.find_resources("AWS::Amplify::App")
    assert len(apps) == 2
    for app in apps.values():
        props = app["Properties"]
        assert props["Repository"] == "https://github.com/Shayman-M-86/FlowForm"
        # GitHub App flow: PAT via AccessToken, never the legacy OauthToken
        assert "AccessToken" in props
        assert "OauthToken" not in props
        assert "flowform/shared/github-pat" in props["AccessToken"]


def test_staging_domain_associations():
    template = _synth_staging_amplify_stack()
    template.resource_count_is("AWS::Amplify::Domain", 2)
    for domain_name in ("staging.flow-form.com.au", "studio.staging.flow-form.com.au"):
        template.has_resource_properties(
            "AWS::Amplify::Domain",
            {
                "DomainName": domain_name,
                # BranchName resolves via Fn::GetAtt at deploy time
                "SubDomainSettings": [{"BranchName": Match.any_value(), "Prefix": ""}],
            },
        )


def test_no_domain_association_when_unset():
    env_config = dataclasses.replace(
        _staging_config(_FAKE_AUTH0), public_site_domain=None, studio_domain=None
    )
    app = cdk.App()
    stack = AmplifyStack(
        app,
        "TestAmplifyStack",
        env_config=env_config,
        env=cdk.Environment(account=env_config.account, region=env_config.region),
    )
    Template.from_stack(stack).resource_count_is("AWS::Amplify::Domain", 0)


def test_studio_app_gets_auth0_env_vars():
    template = _synth_staging_amplify_stack()
    template.has_resource_properties(
        "AWS::Amplify::App",
        {
            "EnvironmentVariables": Match.array_with(
                [
                    {"Name": "VITE_AUTH0_DOMAIN", "Value": _FAKE_AUTH0.domain},
                    {"Name": "VITE_AUTH0_CLIENT_ID", "Value": _FAKE_AUTH0.client_id},
                    {"Name": "VITE_AUTH0_AUDIENCE", "Value": _FAKE_AUTH0.audience},
                ]
            )
        },
    )


def test_missing_auth0_config_fails_synth():
    env_config = _staging_config(auth0_public=None)
    app = cdk.App()
    with pytest.raises(ValueError, match="auth0_public"):
        AmplifyStack(
            app,
            "TestAmplifyStack",
            env_config=env_config,
            env=cdk.Environment(account=env_config.account, region=env_config.region),
        )
