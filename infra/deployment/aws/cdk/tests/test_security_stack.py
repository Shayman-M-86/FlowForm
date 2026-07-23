import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from flowform_infra.config import DOMAIN_NAME, get_env_config, get_security_scope
from flowform_infra.stacks.security_stack import SecurityStack


def _synth_security_stack(env_name: str) -> Template:
    env_config = get_env_config(env_name)
    scope_config = get_security_scope(env_config)
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
    stack = SecurityStack(app, "TestSecurityStack", scope_config=scope_config, env=cdk_env)
    return Template.from_stack(stack)


def test_dev_and_staging_share_the_nonprod_scope_template():
    # dev and staging draw from the same security scope — the templates
    # synthesized under either env context must be byte-identical, or a
    # deploy from one context would silently rewrite the other's resources.
    assert _synth_security_stack("dev").to_json() == _synth_security_stack("staging").to_json()


def test_creates_one_kms_key_with_rotation_enabled():
    template = _synth_security_stack("dev")
    template.resource_count_is("AWS::KMS::Key", 1)
    template.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})


def test_creates_expected_secrets_under_nonprod_namespace():
    template = _synth_security_stack("dev")
    # app-secrets (app_secret_key, auth0_mgmt_secret), db-secrets
    # (db_core_app_password, db_response_app_password), and the standalone
    # versioned linkage secret
    template.resource_count_is("AWS::SecretsManager::Secret", 3)
    template.has_resource_properties(
        "AWS::SecretsManager::Secret", {"Name": "flowform/nonprod/app-secrets"}
    )
    template.has_resource_properties(
        "AWS::SecretsManager::Secret", {"Name": "flowform/nonprod/linkage-secret"}
    )


def test_nonprod_app_role_assumable_by_ec2_and_account():
    # One role serves both envs in the scope: staging's EC2 instance
    # profile AND the locally hosted dev backend (account principals via
    # sts:AssumeRole).
    template = _synth_security_stack("dev")
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "sts:AssumeRole",
                                "Effect": "Allow",
                                "Principal": {"Service": "ec2.amazonaws.com"},
                            }
                        ),
                        Match.object_like(
                            {
                                "Action": "sts:AssumeRole",
                                "Effect": "Allow",
                                "Principal": {"AWS": Match.any_value()},
                            }
                        ),
                    ]
                ),
            }
        },
    )


def test_nonprod_creates_staging_named_ci_roles():
    # Role names keep the env name (not the scope name) so the GitHub
    # workflows reference stable ARNs.
    template = _synth_security_stack("dev")
    template.has_resource_properties(
        "AWS::IAM::Role", {"RoleName": "flowform-staging-frontend-deploy"}
    )
    template.has_resource_properties(
        "AWS::IAM::Role", {"RoleName": "flowform-staging-ci-preview"}
    )


def test_ci_roles_trust_only_their_required_github_oidc_subjects():
    template = _synth_security_stack("dev")
    environment_subject = "repo:Shayman-M-86/FlowForm:environment:staging"
    staging_branch_subject = "repo:Shayman-M-86/FlowForm:ref:refs/heads/staging"

    for role_name in [
        "flowform-staging-frontend-deploy",
        "flowform-staging-image-publisher",
    ]:
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": role_name,
                "AssumeRolePolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Action": "sts:AssumeRoleWithWebIdentity",
                                    "Condition": {
                                        "StringEquals": {
                                            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                                            "token.actions.githubusercontent.com:sub": environment_subject,
                                        }
                                    },
                                }
                            )
                        ]
                    )
                },
            },
        )

    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "flowform-staging-ci-preview",
            "AssumeRolePolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "sts:AssumeRoleWithWebIdentity",
                                "Condition": {
                                    "StringEquals": {
                                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                                        "token.actions.githubusercontent.com:sub": staging_branch_subject,
                                    }
                                },
                            }
                        )
                    ]
                )
            },
        },
    )


def test_ci_roles_do_not_trust_an_arbitrary_repository_oidc_subject():
    template = _synth_security_stack("dev").to_json()
    assert "repo:Shayman-M-86/FlowForm:*" not in str(template)


def test_ssm_parameters_created():
    template = _synth_security_stack("dev")
    # kms-key-arn, aws-region, hosted-zone-id, app-role-arn,
    # linkage-secret-arn
    template.resource_count_is("AWS::SSM::Parameter", 5)
    template.has_resource_properties(
        "AWS::SSM::Parameter", {"Name": "/flowform/nonprod/kms-key-arn"}
    )


def test_app_role_has_scoped_bootstrap_reads_without_repository_wildcards():
    template = _synth_security_stack("dev")
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": [
                                    "ssm:GetParameter",
                                    "ssm:GetParameters",
                                    "ssm:GetParametersByPath",
                                ],
                                "Resource": Match.array_with(
                                    [
                                        {
                                            "Fn::Join": [
                                                "",
                                                Match.array_with(
                                                    [
                                                        ":ssm:ap-southeast-2:908123139858:parameter/flowform/nonprod/*"
                                                    ]
                                                ),
                                            ]
                                        },
                                        {
                                            "Fn::Join": [
                                                "",
                                                Match.array_with(
                                                    [
                                                        ":ssm:ap-southeast-2:908123139858:parameter/flowform/staging/*"
                                                    ]
                                                ),
                                            ]
                                        },
                                    ]
                                ),
                            }
                        ),
                    ]
                )
            }
        },
    )
    assert "repository/flowform-staging-*" not in str(template.to_json())
